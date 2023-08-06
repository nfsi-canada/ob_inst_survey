"""
Simulates a serial stream from a previously saved EdgeTech deckbox streamed 
text file.
"""
from datetime import datetime
import queue as qu
import re
from threading import Thread
from time import sleep


def etech_replay_textfile(
    filename: str,
    edgetech_q: qu.Queue[str, datetime],
    timestamp_start: datetime = None,
    spd_fctr: int = 1,
):
    """Initiate a queue simulating an EdgeTech data stream from a text file."""
    Thread(
        target=__etech_from_file,
        args=(filename, edgetech_q, timestamp_start, spd_fctr),
        daemon=True,
    ).start()


def __etech_from_file(
    filename: str,
    edgetech_q: qu.Queue[str, datetime],
    timestamp_start: datetime,
    spd_fctr: int,
):
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
                timestamp_sntc = re.match(timestamp_pattern, sentence).group()
                timestamp_sntc = re.sub(r"[Tt :_-]", r"_", timestamp_sntc)
                timestamp = datetime.strptime(timestamp_sntc, r"%Y_%m_%d_%H_%M_%S.%f")
            except AttributeError:
                # If no valid timestamp continue with next line.
                continue
            # Remove timestamp and enclosing characters from EdgeTech response
            # sentence.
            sentence = re.sub(r"^.*([A-Z]{3}.*?)(\\r\\n')?$", r"\g<1>", sentence)
            if not timestamp_start:
                timestamp_start = timestamp
            timestamp_diff = timestamp - timestamp_start

            while True:
                # Pause until time for next NMEA sentence
                sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                actltime_diff = (datetime.now() - actltime_start) * spd_fctr
                # print(f"{timestamp_diff=} {actltime_diff=}")
                if actltime_diff >= timestamp_diff:
                    break
            edgetech_q.put((sentence, timestamp))

        edgetech_q.put(("EOF", None))
