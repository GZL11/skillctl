#!/usr/bin/env bash
set -euo pipefail

# Usage: install.sh <github-url> [--skills-dir DIR]
# Example: install.sh https://github.com/user/my-skill

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
REGISTRY_SCRIPT="${SCRIPT_DIR}/registry.py"

# Parse arguments
GITHUB_URL=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --skills-dir) SKILLS_DIR="$2"; shift 2 ;;
        *) GITHUB_URL="$1"; shift ;;
    esac
done

# Validate URL
if [[ -z "$GITHUB_URL" ]]; then
    echo "Error: GitHub URL is required"
    echo "Usage: install.sh <github-url> [--skills-dir DIR]"
    exit 1
fi

if [[ ! "$GITHUB_URL" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$ ]]; then
    echo "Error: URL must be a GitHub repository URL (https://github.com/user/repo)"
    exit 1
fi

# Extract repo name
REPO_NAME=$(basename "$GITHUB_URL" .git)

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "Cloning $GITHUB_URL..."
CLONE_OUTPUT=$(git clone --depth 1 "$GITHUB_URL" "$TEMP_DIR/$REPO_NAME" 2>&1) || {
    echo "Error: Failed to clone repository"
    echo "$CLONE_OUTPUT"
    exit 1
}

# Find SKILL.md files
SKILL_FILES=$(find "$TEMP_DIR/$REPO_NAME" -name "SKILL.md" -type f)
if [[ -z "$SKILL_FILES" ]]; then
    echo "Error: No SKILL.md found in repository"
    exit 1
fi

# Install each skill found
while IFS= read -r skill_file; do
    SKILL_DIR=$(dirname "$skill_file")
    SKILL_NAME=$(basename "$SKILL_DIR")

    # Handle case where SKILL.md is in repo root
    if [[ "$SKILL_NAME" == "$REPO_NAME" ]]; then
        SKILL_NAME="$REPO_NAME"
    fi

    TARGET_DIR="${SKILLS_DIR}/${SKILL_NAME}"

    if [[ -d "$TARGET_DIR" ]]; then
        echo "Warning: Skill '$SKILL_NAME' already exists at $TARGET_DIR"
        echo "Use update.sh to update existing skills"
        continue
    fi

    echo "Installing skill: $SKILL_NAME -> $TARGET_DIR"

    # If SKILL.md is in repo root, selectively copy only skill-related files
    if [[ "$SKILL_DIR" == "$TEMP_DIR/$REPO_NAME" ]]; then
        mkdir -p "$TARGET_DIR"
        cp "$SKILL_DIR/SKILL.md" "$TARGET_DIR/"
        for subdir in references scripts assets; do
            if [[ -d "$SKILL_DIR/$subdir" ]]; then
                cp -r "$SKILL_DIR/$subdir" "$TARGET_DIR/"
            fi
        done
    else
        cp -r "$SKILL_DIR" "$TARGET_DIR"
    fi

    # Get commit SHA
    COMMIT_SHA=$(git -C "$TEMP_DIR/$REPO_NAME" rev-parse HEAD)

    # Register in registry
    if [[ -f "$REGISTRY_SCRIPT" ]]; then
        ORIGIN=$(echo "$GITHUB_URL" | sed -E 's|https://github.com/([^/]+)/.*|\1|')
        python3 "$REGISTRY_SCRIPT" add "$SKILL_NAME" \
            --install-path "$TARGET_DIR" \
            --source-type github \
            --origin "$ORIGIN" \
            --github-url "$GITHUB_URL" \
            --commit-sha "$COMMIT_SHA"
    fi

    echo "Successfully installed: $SKILL_NAME"
done <<< "$SKILL_FILES"
