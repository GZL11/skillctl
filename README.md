# skillctl

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://www.python.org)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen.svg)](#requirements)

Package manager for Claude Code skills — search, install, update, deduplicate, merge, and clean.

## What is skillctl?

When you use Claude Code extensively, skills accumulate from multiple sources — your own, community contributions, marketplace installs — with no way to track where they came from, detect duplicates, or manage updates. **skillctl** solves this by providing a centralized registry and full lifecycle management.

```
                search → install → status → update
                                     ↓
                              detect duplicates
                                     ↓
                               merge → clean
```

## Features

| Feature | Description |
|---------|-------------|
| **Centralized Registry** | Track every skill's source, version, content hash, and category |
| **Bootstrap Scan** | Auto-detect 100+ existing skills and build the registry |
| **Duplicate Detection** | Multi-signal similarity (TF-IDF + frontmatter + structure + name) identifies overlapping skills |
| **GitHub Search** | Find new skills on GitHub directly from Claude Code |
| **Install & Update** | One-command install from GitHub with version tracking |
| **Intelligent Merge** | LLM-powered semantic merging of similar skills |
| **Clean & Disable** | Safely disable skills (recoverable, moved to disabled dir) |

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/GZL11/skillctl.git
```

### 2. Enable as a Claude Code plugin

Add to your `~/.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "skillctl@local": true
  }
}
```

Or if you prefer project-scoped, add to your project's `.claude/settings.json`.

### 3. Bootstrap (first-time setup)

Start Claude Code and run:

```
/slm-status
```

This will detect the registry hasn't been initialized and run the bootstrap scan automatically. Or run manually:

```bash
python3 /path/to/skillctl/scripts/bootstrap.py --skills-dir ~/.claude/skills
```

## Commands

### `/slm-list` — List all skills

```
/slm-list                    # List all skills
/slm-list --category research  # Filter by category
/slm-list --source-type github # Filter by source
```

### `/slm-status` — Health check

Shows registry statistics, duplicate detection results, and orphaned skill warnings.

```
/slm-status
```

### `/slm-search` — Find skills

Search your local registry and GitHub for skills by keyword.

```
/slm-search "paper writing"
/slm-search "git" --local-only
```

### `/slm-install` — Install from GitHub

```
/slm-install https://github.com/user/skill-repo
```

### `/slm-update` — Update skills

```
/slm-update my-skill         # Update one skill
/slm-update --all            # Update all GitHub-sourced skills
```

### `/slm-merge` — Merge duplicates

Invokes the `skill-merger` agent for LLM-powered semantic merging.

```
/slm-merge skill-a skill-b
```

### `/slm-clean` — Disable skills

```
/slm-clean unused-skill      # Disable one skill
/slm-clean --duplicates      # Review and disable duplicate skills
```

## Usage Example

A typical workflow after installation:

```
# 1. First run — initialize registry and check health
/slm-status
#    → Scans ~/.claude/skills/, finds 101 skills
#    → Detects 3 likely duplicate pairs
#    → Shows category breakdown

# 2. Investigate duplicates
/slm-list --category development
#    → Lists all development skills with source and version

# 3. Merge similar skills
/slm-merge finish-release start-release
#    → skill-merger agent analyzes both skills
#    → Generates merged preview for your confirmation
#    → Backs up originals, creates merged skill

# 4. Search for new skills
/slm-search "tdd"
#    → Local: 2 matches
#    → GitHub: 5 repositories found

# 5. Install one from GitHub
/slm-install https://github.com/user/claude-tdd-pro
#    → Clones, installs to ~/.claude/skills/, registers in registry

# 6. Later — check for updates
/slm-update --all
#    → Compares commit SHAs, shows available updates
#    → Backs up old version before applying

# 7. Clean up unused skills
/slm-clean unused-skill
#    → Moves to ~/.claude/skills-disabled/ (recoverable)
```

You can also use the scripts directly without Claude Code:

```bash
# Bootstrap — scan and build registry
python3 scripts/bootstrap.py --skills-dir ~/.claude/skills

# View registry stats
python3 scripts/registry.py stats

# Find duplicates
python3 scripts/similarity.py --skills-dir ~/.claude/skills --threshold 0.5

# Search locally
python3 scripts/search.py "git" --local-only

# Install from GitHub
bash scripts/install.sh https://github.com/user/skill-repo
```

## Architecture

```
skillctl/
├── .claude-plugin/
│   └── marketplace.json         # Plugin manifest
├── skills/
│   └── skillctl/
│       ├── SKILL.md             # Main skill (auto-triggered by Claude)
│       └── references/          # Detailed documentation
│           ├── registry-schema.md
│           ├── merge-strategy.md
│           └── bootstrap-guide.md
├── commands/                    # 7 slash commands
│   ├── slm-list.md
│   ├── slm-status.md
│   ├── slm-search.md
│   ├── slm-install.md
│   ├── slm-update.md
│   ├── slm-merge.md
│   └── slm-clean.md
├── agents/                      # 2 specialized agents
│   ├── skill-merger.md          # Intelligent skill merging
│   └── skill-auditor.md         # Quality audit & health check
├── scripts/                     # Core scripts (zero dependencies)
│   ├── registry.py              # Registry CRUD operations
│   ├── bootstrap.py             # Initial skill scan
│   ├── search.py                # GitHub + local search
│   ├── similarity.py            # Multi-signal duplicate detection
│   ├── install.sh               # Git clone & install
│   ├── update.sh                # Version update
│   └── clean.sh                 # Disable & cleanup
└── data/
    └── registry.json            # Generated at runtime
```

## Registry Schema

Each skill entry tracks:

```json
{
  "name": "git-workflow",
  "description": "...",
  "version": "1.2.0",
  "source": {
    "type": "local",
    "origin": "claude-scholar",
    "github_url": null,
    "commit_sha": null
  },
  "install_path": "~/.claude/skills/git-workflow",
  "installed_at": "2026-03-18T12:00:00Z",
  "updated_at": "2026-03-18T12:00:00Z",
  "category": "development",
  "tags": ["Git", "Workflow"],
  "quality_score": null,
  "content_hash": "sha256:abc123..."
}
```

Source types: `local` (self-authored), `github` (community), `marketplace` (official/third-party marketplace).

## Requirements

- Python >= 3.8 (stdlib only, zero external dependencies)
- Git >= 2.0
- Claude Code

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit with Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
4. Open a Pull Request

## License

[MIT](LICENSE)
