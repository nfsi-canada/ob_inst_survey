"""
Log EdgeTech deckbox serial responses to a text file.
"""
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from queue import Queue
import sys
from time import sleep

import ob_inst_survey as obsurv

TIMESTAMP_START = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
DFLT_PREFIX = "edgetech"
DFLT_PATH = Path.home() / "logs/edgetech/"


def main():
    """
    Initialise EdgeTech data stream and log to text file.
    """
    # Default CLI arguments.
    ser_param = obsurv.SerParam()

    # Retrieve CLI arguments.
    helpdesc: str = (
        "Receives a data stream from an EdgeTech 8011M acoustic deck box via "
        "serial connection and logs the received stream to a text file located "
        "in the directory specified. "
        "If an input file is specified (containg EdgeTech response sentences) "
        "then all serial parameters will be ignored and instead the specified "
        "file will be replayed as if it is a live stream."
    )
    parser = ArgumentParser(
        parents=[
            obsurv.out_filepath_parser(DFLT_PATH),
            obsurv.out_fileprefix_parser(DFLT_PREFIX),
            obsurv.ser_arg_parser(ser_param),
            obsurv.replayfile_parser(None),
        ],
        description=helpdesc,
    )
    args = parser.parse_args()
    outfilepath: Path = args.outfilepath
    outfilename: str = outfilepath / f"{args.outfileprefix}_{TIMESTAMP_START}.txt"
    ser_param = obsurv.SerParam(
        port=args.serport,
        baud=args.serbaud,
        stop=args.serstop,
        parity=args.serparity,
        bytesize=args.serbytesize,
    )
    replay_file: Path = args.replayfile
    replay_start: datetime = args.replaystart
    replay_speed: float = args.replayspeed

    # Create directory for logging.
    outfilepath.mkdir(parents=True, exist_ok=True)
    print(f"Logging EdgeTech responses to {outfilename}")

    edgetech_q: Queue[str, datetime] = Queue()
    if replay_file:
        obsurv.etech_replay_textfile(
            filename=replay_file,
            edgetech_q=edgetech_q,
            spd_fctr=replay_speed,
            timestamp_start=replay_start,
        )
    else:
        obsurv.etech_serial_stream(
            ser_conn=ser_param,
            edgetech_q=edgetech_q,
        )

    try:
        while True:
            sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
            sentence, timestamp = get_next_sentence(edgetech_q)
            if not sentence:
                continue
            timestamp = timestamp.strftime("%Y-%m-%dT%H-%M-%S.%f")
            with open(outfilename, "a+", newline="", encoding="utf-8") as log_file:
                log_file.write(f"{timestamp} {sentence}\n")
                print(sentence)

    except KeyboardInterrupt:
        sys.exit("*** End EdgeTech Logging ***")


def get_next_sentence(edgetech_q: Queue) -> str:
    """Return next sentence from NMEA queue."""
    if edgetech_q.empty():
        return None, None
    edgetech_str, timestamp = edgetech_q.get(block=False)
    if edgetech_str == "EOF":
        sys.exit(f"*** ETech: {edgetech_str} ***")
    return edgetech_str, timestamp


if __name__ == "__main__":
    main()
