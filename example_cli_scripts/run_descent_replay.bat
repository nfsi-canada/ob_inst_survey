@REM python "C:\scripts\ob_inst_survey\ascent_descent_tracking.py" -h

@REM python "C:\scripts\ob_inst_survey\ascent_descent_tracking.py" ^
@REM --replaynmea ./nmea/POSMV_2022-10-11_16-41.txt ^
@REM --replayrange ./raw/raw_edgetech_2022-10-11_16-41.txt ^
@REM --startcoord  178.532052 -39.522104 2036 ^
@REM --outfileprefix "GNS22-PP" ^
@REM --replayspeed 10 ^
@REM --timestampoffset -45

python "C:\scripts\ob_inst_survey\ascent_descent_tracking.py" ^
--replaynmea ./nmea/POSMV_2022-10-11_21-46.txt ^
--replayrange ./raw/raw_edgetech_2022-10-11_21-46.txt ^
--startcoord  178.973383 -39.15585 3430 ^
--outfileprefix "GNS22-PO" ^
--replayspeed 10 ^
--timestampoffset -45

