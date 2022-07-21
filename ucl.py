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

##################################################
# Load data
api = GhApi(token=os.environ["GHAPI_TOKEN"])

# repos = api.get_all_repo_names(org=org, include_private=True)
orgrepos = np.loadtxt("ucl_repos.txt", dtype=str)
print(f"Getting data for {len(orgrepos)} repositories")

query_gh = True
if query_gh:
    # Get job info from GH REST API
    for orgrepo in orgrepos:
        org, repo = orgrepo.split("/")
        if org.lower() != 'ucl-rits':
            continue
        api.get_job_runtimes(org=org, repo=repo, start_date=date(2022, 1, 1))

# Load job info from saved files
ci_dict = {}
for orgrepo in orgrepos:
    org, repo = orgrepo.split("/")
    try:
        ci_dict[repo] = load_cached_job_info(org=org, repo=repo)
    except FileNotFoundError:
        continue

ci_info = pd.concat(ci_dict.values())
ci_info = ci_info.sort_values("started_at")
ci_info = ci_info[ci_info["started_at"] > pd.to_datetime("2022-01-01", utc=True)]

# temp fixes
ci_info.loc[ci_info["os"] == "self", "os"] = "unknown"
ci_info.loc[ci_info["os"] == "unkown", "os"] = "unknown"
ci_info.loc[ci_info["os"] == "macOS", "os"] = "macos"

# Calculate emissions
ci_info["emissions"] = (
    emissions(ci_info["os"].values, ci_info["running_time"].values).to(u.kg).magnitude
)
ci_info["running_time"] = ci_info["running_time"] / np.timedelta64(1, "h")

repo_emissions = ci_info.groupby("repo")["emissions"].sum().sort_values()
repo_emissions = repo_emissions.iloc[-10:]

##################################################
# Plot graphs
fig, axs = plt.subplots(nrows=2, constrained_layout=True, figsize=(4, 6))

ax = axs[0]
ax.plot(ci_info["started_at"], np.cumsum(ci_info["emissions"]))

ax.set_ylabel("kgeCO2")
ax.set_ylim(0)
ax.set_title(f"Estimated CO2 emissions from\n{len(ci_info)} GitHub action runs\non ARC related projects")

locator = mdates.AutoDateLocator()
formatter = mdates.ConciseDateFormatter(locator)
ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(formatter)

ax = axs[1]
ax.barh(repo_emissions.index, repo_emissions.values)

ax.set_title("Top 10 repositories")
ax.tick_params(axis="y", labelsize=10)
ax.set_xlabel("kgeCO2")

plt.show()
