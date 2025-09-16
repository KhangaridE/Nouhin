#!/usr/bin/env python3
"""
GitHub Actions Cron Script for Scheduled Reports
Run by GitHub Actions to send scheduled reports automatically
"""
import sys
import os
from pathlib import Path
from datetime import datetime, time
import traceback

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

def send_scheduled_reports():
    """Check for and send any reports that are scheduled for this time"""
    try:
        from report_manager import report_manager
        from utils import prepare_delivery_params, DeliveryExecutor
        
        # Import the delivery class
        sys.path.append(str(Path(__file__).parent / "delivery"))
        from slack_delivery_simple import SlackDeliverySimple
        
        print(f"🕒 Checking for scheduled reports at {datetime.now()}")
        
        # Load all reports
        reports = report_manager.load_reports()
        
        if not reports:
            print("📝 No reports found")
            return
        
        current_time = datetime.now().time()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        reports_sent = 0
        
        # Check each report
        for report_id, report_data in reports.items():
            if not report_data.get('schedule_enabled', False):
                continue
                
            schedule_time_str = report_data.get('schedule_time', '09:00')
            
            try:
                # Parse the scheduled time
                schedule_hour, schedule_minute = map(int, schedule_time_str.split(':'))
                
                # Check if current time matches scheduled time (within the hour)
                if current_hour == schedule_hour:
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
                    
                    if result.get('success'):
                        print(f"✅ Successfully sent report: {report_id}")
                        reports_sent += 1
                    else:
                        print(f"❌ Failed to send report {report_id}: {result.get('error', 'Unknown error')}")
                        
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
