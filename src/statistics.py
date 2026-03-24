"""Statistics collection and reporting."""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class AnalysisStats:
    """Statistics for an analysis session."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    files_analyzed: int = 0
    lines_of_code: int = 0
    issues_found: int = 0
    issues_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    issues_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    files_by_language: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    analysis_time_seconds: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    errors: List[str] = field(default_factory=list)


class StatisticsCollector:
    """Collect and aggregate analysis statistics."""
    
    def __init__(self):
        """Initialize the statistics collector."""
        self.current_stats: Dict[str, AnalysisStats] = {}
        logger.debug("Statistics collector initialized")
    
    def start_session(self, session_id: str):
        """Start a new statistics session.
        
        Args:
            session_id: Unique identifier for the session
        """
        self.current_stats[session_id] = AnalysisStats()
        logger.info(f"Started statistics session: {session_id}")
    
    def end_session(self, session_id: str):
        """End a statistics session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.current_stats:
            stats = self.current_stats[session_id]
            stats.end_time = datetime.now()
            stats.analysis_time_seconds = (
                stats.end_time - stats.start_time
            ).total_seconds()
            logger.info(f"Ended statistics session: {session_id}")
    
    def record_file(self, session_id: str, file_path: str, language: str, lines: int):
        """Record information about an analyzed file.
        
        Args:
            session_id: Session identifier
            file_path: Path to the file
            language: Programming language
            lines: Number of lines in the file
        """
        if session_id not in self.current_stats:
            self.start_session(session_id)
        
        stats = self.current_stats[session_id]
        stats.files_analyzed += 1
        stats.lines_of_code += lines
        stats.files_by_language[language] += 1
        
        logger.debug(f"Recorded file: {file_path} ({language}, {lines} lines)")
    
    def record_issue(self, session_id: str, severity: str, issue_type: str):
        """Record an issue found during analysis.
        
        Args:
            session_id: Session identifier
            severity: Issue severity
            issue_type: Type of issue
        """
        if session_id not in self.current_stats:
            self.start_session(session_id)
        
        stats = self.current_stats[session_id]
        stats.issues_found += 1
        stats.issues_by_severity[severity] += 1
        stats.issues_by_type[issue_type] += 1
        
        logger.debug(f"Recorded issue: {severity} {issue_type}")
    
    def record_cache_hit(self, session_id: str):
        """Record a cache hit.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.current_stats:
            self.current_stats[session_id].cache_hits += 1
    
    def record_cache_miss(self, session_id: str):
        """Record a cache miss.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.current_stats:
            self.current_stats[session_id].cache_misses += 1
    
    def record_api_call(self, session_id: str):
        """Record an API call.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.current_stats:
            self.current_stats[session_id].api_calls += 1
    
    def record_error(self, session_id: str, error: str):
        """Record an error.
        
        Args:
            session_id: Session identifier
            error: Error message
        """
        if session_id in self.current_stats:
            self.current_stats[session_id].errors.append(error)
            logger.warning(f"Recorded error: {error}")
    
    def get_stats(self, session_id: str) -> AnalysisStats:
        """Get statistics for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Analysis statistics
        """
        return self.current_stats.get(session_id, AnalysisStats())
    
    def get_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of statistics.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary dictionary
        """
        stats = self.get_stats(session_id)
        
        return {
            "session_id": session_id,
            "files_analyzed": stats.files_analyzed,
            "lines_of_code": stats.lines_of_code,
            "issues_found": stats.issues_found,
            "issues_by_severity": dict(stats.issues_by_severity),
            "issues_by_type": dict(stats.issues_by_type),
            "files_by_language": dict(stats.files_by_language),
            "analysis_time_seconds": stats.analysis_time_seconds,
            "cache_hit_rate": (
                stats.cache_hits / (stats.cache_hits + stats.cache_misses)
                if stats.cache_hits + stats.cache_misses > 0
                else 0
            ),
            "api_calls": stats.api_calls,
            "error_count": len(stats.errors),
        }
    
    def get_all_sessions(self) -> List[str]:
        """Get all session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self.current_stats.keys())
    
    def clear_session(self, session_id: str):
        """Clear statistics for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.current_stats:
            del self.current_stats[session_id]
            logger.info(f"Cleared statistics for session: {session_id}")
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics across all sessions.
        
        Returns:
            Global statistics
        """
        total_files = sum(s.files_analyzed for s in self.current_stats.values())
        total_lines = sum(s.lines_of_code for s in self.current_stats.values())
        total_issues = sum(s.issues_found for s in self.current_stats.values())
        total_api_calls = sum(s.api_calls for s in self.current_stats.values())
        total_cache_hits = sum(s.cache_hits for s in self.current_stats.values())
        total_cache_misses = sum(s.cache_misses for s in self.current_stats.values())
        
        return {
            "total_sessions": len(self.current_stats),
            "total_files": total_files,
            "total_lines": total_lines,
            "total_issues": total_issues,
            "total_api_calls": total_api_calls,
            "total_cache_hits": total_cache_hits,
            "total_cache_misses": total_cache_misses,
            "overall_cache_hit_rate": (
                total_cache_hits / (total_cache_hits + total_cache_misses)
                if total_cache_hits + total_cache_misses > 0
                else 0
            ),
        }