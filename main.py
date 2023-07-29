"""
Main script for testing nmea package
"""
from datetime import datetime
import queue as qu
import sys

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
    # ip_conn = nmea.IpParam(port=50000, addr="192.168.1.107", prot="TCP")

    # nmea.ip_stream(ip_conn, nmea_q)

    timestamp_start = datetime.strptime("012635.12", "%H%M%S.%f")
    nmea.replay_textfile(
        "./data/nmea/POSMV_2023-04-14_13-26.txt", nmea_q, timestamp_start
    )

    while True:
        try:
            nmea_str = nmea_q.get(block=False)
            if nmea_str in ["TimeoutError", "EOF"]:
                sys.exit(nmea_str)
            if not nmea.checksum(nmea_str):
                print(
                    f"!!! Checksum for NMEA line is invalid. Line has been "
                    f"ignored: => {nmea_str}"
                )
            print(nmea_str)
        except qu.Empty:
            pass


if __name__ == "__main__":
    main()
