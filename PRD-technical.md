# AI Code Reviewer - Technical Specification

## Project Overview
- **Name:** AI Code Reviewer
- **Type:** CLI Tool + GitHub Action
- **Core Functionality:** Analyze code using AI to detect bugs, security vulnerabilities, code smells, and provide optimization suggestions
- **Target Users:** Developers, DevOps engineers, open source maintainers

## Technology Stack
- **Language:** Python 3.9+
- **AI:** OpenAI GPT-4 API (or local LLM fallback)
- **CLI:** Click framework
- **GitHub Integration:** PyGithub library
- **Code Analysis:** AST parsing with `ast` module
- **Security Scanning:** Bandit for Python security issues

## Core Features

### 1. Local CLI Review
- Accept file path or directory as input
- Support multiple languages (Python, JavaScript, TypeScript, Go, Rust)
- Output formatted review results
- Configurable severity levels

### 2. GitHub Action Integration
- Trigger on pull requests
- Post review comments automatically
- Support for multiple AI models
- Rate limit handling

### 3. Security Scanning
- Integrate with Bandit for Python
- Detect common vulnerabilities (SQL injection, XSS, hardcoded secrets)
- OWASP Top 10 compliance checks

### 4. Code Quality Checks
- Cyclomatic complexity analysis
- Duplicate code detection
- Naming convention validation
- Import/order checks

### 5. Learning Mode
- Explain why issues were flagged
- Suggest resources for improvement
- Code examples for fixes

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   User      │────▶│  CLI/Action  │────▶│   AI Core   │
│  (Input)    │     │   (Entry)    │     │  (Analysis) │
└─────────────┘     └──────────────┘     └─────────────┘
                                               │
                    ┌──────────────┐           │
                    │   Output     │◀──────────┘
                    │ (Review JSON │
                    │    /Markdown)│
                    └──────────────┘
```

## API Design

### CLI Commands
```bash
ai-code-reviewer review <file_or_dir> [--language] [--severity] [--output-format]
ai-code-reviewer setup --github-action
ai-code-reviewer configure --api-key <key> --model <model>
```

### GitHub Action
- `on: [pull_request, push]`
- Inputs: `api-key`, `model`, `paths-ignore`, `severity-threshold`
- Outputs: Review comment on PR

## File Structure
```
ai-code-reviewer/
├── src/
│   ├── __init__.py
│   ├── cli.py          # Click CLI entrypoint
│   ├── analyzer.py     # Core analysis logic
│   ├── ai_client.py    # OpenAI integration
│   ├── security.py     # Security scanning
│   └── formatter.py    # Output formatting
├── tests/
│   ├── test_analyzer.py
│   ├── test_ai_client.py
│   └── test_security.py
├── .github/
│   └── workflows/
│       └── review.yml
├── pyproject.toml
├── README.md
└── LICENSE
```

## Acceptance Criteria
1. CLI accepts file/directory and outputs review
2. GitHub Action posts comments on PRs
3. Security scanner detects OWASP Top 10 issues
4. Supports Python, JavaScript, TypeScript
5. All tests pass
6. README with clear usage instructions
7. MIT License

---

*Built by Himal Badu, AI Founder*