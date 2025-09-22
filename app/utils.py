#!/usr/bin/env python3
"""
Utility functions for Streamlit Slack Delivery App
"""

import streamlit as st
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

def display_environment_status(env_status: Dict[str, Any]):
    """Display environment status in sidebar"""
    st.header("System Status")
    
    if env_status['slack_token_set']:
        st.success(f"Slack Token: {env_status['slack_token_preview']}")
    else:
        st.error("SLACK_BOT_TOKEN not set!")
        st.code("export SLACK_BOT_TOKEN='your-token-here'")

    if env_status['default_channel_set']:
        st.success("Default Channel ID set")
    else:
        st.warning("No default channel ID")
        
    if env_status.get('default_channel'):
        st.info(f"Channel: {env_status['default_channel']}")

def validate_form_inputs(author: str, receiver: str, link: str) -> list:
    """Validate required form inputs"""
    errors = []
    
    # Handle None values by converting to empty string
    author = str(author or '').strip()
    receiver = str(receiver or '').strip()
    link = str(link or '').strip()
    
    if not author:
        errors.append("Author is required")
    if not receiver:
        errors.append("Receiver is required")
    if not link:
        errors.append("Main Link is required")
    
    # Additional URL validation could be added here
    if link and not (link.startswith('http://') or link.startswith('https://')):
        if '.' in link:  # Basic check for domain-like structure
            pass  # Assume it's a valid link without protocol
        else:
            errors.append("Main Link should be a valid URL")
    
    return errors

def format_delivery_preview(params: Dict[str, Any]) -> str:
    """Format delivery parameters for preview"""
    preview_lines = [
        f"**Author:** {params['author']}",
        f"**Receiver:** {params['receiver']}",
        f"**Date:** {params['date']}",
        f"**Main Link:** {params['link']}"
    ]
    
    if params.get('raw_data_link'):
        preview_lines.append(f"**Raw Data:** {params['raw_data_link']}")
    
    if params.get('channel'):
        preview_lines.append(f"**Channel:** #{params['channel']}")
    
    if params.get('thread_content'):
        preview_lines.append(f"**Thread Search:** {params['thread_content']}")
        
    if params.get('thread_ts'):
        preview_lines.append(f"**Thread TS:** {params['thread_ts']}")
        
    return "\n".join(preview_lines)

def display_delivery_results(result: Dict[str, Any]):
    """Display delivery results with proper formatting"""
    if result.get('success'):
        st.success("Message delivered successfully!")
        
        # Show detailed results
        with st.expander("Delivery Details", expanded=True):
            details = []
            
            if 'timestamp' in result:
                details.append(f"**Timestamp:** {result['timestamp']}")
            
            if 'channel' in result:
                details.append(f"**Channel:** {result['channel']}")
            
            if 'author_details' in result:
                author_info = result['author_details']
                details.append(f"**Author Match:** {author_info.get('display_format', 'N/A')}")
                if author_info.get('match_score'):
                    details.append(f"- Match Score: {author_info['match_score']:.2%}")
            
            if 'receiver_details' in result:
                receiver_info = result['receiver_details']
                details.append(f"**Receiver Match:** {receiver_info.get('display_format', 'N/A')}")
                if receiver_info.get('match_score'):
                    details.append(f"- Match Score: {receiver_info['match_score']:.2%}")
            
            if 'thread_info' in result:
                thread_info = result['thread_info']
                if thread_info.get('used_existing'):
                    details.append("**Thread:** Used existing thread")
                    details.append(f"- Thread TS: {thread_info.get('thread_ts', 'N/A')}")
                else:
                    details.append("**Thread:** Created new message")
            
            for detail in details:
                st.info(detail)
        
        # Show JSON response
        with st.expander("Raw Response (JSON)"):
            st.json(result)
    else:
        st.error("Delivery failed!")
        error_msg = result.get('error', 'Unknown error')
        st.error(f"**Error:** {error_msg}")
        
        # Show traceback if available
        if result.get('traceback'):
            with st.expander("Technical Details"):
                st.code(result['traceback'], language='python')
        
        # Show JSON response
        with st.expander("Raw Response (JSON)"):
            st.json(result)

