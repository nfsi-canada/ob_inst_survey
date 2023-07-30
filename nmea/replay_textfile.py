"""
Simulates an NMEA stream from a previously saved NMEA text file.
"""
from datetime import datetime, timedelta
import queue as qu
import re
from threading import Thread
from time import sleep


def replay_textfile(
    filename: str,
    nmea_q: qu.Queue[str],
    timestamp_start: datetime = None,
    spd_fctr: int = 1,
):
    """Initiate a queue simulating an NMEA data stream from a text file."""
    Thread(
        target=__nmea_from_file,
        args=(filename, nmea_q, timestamp_start, spd_fctr),
        daemon=True,
    ).start()


def __nmea_from_file(
    filename: str,
    nmea_q: qu.Queue[str],
    timestamp_start: datetime,
    spd_fctr: int,
):
    timestamp_prev = timestamp_start
    timestamp_days = timedelta(days=0)
    actltime_start = datetime.now()
    with open(filename, encoding="utf-8") as nmea_file:
        for sentence in nmea_file:
            sentence = re.sub(r"^.*\$", "$", sentence.strip())
            nmea_items = sentence.split(sep=",")
            if re.match(r"\d{6}\.\d{2,4}", nmea_items[1]):
                timestamp_curr = datetime.strptime(nmea_items[1], "%H%M%S.%f")
                if not timestamp_start:
                    timestamp_start = timestamp_curr
                    timestamp_prev = timestamp_start
                if timestamp_curr.hour < timestamp_prev.hour:
                    timestamp_days = timestamp_days + timedelta(days=1)
                timestamp_prev = timestamp_curr
                timestamp_diff = timestamp_curr + timestamp_days - timestamp_start
                while True:
                    # Pause until time for next NMEA sentence
                    sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                    actltime_diff = (datetime.now() - actltime_start) * spd_fctr
                    if actltime_diff >= timestamp_diff:
                        break
            nmea_q.put(sentence)

    nmea_q.put("EOF")
