#!/usr/bin/env python3
"""
Extract GTDB SSU sequences for accession IDs.

Given an accession list (e.g., all_gca.txt) and a GTDB SSU FASTA
(e.g., bac120_ssu_reps.fna), this script writes one FASTA file per matched
accession in the style:

  <output_dir>/<ACCESSION>.fna

Each output file contains FASTA records copied from the GTDB SSU file.
"""

from __future__ import annotations

import argparse
import gzip
import re
from pathlib import Path
from typing import Iterator, TextIO


ACCESSION_RE = re.compile(r"(GCA|GCF)_\d+\.\d+")
SSU_LEN_RE = re.compile(r"\[ssu_len=(\d+)\]")

SSU_LEN_MIN = 1400
SSU_LEN_MAX = 1600


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def load_accessions(path: Path) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            match = ACCESSION_RE.search(line)
            if not match:
                continue
            accession = match.group(0)
            if accession not in seen:
                seen.add(accession)
                ordered.append(accession)
    return ordered


def iter_fasta(path: Path) -> Iterator[tuple[str, str]]:
    header: str | None = None
    seq_parts: list[str] = []

    with open_text(path) as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(seq_parts)
                header = line
                seq_parts = []
            elif header is not None:
                seq_parts.append(line.strip())

    if header is not None:
        yield header, "".join(seq_parts)


def write_list(path: Path, values: list[str]) -> None:
    content = "\n".join(values)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract per-accession 16S FASTA files from GTDB bac120_ssu_reps.fna "
            "for accession IDs listed in all_gca.txt."
        )
    )
    parser.add_argument(
        "--accessions",
        default="all_gca.txt",
        type=Path,
        help="Text file containing target accession IDs (default: all_gca.txt).",
    )
    parser.add_argument(
        "--fasta",
        default="bac120_ssu_reps.fna",
        type=Path,
        help="GTDB SSU FASTA file (default: bac120_ssu_reps.fna).",
    )
    parser.add_argument(
        "--output-dir",
        default="16s_rRNA",
        type=Path,
        help="Directory for per-accession FASTA output (default: 16s_rRNA).",
    )
    parser.add_argument(
        "--missing-out",
        default=None,
        type=Path,
        help=(
            "Optional file path to write accession IDs that were not found in the "
            "GTDB SSU FASTA."
        ),
    )
    parser.add_argument(
        "--found-out",
        default=None,
        type=Path,
        help="Optional file path to write accession IDs found in the GTDB SSU FASTA.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing <ACCESSION>.fna files in the output directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    accession_file: Path = args.accessions
    fasta_file: Path = args.fasta
    output_dir: Path = args.output_dir

    if not accession_file.is_file():
        raise SystemExit(f"Accessions file not found: {accession_file}")
    if not fasta_file.is_file():
        raise SystemExit(f"FASTA file not found: {fasta_file}")

    target_accessions = load_accessions(accession_file)
    target_set = set(target_accessions)
    if not target_accessions:
        raise SystemExit("No valid GCA/GCF accession IDs found in accessions file.")

    output_dir.mkdir(parents=True, exist_ok=True)

    existing_skipped: set[str] = set()
    if not args.overwrite:
        for accession in target_set:
            if (output_dir / f"{accession}.fna").exists():
                existing_skipped.add(accession)

    found_counts = {accession: 0 for accession in target_accessions}
    wrote_once: set[str] = set()
    records_written = 0

    for header, sequence in iter_fasta(fasta_file):
        match = ACCESSION_RE.search(header)
        if not match:
            continue

        accession = match.group(0)
        if accession not in target_set:
            continue

        ssu_match = SSU_LEN_RE.search(header)
        if ssu_match is None:
            continue
        ssu_len = int(ssu_match.group(1))
        if ssu_len < SSU_LEN_MIN or ssu_len > SSU_LEN_MAX:
            continue

        found_counts[accession] += 1

        if accession in existing_skipped:
            continue

        output_path = output_dir / f"{accession}.fna"
        mode = "w" if accession not in wrote_once else "a"
        with output_path.open(mode, encoding="utf-8") as out:
            out.write(f"{header}\n{sequence}\n\n")

        wrote_once.add(accession)
        records_written += 1

    found_accessions = [acc for acc in target_accessions if found_counts[acc] > 0]
    not_working_accessions = [acc for acc in target_accessions if found_counts[acc] == 0]

    if args.found_out is not None:
        write_list(args.found_out, found_accessions)
    if args.missing_out is not None:
        write_list(args.missing_out, not_working_accessions)

    print(f"Target accession IDs: {len(target_accessions)}")
    print(f"Found in GTDB SSU FASTA: {len(found_accessions)}")
    print(f"Do not satisfy length range: {len(not_working_accessions)}")
    print(f"Existing files skipped: {len(existing_skipped)}")
    print(f"Records written: {records_written}")
    print(f"Output directory: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
