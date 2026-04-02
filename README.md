# 🤖 AI Code Reviewer

<p align="center">
  <a href="https://github.com/Himal-Badu/ai-code-reviewer">
    <img src="https://img.shields.io/badge/MIT License-purple?style=for-the-badge" alt="License">
  </a>
  <a href="https://github.com/Himal-Badu/ai-code-reviewer">
    <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge" alt="Python">
  </a>
  <a href="https://github.com/Himal-Badu/ai-code-reviewer">
    <img src="https://img.shields.io/badge/GitHub Actions-Automation-green?style=for-the-badge" alt="GitHub Actions">
  </a>
  <a href="https://github.com/Himal-Badu/ai-code-reviewer">
    <img src="https://img.shields.io/badge/OpenAI-GPT--5-orange?style=for-the-badge" alt="OpenAI">
  </a>
</p>

> ⚡ AI-powered code review tool that catches bugs, security issues, and code quality problems before they reach production.

## ✨ Features

- 🔍 **Static Analysis** - Detect hardcoded secrets, dangerous functions, and common bugs
- 🤖 **AI-Powered Review** - Uses OpenAI GPT-4 for intelligent code analysis
- 🛡️ **Security Scanning** - OWASP Top 10 compliance checks with Bandit integration
- 🌐 **Multi-Language** - Python, JavaScript, TypeScript, Go, Rust support
- ⚡ **GitHub Actions** - Automatic PR reviews with comment automation
- 📊 **Rich Output** - Multiple output formats (JSON, Markdown, Text)
- 🎯 **Configurable** - Severity thresholds, custom rules, API key management

## 🚀 Quick Start

### Installation

```bash
pip install ai-code-reviewer
```

### Basic Usage

```bash
# Review a single file
ai-code-reviewer review path/to/file.py

# Review a directory
ai-code-reviewer review ./src

# With specific output format
ai-code-reviewer review ./src --output markdown

# Filter by severity
ai-code-reviewer review ./src --severity high

# Security scan only
ai-code-reviewer security ./src
```

### GitHub Actions Setup

```bash
# Generate GitHub Action workflow
ai-code-reviewer setup
```

Then add your OpenAI API key as a secret (`OPENAI_API_KEY`) in your repository.

## 📖 Usage Examples

### CLI Commands

```bash
# Review with custom language
ai-code-reviewer review app.py --language python

# JSON output for automation
ai-code-reviewer review ./ --output json > review.json

# Configure API key
ai-code-reviewer configure --api-key your-key-here --model gpt-4
```

### Environment Variables

```bash
export OPENAI_API_KEY=sk-...
ai-code-reviewer review ./src
```

### Python API

```python
from src.analyzer import CodeAnalyzer
from src.ai_client import AIClient
from src.config import Config

config = Config(api_key="your-api-key")
ai_client = AIClient(config)
analyzer = CodeAnalyzer(ai_client)

results = analyzer.analyze_file("path/to/file.py")
print(results)
```

## 🔧 Configuration

| Option | Environment Variable | Description |
|--------|---------------------|-------------|
| `--api-key` | `OPENAI_API_KEY` | OpenAI API key |
| `--model` | - | AI model (default: gpt-4) |
| `--severity` | - | Minimum severity (all/high/medium/low) |
| `--output` | - | Output format (text/json/markdown) |

## 📁 Project Structure

```
ai-code-reviewer/
├── src/
│   ├── __init__.py       # Package initialization
│   ├── analyzer.py       # Core analysis logic
│   ├── ai_client.py      # OpenAI integration
│   ├── security.py      # Security scanning
│   ├── formatter.py     # Output formatting
│   └── config.py        # Configuration management
├── tests/               # Test suite
├── .github/workflows/   # GitHub Actions
├── pyproject.toml       # Package configuration
└── README.md           # This file
```

## 🛡️ Security Checks

The tool checks for:

- **Hardcoded Secrets** - Passwords, API keys, tokens
- **SQL Injection** - Unsanitized queries
- **XSS Vulnerabilities** - Dangerous HTML injection
- **Weak Cryptography** - MD5, SHA1 usage
- **Dangerous Functions** - eval(), exec()
- **Empty Exception Blocks** - Silent failures
- **OWASP Top 10** - Comprehensive vulnerability coverage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest tests/`
5. Submit a pull request

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built by Himal Badu, AI Founder** 🤖

[GitHub](https://github.com/Himal-Badu) • [LinkedIn](https://linkedin.com/in/himalbadu)

</div>

## 🔧 Configuration

### Environment Variables

```bash
export OPENAI_API_KEY="your-api-key"
export AI_REVIEWER_SEVERITY="medium"  # low, medium, high
export AI_REVIEWER_LANGUAGES="python,javascript"
```

### Config File

Create `.ai-reviewer.yml` in your project root:

```yaml
severity: medium
languages:
  - python
  - javascript
  - typescript
exclude:
  - node_modules
  - __pycache__
  - .git
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📊 Stats

![GitHub Stars](https://img.shields.io/github/stars/Himal-Badu/ai-code-reviewer)
![GitHub Forks](https://img.shields.io/github/forks/Himal-Badu/ai-code-reviewer)
![GitHub Issues](https://img.shields.io/github/issues/Himal-Badu/ai-code-reviewer)
![GitHub License](https://img.shields.io/github/license/Himal-Badu/ai-code-reviewer)
