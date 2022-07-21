"""
Get UCL repositories
====================
This script is for getting a list of all GitHub repositories
in the UCL organisation or that RSDG has worked on.
"""
import os

from ci_impact.gh import GhApi

orgs = ["brainglobe", "ucl", "UCL-RITS"]
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
                f.write(f"{org}/{repo}\n")