def save_to_session_state(params: Dict[str, Any], prefix: str = "form_"):
    """Save parameters to Streamlit session state"""
    for key, value in params.items():
        st.session_state[f"{prefix}{key}"] = value

def clear_session_state(prefix: str = "form_"):
    """Clear session state with given prefix"""
    keys_to_delete = [key for key in st.session_state.keys() if key.startswith(prefix)]
    for key in keys_to_delete:
        del st.session_state[key]

def prepare_delivery_params(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare and clean delivery parameters"""
    params = {}
    
    # Required fields - ensure they're strings and strip them
    params['author'] = str(form_data.get('author', '')).strip()
    params['receiver'] = str(form_data.get('receiver', '')).strip()
    params['link'] = str(form_data.get('link', '')).strip()
    
    # Optional fields (only include if not empty)
    optional_fields = ['raw_data_link', 'channel', 'thread_content', 'thread_ts']
    for field in optional_fields:
        value = form_data.get(field, '')
        # Handle None values by converting to empty string first
        if value is None:
            value = ''
        value = str(value).strip()
        params[field] = value if value else None
    
    # File upload handling
    if form_data.get('uploaded_file_path'):
        params['uploaded_file_path'] = str(form_data['uploaded_file_path'])
    
    if form_data.get('send_file_directly', False):
        params['send_file_directly'] = True
    
    # Date handling
    if isinstance(form_data.get('date'), str):
        params['date'] = form_data['date']
    else:
        # Assume it's a date object from st.date_input
        date_obj = form_data.get('date')
        if date_obj is not None:
            params['date'] = date_obj.strftime("%Y/%m/%d")
        else:
            # Fallback to current date if date is None
            from datetime import datetime
            params['date'] = datetime.now().strftime("%Y/%m/%d")
    
    return params

class DeliveryExecutor:
    """Helper class to execute delivery with proper error handling"""
    
    @staticmethod
    def execute(delivery_class, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delivery with comprehensive error handling"""
        try:
            # Initialize the delivery system
            delivery = delivery_class(
                channel_name=params.get('channel') if params.get('channel') else None
            )
            
            # Check if we need to send a file directly
            if params.get('send_file_directly') and params.get('uploaded_file_path'):
                # Send file directly
                result = delivery.send_type1_message_with_file(
                    file_path=params['uploaded_file_path'],
                    author=params['author'],
                    receiver=params['receiver'],
                    thread_content=params.get('thread_content'),
                    thread_ts=params.get('thread_ts'),
                    custom_date=params.get('date'),
                    raw_data_link=params.get('raw_data_link')
                )
            else:
                # Send the message with link (traditional method)
                file_link = params['link']
                if not file_link and params.get('uploaded_file_path'):
                    # If no link provided but file was uploaded, use file path as link
                    file_link = params['uploaded_file_path']
                
                result = delivery.send_type1_message(
                    file_link=file_link,
                    author=params['author'],
                    receiver=params['receiver'],
                    thread_content=params.get('thread_content'),
                    thread_ts=params.get('thread_ts'),
                    custom_date=params.get('date'),
                    raw_data_link=params.get('raw_data_link')
                )
            
            return result
            
        except ImportError as e:
            return {
                'success': False,
                'error': f'Import error: {str(e)}',
                'error_type': 'import_error',
                'traceback': traceback.format_exc()
            }
        except ValueError as e:
            return {
                'success': False,
                'error': f'Configuration error: {str(e)}',
                'error_type': 'config_error',
                'traceback': traceback.format_exc()
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'error_type': 'unexpected_error',
                'traceback': traceback.format_exc()
            } 