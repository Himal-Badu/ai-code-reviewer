"""Tests for the progress tracking module."""

import pytest
import time
from src.progress import ProgressTracker, ProgressItem


class TestProgressTracker:
    """Test cases for ProgressTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create a progress tracker instance."""
        return ProgressTracker()
    
    def test_tracker_initializes(self, tracker):
        """Test that tracker initializes correctly."""
        assert tracker is not None
        assert len(tracker.items) == 0
        assert tracker.current is None
    
    def test_start_item(self, tracker):
        """Test starting a new item."""
        tracker.start("test-item", "Starting test")
        
        assert tracker.current is not None
        assert tracker.current.name == "test-item"
        assert tracker.current.status == "running"
    
    def test_complete_item(self, tracker):
        """Test completing an item."""
        tracker.start("test-item")
        tracker.complete("Finished")
        
        assert tracker.current is None
        assert len(tracker.items) == 1
        assert tracker.items[0].status == "completed"
        assert tracker.items[0].message == "Finished"
    
    def test_fail_item(self, tracker):
        """Test failing an item."""
        tracker.start("test-item")
        tracker.fail("Something went wrong")
        
        assert tracker.current is None
        assert len(tracker.items) == 1
        assert tracker.items[0].status == "failed"
        assert "Something went wrong" in tracker.items[0].message
    
    def test_skip_item(self, tracker):
        """Test skipping an item."""
        tracker.start("test-item")
        tracker.skip("Skipped intentionally")
        
        assert tracker.current is None
        assert len(tracker.items) == 1
        assert tracker.items[0].status == "skipped"
    
    def test_update_message(self, tracker):
        """Test updating item message."""
        tracker.start("test-item")
        tracker.update("Processing...")
        
        assert tracker.current.message == "Processing..."
    
    def test_multiple_items(self, tracker):
        """Test tracking multiple items."""
        tracker.start("item1")
        tracker.complete()
        
        tracker.start("item2")
        tracker.complete()
        
        tracker.start("item3")
        tracker.fail("Error")
        
        assert len(tracker.items) == 3
        assert tracker.items[0].status == "completed"
        assert tracker.items[1].status == "completed"
        assert tracker.items[2].status == "failed"
    
    def test_get_progress(self, tracker):
        """Test getting progress information."""
        tracker.start("item1")
        tracker.complete()
        tracker.start("item2")
        
        progress = tracker.get_progress()
        
        assert progress["total"] == 2
        assert progress["completed"] == 1
        assert progress["running"] == 1
        assert progress["failed"] == 0
    
    def test_is_complete(self, tracker):
        """Test is_complete check."""
        tracker.start("item1")
        tracker.complete()
        
        assert not tracker.is_complete()
        
        tracker.start("item2")
        tracker.complete()
        
        assert tracker.is_complete()
    
    def test_has_failures(self, tracker):
        """Test failure detection."""
        tracker.start("item1")
        tracker.complete()
        
        assert not tracker.has_failures()
        
        tracker.start("item2")
        tracker.fail("Error")
        
        assert tracker.has_failures()
    
    def test_reset(self, tracker):
        """Test resetting the tracker."""
        tracker.start("item1")
        tracker.complete()
        
        tracker.reset()
        
        assert len(tracker.items) == 0
        assert tracker.current is None
    
    def test_get_summary(self, tracker):
        """Test getting progress summary."""
        tracker.start("item1")
        tracker.complete()
        
        summary = tracker.get_summary()
        
        assert "Progress: 1/1 completed" in summary
        assert "Failed: 0" in summary


class TestProgressItem:
    """Test cases for ProgressItem."""
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        from datetime import datetime, timedelta
        
        item = ProgressItem(
            name="test",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=5),
        )
        
        assert item.duration is not None
        assert item.duration.total_seconds() >= 5
    
    def test_duration_none_when_incomplete(self):
        """Test duration is None for incomplete items."""
        item = ProgressItem(name="test", start_time=datetime.now())
        
        assert item.duration is None