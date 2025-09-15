#!/usr/bin/env python3
"""
JSON-based Test Script for Slack Delivery System
This version reads delivery parameters from a JSON file instead of interactive input
"""

import subprocess
import json
import os
import sys
from datetime import datetime

def load_arguments_from_json(json_file='arguments.json'):
    """Load delivery arguments from JSON file"""
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file '{json_file}' not found!")
        print("Please create the JSON file with your delivery parameters.")
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate required fields
        required_fields = ['author', 'receiver', 'link']
        for field in required_fields:
            if not data.get(field):
                print(f"❌ Required field '{field}' is missing or empty in JSON file")
                return None
        
        # Add default date if not provided
        if not data.get('date'):
            data['date'] = datetime.now().strftime("%Y/%m/%d")
        
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return None


def call_slack_delivery(author, receiver, link, raw_data_link=None, channel=None, date=None, thread_content=None, thread_ts=None, verbose=None):
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
    if thread_ts:
        cmd.extend(['--thread-ts', thread_ts])
    if verbose:
        cmd.append('--verbose')
    
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
    """Main function that reads from JSON and executes delivery"""
    
    # Check if token is set
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        print("❌ SLACK_BOT_TOKEN not set!")
        print("Please run: export SLACK_BOT_TOKEN='your-token-here'")
        sys.exit(1)
    
    print("=" * 60)
    print("🤖 JSON-BASED SLACK DELIVERY TEST")
    print("=" * 60)
    print(f"✅ Using token: {token[:20]}...")
    print("")
    
    # Handle command line arguments for custom JSON file
    json_file = '/Users/anarbatkhuu/Documents/delivery/client_package_final/arguments.json'
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    # Load arguments from JSON
    params = load_arguments_from_json(json_file)
    if not params:
        return
    
    # Show loaded parameters
    print("📋 LOADED PARAMETERS FROM JSON")
    print("=" * 60)
    print(f"Author: {params['author']}")
    print(f"Receiver: {params['receiver']}")
    print(f"Link: {params['link']}")
    if params.get('raw_data_link'):
        print(f"Raw Data Link: {params['raw_data_link']}")
    if params.get('channel'):
        print(f"Channel: {params['channel']}")
    print(f"Date: {params['date']}")
    if params.get('thread_content'):
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
