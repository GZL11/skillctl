# Registry Schema Reference

## File: `data/registry.json`

The registry is a JSON file with the following top-level structure:

### Top-Level Schema

| Field | Type | Description |
|-------|------|-------------|
| `$schema` | string | Schema version identifier. Always `"slm-registry-v1"` |
| `generated_at` | string | ISO 8601 timestamp of last generation/update |
| `skills` | object | Map of skill name to SkillEntry |
| `categories` | object | Map of category name to list of skill names |
| `sources` | object | Map of source origin to SourceSummary |

### SkillEntry Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Skill directory name (kebab-case) |
| `description` | string | yes | From SKILL.md YAML frontmatter |
| `version` | string | no | Semantic version from frontmatter (default: "0.0.0") |
| `source` | SourceInfo | yes | Origin and tracking information |
| `install_path` | string | yes | Absolute path to skill directory |
| `installed_at` | string | yes | ISO 8601 timestamp of first installation |
| `updated_at` | string | yes | ISO 8601 timestamp of last update |
| `category` | string | yes | One of: research, writing, development, design, tools, plugin-dev, other |
| `tags` | array[string] | no | Tag list from frontmatter or inferred |
| `quality_score` | number|null | no | Score from skill-quality-reviewer (0-100) |
| `content_hash` | string | yes | SHA-256 hash of SKILL.md content, prefixed with "sha256:" |

### SourceInfo Schema

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | One of: "local", "github", "marketplace" |
| `origin` | string | Source identifier (e.g., "claude-scholar", "baoyu", "anthropic") |
| `github_url` | string|null | GitHub repository URL (for github/marketplace types) |
| `commit_sha` | string|null | Git commit SHA of installed version |

### Category Definitions

| Category | Description | Keyword Indicators |
|----------|-------------|-------------------|
| `research` | Research ideation, literature review, citation | research, paper, citation, literature, ideation |
| `writing` | Paper writing, documentation, content creation | writing, paper, document, latex, markdown |
| `development` | Code development, testing, debugging | code, git, debug, test, build, refactor, deploy |
| `design` | UI/UX, visual design, frontend | design, ui, ux, frontend, css, layout |
| `tools` | Utilities, package managers, automation | tool, utility, package, manager, config |
| `plugin-dev` | Plugin/skill/command/agent development | skill, command, agent, hook, plugin, mcp |
| `other` | Uncategorized skills | (default) |

### Example Entry

```json
{
  "git-workflow": {
    "name": "git-workflow",
    "description": "Git workflow standards (Conventional Commits, branch management)",
    "version": "0.1.0",
    "source": {
      "type": "local",
      "origin": "claude-scholar",
      "github_url": null,
      "commit_sha": null
    },
    "install_path": "/root/.claude/skills/git-workflow",
    "installed_at": "2026-03-18T12:00:00Z",
    "updated_at": "2026-03-18T12:00:00Z",
    "category": "development",
    "tags": ["Git", "Workflow", "Conventional Commits"],
    "quality_score": null,
    "content_hash": "sha256:a1b2c3d4e5f6..."
  }
}
```
