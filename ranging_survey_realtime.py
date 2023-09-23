"""
Log NMEA & Ranging data streams to a combined CSV text file.
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
import re
from time import sleep

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer
from pyproj.crs import ProjectedCRS
from pyproj.crs.coordinate_operation import TransverseMercatorConversion

import ob_inst_survey as obsurv


TIMEZONE = +13
STARTTIME = datetime.now() - timedelta(hours=TIMEZONE)
DFLT_PREFIX = "RANGINGSURVEY"
DFLT_PATH = Path.cwd() / "results/"
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
        "from an EdgeTech deckbox. As each new observation is receievd the surveyed "
        "coordinate will be recalculated by trilateration and a plot will be updated "
        "to both screen and file. Alternatively these streams can be simulated "
        "by replaying previously recorded text files (one containing NMEA data "
        "and the other containing EdgeTech ranging responses).\n"
        "For every range response received a record will be logged to a text "
        "file, containing all relevant NMEA and Ranging fields."
    )
    parser = ArgumentParser(
        parents=[
            obsurv.out_filepath_parser(DFLT_PATH),
            obsurv.out_fileprefix_parser(DFLT_PREFIX),
            obsurv.lograw_parser(),
            obsurv.ip_arg_parser(ip_param),
            obsurv.edgetech_arg_parser(etech_param),
            obsurv.replay2files_parser(None),
            obsurv.apriori_coord_parser(),
        ],
        description=helpdesc,
    )
    args = parser.parse_args()
    if args.startcoord:
        apriori_coord = pd.Series(args.startcoord, ("lonDec", "latDec", "htAmsl"))
        apriori_coord["htAmsl"] = -apriori_coord["htAmsl"]
    else:
        apriori_coord = pd.Series()
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
    timestamp_offset: float = args.timestampoffset

    if not (replay_rngfile and replay_nmeafile):
        timestamp_start = STARTTIME.strftime("%Y-%m-%d_%H-%M")
    else:
        with open(replay_rngfile, mode="r", encoding="utf-8") as etech_file:
            etech_lines = etech_file.readlines()
        for sentence in etech_lines:
            try:
                # Attempt to extract the timestamp from the beginning of first
                # senetence of the file replay.
                timestamp_pattern = (
                    r"^\d{4}[:_-]\d{2}[:_-]\d{2}[Tt :_-]"
                    r"\d{2}[:_-]\d{2}[:_-]\d{2}\.\d{0,6}"
                )
                timestamp = re.search(timestamp_pattern, sentence).group()
                timestamp = re.sub(r"[Tt :_-]", r"_", timestamp)
                timestamp = datetime.strptime(timestamp, r"%Y_%m_%d_%H_%M_%S.%f")
                timestamp = (
                    timestamp
                    - timedelta(hours=TIMEZONE)
                    + timedelta(seconds=timestamp_offset)
                )
                timestamp_start = timestamp.strftime("%Y-%m-%d_%H-%M")
                break
            except AttributeError:
                # If no valid timestamp continue with next response line.
                pass

    outfile_path: Path = args.outfilepath
    outfile_name: str = f"{args.outfileprefix}_{timestamp_start}"
    obsfile_name: str = f"{outfile_name}_OBSVNS"
    obsfile_log: str = outfile_path / f"{obsfile_name}.csv"
    rsltfile_name: str = f"{outfile_name}_RESULT"
    rsltfile_log: str = outfile_path / f"{rsltfile_name}.csv"
    if args.lograw:
        rawfile_path = outfile_path
    else:
        rawfile_path = None

    # Create directories for logging (included raw NMEA and Ranging streams).
    outfile_path.mkdir(parents=True, exist_ok=True)
    print(f"Logging survey observations to {obsfile_log}")

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
        timestamp_offset=timestamp_offset,
        rawfile_path=rawfile_path,
        rawfile_prefix=args.outfileprefix,
    )

    figure_displayed = False

    display_cols = (
        f'{"utcTime":^12s}',
        f'{"rngTime":^7s}',
        f'{"range":^8s}',
        f'{"lat":^14s}',
        f'{"lon":^14s}',
        f'{"cog":^6s}',
        f'{"sogKt":^5s}',
        f'{"heading":^6s}',
    )
    print(", ".join(display_cols))

    obsvn_df = pd.DataFrame()

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
            display_vals.append(f'{result_dict["utcTime"]:<12s}')
            display_vals.append(f'{result_dict["rangeTime"]:7.3f}')
            display_vals.append(f'{result_dict["range"]:8.2f}')
            display_vals.append(f'{result_dict["lat"]:>14s}')
            display_vals.append(f'{result_dict["lon"]:>14s}')
            try:
                display_vals.append(f'{result_dict["cog"]:06.2f}')
                display_vals.append(f'{result_dict["sogKt"]:5.1f}')
            except TypeError:
                display_vals.extend([" " * 6, " " * 5])
            try:
                display_vals.append(f'{result_dict["heading"]:06.2f}')
            except TypeError:
                display_vals.append(" " * 6)
            print(", ".join(display_vals))

            next_record = pd.DataFrame.from_dict([result_dict])
            obsvn_df = pd.concat(
                [obsvn_df, next_record],
                axis="rows",
                ignore_index=True,
            )
            final_coord, apriori_returned, all_obs_df = obsurv.trilateration(
                obsvn_df, apriori_coord
            )
            if apriori_coord.empty:
                apriori_coord = apriori_returned

            # Plot the result figure and update it any time a result coordinate
            # is available.
            if not final_coord.empty:
                if not figure_displayed:
                    plt.ion()
                    fig = obsurv.init_plot_trilateration()
                    figure_displayed = True

                # Transform to Transverse Mercator
                local_tm = TransverseMercatorConversion(
                    latitude_natural_origin=apriori_coord["latDec"],
                    longitude_natural_origin=apriori_coord["lonDec"],
                    false_easting=0.0,
                    false_northing=0.0,
                    scale_factor_natural_origin=1.0,
                )

                proj_local_tm = ProjectedCRS(
                    conversion=local_tm,
                    geodetic_crs="EPSG:4979",
                )
                trans_geod_to_tm = Transformer.from_crs(
                    "EPSG:4979", proj_local_tm, always_xy=True
                )

                (
                    all_obs_df["mE"],
                    all_obs_df["mN"],
                ) = trans_geod_to_tm.transform(
                    xx=all_obs_df.lonDec, yy=all_obs_df.latDec
                )

                (
                    final_coord["mE"],
                    final_coord["mN"],
                ) = trans_geod_to_tm.transform(
                    xx=final_coord.lonDec, yy=final_coord.latDec
                )

                (
                    apriori_coord["mE"],
                    apriori_coord["mN"],
                ) = trans_geod_to_tm.transform(
                    xx=apriori_coord.lonDec, yy=apriori_coord.latDec
                )

                final_coord["aprLon"] = apriori_coord["lonDec"]
                final_coord["aprLat"] = apriori_coord["latDec"]
                final_coord["aprHt"] = apriori_coord["htAmsl"]
                final_coord["driftDist"], final_coord["driftBrg"] = rect2pol(
                    final_coord["mN"] - apriori_coord["mN"],
                    final_coord["mE"] - apriori_coord["mE"],
                )
                final_coord.to_frame().T.to_csv(rsltfile_log, index=False)
                obsurv.plot_trilateration(
                    fig=fig,
                    apriori_coord=apriori_returned,
                    final_coord=final_coord,
                    observations=all_obs_df,
                    plotfile_path=outfile_path,
                    plotfile_name=outfile_name,
                    title=f"{args.outfileprefix} {timestamp_start}",
                )

            all_obs_df.to_csv(obsfile_log, index=False)

    except KeyboardInterrupt:
        print("*** Ranging survey ended. ***")


def rect2pol(x, y):
    distance = np.sqrt(x**2 + y**2)
    bearing = np.degrees(np.arctan2(y, x))
    if bearing < 0:
        bearing += 360
    return (distance, bearing)


if __name__ == "__main__":
    main()
