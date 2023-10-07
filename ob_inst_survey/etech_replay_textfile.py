"""
Simulates a serial stream from a previously saved EdgeTech deckbox streamed 
text file.
"""
from datetime import datetime, timedelta
from queue import Queue
import re
from threading import Thread
from time import sleep


def etech_replay_textfile(
    filename: str,
    edgetech_q: Queue[str, datetime],
    actltime_start: datetime = None,
    timestamp_start: datetime = None,
    spd_fctr: int = 1,
    timestamp_offset: int = 0,
):
    """Initiate a queue simulating an EdgeTech data stream from a text file."""
    Thread(
        target=__etech_from_file,
        args=(
            filename,
            edgetech_q,
            actltime_start,
            timestamp_start,
            spd_fctr,
            timestamp_offset,
        ),
        daemon=True,
    ).start()


def __etech_from_file(
    filename: str,
    edgetech_q: Queue[str, datetime],
    actltime_start: datetime,
    timestamp_start: datetime,
    spd_fctr: int,
    timestamp_offset: int = 0,
):
    timestamp_prev = timestamp_start
    timestamp_date = None
    if not actltime_start:
        actltime_start = datetime.now()
    with open(filename, encoding="utf-8") as etech_file:
        for sentence in etech_file:
            sentence = sentence.strip()
            try:
                # Attempt to extract the timestamp from the beginning of each
                # senetence of the file replay.
                timestamp_pattern = (
                    r"^\d{4}[:_-]\d{2}[:_-]\d{2}[Tt :_-]"
                    r"\d{2}[:_-]\d{2}[:_-]\d{2}\.\d{0,6}"
                )
                timestamp_curr = re.match(timestamp_pattern, sentence).group()
                timestamp_curr = re.sub(r"[Tt :_-]", r"_", timestamp_curr)
                timestamp_curr = datetime.strptime(
                    timestamp_curr, r"%Y_%m_%d_%H_%M_%S.%f"
                )
            except AttributeError:
                # If no valid timestamp continue with next response line.
                continue
            # Ignore date portion of timestamp because when syncing with NMEA,
            # NMEA strings do not include dates.
            secs = (
                timestamp_curr.hour * 3600
                + timestamp_curr.minute * 60
                + timestamp_curr.second
                + timestamp_curr.microsecond / 10e6
            ) + timestamp_offset
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

            # Remove timestamp and enclosing characters from EdgeTech response
            # sentence.
            sentence = re.sub(r"^.*([A-Z]{3}.*?)(\\r\\n')?$", r"\g<1>", sentence)

            # Add "replay" flag at end of sentence.
            sentence = f"{sentence} replay"

            while True:
                # Pause until time for next EdgeTech sentence
                sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
                actltime_diff = (datetime.now() - actltime_start) * spd_fctr
                if actltime_diff >= timestamp_diff:
                    break
            edgetech_q.put((sentence, timestamp_curr))

        edgetech_q.put(("EOF", None))
