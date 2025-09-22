#!/usr/bin/env python3
"""
Enhanced Automatic Delivery Manager
Handles time-based delivery checking and once-per-day delivery logic
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pytz

try:
    from google_sheets_service import GoogleSheetsService
    from github_storage import GitHubStorage
    from slack_delivery_simple import SlackDeliverySimple
except ImportError as e:
    print(f"Import error: {e}")

# Configuration constants
DELIVERY_CONFIG = {
    "check_interval_minutes": 5,  # Check 5 minutes before scheduled time
    "status_column": "ステータス",
    "delivery_time_column": "納品時間（日本時間）",
    "completed_status": "完了",
}

class EnhancedAutomaticDeliveryManager:
    """Enhanced manager for time-based automatic deliveries"""
    
    def __init__(self):
        self.google_sheets = GoogleSheetsService()
        self.github_storage = GitHubStorage() if 'GitHubStorage' in globals() else None
        self.delivery_log_file = 'automatic_delivery_log.json'
        self.jst = pytz.timezone('Asia/Tokyo')
    
    def get_current_jst_time(self) -> datetime:
        """Get current time in JST"""
        return datetime.now(self.jst)
    
    def parse_scheduled_time(self, time_str: str) -> Optional[datetime]:
        """Parse scheduled time from Google Sheets"""
        try:
            # Handle various time formats
            if not time_str or time_str.strip() == '':
                return None
            
            # Remove common prefixes/suffixes
            time_str = time_str.strip()
            
            # Try different time formats
            formats = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M:%S %p']
            
            for fmt in formats:
                try:
                    time_obj = datetime.strptime(time_str, fmt).time()
                    # Combine with today's date in JST
                    today = self.get_current_jst_time().date()
                    return self.jst.localize(datetime.combine(today, time_obj))
                except ValueError:
                    continue
            
            return None
        except Exception as e:
            print(f"Error parsing time '{time_str}': {e}")
            return None
    
    def load_delivery_log(self) -> Dict[str, Any]:
        """Load delivery log from GitHub storage"""
        try:
            if self.github_storage:
                return self.github_storage.read_file(self.delivery_log_file) or {}
            return {}
        except Exception as e:
            print(f"Error loading delivery log: {e}")
            return {}
    
    def save_delivery_log(self, log_data: Dict[str, Any]):
        """Save delivery log to GitHub storage"""
        try:
            if self.github_storage:
                self.github_storage.write_file(self.delivery_log_file, log_data)
        except Exception as e:
            print(f"Error saving delivery log: {e}")
    
    def is_already_delivered_today(self, report_name: str) -> bool:
        """Check if report was already delivered today"""
        log = self.load_delivery_log()
        today = self.get_current_jst_time().date().isoformat()
        
        daily_log = log.get(today, {})
        return report_name in daily_log
    
    def mark_as_delivered(self, report_name: str, delivery_info: Dict[str, Any]):
        """Mark report as delivered for today"""
        log = self.load_delivery_log()
        today = self.get_current_jst_time().date().isoformat()
        
        if today not in log:
            log[today] = {}
        
        log[today][report_name] = {
            'delivered_at': self.get_current_jst_time().isoformat(),
            'delivery_info': delivery_info
        }
        
        self.save_delivery_log(log)
    
    def should_check_now(self, scheduled_time: datetime) -> bool:
        """Check if we're in the 5-minute delivery window (e.g., 17:25-17:29 for 17:30 deadline)"""
        if not scheduled_time:
            return False
        
        current_time = self.get_current_jst_time()
        
        # Calculate the 5-minute window: 5 minutes before deadline until deadline
        window_start = scheduled_time - timedelta(minutes=5)  # 17:25 for 17:30 deadline
        window_end = scheduled_time  # 17:30
        
        # Check if current time is within the 5-minute window
        is_in_window = window_start <= current_time <= window_end
        
        if is_in_window:
            minutes_to_deadline = int((scheduled_time - current_time).total_seconds() / 60)
            print(f"🎯 In delivery window! {minutes_to_deadline} minutes until deadline ({scheduled_time.strftime('%H:%M')})")
        
        return is_in_window
    
    def extract_authors(self, row_data: Dict[str, str], config: Dict[str, Any]) -> List[str]:
        """Extract author mentions from row data"""
        authors = []
        for col_name in config.get('author_columns', []):
            if col_name in row_data and row_data[col_name]:
                authors.append(row_data[col_name])
        return authors
    
    def process_automatic_deliveries(self) -> List[Dict[str, Any]]:
        """Process automatic deliveries based on time and status"""
        results = []
        
        try:
            # Import report manager to get reports set to automatic mode
            from report_manager import report_manager
            
            # Get all reports and filter for automatic ones
            all_reports = report_manager.load_reports()
            automatic_reports = {
                report_id: report for report_id, report in all_reports.items() 
                if report.get('delivery_mode') == 'Automatic'
            }
            
            if not automatic_reports:
                print("No reports found with automatic delivery mode")
                return []
            
            print(f"Found {len(automatic_reports)} reports in automatic mode")
            
            # Get Google Sheets URLs from secrets
            import streamlit as st
            status_url = st.secrets.get("GOOGLE_SHEETS_STATUS_URL") if hasattr(st, 'secrets') else None
            
            if not status_url:
                print("❌ Google Sheets Status URL not configured")
                return []
            
            # Read reports from Google Sheets
            reports_data = self.google_sheets.get_status_reports(status_url)
            
            for report_data in reports_data:
                task_name = report_data.get('task_name', '')
                status = report_data.get('status', '')
                delivery_time_str = report_data.get('delivery_time', '')
                
                # Check if this task name matches any of our automatic reports
                matching_report = None
                matching_report_id = None
                
                for report_id, report in automatic_reports.items():
                    # Try to match by name or by checking if task_name contains report name
                    if (report.get('name', '') == task_name or 
                        task_name in report.get('name', '') or
                        report.get('name', '') in task_name):
                        matching_report = report
                        matching_report_id = report_id
                        break
                
                if not matching_report:
                    continue  # Skip reports not in our automatic delivery list
                
                print(f"Processing automatic report: {task_name}")
                
                # Check if already delivered today
                if self.is_already_delivered_today(task_name):
                    print(f"Report {task_name} already delivered today")
                    continue
                
                # Parse scheduled delivery time
                scheduled_time = self.parse_scheduled_time(delivery_time_str)
                if not scheduled_time:
                    print(f"Could not parse delivery time for {task_name}: {delivery_time_str}")
                    continue
                
                # Check if we should check now (5 minutes before scheduled time)
                if not self.should_check_now(scheduled_time):
                    print(f"Not time to check {task_name} yet (scheduled: {scheduled_time})")
                    continue
                
                # Check if status is completed
                if status != DELIVERY_CONFIG['completed_status']:  # Check for '完了'
                    print(f"Report {task_name} not ready (status: {status})")
                    results.append({
                        'task_name': task_name,
                        'report_id': matching_report_id,
                        'status': 'not_ready',
                        'current_status': status,
                        'scheduled_time': scheduled_time.isoformat()
                    })
                    continue
                
                # All conditions met - deliver the report
                print(f"Delivering report: {task_name}")
                
                delivery_result = self.deliver_report(task_name, matching_report, report_data)
                
                if delivery_result.get('success'):
                    self.mark_as_delivered(task_name, delivery_result)
                    print(f"✅ Successfully delivered {task_name}")
                else:
                    print(f"❌ Failed to deliver {task_name}: {delivery_result.get('error')}")
                
                results.append({
                    'task_name': task_name,
                    'report_id': matching_report_id,
                    'status': 'delivered' if delivery_result.get('success') else 'failed',
                    'scheduled_time': scheduled_time.isoformat(),
                    'delivery_result': delivery_result
                })
        
        except Exception as e:
            print(f"Error in process_automatic_deliveries: {e}")
            results.append({
                'error': str(e),
                'status': 'error'
            })
        
        return results
    
    def deliver_report(self, task_name: str, report_config: Dict[str, Any], report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deliver a specific report to Slack using the report configuration"""
        try:
            # Use the report configuration from the report manager
            configured_author = report_config.get('author', '').strip()
            configured_receiver = report_config.get('receiver', '').strip()
            link = report_config.get('link', '')
            raw_data_link = report_config.get('raw_data_link', '')
            channel = report_config.get('channel', '')
            thread_content = report_config.get('thread_content', '')
            thread_ts = report_config.get('thread_ts', '')
            
            # Extract author information from Google Sheets
            sheet_authors = []
            author_columns = ['(1次作成者）', '(2次確認)', '納品者']
            for col in author_columns:
                if col in report_data and report_data[col]:
                    sheet_authors.append(report_data[col].strip())
            
            # Build author mentions
            author_mentions = []
            
            # Add sheet authors
            if sheet_authors:
                author_mentions.extend(sheet_authors)
            
            # Add configured author if provided (in addition to sheet authors)
            if configured_author:
                author_mentions.append(configured_author)
            
            # Build receiver mentions
            receiver_mentions = []
            
            # Always add configured receiver if provided
            if configured_receiver:
                receiver_mentions.append(configured_receiver)
            
            # Build message using the same format as manual delivery
            message_parts = []
            
            if thread_content:
                message_parts.append(thread_content)
            
            # Add author information
            if author_mentions:
                author_text = "Authors: " + ", ".join(author_mentions)
                message_parts.append(author_text)
            
            # Add receiver information
            if receiver_mentions:
                receiver_text = "Receiver: " + ", ".join(receiver_mentions)
                message_parts.append(receiver_text)
            
            if link:
                message_parts.append(f"Link: {link}")
            
            if raw_data_link:
                message_parts.append(f"Raw Data: {raw_data_link}")
            
            # Add automatic delivery info
            message_parts.append(f"🤖 Automatic delivery triggered by status '完了' at {self.get_current_jst_time().strftime('%H:%M JST')}")
            
            message = '\n'.join(message_parts)
            
            # Use SlackDeliverySimple to send
            slack_delivery = SlackDeliverySimple()
            
            # Use configured channel or default
            target_channel = channel if channel else os.getenv('DELIVERY_TEST_SLACK_DEFAULT_CHANNEL_ID')
            if not target_channel:
                return {'success': False, 'error': 'No channel configured'}
            
            # Send message
            result = slack_delivery.send_message(
                channel_id=target_channel,
                message=message,
                thread_ts=thread_ts if thread_ts else None
            )
            
            return {
                'success': True,
                'result': result,
                'message': message,
                'channel': target_channel,
                'report_config': report_config,
                'sheet_authors': sheet_authors,
                'configured_author': configured_author,
                'configured_receiver': configured_receiver
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
enhanced_automatic_delivery_manager = EnhancedAutomaticDeliveryManager()
