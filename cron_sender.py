#!/usr/bin/env python3
"""
GitHub Actions Cron Script for Scheduled Reports
Run by GitHub Actions to send scheduled reports automatically
"""
import sys
import os
from pathlib import Path
from datetime import datetime, time, timedelta
import traceback
import json

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def load_environment():
    """Load environment variables from .env file if it exists"""
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print("✅ Loaded .env file")
        else:
            print("ℹ️ No .env file found, using environment variables")
    except ImportError:
        print("ℹ️ python-dotenv not available, using environment variables")

def log_delivery_result(report_id, report_name, status, message=None, error=None, scheduled_time=None):
    """Log delivery result to GitHub repository for Streamlit to display"""
    try:
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
        from app.delivery_logs_manager import DeliveryLogsManager
        
        logs_manager = DeliveryLogsManager()
        
        # Add log entry
        success = logs_manager.add_log_entry(
            report_id=report_id,
            report_name=report_name,
            status=status,
            scheduled_time=scheduled_time or "",
            message=message or "",
            error=error or ""
        )
        
        if success:
            print(f"📝 Logged delivery result for {report_id} to GitHub")
        else:
            print(f"❌ Failed to log delivery result for {report_id}")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not log delivery result: {e}")

def send_scheduled_reports():
    """Check for and send any reports that are scheduled for this time"""
    try:
        # Add app directory to path for imports
        sys.path.append(str(Path(__file__).parent / "app"))
        from app.report_manager import ReportManager
        from app.utils import prepare_delivery_params, DeliveryExecutor
        
        # Import the delivery class
        sys.path.append(str(Path(__file__).parent / "delivery"))
        from delivery.slack_delivery_simple import SlackDeliverySimple
        
        print(f"🕒 Checking for scheduled reports at {datetime.now()}")
        
        # Create report manager instance
        report_manager = ReportManager()
        
        # Load all reports
        reports = report_manager.load_reports()
        
        if not reports:
            print("📝 No reports found")
            return
        
        current_time = datetime.now().time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        print(f"⏰ Current time: {current_hour:02d}:{current_minute:02d}")
        
        reports_sent = 0
        
        # Check each report
        for report_id, report_data in reports.items():
            if not report_data.get('schedule_enabled', False):
                continue
                
            schedule_time_str = report_data.get('schedule_time', '09:00')
            print(f"📅 Checking report {report_id}: scheduled for {schedule_time_str}")
            
            try:
                # Parse the scheduled time
                schedule_hour, schedule_minute = map(int, schedule_time_str.split(':'))
                
                # Check if current time is within 15 minutes of scheduled time
                # This allows for flexibility with the 15-minute cron intervals
                scheduled_minutes_total = schedule_hour * 60 + schedule_minute
                current_minutes_total = current_hour * 60 + current_minute
                
                # Check if we're within 15 minutes of the scheduled time
                time_diff = abs(current_minutes_total - scheduled_minutes_total)
                
                if time_diff <= 15 or time_diff >= (24 * 60 - 15):  # Handle day rollover
                    # Check if already sent today
                    last_sent = report_data.get('last_sent_date', '')
                    if last_sent == today_str:
                        print(f"⏭️ Report {report_id} already sent today ({last_sent})")
                        
                        # Log skipped delivery
                        report_name = report_data.get('name', report_id)
                        log_delivery_result(
                            report_id=report_id,
                            report_name=report_name,
                            status="skipped",
                            message="Already sent today",
                            scheduled_time=schedule_time_str
                        )
                        continue
                    print(f"📧 Sending scheduled report: {report_id}")
                    
                    # Prepare delivery parameters
                    form_data = {
                        'author': report_data.get('author', ''),
                        'receiver': report_data.get('receiver', ''),
                        'link': report_data.get('link', ''),
                        'raw_data_link': report_data.get('raw_data_link', ''),
                        'channel': report_data.get('channel', ''),
                        'date': datetime.now().date(),
                        'thread_content': report_data.get('thread_content', ''),
                        'thread_ts': '',
                        'uploaded_file_path': None,
                        'send_file_directly': False
                    }
                    
                    params = prepare_delivery_params(form_data)
                    
                    # Execute delivery
                    result = DeliveryExecutor.execute(SlackDeliverySimple, params)
                    
                    report_name = report_data.get('name', report_id)
                    
                    if result.get('success'):
                        print(f"✅ Successfully sent report: {report_id}")
                        reports_sent += 1
                        
                        # Log successful delivery
                        receiver = report_data.get('receiver', '')
                        log_delivery_result(
                            report_id=report_id,
                            report_name=report_name,
                            status="success",
                            message=f"Successfully sent to @{receiver}",
                            scheduled_time=schedule_time_str
                        )
                        
                        # Update delivery count and last delivered timestamp
                        try:
                            report_manager.increment_delivery_count(report_id)
                            # Also update last_sent_date for today's duplicate prevention
                            report_data['last_sent_date'] = today_str
                            report_manager.update_report(report_id, report_data)
                            print(f"📝 Updated delivery stats for {report_id}")
                        except Exception as update_e:
                            print(f"⚠️ Warning: Could not update last_sent_date for {report_id}: {update_e}")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        print(f"❌ Failed to send report {report_id}: {error_msg}")
                        
                        # Log failed delivery
                        log_delivery_result(
                            report_id=report_id,
                            report_name=report_name,
                            status="failed",
                            error=error_msg,
                            scheduled_time=schedule_time_str
                        )
                        
                else:
                    print(f"⏰ Report {report_id} scheduled for {schedule_time_str}, current time {current_hour:02d}:{current_minute:02d} (time_diff: {time_diff} minutes)")
                        
            except Exception as e:
                print(f"❌ Error processing report {report_id}: {e}")
                traceback.print_exc()
        
        print(f"📊 Summary: {reports_sent} reports sent successfully")
        
    except Exception as e:
        print(f"❌ Critical error in send_scheduled_reports: {e}")
        traceback.print_exc()
        raise

def main():
    """Main function"""
    print("🚀 GitHub Actions Scheduled Report Sender")
    print("=" * 50)
    
    # Load environment variables
    load_environment()
    
    # Check if we have the required environment variables
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        print("❌ SLACK_BOT_TOKEN environment variable not set")
        sys.exit(1)
    
    print("✅ Environment configured")
    
    # Send scheduled reports
    try:
        send_scheduled_reports()
        print("✅ Scheduled report check completed")
    except Exception as e:
        print(f"❌ Failed to send scheduled reports: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
