"""
Report Scheduler System
Handles automatic daily delivery of scheduled reports
"""
import threading
import time
import schedule
from datetime import datetime
import sys
import os
from pathlib import Path

# Add the delivery module to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'delivery'))

from report_manager import report_manager
from utils import prepare_delivery_params, DeliveryExecutor

try:
    from slack_delivery_simple import SlackDeliverySimple
except ImportError as e:
    print(f"Warning: Could not import SlackDeliverySimple: {e}")
    SlackDeliverySimple = None

class ReportScheduler:
    def __init__(self):
        self.scheduler_thread = None
        self.running = False
        
    def schedule_report(self, report_id, report_data):
        """Schedule a single report for daily delivery"""
        if not report_data.get('schedule_enabled', False):
            return
            
        schedule_time = report_data.get('schedule_time', '09:00')
        
        def send_report():
            """Function to send the report"""
            try:
                print(f"Sending scheduled report: {report_id} at {datetime.now()}")
                
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
                if SlackDeliverySimple:
                    result = DeliveryExecutor.execute(SlackDeliverySimple, params)
                    if result.get('success'):
                        print(f"✅ Report {report_id} sent successfully")
                    else:
                        print(f"❌ Failed to send report {report_id}: {result.get('error', 'Unknown error')}")
                else:
                    print(f"❌ SlackDeliverySimple not available for report {report_id}")
                    
            except Exception as e:
                print(f"❌ Error sending scheduled report {report_id}: {e}")
        
        # Schedule the report
        schedule.every().day.at(schedule_time).do(send_report).tag(report_id)
        print(f"📅 Scheduled report {report_id} for daily delivery at {schedule_time}")
    
    def load_and_schedule_all_reports(self):
        """Load all reports and schedule the enabled ones"""
        try:
            reports = report_manager.load_reports()
            
            # Clear existing schedules
            schedule.clear()
            
            # Schedule all enabled reports
            for report_id, report_data in reports.items():
                if report_data.get('schedule_enabled', False):
                    self.schedule_report(report_id, report_data)
            
            print(f"📊 Loaded {len([r for r in reports.values() if r.get('schedule_enabled', False)])} scheduled reports")
                    
        except Exception as e:
            print(f"❌ Error loading reports for scheduling: {e}")
    
    def start_scheduler(self):
        """Start the scheduler in a background thread"""
        if self.running:
            print("Scheduler is already running")
            return
            
        self.running = True
        
        def run_scheduler():
            """Background thread function"""
            print("🚀 Starting report scheduler...")
            self.load_and_schedule_all_reports()
            
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    print(f"❌ Scheduler error: {e}")
                    time.sleep(60)
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        print("✅ Report scheduler started")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        schedule.clear()
        print("🛑 Report scheduler stopped")
    
    def refresh_schedules(self):
        """Refresh all schedules (call this when reports are updated)"""
        if self.running:
            print("🔄 Refreshing report schedules...")
            self.load_and_schedule_all_reports()
    
    def get_scheduled_jobs(self):
        """Get list of currently scheduled jobs"""
        jobs = []
        for job in schedule.jobs:
            jobs.append({
                'report_id': list(job.tags)[0] if job.tags else 'unknown',
                'next_run': job.next_run,
                'interval': str(job.interval),
                'unit': job.unit
            })
        return jobs

# Global scheduler instance
report_scheduler = ReportScheduler()

def start_report_scheduler():
    """Convenience function to start the scheduler"""
    report_scheduler.start_scheduler()

def stop_report_scheduler():
    """Convenience function to stop the scheduler"""
    report_scheduler.stop_scheduler()

def refresh_report_schedules():
    """Convenience function to refresh schedules"""
    report_scheduler.refresh_schedules()

def get_scheduler_status():
    """Get current scheduler status"""
    return {
        'running': report_scheduler.running,
        'scheduled_jobs': report_scheduler.get_scheduled_jobs()
    }

if __name__ == "__main__":
    # For testing
    start_report_scheduler()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        stop_report_scheduler()
