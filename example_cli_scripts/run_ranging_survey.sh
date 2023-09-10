#!/usr/bin/bash

# path_root="/home/nev/scripts/ob_inst_survey/data/logs_TAN2301/"
# nmea_file="${path_root}nmea/POSMV_2023-01-06_12-23.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-06_12-23.txt"

path_root="/home/nev/scripts/ob_inst_survey/data/logs_TAN2212/"
nmea_file="${path_root}nmea/POSMV_2022-10-11_22-45.txt"
etech_file="${path_root}raw/raw_edgetech_2022-10-11_22-45.txt"
# nmea_file="${path_root}nmea/POSMV_2022-10-12_14-47.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-12_14-47.txt"

python /home/nev/scripts/ob_inst_survey/ranging_survey.py \
--replaynmea $nmea_file \
--replayrange $etech_file \
--replayspeed 50 \
--outfilepath ~/logs/ \
--outfileprefix SURVEY
# --lograw
