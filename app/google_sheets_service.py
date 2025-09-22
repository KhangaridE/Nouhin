#!/usr/bin/env python3
"""
Google Sheets Service
Handles authentication and reading from Google Sheets using service account
"""

import os
import json
import re
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

try:
    import streamlit as st
except ImportError:
    st = None

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from github_storage import GitHubStorage
except ImportError:
    try:
        from .github_storage import GitHubStorage
    except ImportError:
        GitHubStorage = None


class GoogleSheetsService:
    """Service for reading Google Sheets data using service account authentication"""
    
    def __init__(self):
        """Initialize Google Sheets service with service account credentials"""
        self.service = None
        self.credentials = None
        self._initialize_service()
    
    def _get_service_account_info(self) -> Dict[str, Any]:
        """Get service account credentials from GitHub storage or environment"""
        try:
            if GitHubStorage:
                # Try to get from GitHub storage first
                github_storage = GitHubStorage()
                service_account_data = github_storage.read_file('google-service-account.json')
                if service_account_data:
                    return service_account_data
        except Exception as e:
            print(f"Could not load service account from GitHub storage: {e}")
        
        # Try local file fallback
        try:
            local_service_account_path = os.path.join(os.path.dirname(__file__), '..', 'google-service-account.json')
            if os.path.exists(local_service_account_path):
                with open(local_service_account_path, 'r') as f:
                    service_account_data = json.load(f)
                    print("✅ Loaded service account from local file")
                    return service_account_data
        except Exception as e:
            print(f"Could not load service account from local file: {e}")
        
        # Fallback to Streamlit secrets or environment
        try:
            if st and hasattr(st, 'secrets'):
                service_account_info = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")
                if service_account_info:
                    return json.loads(service_account_info) if isinstance(service_account_info, str) else service_account_info
        except Exception:
            pass
        
        # Fallback to environment variable
        service_account_env = os.getenv("GOOGLE_SERVICE_ACCOUNT")
        if service_account_env:
            return json.loads(service_account_env)
        
        raise ValueError("Google service account credentials not found")
    
    def _initialize_service(self):
        """Initialize the Google Sheets API service"""
        try:
            service_account_info = self._get_service_account_info()
            
            # Define the scope
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            
            # Create credentials from service account info
            self.credentials = Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
        except Exception as e:
            print(f"Failed to initialize Google Sheets service: {e}")
            self.service = None
    
    def read_sheet_data(self, spreadsheet_id: str, range_name: str) -> List[List[str]]:
        """
        Read data from a Google Sheet
        
        Args:
            spreadsheet_id: The ID of the spreadsheet (from URL)
            range_name: The range to read (e.g., 'Sheet1!A:Z')
        
        Returns:
            List of rows, where each row is a list of cell values
        """
        if not self.service:
            raise RuntimeError("Google Sheets service not initialized")
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            return values
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            raise
    
    def extract_spreadsheet_id(self, sheet_url: str) -> str:
        """
        Extract spreadsheet ID from Google Sheets URL
        
        Args:
            sheet_url: Full Google Sheets URL
        
        Returns:
            Spreadsheet ID
        """
        # Match pattern: /spreadsheets/d/{ID}/
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            return match.group(1)
        
        raise ValueError(f"Could not extract spreadsheet ID from URL: {sheet_url}")
    
    def get_status_reports(self, status_sheet_url: str) -> List[Dict[str, str]]:
        """
        Get all reports from status sheet
        
        Args:
            status_sheet_url: URL of the status tracking sheet
        
        Returns:
            List of report dictionaries with status information
        """
        try:
            spreadsheet_id = self.extract_spreadsheet_id(status_sheet_url)
            # Read from the "Report main" tab specifically
            data = self.read_sheet_data(spreadsheet_id, "'Report main'!A:BZ")
            
            if not data or len(data) < 3:  # Need at least 3 rows (row 1, headers in row 2, data in row 3+)
                print("No sufficient data found in Report main sheet")
                return []
            
            # Headers are in row 2 (index 1)
            headers = data[1]
            reports = []
            
            print(f"Found {len(headers)} columns in Report main sheet")
            print("Headers (row 2):", headers[:10])
            
            # Find key column indices based on our discovered structure
            task_no_col = None
            report_name_col = None
            delivery_time_col = None
            status_col = None
            primary_author_col = None
            secondary_confirm_col = None
            deliverer_col = None
            
            for i, header in enumerate(headers):
                header_str = str(header).strip()
                if 'タスクNO' in header_str:
                    task_no_col = i
                    print(f"Found task number column at index {i}: {header}")
                elif 'レポート名' in header_str:
                    report_name_col = i
                    print(f"Found report name column at index {i}: {header}")
                elif '納品時間' in header_str and '日本時間' in header_str:
                    delivery_time_col = i
                    print(f"Found delivery time column at index {i}: {header}")
                elif header_str == 'ステータス':  # Exact match for status column
                    status_col = i
                    print(f"Found status column at index {i}: {header}")
                elif '1次作成者' in header_str:
                    primary_author_col = i
                    print(f"Found primary author column at index {i}: {header}")
                elif '2次確認' in header_str:
                    secondary_confirm_col = i
                    print(f"Found secondary confirmation column at index {i}: {header}")
                elif '納品者' in header_str:
                    deliverer_col = i
                    print(f"Found deliverer column at index {i}: {header}")
            
            if report_name_col is None:
                print("Could not find report name column. Available headers:")
                for i, header in enumerate(headers[:20]):
                    print(f"  {i}: {header}")
                return []
                
            if status_col is None:
                print("Could not find status column. Available headers:")
                for i, header in enumerate(headers[:20]):
                    print(f"  {i}: {header}")
                return []
            
            # Process data rows (starting from row 3, which is index 2)
            for row_idx, row in enumerate(data[2:], start=3):
                if len(row) > max(report_name_col, status_col):
                    report_name = row[report_name_col] if report_name_col < len(row) else ""
                    status = row[status_col] if status_col < len(row) else ""
                    task_no = row[task_no_col] if task_no_col is not None and task_no_col < len(row) else ""
                    delivery_time = row[delivery_time_col] if delivery_time_col is not None and delivery_time_col < len(row) else ""
                    primary_author = row[primary_author_col] if primary_author_col is not None and primary_author_col < len(row) else ""
                    secondary_confirm = row[secondary_confirm_col] if secondary_confirm_col is not None and secondary_confirm_col < len(row) else ""
                    deliverer = row[deliverer_col] if deliverer_col is not None and deliverer_col < len(row) else ""
                    
                    # Extract task ID from report name using regex
                    task_id_match = re.search(r'DDAMOP_\d+', str(report_name))
                    if task_id_match:
                        task_id = task_id_match.group()
                        reports.append({
                            'task_id': task_id,
                            'task_no': task_no,
                            'report_name': report_name,
                            'status': status,
                            'delivery_time': delivery_time,
                            'primary_author': primary_author,
                            'secondary_confirm': secondary_confirm,
                            'deliverer': deliverer,
                            'row_number': row_idx,
                            'full_row': row
                        })
                        
                        # Debug: print first few reports
                        if len(reports) <= 3:
                            print(f"Sample report {len(reports)}: {task_id} | {status} | {report_name[:50]}...")
            
            print(f"Total reports found: {len(reports)}")
            return reports
            
        except Exception as e:
            print(f"Error reading status sheet: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_report_metadata(self, metadata_sheet_url: str) -> Dict[str, Dict[str, str]]:
        """
        Get report metadata indexed by task ID
        
        Args:
            metadata_sheet_url: URL of the metadata sheet
        
        Returns:
            Dictionary mapping task_id to metadata
        """
        try:
            spreadsheet_id = self.extract_spreadsheet_id(metadata_sheet_url)
            data = self.read_sheet_data(spreadsheet_id, 'A:Z')  # Read all columns
            
            if not data or len(data) < 2:
                return {}
            
            headers = data[0]
            metadata = {}
            
            # Find key column indices
            task_no_col = None
            report_name_col = None
            delivery_time_col = None
            
            for i, header in enumerate(headers):
                if 'タスクNO' in header:
                    task_no_col = i
                elif 'レポート名' in header:
                    report_name_col = i
                elif '納品時間' in header and '日本時間' in header:
                    delivery_time_col = i
            
            if task_no_col is None or report_name_col is None:
                print("Could not find required columns in metadata sheet")
                return {}
            
            # Process data rows
            for row in data[1:]:
                if len(row) > max(task_no_col or 0, report_name_col or 0):
                    task_no = row[task_no_col] if task_no_col is not None and task_no_col < len(row) else ""
                    report_name = row[report_name_col] if report_name_col < len(row) else ""
                    delivery_time = row[delivery_time_col] if delivery_time_col is not None and delivery_time_col < len(row) else ""
                    
                    # Extract task ID from report name
                    task_id_match = re.search(r'DDAMOP_\d+', report_name)
                    if task_id_match:
                        task_id = task_id_match.group()
                        metadata[task_id] = {
                            'task_no': task_no,
                            'report_name': report_name,
                            'delivery_time': delivery_time,
                            'full_row': row
                        }
            
            return metadata
            
        except Exception as e:
            print(f"Error reading metadata sheet: {e}")
            return {}
    
    def get_ready_reports(self, status_sheet_url: str, metadata_sheet_url: str) -> List[Dict[str, Any]]:
        """
        Get reports that are ready for delivery (status = '完了')
        
        Args:
            status_sheet_url: URL of the status tracking sheet
            metadata_sheet_url: URL of the metadata sheet
        
        Returns:
            List of ready reports with combined status and metadata
        """
        status_reports = self.get_status_reports(status_sheet_url)
        metadata = self.get_report_metadata(metadata_sheet_url)
        
        ready_reports = []
        
        for report in status_reports:
            if report['status'] == '完了':
                task_id = report['task_id']
                if task_id in metadata:
                    combined_report = {
                        **report,
                        **metadata[task_id],
                        'is_ready': True
                    }
                    ready_reports.append(combined_report)
        
        return ready_reports
    
    def should_check_report(self, delivery_time: str, check_window_minutes: int = 10) -> bool:
        """
        Check if we should monitor this report based on delivery time
        
        Args:
            delivery_time: Delivery time in format "HH:MM"
            check_window_minutes: Minutes before delivery time to start checking
        
        Returns:
            True if we should check this report now
        """
        if not delivery_time or ':' not in delivery_time:
            return False
        
        try:
            # Parse delivery time
            time_parts = delivery_time.split(':')
            delivery_hour = int(time_parts[0])
            delivery_minute = int(time_parts[1])
            
            # Get current time
            now = datetime.now()
            
            # Create delivery datetime for today
            delivery_today = now.replace(
                hour=delivery_hour,
                minute=delivery_minute,
                second=0,
                microsecond=0
            )
            
            # If delivery time has passed today, check tomorrow's delivery
            if delivery_today <= now:
                delivery_today += timedelta(days=1)
            
            # Calculate check start time (10 minutes before delivery)
            check_start_time = delivery_today - timedelta(minutes=check_window_minutes)
            
            # Should check if current time is between check start time and delivery time
            return check_start_time <= now <= delivery_today
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing delivery time '{delivery_time}': {e}")
            return False


# Create a singleton instance
google_sheets_service = GoogleSheetsService()
