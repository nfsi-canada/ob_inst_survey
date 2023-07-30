"""
Main script for testing nmea package
"""
from datetime import datetime
import queue as qu
import sys
from time import sleep

import nmea


def main():
    """Main function."""
    nmea_q = qu.Queue()

    # ip_conn = nmea.IpParam(port=50001, addr="192.168.1.131")  # Defaults to UDP
    # Valid UPD addresses:
    #   socket.gethostbyname(socket.gethostname())
    #   "0.0.0.0",
    #   "127.0.0.1",
    #   "192.168.1.133",
    ip_conn = nmea.IpParam(port=50000, addr="192.168.1.107", prot="TCP")

    # nmea.ip_stream(ip_conn, nmea_q)

    filename = "./data/nmea/POSMV_2023-04-14_13-26.txt"
    # timestamp_start = datetime.strptime("012635.12", "%H%M%S.%f")
    timestamp_start = None
    nmea.replay_textfile(filename, nmea_q, timestamp_start, 10)

    try:
        while True:
            process_next_nmea_sentence(nmea_q)
    except KeyboardInterrupt:
        sys.exit("*** End Survey ***")


def process_next_nmea_sentence(nmea_q: qu.Queue):
    """Get next element from NMEA queue and process as NMEA sentence."""
    if nmea_q.empty():
        sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
        return
    nmea_str = nmea_q.get(block=False)
    if nmea_str in ["TimeoutError", "EOF"]:
        sys.exit(f"*** {nmea_str} ***")
    if not nmea.checksum(nmea_str):
        print(
            f"!!! Checksum for NMEA line is invalid. Line has "
            f"been ignored: => {nmea_str}"
        )
    print(nmea_str)


if __name__ == "__main__":
    main()
