#!/usr/bin/bash

# python ~/scripts/ob_inst_survey/ranging_survey_from_obsfile.py -h

# prefix="GNS23-PF"
# start="179.1107 -38.2399 1970"
# obs="./GNS23-PF_2023-10-31_01-41_OBSVNS.csv"

prefix="GNS23-PH"
start="178.68498 -38.73988 1000"
obs="GNS23-PH_2023-10-30_01-32_OBSVNS.csv"

python ~/scripts/ob_inst_survey/ranging_survey_from_obsfile.py \
--obsfile $obs \
--startcoord  $start \
--outfilepath ~/logs/rework/ \
--outfileprefix $prefix \


