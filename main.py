"""Generate the animated terminal used by the GitHub profile README."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


GITHUB_USER = "ezhulenev"
GITHUB_API = "https://api.github.com"
PACIFIC = ZoneInfo("America/Los_Angeles")
IGNORED_LANGUAGES = {"Jupyter Notebook", "Makefile"}


def github_json(url: str) -> Any:
    """Read GitHub API JSON, retrying transient failures before giving up."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{GITHUB_USER}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_error: Exception | None = None
    for attempt in range(1, 4):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except (
            json.JSONDecodeError,
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
        ) as error:
            last_error = error
            print(f"WARNING: GitHub API attempt {attempt}/3 failed for {url}: {error}")
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))

    raise RuntimeError(f"GitHub API request failed after 3 attempts: {url}") from last_error


def fetch_repositories(user: str) -> list[dict[str, Any]]:
    """Fetch every public repository owned by the profile user."""
    repositories: list[dict[str, Any]] = []
    for page in range(1, 11):
        url = (
            f"{GITHUB_API}/users/{user}/repos"
            f"?per_page=100&type=owner&sort=updated&page={page}"
        )
        batch = github_json(url)
        if not isinstance(batch, list):
            raise RuntimeError(f"Unexpected GitHub repositories response on page {page}")
        repositories.extend(batch)
        if len(batch) < 100:
            break
    return repositories


def fetch_profile(user: str) -> dict[str, Any]:
    """Collect public profile stats for the terminal."""
    user_data = github_json(f"{GITHUB_API}/users/{user}")
    if not isinstance(user_data, dict):
        raise RuntimeError("Unexpected GitHub user response")

    repositories = fetch_repositories(user)
    language_totals: defaultdict[str, int] = defaultdict(int)
    token_available = bool(os.environ.get("GITHUB_TOKEN"))

    for repository in repositories:
        if token_available:
            languages = github_json(str(repository["languages_url"]))
            if not isinstance(languages, dict):
                raise RuntimeError(
                    f"Unexpected languages response for {repository['full_name']}"
                )
            for language, size in languages.items():
                if language not in IGNORED_LANGUAGES and isinstance(size, int):
                    language_totals[language] += size
            continue

        # Unauthenticated local runs stay below GitHub's low REST rate limit by
        # using each repository's primary language instead of another API call.
        language = repository.get("language")
        if isinstance(language, str) and language not in IGNORED_LANGUAGES:
            language_totals[language] += 1

    top_languages = [
        language
        for language, _ in sorted(
            language_totals.items(), key=lambda item: item[1], reverse=True
        )[:5]
    ]
    if not top_languages:
        top_languages = ["C++", "Python", "Scala"]

    created_at = str(user_data["created_at"])
    return {
        "followers": user_data["followers"],
        "repositories": user_data["public_repos"],
        "stars": sum(int(repo["stargazers_count"]) for repo in repositories),
        "since": created_at[:4],
        "languages": top_languages,
    }


