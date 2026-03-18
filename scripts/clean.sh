#!/usr/bin/env bash
set -euo pipefail

# Usage: clean.sh <skill-name|--duplicates> [--skills-dir DIR] [--dry-run]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
DISABLED_DIR="${SKILLS_DIR}-disabled"
REGISTRY_SCRIPT="${SCRIPT_DIR}/registry.py"
SIMILARITY_SCRIPT="${SCRIPT_DIR}/similarity.py"

SKILL_NAME=""
CLEAN_DUPLICATES=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --duplicates) CLEAN_DUPLICATES=true; shift ;;
        --skills-dir) SKILLS_DIR="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) SKILL_NAME="$1"; shift ;;
    esac
done

mkdir -p "$DISABLED_DIR"

disable_skill() {
    local name="$1"
    local skill_path="${SKILLS_DIR}/${name}"

    if [[ ! -d "$skill_path" ]]; then
        echo "Error: Skill '$name' not found at $skill_path"
        return 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would disable: $name -> $DISABLED_DIR/$name"
        return 0
    fi

    echo "Disabling skill: $name"
    mv "$skill_path" "${DISABLED_DIR}/${name}"

    # Update registry
    if [[ -f "$REGISTRY_SCRIPT" ]]; then
        python3 "$REGISTRY_SCRIPT" remove "$name"
    fi

    echo "Disabled: $name (moved to $DISABLED_DIR/$name)"
}

if [[ "$CLEAN_DUPLICATES" == "true" ]]; then
    echo "Running similarity detection..."
    python3 "$SIMILARITY_SCRIPT" --skills-dir "$SKILLS_DIR" --threshold 0.7
    echo ""
    echo "Review the duplicates above and use:"
    echo "  clean.sh <skill-name> to disable specific skills"
elif [[ -n "$SKILL_NAME" ]]; then
    disable_skill "$SKILL_NAME"
else
    echo "Usage: clean.sh <skill-name|--duplicates> [--skills-dir DIR] [--dry-run]"
    exit 1
fi
