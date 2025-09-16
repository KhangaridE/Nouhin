"""
Report management utilities for reading and writing reports configuration
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

class ReportManager:
    def __init__(self):
        self.reports_file = Path(__file__).parent.parent / "client_info" / "reports.json"
    
    def load_reports(self) -> Dict[str, Any]:
        """Load reports from JSON file"""
        try:
            if self.reports_file.exists():
                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
        except Exception as e:
            print(f"Error loading reports: {e}")
            return {}
    
    def save_reports(self, reports: Dict[str, Any]) -> bool:
        """Save reports to JSON file"""
        try:
            # Ensure directory exists
            self.reports_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.reports_file, 'w', encoding='utf-8') as f:
                json.dump(reports, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving reports: {e}")
            return False
    
    def add_report(self, report_data: Dict[str, Any]) -> str:
        """Add a new report and return its ID"""
        reports = self.load_reports()
        
        # Generate new report ID
        existing_ids = [int(k.split('-')[1]) for k in reports.keys() if k.startswith('Report-')]
        new_id = max(existing_ids) + 1 if existing_ids else 1
        report_id = f"Report-{new_id}"
        
        # Add timestamp
        report_data['created_at'] = datetime.now().isoformat()
        report_data['updated_at'] = datetime.now().isoformat()
        
        reports[report_id] = report_data
        
        if self.save_reports(reports):
            return report_id
        else:
            return None
    
    def update_report(self, report_id: str, report_data: Dict[str, Any]) -> bool:
        """Update an existing report"""
        reports = self.load_reports()
        
        if report_id in reports:
            # Preserve created_at, update updated_at
            if 'created_at' in reports[report_id]:
                report_data['created_at'] = reports[report_id]['created_at']
            report_data['updated_at'] = datetime.now().isoformat()
            
            reports[report_id] = report_data
            return self.save_reports(reports)
        else:
            return False
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report"""
        reports = self.load_reports()
        
        if report_id in reports:
            del reports[report_id]
            return self.save_reports(reports)
        else:
            return False
    
    def get_report(self, report_id: str) -> Dict[str, Any]:
        """Get a specific report"""
        reports = self.load_reports()
        return reports.get(report_id, {})

# Create global instance
report_manager = ReportManager()
