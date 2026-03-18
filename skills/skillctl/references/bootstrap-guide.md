# Bootstrap Guide

## Overview

The bootstrap process (`scripts/bootstrap.py`) performs a one-time scan of all installed skills to build the initial registry. This is required before any other SLM commands can function.

## Scan Process

### Step 1: Directory Discovery

Scan the skills directory (default: `~/.claude/skills/`) for all subdirectories containing a `SKILL.md` file:

```
~/.claude/skills/
├── git-workflow/SKILL.md       Found
├── ml-paper-writing/SKILL.md   Found
├── some-dir/                   No SKILL.md, skipped
└── empty-skill/SKILL.md        Found (even if empty)
```

### Step 2: Frontmatter Extraction

Extract YAML frontmatter from each SKILL.md using regex (no PyYAML dependency):

```python
# Pattern: content between first two --- lines
match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
# Parse key: value pairs line by line
```

Extracted fields: `name`, `description`, `version`, `tags`

### Step 3: Source Inference

Determine how each skill was installed:

| Pattern | Source Type | Origin |
|---------|------------|--------|
| Name starts with `baoyu-` | github | baoyu |
| Known claude-scholar skills | local | claude-scholar |
| Found in `installed_plugins.json` | marketplace | (from plugin data) |
| Found in marketplace cache dirs | marketplace | (from cache data) |
| Default | local | unknown |

#### Claude-Scholar Known Skills (32)

The following skills are identified as locally authored:
```
research-ideation, results-analysis, citation-verification, daily-paper-generator,
ml-paper-writing, writing-anti-ai, paper-self-review, review-response,
post-acceptance, doc-coauthoring, latex-conference-template-organizer,
daily-coding, git-workflow, code-review-excellence, bug-detective,
architecture-design, verification-loop,
skill-development, skill-improver, skill-quality-reviewer, command-development,
command-name, agent-identifier, hook-development, mcp-integration,
planning-with-files, uv-package-manager, webapp-testing, kaggle-learner,
frontend-design, ui-ux-pro-max, web-design-reviewer
```

### Step 4: Category Inference

Assign categories based on keyword matching in name and description:

| Category | Keywords |
|----------|----------|
| research | research, paper, citation, literature, ideation, survey |
| writing | writing, paper, document, latex, markdown, anti-ai, review |
| development | code, git, debug, test, build, refactor, deploy, tdd, commit |
| design | design, ui, ux, frontend, css, layout, theme, canvas |
| tools | tool, utility, package, manager, config, pdf, docx, xlsx |
| plugin-dev | skill, command, agent, hook, plugin, mcp |
| other | (no keyword match) |

### Step 5: Content Hashing

Compute SHA-256 hash of each SKILL.md file content:

```python
content_hash = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
```

### Step 6: Registry Generation

Assemble all entries into registry.json and write atomically (write to .tmp, then rename).

## Command Line Usage

```bash
# Default scan
python3 scripts/bootstrap.py

# Custom skills directory
python3 scripts/bootstrap.py --skills-dir /path/to/skills

# Custom output path
python3 scripts/bootstrap.py --output /path/to/registry.json

# Force rescan (overwrite existing registry)
python3 scripts/bootstrap.py --force
```

## Output Example

```
Bootstrap Scan Summary
======================
Total skills scanned: 104
  - Local (claude-scholar): 32
  - GitHub (baoyu): 17
  - GitHub (community): 41
  - Marketplace: 14

Categories:
  - research: 8
  - writing: 12
  - development: 28
  - design: 10
  - tools: 15
  - plugin-dev: 12
  - other: 19

Registry written to: data/registry.json
```

## Troubleshooting

- **Empty SKILL.md**: Skill is registered with minimal metadata (name from directory, no description)
- **Malformed frontmatter**: Warning is printed, skill registered with what could be parsed
- **Permission errors**: Skill is skipped with warning
- **Duplicate names**: Should not happen (directory names are unique), but warned if detected
