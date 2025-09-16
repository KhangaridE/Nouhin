#!/usr/bin/env python3
"""
Streamlit Web App for Slack Delivery System
Direct integration with SlackDeliverySimple class
"""

# Load environment variables from .env file first
try:
    from dotenv import load_dotenv
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

import streamlit as st
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the delivery module to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'delivery'))

# Import local modules
from config import config
from utils import (
    display_environment_status, 
    validate_form_inputs, 
    format_delivery_preview,
    display_delivery_results,
    save_to_session_state,
    clear_session_state,
    prepare_delivery_params,
    DeliveryExecutor
)

try:
    from slack_delivery_simple import SlackDeliverySimple
except ImportError as e:
    st.error(f"❌ Failed to import SlackDeliverySimple: {e}")
    st.error("Please ensure the delivery module is properly configured.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Slack Delivery System",
    page_icon="📨",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("📨 Delivery System (納品)")
    st.markdown("---")
    
    # Initialize page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Delivery List"
    
    # Sidebar navigation with buttons
    with st.sidebar:
        st.subheader("Navigation (ナビゲーション)")
        
        if st.button("Delivery List (配送リスト)", use_container_width=True):
            st.session_state.current_page = "Delivery List"
        
        if st.button("Report Management (レポート管理)", use_container_width=True):
            st.session_state.current_page = "Report Management"
        
        if st.button("Custom Delivery (カスタム配送)", use_container_width=True):
            st.session_state.current_page = "Custom Delivery"
        
        st.markdown("---")
        
        # Environment status
        # env_status = config.get_environment_status()
        # st.subheader("⚙️ Status")
        
        # if env_status['slack_token_set']:
        #     st.success("✅ Slack Ready")
        # else:
        #     st.error("❌ Slack Token Missing")
        
        # if env_status.get('default_channel_id'):
        #     st.success("✅ Channel Set") 
        # else:
        #     st.warning("⚠️ No Default Channel")
        
        st.markdown("---")
        
        # Scheduler status and controls
        st.subheader("⏰ Scheduler")
        
        # Check if running on Streamlit Cloud or with GitHub Actions
        is_cloud_deployment = os.getenv('STREAMLIT_CLOUD') or os.getenv('GITHUB_ACTIONS') or not os.path.exists(Path(__file__).parent / 'scheduler.py')
        
        if is_cloud_deployment:
            # Show GitHub Actions scheduler status
            st.info("☁️ GitHub Actions Scheduler")
            st.caption("Automatic scheduling via GitHub Actions")
            st.caption("Checks every hour for scheduled reports")
            
            # Show count of scheduled reports
            try:
                from report_manager import report_manager
                reports = report_manager.load_reports()
                scheduled_count = sum(1 for r in reports.values() if r.get('schedule_enabled', False))
                if scheduled_count > 0:
                    st.success(f"✅ {scheduled_count} reports scheduled")
                else:
                    st.info("📝 No reports scheduled yet")
            except:
                pass
                
        else:
            # Local scheduler controls (for local development)
            try:
                from scheduler import report_scheduler, get_scheduler_status, start_report_scheduler, stop_report_scheduler, refresh_report_schedules
                
                status = get_scheduler_status()
                
                if status['running']:
                    st.success("✅ Local Scheduler Running")
                    st.caption(f"📊 {len(status['scheduled_jobs'])} jobs scheduled")
                    
                    if st.button("🛑 Stop Scheduler", use_container_width=True):
                        stop_report_scheduler()
                        st.rerun()
                        
                    if st.button("🔄 Refresh Schedules", use_container_width=True):
                        refresh_report_schedules()
                        st.success("Schedules refreshed!")
                        
                else:
                    st.error("❌ Local Scheduler Stopped")
                    if st.button("🚀 Start Scheduler", use_container_width=True):
                        start_report_scheduler()
                        st.rerun()
                        
            except ImportError:
                st.warning("⚠️ Local scheduler not available")
            except Exception as e:
                st.error(f"❌ Local scheduler error: {e}")
    
    # Route to different pages
    if st.session_state.current_page == "Delivery List":
        delivery_section_page()
    elif st.session_state.current_page == "Report Management":
        delivery_parameters_page()
    elif st.session_state.current_page == "Custom Delivery":
        custom_delivery_page()

def delivery_section_page():
    """First page - Delivery List with daily reports list"""
    st.header("📦 Delivery List")
    st.markdown("Here are the scheduled daily reports. Click on any report to view details.")
    
    # Import report manager
    try:
        from report_manager import report_manager
        
        reports = report_manager.load_reports()
        
        if reports:
            for report_id, report in reports.items():
                # Create expandable section for each report
                with st.expander(f"📋 {report.get('name', report.get('thread_content', report_id))}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**👤 Author:**")
                        st.code(report.get('author', ''))
                    
                    with col2:
                        st.write("**👥 Receiver:**")
                        st.code(report.get('receiver', ''))
                    
                    with col3:
                        st.write("🔗 **Link:**")
                        if report.get('link'):
                            st.code(report['link'])
                        else:
                            st.code("(No link)")
                            
                        
                    
                    st.markdown("---")
                    st.write("**📋 Full Parameters (Read-Only):**")
                    
                    # Display all parameters in a clean format
                    param_col1, param_col2 = st.columns(2)
                    
                    with param_col1:

                        st.write("📢 **Channel:**")
                        if report.get('channel'):
                            st.code(report['channel'])
                        else:
                            st.code("(Default channel)")

                            
                        st.write("📊 **Raw Data Link:**")
                        if report.get('raw_data_link'):
                            st.code(report['raw_data_link'])
                        else:
                            st.code("(No raw data link)")

                        st.write("⏰ **Schedule:**")
                        if report.get('schedule_enabled', False):
                            schedule_time = report.get('schedule_time', '09:00')
                            st.code(f"Daily at {schedule_time}")
                        else:
                            st.code("(Manual delivery only)")
                    
                    with param_col2:
                        st.write("**🧵 Thread:**")
                        if report.get('thread_content'):
                            st.code(report.get('thread_content', ''))
                        else:
                            st.code("(No thread content, sending as a new thread)")
                            
                        st.write("📅 **Date:**")
                        if report.get('date'):
                            st.code(report['date'])
                        else:
                            st.code("(Current date)")
                            
                        
                    
                    # Schedule info
                    if report.get('schedule_enabled', False):
                        schedule_time = report.get('schedule_time', '09:00')
                        st.success(f"✅ Automatic delivery enabled - Daily at {schedule_time}")
                    else:
                        st.info("📝 Manual delivery only - Use Custom Delivery page to send")
        else:
            st.info("No reports configured yet. Go to 'Report Management' to create reports.")
            
    except ImportError:
        st.error("❌ Could not load report manager.")
    except Exception as e:
        st.error(f"❌ Error loading reports: {e}")

def delivery_parameters_page():
    """Second page - Report Management with modifying parameters"""
    st.header("📅 Report Management")
    st.markdown("Create, edit, and manage your delivery reports.")
    
    # Import report manager
    try:
        from report_manager import report_manager
        
        # Initialize session state for editing
        if 'editing_report' not in st.session_state:
            st.session_state.editing_report = None
        if 'creating_report' not in st.session_state:
            st.session_state.creating_report = False
        
        # Action buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("➕ Create New Report", use_container_width=True):
                st.session_state.creating_report = True
                st.session_state.editing_report = None
                st.rerun()
        
        with col2:
            if st.button("📋 View All Reports", use_container_width=True):
                st.session_state.creating_report = False
                st.session_state.editing_report = None
                st.rerun()
        
        st.markdown("---")
        
        # Show create form if creating new report
        if st.session_state.creating_report:
            st.subheader("➕ Create New Report")
            
            with st.form("create_report_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    report_name = st.text_input("Report Name/ID", help="Unique identifier for this report")
                    author = st.text_input("Author", help="Who is sending this report")
                    receiver = st.text_input("Receiver", help="Who will receive this report")
                    thread_content = st.text_input("Thread Content", help="Main content/title of the report")
                
                with col2:
                    link = st.text_input("Link", help="Optional: URL link to include")
                    raw_data_link = st.text_input("Raw Data Link", help="Optional: Link to raw data")
                    channel = st.text_input("Channel", help="Optional: Specific Slack channel")
                    date = st.text_input("Date", help="Optional: Specific date format")
                
                # Scheduling section
                st.markdown("---")
                st.subheader("⏰ Automatic Scheduling (Optional)")
                
                schedule_col1, schedule_col2 = st.columns(2)
                
                with schedule_col1:
                    schedule_enabled = st.checkbox("Enable automatic daily delivery", value=False, help="When enabled, this report will be sent automatically every day at the specified time")
                
                with schedule_col2:
                    schedule_time = st.time_input("Delivery time", value=datetime.now().time().replace(second=0, microsecond=0), help="What time to send the report daily (24-hour format)")
                
                if schedule_enabled:
                    st.info(f"📅 This report will be automatically delivered every day at {schedule_time.strftime('%H:%M')}")
                else:
                    st.info("📝 Scheduling is disabled. You can manually send this report from the Custom Delivery page.")
                
                submitted = st.form_submit_button("💾 Create Report", use_container_width=True)
                
                if submitted:
                    if report_name and author and receiver and thread_content:
                        new_report = {
                            "name": report_name,  # Store the custom name
                            "author": author,
                            "receiver": receiver,
                            "thread_content": thread_content,
                            "link": link,
                            "raw_data_link": raw_data_link,
                            "channel": channel,
                            "date": date,
                            "schedule_enabled": schedule_enabled,
                            "schedule_time": schedule_time.strftime('%H:%M') if schedule_time else "09:00"
                        }
                        
                        report_id = report_manager.add_report(new_report)
                        if report_id:
                            # Refresh scheduler if report has scheduling enabled
                            try:
                                from scheduler import refresh_report_schedules
                                refresh_report_schedules()
                            except ImportError:
                                pass
                            
                            st.success(f"✅ Report '{report_name}' created successfully with ID: {report_id}!")
                            st.session_state.creating_report = False
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to create report!")
                    else:
                        st.error("❌ Please fill in all required fields (Report Name, Author, Receiver, Thread Content)")
        
        # Show edit form if editing existing report
        elif st.session_state.editing_report:
            reports = report_manager.load_reports()
            current_report = reports.get(st.session_state.editing_report, {})
            report_name = current_report.get('name', 'Unknown')
            report_id = st.session_state.editing_report
            
            st.subheader(f"✏️ Edit Report: {report_name}-{report_id}")
            
            with st.form("edit_report_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Report Name/ID", value=current_report.get('name', ''), help="Unique identifier for this report")
                    author = st.text_input("Author", value=current_report.get('author', ''), help="Who is sending this report")
                    receiver = st.text_input("Receiver", value=current_report.get('receiver', ''), help="Who will receive this report")
                    thread_content = st.text_input("Thread Content", value=current_report.get('thread_content', ''), help="Optional: Main content/title of the report")
                
                with col2:
                    link = st.text_input("Link", value=current_report.get('link', ''), help="Optional: URL link to include")
                    raw_data_link = st.text_input("Raw Data Link", value=current_report.get('raw_data_link', ''), help="Optional: Link to raw data")
                    channel = st.text_input("Channel", value=current_report.get('channel', ''), help="Optional: Specific Slack channel")
                    date = st.text_input("Date", value=current_report.get('date', ''), help="Optional: Specific date format")
                
                # Scheduling section
                st.markdown("---")
                st.subheader("⏰ Automatic Scheduling (Optional)")
                
                schedule_col1, schedule_col2 = st.columns(2)
                
                with schedule_col1:
                    schedule_enabled = st.checkbox("Enable automatic daily delivery", 
                                                 value=current_report.get('schedule_enabled', False), 
                                                 help="When enabled, this report will be sent automatically every day at the specified time")
                
                with schedule_col2:
                    # Parse existing time or use default
                    default_time = datetime.now().time().replace(second=0, microsecond=0)
                    if current_report.get('schedule_time'):
                        try:
                            time_parts = current_report['schedule_time'].split(':')
                            default_time = datetime.strptime(f"{time_parts[0]}:{time_parts[1]}", "%H:%M").time()
                        except:
                            pass
                    
                    schedule_time = st.time_input("Delivery time", 
                                                value=default_time, 
                                                help="What time to send the report daily (24-hour format)")
                
                if schedule_enabled:
                    st.info(f"📅 This report will be automatically delivered every day at {schedule_time.strftime('%H:%M')}")
                else:
                    st.info("📝 Scheduling is disabled. You can manually send this report from the Custom Delivery page.")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    save_clicked = st.form_submit_button("� Save Changes", use_container_width=True)
                
                with col2:
                    cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                
                with col3:
                    delete_clicked = st.form_submit_button("🗑️ Delete Report", use_container_width=True)
                
                if save_clicked:
                    # Only require Name, Author, and Receiver - Thread Content is optional
                    if name and name.strip() and author and author.strip() and receiver and receiver.strip():
                        updated_report = {
                            "name": name.strip(),
                            "author": author.strip(),
                            "receiver": receiver.strip(),
                            "thread_content": thread_content.strip() if thread_content else '',
                            "link": link.strip() if link else '',
                            "raw_data_link": raw_data_link.strip() if raw_data_link else '',
                            "channel": channel.strip() if channel else '',
                            "date": date.strip() if date else '',
                            "schedule_enabled": schedule_enabled,
                            "schedule_time": schedule_time.strftime('%H:%M') if schedule_time else "09:00"
                        }
                        
                        success = report_manager.update_report(st.session_state.editing_report, updated_report)
                        if success:
                            # Refresh scheduler when report is updated
                            try:
                                from scheduler import refresh_report_schedules
                                refresh_report_schedules()
                            except ImportError:
                                pass
                                
                            st.success(f"✅ Report '{name.strip()}' updated successfully!")
                            st.session_state.editing_report = None
                            st.rerun()
                        else:
                            st.error("❌ Failed to update report!")
                    else:
                        st.error("❌ Please fill in all required fields (Report Name, Author, Receiver)")
                        st.error("Missing fields:")
                        if not (name and name.strip()):
                            st.error("- Report Name is empty")
                        if not (author and author.strip()):
                            st.error("- Author is empty")
                        if not (receiver and receiver.strip()):
                            st.error("- Receiver is empty")
                
                if cancel_clicked:
                    st.session_state.editing_report = None
                    st.rerun()
                
                if delete_clicked:
                    success = report_manager.delete_report(st.session_state.editing_report)
                    if success:
                        # Refresh scheduler when report is deleted
                        try:
                            from scheduler import refresh_report_schedules
                            refresh_report_schedules()
                        except ImportError:
                            pass
                            
                        st.success(f"✅ Report '{st.session_state.editing_report}' deleted successfully!")
                        st.session_state.editing_report = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete report!")
        
        # Show all reports list (default view)
        else:
            st.subheader("📋 All Reports")
            
            reports = report_manager.load_reports()
            
            if reports:
                for report_id, report in reports.items():
                    # Create expandable section for each report (matching first page style)
                    with st.expander(f"📋 {report.get('name', report.get('thread_content', report_id))}", expanded=False):
                        # Header row with main info and edit button
                        header_col1, header_col2, header_col3, edit_col = st.columns([1, 1, 1, 1])
                        
                        with header_col1:
                            st.write("**� Author:**")
                            st.code(report.get('author', ''))
                        
                        with header_col2:
                            st.write("**👥 Receiver:**")
                            st.code(report.get('receiver', ''))
                        
                        with header_col3:
                            st.write("🔗 **Link:**")
                            if report.get('link'):
                                st.code(report['link'])
                            else:
                                st.code("(No link)")
                        
                        with edit_col:
                            st.write("**⚙️ Actions:**")
                            if st.button(f"✏️ Edit", key=f"edit_{report_id}", use_container_width=True):
                                st.session_state.editing_report = report_id
                                st.session_state.creating_report = False
                                st.rerun()
                        
                        st.markdown("---")
                        st.write("**📋 Full Parameters:**")
                        
                        # Display all parameters in a clean format
                        param_col1, param_col2 = st.columns(2)
                        
                        with param_col1:

                            st.write("📢 **Channel:**")
                            if report.get('channel'):
                                st.code(report['channel'])
                            else:
                                st.code("(Default channel)")

                            
                                
                            st.write("📊 **Raw Data Link:**")
                            if report.get('raw_data_link'):
                                st.code(report['raw_data_link'])
                            else:
                                st.code("(No raw data link)")

                            st.write("⏰ **Schedule:**")
                            if report.get('schedule_enabled', False):
                                schedule_time = report.get('schedule_time', '09:00')
                                st.code(f"Daily at {schedule_time}")
                            else:
                                st.code("(Manual delivery only)")
                        
                        with param_col2:

                            st.write("**🧵 Thread:**")
                            if report.get('thread_content'):
                                st.code(report.get('thread_content', ''))
                            else:
                                st.code("(No thread content, sending as a new thread)")
                                
                            st.write("📅 **Date:**")
                            if report.get('date'):
                                st.code(report['date'])
                            else:
                                st.code("(Current date)")
                                
                            
                        
                        # Management info with scheduling status
                        if report.get('schedule_enabled', False):
                            schedule_time = report.get('schedule_time', '09:00')
                            st.success(f"✅ Automatic delivery enabled - Daily at {schedule_time}")
                        else:
                            st.info("📝 Manual delivery only - Click Edit to enable scheduling")
                        
                        st.markdown("---")
            else:
                st.info("📝 No reports configured yet. Click 'Create New Report' to get started.")
        
    except ImportError:
        st.error("❌ Could not load report manager.")
    except Exception as e:
        st.error(f"❌ Error managing reports: {e}")

def custom_delivery_page():
    """Third page - Custom Delivery (original form)"""
    # Get environment status
    env_status = config.get_environment_status()
    
    # Check if environment is ready
    if not env_status['slack_token_set']:
        st.error("Please set your SLACK_BOT_TOKEN environment variable before using this app.")
        st.code("export SLACK_BOT_TOKEN='your-token-here'")
        st.stop()
    
    # Main form
    st.header("📝 Custom Delivery")
    
    # Create two columns for method selection and form controls
    method_col, controls_col = st.columns([2, 1])
    
    with method_col:
        # Content delivery method selection (outside form for immediate updates)
        st.subheader("📎 Content Delivery Method")
        delivery_method = st.radio(
            "How do you want to share content?",
            ["Send file link", "Send file directly"],
            help="Choose whether to send a link or upload a file directly"
        )
    
    with controls_col:
        st.subheader("📋 Form Controls")
        st.caption("Manage your form data")
        
        # Load from reports dropdown
        try:
            from report_manager import report_manager
            reports = report_manager.load_reports()
            
            if reports:
                report_options = ["Select a report..."] + [f"{report.get('name', report_id)} ({report_id})" for report_id, report in reports.items()]
                selected_report = st.selectbox(
                    "📋 Load from Report",
                    options=report_options,
                    help="Choose a report to automatically load its parameters"
                )
                
                # Automatically load report when selected
                if selected_report != "Select a report...":
                    # Extract report ID from the selected option
                    report_id = selected_report.split(" (")[-1].rstrip(")")
                    selected_report_data = reports.get(report_id)
                    
                    if selected_report_data:
                        # Check if this report is different from currently loaded one
                        if st.session_state.get('loaded_report_id') != report_id:
                            # Populate session state with report values
                            for key, value in selected_report_data.items():
                                if key not in ['created_at', 'updated_at'] and value:  # Skip metadata and empty values
                                    st.session_state[f'form_{key}'] = value
                            
                            # Handle date separately if it exists
                            if 'date' in selected_report_data and selected_report_data['date']:
                                try:
                                    st.session_state['form_date'] = selected_report_data['date']
                                except:
                                    pass
                            
                            # Remember which report was loaded
                            st.session_state['loaded_report_id'] = report_id
                            st.success(f"Report '{selected_report_data.get('name', report_id)}' loaded!")
                            st.rerun()
                    else:
                        st.error("Selected report not found!")
            else:
                st.info("📝 No reports available. Create reports in 'Report Management' first.")
        except ImportError:
            st.error("❌ Could not load report manager.")
        
        # Clear form button
        if st.button("🗑️ Clear Form", use_container_width=True):
            # Get current form key to clear the right FormSubmitter
            current_form_key = st.session_state.get('form_key', 0)
            
            # Get all session state keys to clear
            keys_to_clear = []
            for key in list(st.session_state.keys()):
                if (key.startswith('form_') or 
                    key in ['last_params'] or
                    key.startswith('FormSubmitter:delivery_form')):
                    keys_to_clear.append(key)
            
            # Clear all form-related keys
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Increment form key to force form recreation
            st.session_state['form_key'] = current_form_key + 1
            
            st.success("✅ Form cleared!")
            st.rerun()
        
    st.markdown("---")
    
    # Don't auto-load defaults - form starts blank by default
    # Create form with a key that changes when we want to clear
    form_key = st.session_state.get('form_key', 0)
    
    with st.form(f"delivery_form_{form_key}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 Required Information")
            # Add Name field above Author
            name = st.text_input(
                "📛 Name (required if saving as report)",
                value=st.session_state.get('form_name', ''),
                help="Report name/title. Required only if you want to save as a report template."
            )
            author = st.text_input(
                "👤 Author (作成者)",
                value=st.session_state.get('form_author', ''),
                help="Your name/username"
            )
            receiver = st.text_input(
                "👥 Receiver (受信者)",
                value=st.session_state.get('form_receiver', ''),
                help="Person to mention/notify"
            )
            # Conditional input based on delivery method
            link = None
            uploaded_file = None
            
            if delivery_method == "Send file link":
                # st.write("🔗 **Link Input Section**")
                link = st.text_input(
                    "Main Link (格納先)",
                    value=st.session_state.get('form_link', ''),
                    help="File link/URL to share"
                )
            else:  # Send file directly
                st.write("📁 **File Upload Section**")
                uploaded_file = st.file_uploader(
                    "Upload a file to share",
                    type=None,  # Allow all file types
                    help="Upload a file to attach directly to the message",
                    key=f"file_uploader_{form_key}"
                )
                
                if uploaded_file is not None:
                    st.info(f"✅ File ready: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
                else:
                    st.info("👆 Please select a file to upload")
        
        with col2:
            st.subheader("⚙️ Optional Settings")
            
            raw_data_link = st.text_input(
                "📊 Raw Data Link",
                value=st.session_state.get('form_raw_data_link', ''),
                help="Raw data spreadsheet link (optional)"
            )
            
            channel = st.text_input(
                "📢 Channel Name",
                value=st.session_state.get('form_channel', ''),
                help="Override default channel (optional)"
            )

            thread_content = st.text_input(
                "📝 Thread Content (for finding existing thread)",
                value=st.session_state.get('form_thread_content', ''),
                help="Text content to find matching thread"
            )

            thread_ts = st.text_input(
                "🔢 Thread Timestamp",
                value=st.session_state.get('form_thread_ts', ''),
                help="Specific thread timestamp (optional)"
            )

            # Date input - always start with today's date
            default_date = datetime.now().date()
            # Check if we have a date in session state (from loaded defaults or previous form)
            if 'form_date' in st.session_state and st.session_state['form_date']:
                try:
                    if isinstance(st.session_state['form_date'], str):
                        default_date = datetime.strptime(st.session_state['form_date'], "%Y/%m/%d").date()
                    else:
                        default_date = st.session_state['form_date']
                except:
                    pass
            
            date = st.date_input(
                "📅 Delivery Date",
                value=default_date,
                help="Date for the delivery message"
            )

        # Form submission
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_button = st.form_submit_button("🚀 Send Delivery", use_container_width=True)
        with col3:
            # Save as report button (only for Send file link)
            if delivery_method == "Send file link":
                save_report_btn = st.form_submit_button("💾 Save as report", use_container_width=True)
                if save_report_btn:
                    if not name:
                        st.error("Name is required to save as report.")
                    else:
                        # Prepare report data
                        report_data = {
                            "name": name,
                            "author": author,
                            "receiver": receiver,
                            "link": link,
                            "raw_data_link": st.session_state.get('form_raw_data_link', ''),
                            "channel": st.session_state.get('form_channel', ''),
                            "thread_content": st.session_state.get('form_thread_content', ''),
                            "thread_ts": st.session_state.get('form_thread_ts', None),
                            "date": str(st.session_state.get('form_date', ''))
                        }
                        try:
                            from report_manager import report_manager
                            report_id = report_manager.add_report(report_data)
                            if report_id:
                                st.success(f"Report saved as '{name}' (ID: {report_id})!")
                            else:
                                st.error("Failed to save report.")
                        except Exception as e:
                            st.error(f"Error saving report: {e}")
    
    # Handle form submission (rest of the logic from original function)
    if submit_button:
        handle_form_submission(author, receiver, link, uploaded_file, raw_data_link, 
                              channel, thread_content, thread_ts, date, delivery_method)

def handle_form_submission(author, receiver, link, uploaded_file, raw_data_link, 
                          channel, thread_content, thread_ts, date, delivery_method):
    """Handle the form submission logic"""
    # Handle file uploads first
    file_path = None
    if uploaded_file is not None:
        # Save uploaded file
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "slack_delivery_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        file_path = temp_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ File saved: {file_path}")
    
    # Validate required fields
    errors = []
    
    if not author or not author.strip():
        errors.append("Author is required")
    if not receiver or not receiver.strip():
        errors.append("Receiver is required")
    
    # Check content based on delivery method
    if delivery_method == "Send file link":
        if not link or not link.strip():
            errors.append("Main Link is required when sending file link")
    else:  # Send file directly
        if uploaded_file is None:
            errors.append("File upload is required when sending file directly")
    
    if errors:
        st.error("Please fix the following errors:")
        for error in errors:
            st.error(f"• {error}")
    else:
        # Prepare parameters - ensure no None values
        form_data = {
            'author': author or '',
            'receiver': receiver or '',
            'link': link or '',
            'raw_data_link': raw_data_link or '',
            'channel': channel or '',
            'date': date,
            'thread_content': thread_content or '',
            'thread_ts': thread_ts or '',
            'uploaded_file_path': file_path if uploaded_file is not None else None,
            'send_file_directly': delivery_method == "Send file directly"
        }
        
        params = prepare_delivery_params(form_data)
        
        # Save to session state
        save_to_session_state(params)
        st.session_state['last_params'] = params
        
        # Show preview
        st.subheader("📋 Delivery Preview")
        with st.expander("📄 Message Preview", expanded=True):
            preview_text = format_delivery_preview(params)
            st.markdown(preview_text)
        
        # Execute delivery
        with st.spinner("🚀 Sending delivery..."):
            result = DeliveryExecutor.execute(SlackDeliverySimple, params)
        
        # Show results
        st.subheader("📊 Delivery Results")
        display_delivery_results(result)

if __name__ == "__main__":
    main()
