from git import Repo
from pathlib import Path


def clone_repository(repo_url: str, base_dir: str = "./repos"):

    repo_name = repo_url.split("/")[-1].replace(".git", "")

    target_dir = Path(base_dir) / repo_name

    if target_dir.exists():
        print(f"Repository already exists: {target_dir}")
        return str(target_dir)

    print(f"Cloning repository into {target_dir}")

    Repo.clone_from(repo_url, target_dir)

    return str(target_dir)