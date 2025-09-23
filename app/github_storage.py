"""
GitHub Storage Module for accessing files in a private repository
"""
import json
import base64
import os
import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
import requests


class GitHubStorage:
    """Handle reading and writing files to a GitHub repository"""
    
    def __init__(self):
        """Initialize GitHub storage with credentials from Streamlit secrets or environment"""
        # Try to get from Streamlit secrets first, then environment
        try:
            self.repo_owner = st.secrets.get("GITHUB_REPO_OWNER") or os.getenv("GITHUB_REPO_OWNER", "KhangaridE")
            self.repo_name = st.secrets.get("GITHUB_REPO_NAME") or os.getenv("GITHUB_REPO_NAME", "nouhin_client_info")
            self.token = st.secrets.get("STORAGE_TOKEN") or os.getenv("STORAGE_TOKEN")
            self.branch = st.secrets.get("GITHUB_BRANCH") or os.getenv("GITHUB_BRANCH", "main")
        except:
            # Fallback to environment variables if Streamlit secrets not available
            self.repo_owner = os.getenv("GITHUB_REPO_OWNER", "KhangaridE")
            self.repo_name = os.getenv("GITHUB_REPO_NAME", "nouhin_client_info")
            self.token = os.getenv("STORAGE_TOKEN")
            self.branch = os.getenv("GITHUB_BRANCH", "main")
        
        if not self.token:
            raise ValueError("GitHub token not found in secrets or environment variables")
        
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Simple in-memory cache
        self._cache = {}
        self._cache_time = {}
        self.cache_duration = 60  # 60 seconds
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache or key not in self._cache_time:
            return False
        return (datetime.now().timestamp() - self._cache_time[key]) < self.cache_duration
    
    def _update_cache(self, key: str, data: Any):
        """Update cache with new data"""
        self._cache[key] = data
        self._cache_time[key] = datetime.now().timestamp()
    
    def read_file(self, file_path: str, use_cache: bool = True) -> Optional[Dict[Any, Any]]:
        """
        Read a JSON file from the repository
        
        Args:
            file_path: Path to the file in the repository (e.g., "reports.json")
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary content of the JSON file or None if not found
        """
        # Check cache first
        if use_cache and self._is_cache_valid(file_path):
            return self._cache[file_path]
        
        try:
            url = f"{self.base_url}/contents/{file_path}"
            params = {"ref": self.branch}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            file_data = response.json()
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            data = json.loads(content)
            
            # Update cache
            if use_cache:
                self._update_cache(file_path, data)
            
            return data
            
        except requests.exceptions.RequestException as e:
            # Handle 404 (file not found) silently - this is expected for new files
            if hasattr(e, 'response') and e.response.status_code == 404:
                print(f"File {file_path} not found in GitHub repo (will be created when needed)")
                return None
            
            error_msg = f"Error reading file {file_path} from GitHub: {e}"
            try:
                st.error(error_msg)
            except:
                print(error_msg)
            return None
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing JSON from {file_path}: {e}"
            try:
                st.error(error_msg)
            except:
                print(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected error reading {file_path}: {e}"
            try:
                st.error(error_msg)
            except:
                print(error_msg)
            return None
    
    def write_file(self, file_path: str, content: Dict[Any, Any], 
                   commit_message: Optional[str] = None) -> bool:
        """
        Write a JSON file to the repository
        
        Args:
            file_path: Path to the file in the repository
            content: Dictionary to write as JSON
            commit_message: Commit message (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current file SHA if it exists
            sha = self._get_file_sha(file_path)
            
            # Prepare content
            json_content = json.dumps(content, indent=2, ensure_ascii=False)
            encoded_content = base64.b64encode(json_content.encode("utf-8")).decode("utf-8")
            
            # Prepare commit message
            if not commit_message:
                commit_message = f"Update {file_path} - {datetime.now().isoformat()}"
            
            # Prepare data for API
            data = {
                "message": commit_message,
                "content": encoded_content,
                "branch": self.branch
            }
            
            if sha:
                data["sha"] = sha
            
            url = f"{self.base_url}/contents/{file_path}"
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            # Update cache
            self._update_cache(file_path, content)
            
            return True
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error writing file {file_path} to GitHub: {e}"
            try:
                st.error(error_msg)
            except:
                print(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error writing {file_path}: {e}"
            try:
                st.error(error_msg)
            except:
                print(error_msg)
            return False
    
    def _get_file_sha(self, file_path: str) -> Optional[str]:
        """Get the SHA of a file if it exists"""
        try:
            url = f"{self.base_url}/contents/{file_path}"
            params = {"ref": self.branch}
            
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                return response.json()["sha"]
            return None
            
        except requests.exceptions.RequestException:
            return None
    
    def test_connection(self) -> bool:
        """Test if the connection to the repository works"""
        try:
            url = f"{self.base_url}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            error_msg = f"GitHub connection test failed: {e}"
            try:
                st.error(error_msg)
            except:
                print(error_msg)
            return False
