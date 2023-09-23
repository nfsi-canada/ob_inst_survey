#!/usr/bin/bash

# python ~/scripts/ob_inst_survey/log_etech_to_file.py \
# --serport COM5 \
# --serbaud 9600 \
# --serparity N \
# --serstop 1 \
# --serbytesize 8 \
# --outfilepath ~/logs/etech/ \
# --outfileprefix EdgeTech

python ~/scripts/ob_inst_survey/log_etech_to_file.py \
--replayfile ~/scripts/ob_inst_survey/data/logs_TAN2301/raw/raw_edgetech_2023-01-06_12-23.txt \
--replayspeed 100 \
--outfilepath ~/logs/etech/ \
--outfileprefix EdgeTech
# --replaystart "2023-01-06_12:19:47" \

# python ~/scripts/ob_inst_survey/log_etech_to_file.py -h
