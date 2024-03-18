"""
sunpy CI jobs
=============
"""

import os
from datetime import date

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pint

from ci_impact.emissions import emissions
from ci_impact.gh import GhApi, load_cached_job_info

u = pint.UnitRegistry()

org = "matplotlib"
repo = "matplotlib"

##################################################
# Load data
scrape_api = False

start_date = date(2023, 1, 1)
if scrape_api:
    api = GhApi(token=os.environ["GHAPI_TOKEN"])
    df = api.get_job_runtimes(org=org, repo=repo, start_date=start_date)

df = load_cached_job_info(org=org, repo=repo)
df = df[df["started_at"] > pd.to_datetime(start_date, utc=True)]
df = df[df["started_at"] < pd.to_datetime(date(2023, 2, 1), utc=True)]
# Convert times to hours
df["emissions"] = (
    emissions(df["os"].values, df["running_time"].values).to(u.kg).magnitude
)
df["running_time"] = df["running_time"] / np.timedelta64(1, "h")

##################################################
# Plot data
fig, axs = plt.subplots(nrows=2, sharex=True, figsize=(5, 8), constrained_layout=True)

# Plot total
ax = axs[0]
ax.set_title(f"Estimated CO2 emissions from GitHub Actions\n{org}/{repo}")
ax.plot(df["started_at"], np.cumsum(df["emissions"]), color="tab:blue")
ax.set_ylim(0)
ax.set_ylabel("kgeCO2")
ax.margins(x=0)

ax = axs[1]
times = {}
for name in np.unique(df["name"]):
    t = df["running_time"].copy()
    t[df["name"] != name] = 0
    times[name] = np.cumsum(t)

all_ts = np.sort([t.iloc[-1] for t in times.values()])

other_t = None
n_jobs = 5
for name, t in times.items():
    other_t = t if other_t is None else other_t + t
    if t.iloc[-1] < all_ts[-n_jobs]:
        continue

    label = name.split("/")[1][1:] if "/" in name else name
    ax.plot(df["started_at"], t, label=label)

ax.legend(bbox_to_anchor=(0.1, -0.2), loc="upper left", fontsize=8)
ax.set_title(f"Top {n_jobs} jobs")
ax.set_ylabel("Hours")
ax.set_ylim(0)
ax.margins(x=0)

locator = mdates.AutoDateLocator()
formatter = mdates.ConciseDateFormatter(locator)
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(formatter)

plt.show()
