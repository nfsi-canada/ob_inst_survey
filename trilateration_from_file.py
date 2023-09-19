"""Trilateration survey of ocean bottom instrument from ship positions and ranges."""
import logging
import sys

import pandas as pd
import numpy as np

import ob_inst_survey as obsurv


def main():
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s:\n%(message)s", datefmt="%Y-%m-%d - %H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARN)
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    obsvn_file = (
        "/home/nev/scripts/ob_inst_survey/data/logs_TAN2212/"
        # "bpr_rangelog_2022-10-12_19-26_LDE22-AG_survey.csv"
        # "bpr_rangelog_2022-10-13_14-21_GNS22-PJ_survey.csv"
        # "bpr_rangelog_2022-10-11_17-30_GNS22-PP_survey.csv"
        # "bpr_rangelog_2022-10-17_21-51_LDE22-AE_survey.csv"
        "bpr_rangelog_2022-10-11_22-45_GNS22-PO_survey.csv"
        # "bpr_rangelog_2022-10-12_14-47_GNS22-PK_survey.csv"
    )

    all_obs_df = load_survey_data(obsvn_file)

    apriori_coord = None
    final_coord, all_obs_df = obsurv.trilateration(all_obs_df, apriori_coord)

    # Log details to console
    log.info("Observations used in determining surveyed coord:\n%s", all_obs_df)
    log.info("Final coordinate Series:\n%s", final_coord)

    fig = obsurv.init_plot_trilateration()
    obsurv.plot_trilateration(
        fig=fig, final_coord=final_coord, observations=all_obs_df, title=f"{obsvn_file}"
    )

    input("Press <Enter> to close plot.")


def load_survey_data(filename):
    data_file = filename
    try:
        input_df = pd.read_csv(data_file)
    except FileNotFoundError:
        sys.exit(f"File '{data_file}' does not exist!")

    # Ensure decimal latutiude and longitude values have correct sign.
    try:
        input_df["latDec"] = np.where(
            input_df["lat"].str[-1].isin(("S", "s")),
            -1 * input_df["latDec"].abs(),
            input_df["latDec"].abs(),
        )
    except KeyError:
        input_df["latDec"] = -1 * input_df["latDec"].abs()

    try:
        input_df["lonDec"] = np.where(
            input_df["lon"].str[-1].isin(("W", "w")),
            -1 * input_df["lonDec"].abs(),
            input_df["lonDec"].abs(),
        )
    except KeyError:
        pass

    return input_df


if __name__ == "__main__":
    main()
