"""
Log NMEA stream to a text file.
"""
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
import queue as qu
import sys
from time import sleep

import ob_inst_survey as obsurv

TIMESTAMP_START = datetime.now().strftime("%Y-%m-%d_%H-%M")
DFLT_PREFIX = "NMEA"
DFLT_PATH = Path.home() / "logs/nmea/"


def main():
    """
    Initialise NMEA data stream and log to text file.
    """
    # Default CLI arguments.
    ip_param = obsurv.IpParam()

    # Retrieve CLI arguments.
    helpdesc: str = (
        "Receives an NMEA stream via either UDP or TCP over an IP connection "
        "and logs the received stream to a text file located in the directory "
        "specified. "
        "If an input file is specified (containg NMEA text sentences) then "
        "all IP parameters will be ignored and instead the specified file will "
        "be replayed as if it is a live stream."
    )
    parser = ArgumentParser(
        parents=[
            obsurv.out_filepath_parser(DFLT_PATH),
            obsurv.out_fileprefix_parser(DFLT_PREFIX),
            obsurv.ip_arg_parser(ip_param),
            obsurv.replayfile_parser(None),
        ],
        description=helpdesc,
    )
    args = parser.parse_args()
    outfilepath: Path = args.outfilepath
    outfilename: str = outfilepath / f"{args.outfileprefix}_{TIMESTAMP_START}.txt"
    ip_param = obsurv.IpParam(
        port=args.ipport,
        addr=args.ipaddr,
        prot=args.ipprot,
        buffer=args.ipbuffer,
    )
    replay_file: Path = args.replayfile
    replay_start: datetime = args.replaystart
    replay_speed: float = args.replayspeed

    # Create directory for logging.
    outfilepath.mkdir(parents=True, exist_ok=True)
    print(f"Logging NMEA to {outfilename}")

    nmea_q: qu.Queue[str] = qu.Queue()
    if replay_file:
        obsurv.nmea_replay_textfile(
            filename=replay_file,
            nmea_q=nmea_q,
            spd_fctr=replay_speed,
            timestamp_start=replay_start,
        )
    else:
        obsurv.nmea_ip_stream(ip_param, nmea_q)

    try:
        while True:
            sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
            sentence = get_next_sentence(nmea_q)
            if not sentence:
                continue
            with open(outfilename, "a+", newline="", encoding="utf-8") as nmea_file:
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
        sys.exit(f"*** NMEA: {nmea_str} ***")
    if not obsurv.nmea_checksum(nmea_str):
        print(
            f"!!! Checksum for NMEA line is invalid. Line has "
            f"been ignored: => {nmea_str}"
        )
    return nmea_str


if __name__ == "__main__":
    main()
