"""
Log NMEA & Ranging data streams to a combined CSV text file.
"""
from argparse import ArgumentParser
import csv
from datetime import datetime
from pathlib import Path
from queue import Queue
from time import sleep

import pandas as pd

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
    parser.add_argument(
        "--lograw",
        help=(
            "Option to additionally log raw NMEA and Range data to files in "
            "subdirectories of the provided <outfile_path>."
        ),
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    outfile_path: Path = args.outfilepath
    outfile_name: str = f"{args.outfileprefix}_{TIMESTAMP_START}"
    outfile_log: str = outfile_path / f"{outfile_name}.csv"
    rawfile_path = None
    if args.lograw:
        rawfile_path = outfile_path
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
    outfile_path.mkdir(parents=True, exist_ok=True)
    print(f"Logging survey observations to {outfile_log}")

    # Initiate NMEA and Ranging data streams to the observation queue.
    obsvn_q: Queue[dict] = Queue()
    obsurv.ranging_survey_stream(
        obsvn_q=obsvn_q,
        nmea_conn=ip_param,
        etech_conn=etech_param,
        nmea_filename=replay_nmeafile,
        etech_filename=replay_rngfile,
        replay_start=replay_start,
        spd_fctr=replay_speed,
        rawfile_path=rawfile_path,
        rawfile_prefix=args.outfileprefix,
    )

    fig = obsurv.init_plot_trilateration(title="Trilateration")

    print(",".join(DISPLAY_COLS))
    obsvn_df = pd.DataFrame()
    with open(outfile_log, "a+", newline="", encoding="utf-8") as csvfile:
        logwriter = csv.DictWriter(csvfile, delimiter=",", fieldnames=OBSVN_COLS)
        logwriter.writeheader()

    # Main survey loop.
    try:
        while True:
            if obsvn_q.empty():
                sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
                continue
            result_dict = obsvn_q.get()
            if result_dict["flag"] in ["TimeoutError", "EOF"]:
                print(f"*** Survey Ended: {result_dict['flag']} ***")
                input("Press <Enter> to close plot.")
                break

            # Display summary values to screen
            display_vals = []
            display_vals.append(result_dict["utcTime"])
            display_vals.append(f'{result_dict["rangeTime"]:6.3f}')
            display_vals.append(f'{result_dict["range"]:8.2f}')
            display_vals.append(result_dict["lat"])
            display_vals.append(result_dict["lon"])
            try:
                display_vals.append(f'{result_dict["cog"]:06.2f}')
                display_vals.append(f'{result_dict["sogKt"]:4.1f}')
            except TypeError:
                display_vals.extend([" " * 6, " " * 4])
            display_vals.append(f'{result_dict["heading"]:06.2f}')
            print(", ".join(display_vals))

            # display_vals = [result_dict[key] for key in DISPLAY_COLS]
            # print(str(display_vals).strip("[]"))

            # Save values to log file
            save_dict = {key: result_dict[key] for key in OBSVN_COLS}
            with open(outfile_log, "a+", newline="", encoding="utf-8") as csvfile:
                logwriter = csv.DictWriter(
                    csvfile, delimiter=",", fieldnames=OBSVN_COLS
                )
                logwriter.writerow(save_dict)

            next_record = pd.DataFrame.from_dict([result_dict])
            obsvn_df = pd.concat(
                [obsvn_df, next_record],
                axis="rows",
                ignore_index=True,
            )
            apriori_coord = None
            final_coord, all_obs_df = obsurv.trilateration(obsvn_df, apriori_coord)

            if not final_coord.empty:
                obsurv.plot_trilateration(
                    fig=fig,
                    final_coord=final_coord,
                    observations=all_obs_df,
                    plotfile_path=outfile_path,
                    plotfile_name=outfile_name,
                )
    except KeyboardInterrupt:
        print("*** Ranging survey ended. ***")


if __name__ == "__main__":
    main()
