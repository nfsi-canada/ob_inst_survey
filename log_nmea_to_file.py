"""
Log NMEA stream to a text file.
"""
from datetime import datetime
from pathlib import Path
import queue as qu
import sys
from time import sleep

import ob_inst_survey as obsurv

TIMESTAMP_START = datetime.now().strftime("%Y-%m-%d_%H-%M")
FILEPREFIX = "NMEA"
FILEPATH = Path("./logs/nmea/")
FILENAME = FILEPATH / f"{FILEPREFIX}_{TIMESTAMP_START}.txt"


def main(ip_conn=obsurv.IpParam):
    """
    Initialise NMEA data stream and log to text file.
    """
    FILEPATH.mkdir(parents=True, exist_ok=True)
    print(f"Logging to {FILENAME}")

    ip_conn = obsurv.IpParam(port=50000, addr="192.168.1.107", prot="TCP")
    ip_conn = obsurv.IpParam(port=50001, addr="127.0.0.1", prot="UDP")

    nmea_q: qu.Queue[str] = qu.Queue()
    obsurv.nmea_ip_stream(ip_conn, nmea_q)

    try:
        while True:
            sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
            sentence = get_next_sentence(nmea_q)
            if not sentence:
                continue
            with open(FILENAME, "a+", newline="", encoding="utf-8") as nmea_file:
                nmea_file.write(f"{sentence}\n")
                print(sentence)

    except KeyboardInterrupt:
        sys.exit("*** End NMEA Logging ***")


def get_next_sentence(nmea_q: qu.Queue) -> str:
    """Return next sentence from NMEA queue."""
    if nmea_q.empty():
        return None
    nmea_str = nmea_q.get(block=False)
    if nmea_str in ["TimeoutError", "EOF"]:
        sys.exit(f"*** {nmea_str} ***")
    if not obsurv.nmea_checksum(nmea_str):
        print(
            f"!!! Checksum for NMEA line is invalid. Line has "
            f"been ignored: => {nmea_str}"
        )
    return nmea_str


if __name__ == "__main__":
    main()
