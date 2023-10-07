#!/usr/bin/bash

# python ~/scripts/ob_inst_survey/log_nmea_to_file.py \
# --ipaddr 192.168.1.107 \
# --ipport 50000 \
# --ipprot TCP \
# --outfilepath ~/logs/nmea/ \
# --outfileprefix NMEA

python ~/scripts/ob_inst_survey/log_nmea_to_file.py \
--ipaddr 138.71.128.106 \
--ipport 4066 \
--ipprot UDP \
--outfilepath ~/logs/nmea/ \
--outfileprefix NMEA
# --ipaddr 138.71.128.182 \


# python ~/scripts/ob_inst_survey/log_nmea_to_file.py \
# --replayfile ~/scripts/ob_inst_survey/data/logs_TAN2301/nmea/POSMV_2023-01-06_12-23.txt \
# --replaystart "2023-01-06_23:19:47" \
# --replayspeed 1 \
# --outfilepath ~/logs/nmea/ \
# --outfileprefix NMEA

# python ~/scripts/ob_inst_survey//log_nmea_to_file.py -h