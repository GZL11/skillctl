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

3. **Duplicate Detection**
   - Run `python3 skillctl/scripts/similarity.py --skills-dir ~/.claude/skills --threshold 0.5`
   - Display results grouped by severity:
     - Near Identical (≥0.9): Flag as urgent
     - Likely Duplicate (≥0.7): Recommend merge
     - Possible Match (≥0.5): Inform user

4. **Orphan Detection**
   - Compare skill directories on disk vs registry entries
   - Skills on disk but not in registry → "Orphaned" (suggest re-running bootstrap)
   - Skills in registry but not on disk → "Missing" (suggest removal from registry)

5. **Summary**
   - Present a health score summary
   - Suggest actionable next steps (merge duplicates, clean orphans, update outdated)
