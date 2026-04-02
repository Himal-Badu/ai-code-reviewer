# 🤖 AI Code Reviewer

<p align="center">
  <a href="https://github.com/Himal-Badu/ai-code-reviewer"><img src="https://img.shields.io/badge/MIT%20License-purple?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/Himal-Badu/ai-code-reviewer"><img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge" alt="Python"></a>
  <a href="https://github.com/Himal-Badu/ai-code-reviewer/actions"><img src="https://img.shields.io/badge/GitHub%20Actions-Automation-green?style=for-the-badge" alt="CI"></a>
  <a href="https://github.com/Himal-Badu/ai-code-reviewer"><img src="https://img.shields.io/badge/Universal%20AI-OpenAI%20%7C%20Anthropic%20%7C%20Google-orange?style=for-the-badge" alt="AI Providers"></a>
</p>

<p align="center">
  <strong>Multi-agent AI code review tool with cache-aware prompts and background learning.</strong><br>
  Architecture inspired by <a href="https://github.com/instructkr/claw-code">Claude Code's production patterns</a>.
</p>

---

## ⚡ What Is This?

AI Code Reviewer analyzes your codebase for bugs, security vulnerabilities, performance issues, and code quality problems — using AI agents that specialize in each category.

**v2.0 Architecture** (inspired by patterns from the [Claude Code source leak](https://layer5.io/blog/engineering/the-claude-code-source-leak-512000-lines-a-missing-npmignore-and-the-fastest-growing-repo-in-github-history/)):

| Feature | How It Works | Why It Matters |
|---|---|---|
| **Multi-Agent Pipeline** | 4 specialized review stages (security, bugs, performance, style) | Each agent focuses on one thing → more accurate findings |
| **Universal AI Support** | OpenAI, Anthropic, Google — just add your API key | Use whatever AI you already have access to |
| **Cache-Aware Prompts** | Static system prompt first, dynamic file content after | Lower API cost, faster responses |
| **Background Learning** | Records patterns from past reviews, consolidates during idle | Gets smarter on YOUR codebase over time |
| **Parallel Stages** | Review stages run concurrently via ThreadPoolExecutor | 2-4x faster than sequential review |

---

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Set Your API Key (any one of these)

```bash
# OpenAI (GPT-4, GPT-5)
export OPENAI_API_KEY=sk-...

# Anthropic (Claude)
export ANTHROPIC_API_KEY=sk-ant-...

# Google (Gemini)
export GOOGLE_API_KEY=AIza...
```

The tool auto-detects which provider you have configured. Or pick one explicitly:

```bash
python -m src.cli review ./src --provider anthropic
python -m src.cli review ./src --provider google
python -m src.cli review ./src --provider openai
```

### Review a File

```bash
python -m src.cli review path/to/file.py
```

### Review a Directory

```bash
python -m src.cli review ./src
```

---

## 📖 Commands

### `review` — Full Multi-Stage Review

```bash
# All stages (security + bugs + performance + style)
python -m src.cli review ./src

# Only specific stages
python -m src.cli review ./src --stages security,bugs

# JSON output for CI/CD integration
python -m src.cli review ./src --format json

# Markdown report
python -m src.cli review ./src --format markdown -o report.md

# Filter by minimum severity
python -m src.cli review ./src --severity high

# Sequential (not parallel) stages
python -m src.cli review ./src --sequential
```

### `security` — Security-Only Review

```bash
python -m src.cli security ./src
```

Checks for: OWASP Top 10, hardcoded secrets, SQL injection, dangerous functions (eval/exec), unsafe deserialization.

### `bugs` — Bug Detection Only

```bash
python -m src.cli bugs ./src
```

Checks for: logic errors, null dereference risks, unhandled exceptions, edge cases, unreachable code.

### `performance` — Performance Review Only

```bash
python -m src.cli performance ./src
```

Checks for: O(n²) complexity, string concat in loops, unnecessary allocations, N+1 patterns, blocking I/O.

### `style` — Code Quality Review Only

```bash
python -m src.cli style ./src
```

Checks for: naming conventions, function length, DRY violations, unused imports, missing docs, complex nesting.

### `learn` — View Learning Insights

```bash
# View what patterns the tool has learned from your codebase
python -m src.cli learn

# Filter by language
python -m src.cli learn --language python

# Clear learning data
python -m src.cli learn --clear
```

### `stats` — Show Configuration

```bash
python -m src.cli stats
```

---

## 🏗️ Architecture

```
src/
├── cli.py           # CLI entry point (click-based)
├── analyzer.py      # Core analysis logic (static + AI)
├── ai_client.py     # OpenAI client with cache-aware prompts
├── pipeline.py      # Multi-agent stage orchestration
├── learning.py      # Background pattern consolidation
├── models.py        # Data structures (CodeIssue, ReviewStageResult)
├── plugins.py       # Plugin system for custom scanners
├── config.py        # Configuration management
├── cache.py         # File-based result caching
├── reporter.py      # Report generation
└── security.py      # Security-specific checks
```

### How the Multi-Agent Pipeline Works

```
┌─────────────────────────────────────────────────┐
│                   ReviewPipeline                 │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────┐ │
│  │ Security │ │   Bugs   │ │ Perform. │ │Style│ │
│  │  Agent   │ │  Agent   │ │  Agent   │ │Agent│ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬──┘ │
│       │             │            │           │    │
│       └─────────────┴────────────┴───────────┘    │
│                        │                          │
│                   ┌────▼────┐                     │
│                   │ Dedup & │                     │
│                   │  Merge  │                     │
│                   └────┬────┘                     │
│                        │                          │
│                   ┌────▼────┐                     │
│                   │Learning │ ← Record patterns   │
│                   │  Store  │                      │
│                   └─────────┘                     │
└─────────────────────────────────────────────────┘
```

Each agent gets a **focused system prompt** that tells it to ONLY look for issues in its specialty. This produces more accurate results than one giant prompt trying to do everything.

### How Cache-Aware Prompts Work

```python
# STATIC (cached by OpenAI's API) — sent first, same every request
system_prompt = """You are a security specialist...
[1000+ lines of rules, definitions, response format]"""

# DYNAMIC (changes per request) — sent second
user_message = f"""File: {file_name}
Language: python
Code:
```python
{file_content}
```"""
```

The API can cache the static portion, so subsequent reviews for the same stage reuse the cached prompt → **faster and cheaper**.

### How Background Learning Works

```python
learner = ReviewLearner()

# After every review, record what was found
learner.record_review("app.py", issues, "python")

# During idle time, consolidate patterns
learner.consolidate()
# → "hardcoded_secret seen 47x in python projects"
# → Generates custom regex rules to catch them without AI

# Query what's been learned
hot = learner.get_hot_patterns(language="python")
```

---

## 🔧 GitHub Actions Integration

Create `.github/workflows/code-review.yml`:

```yaml
name: AI Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m src.cli review . --format json --severity high
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## 🌐 Supported Languages & Providers

### Languages

| Language | Static Analysis | AI Review |
|---|---|---|
| Python | ✅ AST-based | ✅ |
| JavaScript | — | ✅ |
| TypeScript | — | ✅ |
| Go | — | ✅ |
| Rust | — | ✅ |

### AI Providers

| Provider | Env Variable | Default Model | Status |
|---|---|---|---|
| **OpenAI** | `OPENAI_API_KEY` | `gpt-4o` | ✅ |
| **Anthropic** | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` | ✅ |
| **Google** | `GOOGLE_API_KEY` | `gemini-2.0-flash` | ✅ |

Just set any one API key and the tool auto-detects it. Use `--provider` to override. |

---

## 🧠 The Inspiration

This project's v2 architecture is directly inspired by patterns discovered in the [Claude Code source leak](https://layer5.io/blog/engineering/the-claude-code-source-leak-512000-lines-a-missing-npmignore-and-the-fastest-growing-repo-in-github-history/) (March 31, 2026):

1. **Multi-agent orchestration via prompts, not frameworks** — Claude Code doesn't use LangChain. Neither do we. Each review stage is just a prompt variant + a function call.

2. **Cache-aware prompt boundaries** — Claude Code structures system prompts with API caching in mind. We do the same: static rules first, dynamic content after.

3. **KAIROS autoDream pattern** — Claude Code's autonomous daemon mode includes "autoDream" — background memory consolidation. Our learning module does the same: records observations, consolidates patterns, generates custom rules.

---

## 📊 Example Output

```
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Severity ┃ Type          ┃ File     ┃ Line ┃ Message                       ┃ Suggestion               ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ HIGH     │ security      │ app.py   │   42 │ Potential hardcoded secret    │ Use env vars             │
│ MEDIUM   │ performance   │ utils.py │   88 │ String concat in loop         │ Use join()               │
│ LOW      │ best_practice │ main.py  │   12 │ TODO: add error handling      │ Address the TODO         │
└──────────┴───────────────┴──────────┴──────┴───────────────────────────────┴──────────────────────────┘

📊 Review Summary
Files reviewed: 12
Total issues: 8
By severity:
  HIGH: 2
  MEDIUM: 4
  LOW: 2
Stages: security, bugs, performance, style
```

---

## 🛣️ Roadmap

- [ ] Add Anthropic Claude support (not just OpenAI)
- [ ] Web UI dashboard for review history
- [ ] Custom rule editor (YAML-based)
- [ ] VS Code extension
- [ ] Incremental review (only re-check changed files)
- [ ] Export to SARIF format for GitHub Code Scanning

---

## 📝 License

MIT License — see [LICENSE](LICENSE)

---

## 👤 Author

**Himal Badu** — 16-year-old AI Founder

- 🔗 [LinkedIn](https://www.linkedin.com/in/himal-badu)
- 🐙 [GitHub](https://github.com/Himal-Badu)
- ✉️ himalbaduhimalbadu@gmail.com

---

> *"Architecture is what you see when you look at how something works, not what it looks like."*
