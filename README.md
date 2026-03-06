# 16S Processing Workflow (NCBI + GTDB + barrnap)
16S extraction workflow for `2753` genome accessions listed in `texts/all_gca.txt`.

## Overview
Workflow was executed in four stages:

1. Download all assemblies from NCBI (`scripts/ncbi.py`) into `ncbi/`.
2. Split by assembly level (`Complete Genome`, `Contig`, `Scaffold`, `Chromosome`) using `assembly_data_report.jsonl`.
3. For non-complete assemblies, use GTDB `data/bac120_ssu_reps.fna` when possible.
4. For remaining non-complete assemblies not present in GTDB, run `barrnap` on NCBI genomic FASTA files.

## Assembly-Level Counts (from NCBI reports)
- Complete Genome: `543`
- Contig: `1260`
- Scaffold: `899`
- Chromosome: `51`
- Total: `2753`

## Output Structure
### 1) Complete Genome outputs

- `16s_rRNA/`: `542` accessions with 16S files named as `ACCESSION_(bp).fna`
- `16s_rRNA_complete_short/`: `1` accession with short 16S (`1074 bp`)

Reference lists:
- `texts/542_complete_1400_1600.txt`
- `texts/1_complete_1074.txt`

### 2) Non-complete outputs from GTDB (2065 accessions)

Source: `data/bac120_ssu_reps.fna`

- `16s_rRNA_noncomplete/yes/contig`: `1039` files
- `16s_rRNA_noncomplete/yes/scaffold`: `648` files
- `16s_rRNA_noncomplete/yes/chromosome`: `47` files
- `16s_rRNA_noncomplete/no/contig`: `127` files
- `16s_rRNA_noncomplete/no/scaffold`: `200` files
- `16s_rRNA_noncomplete/no/chromosome`: `4` files

Reference lists:
- `texts/1734_noncomplete_1400_1600.txt`
- `texts/331_noncomplete.txt`

### 3) Non-complete assemblies not in GTDB (145 accessions)
Input genomic FASTA files:
- `16s_rRNA_noncomplete_barrnap/*.fna` (one per accession)

barrnap outputs:
- `16s_rRNA_noncomplete_barrnap/yes/`:
  - `11` accessions with 16S hits
  - files per accession: `*.rRNA.gff3`, `*.16S.gff3`, `*.16S.fna`
- `16s_rRNA_noncomplete_barrnap/no/`:
  - `134` accessions without 16S hits
  - same file triplet format

Reference lists:
- `texts/145_noncomplete_barrnap.txt`
- `texts/134_noncomplete_barrnap.txt`
- `texts/10_noncomplete_barrnap.txt` (subset: 16S hit exists but not 1400-1600 bp)
- `texts/1_noncomplete_1400_1600.txt` (single non-complete accession in 1400-1600 bp range)

## Script Notes
- NCBI download script: `scripts/ncbi.py`
- barrnap command template: `barrnap.sh`
- Environment used for barrnap: `barnnap` (contains `barrnap` and `bedtools`)