def generate_terminal(profile: dict[str, Any]) -> None:
    """Render an original OpenXLA-themed boot and profile sequence."""
    # Never expose the API token to the third-party renderer.
    os.environ.pop("GITHUB_TOKEN", None)
    import gifos

    now = datetime.now(PACIFIC)
    year = now.strftime("%Y")
    version = now.strftime("2.0.%y")
    terminal = gifos.Terminal(750, 520, 15, 15)

    # Firmware and hardware discovery.
    terminal.gen_text("", 1, count=6)
    terminal.toggle_show_cursor(False)
    terminal.gen_text(f"EZV_OS Modular BIOS v{version}", 1)
    terminal.gen_text(f"Copyright (C) {year}, \x1b[96mEugene Zhulenev\x1b[0m", 2)
    terminal.gen_text("\x1b[94mOpenXLA Distributed GPU Compute Engine\x1b[0m", 4)
    terminal.gen_text("Target: NVIDIA GPU clusters | Scale: tens of thousands of GPUs", 6)
    for memory in range(0, 65537, 8192):
        terminal.delete_row(7)
        terminal.gen_text(f"Compiler cache: {memory // 1024} MB", 7, contin=True)
    terminal.delete_row(7)
    terminal.gen_text("Compiler cache: 64 MB OK", 7, count=4, contin=True)
    terminal.gen_text("", 9, count=3, contin=True)

    # Boot and login.
    terminal.clear_frame()
    terminal.gen_text("Loading distributed XLA:GPU runtime ", 1, contin=True)
    terminal.gen_typing_text(".....", 1, contin=True)

    terminal.clear_frame()
    terminal.clone_frame(3)
    terminal.toggle_show_cursor(False)
    terminal.gen_text(f"\x1b[96mEZV_OS v{version} (tty1)\x1b[0m", 1, count=3)
    terminal.gen_text("login: ", 3, count=3)
    terminal.toggle_show_cursor(True)
    terminal.gen_typing_text("eugene", 3, contin=True)
    terminal.gen_text("", 4, count=3)
    terminal.toggle_show_cursor(False)
    terminal.gen_text("password: ", 4, count=3)
    terminal.gen_text("************", 4, count=3, contin=True)
    terminal.gen_text(
        f"Last login: {now.strftime('%a %b %d %I:%M:%S %p %Z %Y')} on tty1", 6
    )

    # Profile fetch followed by an animated, neofetch-inspired result.
    terminal.gen_prompt(8, count=3)
    prompt_column = terminal.curr_col
    terminal.toggle_show_cursor(True)
    terminal.gen_typing_text("\x1b[91mprofile.s", 8, contin=True)
    terminal.delete_row(8, prompt_column)
    terminal.gen_text("\x1b[92mprofile.sh\x1b[0m", 8, contin=True)
    terminal.gen_text(f" --github {GITHUB_USER}", 8, contin=True)

    details = f"""
\x1b[30;106m{GITHUB_USER}@GitHub\x1b[0m
----------------
\x1b[96mRole:    \x1b[93mSenior Staff Software Engineer @ Google\x1b[0m
\x1b[96mMission: \x1b[93mScale XLA:GPU pretraining to tens of thousands of GPUs\x1b[0m
\x1b[96mRuntime: \x1b[93mThunks | command buffers | async execution\x1b[0m
\x1b[96mComm:    \x1b[93mNCCL | symmetric memory | comm/compute overlap\x1b[0m
\x1b[96mMemory:  \x1b[93mDynamic slice fusion | allocators | buffers\x1b[0m
\x1b[96mAlso:    \x1b[93mXLA:CPU | heterogeneous accelerator + host\x1b[0m

\x1b[30;106mGitHub Stats\x1b[0m
----------------
\x1b[96mFollowers:       \x1b[93m{profile['followers']}\x1b[0m
\x1b[96mPublic repos:    \x1b[93m{profile['repositories']}\x1b[0m
\x1b[96mOwned repo stars:\x1b[93m {profile['stars']}\x1b[0m

\x1b[30;106mPublic Repo Languages\x1b[0m
----------------
\x1b[93m{' | '.join(profile['languages'])}\x1b[0m
""".strip()

    terminal.toggle_show_cursor(False)
    terminal.gen_text(details, 9, 5, count=4, contin=True)
    terminal.toggle_show_cursor(True)
    terminal.gen_prompt(terminal.curr_row)
    terminal.gen_typing_text(
        "\x1b[92m# Scaling pretraining across tens of thousands of GPUs\x1b[0m",
        terminal.curr_row,
        contin=True,
    )
    terminal.gen_text("", terminal.curr_row, count=80, contin=True)
    terminal.gen_gif()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    profile_source = parser.add_mutually_exclusive_group()
    profile_source.add_argument(
        "--fetch-profile",
        type=Path,
        metavar="PATH",
        help="fetch profile data and write it to PATH without rendering",
    )
    profile_source.add_argument(
        "--profile-json",
        type=Path,
        metavar="PATH",
        help="render using previously fetched profile JSON",
    )
    return parser.parse_args()


def load_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    required = {"followers", "repositories", "stars", "since", "languages"}
    if not isinstance(profile, dict) or not required.issubset(profile):
        raise RuntimeError(f"Invalid profile data in {path}")
    return profile


def main() -> None:
    args = parse_args()
    if args.fetch_profile:
        profile = fetch_profile(GITHUB_USER)
        args.fetch_profile.parent.mkdir(parents=True, exist_ok=True)
        args.fetch_profile.write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Fetched profile data to {args.fetch_profile}")
        return

    profile = (
        load_profile(args.profile_json)
        if args.profile_json
        else fetch_profile(GITHUB_USER)
    )
    generated = Path("output.gif")
    generated.unlink(missing_ok=True)

    try:
        generate_terminal(profile)
        if not generated.is_file():
            raise RuntimeError("gifos did not produce output.gif; is FFmpeg installed?")
        destination = Path("assets/terminal.gif")
        destination.parent.mkdir(parents=True, exist_ok=True)
        generated.replace(destination)
        print(f"Generated {destination} ({destination.stat().st_size:,} bytes)")
    finally:
        shutil.rmtree("frames", ignore_errors=True)


if __name__ == "__main__":
    main()
