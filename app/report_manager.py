"""
Report management utilities for reading and writing reports configuration
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

try:
    from .github_storage import GitHubStorage
except ImportError:
    from github_storage import GitHubStorage

class ReportManager:
    def __init__(self):
        self.github_storage = GitHubStorage()
        # Keep local path for fallback/reference
        self.reports_file = Path(__file__).parent.parent / "client_info" / "reports.json"
    
    def load_reports(self) -> Dict[str, Any]:
        """Load reports from GitHub repository"""
        try:
            reports = self.github_storage.read_file("reports.json")
            return reports if reports is not None else {}
        except Exception as e:
            print(f"Error loading reports from GitHub: {e}")
            return {}
    
    def save_reports(self, reports: Dict[str, Any]) -> bool:
        """Save reports to GitHub repository"""
        try:
            return self.github_storage.write_file("reports.json", reports, "Update reports from Streamlit app")
        except Exception as e:
            print(f"Error saving reports to GitHub: {e}")
            return False
    
    def add_report(self, report_data: Dict[str, Any]) -> str:
        """Add a new report and return its ID"""
        reports = self.load_reports()
        
        # Generate new report ID with proper format
        existing_ids = []
        for key in reports.keys():
            if key.startswith('RPT_') and len(key) == 9:  # RPT_XXXXX format
                try:
                    existing_ids.append(int(key[4:]))
                except ValueError:
                    continue
        
        new_id = max(existing_ids) + 1 if existing_ids else 1
        report_id = f"RPT_{new_id:05d}"  # Format: RPT_00001, RPT_00002, etc.
        
        # Standardize report data structure
        standardized_data = self._standardize_report_data(report_data)
        standardized_data['id'] = report_id
        standardized_data['created_at'] = datetime.now().isoformat()
        standardized_data['updated_at'] = datetime.now().isoformat()
        
        reports[report_id] = standardized_data
        
        if self.save_reports(reports):
            return report_id
        else:
            return None
    
    def _standardize_report_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure all required fields are present with default values"""
        standard_fields = {
            'id': '',  # Will be set by add_report/update_report
            'name': data.get('name', ''),
            'author': data.get('author', ''),
            'receiver': data.get('receiver', ''),
            'link': data.get('link', ''),
            'raw_data_link': data.get('raw_data_link', ''),
            'channel': data.get('channel', ''),
            'thread_content': data.get('thread_content', ''),
            'thread_ts': data.get('thread_ts', None),
            'date': data.get('date', ''),
            'delivery_mode': data.get('delivery_mode', 'manual'),  # manual, scheduled, automatic
            'schedule_enabled': data.get('schedule_enabled', False),
            'schedule_time': data.get('schedule_time', '09:00'),
            'automatic_task_id': data.get('automatic_task_id', ''),  # DDAMOP_XXXXX for automatic mode
            'created_at': data.get('created_at', ''),
            'updated_at': data.get('updated_at', ''),
            'last_delivered': data.get('last_delivered', None),
            'delivery_count': data.get('delivery_count', 0),
            'status': data.get('status', 'active')  # active, inactive, archived
        }
        return standard_fields
    
    def update_report(self, report_id: str, report_data: Dict[str, Any]) -> bool:
        """Update an existing report"""
        reports = self.load_reports()
        
        if report_id in reports:
            # Preserve certain fields and standardize
            existing_data = reports[report_id]
            standardized_data = self._standardize_report_data(report_data)
            
            # Preserve important fields
            standardized_data['id'] = report_id
            standardized_data['created_at'] = existing_data.get('created_at', datetime.now().isoformat())
            standardized_data['updated_at'] = datetime.now().isoformat()
            standardized_data['delivery_count'] = existing_data.get('delivery_count', 0)
            standardized_data['last_delivered'] = existing_data.get('last_delivered', None)
            
            reports[report_id] = standardized_data
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
    
    def increment_delivery_count(self, report_id: str) -> bool:
        """Increment delivery count and update last delivered timestamp"""
        reports = self.load_reports()
        
        if report_id in reports:
            reports[report_id]['delivery_count'] = reports[report_id].get('delivery_count', 0) + 1
            reports[report_id]['last_delivered'] = datetime.now().isoformat()
            reports[report_id]['updated_at'] = datetime.now().isoformat()
            return self.save_reports(reports)
        return False
    
    def migrate_existing_data(self) -> bool:
        """Migrate existing reports to new standardized format"""
        reports = self.load_reports()
        migrated = False
        
        for report_id, report_data in list(reports.items()):  # Use list() to avoid dict modification during iteration
            # Check if this report needs migration
            if 'id' not in report_data or not report_id.startswith('RPT_'):
                # Create new standardized ID if needed
                if not report_id.startswith('RPT_') and report_id != 'Default':
                    # Generate new ID
                    existing_ids = []
                    for key in reports.keys():
                        if key.startswith('RPT_') and len(key) == 9:
                            try:
                                existing_ids.append(int(key[4:]))
                            except ValueError:
                                continue
                    
                    new_id = max(existing_ids) + 1 if existing_ids else 1
                    new_report_id = f"RPT_{new_id:05d}"
                    
                    # Migrate to new ID
                    standardized_data = self._standardize_report_data(report_data)
                    standardized_data['id'] = new_report_id
                    
                    # Copy over if missing timestamps
                    if 'created_at' not in report_data:
                        standardized_data['created_at'] = datetime.now().isoformat()
                    
                    reports[new_report_id] = standardized_data
                    del reports[report_id]  # Remove old entry
                    migrated = True
                elif report_id == 'Default':
                    # Standardize Default template
                    standardized_data = self._standardize_report_data(report_data)
                    standardized_data['id'] = 'Default'
                    reports[report_id] = standardized_data
                    migrated = True
                else:
                    # Just standardize existing data
                    standardized_data = self._standardize_report_data(report_data)
                    standardized_data['id'] = report_id
                    reports[report_id] = standardized_data
                    migrated = True
        
        if migrated:
            return self.save_reports(reports)
        return True
    
    def get_automatic_reports(self) -> Dict[str, Any]:
        """Get all reports configured for automatic delivery"""
        reports = self.load_reports()
        automatic_reports = {}
        
        for report_id, report_data in reports.items():
            if report_data.get('delivery_mode') == 'automatic' and report_data.get('automatic_task_id'):
                automatic_reports[report_id] = report_data
        
        return automatic_reports
    
    def get_reports_by_delivery_mode(self, mode: str) -> Dict[str, Any]:
        """Get reports filtered by delivery mode"""
        reports = self.load_reports()
        filtered_reports = {}
        
        for report_id, report_data in reports.items():
            if report_data.get('delivery_mode') == mode:
                filtered_reports[report_id] = report_data
        
        return filtered_reports
    
    def update_automatic_delivery_status(self, report_id: str, delivered: bool = True) -> bool:
        """Update automatic delivery status to prevent duplicate deliveries"""
        reports = self.load_reports()
        
        if report_id in reports:
            if delivered:
                reports[report_id]['last_auto_delivered'] = datetime.now().isoformat()
                reports[report_id]['delivery_count'] = reports[report_id].get('delivery_count', 0) + 1
            reports[report_id]['updated_at'] = datetime.now().isoformat()
            return self.save_reports(reports)
        return False

# Create global instance
report_manager = ReportManager()
