"""
Initiates a thread that connects to an NMEA data stream via UDP or TCP, and 
connects to a serial data stream from an EdgeTech deckbox.
Or will simulate the same by replaying previously recorded text files. One
containing NMEA data and the other containing EdgeTech ranging responses.
It then populates the specified Queue with a dict for each range response. This
dict will contain a union of NMEA and Range data fields.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue
import re
import sys
from threading import Thread
from time import sleep

import ob_inst_survey as obsurv


OBSVN_COLS = (
    "flag",
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

STARTTIME = datetime.now()
STARTTIME = STARTTIME + timedelta(seconds=1)  # Allow time for startup.


@dataclass
class EtechParam(obsurv.SerParam):
    """
    Dataclass for specifying EdgeTech 8011M deckbox parameters.
    """

    turn_time: float = 12.5  # Delay in ms for reply from BPR transducer.
    snd_spd: int = 1500  # Speed of sound in water (typical 1450 to 1570 m/sec)


def ranging_survey_stream(
    obsvn_q: Queue[dict],
    nmea_conn: obsurv.IpParam = obsurv.IpParam(),
    etech_conn: EtechParam = EtechParam(),
    nmea_filename: Path = None,
    etech_filename: Path = None,
    replay_start: datetime = None,
    spd_fctr: float = 1,
    timestamp_offset: float = 0.0,
    rawfile_path: Path = None,
    rawfile_prefix: str = None,
):
    """
    Initiate a queue that populates with dicts of ranging obseravtions.
    Either provide parameters for both NMEA and EdgeTech deckbox data streams,
    or provide input file details for replaying streams previously recorded.

    Args:
        obsvn_q (Queue[dict]): _description_
        nmea_conn (obsurv.IpParam, optional): _description_. Defaults to None.
        etech_conn (obsurv.SerParam, optional): _description_. Defaults to None.
        nmea_filename (Path, optional): _description_. Defaults to None.
        etech_filename (Path, optional): _description_. Defaults to None.
        replay_start (datetime, optional): _description_. Defaults to None.
        spd_fctr (float, optional): _description_. Defaults to 1.
    """
    timestamp_start = STARTTIME.strftime("%Y-%m-%d_%H-%M")

    if (nmea_filename or etech_filename) and not (nmea_filename and etech_filename):
        sys.exit(
            "If you specify a replay file for either NMEA or EdgeTech "
            "deckbox responses, then you must specify both!"
        )
    if not (nmea_filename) and not (nmea_conn and etech_conn):
        sys.exit(
            "You must specify connection parameters for both NMEA and EdgeTech "
            "response data streams!"
        )

    # Create directories for logging raw NMEA and Ranging streams if specified.
    rangefile_log = None
    nmeafile_log = None
    if rawfile_path:
        rangefile_log: str = (
            rawfile_path / f"rng/{rawfile_prefix}_{timestamp_start}_RNG.txt"
        )
        rangefile_log.parents[0].mkdir(parents=True, exist_ok=True)
        nmeafile_log: str = (
            rawfile_path / f"nmea/{rawfile_prefix}_{timestamp_start}_NMEA.txt"
        )
        nmeafile_log.parents[0].mkdir(parents=True, exist_ok=True)

    Thread(
        target=_get_ranging_dict,
        args=(
            obsvn_q,
            nmea_conn,
            etech_conn,
            nmea_filename,
            etech_filename,
            replay_start,
            spd_fctr,
            timestamp_offset,
            rangefile_log,
            nmeafile_log,
        ),
        daemon=True,
    ).start()


def _get_ranging_dict(
    obsvn_q: Queue[dict],
    nmea_conn: obsurv.IpParam,
    etech_conn: EtechParam,
    nmea_filename: Path,
    etech_filename: Path,
    replay_start: datetime,
    spd_fctr: float,
    timestamp_offset: float,
    rangefile_log: Path,
    nmeafile_log: Path,
):
    """
    _summary_

    Args:
        nmea_conn (obsurv.IpParam, optional): _description_. Defaults to None.
        etech_conn (obsurv.SerParam, optional): _description_. Defaults to None.
        nmea_filename (Path, optional): _description_. Defaults to None.
        etech_filename (Path, optional): _description_. Defaults to None.
        replay_start (datetime, optional): _description_. Defaults to None.
        spd_fctr (float, optional): _description_. Defaults to 1.

    Returns:
        dict: _description_
    """

    accou = {
        "turnTime": etech_conn.turn_time,
        "sndSpd": etech_conn.snd_spd,
    }

    # If replay text files are specified then the stream will be simulated by
    # 'replaying' the files. Otherwise assume streaming over the specified UDP
    # or TCP network connection.

    # Start thread that will populate NMEA queue
    nmea_q: Queue[str] = Queue()
    if nmea_filename:
        obsurv.nmea_replay_textfile(
            nmea_filename, nmea_q, STARTTIME, replay_start, spd_fctr
        )
    else:
        obsurv.nmea_ip_stream(nmea_conn, nmea_q)

    # If we are replaying from files then we need to have the timestamp from
    # the first NMEA record before starting Edgetech file replay to provide
    # syncronisation.
    while nmea_q.empty():
        sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
    nmea_str = nmea_q.get()
    nmea_dict, nmea_next_str = _get_next_nmea_dict(nmea_q, nmea_str, nmeafile_log)

    # Start thread that will populate EdgeTech ranging queue
    edgetech_q: Queue[str] = Queue()
    if nmea_filename:
        if not replay_start:
            replay_start = datetime.strptime(nmea_dict["utcTime"], "%H:%M:%S.%f")
        obsurv.etech_replay_textfile(
            etech_filename,
            edgetech_q,
            STARTTIME,
            replay_start,
            spd_fctr,
            timestamp_offset,
        )
    else:
        obsurv.etech_serial_stream(etech_conn, edgetech_q)

    while True:
        if nmea_q.empty():
            sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
        else:
            nmea_dict, nmea_next_str = _get_next_nmea_dict(
                nmea_q, nmea_next_str, nmeafile_log
            )
            if nmea_dict:
                if nmea_dict["flag"] in ["TimeoutError", "EOF"]:
                    obsvn_q.put(nmea_dict)

        if edgetech_q.empty():
            pass
        else:
            range_dict = _get_next_edgetech_dict(edgetech_q, accou, rangefile_log)
            if range_dict:
                # Note: at end of EdgeTech stream
                #  => range_dict["flag"] in ["TimeoutError", "EOF"]:
                range_dict = {**nmea_dict, **range_dict}
                obsvn_q.put(range_dict)


def _get_next_edgetech_dict(edgetech_q: Queue, accou: dict, rangefile_log: Path):
    """Get next element from queue and process as edgetech sentence."""
    range_dict = {}
    if edgetech_q.empty():
        return range_dict
    edgetech_str, timestamp = edgetech_q.get(block=False)
    if edgetech_str in ["TimeoutError", "EOF"]:
        range_dict["flag"] = edgetech_str
        return range_dict

    if rangefile_log:
        timestamp = timestamp.strftime("%Y-%m-%dT%H-%M-%S.%f")
        with open(rangefile_log, "a+", newline="", encoding="utf-8") as rng_file:
            rng_file.write(f"{timestamp} {edgetech_str}\n")

    edgetech_item = edgetech_str.split(" ")

    if edgetech_item[0] == "RNG:":
        try:
            range_dict["flag"] = None
            range_dict["tx"] = float(edgetech_item[3])
            range_dict["rx"] = float(edgetech_item[6])
            try:
                range_dict["rangeTime"] = float(edgetech_item[9])
            except ValueError:
                # Returns '--.---' if no range received.
                range_dict["rangeTime"] = 0.0
            range_dict["turnTime"] = accou["turnTime"]
            range_dict["sndSpd"] = accou["sndSpd"]
            range_dict["range"] = (range_dict["rangeTime"] / 2) * range_dict["sndSpd"]
        except IndexError:
            print(
                f"Serial range response string was incomplete. No "
                f"range has been logged.\n"
                f"String received: {edgetech_str}"
            )
    return range_dict


def _get_next_nmea_dict(nmea_q: Queue, nmea_next_str: str, nmeafile_log: Path):
    """Get next element from queue and process as NMEA sentence."""
    gga = []  # Global Positioning System Fix Data
    # $<TalkerID>GGA,<Timestamp>,<Lat>,<N/S>,<Long>,<E/W>,<GPSQual>,
    # <Sats>,<HDOP>,<Alt>,<AltVal>,<GeoSep>,<GeoVal>,<DGPSAge>,
    # <DGPSRef>*<checksum><CR><LF>
    vtg = []  # Track made good and speed over ground
    # $<TalkerID>VTG,<COGtrue>,T,<COGmag>,M,<SOGknt>,N,<SOGkph>,K,
    # <mode-A/D/E/M/S/N>*<checksum><CR><LF>
    rmc = []  # Recommended minimum specific GPS/Transit data
    # $<TalkerID>RMC,<Timestamp>,<Status>,<Lat>,<N/S>,<Long>,<E/W>,<SOG>,
    # <COG>,<Date>,<MagVar>,<MagVarDir>,<mode>,<NavStatus>*<checksum><CR><LF>
    hdt = []  # True heading.
    # $<TalkerID>RMC,<TrueHeading>,T*<checksum><CR><LF>
    shr = []  # Inertial Attitude Data
    # $<TalkerID>SHR,<Timestamp>,<TrueHeading>,T,<Roll>,<Pitch>,<Heave>,
    # <RollAccy>,<PitchAccy>,<HeadingAccy>,<GPSQlty>,<INSStatus>*<checksum><CR><LF>

    ts_start = None
    nmea_str = nmea_next_str
    nmea_dict = {}

    while True:
        if nmea_str in ["TimeoutError", "EOF"]:
            nmea_dict["flag"] = nmea_str
            return nmea_dict, nmea_str

        if nmeafile_log:
            with open(nmeafile_log, "a+", newline="", encoding="utf-8") as nmea_file:
                nmea_file.write(f"{nmea_str}\n")

        if not obsurv.nmea_checksum(nmea_str):
            print(
                f"!!! Checksum for NMEA line is invalid. Line has "
                f"been ignored: => {nmea_str}"
            )
            continue

        nmea_msg = re.match(r"\$(.*)\*", nmea_str)[1].split(",")
        msg_type = nmea_msg[0][2:]
        if msg_type in ("GGA", "RMC", "VTG", "SHR"):
            ts_msg = nmea_msg[1][:8]
            if ts_start is None:
                ts_start = ts_msg
            if ts_msg != ts_start:
                if gga or rmc:
                    nmea_dict = _nmea_to_dict(gga, rmc, shr, vtg, hdt)
                    nmea_dict["flag"] = None
                    return (nmea_dict, nmea_str)
                gga = rmc = shr = vtg = hdt = []
                ts_start = ts_msg

        if msg_type == "GGA":
            gga = nmea_msg
        elif msg_type == "RMC":
            rmc = nmea_msg
        elif msg_type == "VTG":
            vtg = nmea_msg
        elif msg_type == "SHR":
            shr = nmea_msg
        elif msg_type == "HDT":
            hdt = nmea_msg

        if nmea_q.empty():
            sleep(0.000001)  # Prevents idle loop from 100% CPU thread usage.
            pass
        else:
            nmea_str = nmea_q.get(block=False)


def _nmea_to_dict(nmea_gga, nmea_rmc, nmea_shr, nmea_vtg, nmea_hdt):
    try:
        nmea_dict = {}

        if nmea_gga:
            time = nmea_gga[1]
            lat = nmea_gga[2]
            lat_hemi = nmea_gga[3]
            lon = nmea_gga[4]
            lon_hemi = nmea_gga[5]
        else:
            time = nmea_rmc[1]
            lat = nmea_rmc[3]
            lat_hemi = nmea_rmc[4]
            lon = nmea_rmc[5]
            lon_hemi = nmea_rmc[6]

        nmea_dict["utcTime"] = f"{time[0:2]}:{time[2:4]}:{time[4:]}"

        nmea_dict["lat"] = f"{lat[0:2]}\u00b0{lat[2:11]}'{lat_hemi}"
        nmea_dict["latDec"] = int(lat[0:2]) + float(lat[2:11]) / 60
        if lat_hemi.upper() == "S":
            nmea_dict["latDec"] *= -1

        nmea_dict["lon"] = f"{lon[0:3]}\u00b0{lon[3:12]}'{lon_hemi}"
        nmea_dict["lonDec"] = int(lon[0:3]) + float(lon[3:12]) / 60
        if lon_hemi.upper() == "W":
            nmea_dict["lonDec"] *= -1
    except (IndexError, ValueError):
        print("NMEA stream is not present or is invalid.")

    if nmea_gga:
        try:
            nmea_dict["qlty"] = _fix_qlty(int(nmea_gga[6]))
        except ValueError:
            nmea_dict["qlty"] = ""
        try:
            nmea_dict["noSats"] = int(nmea_gga[7])
        except ValueError:
            nmea_dict["noSats"] = ""
        try:
            nmea_dict["hdop"] = float(nmea_gga[8])
        except ValueError:
            nmea_dict["hdop"] = ""
        try:
            nmea_dict["htAmsl"] = float(nmea_gga[9])
        except ValueError:
            nmea_dict["htAmsl"] = ""
        nmea_dict["htAmslUnit"] = nmea_gga[10].upper()
        try:
            nmea_dict["geiodSep"] = float(nmea_gga[11])
        except ValueError:
            nmea_dict["geiodSep"] = ""
        nmea_dict["geiodSepUnit"] = nmea_gga[12].upper()
    else:
        nmea_dict["qlty"] = ""
        nmea_dict["noSats"] = ""
        nmea_dict["hdop"] = ""
        nmea_dict["htAmsl"] = ""
        nmea_dict["htAmslUnit"] = ""
        nmea_dict["geiodSep"] = ""
        nmea_dict["geiodSepUnit"] = ""

    if nmea_vtg:
        nmea_dict["cog"] = float(nmea_vtg[1])
        nmea_dict["sogKt"] = float(nmea_vtg[5])
    elif nmea_rmc:
        nmea_dict["cog"] = float(nmea_rmc[8])
        nmea_dict["sogKt"] = float(nmea_rmc[7])
    else:
        nmea_dict["cog"] = ""
        nmea_dict["sogKt"] = ""

    if nmea_shr:
        nmea_dict["heading"] = float(nmea_shr[2])
        nmea_dict["roll"] = float(nmea_shr[4])
        nmea_dict["pitch"] = float(nmea_shr[5])
        nmea_dict["heave"] = float(nmea_shr[6])
    else:
        if nmea_hdt:
            nmea_dict["heading"] = float(nmea_hdt[1])
        else:
            nmea_dict["heading"] = ""

        nmea_dict["roll"] = ""
        nmea_dict["pitch"] = ""
        nmea_dict["heave"] = ""

    return nmea_dict


def _fix_qlty(idx):
    return [
        "Invalid",
        "GPS fix - (Standard Positioning Service)",
        "DGPS fix",
        "PPS fix",
        "Real Time Kinematic",
        "Float RTK",
        "Estimated (dead reckoning)",
        "Manual input mode",
        "Simulation mode",
    ][idx]
