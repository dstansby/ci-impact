"""
Get UCL repositories
====================
Get a list of all GitHub repositories in the UCL related
organisations.
"""

import os

from ci_impact.gh import GhApi

orgs = sorted(["UCL", "UCL-RITS", "UCL-MIRSG", "UCL-ARC"])
repo_file = "ucl_repos.txt"

with open(repo_file, "r") as f:
    existing_repos = f.readlines()

# Strip newline charcaters
existing_repos = [r.replace("\n", "") for r in existing_repos]

##################################################
# Load data
api = GhApi(token=os.environ["GHAPI_TOKEN"])

for org in orgs:
    repos = api.get_all_repo_names(org=org, include_private=True)
    print(f"Found {len(repos)} repos in {org} org")
    with open(repo_file, "a") as f:
        for repo in repos:
            orgrepo = f"{org}/{repo}"
            if orgrepo not in existing_repos:
                print(f"🐢 Adding new repo: {orgrepo}")
                f.write(f"{org}/{repo}\n")
