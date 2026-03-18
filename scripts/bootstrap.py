#!/usr/bin/env python3
"""SLM Bootstrap — scan existing skills and build the initial registry.

Walks the skills directory, extracts YAML frontmatter from each SKILL.md,
infers source provenance and category, and writes a complete registry.json.

Usage:
    python3 bootstrap.py [--skills-dir DIR] [--output PATH] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Resolve sibling import
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from registry import (
    Registry,
    SkillEntry,
    SourceInfo,
    compute_content_hash,
    extract_yaml_frontmatter,
    infer_category,
)

# ---------------------------------------------------------------------------
# Constants — known skill origins
# ---------------------------------------------------------------------------

CLAUDE_SCHOLAR_SKILLS: Set[str] = {
    "research-ideation", "results-analysis", "citation-verification",
    "daily-paper-generator", "ml-paper-writing", "writing-anti-ai",
    "paper-self-review", "review-response", "post-acceptance",
    "doc-coauthoring", "latex-conference-template-organizer",
    "daily-coding", "git-workflow", "code-review-excellence",
    "bug-detective", "architecture-design", "verification-loop",
    "skill-development", "skill-improver", "skill-quality-reviewer",
    "command-development", "command-name", "agent-identifier",
    "hook-development", "mcp-integration", "planning-with-files",
    "uv-package-manager", "webapp-testing", "kaggle-learner",
    "frontend-design", "ui-ux-pro-max", "web-design-reviewer",
}

BAOYU_PREFIX = "baoyu-"

ANTHROPIC_SKILLS: Set[str] = {
    "pdf", "docx", "xlsx", "pptx", "quick", "best-practices",
    "hierarchical", "references", "brainstorming", "get-context",
    "executing-plans", "writing-plans", "superpowers-references",
    "claude-api",
}


# ---------------------------------------------------------------------------
# Source inference
# ---------------------------------------------------------------------------

def infer_source(
    skill_name: str,
    installed_plugins: Dict[str, Any],
    known_marketplaces: Dict[str, Any],
) -> SourceInfo:
    """Determine the most likely source of a skill.

    Priority:
    1. Exact match in installed_plugins → marketplace
    2. Name starts with 'baoyu-' → github/baoyu
    3. In CLAUDE_SCHOLAR_SKILLS set → local/claude-scholar
    4. In ANTHROPIC_SKILLS set → marketplace/anthropic
    5. Check if any marketplace key contains the skill name → marketplace
    6. Default → local/unknown
    """
    # Check installed plugins
    for plugin_key, installs in installed_plugins.get("plugins", {}).items():
        plugin_name = plugin_key.split("@")[0] if "@" in plugin_key else plugin_key
        if skill_name == plugin_name or skill_name in plugin_name:
            marketplace = plugin_key.split("@")[1] if "@" in plugin_key else ""
            github_url = None
            commit_sha = None

            # Try to get GitHub URL from known marketplaces
            if marketplace and marketplace in known_marketplaces:
                mp = known_marketplaces[marketplace]
                src_info = mp.get("source", {})
                if src_info.get("source") == "github":
                    repo = src_info.get("repo", "")
                    if repo:
                        github_url = f"https://github.com/{repo}"

            # Get commit SHA from install data
            if isinstance(installs, list) and installs:
                commit_sha = installs[0].get("gitCommitSha")

            return SourceInfo(
                type="marketplace",
                origin=marketplace or "unknown",
                github_url=github_url,
                commit_sha=commit_sha,
            )

    # Baoyu skills
    if skill_name.startswith(BAOYU_PREFIX):
        return SourceInfo(type="github", origin="baoyu")

    # Claude Scholar skills
    if skill_name in CLAUDE_SCHOLAR_SKILLS:
        return SourceInfo(type="local", origin="claude-scholar")

    # Anthropic skills
    if skill_name in ANTHROPIC_SKILLS:
        return SourceInfo(type="marketplace", origin="anthropic")

    # Default: community / unknown
    return SourceInfo(type="local", origin="unknown")


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan_skills_directory(skills_dir: Path) -> List[Path]:
    """Find all skill directories containing a SKILL.md file."""
    results = []
    if not skills_dir.exists():
        return results
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            results.append(child)
    return results


def build_entry(
    skill_dir: Path,
    installed_plugins: Dict[str, Any],
    known_marketplaces: Dict[str, Any],
) -> SkillEntry:
    """Build a SkillEntry from a skill directory."""
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    # Read and parse SKILL.md
    raw = ""
    frontmatter: Dict[str, str] = {}
    content_hash = ""
    if skill_md.exists():
        try:
            raw = skill_md.read_text(encoding="utf-8")
            frontmatter = extract_yaml_frontmatter(raw)
            content_hash = compute_content_hash(str(skill_md))
        except (OSError, UnicodeDecodeError) as exc:
            print(f"  Warning: Could not read {skill_md}: {exc}", file=sys.stderr)

    # Extract metadata
    description = frontmatter.get("description", "")
    version = frontmatter.get("version", "0.0.0")
    name_display = frontmatter.get("name", skill_name)

    # Parse tags if present
    tags: List[str] = []
    tags_raw = frontmatter.get("tags", "")
    if tags_raw:
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # Infer source and category
    source = infer_source(skill_name, installed_plugins, known_marketplaces)
    category = infer_category(skill_name, description)

    # Timestamps — use file modification time as approximation
    try:
        mtime = skill_md.stat().st_mtime if skill_md.exists() else 0
        ts = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except OSError:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return SkillEntry(
        name=skill_name,
        description=description[:500],  # cap for registry readability
        version=version,
        source=source,
        install_path=str(skill_dir),
        installed_at=ts,
        updated_at=ts,
        category=category,
        tags=tags,
        quality_score=None,
        content_hash=content_hash,
    )


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def bootstrap(
    skills_dir: Path,
    output_path: Path,
    force: bool = False,
) -> None:
    """Run the full bootstrap process."""
    if output_path.exists() and not force:
        print(f"Registry already exists at {output_path}")
        print("Use --force to overwrite.")
        sys.exit(1)

    print(f"Scanning skills directory: {skills_dir}")
    print()

    # Load external data sources
    installed_plugins = _load_json(Path.home() / ".claude" / "plugins" / "installed_plugins.json")
    known_marketplaces = _load_json(Path.home() / ".claude" / "plugins" / "known_marketplaces.json")

    # Also scan marketplace cache if exists
    marketplace_cache = Path.home() / ".claude" / "plugins" / "cache"
    extra_skill_dirs: List[Path] = []
    if marketplace_cache.exists():
        for mp_dir in marketplace_cache.iterdir():
            if mp_dir.is_dir():
                extra_skill_dirs.extend(scan_skills_directory(mp_dir / "skills"))

    # Scan main skills directory
    skill_dirs = scan_skills_directory(skills_dir)

    # Build registry
    reg = Registry(output_path)
    counters: Dict[str, int] = {}
    cat_counters: Dict[str, int] = {}
    warnings: List[str] = []

    for skill_dir in skill_dirs:
        try:
            entry = build_entry(skill_dir, installed_plugins, known_marketplaces)
            reg.add_skill(entry)

            # Count by source
            src_key = f"{entry.source.type}/{entry.source.origin}"
            counters[src_key] = counters.get(src_key, 0) + 1

            # Count by category
            cat_counters[entry.category] = cat_counters.get(entry.category, 0) + 1
        except Exception as exc:
            warnings.append(f"Failed to process {skill_dir.name}: {exc}")

    # Save
    reg.save()

    # Summary
    total = len(reg.skills)
    print(f"Bootstrap Scan Summary")
    print(f"======================")
    print(f"Total skills scanned: {total}")
    print()

    print("By Source:")
    for src in sorted(counters, key=lambda s: -counters[s]):
        print(f"  {src:35s} {counters[src]:3d}")
    print()

    print("By Category:")
    for cat in sorted(cat_counters, key=lambda c: -cat_counters[c]):
        print(f"  {cat:15s} {cat_counters[cat]:3d}")
    print()

    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
        print()

    print(f"Registry written to: {output_path}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Dict[str, Any]:
    """Load a JSON file, returning empty dict if missing or invalid."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="SLM Bootstrap — scan skills and build registry"
    )
    parser.add_argument(
        "--skills-dir",
        default=str(Path.home() / ".claude" / "skills"),
        help="Path to skills directory (default: ~/.claude/skills)",
    )
    parser.add_argument(
        "--output",
        default=str(_SCRIPT_DIR.parent / "data" / "registry.json"),
        help="Output registry.json path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing registry",
    )
    args = parser.parse_args()

    bootstrap(
        skills_dir=Path(args.skills_dir),
        output_path=Path(args.output),
        force=args.force,
    )


if __name__ == "__main__":
    main()
