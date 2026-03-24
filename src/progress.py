"""Progress tracking for analysis operations."""

import time
import logging
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ProgressItem:
    """Represents a single progress item."""
    name: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message: str = ""
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get the duration of this item."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


class ProgressTracker:
    """Track progress of analysis operations."""
    
    def __init__(self):
        """Initialize the progress tracker."""
        self.items: List[ProgressItem] = []
        self.current: Optional[ProgressItem] = None
        self.start_time = datetime.now()
        logger.debug("Progress tracker initialized")
    
    def start(self, name: str, message: str = ""):
        """Start tracking a new item.
        
        Args:
            name: Name of the item
            message: Optional message
        """
        item = ProgressItem(
            name=name,
            status="running",
            start_time=datetime.now(),
            message=message,
        )
        self.items.append(item)
        self.current = item
        logger.info(f"Started: {name}")
    
    def complete(self, message: str = ""):
        """Mark the current item as completed.
        
        Args:
            message: Optional completion message
        """
        if self.current:
            self.current.status = "completed"
            self.current.end_time = datetime.now()
            self.current.message = message or "Completed"
            logger.info(f"Completed: {self.current.name} ({self.current.duration})")
            self.current = None
    
    def fail(self, message: str = ""):
        """Mark the current item as failed.
        
        Args:
            message: Failure message
        """
        if self.current:
            self.current.status = "failed"
            self.current.end_time = datetime.now()
            self.current.message = message or "Failed"
            logger.error(f"Failed: {self.current.name} - {message}")
            self.current = None
    
    def skip(self, message: str = ""):
        """Skip the current item.
        
        Args:
            message: Skip reason
        """
        if self.current:
            self.current.status = "skipped"
            self.current.end_time = datetime.now()
            self.current.message = message or "Skipped"
            logger.info(f"Skipped: {self.current.name}")
            self.current = None
    
    def update(self, message: str):
        """Update the current item's message.
        
        Args:
            message: Update message
        """
        if self.current:
            self.current.message = message
            logger.debug(f"Update: {self.current.name} - {message}")
    
    def get_progress(self) -> dict:
        """Get progress summary.
        
        Returns:
            Dictionary with progress information
        """
        total = len(self.items)
        completed = sum(1 for i in self.items if i.status == "completed")
        failed = sum(1 for i in self.items if i.status == "failed")
        skipped = sum(1 for i in self.items if i.status == "skipped")
        running = sum(1 for i in self.items if i.status == "running")
        
        elapsed = datetime.now() - self.start_time
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "elapsed_seconds": elapsed.total_seconds(),
            "current": self.current.name if self.current else None,
        }
    
    def get_items(self) -> List[ProgressItem]:
        """Get all progress items.
        
        Returns:
            List of progress items
        """
        return self.items.copy()
    
    def is_complete(self) -> bool:
        """Check if all items are complete.
        
        Returns:
            True if all items have been processed (completed, failed, or skipped)
        """
        if not self.items:
            return False
        return all(
            i.status in ["completed", "failed", "skipped"]
            for i in self.items
        )
    
    def has_failures(self) -> bool:
        """Check if any items failed.
        
        Returns:
            True if any items failed
        """
        return any(i.status == "failed" for i in self.items)
    
    def reset(self):
        """Reset the tracker."""
        self.items = []
        self.current = None
        self.start_time = datetime.now()
        logger.info("Progress tracker reset")
    
    def get_summary(self) -> str:
        """Get a text summary of progress.
        
        Returns:
            Progress summary as string
        """
        progress = self.get_progress()
        
        summary = f"""Progress: {progress['completed']}/{progress['total']} completed
Elapsed: {progress['elapsed_seconds']:.1f}s
Failed: {progress['failed']}
Skipped: {progress['skipped']}
"""
        
        if progress['current']:
            summary += f"Current: {progress['current']}\n"
        
        return summary