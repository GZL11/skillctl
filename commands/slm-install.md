---
description: Install a skill from a GitHub repository URL.
---

# SLM Install

Install a Claude Code skill from GitHub.

## Instructions

1. **Get GitHub URL**
   - Extract the GitHub URL from user input after `/slm-install`
   - If no URL provided, ask the user for the repository URL
   - Validate URL format (must be a GitHub URL)

2. **Check for Name Conflicts**
   - Load the registry and check if a skill with the same name already exists
   - If conflict found, warn the user and suggest using `/slm-update` instead

3. **Pre-install Similarity Check**

   Before installing, check if the new skill overlaps with existing skills. Use progressive disclosure to minimize overhead:

   **Step A — Name Check**
   - Extract the skill name from the GitHub repo (repo name or SKILL.md frontmatter)
   - Compare against all existing skill names in `~/.claude/skills/`
   - If name tokens overlap with existing skills (e.g., installing `git-release` when `finish-release` exists), flag for deeper check

   **Step B — Frontmatter Comparison** (only if Step A flagged matches)
   - Fetch the new skill's SKILL.md from GitHub (read raw content)
   - Read the frontmatter (name, description, tags) of flagged existing skills
   - Compare descriptions semantically:
     - **High overlap**: Warn user — "Similar skill already installed: `<name>`. Continue / Merge / Cancel?"
     - **Low overlap**: Proceed with installation

   **Step C — User Decision** (only if overlap detected)
   - Present the comparison: new skill description vs existing skill description
   - Options:
     - **Install anyway**: Proceed, both skills will coexist
     - **Merge**: Run `/slm-merge` after installation to combine them
     - **Cancel**: Abort installation

4. **Run Installation**
   - Run `bash skillctl/scripts/install.sh "<github-url>"`
   - Monitor output for errors

5. **Verify Installation**
   - Check that the skill directory was created in `~/.claude/skills/`
   - Verify SKILL.md exists in the new directory
   - Confirm registry was updated

6. **Post-Install**
   - Display the installed skill's metadata (name, description, category)
   - If overlap was detected in Step 3 but user chose "Install anyway", remind them they can run `/slm-merge` later
