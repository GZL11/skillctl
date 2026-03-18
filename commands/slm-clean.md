---
description: Disable or clean up skills by moving them to the disabled directory.
---

# SLM Clean

Disable or clean up unwanted skills.

## Instructions

1. **Determine Mode**
   - If user specified a skill name: disable that specific skill
   - If user specified `--duplicates`: show duplicates and offer to disable
   - If neither: ask what the user wants to clean

2. **For Specific Skill**
   - Show the skill's registry entry (name, description, source)
   - Confirm with user: "Disable <skill-name>? It will be moved to ~/.claude/skills-disabled/"
   - Run `bash skillctl/scripts/clean.sh "<skill-name>"`

3. **For Duplicates**
   - Run `bash skillctl/scripts/clean.sh --duplicates`
   - Display similarity results
   - For each duplicate pair, recommend which to keep (based on quality score, content richness, recency)
   - Ask user which skills to disable
   - Disable selected skills one by one

4. **Post-Clean**
   - Show summary of disabled skills
   - Mention that disabled skills can be recovered from `~/.claude/skills-disabled/`
   - Suggest running `/slm-status` to verify
