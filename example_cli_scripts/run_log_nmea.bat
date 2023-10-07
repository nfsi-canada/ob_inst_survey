@REM python c:/scripts/ob_inst_survey/log_nmea_to_file.py ^
@REM --ipaddr 192.168.1.107 ^
@REM --ipport 50000 ^
@REM --ipprot TCP ^
@REM --outfilepath ../logs/nmea/ ^
@REM --outfileprefix NMEA

python c:/scripts/ob_inst_survey/log_nmea_to_file.py ^
--ipaddr 0.0.0.0 ^
--ipport 6044 ^
--ipprot UDP ^
--outfilepath ../logs/nmea/ ^
--outfileprefix NMEA
@REM --ipaddr 138.71.128.182 ^
@REM --ipaddr 138.71.128.106 ^


@REM python c:/scripts/ob_inst_survey/log_nmea_to_file.py ^
@REM --replayfile ../scripts/ob_inst_survey/data/logs_TAN2301/nmea/POSMV_2023-01-06_12-23.txt ^
@REM --replaystart "2023-01-06_23:19:47" ^
@REM --replayspeed 1 ^
@REM --outfilepath ~/logs/nmea/ ^
@REM --outfileprefix NMEA

@REM python c:/scripts/ob_inst_survey/log_nmea_to_file.py -h