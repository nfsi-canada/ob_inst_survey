"""
Log NMEA & Ranging data streams to a combined CSV text file.
"""
from argparse import ArgumentParser
import csv
from datetime import datetime
from pathlib import Path
from queue import Queue
import sys
from time import sleep

import ob_inst_survey as obsurv


OBSVN_COLS = (
    "utcTime",
    "rangeTime",
    "range",
    "lat",
    "latDec",
    "lon",
    "lonDec",
    "qlty",
    "noSats",
    "hdop",
    "htAmsl",
    "htAmslUnit",
    "geiodSep",
    "geiodSepUnit",
    "cog",
    "sogKt",
    "heading",
    "roll",
    "pitch",
    "heave",
    "turnTime",
    "sndSpd",
    "tx",
    "rx",
)

DISPLAY_COLS = (
    "utcTime",
    "rangeTime",
    "range",
    "lat",
    "lon",
    "cog",
    "sogKt",
    "heading",
)

STARTTIME = datetime.now()
TIMESTAMP_START = STARTTIME.strftime("%Y-%m-%d_%H-%M")
DFLT_PREFIX = "RANGELOG"
DFLT_PATH = Path.home() / "logs/"
ACCOU_TURNTIME = 12.5  # millisec
ACCOU_SPD = 1500  # m/sec


def main():
    """
    Initialise NMEA and EdgeTech data streams and log to CSV text file.
    """
    # Default CLI arguments.
    ip_param = obsurv.IpParam()
    etech_param = obsurv.EtechParam()

    # Retrieve CLI arguments.
    helpdesc: str = (
        "Receives an NMEA data stream via UDP or TCP, and a serial data stream "
        "from an EdgeTech deckbox. Alternatively these streams can be simulated "
        "by replaying previously recorded text files (one containing NMEA data "
        "and the other containing EdgeTech ranging responses).\n"
        "For every range response received a record will be logged to a text "
        "file, containing all relevant NMEA and Ranging fields."
    )
    parser = ArgumentParser(
        parents=[
            obsurv.out_filepath_parser(DFLT_PATH),
            obsurv.out_fileprefix_parser(DFLT_PREFIX),
            obsurv.ip_arg_parser(ip_param),
            obsurv.edgetech_arg_parser(etech_param),
            obsurv.replay2files_parser(None),
        ],
        description=helpdesc,
    )
    args = parser.parse_args()
    outfilepath: Path = args.outfilepath
    outfile_log: str = outfilepath / f"{args.outfileprefix}_{TIMESTAMP_START}.csv"
    ip_param = obsurv.IpParam(
        port=args.ipport,
        addr=args.ipaddr,
        prot=args.ipprot,
        buffer=args.ipbuffer,
    )
    etech_param = obsurv.EtechParam(
        port=args.serport,
        baud=args.serbaud,
        stop=args.serstop,
        parity=args.serparity,
        bytesize=args.serbytesize,
        turn_time=args.acouturn,
        snd_spd=args.acouspd,
    )
    replay_nmeafile: Path = args.replaynmea
    replay_rngfile: Path = args.replayrange
    replay_start: datetime = args.replaystart
    replay_speed: float = args.replayspeed

    # Create directories for logging (included raw NMEA and Ranging streams).
    outfilepath.mkdir(parents=True, exist_ok=True)
    print(f"Logging survey observations to {outfile_log}")

    # Initiate NMEA and Ranging data streams to the observation queue.
    obsvn_q: Queue[dict] = Queue()
    obsurv.ranging_survey_stream(
        obsvn_q=obsvn_q,
        nmea_conn=ip_param,
        etech_conn=etech_param,
        nmea_filename=replay_nmeafile,
        etech_filename=replay_rngfile,
        timestamp_start=replay_start,
        spd_fctr=replay_speed,
    )

    print(",".join(DISPLAY_COLS))
    with open(outfile_log, "a+", newline="", encoding="utf-8") as csvfile:
        logwriter = csv.DictWriter(csvfile, delimiter=",", fieldnames=OBSVN_COLS)
        logwriter.writeheader()
    try:
        while True:
            if obsvn_q.empty():
                sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                continue
            result_dict = obsvn_q.get()
            if result_dict["flag"] in ["TimeoutError", "EOF"]:
                sys.exit(f"*** Survey Ended: {result_dict['flag']} ***")

            # Display summary values to screen
            display_vals = [result_dict[key] for key in DISPLAY_COLS]
            # values = []
            # for key in DISPLAY_COLS:
            #     values.append(result_dict[key])
            print(str(display_vals).strip("[]"))

            # Save values to log file

            save_dict = {key: result_dict[key] for key in OBSVN_COLS}
            with open(outfile_log, "a+", newline="", encoding="utf-8") as csvfile:
                logwriter = csv.DictWriter(
                    csvfile, delimiter=",", fieldnames=OBSVN_COLS
                )
                logwriter.writerow(save_dict)

    except KeyboardInterrupt:
        sys.exit("*** End Ranging Survey ***")


if __name__ == "__main__":
    main()
