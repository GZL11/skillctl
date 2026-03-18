---
description: List all registered skills with optional category and source filtering.
---

# SLM List

List all skills in the SLM registry with optional filtering.

## Instructions

1. **Check Registry Exists**
   - Check if `skillctl/data/registry.json` exists
   - If not, inform the user and suggest running bootstrap: `python3 skillctl/scripts/bootstrap.py`

2. **Load Registry**
   - Run `python3 skillctl/scripts/registry.py list`
   - If the user specified `--category <name>`, add `--category <name>` flag

3. **Display Results**
   - Format as a markdown table with columns: Name, Category, Source, Version, Updated
   - Group by category if no specific category filter
   - Show total count at the bottom
   - Example:
     ```
     | Name | Category | Source | Version | Updated |
     |------|----------|--------|---------|---------|
     | git-workflow | development | local/claude-scholar | 0.1.0 | 2026-03-18 |
     ```

4. **Additional Options**
   - If user asks for details on a specific skill, run `python3 skillctl/scripts/registry.py get <name>`
   - If user asks about quality scores, mention running skill-quality-reviewer
