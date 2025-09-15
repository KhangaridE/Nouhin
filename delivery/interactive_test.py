#!/usr/bin/env python3
"""
Interactive RPA Test Script for Slack Delivery System
This version asks for user input before calling the delivery system
"""

import subprocess
import json
import os
import sys
from datetime import datetime

def get_user_input():
    """Get delivery parameters from user input"""
    
    print("=" * 60)
    print("🤖 INTERACTIVE SLACK DELIVERY TEST")
    print("=" * 60)
    print("Please enter the delivery information:")
    print("")
    
    # Required parameters
    author = input("📝 Author (作成者): ").strip()
    receiver = input("📤 Receiver (受信者): ").strip()
    link = input("📎 Main Link (格納先): ").strip()
    
    print("")
    print("Optional parameters (press Enter to skip):")
    
    # Optional parameters
    raw_data_link = input("📊 Raw Data Link (raw貼り付けスプシ): ").strip()
    channel = input("📢 Channel Name (override default): ").strip()
    date = input("📅 Custom Date (YYYY/MM/DD, or Enter for today): ").strip()
    thread_content = input("🧵 Thread Content (to find existing thread): ").strip()
    
    # Use today's date if not provided
    if not date:
        date = datetime.now().strftime("%Y/%m/%d")
    
    # Convert empty strings to None
    params = {
        'author': author,
        'receiver': receiver,
        'link': link,
        'raw_data_link': raw_data_link if raw_data_link else None,
        'channel': channel if channel else None,
        'date': date,
        'thread_content': thread_content if thread_content else None
    }
    
    return params

def call_slack_delivery(author, receiver, link, raw_data_link=None, channel=None, date=None, thread_content=None):
    """
    Call the slack delivery system and return the result
    """
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    slack_script = os.path.join(script_dir, 'slack_delivery_simple.py')
    
    # Build the command
    cmd = [
        'python3', slack_script,
        '--author', author,
        '--receiver', receiver,
        '--link', link
    ]
    
    # Add optional parameters
    if raw_data_link:
        cmd.extend(['--raw-data-link', raw_data_link])
    if channel:
        cmd.extend(['--channel', channel])
    if date:
        cmd.extend(['--date', date])
    if thread_content:
        cmd.extend(['--thread-content', thread_content])
    
    try:
        print(f"\n🚀 Executing command:")
        print(f"   {' '.join(cmd)}")
        print("")
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Show the raw output first
        print("📄 Raw Output:")
        print("-" * 40)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("Error output:")
            print(result.stderr)
        print("-" * 40)
        
        # Parse the JSON response
        if result.stdout:
            try:
                response = json.loads(result.stdout)
                return {
                    'success': True,
                    'exit_code': result.returncode,
                    'response': response,
                    'raw_output': result.stdout
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'exit_code': result.returncode,
                    'error': 'Invalid JSON response',
                    'raw_output': result.stdout,
                    'raw_error': result.stderr
                }
        else:
            return {
                'success': False,
                'exit_code': result.returncode,
                'error': 'No output received',
                'raw_error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Command timed out (30 seconds)'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def main():
    """Main interactive function"""
    
    # Check if token is set
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        print("❌ SLACK_BOT_TOKEN not set!")
        print("Please run: export SLACK_BOT_TOKEN='your-token-here'")
        sys.exit(1)
    
    print(f"✅ Using token: {token[:20]}...")
    print("")
    
    # Get user input
    params = get_user_input()
    
    # Show confirmation
    print("\n" + "=" * 60)
    print("📋 DELIVERY SUMMARY")
    print("=" * 60)
    print(f"Author: {params['author']}")
    print(f"Receiver: {params['receiver']}")
    print(f"Link: {params['link']}")
    if params['raw_data_link']:
        print(f"Raw Data Link: {params['raw_data_link']}")
    if params['channel']:
        print(f"Channel: {params['channel']}")
    print(f"Date: {params['date']}")
    if params['thread_content']:
        print(f"Thread Content: {params['thread_content']}")
    
    # Ask for confirmation
    print("")
    confirm = input("Proceed with delivery? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled by user")
        return
    
    # Execute delivery
    print("\n" + "=" * 60)
    print("🚀 EXECUTING DELIVERY")
    print("=" * 60)
    
    result = call_slack_delivery(**params)
    
    # Show final result
    print("\n" + "=" * 60)
    print("📊 FINAL RESULT")
    print("=" * 60)
    
    if result['success'] and result.get('response', {}).get('success'):
        print("✅ SUCCESS: Message delivered to Slack!")
        response = result.get('response', {})
        if 'timestamp' in response:
            print(f"📅 Timestamp: {response['timestamp']}")
        if 'channel' in response:
            print(f"📢 Channel: {response['channel']}")
    else:
        print("❌ FAILED:")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        if result.get('raw_error'):
            print(f"   Details: {result['raw_error']}")

if __name__ == "__main__":
    main()
