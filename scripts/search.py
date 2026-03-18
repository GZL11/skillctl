#!/usr/bin/env python3
"""Search for Claude Code skills in local registry and on GitHub.

Provides two search modes:
- Local: searches the installed skill registry (registry.json)
- GitHub: searches GitHub repositories and SKILL.md files via the API

Usage:
    python search.py <keyword> [--local-only] [--github-only] [--json]
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_MAX_RESULTS = 20
DEFAULT_REGISTRY_PATH = str(
    Path(__file__).resolve().parent.parent / "data" / "registry.json"
)


# ---------------------------------------------------------------------------
# Local search
# ---------------------------------------------------------------------------


def search_local(registry_path: str, keyword: str) -> List[Dict[str, Any]]:
    """Search the local skill registry for *keyword*.

    Performs case-insensitive substring matching against each skill's name,
    description, and tags.

    Args:
        registry_path: Path to registry.json.
        keyword: Search term.

    Returns:
        List of matching registry entries with ``match_type`` set to
        ``"local"``.
    """
    path = Path(registry_path)
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8") as fh:
            registry: Dict[str, Any] = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: failed to read registry – {exc}", file=sys.stderr)
        return []

    skills = registry.get("skills", {})
    if not skills:
        return []

    pattern = keyword.lower()
    results: List[Dict[str, Any]] = []

    for name, entry in skills.items():
        searchable = " ".join(
            [
                name,
                entry.get("description", ""),
                " ".join(entry.get("tags", [])),
            ]
        ).lower()

        if pattern in searchable:
            source = entry.get("source", {})
            results.append(
                {
                    "name": name,
                    "description": entry.get("description", ""),
                    "tags": entry.get("tags", []),
                    "install_path": entry.get("install_path", ""),
                    "source_type": source.get("type", "local"),
                    "url": source.get("github_url", ""),
                    "match_type": "local",
                }
            )

    return results


# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------


def _github_request(url: str) -> Optional[Dict[str, Any]]:
    """Make an authenticated (when possible) GitHub API request.

    Args:
        url: Fully-qualified API URL.

    Returns:
        Parsed JSON response, or ``None`` on failure.
    """
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "skillctl")

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            remaining = resp.headers.get("X-RateLimit-Remaining")
            if remaining is not None and int(remaining) < 5:
                reset_ts = resp.headers.get("X-RateLimit-Reset", "")
                _warn_rate_limit(remaining, reset_ts)
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            reset_ts = exc.headers.get("X-RateLimit-Reset", "")
            _warn_rate_limit("0", reset_ts)
        elif exc.code == 422:
            print(
                "Warning: GitHub search validation error – "
                "try a simpler keyword.",
                file=sys.stderr,
            )
        else:
            print(
                f"Warning: GitHub API returned HTTP {exc.code}.",
                file=sys.stderr,
            )
        return None
    except (urllib.error.URLError, OSError) as exc:
        print(f"Warning: network error – {exc}", file=sys.stderr)
        return None


def _warn_rate_limit(remaining: str, reset_ts: str) -> None:
    """Print a user-friendly rate-limit warning."""
    msg = f"GitHub API rate limit low (remaining: {remaining})."
    if reset_ts:
        try:
            reset_time = time.strftime(
                "%H:%M:%S", time.localtime(int(reset_ts))
            )
            msg += f" Resets at {reset_time}."
        except (ValueError, OSError):
            pass
    if not os.environ.get("GITHUB_TOKEN"):
        msg += (
            " Set GITHUB_TOKEN env var for higher limits"
            " (5000 req/h vs 60 req/h)."
        )
    print(f"Warning: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# GitHub search
# ---------------------------------------------------------------------------


def search_github(
    keyword: str, max_results: int = DEFAULT_MAX_RESULTS
) -> List[Dict[str, Any]]:
    """Search GitHub for skill repositories and SKILL.md files.

    Two queries are issued:
    1. Repository search – repos matching *claude skill <keyword>*.
    2. Code search – ``SKILL.md`` files containing *keyword*.

    Args:
        keyword: Search term.
        max_results: Maximum results per query.

    Returns:
        Deduplicated list of result dicts with ``match_type`` set to
        ``"github"``.
    """
    results: List[Dict[str, Any]] = []
    seen_urls: set = set()

    # --- 1. Repository search -------------------------------------------
    q_repo = urllib.parse.quote(f"claude skill {keyword}")
    repo_url = (
        f"{GITHUB_API_BASE}/search/repositories"
        f"?q={q_repo}&sort=stars&per_page={max_results}"
    )
    repo_data = _github_request(repo_url)
    if repo_data and "items" in repo_data:
        for item in repo_data["items"]:
            html_url = item.get("html_url", "")
            if html_url in seen_urls:
                continue
            seen_urls.add(html_url)
            results.append(
                {
                    "name": item.get("full_name", item.get("name", "")),
                    "description": item.get("description", "") or "",
                    "stars": item.get("stargazers_count", 0),
                    "url": html_url,
                    "updated_at": item.get("updated_at", ""),
                    "match_type": "github",
                }
            )

    # --- 2. Code search (SKILL.md files) --------------------------------
    q_code = urllib.parse.quote(f"filename:SKILL.md {keyword}")
    code_url = (
        f"{GITHUB_API_BASE}/search/code"
        f"?q={q_code}&per_page={max_results}"
    )
    code_data = _github_request(code_url)
    if code_data and "items" in code_data:
        for item in code_data["items"]:
            repo = item.get("repository", {})
            html_url = repo.get("html_url", "")
            if html_url in seen_urls:
                continue
            seen_urls.add(html_url)
            results.append(
                {
                    "name": repo.get("full_name", repo.get("name", "")),
                    "description": repo.get("description", "") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "url": html_url,
                    "updated_at": repo.get("updated_at", ""),
                    "match_type": "github",
                }
            )

    return results


# ---------------------------------------------------------------------------
# Combined search
# ---------------------------------------------------------------------------


def search(
    keyword: str,
    registry_path: str,
    local_only: bool = False,
    github_only: bool = False,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> List[Dict[str, Any]]:
    """Run local and/or GitHub searches and merge results.

    Args:
        keyword: Search term.
        registry_path: Path to registry.json.
        local_only: Only search local registry.
        github_only: Only search GitHub.
        max_results: Max GitHub results per query.

    Returns:
        Combined, deduplicated list (local results first).
    """
    results: List[Dict[str, Any]] = []
    seen_keys: set = set()

    # Local search
    if not github_only:
        if not Path(registry_path).exists():
            print(
                "Warning: registry.json not found. "
                "Run bootstrap.py first to build it.",
                file=sys.stderr,
            )
        for entry in search_local(registry_path, keyword):
            key = entry.get("name", "")
            if key and key not in seen_keys:
                seen_keys.add(key)
                results.append(entry)

    # GitHub search
    if not local_only:
        for entry in search_github(keyword, max_results):
            key = entry.get("url", entry.get("name", ""))
            if key and key not in seen_keys:
                seen_keys.add(key)
                results.append(entry)

    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _truncate(text: str, width: int) -> str:
    """Truncate *text* to *width*, adding ellipsis if needed."""
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def format_table(results: List[Dict[str, Any]], keyword: str) -> str:
    """Render search results as a human-readable table.

    Args:
        results: Search result dicts.
        keyword: Original search keyword (for the header).

    Returns:
        Formatted table string.
    """
    if not results:
        return f'No results found for "{keyword}".'

    lines: List[str] = []
    lines.append(f'Search Results for "{keyword}"')
    lines.append("=" * 78)
    header = (
        f"{'#':<4}| {'Source':<8}| {'Name':<25}| "
        f"{'Description':<30}| {'Stars':<5}"
    )
    lines.append(header)
    lines.append(
        f"{'---':<4}|{'-' * 8}|{'-' * 25}|{'-' * 30}|{'-' * 5}"
    )

    for idx, entry in enumerate(results, 1):
        source = entry.get("match_type", "?")
        name = _truncate(entry.get("name", ""), 23)
        desc = _truncate(entry.get("description", ""), 28)
        stars = entry.get("stars", "-")
        if stars == 0 or source == "local":
            stars = "-"
        lines.append(
            f"{idx:<4}| {source:<8}| {name:<25}| {desc:<30}| {stars!s:<5}"
        )

    return "\n".join(lines)


def format_json(results: List[Dict[str, Any]]) -> str:
    """Render search results as a JSON string.

    Args:
        results: Search result dicts.

    Returns:
        Pretty-printed JSON.
    """
    return json.dumps(results, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Search for Claude Code skills locally and on GitHub.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python search.py git-workflow\n"
            "  python search.py writing --local-only\n"
            "  python search.py tdd --github-only --max-results 10\n"
            "  python search.py refactor --json\n"
        ),
    )
    parser.add_argument("keyword", help="Search keyword (required).")
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Search only the local registry.",
    )
    parser.add_argument(
        "--github-only",
        action="store_true",
        help="Search only GitHub.",
    )
    parser.add_argument(
        "--registry-path",
        default=DEFAULT_REGISTRY_PATH,
        help="Path to registry.json (default: ../data/registry.json).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Max GitHub results per query (default: {DEFAULT_MAX_RESULTS}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output results as JSON instead of a table.",
    )
    return parser


def main() -> None:
    """Entry point for the search CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.local_only and args.github_only:
        parser.error("--local-only and --github-only are mutually exclusive.")

    results = search(
        keyword=args.keyword,
        registry_path=args.registry_path,
        local_only=args.local_only,
        github_only=args.github_only,
        max_results=args.max_results,
    )

    if args.output_json:
        print(format_json(results))
    else:
        print(format_table(results, args.keyword))


if __name__ == "__main__":
    main()
