---
description: Show registry health status including statistics, duplicates, and orphaned skills.
---

# SLM Status

Display comprehensive health status of the skill registry.

## Instructions

1. **Check Registry Exists**
   - Check if `skillctl/data/registry.json` exists
   - If not, run bootstrap first: `python3 skillctl/scripts/bootstrap.py`

2. **Registry Statistics**
   - Run `python3 skillctl/scripts/registry.py stats`
   - Display: total skills, per-category counts, per-source counts

3. **Duplicate Detection** (progressive disclosure, 3 layers)

   Use a progressive disclosure approach to minimize token usage while maximizing accuracy. Stop at the earliest layer that gives a confident answer for each group.

   **Layer 1 — Name Scan** (~500 tokens)
   - List all skill directory names under `~/.claude/skills/`
   - Group names that share significant tokens (e.g., `finish-release` / `start-release` / `finish-feature` share "release" or "finish")
   - Identify prefix/suffix families (e.g., all `scientific-*` skills, all `baoyu-*` skills)
   - Output: list of suspect groups with reasoning
   - Skills with clearly distinct names and no family pattern → **Dismiss** (no further checking)

   **Layer 2 — Frontmatter Comparison** (~2000 tokens)
   - For each suspect group from Layer 1, read only the YAML frontmatter (first 10 lines) from each skill's SKILL.md
   - Compare: `name`, `description`, `tags`, `version`
   - Make a judgment for each pair:
     - Descriptions describe the same use case → **Likely Duplicate** (proceed to Layer 3 if uncertain)
     - Descriptions clearly different despite similar names → **Dismiss**
     - Descriptions partially overlap → **Flag for Layer 3**

   **Layer 3 — Full Content Deep Dive** (on-demand)
   - Only for pairs still uncertain after Layer 2
   - Read the complete SKILL.md body for both skills
   - Compare: workflow steps, trigger phrases, referenced scripts/tools, section structure
   - Final judgment:
     - **True Duplicate**: Both skills do the same thing → Recommend `/slm-merge`
     - **Functional Overlap**: Partial overlap, each has unique value → Suggest review
     - **False Positive**: Different purposes → Dismiss

   Present results as a table with judgment, pair names, and 1-sentence explanation.

4. **Algorithm Cross-check** (optional, for completeness)
   - Run `python3 skillctl/scripts/similarity.py --skills-dir ~/.claude/skills --threshold 0.5 --detailed`
   - Check if the algorithm found any pairs your LLM analysis missed
   - If so, run Layer 2-3 on those additional pairs

5. **Orphan Detection**
   - Compare skill directories on disk vs registry entries
   - Skills on disk but not in registry → "Orphaned" (suggest re-running bootstrap)
   - Skills in registry but not on disk → "Missing" (suggest removal from registry)

6. **Summary**
   - Present a health score summary
   - Suggest actionable next steps (merge duplicates, clean orphans, update outdated)
