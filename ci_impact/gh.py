import warnings
from datetime import date, datetime
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

    def get_rate_limit(self) -> int:
        return int(self.api.limit_rem)

    def get_all_repo_names(
        self, *, org: str, include_private: bool = False
    ) -> List[str]:
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
        repos_paged = ghapi.all.paged(
            self.api.repos.list_for_org, org=org, per_page=100
        )
        for page in repos_paged:
            print(f"Getting page {i} of repositories for {org}")
            repos += page
            i += 1

        if include_private:
            repo_names = [repo.name for repo in repos]
        else:
            repo_names = [repo.name for repo in repos if not repo.private]
        return repo_names

    def get_job_runtimes(
        self, *, org: str, repo: str, start_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Get a list of completed jobs with starttimes, endtimes, and total runtimes
        from a given GitHub respository.

        Parameters
        ----------
        org : str
            Organisation name.
        repo : str
            Repository name.
        start_date : datetime.date
            Date from which to get jobs from. Jobs are fetched form this date to
            the present day. Because workflows are fetched in batches of 100,
            some jobs before this date may be present.

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
            cached_df = pd.read_csv(
                job_cache_file,
                index_col="id",
                parse_dates=["started_at", "completed_at"],
            )
            workflow_ids = set(cached_df["workflow_id"])
        else:
            cached_df = None
            workflow_ids = set()

        workflows_paged = ghapi.all.paged(
            self.api.actions.list_workflow_runs_for_repo,
            owner=org,
            repo=repo,
            per_page=100,
        )
        runtimes = []
        # Fields to save
        keys = ["id", "name", "started_at", "completed_at"]
        i = 1
        for workflows in workflows_paged:
            print(f"🗄  Downloading page {i} of workflows for {org}/{repo}")
            i += 1
            if len(workflows["workflow_runs"]) == 0:
                break

            for workflow_run in workflows["workflow_runs"]:
                workflow_id = workflow_run["id"]
                if workflow_id in workflow_ids:
                    # Job already saved
                    continue

                run_started = workflow_run["run_started_at"]
                print(
                    f"🌎 Downloading jobs for workflow #{workflow_id} from {org}/{repo} ({run_started})"
                )
                jobs = self.api.actions.list_jobs_for_workflow_run(
                    owner=org,
                    repo=repo,
                    run_id=workflow_id,
                    per_page=100,
                )
                if jobs["total_count"] > 100:
                    warnings.warn(
                        "More than 100 jobs in workflow, only saving the first 100"
                    )
                for job in jobs["jobs"]:
                    data = {key: job[key] for key in keys}
                    data["workflow_id"] = workflow_id

                    # Extract OS from labels
                    if "labels" not in job:
                        warnings.warn("No labels in job info")
                        data["os"] = "unknown"
                    else:
                        data["os"] = self._os_from_labels(job["labels"])

                    data["workflow_run"] = workflow_run["name"]
                    runtimes.append(data)

            # Save
            if len(runtimes):
                df = pd.DataFrame(runtimes)
                df = df.set_index("id")
                df["completed_at"] = pd.to_datetime(df["completed_at"])
                df["started_at"] = pd.to_datetime(df["started_at"])
                df = df[np.isfinite(df["completed_at"])]
                if cached_df is not None:
                    df = pd.concat([df, cached_df])
                df = df.sort_values("started_at")
                df.to_csv(job_cache_file)

            # Check date of the oldest workflow run in this batch
            if workflow_run["run_started_at"] is not None:
                run_start = datetime.strptime(
                    workflow_run["run_started_at"], "%Y-%m-%dT%H:%M:%SZ"
                )
                if run_start.date() < start_date:
                    break
            else:
                warnings.warn("Run start time is None")

        if not len(runtimes):
            return None
        return load_cached_job_info(org=org, repo=repo)

    @staticmethod
    def _os_from_labels(labels: List[str]) -> str:
        """
        Get operating system from a list of GH actions labels.
        """
        if len(labels) > 1:
            return "self-hosted"
        elif len(labels) == 0:
            return "unknown"
        else:
            label = labels[0]
            if "-" in label:
                return label.split("-")[0]
            else:
                return "unknown"


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
        parse_dates=["started_at", "completed_at"],
    )
    # Only include completed jobs
    df = df[np.isfinite(df["completed_at"])]
    # Add a running time column
    df["running_time"] = pd.to_timedelta(df["completed_at"] - df["started_at"])
    # Sort by start time
    df = df.sort_values("started_at")
    df["repo"] = repo
    return df
