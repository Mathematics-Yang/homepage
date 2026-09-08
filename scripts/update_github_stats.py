"""Refresh the public GitHub statistics snapshot used by the homepage."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import (  # noqa: E402
    collect_github_stats,
    config,
    get_github_repositories,
    make_github_request,
    select_popular_repositories,
)


SNAPSHOT_PATH = PROJECT_ROOT / "data" / "github_stats.json"


def comparable_snapshot(snapshot):
    """Return the data fields that should trigger a repository update."""
    return {
        key: value
        for key, value in snapshot.items()
        if key not in {"generated_at", "version"}
    }


def read_existing_snapshot():
    try:
        with SNAPSHOT_PATH.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def write_snapshot(snapshot):
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = SNAPSHOT_PATH.with_suffix(".json.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(snapshot, file, ensure_ascii=False, indent=2)
        file.write("\n")
    os.replace(temporary_path, SNAPSHOT_PATH)


def main():
    github_url = config.get("github_url", "").rstrip("/")
    username = github_url.split("/")[-1]
    if not username:
        raise RuntimeError("config.json 中缺少有效的 github_url")

    repositories = get_github_repositories(username)
    if not repositories:
        raise RuntimeError("未获取到 GitHub 仓库，保留现有统计快照")

    user_response = make_github_request(f"https://api.github.com/users/{username}")
    if user_response.status_code != 200:
        raise RuntimeError("未获取到 GitHub 用户资料，保留现有统计快照")
    user_data = user_response.json()

    stats = collect_github_stats(username, repositories)
    snapshot = {
        "version": 1,
        "username": username,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "name": user_data.get("name") or config.get("name") or username,
        "avatar_url": user_data.get("avatar_url", ""),
        "total_repos": user_data.get("public_repos", len(repositories)),
        "total_stars": sum(
            repository.get("stargazers_count", 0) for repository in repositories
        ),
        "popular_repos": select_popular_repositories(username, repositories),
        **stats,
    }

    existing_snapshot = read_existing_snapshot()
    if existing_snapshot and comparable_snapshot(
        existing_snapshot
    ) == comparable_snapshot(snapshot):
        print("GitHub 统计数据没有变化，无需更新快照。")
        return

    write_snapshot(snapshot)
    print(f"GitHub 统计快照已更新: {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
