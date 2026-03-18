#!/usr/bin/env bash
set -euo pipefail

# Usage: update.sh [skill-name|--all] [--skills-dir DIR] [--force]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
BACKUP_DIR="${HOME}/.claude/skillctl-backup"
REGISTRY_SCRIPT="${SCRIPT_DIR}/registry.py"
REGISTRY_PATH="${SCRIPT_DIR}/../data/registry.json"

SKILL_NAME=""
UPDATE_ALL=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all) UPDATE_ALL=true; shift ;;
        --skills-dir) SKILLS_DIR="$2"; shift 2 ;;
        --force) FORCE=true; shift ;;
        *) SKILL_NAME="$1"; shift ;;
    esac
done

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

update_skill() {
    local name="$1"
    local github_url="$2"
    local current_sha="$3"
    local install_path="$4"

    # Get latest commit SHA from remote
    local latest_sha
    latest_sha=$(git ls-remote "$github_url" HEAD 2>/dev/null | cut -f1)

    if [[ -z "$latest_sha" ]]; then
        echo "  Warning: Cannot reach $github_url"
        return 1
    fi

    if [[ "$current_sha" == "$latest_sha" ]]; then
        echo "  Already up to date: $name ($current_sha)"
        return 0
    fi

    echo "  Update available: $name"
    echo "    Current: ${current_sha:0:8}"
    echo "    Latest:  ${latest_sha:0:8}"

    if [[ "$FORCE" != "true" ]] && [[ -t 0 ]]; then
        read -r -p "  Update $name? [y/N] " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "  Skipped."
            return 0
        fi
    elif [[ "$FORCE" != "true" ]]; then
        echo "  Non-interactive mode: use --force to auto-confirm"
        return 0
    fi

    # Backup
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/${name}_${timestamp}"
    echo "  Backing up to $backup_path"
    cp -r "$install_path" "$backup_path"

    # Clone and update
    local temp_dir
    temp_dir=$(mktemp -d)

    cleanup_temp() {
        rm -rf "$temp_dir"
    }

    git clone --depth 1 "$github_url" "$temp_dir/repo" 2>/dev/null

    # Find the skill in the cloned repo
    local skill_md
    skill_md=$(find "$temp_dir/repo" -name "SKILL.md" -path "*${name}*" -type f | head -1)
    if [[ -z "$skill_md" ]]; then
        skill_md=$(find "$temp_dir/repo" -name "SKILL.md" -type f | head -1)
    fi

    if [[ -z "$skill_md" ]]; then
        echo "  Error: SKILL.md not found in updated repo"
        cleanup_temp
        return 1
    fi

    local source_dir
    source_dir=$(dirname "$skill_md")

    # Replace skill directory
    rm -rf "$install_path"
    cp -r "$source_dir" "$install_path"

    # Update registry
    if [[ -f "$REGISTRY_SCRIPT" ]]; then
        python3 "$REGISTRY_SCRIPT" update "$name" \
            --commit-sha "$latest_sha"
    fi

    echo "  Updated: $name (${current_sha:0:8} -> ${latest_sha:0:8})"
    cleanup_temp
}

# Get skills to update from registry
if [[ ! -f "$REGISTRY_PATH" ]]; then
    echo "Error: Registry not found at $REGISTRY_PATH"
    echo "Run bootstrap.py first to create the registry."
    exit 1
fi

echo "Checking for updates..."

if [[ "$UPDATE_ALL" == "true" ]] || [[ -n "$SKILL_NAME" ]]; then
    # Parse registry JSON to find github-sourced skills
    REGISTRY_PATH="$REGISTRY_PATH" SKILL_NAME="$SKILL_NAME" UPDATE_ALL="$UPDATE_ALL" python3 -c "
import json, os, sys
registry_path = os.environ['REGISTRY_PATH']
skill_name = os.environ['SKILL_NAME']
update_all = os.environ['UPDATE_ALL']
with open(registry_path) as f:
    reg = json.load(f)
skills = reg.get('skills', {})
for name, info in skills.items():
    src = info.get('source', {})
    if src.get('type') == 'github' and src.get('github_url'):
        if update_all == 'true' or name == skill_name:
            sha = src.get('commit_sha', '')
            url = src.get('github_url', '')
            path = info.get('install_path', '')
            print(f'{name}|{url}|{sha}|{path}')
" | while IFS='|' read -r name url sha path; do
        update_skill "$name" "$url" "$sha" "$path"
    done
else
    echo "Usage: update.sh [skill-name|--all] [--skills-dir DIR] [--force]"
    exit 1
fi

echo "Update check complete."
