"""
Log EdgeTech deckbox serial responses to a text file.
"""
from datetime import datetime
from pathlib import Path
import queue as qu
import sys
from time import sleep

import ob_inst_survey as obsurv

TIMESTAMP_START = datetime.now().strftime("%Y-%m-%d_%H-%M")
FILEPREFIX = "edgetech"
FILEPATH = Path("./logs/edgetech/")
FILENAME = FILEPATH / f"{FILEPREFIX}_{TIMESTAMP_START}.txt"


def main(ser_conn=obsurv.IpParam):
    """
   Initialise EdgeTech data stream and log to text file.
    """
    FILEPATH.mkdir(parents=True, exist_ok=True)
    print(f"Logging to {FILENAME}")

    ser_conn = obsurv.SerParam(port="COM5", baud=9600)

    edgetech_q: qu.Queue[str] = qu.Queue()
    obsurv.etech_serial_stream(ser_conn, edgetech_q)

    try:
        while True:
            sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
            sentence = get_next_sentence(edgetech_q)
            if not sentence:
                continue
            with open(FILENAME, "a+", newline="", encoding="utf-8") as log_file:
                log_file.write(f"{sentence}\n")
                print(sentence)

    except KeyboardInterrupt:
        sys.exit("*** End EdgeTech Logging ***")


def get_next_sentence(edgetech_q: qu.Queue) -> str:
    """Return next sentence from NMEA queue."""
    if edgetech_q.empty():
        return None
    edgetech_str = edgetech_q.get(block=False)
    if edgetech_str in ["TimeoutError", "EOF"]:
        sys.exit(f"*** {edgetech_str} ***")
    return edgetech_str


if __name__ == "__main__":
    main()
