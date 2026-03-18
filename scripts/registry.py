#!/usr/bin/env python3
"""SLM Registry — CRUD operations for the skill registry.

Maintains a centralized JSON registry tracking all installed Claude Code
skills with their metadata, source provenance, and content hashes.

Usage:
    python3 registry.py add <name> [--install-path PATH] [--source-type TYPE] ...
    python3 registry.py remove <name>
    python3 registry.py update <name> [--commit-sha SHA] [--quality-score N]
    python3 registry.py get <name>
    python3 registry.py list [--category CAT] [--source-type TYPE]
    python3 registry.py stats
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SourceInfo:
    """Origin and tracking information for a skill."""

    type: str = "local"          # local | github | marketplace
    origin: str = "unknown"      # e.g. claude-scholar, baoyu, anthropic
    github_url: Optional[str] = None
    commit_sha: Optional[str] = None


@dataclass
class SkillEntry:
    """Complete metadata for a single registered skill."""

    name: str
    description: str = ""
    version: str = "0.0.0"
    source: SourceInfo = field(default_factory=SourceInfo)
    install_path: str = ""
    installed_at: str = ""
    updated_at: str = ""
    category: str = "other"
    tags: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillEntry":
        """Deserialize from dict."""
        src = data.pop("source", {})
        source = SourceInfo(**src) if isinstance(src, dict) else SourceInfo()
        return cls(source=source, **data)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class Registry:
    """Centralized skill registry backed by a JSON file."""

    SCHEMA_VERSION = "slm-registry-v1"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.skills: Dict[str, SkillEntry] = {}
        self.categories: Dict[str, List[str]] = {}
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.generated_at: str = ""

    # -- persistence --------------------------------------------------------

    def load(self) -> None:
        """Load registry from disk."""
        if not self.path.exists():
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.generated_at = data.get("generated_at", "")
        for name, entry_data in data.get("skills", {}).items():
            self.skills[name] = SkillEntry.from_dict(dict(entry_data))
        self.categories = data.get("categories", {})
        self.sources = data.get("sources", {})

    def save(self) -> None:
        """Atomic write: write to tmp file then rename."""
        self.generated_at = _now_iso()
        self._rebuild_indexes()
        payload = {
            "$schema": self.SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "skills": {n: e.to_dict() for n, e in sorted(self.skills.items())},
            "categories": dict(sorted(self.categories.items())),
            "sources": dict(sorted(self.sources.items())),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.path.parent), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp_path, str(self.path))
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # -- CRUD ---------------------------------------------------------------

    def add_skill(self, entry: SkillEntry) -> None:
        """Add or overwrite a skill entry."""
        now = _now_iso()
        if not entry.installed_at:
            entry.installed_at = now
        entry.updated_at = now
        self.skills[entry.name] = entry

    def remove_skill(self, name: str) -> bool:
        """Remove a skill entry. Return True if it existed."""
        return self.skills.pop(name, None) is not None

    def update_skill(self, name: str, **kwargs: Any) -> bool:
        """Update specific fields of an existing entry."""
        entry = self.skills.get(name)
        if entry is None:
            return False
        for key, value in kwargs.items():
            if key == "source" and isinstance(value, dict):
                for sk, sv in value.items():
                    setattr(entry.source, sk, sv)
            elif hasattr(entry, key):
                setattr(entry, key, value)
        entry.updated_at = _now_iso()
        return True

    def get_skill(self, name: str) -> Optional[SkillEntry]:
        """Retrieve a single skill entry."""
        return self.skills.get(name)

    def list_skills(
        self,
        category: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> List[SkillEntry]:
        """Return skill entries with optional filtering."""
        results = list(self.skills.values())
        if category:
            results = [s for s in results if s.category == category]
        if source_type:
            results = [s for s in results if s.source.type == source_type]
        return sorted(results, key=lambda s: s.name)

    # -- utilities ----------------------------------------------------------

    def _rebuild_indexes(self) -> None:
        """Rebuild category and source indexes from skill entries."""
        cats: Dict[str, List[str]] = {}
        srcs: Dict[str, Dict[str, Any]] = {}
        for name, entry in self.skills.items():
            cats.setdefault(entry.category, []).append(name)
            origin = entry.source.origin
            if origin not in srcs:
                srcs[origin] = {"type": entry.source.type, "count": 0}
            srcs[origin]["count"] += 1
        for names in cats.values():
            names.sort()
        self.categories = cats
        self.sources = srcs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_content_hash(filepath: str | Path) -> str:
    """Compute SHA-256 hash of a file's content."""
    h = hashlib.sha256()
    with open(filepath, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def infer_category(name: str, description: str) -> str:
    """Infer skill category from name and description keywords."""
    text = f"{name} {description}".lower()
    rules = [
        ("research", ["research", "paper", "citation", "literature", "ideation", "survey"]),
        ("writing", ["writing", "paper", "document", "latex", "markdown", "anti-ai", "review-response", "rebuttal"]),
        ("development", ["code", "git", "debug", "test", "build", "refactor", "deploy", "tdd", "commit", "bug"]),
        ("design", ["design", "ui", "ux", "frontend", "css", "layout", "theme", "canvas"]),
        ("tools", ["tool", "utility", "package", "manager", "config", "pdf", "docx", "xlsx", "pptx"]),
        ("plugin-dev", ["skill", "command", "agent", "hook", "plugin", "mcp"]),
    ]
    for category, keywords in rules:
        if any(kw in text for kw in keywords):
            return category
    return "other"


def extract_yaml_frontmatter(content: str) -> Dict[str, str]:
    """Extract YAML frontmatter from SKILL.md content (pure stdlib, no PyYAML).

    Parses the text between the first pair of ``---`` lines.
    Handles simple ``key: value`` pairs only (no nested YAML).
    """
    import re

    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    result: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sep = line.find(":")
        if sep == -1:
            continue
        key = line[:sep].strip()
        value = line[sep + 1:].strip().strip('"').strip("'")
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# CLI formatting
# ---------------------------------------------------------------------------

def _print_table(headers: List[str], rows: List[List[str]]) -> None:
    """Print a simple aligned text table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    def fmt_row(cells: List[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            w = widths[i] if i < len(widths) else len(cell)
            parts.append(cell.ljust(w))
        return " | ".join(parts)

    print(fmt_row(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row(row))


def _format_entry(entry: SkillEntry) -> None:
    """Print a single skill entry in detail."""
    print(f"Name:         {entry.name}")
    print(f"Description:  {entry.description}")
    print(f"Version:      {entry.version}")
    print(f"Category:     {entry.category}")
    print(f"Tags:         {', '.join(entry.tags) if entry.tags else '-'}")
    print(f"Source:       {entry.source.type}/{entry.source.origin}")
    print(f"GitHub URL:   {entry.source.github_url or '-'}")
    print(f"Commit SHA:   {entry.source.commit_sha or '-'}")
    print(f"Install Path: {entry.install_path}")
    print(f"Installed At: {entry.installed_at}")
    print(f"Updated At:   {entry.updated_at}")
    print(f"Quality:      {entry.quality_score if entry.quality_score is not None else '-'}")
    print(f"Content Hash: {entry.content_hash}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_registry_path() -> Path:
    """Resolve the default registry.json path (sibling data/ dir)."""
    return Path(__file__).resolve().parent.parent / "data" / "registry.json"


def cli_add(args: argparse.Namespace, reg: Registry) -> None:
    """Handle the ``add`` subcommand."""
    source = SourceInfo(
        type=args.source_type or "local",
        origin=args.origin or "unknown",
        github_url=args.github_url,
        commit_sha=args.commit_sha,
    )
    install_path = args.install_path or ""
    content_hash = ""
    description = args.description or ""
    version = args.version or "0.0.0"
    category = args.category or "other"
    tags: List[str] = []

    # Try to read SKILL.md for metadata
    skill_md = Path(install_path) / "SKILL.md" if install_path else None
    if skill_md and skill_md.exists():
        raw = skill_md.read_text(encoding="utf-8")
        fm = extract_yaml_frontmatter(raw)
        description = description or fm.get("description", "")
        version = version if version != "0.0.0" else fm.get("version", "0.0.0")
        content_hash = compute_content_hash(str(skill_md))
        category = args.category or infer_category(args.name, description)
        tags_raw = fm.get("tags", "")
        if tags_raw:
            tags = [t.strip() for t in tags_raw.split(",")]

    entry = SkillEntry(
        name=args.name,
        description=description,
        version=version,
        source=source,
        install_path=install_path,
        category=category,
        tags=tags,
        content_hash=content_hash,
    )
    reg.add_skill(entry)
    reg.save()
    print(f"Added: {args.name}")


def cli_remove(args: argparse.Namespace, reg: Registry) -> None:
    """Handle the ``remove`` subcommand."""
    if reg.remove_skill(args.name):
        reg.save()
        print(f"Removed: {args.name}")
    else:
        print(f"Not found: {args.name}", file=sys.stderr)
        sys.exit(1)


def cli_update(args: argparse.Namespace, reg: Registry) -> None:
    """Handle the ``update`` subcommand."""
    updates: Dict[str, Any] = {}
    if args.commit_sha:
        updates["source"] = {"commit_sha": args.commit_sha}
    if args.quality_score is not None:
        updates["quality_score"] = args.quality_score
    if args.description:
        updates["description"] = args.description

    # Recompute content hash if install path is known
    entry = reg.get_skill(args.name)
    if entry and entry.install_path:
        skill_md = Path(entry.install_path) / "SKILL.md"
        if skill_md.exists():
            updates["content_hash"] = compute_content_hash(str(skill_md))

    if reg.update_skill(args.name, **updates):
        reg.save()
        print(f"Updated: {args.name}")
    else:
        print(f"Not found: {args.name}", file=sys.stderr)
        sys.exit(1)


def cli_get(args: argparse.Namespace, reg: Registry) -> None:
    """Handle the ``get`` subcommand."""
    entry = reg.get_skill(args.name)
    if entry is None:
        print(f"Not found: {args.name}", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False))
    else:
        _format_entry(entry)


def cli_list(args: argparse.Namespace, reg: Registry) -> None:
    """Handle the ``list`` subcommand."""
    entries = reg.list_skills(
        category=args.category,
        source_type=args.source_type,
    )
    if not entries:
        print("No skills found matching the filter criteria.")
        return
    if args.json:
        print(json.dumps(
            [e.to_dict() for e in entries], indent=2, ensure_ascii=False
        ))
        return

    headers = ["Name", "Category", "Source", "Version", "Updated"]
    rows = []
    for e in entries:
        source_label = f"{e.source.type}/{e.source.origin}"
        updated = e.updated_at[:10] if e.updated_at else "-"
        rows.append([e.name, e.category, source_label, e.version, updated])
    _print_table(headers, rows)
    print(f"\nTotal: {len(entries)} skills")


def cli_stats(args: argparse.Namespace, reg: Registry) -> None:
    """Handle the ``stats`` subcommand."""
    total = len(reg.skills)
    print(f"Registry Statistics")
    print(f"===================")
    print(f"Total skills: {total}")
    print()

    # Category breakdown
    print("By Category:")
    cat_counts: Dict[str, int] = {}
    for entry in reg.skills.values():
        cat_counts[entry.category] = cat_counts.get(entry.category, 0) + 1
    for cat in sorted(cat_counts, key=lambda c: -cat_counts[c]):
        print(f"  {cat:15s} {cat_counts[cat]:3d}")
    print()

    # Source breakdown
    print("By Source:")
    src_counts: Dict[str, int] = {}
    for entry in reg.skills.values():
        key = f"{entry.source.type}/{entry.source.origin}"
        src_counts[key] = src_counts.get(key, 0) + 1
    for src in sorted(src_counts, key=lambda s: -src_counts[s]):
        print(f"  {src:30s} {src_counts[src]:3d}")
    print()

    # Quality summary
    scored = [e for e in reg.skills.values() if e.quality_score is not None]
    if scored:
        avg = sum(e.quality_score for e in scored) / len(scored)
        print(f"Quality Scores: {len(scored)}/{total} scored, avg={avg:.1f}")
    else:
        print(f"Quality Scores: No skills scored yet")


def main() -> None:
    """Entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="SLM Registry — manage the skill registry"
    )
    parser.add_argument(
        "--registry", "-r",
        default=str(_default_registry_path()),
        help="Path to registry.json",
    )
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a skill to the registry")
    p_add.add_argument("name", help="Skill name")
    p_add.add_argument("--install-path", help="Skill directory path")
    p_add.add_argument("--source-type", help="local|github|marketplace")
    p_add.add_argument("--origin", help="Source origin identifier")
    p_add.add_argument("--github-url", help="GitHub repository URL")
    p_add.add_argument("--commit-sha", help="Git commit SHA")
    p_add.add_argument("--description", help="Skill description override")
    p_add.add_argument("--version", help="Version override")
    p_add.add_argument("--category", help="Category override")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a skill from the registry")
    p_rm.add_argument("name", help="Skill name")

    # update
    p_up = sub.add_parser("update", help="Update a skill entry")
    p_up.add_argument("name", help="Skill name")
    p_up.add_argument("--commit-sha", help="New commit SHA")
    p_up.add_argument("--quality-score", type=float, help="Quality score 0-100")
    p_up.add_argument("--description", help="New description")

    # get
    p_get = sub.add_parser("get", help="Get a skill entry")
    p_get.add_argument("name", help="Skill name")
    p_get.add_argument("--json", action="store_true", help="Output as JSON")

    # list
    p_ls = sub.add_parser("list", help="List skills")
    p_ls.add_argument("--category", help="Filter by category")
    p_ls.add_argument("--source-type", help="Filter by source type")
    p_ls.add_argument("--json", action="store_true", help="Output as JSON")

    # stats
    sub.add_parser("stats", help="Show registry statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    reg = Registry(args.registry)
    reg.load()

    dispatch = {
        "add": cli_add,
        "remove": cli_remove,
        "update": cli_update,
        "get": cli_get,
        "list": cli_list,
        "stats": cli_stats,
    }
    dispatch[args.command](args, reg)


if __name__ == "__main__":
    main()
