---
name: skillctl
description: This skill should be used when the user wants to "manage skills", "list installed skills", "find duplicate skills", "install a new skill", "update skills", "merge similar skills", "clean up skills", "check skill status", "search for skills", or needs guidance on skill registry management and lifecycle operations for Claude Code plugins.
version: 0.1.0
---

# skillctl — Package Manager for Claude Code Skills

Provide complete lifecycle management for Claude Code skills — from discovery and installation through maintenance, deduplication, and cleanup.

## Overview

skillctl maintains a centralized registry (`data/registry.json`) that tracks every installed skill's metadata, source, version, and quality score. It provides seven commands for the full skill lifecycle:

| Command | Purpose |
|---------|---------|
| `/slm-list` | List all registered skills with filtering |
| `/slm-status` | Registry health: statistics, duplicates, orphans |
| `/slm-search` | Search for skills locally and on GitHub |
| `/slm-install` | Install a skill from GitHub |
| `/slm-update` | Update GitHub-sourced skills |
| `/slm-merge` | Intelligently merge similar skills |
| `/slm-clean` | Disable or remove skills |

## First-Time Setup (Bootstrap)

On first use, run the bootstrap process to scan all existing skills and build the registry:

```bash
python3 scripts/bootstrap.py --skills-dir ~/.claude/skills
```

This scans all skill directories, extracts YAML frontmatter, infers source and category, computes content hashes, and generates `data/registry.json`.

Refer to `references/bootstrap-guide.md` for detailed scan logic and source inference rules.

## Registry

The registry is the single source of truth for all skill metadata. Each entry tracks:

- **Identity**: name, description, version
- **Source**: type (local/github/marketplace), origin, GitHub URL, commit SHA
- **Location**: install_path on disk
- **Timestamps**: installed_at, updated_at
- **Classification**: category, tags
- **Quality**: quality_score (from skill-quality-reviewer), content_hash

Refer to `references/registry-schema.md` for the complete JSON schema.

## Core Workflows

### Discover and Install

1. Run `/slm-search <keyword>` to find skills locally and on GitHub
2. Run `/slm-install <github-url>` to install from a repository
3. The skill is automatically registered with source tracking

### Monitor and Maintain

1. Run `/slm-status` to check registry health
2. View duplicate detection results (TF-IDF similarity analysis)
3. Identify orphaned skills (on disk but not in registry)
4. Check for available updates on GitHub-sourced skills

### Update

1. Run `/slm-update <skill-name>` or `/slm-update --all`
2. Compares current commit SHA with remote HEAD
3. Shows diff summary and prompts for confirmation
4. Backs up old version before applying update

### Merge Duplicates

1. Run `/slm-merge <skill-a> <skill-b>` when duplicates are detected
2. The skill-merger agent decomposes both skills into semantic sections
3. Matches corresponding sections and selects stronger versions
4. Generates a merged preview for confirmation
5. Backs up originals and applies the merge

Refer to `references/merge-strategy.md` for the detailed merge algorithm.

### Clean Up

1. Run `/slm-clean <skill-name>` to disable a specific skill
2. Run `/slm-clean --duplicates` to review and disable duplicates
3. Disabled skills are moved to `~/.claude/skills-disabled/` (recoverable)

## Scripts Reference

All scripts use Python stdlib only (zero external dependencies):

| Script | Purpose |
|--------|---------|
| `registry.py` | Registry CRUD operations (add, remove, update, list, stats) |
| `bootstrap.py` | Initial scan and registry generation |
| `search.py` | GitHub API + local registry search |
| `similarity.py` | TF-IDF duplicate detection |
| `install.sh` | Git clone and install from GitHub |
| `update.sh` | Check and apply updates |
| `clean.sh` | Disable and move skills |

## Agents

| Agent | Purpose |
|-------|---------|
| `skill-merger` | Semantic analysis and intelligent merging of similar skills |
| `skill-auditor` | Quality audit, duplicate detection, and registry health checks |

## Integration with Existing Tools

- Calls `skill-quality-reviewer` to populate `quality_score` in registry entries
- Uses the same YAML frontmatter extraction pattern as `extract-yaml.sh`
- Compatible with Claude Code plugin marketplace structure
