#!/usr/bin/env python3
import requests
import base64
import os
from dotenv import load_dotenv

# Define the URL
url = "https://noordwijk.accept.commonground.nu/apps/opencatalogi"

# Define credentials
# Get credentials from environment variables
username = os.getenv('API_USERNAME', '')
password = os.getenv('API_PASSWORD', '')

# Create basic auth header
auth_header = base64.b64encode(f"{username}:{password}".encode()).decode()

# Set headers
headers = {
    "Authorization": f"Basic {auth_header}"
}

# Set auth tuple
auth = (username, password)

print(f"Testing URL: {url}")
print(f"Using username: {username}, password: [FILTERED]")

try:
    # Make the request
    response = requests.get(url, headers=headers, auth=auth, timeout=10)
    
    # Print result
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    
    # Print a sample of the response body
    content_sample = response.text[:500] + "..." if len(response.text) > 500 else response.text
    print(f"Response content sample: {content_sample}")
    
except Exception as e:
    print(f"Error: {str(e)}")

print("Test completed.") 