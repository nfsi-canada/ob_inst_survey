"""Process NMEA & Ranging data streams to determin ascent and/or descent rates."""

import re
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from time import sleep

import numpy as np
import pandas as pd
from pyproj import Transformer
from pyproj.crs import ProjectedCRS
from pyproj.crs.coordinate_operation import TransverseMercatorConversion

import ob_inst_survey as obsurv

STARTTIME = datetime.now(timezone.utc)
DFLT_PREFIX = "ASCENT-DESCENT"
DFLT_PATH = Path.cwd() / "results/"
ACCOU_TURNTIME = 12.5  # millisec
ACCOU_SPD = 1500  # m/sec


def main():
    """Initialise NMEA and EdgeTech data streams and log to CSV text file."""
    # Default CLI arguments.
    ip_param = obsurv.IpParam()
    etech_param = obsurv.EtechParam()

    # Retrieve CLI arguments.
    helpdesc: str = (
        "Receives an NMEA data stream via UDP or TCP, and a serial data stream "
        "from an EdgeTech deckbox. As each new observation is receievd the ascent "
        "or descent rate will be calculated along with an estimated ETA to surface "
        "or bottom.\n"
        "Alternatively these streams can be simulated "
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
        apriori_coord = pd.Series(dtype=float)
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
        with open(replay_rngfile, encoding="utf-8") as etech_file:
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
                timestamp = timestamp + timedelta(seconds=timestamp_offset)
                timestamp_start = timestamp.strftime("%Y-%m-%d_%H-%M")
                break
            except AttributeError:
                # If no valid timestamp continue with next response line.
                pass

    outfile_path: Path = args.outfilepath
    outfile_name: str = f"{args.outfileprefix}_{timestamp_start}"
    obsfile_name: str = f"{outfile_name}_OBSVNS"
    obsfile_log: str = outfile_path / f"{obsfile_name}.csv"
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

    display_cols = (
        f'{"utcTime":^12s}',
        f'{"range":^8s}',
        f'{"horzntl":^8s}',
        f'{"depth":^8s}',
        f'{"rate":^8s}',
        f'{"eta_min":^6s}',
        f'{"eta_time":^8s}',
        f'{"towards":^8s}',
        f'{"lat":^14s}',
        f'{"lon":^14s}',
        f'{"cog":^6s}',
        f'{"sogKt":^5s}',
        f'{"heading":^6s}',
    )
    print(", ".join(display_cols))

    obsvn_df = pd.DataFrame(dtype=object)
    prev_record = {}
    # Main survey loop.
    try:
        while True:
            if obsvn_q.empty():
                sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
                continue
            curr_record = dict(obsvn_q.get())
            if curr_record["flag"] in ["TimeoutError", "EOF"]:
                print(f"*** Survey Ended: {curr_record['flag']} ***")
                break

            # If range is less than 50m or more than 1.6x water depth then flag.
            if curr_record["range"] < 50 or curr_record["range"] > (
                -apriori_coord["htAmsl"] * 1.6
            ):
                bad_range = True
            else:
                bad_range = False

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

            curr_record["mE"], curr_record["mN"] = trans_geod_to_tm.transform(
                xx=curr_record["lonDec"], yy=curr_record["latDec"]
            )

            apriori_coord["mE"], apriori_coord["mN"] = trans_geod_to_tm.transform(
                xx=apriori_coord["lonDec"], yy=apriori_coord["latDec"]
            )

            curr_record["dist"], curr_record["bearing"] = rect2pol(
                curr_record["mN"] - apriori_coord["mN"],
                curr_record["mE"] - apriori_coord["mE"],
            )

            if not bad_range:
                curr_record["depth"] = vert_depth(
                    curr_record["range"],
                    curr_record["dist"],
                )
            else:
                curr_record["depth"] = 0

            if prev_record and not bad_range:
                timestamp = re.sub(r"[Tt :_-]", r"_", curr_record["utcTime"])
                curr_time = datetime.strptime(timestamp, r"%H_%M_%S.%f")
                timestamp = re.sub(r"[Tt :_-]", r"_", prev_record["utcTime"])
                prev_time = datetime.strptime(timestamp, r"%H_%M_%S.%f")
                time_diff = curr_time - prev_time
                if time_diff.seconds < 0:
                    time_diff = time_diff + timedelta(hours=24)
                if curr_record["depth"] == 0:
                    depth_diff = 0
                else:
                    depth_diff = curr_record["depth"] - prev_record["depth"]
                curr_record["rate_mpsec"] = depth_diff / time_diff.total_seconds()
                curr_record["rate_mpmin"] = curr_record["rate_mpsec"] * 60
                if curr_record["rate_mpsec"] > 0:
                    direction = "bottom"
                    depth_remain = -apriori_coord["htAmsl"] - curr_record["depth"]
                    eta_secs = depth_remain / curr_record["rate_mpsec"]
                elif curr_record["rate_mpsec"] < 0:
                    direction = "surface"
                    eta_secs = curr_record["depth"] / -curr_record["rate_mpsec"]
                else:
                    direction = "invalid"
                    eta_secs = 0
                eta_time = curr_time + timedelta(seconds=eta_secs)
                curr_record["eta_time"] = eta_time.strftime("%H:%M:%S")
                eta_mins = f"{eta_secs / 60:6.2f}"
                curr_record["eta_mins"] = eta_secs / 60
            else:
                curr_record["rate_mpsec"] = 0
                curr_record["rate_mpmin"] = 0
                curr_record["eta_mins"] = 0
                curr_record["eta_time"] = ""
                eta_mins = ""
                direction = ""

            if not bad_range:
                prev_record = curr_record

            curr_obsvn = pd.DataFrame.from_dict([curr_record])
            curr_obsvn = curr_obsvn.dropna()
            if not obsvn_df.empty:
                obsvn_df = pd.concat(
                    [obsvn_df, curr_obsvn],
                    axis="rows",
                    ignore_index=True,
                )
            else:
                obsvn_df = curr_obsvn
            obsvn_df.to_csv(obsfile_log, index=False)

            # Display summary values to screen
            display_vals = []
            display_vals.append(f'{curr_record["utcTime"]:<12s}')
            display_vals.append(f'{curr_record["range"]:8.2f}')
            display_vals.append(f'{curr_record["dist"]:8.2f}')
            if curr_record["depth"]:
                display_vals.append(f'{curr_record["depth"]:8.2f}')
            else:
                display_vals.append(f'{"":8s}')
            if curr_record["rate_mpsec"]:
                display_vals.append(f'{curr_record["rate_mpsec"]*60:8.2f}')
            else:
                display_vals.append(f'{"":>8s}')
            display_vals.append(f"{eta_mins:>7s}")
            display_vals.append(f'{curr_record["eta_time"]:>8s}')
            display_vals.append(f"{direction:>8s}")
            display_vals.append(f'{curr_record["lat"]:>14s}')
            display_vals.append(f'{curr_record["lon"]:>14s}')
            try:
                display_vals.append(f'{curr_record["cog"]:06.2f}')
                display_vals.append(f'{curr_record["sogKt"]:5.1f}')
            except ValueError:
                display_vals.extend([" " * 6, " " * 5])
            try:
                display_vals.append(f'{curr_record["heading"]:06.2f}')
            except ValueError:
                display_vals.append(" " * 6)
            print(", ".join(display_vals))

            if bad_range:
                print(
                    f"{curr_record['range']} m appears to be an invalid "
                    f"range, try again."
                )

    except KeyboardInterrupt:
        print("*** Ranging survey ended. ***")


def rect2pol(x_coord, y_coord):
    """Convert rectangular to polar coordinates."""
    distance = np.sqrt(x_coord**2 + y_coord**2)
    bearing = np.degrees(np.arctan2(y_coord, x_coord))
    if bearing < 0:
        bearing += 360
    return (distance, bearing)


def vert_depth(slant_range, horz):
    """Compute vertical depth from given slant range and horizontal distance."""
    if slant_range < horz:
        print(
            "Slant range is less than horizontal distance to initial coordinate. "
            "Either the initial coordinate is incorrect or the instrument is "
            "drifting towards the vessel."
        )
        return 0
    return (slant_range**2 - horz**2) ** 0.5


if __name__ == "__main__":
    main()
