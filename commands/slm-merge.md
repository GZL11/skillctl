---
description: Intelligently merge two similar skills into one using the skill-merger agent.
---

# SLM Merge

Merge two similar or duplicate skills into a single, stronger skill.

## Instructions

1. **Get Skill Names**
   - Extract two skill names from user input: `/slm-merge <skill-a> <skill-b>`
   - If not provided, run similarity detection and suggest pairs to merge

2. **Validate Skills Exist**
   - Check both skills exist in registry and on disk
   - Read both SKILL.md files for context

3. **Run Similarity Check**
   - Run `python3 skillctl/scripts/similarity.py --skills-dir ~/.claude/skills --threshold 0.3`
   - Confirm the two skills are related enough to merge
   - If similarity < 0.3, warn user that skills may be too different to merge

4. **Invoke Skill Merger Agent**
   - Use the Task tool to invoke the `skill-merger` agent
   - Pass both skill paths and their content as context
   - The agent will decompose, match sections, and produce a merged version

5. **Preview**
   - Display the merged SKILL.md preview to the user
   - List all files that will be created/modified
   - Ask for explicit confirmation

6. **Execute Merge**
   - Back up both originals to `~/.claude/skillctl-backup/`
   - Create the merged skill directory
   - Update registry (add merged, remove originals)
   - Confirm completion
