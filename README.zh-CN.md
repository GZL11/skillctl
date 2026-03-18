# skillctl

[**English**](README.md) | **中文**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-green.svg)](https://www.python.org)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-blueviolet.svg)](https://docs.anthropic.com/en/docs/claude-code)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-brightgreen.svg)](#要求)

Claude Code 技能包管理器 — 搜索、安装、更新、去重、合并与清理。

## 什么是 skillctl？

当你深度使用 Claude Code 时，技能会从多个来源不断积累 — 自己编写的、社区贡献的、从市场安装的 — 却没有办法追踪它们的来源、检测重复项或管理更新。**skillctl** 通过提供集中式注册表和完整的生命周期管理来解决这个问题。

```
                search → install → status → update
                                     ↓
                              detect duplicates
                                     ↓
                               merge → clean
```

## 功能特性

| 功能 | 说明 |
|------|------|
| **集中式注册表** | 追踪每个技能的来源、版本、内容哈希和分类 |
| **引导扫描** | 自动检测 100+ 个现有技能并构建注册表 |
| **重复检测** | 多信号相似度分析（TF-IDF + frontmatter + 结构 + 名称）识别重叠技能 |
| **GitHub 搜索** | 直接在 Claude Code 中从 GitHub 查找新技能 |
| **安装与更新** | 一条命令从 GitHub 安装，并跟踪版本 |
| **智能合并** | 由 LLM 驱动的语义合并相似技能 |
| **清理与禁用** | 安全禁用技能（可恢复，移至 disabled 目录） |

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/GZL11/skillctl.git
```

### 2. 启用为 Claude Code 插件

添加到你的 `~/.claude/settings.json`：

```json
{
  "enabledPlugins": {
    "skillctl@local": true
  }
}
```

如果你希望仅在项目范围内生效，也可以添加到项目的 `.claude/settings.json`。

### 3. 引导初始化（首次使用）

启动 Claude Code 并运行：

```
/slm-status
```

系统会检测到注册表尚未初始化，并自动运行引导扫描。也可以手动执行：

```bash
python3 /path/to/skillctl/scripts/bootstrap.py --skills-dir ~/.claude/skills
```

## 命令

### `/slm-list` — 列出所有技能

```
/slm-list                    # 列出所有技能
/slm-list --category research  # 按分类筛选
/slm-list --source-type github # 按来源筛选
```

### `/slm-status` — 健康检查

显示注册表统计信息、重复检测结果以及孤立技能警告。

```
/slm-status
```

### `/slm-search` — 搜索技能

通过关键词搜索本地注册表和 GitHub 上的技能。

```
/slm-search "paper writing"
/slm-search "git" --local-only
```

### `/slm-install` — 从 GitHub 安装

```
/slm-install https://github.com/user/skill-repo
```

### `/slm-update` — 更新技能

```
/slm-update my-skill         # 更新单个技能
/slm-update --all            # 更新所有来自 GitHub 的技能
```

### `/slm-merge` — 合并重复项

调用 `skill-merger` agent 进行 LLM 驱动的语义合并。

```
/slm-merge skill-a skill-b
```

### `/slm-clean` — 禁用技能

```
/slm-clean unused-skill      # 禁用单个技能
/slm-clean --duplicates      # 审查并禁用重复技能
```

## 使用示例

安装后的典型工作流：

```
# 1. 首次运行 — 初始化注册表并进行健康检查
/slm-status
#    → 扫描 ~/.claude/skills/，发现 101 个技能
#    → 检测到 3 对可能的重复项
#    → 显示分类分布

# 2. 调查重复项
/slm-list --category development
#    → 列出所有开发类技能及其来源和版本

# 3. 合并相似技能
/slm-merge finish-release start-release
#    → skill-merger agent 分析两个技能
#    → 生成合并预览供你确认
#    → 备份原始文件，创建合并后的技能

# 4. 搜索新技能
/slm-search "tdd"
#    → 本地：2 个匹配
#    → GitHub：找到 5 个仓库

# 5. 从 GitHub 安装
/slm-install https://github.com/user/claude-tdd-pro
#    → 克隆仓库，安装到 ~/.claude/skills/，注册到注册表

# 6. 之后 — 检查更新
/slm-update --all
#    → 比较 commit SHA，显示可用更新
#    → 更新前备份旧版本

# 7. 清理不用的技能
/slm-clean unused-skill
#    → 移至 ~/.claude/skills-disabled/（可恢复）
```

你也可以不通过 Claude Code，直接使用脚本：

```bash
# 引导扫描 — 扫描并构建注册表
python3 scripts/bootstrap.py --skills-dir ~/.claude/skills

# 查看注册表统计
python3 scripts/registry.py stats

# 查找重复项
python3 scripts/similarity.py --skills-dir ~/.claude/skills --threshold 0.5

# 本地搜索
python3 scripts/search.py "git" --local-only

# 从 GitHub 安装
bash scripts/install.sh https://github.com/user/skill-repo
```

## 架构

```
skillctl/
├── .claude-plugin/
│   └── marketplace.json         # 插件清单
├── skills/
│   └── skillctl/
│       ├── SKILL.md             # 主技能（由 Claude 自动触发）
│       └── references/          # 详细文档
│           ├── registry-schema.md
│           ├── merge-strategy.md
│           └── bootstrap-guide.md
├── commands/                    # 7 个斜杠命令
│   ├── slm-list.md
│   ├── slm-status.md
│   ├── slm-search.md
│   ├── slm-install.md
│   ├── slm-update.md
│   ├── slm-merge.md
│   └── slm-clean.md
├── agents/                      # 2 个专用 agent
│   ├── skill-merger.md          # 智能技能合并
│   └── skill-auditor.md         # 质量审计与健康检查
├── scripts/                     # 核心脚本（零依赖）
│   ├── registry.py              # 注册表 CRUD 操作
│   ├── bootstrap.py             # 初始技能扫描
│   ├── search.py                # GitHub + 本地搜索
│   ├── similarity.py            # 多信号重复检测
│   ├── install.sh               # Git clone 与安装
│   ├── update.sh                # 版本更新
│   └── clean.sh                 # 禁用与清理
└── data/
    └── registry.json            # 运行时生成
```

## 注册表 Schema

每个技能条目包含以下信息：

```json
{
  "name": "git-workflow",
  "description": "...",
  "version": "1.2.0",
  "source": {
    "type": "local",
    "origin": "claude-scholar",
    "github_url": null,
    "commit_sha": null
  },
  "install_path": "~/.claude/skills/git-workflow",
  "installed_at": "2026-03-18T12:00:00Z",
  "updated_at": "2026-03-18T12:00:00Z",
  "category": "development",
  "tags": ["Git", "Workflow"],
  "quality_score": null,
  "content_hash": "sha256:abc123..."
}
```

来源类型：`local`（自行编写）、`github`（社区贡献）、`marketplace`（官方/第三方市场）。

## 要求

- Python >= 3.8（仅使用标准库，零外部依赖）
- Git >= 2.0
- Claude Code

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feature/my-feature`）
3. 使用 Conventional Commits 提交（`feat:`、`fix:`、`docs:` 等）
4. 发起 Pull Request

## 许可证

[MIT](LICENSE)
