#!/usr/bin/bash

path_root="/home/nev/scripts/ob_inst_survey/data/logs_TAN2212/"

# prefix="GNS22-PF"
# start="179.117367 -38.233217 1992"
# nmea_file="${path_root}nmea/POSMV_2022-10-15_15-05.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-15_15-05.txt"

# prefix="GNS22-PI"
# start="178.829333 -38.597317 958"
# nmea_file="${path_root}nmea/POSMV_2022-10-14_14-17.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-14_14-17.txt"

# prefix="GNS22-PJ"
# start="178.493000 -38.827300 707"
# nmea_file="${path_root}nmea/POSMV_2022-10-13_14-21.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-13_14-21.txt"

# prefix="GNS22-PK"
# start="178.839683 -38.9475 2203"
# nmea_file="${path_root}nmea/POSMV_2022-10-12_14-47.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-12_14-47.txt"

# prefix="GNS22-PL"
# start="178.367133 -38.955083 1231"
# nmea_file="${path_root}nmea/POSMV_2022-10-13_19-01.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-13_19-01.txt"

# prefix="GNS22-PM"
# start="178.630417 -38.985283 1547"
# nmea_file="${path_root}nmea/POSMV_2022-10-12_21-32.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-12_21-32.txt"

# prefix="GNS22-PO"
# start="178.973383 -39.15585 3430"
# nmea_file="${path_root}nmea/POSMV_2022-10-11_22-45.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-11_22-45.txt"

# prefix="GNS22-PP"
# start="178.532917 -39.524050 2036"
# nmea_file="${path_root}nmea/POSMV_2022-10-11_17-30.txt"
# etech_file="${path_root}raw/raw_edgetech_2022-10-11_17-30.txt"

path_root="/home/nev/scripts/ob_inst_survey/data/logs_TAN2301/"

# prefix="GNS22-PF2"
# start="179.1153 -38.2351 2000"
# nmea_file="${path_root}nmea/POSMV_2023-01-07_04-42.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-07_04-42.txt"

# prefix="GNS22-PH"
# start="178.6872 -38.737833 1000"
# nmea_file="${path_root}nmea/POSMV_2023-01-06_12-23.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-06_12-23.txt"

# prefix="GNS22-PI2"
# start="178.83097 -38.594983 960"
# nmea_file="${path_root}nmea/POSMV_2023-01-07_07-52.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-07_07-52.txt"

# prefix="GNS22-PJ2"
# start="178.49247 -38.82855 730"
# nmea_file="${path_root}nmea/POSMV_2023-01-07_10-57.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-07_10-57.txt"

# prefix="GNS22-PK2"
# start="178.83772 -38.947067 2170"
# nmea_file="${path_root}nmea/POSMV_2023-01-07_21-22.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-07_21-22.txt"

# prefix="LDE22-AF"
# start="178.55633 -38.776833 878"
# nmea_file="${path_root}nmea/POSMV_2023-01-06_09-58.txt"
# etech_file="${path_root}raw/raw_edgetech_2023-01-06_09-58.txt"

prefix="LDE22-AH"
start="178.41928 -38.896667 1187"
nmea_file="${path_root}nmea/POSMV_2023-01-06_07-24.txt"
etech_file="${path_root}raw/raw_edgetech_2023-01-06_07-24.txt"

python /home/nev/scripts/ob_inst_survey/ranging_survey.py \
--replaynmea $nmea_file \
--replayrange $etech_file \
--startcoord  $start \
--replayspeed 60 \
--timestampoffset -45 \
--outfilepath ~/logs/ \
--outfileprefix $prefix
# --lograw

# python /home/nev/scripts/ob_inst_survey/ranging_survey.py -h