# Merge Strategy Reference

## Overview

The skill merge process combines two similar skills into a single, stronger skill. This is executed by the `skill-merger` agent (LLM-driven) with human confirmation at each critical step.

## Merge Algorithm

### Step 1: Decomposition

Both skills are decomposed into semantic sections:

1. **Frontmatter** — YAML metadata (name, description, version, trigger phrases)
2. **Overview** — Introduction and purpose section
3. **Workflow sections** — Numbered or named procedural sections
4. **Reference material** — Links, tables, schemas
5. **Scripts** — Bundled scripts in scripts/
6. **References** — Files in references/
7. **Assets** — Files in assets/

### Step 2: Section Matching

Corresponding sections from both skills are matched by:
- Exact heading match (e.g., "## Installation" <-> "## Installation")
- Semantic similarity of heading text (e.g., "## Getting Started" <-> "## Setup Guide")
- Content overlap analysis for unmatched sections

### Step 3: Section Merging Rules

For each matched section pair:

| Condition | Action |
|-----------|--------|
| One section is empty | Keep the non-empty version |
| Sections are nearly identical (>0.9 similarity) | Keep the longer/more detailed version |
| Sections cover different aspects | Merge content, remove redundancy |
| Sections contradict each other | Flag for human review |

### Step 4: Frontmatter Merge

- **name**: Use the more descriptive name, or propose a new combined name
- **description**: Union of trigger phrases from both skills, deduplicated
- **version**: Bump to next minor version from the higher of the two

### Step 5: Resources Merge

#### references/ files
- Same filename: compare content, keep richer version or merge
- Different filenames: keep both

#### scripts/ files
- Same filename: compare content, keep both with suffix if different (e.g., `validate_a.sh`, `validate_b.sh`)
- Different filenames: keep both

#### assets/ files
- Keep all from both, rename on conflict

### Step 6: Preview and Confirmation

Before applying the merge:
1. Generate a complete preview of the merged SKILL.md
2. List all files that will be created/modified/deleted
3. Show a diff-style comparison
4. Require explicit user confirmation

### Step 7: Execution

1. Create backup of both original skills in `~/.claude/skillctl-backup/`
2. Create the merged skill directory
3. Write merged SKILL.md and copy resources
4. Update registry: add merged entry, remove original entries
5. Optionally disable (not delete) original skills

## Conflict Resolution

When automatic merge is not possible:
- Present both versions side by side
- Ask user to choose or provide manual edit
- Never silently discard content
