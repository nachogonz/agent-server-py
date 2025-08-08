#!/usr/bin/env python3
"""
Verify LangSmith API key and basic functionality
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def verify_langsmith_api():
    """Verify LangSmith API key and test basic functionality."""
    
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ LANGSMITH_API_KEY not found in environment")
        return False
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    # Test API key by making a request to LangSmith API
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Check if we can access the API
    try:
        response = requests.get(
            "https://api.smith.langchain.com/runs",
            headers=headers,
            params={"limit": 1}
        )
        
        print(f"📊 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API key is valid and working!")
            data = response.json()
            print(f"📊 Found {len(data.get('runs', []))} runs")
            return True
        elif response.status_code == 401:
            print("❌ API key is invalid or expired")
            return False
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API request failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_langsmith_api()
    if success:
        print("🎉 LangSmith API verification PASSED!")
    else:
        print("💥 LangSmith API verification FAILED!")
        exit(1)
