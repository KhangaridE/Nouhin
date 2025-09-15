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
    st.title("📨 Delivery System")
    st.markdown("---")
    
    # Sidebar for environment status and settings
    with st.sidebar:
        env_status = config.get_environment_status()
        # display_environment_status(env_status)
        
        st.markdown("---")
        st.subheader("📋 Form Controls")
        # st.info("Form starts blank by default. Use buttons below to load defaults or clear form.")
        
        # Load defaults button
        if st.button("📂 Load Default Arguments"):
            defaults = config.load_default_arguments()
            if defaults:
                # Populate session state with default values
                for key, value in defaults.items():
                    if value:  # Only set non-empty values
                        st.session_state[f'form_{key}'] = value
                # Handle date separately if it exists
                if 'date' in defaults and defaults['date']:
                    try:
                        # Store as string in session state for consistency
                        st.session_state['form_date'] = defaults['date']
                    except:
                        pass
                st.success("Default arguments loaded!")
                st.rerun()
            else:
                st.warning("No default arguments found in arguments.json")
        
        # Clear form button
        if st.button("🗑️ Clear Form", key="clear_button"):
            # Get current form key to clear the right FormSubmitter
            current_form_key = st.session_state.get('form_key', 0)
            form_submitter_key = f'FormSubmitter:delivery_form_{current_form_key}'
            
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
            
            st.success("✅ Form cleared! All fields are now blank.")
            st.rerun()
        
        # Save current form as defaults
        if st.button("💾 Save as Defaults"):
            if 'last_params' in st.session_state:
                if config.save_arguments(st.session_state['last_params']):
                    st.success("Arguments saved as defaults!")
                    st.info(f"Saved to: {config.arguments_file}")
                else:
                    st.error("Failed to save arguments")
            else:
                st.warning("No form data to save. Please submit the form first.")
        
        # Debug section (expandable)
        # with st.expander("🔍 Debug Info"):
        #     st.write("**Session State Keys:**")
        #     form_keys = [k for k in st.session_state.keys() if k.startswith('form_')]
        #     if form_keys:
        #         for key in form_keys:
        #             st.text(f"{key}: {repr(st.session_state[key])}")
        #     else:
        #         st.text("No form data in session state")
            
        #     st.write("**Other relevant keys:**")
        #     other_keys = ['form_key', 'last_params']
        #     for key in other_keys:
        #         if key in st.session_state:
        #             st.text(f"{key}: {repr(st.session_state[key])}")
        #         else:
        #             st.text(f"{key}: Not set")
            
        #     # Show FormSubmitter keys
        #     st.write("**FormSubmitter keys:**")
        #     form_submitter_keys = [k for k in st.session_state.keys() if k.startswith('FormSubmitter:')]
        #     if form_submitter_keys:
        #         for key in form_submitter_keys:
        #             st.text(f"{key}: {repr(st.session_state[key])}")
        #     else:
        #         st.text("No FormSubmitter keys found")
            
        #     st.write("**Arguments File Location:**")
        #     st.text(str(config.arguments_file))
            
        #     if config.arguments_file.exists():
        #         st.success("✅ Arguments file exists")
        #     else:
        #         st.warning("⚠️ No arguments file found")
    
    # Check if environment is ready
    if not env_status['slack_token_set']:
        st.error("Please set your SLACK_BOT_TOKEN environment variable before using this app.")
        st.code("export SLACK_BOT_TOKEN='your-token-here'")
        st.stop()
    
    # Main form
    st.header("📝 Delivery Parameters")
    
    # Content delivery method selection (outside form for immediate updates)
    st.subheader("📎 Content Delivery Method")
    delivery_method = st.radio(
        "How do you want to share content?",
        ["Send file link", "Send file directly"],
        help="Choose whether to send a link or upload a file directly"
    )
    
    # Debug info (can remove later)
    st.caption(f"Selected method: {delivery_method}")
    
    # Don't auto-load defaults - only load them when explicitly requested
    # This makes the form start blank by default
    
    # Create form with a key that changes when we want to clear
    form_key = st.session_state.get('form_key', 0)
    
    with st.form(f"delivery_form_{form_key}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Required Information")
            
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
                st.write("🔗 **Link Input Section**")
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
                
                # if uploaded_file is not None:
                #     st.info(f"✅ File ready: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
                # else:
                #     st.info("👆 Please select a file to upload")
        
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

            


        
        # st.subheader("🧵 Thread Options")
        
        # thread_col1, thread_col2 = st.columns(2)
        
        # with thread_col1:
        #     thread_content = st.text_area(
        #         "📝 Thread Content (for finding existing thread)",
        #         value=st.session_state.get('form_thread_content', defaults.get('thread_content', '')),
        #         help="Text content to find matching thread",
        #         height=100
        #     )
        
        # with thread_col2:
        #     thread_ts = st.text_input(
        #         "🔢 Thread Timestamp",
        #         value=st.session_state.get('form_thread_ts', defaults.get('thread_ts', '')),
        #         help="Specific thread timestamp (optional)"
        #     )
        
        # Form submission
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            submit_button = st.form_submit_button("🚀 Send Delivery", use_container_width=True)
    
    # Form validation and submission
    if submit_button:
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
