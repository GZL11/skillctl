---
description: Search for skills by keyword in local registry and GitHub.
---

# SLM Search

Search for Claude Code skills by keyword.

## Instructions

1. **Get Search Keyword**
   - Extract the keyword from user input after `/slm-search`
   - If no keyword provided, ask the user what they want to search for

2. **Run Search**
   - Run `python3 skillctl/scripts/search.py "<keyword>"`
   - This searches both the local registry and GitHub

3. **Display Results**
   - Show local matches first, then GitHub matches
   - Format as a numbered list with source indicator:
     ```
     Local Results:
     1. [local] git-workflow — Git workflow standards...
     2. [local] config-git — Git configuration...

     GitHub Results:
     3. [github] user/claude-git ★42 — Advanced git skills...
     4. [github] user/git-tools ★15 — Git utility skills...
     ```

4. **Offer Actions**
   - For GitHub results, offer to install: "Would you like to install any of these? Use `/slm-install <url>`"
   - For local results, offer to view details: "Use `/slm-list` to see full details"
