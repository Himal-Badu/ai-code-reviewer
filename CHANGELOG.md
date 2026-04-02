# Changelog

All notable changes to AI Code Reviewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.0] - 2026-04-02

### Added
- **Multi-agent review pipeline** — 4 specialized stages (security, bugs, performance, style)
- **Cache-aware prompt architecture** — static/dynamic prompt separation for lower API cost
- **Background learning system** — KAIROS-inspired pattern consolidation and custom rule generation
- Parallel stage execution via ThreadPoolExecutor
- Cross-stage issue deduplication
- New CLI commands: `security`, `bugs`, `performance`, `style`, `learn`
- JSON and Markdown output formats
- Severity filtering (`--severity high`)
- Stage selection (`--stages security,bugs`)
- Learning insights dashboard (`ai-reviewer learn`)

### Changed
- Rewrote `ai_client.py` with cache-aware prompt layers
- Integrated pipeline and learning into `analyzer.py`
- Upgraded CLI with Rich panels and better formatting
- Updated README with full architecture documentation

### Fixed
- `ast.Exec`/`ast.Eval` usage (removed in Python 3) — now uses ast.Call detection
- Missing `CodeIssue` dataclass in models.py
- JSON output mixed with console messages

### Architecture
Inspired by patterns from the [Claude Code source leak](https://layer5.io/blog/engineering/the-claude-code-source-leak-512000-lines-a-missing-npmignore-and-the-fastest-growing-repo-in-github-history/) (March 31, 2026).

## [1.1.0] - 2026-03-30

### Added
- GitHub issue templates (bug report, feature request)
- Pull request template
- CHANGELOG.md for tracking changes
- Enhanced CI workflow with multi-Python testing

### Changed
- Improved project structure documentation

## [1.0.0] - 2026-03-25

### Added
- Initial release
- Static analysis engine for detecting hardcoded secrets, dangerous functions
- AI-powered code review using OpenAI GPT-4
- Security scanning with OWASP Top 10 compliance
- Multi-language support (Python, JavaScript, TypeScript, Go, Rust)
- GitHub Actions integration for automatic PR reviews
- Multiple output formats (JSON, Markdown, Text)
- Configurable severity thresholds and custom rules
- Rate limiting and caching for API efficiency
- Comprehensive test suite
- Rich CLI interface with progress indicators

### Security
- API key validation and secure storage
- Input sanitization for all user inputs
- Rate limiting to prevent abuse
