# skillctl

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
| **Duplicate Detection** | TF-IDF similarity analysis identifies overlapping skills |
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
│   ├── similarity.py            # TF-IDF duplicate detection
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
