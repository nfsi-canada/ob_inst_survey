"""Simulates an NMEA stream from a previously saved NMEA text file."""

import re
from datetime import datetime, timedelta, timezone
from queue import Queue
from threading import Thread
from time import sleep


def nmea_replay_textfile(
    filename: str,
    nmea_q: Queue[str],
    actltime_start: datetime = None,
    timestamp_start: datetime = None,
    spd_fctr: float = 1,
):
    """Initiate a queue simulating an NMEA data stream from a text file."""
    Thread(
        target=__nmea_from_file,
        args=(filename, nmea_q, actltime_start, timestamp_start, spd_fctr),
        daemon=True,
    ).start()


def __nmea_from_file(
    filename: str,
    nmea_q: Queue[str],
    actltime_start: datetime,
    timestamp_start: datetime,
    spd_fctr: int,
):
    timestamp_prev = timestamp_start
    timestamp_date = None
    if not actltime_start:
        actltime_start = datetime.now(timezone.utc)
    with open(filename, encoding="utf-8") as nmea_file:
        for sentence in nmea_file:
            sentence = re.sub(r"^.*\$", "$", sentence.strip())
            nmea_items = sentence.split(sep=",")
            if re.match(r"\d{6}\.\d{0,4}", nmea_items[1]):
                if nmea_items[1][:6] == "240000":
                    # At UTC midnight timestamp may incorrectly show hrs as 24.
                    nmea_items[1] = "000000.000"
                timestamp_curr = datetime.strptime(nmea_items[1], "%H%M%S.%f")
                secs = (
                    timestamp_curr.hour * 3600
                    + timestamp_curr.minute * 60
                    + timestamp_curr.second
                    + timestamp_curr.microsecond / 1e6
                )
                timestamp_delta = timedelta(seconds=secs)
                if not timestamp_date:
                    timestamp_date = datetime(1900, 1, 1)
                timestamp_curr = timestamp_date + timestamp_delta
                if not timestamp_start:
                    timestamp_start = timestamp_curr
                    timestamp_prev = timestamp_start
                if timestamp_curr.hour < timestamp_prev.hour:
                    timestamp_date = timestamp_date + timedelta(days=1)
                timestamp_prev = timestamp_curr
                timestamp_diff = timestamp_curr - timestamp_start

                while True:
                    # Pause until time for next NMEA sentence
                    sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
                    now = datetime.now(timezone.utc)
                    actltime_diff = (now - actltime_start) * spd_fctr
                    if actltime_diff >= timestamp_diff:
                        break
            nmea_q.put(sentence)

    nmea_q.put("EOF")


def set_timestamp_date(timestamp_curr, timestamp_start):
    """Returns initial date to be prepended to NMEA timestamp."""
    date = datetime(timestamp_start.year, timestamp_start.month, timestamp_start.day)
    if timestamp_curr.hour > timestamp_start.hour:
        return date - timedelta(days=1)
    else:
        return date
