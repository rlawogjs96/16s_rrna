#!/usr/bin/env python3
"""
Download NCBI genome datasets for a list of assembly accessions.

Given an accession list file (e.g., all_gca.txt), this script downloads one
NCBI data package per accession via the `datasets` CLI and extracts each package
to:

  <output_dir>/<ACCESSION>/

so the directory layout matches the expected form:

  <output_dir>/<ACCESSION>/ncbi_dataset/data/assembly_data_report.jsonl
  <output_dir>/<ACCESSION>/ncbi_dataset/data/<ACCESSION>/*_genomic.fna
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path


ACCESSION_RE = re.compile(r"(GCA|GCF)_\d+\.\d+")


def load_accessions(path: Path) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = ACCESSION_RE.search(line)
        if not m:
            continue
        acc = m.group(0)
        if acc in seen:
            continue
        seen.add(acc)
        ordered.append(acc)
    return ordered


def has_expected_files(accession_dir: Path, accession: str) -> bool:
    report = accession_dir / "ncbi_dataset" / "data" / "assembly_data_report.jsonl"
    genome_dir = accession_dir / "ncbi_dataset" / "data" / accession
    genome_fna = list(genome_dir.glob("*_genomic.fna"))
    return report.is_file() and len(genome_fna) > 0


def run_datasets_download(
    accession: str,
    zip_path: Path,
    datasets_bin: str,
    include: str,
    api_key: str | None,
) -> tuple[bool, str]:
    cmd = [
        datasets_bin,
        "download",
        "genome",
        "accession",
        accession,
        "--include",
        include,
        "--filename",
        str(zip_path),
        "--no-progressbar",
    ]
    if api_key:
        cmd.extend(["--api-key", api_key])

    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        return False, err if err else f"datasets failed with exit code {proc.returncode}"
    return True, ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Download genome data packages from NCBI Datasets for accession IDs "
            "listed in a text file."
        )
    )
    p.add_argument(
        "--accessions",
        type=Path,
        default=Path("all_gca.txt"),
        help="Input text file containing GCA/GCF accessions (default: all_gca.txt).",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ncbi"),
        help="Output directory root for per-accession packages (default: ncbi).",
    )
    p.add_argument(
        "--datasets-bin",
        default="datasets",
        help="Path/name of NCBI datasets CLI executable (default: datasets).",
    )
    p.add_argument(
        "--include",
        default="genome",
        help="datasets --include value (default: genome).",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Optional NCBI API key passed to datasets CLI.",
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip accession if expected files already exist in output.",
    )
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Delay between accessions to reduce request rate (default: 0).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit of accessions to process (0 = all).",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if not args.accessions.is_file():
        raise SystemExit(f"Accessions file not found: {args.accessions}")

    accessions = load_accessions(args.accessions)
    if not accessions:
        raise SystemExit("No valid GCA/GCF accessions found in input file.")

    if args.limit > 0:
        accessions = accessions[: args.limit]

    out_root: Path = args.output_dir
    out_root.mkdir(parents=True, exist_ok=True)

    # Quick executable check (fails fast if datasets is unavailable).
    probe = subprocess.run(
        [args.datasets_bin, "--help"],
        text=True,
        capture_output=True,
    )
    if probe.returncode != 0:
        msg = (probe.stderr or probe.stdout or "").strip()
        raise SystemExit(
            f"Failed to run '{args.datasets_bin} --help'. "
            f"Check datasets CLI installation. Details: {msg}"
        )

    ok = 0
    skipped = 0
    failed = 0

    for i, accession in enumerate(accessions, start=1):
        acc_dir = out_root / accession

        if args.skip_existing and has_expected_files(acc_dir, accession):
            skipped += 1
            print(f"[{i}/{len(accessions)}] SKIP {accession} (already present)")
            continue

        tmp_zip = out_root / f".{accession}.zip"
        tmp_extract = out_root / f".{accession}.tmp"

        if tmp_zip.exists():
            tmp_zip.unlink()
        if tmp_extract.exists():
            shutil.rmtree(tmp_extract)
        tmp_extract.mkdir(parents=True, exist_ok=True)

        success, error = run_datasets_download(
            accession=accession,
            zip_path=tmp_zip,
            datasets_bin=args.datasets_bin,
            include=args.include,
            api_key=args.api_key,
        )
        if not success:
            failed += 1
            print(f"[{i}/{len(accessions)}] FAIL {accession} :: {error}")
            if tmp_zip.exists():
                tmp_zip.unlink()
            if tmp_extract.exists():
                shutil.rmtree(tmp_extract)
            continue

        try:
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(tmp_extract)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[{i}/{len(accessions)}] FAIL {accession} :: unzip error: {exc}")
            if tmp_zip.exists():
                tmp_zip.unlink()
            if tmp_extract.exists():
                shutil.rmtree(tmp_extract)
            continue
        finally:
            if tmp_zip.exists():
                tmp_zip.unlink()

        if not has_expected_files(tmp_extract, accession):
            failed += 1
            print(
                f"[{i}/{len(accessions)}] FAIL {accession} :: "
                "downloaded package missing expected assembly report/genome fasta"
            )
            shutil.rmtree(tmp_extract, ignore_errors=True)
            continue

        if acc_dir.exists():
            shutil.rmtree(acc_dir)
        tmp_extract.rename(acc_dir)
        ok += 1
        print(f"[{i}/{len(accessions)}] OK   {accession}")

        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    print("\nDownload summary")
    print(f"Input accessions: {len(accessions)}")
    print(f"Downloaded OK: {ok}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Output directory: {out_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
