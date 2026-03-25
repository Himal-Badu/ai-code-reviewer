"""Notification system for AI Code Reviewer."""

from typing import Dict, Any, List, Optional
from enum import Enum


class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    CONSOLE = "console"


class Notifier:
    """Base notifier class."""
    
    def send(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send notification."""
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """Console notification."""
    
    def send(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send to console."""
        print(f"[NOTIFICATION] {message}")
        if data:
            print(f"Data: {data}")
        return True


class EmailNotifier(Notifier):
    """Email notification."""
    
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, from_addr: str, to_addrs: List[str]):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
    
    def send(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send email notification."""
        # This would use smtplib in production
        print(f"[EMAIL] Would send: {message}")
        return True


class SlackNotifier(Notifier):
    """Slack notification."""
    
    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send(self, message: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send Slack notification."""
        # This would use Slack SDK in production
        print(f"[SLACK] Would send: {message}")
        return True


class NotificationManager:
    """Manage notifications."""
    
    def __init__(self):
        self.notifiers: List[Notifier] = []
    
    def add_notifier(self, notifier: Notifier) -> 'NotificationManager':
        """Add a notifier."""
        self.notifiers.append(notifier)
        return self
    
    def notify(self, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Send notification to all channels."""
        for notifier in self.notifiers:
            try:
                notifier.send(message, data)
            except Exception as e:
                print(f"Notification failed: {e}")
    
    def notify_scan_complete(self, scan_results: Dict[str, Any]) -> None:
        """Notify scan completion."""
        issues = scan_results.get("total_issues", 0)
        message = f"Code review complete. Found {issues} issues."
        self.notify(message, scan_results)
    
    def notify_critical_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Notify about critical issues."""
        message = f"Critical issues found: {len(issues)}"
        self.notify(message, {"issues": issues})


# Global notification manager
_notifier_manager = None


def get_notification_manager() -> NotificationManager:
    """Get global notification manager."""
    global _notifier_manager
    if _notifier_manager is None:
        _notifier_manager = NotificationManager()
    return _notifier_manager