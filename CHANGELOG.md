# Changelog

All notable changes to AI Code Reviewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
