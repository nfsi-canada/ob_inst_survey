#!/usr/bin/bash

path_root="/home/nev/scripts/ob_inst_survey/data/logs_TAN2301/"
nmea_file="${path_root}nmea/POSMV_2023-01-06_12-23.txt"
etech_file="${path_root}raw/raw_edgetech_2023-01-06_12-23.txt"

python /home/nev/scripts/ob_inst_survey/ranging_survey_to_file.py \
--replaynmea $nmea_file \
--replayrange $etech_file \
--replayspeed 100 \
--outfilepath ~/logs/ \
--outfileprefix SURVEY
# --lograw
