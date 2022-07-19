from datetime import timedelta
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

import numpy as np
import numpy.typing as npt
import pandas as pd
import pint
from pint.quantity import Quantity

u = pint.UnitRegistry()
DATA_DIR = Path(__file__).parent / "data"

# Typing
iter_str = Union[str, np.ndarray]

# Constants
CARBON_INTENSITY = 357.32 * u.g / (u.kW * u.hour)
TREE_ABSORBTION = 11000 * u.g / u.year


def get_cpu_draw(
    model: npt.ArrayLike, *, n_cores: Optional[npt.ArrayLike] = None
) -> Quantity:
    """
    Get total CPU draw in watts.

    Parameters
    ----------
    model :
        CPU model name.
    n_cores:
        Number of cores being used. If `None` assumes all cores are being used.
    """
    cpu_data = pd.read_csv(DATA_DIR / "cpu.csv", header=1, index_col="model")
    cpu = cpu_data.loc[model]
    if n_cores is None:
        n_cores = cpu["n_cores"].values
    return cpu["TDP"].values * u.W * n_cores / cpu["n_cores"].values


def get_runner_info(os: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    For a given GH actions runner, return the
    - cpu model
    - number of cores
    - amount of RAM
    """
    gh_runner_data = pd.read_csv(DATA_DIR / "gh_runners.csv", index_col="os")
    return (
        gh_runner_data.loc[os]["cpu"].values,
        gh_runner_data.loc[os]["n_cores"].values,
        gh_runner_data.loc[os]["memory"].values * u.GB,
    )


def power_usage(os: str, runtime: timedelta) -> Quantity:
    runtime = runtime * u.hours / np.timedelta64(1, "h")
    model, n_cores, memory = get_runner_info(os)
    cpu_draw = get_cpu_draw(model, n_cores=n_cores)
    # Assume full useage of CPU
    usage = 1
    memory_draw = memory * 0.3725 * u.W / u.GB
    # Any extra energy use for the datacenter (e.g. cooling, lighting etc.)
    # Value from https://azure.microsoft.com/en-gb/global-infrastructure/
    power_usage_effectiveness = 1.125
    return (runtime * (cpu_draw * usage + memory_draw) * power_usage_effectiveness).to(
        u.kW * u.hour
    )


def emissions(os: str, runtime: timedelta) -> Quantity:
    """
    Get CO2 emissions for running a GH Actions job on a given OS for a given
    amount of time.
    """
    power = power_usage(os, runtime)
    return (power * CARBON_INTENSITY).to(u.g)
