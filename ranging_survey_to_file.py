from pathlib import Path
from queue import Queue
import sys
from time import sleep

import ob_inst_survey as obsurv


def main():
    """Main function for testing"""
    obsvn_q = Queue()
    path_root = Path.home() / "scripts/ob_inst_survey/data/logs_TAN2301/"
    nmea_file = path_root / "nmea/POSMV_2023-01-06_12-23.txt"
    etech_file = path_root / "raw/raw_edgetech_2023-01-06_12-23.txt"
    obsurv.ranging_survey_stream(
        obsvn_q=obsvn_q,
        nmea_filename=nmea_file,
        etech_filename=etech_file,
        spd_fctr=100,
    )
    try:
        while True:
            if obsvn_q.empty():
                sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                continue
            result_dict = obsvn_q.get()
            if result_dict["flag"] in ["TimeoutError", "EOF"]:
                sys.exit(f"*** Survey Ended: {result_dict['flag']} ***")
            print(result_dict)
    except KeyboardInterrupt:
        sys.exit("*** End Ranging Survey ***")


if __name__ == "__main__":
    main()
