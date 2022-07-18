import warnings
from pathlib import Path
from typing import List, Optional

import ghapi.all
import numpy as np
import pandas as pd

__all__ = ["GhApi", "load_cached_job_info"]

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


class GhApi:
    """
    A GitHub API class that extends `ghapi.all.GhApi`.
    """

    def __init__(self, token: str) -> None:
        """
        Parameters
        ----------
        token : str
            GitHub API token.
        """
        self.api = ghapi.all.GhApi(token=token)

    def get_all_repo_names(self, *, org: str, include_private=False) -> List[str]:
        """
        Get all repository names for a given organisation.

        Parameters
        ----------
        org : str
            Orgainisation name.
        include_private : bool, optional
            If `True`, include private repositories that can be accessed by the
            currently authenticated user.

        Returns
        -------
        names : list[str]
            List of repository names.
        """
        repos = []
        i = 1
        repos = ghapi.all.paged(self.api.repos.list_for_org, org=org, per_page=100)
        for page in repos:
            print(f"Getting page {i} of repositories for {org}")
            repos += page
            i += 1

        if include_private:
            repo_names = [repo.name for repo in repos]
        else:
            repo_names = [repo.name for repo in repos if not repo.private]
        return repo_names

    def get_job_runtimes(self, *, org: str, repo: str) -> Optional[pd.DataFrame]:
        """
        Get a list of completed jobs with starttimes, endtimes, and total runtimes
        from a given GitHub respository.

        Parameters
        ----------
        org : str
            Organisation name.
        repo : str
            Repository name.

        Returns
        -------
        None, pd.DataFrame
            `None` if there are no jobs for this repository.
            Otherwise a DataFrame with job ID as the index, and the following
            columns:
             - job name
             - job start time
             - job end time
             - total running time

        Notes
        -----
        This currently only queries the last 100 workflow runs in a given
        repository.
        """
        job_cache_file = get_job_cache_file(repo=repo, org=org)
        if job_cache_file.exists():
            new_df = pd.read_csv(
                job_cache_file,
                index_col="id",
                parse_dates=["started_at", "completed_at"],
            )
            workflow_ids = set(new_df["workflow_id"])
        else:
            workflow_ids = set()

        workflows = self.api.actions.list_workflow_runs_for_repo(
            owner=org, repo=repo, per_page=10
        )
        if workflows.total_count == 0:
            return None

        runtimes = []
        keys = ["id", "name", "started_at", "completed_at"]
        for workflow_run in workflows["workflow_runs"]:
            workflow_id = workflow_run["id"]
            if workflow_id in workflow_ids:
                print(
                    f"💾 Getting cached jobs for workflow #{workflow_id} from {org}/{repo}"
                )
                # Job already saved
                continue

            print(f"🌎 Downloading jobs for workflow #{workflow_id} from {org}/{repo}")
            jobs = self.api.actions.list_jobs_for_workflow_run(
                owner=org,
                repo=repo,
                run_id=workflow_id,
                per_page=100,
            )
            if jobs["total_count"] > 100:
                warnings.warn("More than 100 jobs, only saving the first 100")
            for job in jobs["jobs"]:
                data = {key: job[key] for key in keys}
                data["workflow_id"] = workflow_id
                runtimes.append(data)

        if len(runtimes):
            df = pd.DataFrame(runtimes)
            df = df.set_index("id")
            df["completed_at"] = pd.to_datetime(df["completed_at"])
            df["started_at"] = pd.to_datetime(df["started_at"])
            df = df[np.isfinite(df["completed_at"])]
            if job_cache_file.exists():
                df = pd.concat([df, new_df])
        else:
            df = new_df

        df.to_csv(job_cache_file)
        return load_cached_job_info(org=org, repo=repo)


def get_job_cache_file(*, org: str, repo: str) -> Path:
    """
    Get the cached job file for a given org/repo.
    """
    return CACHE_DIR / f"{org}_{repo}_jobs.csv"


def load_cached_job_info(*, org: str, repo: str) -> pd.DataFrame:
    """
    Load cached job information saved by `GhApi.get_job_runtimes`.
    """
    job_cache_file = get_job_cache_file(org=org, repo=repo)
    if not job_cache_file.exists():
        raise FileNotFoundError(f"Could not find {job_cache_file}")

    df = pd.read_csv(
        job_cache_file,
        index_col="id",
        parse_dates=["started_at", "completed_at", "running_time"],
    )
    # Only include completed jobs
    df = df[np.isfinite(df["completed_at"])]
    # Add a running time column
    df["running_time"] = pd.to_timedelta(df["completed_at"] - df["started_at"])
    # Sort by start time
    df = df.sort_values("started_at")
    return df
