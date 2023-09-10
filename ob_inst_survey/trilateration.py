import logging
import sys

import pandas as pd
from pyproj import Transformer
from scipy.optimize import least_squares


def trilateration(
    obsvns: pd.DataFrame,
    apriori_coord: tuple[float, float, float] = None,
) -> (pd.Series, pd.DataFrame):
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s:\n%(message)s", datefmt="%Y-%m-%d - %H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    if len(obsvns.index) < 3:
        print(
            "A minimum of three range observations are required to "
            "compute a surveyed location."
        )
        return (pd.DataFrame(), obsvns)

    # Define transformations
    trans_geoctrc_to_geod = Transformer.from_crs(
        "EPSG:4978", "EPSG:4979", always_xy=True
    )
    trans_geod_to_geoctrc = Transformer.from_crs(
        "EPSG:4979", "EPSG:4978", always_xy=True
    )

    obsvns["X"], obsvns["Y"], obsvns["Z"] = trans_geod_to_geoctrc.transform(
        obsvns["lonDec"], obsvns["latDec"], obsvns["htAmsl"]
    )

    mean_crd = obsvns[["X", "Y", "Z"]].mean()
    if not apriori_coord:
        # Assume apriori is the mean observation of all coordinates and is 1000m
        # below observation locations (towards earth ctr).
        earth_ctr_dist = distance_3d((0, 0, 0), mean_crd)
        apriori_coord = mean_crd * ((earth_ctr_dist - 1000) / earth_ctr_dist)

    # Subtract mean coordinate value from all coordinates to minimuse floating
    # point calculation errors.
    obsvns[["X", "Y", "Z"]] = obsvns[["X", "Y", "Z"]] - mean_crd
    apriori_coord = apriori_coord - mean_crd
    # log.info("Apriori coordinate:\n%s", apriori_coord)
    obsvns["outlier"] = False
    obsvns.loc[obsvns["range"] < 50, "outlier"] = True
    obsvns["residual"] = None
    while True:
        # Extract datframes for computation. Exclude any observations marked
        # as outliers.
        used_obs_df = obsvns.loc[~obsvns["outlier"]]
        excl_obs_df = obsvns.loc[obsvns["outlier"]]

        if len(used_obs_df.index) < 3:
            print(
                "A minimum of three valid range observations are required to "
                "compute a surveyed location."
            )
            return (pd.DataFrame(), obsvns)
        result = least_squares(
            rms_err,
            x0=apriori_coord,
            args=(used_obs_df[["X", "Y", "Z"]], used_obs_df["range"]),
        )
        log.debug(result)
        obsvns["residual"] = (
            distance_3d(result.x, obsvns[["X", "Y", "Z"]]) - obsvns["range"]
        )

        # Update residuals of observations included in computation.
        used_obs_df.loc[:, "residual"] = obsvns.loc[~obsvns["outlier"], "residual"]
        excl_obs_df.loc[:, "residual"] = obsvns.loc[obsvns["outlier"], "residual"]
        std_error = std_devn(used_obs_df["residual"])

        # Exclude all observations for next itteration where
        # residuals of ranges are > 3 std deviations.
        obsvns.loc[obsvns["residual"].abs() >= std_error * 3, "outlier"] = True

        # If any new outliers were identified in current itteration then repeat.
        if not (used_obs_df["residual"].abs() >= std_error * 3).any():
            break

        # used_obs_df = obsvns.loc[~obsvns["outlier"]]
        # excl_obs_df = obsvns.loc[obsvns["outlier"]]
        apriori_coord = result.x

    obsvns[["X", "Y", "Z"]] = obsvns[["X", "Y", "Z"]] + mean_crd
    final_crd = result.x + mean_crd
    final_crd["stdErr"] = std_error

    (
        final_crd["lonDec"],
        final_crd["latDec"],
        final_crd["htAmsl"],
    ) = trans_geoctrc_to_geod.transform(xx=final_crd.X, yy=final_crd.Y, zz=final_crd.Z)

    return (final_crd, obsvns)


def distance_3d(crd1, crd2):
    """
    Calculate a 3D distance where one parameter is a Pandas DF that contains
    columns ["X", "Y", "Z"], and the other conatins values (X, Y, Z)
    """
    crd_diff = crd2 - crd1
    return (crd_diff["X"] ** 2 + crd_diff["Y"] ** 2 + crd_diff["Z"] ** 2) ** 0.5


def rms_err(coord, locn_df, range_df):
    """
    Root Mean Square Error
    apriori coord: (X, Y, Z)
    locn_df: [["X", "Y", "Z"]]
    range_df: ["range"]
    """
    residuals = distance_3d(coord, locn_df) - range_df
    return std_devn(residuals)


def std_devn(residuals: pd.Series):
    """Compute standard deviation from a Pandas Series of residuals."""
    sum_of_sqs = ((residuals) ** 2).sum()
    return (sum_of_sqs / (len(residuals.index) - 2)) ** 0.5
