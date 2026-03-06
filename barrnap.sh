# 0) Set barrnap/bedtools path
export PATH="/home/lukecarlate/.conda/envs/barnnap/bin:$PATH"

# 1) Working directory
cd /data/lukecarlate/gtdb3/genomes_barrnap_fna_only

# 2) Generate full rRNA hit GFF3
barrnap --quiet --threads 10 --kingdom bac --reject 0.1 \
"GCA_003326195.1.fna" > "GCA_003326195.1.rRNA.gff3"

# 3) Filter 16S hits only
awk -F '\t' '$0 !~ /^#/ && $9 ~ /Name=16S_rRNA/ {print}' \
"GCA_003326195.1.rRNA.gff3" > "GCA_003326195.1.16S.gff3"

# 4) Extract 16S coordinate sequences (including strand orientation)
awk -F '\t' 'BEGIN{OFS="\t"} {print $1,$4-1,$5,$1":"$4"-"$5"("$7")",$6,$7}' \
"GCA_003326195.1.16S.gff3" \
| bedtools getfasta -fi "GCA_003326195.1.fna" -bed - -s -name \
> "GCA_003326195.1.16S.fna"