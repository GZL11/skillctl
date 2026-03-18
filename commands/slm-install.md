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

2. **Check for Conflicts**
   - Load the registry and check if a skill with the same name already exists
   - If conflict found, warn the user and suggest using `/slm-update` instead

3. **Run Installation**
   - Run `bash skillctl/scripts/install.sh "<github-url>"`
   - Monitor output for errors

4. **Verify Installation**
   - Check that the skill directory was created in `~/.claude/skills/`
   - Verify SKILL.md exists in the new directory
   - Confirm registry was updated

5. **Post-Install**
   - Display the installed skill's metadata (name, description, category)
   - Suggest running `/slm-status` to check for duplicates with existing skills
