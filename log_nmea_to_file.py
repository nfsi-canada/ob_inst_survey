"""
Log NMEA stream to a text file.
"""
from argparse import ArgumentParser
from datetime import datetime, timezone, timedelta
from pathlib import Path
from queue import Queue
import sys
from time import sleep

import ob_inst_survey as obsurv

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
            obsurv.file_split_parser(),
            obsurv.replayfile_parser(None),
        ],
        description=helpdesc,
    )
    args = parser.parse_args()
    outfilepath: Path = args.outfilepath
    outfileprefix: str = args.outfileprefix
    ip_param = obsurv.IpParam(
        port=args.ipport,
        addr=args.ipaddr,
        prot=args.ipprot,
        buffer=args.ipbuffer,
    )
    file_split_hours: int = args.filesplit
    last_file_split = 0
    replay_file: Path = args.replayfile
    replay_start: datetime = args.replaystart
    replay_speed: float = args.replayspeed

    # Create directory for logging.
    outfilepath.mkdir(parents=True, exist_ok=True)
    print(f"Logging NMEA to directory {outfilepath}")

    nmea_q: Queue[str] = Queue()
    if replay_file:
        obsurv.nmea_replay_textfile(
            filename=replay_file,
            nmea_q=nmea_q,
            spd_fctr=replay_speed,
            timestamp_start=replay_start,
        )
    else:
        obsurv.nmea_ip_stream(
            ip_conn=ip_param,
            nmea_q=nmea_q,
        )

    try:
        while True:
            sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
            sentence = get_next_sentence(nmea_q)
            if not sentence:
                continue

            nmea_time = time_from_nmea(sentence)
            if nmea_time:
                curr_file_split = int(nmea_time.timestamp()/(file_split_hours*3600))
                if curr_file_split > last_file_split:
                    file_timestamp = nmea_time.strftime("%Y-%m-%d_%H-%M")
                    outfilename: str = outfilepath / f"{outfileprefix}_{file_timestamp}.txt"
                    last_file_split = curr_file_split
            elif last_file_split == 0:
                continue

            with open(outfilename, "a+", newline="", encoding="utf-8") as nmea_file:
                nmea_file.write(f"{sentence}\n")
                print(sentence)

    except KeyboardInterrupt:
        sys.exit("*** End NMEA Logging ***")


def get_next_sentence(nmea_q: Queue) -> str:
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


def time_from_nmea(sentence: str) -> datetime:
    """Return the time from an NMEA sentence"""
    try:
        nmea_hr = int(sentence[7:9])
        nmea_min = int(sentence[9:11])
        nmea_sec = int(sentence[11:13])
    except ValueError:
        return 0
    sys_time = datetime.now(timezone.utc)
    sys_yr = sys_time.year
    sys_mth = sys_time.month
    sys_day = sys_time.day
    sys_hr = sys_time.hour
    nmea_time = datetime(sys_yr, sys_mth, sys_day, nmea_hr, nmea_min, nmea_sec)
    nmea_time = nmea_time.replace(tzinfo=timezone.utc)
    if nmea_hr == 0 and sys_hr == 23:
        nmea_time += timedelta(days=1)
    if nmea_hr == 23 and sys_hr == 0:
        nmea_time -= timedelta(days=1)

    return nmea_time


if __name__ == "__main__":
    main()
