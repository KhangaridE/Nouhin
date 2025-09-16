"""
Delivery logs management utilities for reading and writing delivery logs
"""
import json
from typing import Dict, Any, List
from datetime import datetime

try:
    from .github_storage import GitHubStorage
except ImportError:
    from github_storage import GitHubStorage


class DeliveryLogsManager:
    def __init__(self):
        self.github_storage = GitHubStorage()
    
    def load_logs(self) -> Dict[str, Any]:
        """Load delivery logs from GitHub repository"""
        try:
            logs = self.github_storage.read_file("delivery_logs.json")
            return logs if logs is not None else {}
        except Exception as e:
            print(f"Error loading delivery logs from GitHub: {e}")
            return {}
    
    def save_logs(self, logs: Dict[str, Any]) -> bool:
        """Save delivery logs to GitHub repository"""
        try:
            return self.github_storage.write_file("delivery_logs.json", logs, "Update delivery logs")
        except Exception as e:
            print(f"Error saving delivery logs to GitHub: {e}")
            return False
    
    def add_log_entry(self, report_id: str, report_name: str, status: str, 
                      scheduled_time: str, message: str = "", error: str = "") -> bool:
        """Add a new log entry"""
        logs = self.load_logs()
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Initialize today's logs if not exists
        if today not in logs:
            logs[today] = []
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "report_id": report_id,
            "report_name": report_name,
            "status": status,
            "scheduled_time": scheduled_time
        }
        
        if message:
            log_entry["message"] = message
        if error:
            log_entry["error"] = error
        
        # Add to logs
        logs[today].append(log_entry)
        
        # Save
        return self.save_logs(logs)
    
    def get_logs_for_date(self, date: str) -> List[Dict[str, Any]]:
        """Get logs for a specific date"""
        logs = self.load_logs()
        return logs.get(date, [])
    
    def get_recent_logs(self, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get logs for the last N days"""
        logs = self.load_logs()
        
        # Get recent dates
        from datetime import timedelta
        today = datetime.now()
        recent_logs = {}
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in logs:
                recent_logs[date] = logs[date]
        
        return recent_logs
    
    def get_logs_for_report(self, report_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get all logs for a specific report in the last N days"""
        logs = self.load_logs()
        
        report_logs = []
        from datetime import timedelta
        today = datetime.now()
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in logs:
                for log_entry in logs[date]:
                    if log_entry.get("report_id") == report_id:
                        report_logs.append(log_entry)
        
        return sorted(report_logs, key=lambda x: x["timestamp"], reverse=True)
