"""
Main script for testing ob_inst_survey package
"""
from datetime import datetime
import queue as qu
import sys
from time import sleep

import ob_inst_survey as obsurv


def main():
    """Main function."""
    # timestamp_start = datetime.strptime("012635.12", "%H%M%S.%f")
    timestamp_start = None

    nmea_q: qu.Queue[str] = qu.Queue()

    # ip_conn = obsurv.IpParam(port=50001, addr="192.168.1.131")  # Defaults to UDP
    # Valid UPD addresses:
    #   socket.gethostbyname(socket.gethostname())
    #   "0.0.0.0",
    #   "127.0.0.1",
    #   "192.168.1.133",
    ip_conn = obsurv.IpParam(port=50000, addr="192.168.1.107", prot="TCP")

    # obsurv.nmea_ip_stream(ip_conn, nmea_q)

    nmea_filename = "./data/nmea/POSMV_2023-04-14_13-26.txt"
    # obsurv.nmea_replay_textfile(nmea_filename, nmea_q, timestamp_start, 10)

    turn_time: float = 12.5  # Delay in ms for reply from BPR transducer.
    snd_spd: int = 1500  # Speed of sound in water (typical 1450 to 1570 m/sec)

    edgetech_q: qu.Queue[str] = qu.Queue()
    et_filename = "./data/logs_TAN2301/raw/raw_edgetech_2023-01-06_09-58.txt"
    obsurv.etech_replay_textfile(et_filename, edgetech_q, timestamp_start, 100)

    try:
        while True:
            sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
            process_next_nmea_sentence(nmea_q)
            process_next_edgetech_sentence(edgetech_q)
    except KeyboardInterrupt:
        sys.exit("*** End Survey ***")


def process_next_nmea_sentence(nmea_q: qu.Queue):
    """Get next element from NMEA queue and process as NMEA sentence."""
    if nmea_q.empty():
        return
    nmea_str = nmea_q.get(block=False)
    if nmea_str in ["TimeoutError", "EOF"]:
        sys.exit(f"*** {nmea_str} ***")
    if not obsurv.nmea_checksum(nmea_str):
        print(
            f"!!! Checksum for NMEA line is invalid. Line has "
            f"been ignored: => {nmea_str}"
        )
    print(nmea_str)


def process_next_edgetech_sentence(edgetech_q: qu.Queue):
    """Get next element from queue and process as edgetech sentence."""
    if edgetech_q.empty():
        return
    edgetech_str = edgetech_q.get(block=False)
    if edgetech_str in ["TimeoutError", "EOF"]:
        sys.exit(f"*** {edgetech_str} ***")
    print(edgetech_str)


if __name__ == "__main__":
    main()
