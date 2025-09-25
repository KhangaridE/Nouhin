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
        try:
            self.google_sheets = GoogleSheetsService()
        except NameError:
            print("GoogleSheetsService not available")
            self.google_sheets = None
            
        try:
            self.github_storage = GitHubStorage()
        except NameError:
            print("GitHubStorage not available")
            self.github_storage = None
            
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
                log_data = self.github_storage.read_file(self.delivery_log_file)
                if log_data is None:
                    # File doesn't exist, create initial empty log
                    print(f"Creating initial {self.delivery_log_file} in GitHub repo")
                    initial_log = {}
                    self.save_delivery_log(initial_log)
                    return initial_log
                return log_data
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
    
    def is_already_delivered_today(self, report_name: str, scheduled_time: datetime = None) -> bool:
        """Check if report was already delivered today for this specific time"""
        log = self.load_delivery_log()
        today = self.get_current_jst_time().date().isoformat()
        
        daily_log = log.get(today, {})
        
        if scheduled_time:
            # Create unique key combining report name and scheduled time
            time_str = scheduled_time.strftime('%H:%M')
            delivery_key = f"{report_name}_{time_str}"
            return delivery_key in daily_log
        else:
            # Fallback to old behavior for backward compatibility
            return report_name in daily_log
    
    def mark_as_delivered(self, report_name: str, delivery_info: Dict[str, Any], scheduled_time: datetime = None):
        """Mark report as delivered for today with specific time"""
        log = self.load_delivery_log()
        today = self.get_current_jst_time().date().isoformat()
        
        if today not in log:
            log[today] = {}
        
        if scheduled_time:
            # Create unique key combining report name and scheduled time
            time_str = scheduled_time.strftime('%H:%M')
            delivery_key = f"{report_name}_{time_str}"
        else:
            # Fallback to old behavior
            delivery_key = report_name
        
        log[today][delivery_key] = {
            'delivered_at': self.get_current_jst_time().isoformat(),
            'scheduled_time': scheduled_time.isoformat() if scheduled_time else None,
            'delivery_info': delivery_info,
            'report_name': report_name,  # Keep original name for reference
            'deadline_time': time_str if scheduled_time else None
        }
        
        self.save_delivery_log(log)
        
        # Also record to main delivery logs for history page visibility
        try:
            from delivery_logs_manager import DeliveryLogsManager
            logs_manager = DeliveryLogsManager()
            
            # Determine status based on delivery_info
            if isinstance(delivery_info, dict):
                if delivery_info.get('success') or delivery_info.get('delivery_method') == 'manual_test':
                    status = 'success'
                    message = f" Automatic delivery (Task ID: {delivery_info.get('task_id', report_name)})"
                else:
                    status = 'failed' 
                    message = f" Automatic delivery failed: {delivery_info.get('error', 'Unknown error')}"
            else:
                status = 'success'
                message = f" Automatic delivery (Task: {report_name})"
            
            # Add to main delivery logs
            time_str = scheduled_time.strftime('%H:%M') if scheduled_time else 'Unknown'
            logs_manager.add_log_entry(
                report_id=delivery_key,  # Use our unique key as report_id
                report_name=report_name,
                status=status,
                scheduled_time=time_str,
                message=message
            )
            print(f"✅ Recorded automatic delivery to main delivery logs: {delivery_key}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not record to main delivery logs: {e}")
            # Don't fail the delivery if logging fails
    
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
            # Check if automatic delivery system is enabled
            try:
                from system_settings_manager import SystemSettingsManager
                settings_manager = SystemSettingsManager()
                automatic_delivery_enabled = settings_manager.get_automatic_delivery_enabled()
                
                if not automatic_delivery_enabled:
                    print("Automatic delivery system is disabled - skipping processing")
                    return []
                    
                print("Automatic delivery system is enabled - proceeding with processing")
            except ImportError:
                print("Warning: Could not load system settings manager - proceeding anyway")
            
            # Import report manager to get reports set to automatic mode
            from report_manager import report_manager
            
            # Get all reports and filter for automatic ones
            all_reports = report_manager.load_reports()
            automatic_reports = {
                report_id: report for report_id, report in all_reports.items() 
                if report.get('delivery_mode') == 'automatic'
            }
            
            if not automatic_reports:
                print("No reports found with automatic delivery mode")
                return []
            
            print(f"Found {len(automatic_reports)} reports in automatic mode")
            
            # Get Google Sheets URLs from environment or secrets
            import streamlit as st
            import os
            
            # Try environment variable first (for GitHub Actions), then Streamlit secrets
            status_url = os.environ.get('AUTOMATIC_DELIVERY_STATUS_SHEET_URL')
            if not status_url and hasattr(st, 'secrets'):
                status_url = st.secrets.get("GOOGLE_SHEETS_STATUS_URL")
            
            if not status_url:
                print("❌ Google Sheets Status URL not configured")
                print("   - GitHub Actions: Set AUTOMATIC_DELIVERY_STATUS_SHEET_URL secret")
                print("   - Streamlit: Set GOOGLE_SHEETS_STATUS_URL in secrets.toml")
                return []
            
            # Read reports from Google Sheets
            reports_data = self.google_sheets.get_status_reports(status_url)
            
            for report_data in reports_data:
                task_id = report_data.get('task_id', '')
                status = report_data.get('status', '')
                delivery_time_str = report_data.get('delivery_time', '')
                
                # Check if this task ID matches any of our automatic reports
                matching_report = None
                matching_report_id = None
                
                for report_id, report in automatic_reports.items():
                    automatic_task_id = report.get('automatic_task_id', '')
                    # Match by automatic_task_id from report configuration
                    if automatic_task_id == task_id:
                        matching_report = report
                        matching_report_id = report_id
                        break
                
                if not matching_report:
                    continue  # Skip reports not in our automatic delivery list
                
                print(f"Processing automatic report: {task_id}")
                
                # Parse scheduled delivery time first (needed for delivery tracking)
                scheduled_time = self.parse_scheduled_time(delivery_time_str)
                if not scheduled_time:
                    print(f"Could not parse delivery time for {task_id}: {delivery_time_str}")
                    continue
                
                # Check if already delivered today for this specific time
                if self.is_already_delivered_today(task_id, scheduled_time):
                    print(f"Report {task_id} already delivered today for {scheduled_time.strftime('%H:%M')}")
                    continue
                
                # Check if we should check now (5 minutes before scheduled time)
                if not self.should_check_now(scheduled_time):
                    print(f"Not time to check {task_id} yet (scheduled: {scheduled_time.strftime('%H:%M')})")
                    continue
                
                # Check if status is completed
                if status != DELIVERY_CONFIG['completed_status']:  # Check for '完了'
                    print(f"Report {task_id} not ready (status: {status})")
                    results.append({
                        'task_name': task_id,
                        'report_id': matching_report_id,
                        'status': 'not_ready',
                        'current_status': status,
                        'scheduled_time': scheduled_time.isoformat()
                    })
                    continue
                
                # All conditions met - deliver the report
                print(f"Delivering report: {task_id} for {scheduled_time.strftime('%H:%M')} deadline")
                
                delivery_result = self.deliver_report(task_id, matching_report, report_data)
                
                if delivery_result.get('success'):
                    self.mark_as_delivered(task_id, delivery_result, scheduled_time)
                    print(f"Successfully delivered {task_id} for {scheduled_time.strftime('%H:%M')}")
                else:
                    print(f"Failed to deliver {task_id}: {delivery_result.get('error')}")
                
                results.append({
                    'task_name': task_id,
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
            message_parts.append(f" Automatic delivery triggered by status '完了' at {self.get_current_jst_time().strftime('%H:%M JST')}")
            
            message = '\n'.join(message_parts)
            
            # Import and use SlackDeliverySimple to send
            try:
                import sys
                sys.path.insert(0, 'delivery')
                from slack_delivery_simple import SlackDeliverySimple
                
                # Use configured channel or default
                target_channel = channel if channel else os.getenv('DELIVERY_TEST_SLACK_DEFAULT_CHANNEL_ID')
                if not target_channel:
                    return {'success': False, 'error': 'No channel configured'}
                
                # Initialize SlackDeliverySimple with proper channel handling
                if target_channel.startswith('C'):
                    # It's a channel ID, use default constructor and set channel_id
                    slack_delivery = SlackDeliverySimple()
                    slack_delivery.channel_id = target_channel
                else:
                    # It's a channel name, use constructor with channel_name parameter
                    slack_delivery = SlackDeliverySimple(channel_name=target_channel)
                
            except ImportError as e:
                return {'success': False, 'error': f'Could not import SlackDeliverySimple: {e}'}
            except Exception as e:
                return {'success': False, 'error': f'Could not initialize SlackDeliverySimple: {e}'}
            
            # Prepare data for SlackDeliverySimple
            authors = ", ".join(author_mentions) if author_mentions else "Unknown"
            receivers = ", ".join(receiver_mentions) if receiver_mentions else "Unknown"
            
            # Send message using send_type1_message
            result = slack_delivery.send_type1_message(
                file_link=link,
                author=authors,
                receiver=receivers,
                thread_content=thread_content if thread_content else None,
                thread_ts=thread_ts if thread_ts else None,
                raw_data_link=raw_data_link if raw_data_link else None
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
