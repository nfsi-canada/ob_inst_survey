#!/usr/bin/bash

# python ../log_etech_to_file.py \
# --serport COM5 \
# --serbaud 9600 \
# --serparity N \
# --serstop 1 \
# --serbytesize 8 \
# --outfilepath ~/logs/etech/ \
# --outfileprefix EdgeTech

python ../log_etech_to_file.py \
--replayfile ../data/logs_TAN2301/raw/raw_edgetech_2023-01-06_12-23.txt \
--replaystart "2023-01-06_12:19:47" \
--replayspeed 100 \
--outfilepath ~/logs/etech/ \
--outfileprefix EdgeTech

# python ../log_etech_to_file.py -h
