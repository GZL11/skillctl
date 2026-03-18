---
description: Update installed skills from their GitHub sources.
---

# SLM Update

Check for and apply updates to GitHub-sourced skills.

## Instructions

1. **Determine Scope**
   - If user specified a skill name: update that skill only
   - If user specified `--all`: update all GitHub-sourced skills
   - If neither: show list of GitHub-sourced skills and ask what to update

2. **Run Update Check**
   - For single skill: `bash skillctl/scripts/update.sh "<skill-name>"`
   - For all: `bash skillctl/scripts/update.sh --all`
   - The script compares commit SHAs and shows what's changed

3. **Confirm Updates**
   - Show the user which skills have updates available
   - Display current vs latest commit SHA
   - Ask for confirmation before applying

4. **Apply Updates**
   - If confirmed, the script backs up old versions and applies updates
   - Run with `--force` flag if user explicitly confirms

5. **Post-Update**
   - Show summary of what was updated
   - Suggest running `/slm-status` to verify
