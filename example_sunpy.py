"""
sunpy CI jobs
=============
"""
from datetime import date

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ci_impact import GhApi, load_cached_job_info

org = "sunpy"
repo = "sunpy"

##################################################
# Load data
api = GhApi(token="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")
# df = api.get_job_runtimes(org='sunpy', repo='sunpy', start_date=date(2022, 6, 18))
df = load_cached_job_info(org=org, repo=repo)
# Convert times to hours
df["running_time"] = df["running_time"] / np.timedelta64(1, "h")

##################################################
# Plot data
fig, axs = plt.subplots(nrows=2, sharex=True, figsize=(5, 8))
fig.subplots_adjust(bottom=0.33)
# Plot total
ax = axs[0]
ax.plot(df["started_at"], np.cumsum(df["running_time"]), color="k")

ax.set_title(f"Total CI time for {org}/{repo}")
ax.set_ylim(0)
ax.set_ylabel("Hours")

ax = axs[1]
times = {}
for name in np.unique(df["name"]):
    t = df["running_time"].copy()
    t[df["name"] != name] = 0
    times[name] = np.cumsum(t)

all_ts = np.sort([t.iloc[-1] for t in times.values()])

for name, t in times.items():
    if t.iloc[-1] < all_ts[-10]:
        continue

    label = name.split("/")[1][1:] if "/" in name else name
    ax.plot(df["started_at"], t, label=label)

ax.legend(bbox_to_anchor=(0.1, -0.2), loc="upper left", fontsize=8)
ax.set_title("Top 10 jobs")

locator = mdates.AutoDateLocator()
formatter = mdates.ConciseDateFormatter(locator)
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(formatter)

plt.show()
