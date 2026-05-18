from pathlib import Path


def scan_repository(repo_path):

    files = []

    for path in Path(repo_path).rglob("*"):

        if path.is_file():
            files.append(path)

    return files