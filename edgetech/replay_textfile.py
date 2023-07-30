"""
Simulates a serial stream from a previously saved EdgeTech deckbox streamed 
text file.
"""
from datetime import datetime
import queue as qu
import re
from threading import Thread
from time import sleep


def replay_textfile(
    filename: str,
    edgetech_q: qu.Queue[str],
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
    edgetech_q: qu.Queue[str],
    timestamp_start: datetime,
    spd_fctr: int,
):
    actltime_start = datetime.now()
    with open(filename, encoding="utf-8") as etech_file:
        for sentence in etech_file:
            sentence = re.sub(r"(\d{2}) (\d{2})", "\g<1>T\g<2>", sentence.strip())
            sentence = re.sub(r": b'", " ", sentence)
            sentence = re.sub(r"\\r\\n'", "", sentence)
            timestamp_curr = datetime.strptime(sentence[0:26], "%Y-%m-%dT%H:%M:%S.%f")
            if not timestamp_start:
                timestamp_start = timestamp_curr
            timestamp_diff = timestamp_curr - timestamp_start
            while True:
                # Pause until time for next NMEA sentence
                sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                actltime_diff = (datetime.now() - actltime_start) * spd_fctr
                # print(f"{timestamp_diff=} {actltime_diff=}")
                if actltime_diff >= timestamp_diff:
                    break
            edgetech_q.put(sentence)

        edgetech_q.put("EOF")
