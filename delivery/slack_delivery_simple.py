#!/usr/bin/env python3
"""
Simple Slack Delivery for RPA Integration
Uses environment variables for secure token handling
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, List
from difflib import SequenceMatcher
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure minimal logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SlackDeliverySimple:
    """Simple Slack delivery for RPA integration"""
    
    def __init__(self, channel_name: Optional[str] = None):
        """Initialize with environment variables"""
        # Get token from environment variable (try both names for compatibility)
        self.bot_token = os.getenv('SLACK_BOT_TOKEN') or os.getenv('SLACK_TOKEN')
        self.default_channel_id = os.getenv('DELIVERY_TEST_SLACK_DEFAULT_CHANNEL_ID')
        
        if not self.bot_token:
            raise ValueError("SLACK_BOT_TOKEN or SLACK_TOKEN environment variable required")
        
        # Initialize client (use bot token for all operations)
        self.bot_client = WebClient(token=self.bot_token)
        self.user_client = self.bot_client  # Use same client for both operations
        
        # Cache for user lookups
        self._users_cache = None
        
        # Use provided channel or default from environment
        if channel_name:
            self.channel_id = self._get_channel_id(channel_name)
        else:
            self.channel_id = self.default_channel_id
            
        if not self.channel_id:
            raise ValueError("No channel specified and no DELIVERY_TEST_SLACK_DEFAULT_CHANNEL_ID environment variable")
    
    def _get_channel_id(self, channel_name: str) -> Optional[str]:
        """Get channel ID from channel name"""
        try:
            # Remove # if present
            channel_name = channel_name.lstrip('#')
            
            # Get channels list
            result = self.user_client.conversations_list(
                types="public_channel,private_channel",
                limit=1000
            )
            
            for channel in result['channels']:
                if channel['name'] == channel_name:
                    return channel['id']
            
            logger.error(f"Channel '{channel_name}' not found")
            return None
            
        except SlackApiError as e:
            logger.error(f"Error getting channel ID: {e}")
            return None
    
    def _get_users_list(self) -> List[Dict]:
        """Get and cache list of Slack users"""
        if self._users_cache is None:
            try:
                result = self.bot_client.users_list()
                # Filter active, non-bot users
                self._users_cache = [
                    user for user in result['members']
                    if not user.get('deleted', False) and not user.get('is_bot', False)
                ]
            except SlackApiError as e:
                logger.error(f"Error getting users list: {e}")
                self._users_cache = []
        
        return self._users_cache
    
    def _find_user_by_name(self, name: str) -> Optional[Dict]:
        """Find user by name (exact match first, then fuzzy matching) - returns full user info"""
        users = self._get_users_list()
        if not users:
            return None
        
        name_lower = name.lower()
        
        # First pass: Look for exact matches or substring matches
        for user in users:
            real_name = user.get('real_name', '').lower()
            username = user.get('name', '').lower()
            display_name = user.get('profile', {}).get('display_name', '').lower()
            
            # Exact match
            if (name_lower == real_name or name_lower == username or name_lower == display_name):
                return {
                    'user': user,
                    'score': 1.0,
                    'matched_field': 'exact_match'
                }
            
            # Substring match (like the reference function)
            if (name_lower in real_name or name_lower in username or name_lower in display_name):
                return {
                    'user': user,
                    'score': 0.9,
                    'matched_field': 'substring_match'
                }
        
        # Second pass: Fuzzy matching (only if no exact/substring match found)
        best_match = None
        best_score = 0.0
        
        for user in users:
            real_name = user.get('real_name', '').lower()
            username = user.get('name', '').lower()
            display_name = user.get('profile', {}).get('display_name', '').lower()
            
            # Calculate similarity scores
            scores = [
                SequenceMatcher(None, name_lower, real_name).ratio(),
                SequenceMatcher(None, name_lower, username).ratio(),
                SequenceMatcher(None, name_lower, display_name).ratio(),
            ]
            
            max_score = max(scores)
            if max_score > best_score and max_score > 0.8:  # High threshold for fuzzy matching
                best_score = max_score
                best_match = {
                    'user': user,
                    'score': max_score,
                    'matched_field': 'fuzzy_match'
                }
        
        return best_match
    
    def _convert_name_to_mention(self, name: str) -> str:
        """Convert name to Slack mention format with detailed logging"""
        match_result = self._find_user_by_name(name)
        
        if match_result:
            user = match_result['user']
            score = match_result['score']
            matched_field = match_result['matched_field']
            
            real_name = user.get('real_name', 'N/A')
            username = user.get('name', 'N/A')
            user_id = user.get('id', 'N/A')
            
            # Log the match details
            logger.info(f"Found user for '{name}': {real_name} (@{username}) - ID: {user_id}")
            logger.info(f"Match score: {score:.2%}, matched on: {matched_field}")
            
            return f"<@{user_id}>"
        else:
            # Return original name if user not found
            logger.warning(f"No user found for '{name}' (no matches above 80% threshold)")
            return f"@{name}"
    
    def _get_user_details(self, name: str) -> Dict:
        """Get detailed user information for response"""
        match_result = self._find_user_by_name(name)
        
        if match_result:
            user = match_result['user']
            return {
                "input_name": name,
                "real_name": user.get('real_name', 'N/A'),
                "username": user.get('name', 'N/A'),
                "user_id": user.get('id', 'N/A'),
                "display_format": f"{user.get('real_name', 'N/A')} (@{user.get('name', 'N/A')}) - ID: {user.get('id', 'N/A')}",
                "match_score": match_result['score'],
                "match_type": match_result['matched_field']
            }
        else:
            return {
                "input_name": name,
                "real_name": "Not found",
                "username": "Not found",
                "user_id": "Not found",
                "display_format": f"No user found for '{name}'",
                "match_score": 0.0,
                "match_type": "no_match"
            }
    
    def _find_matching_thread(self, thread_content: str = None) -> Optional[str]:
        """Find matching thread based on provided content text"""
        if not thread_content:
            logger.info("No thread content provided for matching")
            return None
        
        try:
            # Get recent messages from channel
            result = self.user_client.conversations_history(
                channel=self.channel_id,
                limit=50
            )
            
            messages = result.get('messages', [])
            thread_content_lower = thread_content.lower().strip()
            
            best_match = None
            best_score = 0.0
            
            for message in messages:
                message_text = message.get('text', '').lower().strip()
                
                # Skip empty messages or system messages
                if not message_text or message.get('subtype') == 'channel_join':
                    continue
                
                # Calculate text similarity between provided content and actual message text
                similarity_score = SequenceMatcher(None, thread_content_lower, message_text).ratio()
                
                # Also check if thread_content is a substring of the message (or vice versa)
                if (thread_content_lower in message_text or message_text in thread_content_lower):
                    similarity_score = max(similarity_score, 0.8)  # Boost for substring matches
                
                if similarity_score > best_score:
                    best_score = similarity_score
                    best_match = {
                        'timestamp': message.get('ts'),
                        'text': message.get('text', ''),
                        'score': similarity_score
                    }
            
            # Only return match if score is above threshold
            if best_match and best_score > 0.7:  # 70% similarity threshold
                thread_ts = best_match['timestamp']
                message_preview = best_match['text'][:100] + "..." if len(best_match['text']) > 100 else best_match['text']
                
                logger.info(f"Found matching thread (score: {best_score:.2%}):")
                logger.info(f"Thread TS: {thread_ts}")
                logger.info(f"Matched text: {message_preview}")
                logger.info(f"Your input: {thread_content}")
                
                return thread_ts
            else:
                logger.info(f"No matching thread found for content: '{thread_content}'")
                logger.info(f"Best match score was only {best_score:.2%} (below 70% threshold)")
                return None
                
        except SlackApiError as e:
            logger.error(f"Error finding matching thread: {e}")
            return None
    
    def send_type1_message(
        self,
        file_link: str,
        author: str,
        receiver: str,
        thread_content: Optional[str] = None,
        thread_ts: Optional[str] = None,
        custom_date: Optional[str] = None,
        raw_data_link: Optional[str] = None
    ) -> Dict:
        """Send Type 1 delivery message"""
        try:
            # Determine thread timestamp with stricter validation
            if thread_ts:
                # Client provided explicit thread timestamp
                target_thread_ts = thread_ts
                logger.info(f"Using provided thread timestamp: {thread_ts}")
            elif thread_content:
                # Client provided thread content - we MUST find a matching thread
                target_thread_ts = self._find_matching_thread(thread_content)
                if not target_thread_ts:
                    error_msg = f"Thread content was specified ('{thread_content}') but no matching thread found. Please check the thread content or remove --thread-content to create a new message."
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg,
                        "suggestion": "Remove --thread-content parameter to create a new message, or verify the thread content matches an existing message"
                    }
                logger.info(f"Found matching thread for content: '{thread_content}'")
            else:
                # No thread specified - create new message
                target_thread_ts = None
                logger.info("No thread parameters provided, will create new message")
            
            # Use custom date or current date
            if custom_date:
                date_str = custom_date
            else:
                date_str = datetime.now().strftime("%Y/%m/%d")
            
            # Convert names to proper Slack mentions
            receiver_mention = self._convert_name_to_mention(receiver)
            author_mention = self._convert_name_to_mention(author)
            
            # Create Japanese business style message with proper mentions
            message = f"{receiver_mention}\n"
            message += f"お世話になっております。\n"
            message += f"DDAMチームの{author_mention}でございます。\n\n"
            message += f"本日分の更新が完了致しましたのでご確認お願い致します。({date_str})\n\n"
            
            # Add raw data link if provided
            if raw_data_link:
                message += f"▼raw貼り付けスプシ\n"
                message += f"{raw_data_link}\n\n"
            
            message += f"▼格納先\n"
            message += f"{file_link}\n\n"
            message += f"お忙しいところ恐れ入りますが、何卒よろしくお願いいたします。"
            
            # Get user details for response
            author_details = self._get_user_details(author)
            receiver_details = self._get_user_details(receiver)
            
            # Send message
            if target_thread_ts:
                # Reply in thread
                result = self.bot_client.chat_postMessage(
                    channel=self.channel_id,
                    text=message,
                    thread_ts=target_thread_ts
                )
                
                return {
                    "success": True,
                    "message": "Message delivered successfully in thread",
                    "timestamp": result['ts'],
                    "channel": self.channel_id,
                    "thread_ts": target_thread_ts,
                    "author": author_details["display_format"],
                    "receiver": receiver_details["display_format"]
                }
            else:
                # Create new message
                result = self.bot_client.chat_postMessage(
                    channel=self.channel_id,
                    text=message
                )
                
                return {
                    "success": True,
                    "message": "New message created successfully",
                    "timestamp": result['ts'],
                    "channel": self.channel_id,
                    "author": author_details["display_format"],
                    "receiver": receiver_details["display_format"]
                }
                
        except SlackApiError as e:
            error_msg = f"Slack API error: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def send_type1_message_with_file(
        self,
        file_path: str,
        author: str,
        receiver: str,
        thread_content: Optional[str] = None,
        thread_ts: Optional[str] = None,
        custom_date: Optional[str] = None,
        raw_data_link: Optional[str] = None
    ) -> Dict:
        """Send type1 message with file attachment instead of link"""
        try:
            # First determine target thread
            target_thread_ts = None
            if thread_ts:
                # Use explicit thread timestamp
                target_thread_ts = thread_ts
                logger.info(f"Using explicit thread timestamp: {thread_ts}")
            elif thread_content:
                # Find thread by content similarity
                target_thread_ts = self._find_matching_thread(thread_content)
                if not target_thread_ts:
                    return {
                        "success": False,
                        "error": f"Could not find thread matching content: '{thread_content}'",
                        "suggestion": "Remove --thread-content parameter to create a new message, or verify the thread content matches an existing message"
                    }
                logger.info(f"Found matching thread for content: '{thread_content}'")
            else:
                # No thread specified - create new message
                target_thread_ts = None
                logger.info("No thread parameters provided, will create new message")
            
            # Use custom date or current date
            if custom_date:
                date_str = custom_date
            else:
                date_str = datetime.now().strftime("%Y/%m/%d")
            
            # Convert names to proper Slack mentions
            receiver_mention = self._convert_name_to_mention(receiver)
            author_mention = self._convert_name_to_mention(author)
            
            # Create Japanese business style message with proper mentions
            message = f"{receiver_mention}\n"
            message += f"お世話になっております。\n"
            message += f"DDAMチームの{author_mention}でございます。\n\n"
            message += f"本日分の更新が完了致しましたのでご確認お願い致します。({date_str})\n\n"
            
            # Add raw data link if provided
            if raw_data_link:
                message += f"▼raw貼り付けスプシ\n"
                message += f"{raw_data_link}\n\n"
            
            message += f"▼格納先\n"
            message += f"ファイルをアップロードしました（下記参照）\n\n"
            message += f"お忙しいところ恐れ入りますが、何卒よろしくお願いいたします。"
            
            # Get user details for response
            author_details = self._get_user_details(author)
            receiver_details = self._get_user_details(receiver)
            
            # Upload file
            with open(file_path, 'rb') as file_content:
                if target_thread_ts:
                    # Upload to thread
                    result = self.bot_client.files_upload_v2(
                        channel=self.channel_id,
                        file=file_content,
                        filename=os.path.basename(file_path),
                        initial_comment=message,
                        thread_ts=target_thread_ts
                    )
                    
                    return {
                        "success": True,
                        "message": "File uploaded to thread successfully",
                        "file_id": result['file']['id'],
                        "thread_ts": target_thread_ts,
                        "channel": self.channel_id,
                        "author": author_details["display_format"],
                        "receiver": receiver_details["display_format"]
                    }
                else:
                    # Upload as new message
                    result = self.bot_client.files_upload_v2(
                        channel=self.channel_id,
                        file=file_content,
                        filename=os.path.basename(file_path),
                        initial_comment=message
                    )
                    
                    return {
                        "success": True,
                        "message": "File uploaded successfully",
                        "file_id": result['file']['id'],
                        "timestamp": result.get('ts'),
                        "channel": self.channel_id,
                        "author": author_details["display_format"],
                        "receiver": receiver_details["display_format"]
                    }
                    
        except SlackApiError as e:
            error_msg = f"Slack API error: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }


def main():
    """Main function for RPA command line usage"""
    parser = argparse.ArgumentParser(description='Simple Slack Delivery for RPA')
    
    # Required arguments
    parser.add_argument('--link', required=True, help='File link/URL to share')
    parser.add_argument('--author', required=True, help='Report author name')
    parser.add_argument('--receiver', required=True, help='Person to mention/notify')
    
    # Optional arguments
    parser.add_argument('--channel', help='Slack channel name (overrides DELIVERY_TEST_SLACK_DEFAULT_CHANNEL_ID)')
    parser.add_argument('--raw-data-link', help='Raw data spreadsheet link (optional)')
    parser.add_argument('--thread-content', help='Text content to find matching thread')
    parser.add_argument('--thread-ts', help='Specific thread timestamp')
    parser.add_argument('--date', help='Custom date string (YYYY/MM/DD)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Enable verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    try:
        # Initialize delivery system
        delivery = SlackDeliverySimple(channel_name=args.channel)
        
        # Send message
        result = delivery.send_type1_message(
            file_link=args.link,
            author=args.author,
            receiver=args.receiver,
            thread_content=args.thread_content,
            thread_ts=args.thread_ts,
            custom_date=args.date,
            raw_data_link=getattr(args, 'raw_data_link', None)
        )
        
        # Output JSON response for RPA
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)
        
    except Exception as e:
        # Error response for RPA
        error_result = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
