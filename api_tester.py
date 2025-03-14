#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import yaml
import json
import logging
import requests
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from dotenv import load_dotenv
import base64

# Configure logging
def setup_logging():
    """Configure logging based on environment variables."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'api_test.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class APITester:
    def __init__(self, oas_path: str, base_url: str, tool: str):
        self.oas_path = oas_path
        self.base_url = base_url
        self.tool = tool
        self.report_file = "api_test_report.md"
        self.logger = logging.getLogger(__name__)
        
        # Default to read-only mode (only GET methods)
        self.read_only = True
        
        # CRUD testing results
        self.crud_results = {}
        self.test_id = str(uuid.uuid4())[:8]
        
        # Direct environment variable loading with debug info
        self.logger.debug("Environment variables available:")
        env_vars = {k: v for k, v in os.environ.items() if not (
            k.startswith('API_PASSWORD') or 
            k.startswith('API_TOKEN') or
            'SECRET' in k or 
            'KEY' in k
        )}
        for k, v in sorted(env_vars.items()):
            if k.startswith('API_'):
                self.logger.debug(f"  {k}={v}")
        
        # Check if .env file exists
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if not os.path.exists(env_path):
            self.logger.error(f".env file not found at {env_path}")
            self.logger.info("Creating .env file from example...")
            try:
                example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.example')
                if os.path.exists(example_path):
                    with open(example_path, 'r') as example, open(env_path, 'w') as env_file:
                        env_file.write(example.read())
                    self.logger.info(f".env file created at {env_path}. Please edit it with your credentials.")
                else:
                    self.logger.error(f".env.example file not found at {example_path}")
            except Exception as e:
                self.logger.error(f"Error creating .env file: {str(e)}")
        else:
            self.logger.info(f".env file found at {env_path}")
            # Debug: Print the contents of .env (excluding sensitive data)
            try:
                with open(env_path, 'r') as f:
                    env_content = f.readlines()
                    self.logger.debug(f".env file contains {len(env_content)} lines")
                    for line in env_content:
                        if line.strip() and not line.strip().startswith('#'):
                            key = line.split('=')[0].strip() if '=' in line else line.strip()
                            value = line.split('=')[1].strip() if '=' in line and len(line.split('=')) > 1 else "???"
                            if 'PASSWORD' not in key and 'TOKEN' not in key and 'SECRET' not in key and 'KEY' not in key:
                                self.logger.debug(f"  {key}={value}")
                            else:
                                self.logger.debug(f"  {key}=[FILTERED]")
            except Exception as e:
                self.logger.error(f"Error reading .env file: {str(e)}")
        
        # Load environment variables
        load_dotenv(dotenv_path=env_path, override=True)
        
        # Get API credentials from environment
        self.api_username = os.getenv('API_USERNAME', 'admin')  # Default to 'admin' if not set
        self.api_password = os.getenv('API_PASSWORD', 'admin')  # Default to 'admin' if not set
        self.api_token = os.getenv('API_TOKEN')
        
        # Ensure we have some authentication
        if not self.api_username or not self.api_password:
            self.logger.warning("Using default credentials - consider setting proper credentials in .env")
            self.api_username = 'admin'
            self.api_password = 'admin'
        
        # Debug log credentials (without exposing sensitive data)
        self.logger.debug(f"Using credentials - Username: {self.api_username}, "
                         f"Password: {'[FILTERED]' if self.api_password else 'missing'}, "
                         f"Token: {'[FILTERED]' if self.api_token else 'missing'}")
        
        self.logger.info(f"Initialized APITester with OAS file: {oas_path}, Base URL: {base_url}, Tool: {tool}")

    def validate_oas_file(self) -> bool:
        """Validate if the OAS file exists and is valid YAML/JSON."""
        self.logger.info(f"Validating OAS file: {self.oas_path}")
        
        if not os.path.exists(self.oas_path):
            self.logger.error(f"OAS file not found at {self.oas_path}")
            return False

        try:
            with open(self.oas_path, 'r') as f:
                if self.oas_path.endswith('.yaml') or self.oas_path.endswith('.yml'):
                    yaml.safe_load(f)
                    self.logger.info("Successfully validated YAML format")
                elif self.oas_path.endswith('.json'):
                    json.load(f)
                    self.logger.info("Successfully validated JSON format")
                else:
                    self.logger.error("OAS file must be YAML or JSON")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Invalid OAS file format: {str(e)}")
            return False

    def test_api_connection(self) -> bool:
        """Test if the API is accessible with the provided credentials."""
        self.logger.info(f"Testing API connection to {self.base_url}")
        
        # First, test without authentication - should get 401
        try:
            no_auth_response = requests.get(self.base_url, timeout=10)
            self.logger.info(f"No-auth test result: {no_auth_response.status_code}")
            
            if no_auth_response.status_code != 401:
                self.logger.warning(f"Expected 401 when not authenticated, got {no_auth_response.status_code}")
        except Exception as e:
            self.logger.error(f"Error testing without authentication: {str(e)}")
        
        # Now try with authentication
        try:
            headers = {"Accept": "application/json"}
            auth = None
            
            if self.api_token:
                headers['Authorization'] = f"Bearer {self.api_token}"
            elif self.api_username and self.api_password:
                auth = (self.api_username, self.api_password)
            
            # Try to make a simple GET request to the base URL
            response = requests.get(
                self.base_url, 
                headers=headers,
                auth=auth,
                timeout=10,
                verify=True
            )
            
            self.logger.info(f"API connection test result: {response.status_code}")
            
            # For an API endpoint, we're looking for a 200 or 401 response
            if response.status_code == 200:
                self.logger.info("Successfully authenticated to API")
                return True
            elif response.status_code == 401:
                self.logger.warning("Authentication failed - 401 Unauthorized")
                return False
            else:
                self.logger.error(f"API connection test failed with unexpected status code: {response.status_code}")
                
                # Log response content for debugging
                content_sample = response.text[:500] + "..." if len(response.text) > 500 else response.text
                self.logger.debug(f"Response content sample: {content_sample}")
                
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"API connection test failed with error: {str(e)}")
            return False
            
        return False

    def run_dredd(self) -> Tuple[int, str]:
        """Run Dredd tests and return exit code and output."""
        self.logger.info("Starting Dredd tests")
        try:
            cmd = ["dredd", "--verbose", "--reporter", "apiary"]
            
            # If in read-only mode, only test GET operations to avoid modifying data
            if self.read_only:
                cmd.extend(["--method", "GET"])
                self.logger.info("Testing only GET operations to avoid modifying data")
            else:
                self.logger.warning("Testing ALL HTTP methods - this may modify data!")
            
            # Add authentication if available
            if self.api_token:
                cmd.extend(["--header", f"Authorization: Bearer {self.api_token}"])
                self.logger.info("Using token-based authentication")
            elif self.api_username and self.api_password:
                # For Dredd, try multiple authentication approaches
                # 1. Use the --user flag for basic auth
                cmd.extend(["--user", f"{self.api_username}:{self.api_password}"])
                
                # 2. Add explicit Authorization header
                auth_header = base64.b64encode(f"{self.api_username}:{self.api_password}".encode()).decode()
                cmd.extend(["--header", f"Authorization: Basic {auth_header}"])
                
                self.logger.info(f"Using basic authentication with username: {self.api_username}")
            else:
                self.logger.warning("No authentication credentials provided. Tests may fail due to authentication issues.")
                # Remove hardcoded credentials - rely only on what's in .env
            
            # Add OAS file and base URL
            cmd.extend([self.oas_path, self.base_url])
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.logger.info(f"Dredd tests completed with exit code: {result.returncode}")
            return result.returncode, result.stdout + result.stderr
        except FileNotFoundError:
            self.logger.error("Dredd is not installed")
            return 1, "Error: Dredd is not installed. Please install it using: npm install -g dredd"
        except Exception as e:
            self.logger.error(f"Error running Dredd: {str(e)}")
            return 1, f"Error running Dredd: {str(e)}"

    def run_schemathesis(self) -> Tuple[int, str]:
        """Run Schemathesis tests and return exit code and output."""
        self.logger.info("Starting Schemathesis tests")
        try:
            # Build the command with the correct order and format
            # Schemathesis expects: schemathesis run schema_path [options]
            cmd = ["schemathesis", "run"]
            
            # Add schema path (must be first positional argument)
            cmd.append(self.oas_path)
            
            # Extract the base domain without path components to avoid path duplication
            base_domain = self.base_url
            if '/apps/' in self.base_url:
                # Extract just the domain portion
                base_domain = self.base_url.split('/apps/')[0]
                self.logger.info(f"Using domain-only base URL: {base_domain} to avoid path duplication")
            
            # Add options for API-specific behavior
            cmd.extend([
                "--checks=all",
                "--experimental=openapi-3.1",
                "--show-trace",
                "--validate-schema=false",
                "--max-response-time=30000",  # 30 seconds timeout
                "--hypothesis-max-examples=10",  # Reduce the number of examples to speed up testing
                "--base-url", base_domain
            ])
            
            # If in read-only mode, only test GET operations to avoid modifying data
            if self.read_only:
                cmd.extend(["--method", "GET"])
                self.logger.info("Testing only GET operations to avoid modifying data")
            else:
                self.logger.warning("Testing ALL HTTP methods - this may modify data!")
            
            # Add authentication if available
            if self.api_token:
                # Add token to Authorization header
                cmd.extend(["--header", f"Authorization: Bearer {self.api_token}"])
                self.logger.info("Using token-based authentication")
            elif self.api_username and self.api_password:
                # Use basic auth 
                cmd.extend(["--auth", f"{self.api_username}:{self.api_password}"])
                cmd.extend(["--auth-type", "basic"])
                
                # Log authentication being used (without sensitive data)
                self.logger.info(f"Using basic authentication with username: {self.api_username}")
                self.logger.debug(f"Auth string format: {self.api_username}:*****")
            else:
                self.logger.warning("No authentication credentials provided")
            
            # For OpenAPI endpoints, add extra headers that might be needed
            cmd.extend(["--header", "Accept: application/json"])
            
            self.logger.debug(f"Running command: {' '.join([c if not (self.api_password and self.api_password in c) else '******' for c in cmd])}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.logger.info(f"Schemathesis tests completed with exit code: {result.returncode}")
            return result.returncode, result.stdout + result.stderr
        except FileNotFoundError:
            self.logger.error("Schemathesis is not installed")
            return 1, "Error: Schemathesis is not installed. Please install it using: pip install schemathesis"
        except Exception as e:
            self.logger.error(f"Error running Schemathesis: {str(e)}")
            return 1, f"Error running Schemathesis: {str(e)}"

    def generate_report(self, exit_code: int, output: str) -> None:
        """Generate a markdown report with the test results."""
        self.logger.info("Generating test report")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "[PASSED]" if exit_code == 0 else "[FAILED]"
        
        # Start with basic information
        report_content = f"""# API Contract Test Report
Generated on: {timestamp}

## Test Configuration
- OAS File: {self.oas_path}
- Base URL: {self.base_url}
- Tool: {self.tool}
- Status: {status}
- Read-Only Mode: {"Yes - Only testing GET methods" if self.read_only else "No - Testing all HTTP methods"}
- Test ID: {self.test_id}

"""

        # Add CRUD test results if available
        if hasattr(self, 'crud_results') and self.crud_results:
            report_content += """## CRUD Test Results

The following table shows which HTTP methods are supported by each API endpoint:

| Endpoint | GET | POST | PATCH | PUT | DELETE | Object ID |
|----------|-----|------|-------|-----|--------|-----------|
"""
            for endpoint, results in self.crud_results.items():
                get_result = "YES" if results.get("GET", False) else "NO"
                post_result = "YES" if results.get("POST", False) else "NO"
                patch_result = "YES" if results.get("PATCH", False) else "NO"
                put_result = "YES" if results.get("PUT", False) else "NO"
                delete_result = "YES" if results.get("DELETE", False) else "NO"
                object_id = results.get("object_id", "N/A")
                
                report_content += f"| {endpoint} | {get_result} | {post_result} | {patch_result} | {put_result} | {delete_result} | {object_id} |\n"
            
            report_content += """
### CRUD Testing Summary

YES = Method successfully tested
NO = Method not supported or test failed
N/A = Test not run (e.g., in read-only mode)

"""
            
            # If read-only mode was enabled, add a note
            if self.read_only:
                report_content += """
> **Note**: CRUD tests were run in READ-ONLY mode, so only GET operations were fully tested.
> To test all methods (POST, PATCH, PUT, DELETE), run with the `--all-methods` flag.
"""
        
        # Add contract testing results
        report_content += f"""
## Contract Test Output
```bash
{output}
```
"""
        try:
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.logger.info(f"Report generated: {self.report_file}")
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            print("\nTest Results:")
            print(report_content)

    def run_tests(self) -> bool:
        """Run the selected test tool and generate a report."""
        self.logger.info("Starting test execution")
        
        # First validate the OAS file
        if not self.validate_oas_file():
            return False
            
        # Test the API connection first
        api_accessible = self.test_api_connection()
        if not api_accessible:
            self.logger.warning("API connection test failed. Authentication may be required.")
            self.logger.warning("Tests will continue but may fail due to authentication issues.")
            
            # Add a note to the report about the authentication issues
            report_content = f"""# API Connection Test Failed

The API at {self.base_url} returned a 401 Unauthorized response.

This could be due to:
1. Invalid credentials in the .env file
2. The API requires a different authentication method
3. The API requires a session-based login instead of basic authentication

## Recommendations:
- Verify your credentials
- Try accessing the API through a browser to understand its authentication mechanism
- Check the API documentation for authentication requirements

---
"""
            try:
                with open("api_auth_note.md", 'w', encoding='utf-8') as f:
                    f.write(report_content)
                self.logger.info("Authentication issue note written to api_auth_note.md")
            except Exception as e:
                self.logger.error(f"Error writing authentication note: {str(e)}")
        
        # Test some basic endpoints defined in the OAS to see if they exist
        # This helps identify if the OAS spec matches the actual API implementation
        self.logger.info("Testing some endpoints defined in the OAS...")
        try:
            # This is a crude check - in a real implementation, we'd parse the OAS file to get endpoints
            test_endpoints = ["/catalogi", "/api", "/api/catalogi", "/organizaties"]
            found_endpoints = 0
            working_endpoints = []
            
            for endpoint in test_endpoints:
                test_url = f"{self.base_url}{endpoint}"
                try:
                    auth = (self.api_username, self.api_password) if self.api_username and self.api_password else None
                    resp = requests.get(test_url, auth=auth, headers={"Accept": "application/json"}, timeout=10)
                    self.logger.info(f"Endpoint {endpoint}: Status {resp.status_code}")
                    
                    if resp.status_code == 200:
                        found_endpoints += 1
                        working_endpoints.append(endpoint)
                        self.logger.info(f"Found working endpoint: {endpoint}")
                        
                        # Try to parse JSON
                        try:
                            json_data = resp.json()
                            self.logger.debug(f"Response: {json_data}")
                        except ValueError:
                            self.logger.warning(f"Endpoint {endpoint} returned non-JSON response")
                    elif resp.status_code == 404:
                        self.logger.warning(f"Endpoint {endpoint} not found (404)")
                except Exception as e:
                    self.logger.error(f"Error testing endpoint {endpoint}: {str(e)}")
            
            # Run CRUD tests on working endpoints
            if working_endpoints:
                self.logger.info("Running CRUD tests on working endpoints")
                self.crud_results = self.run_crud_tests(working_endpoints)
                self.logger.info(f"CRUD tests completed: {json.dumps(self.crud_results, indent=2)}")
            
            # If we found working endpoints but they're not in OAS, suggest adding them
            if found_endpoints > 0:
                self.logger.info(f"Found {found_endpoints} working endpoints: {', '.join(working_endpoints)}")
                
                # Look specifically for /api/catalogi since we know it works
                if "/api/catalogi" in working_endpoints:
                    self.logger.info("The /api/catalogi endpoint works but might not be in your OAS specification!")
                    
                    # Create a note with working endpoints
                    working_endpoints_note = f"""# Working API Endpoints Found

While testing the API at {self.base_url}, we found these working endpoints:

{chr(10).join(['- ' + endpoint for endpoint in working_endpoints])}

These endpoints work correctly but might not be defined in your OpenAPI specification ({self.oas_path}).

## Recommendation:
Consider updating your OAS specification to include these working endpoints for more accurate testing.

---
"""
                    try:
                        with open("api_working_endpoints.md", 'w', encoding='utf-8') as f:
                            f.write(working_endpoints_note)
                        self.logger.info("Working endpoints note written to api_working_endpoints.md")
                    except Exception as e:
                        self.logger.error(f"Error writing working endpoints note: {str(e)}")
            
            if found_endpoints == 0:
                self.logger.warning("None of the tested endpoints were found. The OAS specification may not match this server implementation.")
                # Create a warning file
                warning_content = f"""# OAS Specification Warning

The OpenAPI specification file ({self.oas_path}) may not match the actual API implementation at {self.base_url}.

None of the test endpoints were found (all returned 404 Not Found).

This could mean:
1. The API is hosted at a different base URL
2. The API implementation doesn't include the paths defined in the specification
3. The specification is for a different version of the API

## Recommendation:
Verify that the OAS file matches the actual API implementation. The tests will continue but may report failures due to missing endpoints.

---
"""
                try:
                    with open("api_oas_mismatch.md", 'w', encoding='utf-8') as f:
                        f.write(warning_content)
                    self.logger.info("OAS mismatch warning written to api_oas_mismatch.md")
                except Exception as e:
                    self.logger.error(f"Error writing OAS mismatch warning: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error testing endpoints: {str(e)}")
        
        # Run the selected test tool (Dredd or Schemathesis)
        self.logger.info(f"Running {self.tool} tests...")
        if self.tool == "dredd":
            exit_code, output = self.run_dredd()
        else:  # schemathesis
            exit_code, output = self.run_schemathesis()

        # Generate a comprehensive report including CRUD test results
        self.generate_report(exit_code, output)
        return exit_code == 0

    def extract_object_structure(self, endpoint: str) -> Dict[str, Any]:
        """Extract a sample object structure from a GET response."""
        self.logger.info(f"Extracting object structure from {endpoint}...")
        
        url = f"{self.base_url}{endpoint}"
        try:
            auth = (self.api_username, self.api_password) if self.api_username and self.api_password else None
            headers = {"Accept": "application/json"}
            
            response = requests.get(
                url, 
                auth=auth, 
                headers=headers,
                timeout=int(os.getenv('API_TIMEOUT', '60'))
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to get objects from {endpoint}: Status {response.status_code}")
                return {}
                
            try:
                data = response.json()
                
                # Look for results array in common API response format
                if 'results' in data and isinstance(data['results'], list) and len(data['results']) > 0:
                    sample_object = data['results'][0]
                    self.logger.info(f"Found sample object in results array")
                    return sample_object
                    
                # Alternative: check if it's a single object with fields
                elif isinstance(data, dict) and len(data) > 0 and any(key not in ['total', 'page', 'pages'] for key in data.keys()):
                    self.logger.info(f"Found single object")
                    return data
                    
                else:
                    self.logger.warning(f"No suitable object structure found in response from {endpoint}")
                    return {}
                    
            except ValueError:
                self.logger.error(f"Response from {endpoint} is not valid JSON")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error extracting object structure from {endpoint}: {str(e)}")
            return {}
    
    def create_test_object(self, endpoint: str, template: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Create a test object using the provided template structure."""
        self.logger.info(f"Creating test object at {endpoint}...")
        
        # Create a new object based on the template, but simplified
        test_object = {}
        
        # List of properties to exclude from the test object
        exclude_properties = ['id', '@id', '@self', 'uri', 'dateCreated', 'dateModified', 'uuid']
        
        # Add relevant properties from the template
        for key, value in template.items():
            if key not in exclude_properties:
                # For string values, create test values
                if isinstance(value, str):
                    test_object[key] = f"Test {key} {self.test_id}"
                # For boolean values, keep them
                elif isinstance(value, bool):
                    test_object[key] = value
                # For numeric values, use the same
                elif isinstance(value, (int, float)):
                    test_object[key] = value
                # For simple arrays, create a simple test array
                elif isinstance(value, list) and len(value) > 0:
                    test_object[key] = [f"Test item {self.test_id}"]
                # For objects, create a simplified object
                elif isinstance(value, dict):
                    test_object[key] = {"name": f"Test {key} {self.test_id}"}
        
        # Add required test properties
        test_object["name"] = f"API Test Object {self.test_id}"
        test_object["description"] = f"Created for API testing on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Try to create the object
        url = f"{self.base_url}{endpoint}"
        try:
            auth = (self.api_username, self.api_password) if self.api_username and self.api_password else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            
            response = requests.post(
                url,
                auth=auth,
                headers=headers,
                json=test_object,
                timeout=int(os.getenv('API_TIMEOUT', '60'))
            )
            
            self.logger.info(f"POST Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                self.logger.info("Successfully created test object")
                
                try:
                    created_object = response.json()
                    
                    # Extract the ID of the created object for later operations
                    object_id = None
                    
                    # Try different common ID field names
                    if '@self' in created_object and 'id' in created_object['@self']:
                        object_id = str(created_object['@self']['id'])
                    elif 'id' in created_object:
                        object_id = str(created_object['id'])
                    elif '@id' in created_object:
                        object_id = str(created_object['@id'])
                    elif 'uuid' in created_object:
                        object_id = str(created_object['uuid'])
                    # Try to extract from URI if available
                    elif '@self' in created_object and 'uri' in created_object['@self']:
                        uri = created_object['@self']['uri']
                        object_id = uri.split('/')[-1]
                    
                    if object_id:
                        self.logger.info(f"Created object ID: {object_id}")
                        return True, created_object, object_id
                    else:
                        self.logger.warning("Could not extract ID from created object")
                        return True, created_object, None
                    
                except ValueError:
                    self.logger.error("Response is not valid JSON")
                    return True, {'raw_response': response.text[:500]}, None
            else:
                self.logger.error(f"Failed to create object: Status {response.status_code}")
                self.logger.error(f"Response: {response.text[:500]}")
                return False, None, None
                
        except Exception as e:
            self.logger.error(f"Error creating test object: {str(e)}")
            return False, None, None
    
    def update_test_object(self, endpoint: str, object_id: str, original_object: Dict[str, Any]) -> bool:
        """Update the test object with PATCH."""
        self.logger.info(f"Updating test object {object_id} at {endpoint}...")
        
        # Create an update with modified values
        update_object = {
            "name": f"Updated Test Object {self.test_id}",
            "description": f"Updated via API testing on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        
        # Add one additional field from the original object if possible
        for key, value in original_object.items():
            if key not in ['id', '@id', '@self', 'name', 'description', 'dateCreated', 'dateModified', 'uuid'] and isinstance(value, str):
                update_object[key] = f"Updated {key} {self.test_id}"
                break
        
        # Try to update the object
        url = f"{self.base_url}{endpoint}/{object_id}"
        try:
            auth = (self.api_username, self.api_password) if self.api_username and self.api_password else None
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            
            response = requests.patch(
                url,
                auth=auth,
                headers=headers,
                json=update_object,
                timeout=int(os.getenv('API_TIMEOUT', '60'))
            )
            
            self.logger.info(f"PATCH Status: {response.status_code}")
            
            if response.status_code in [200, 201, 204]:
                self.logger.info("Successfully updated test object")
                
                if response.status_code != 204:  # 204 means no content
                    try:
                        updated_object = response.json()
                        self.logger.info(f"Updated object: {json.dumps(updated_object, indent=2)[:500]}")
                    except ValueError:
                        self.logger.info("Response is not JSON (might be empty for 204 status)")
                
                return True
            else:
                self.logger.error(f"Failed to update object: Status {response.status_code}")
                self.logger.error(f"Response: {response.text[:500]}")
                
                # Try PUT if PATCH fails
                self.logger.info("Trying PUT instead of PATCH...")
                try:
                    # For PUT, we typically need to send the full object
                    full_update = original_object.copy()
                    full_update.update(update_object)
                    
                    # Remove server-generated fields
                    for field in ['@self', '@id', 'dateCreated', 'dateModified']:
                        if field in full_update:
                            del full_update[field]
                    
                    put_response = requests.put(
                        url,
                        auth=auth,
                        headers=headers,
                        json=full_update,
                        timeout=int(os.getenv('API_TIMEOUT', '60'))
                    )
                    
                    self.logger.info(f"PUT Status: {put_response.status_code}")
                    
                    if put_response.status_code in [200, 201, 204]:
                        self.logger.info("Successfully updated test object with PUT")
                        return True
                    else:
                        self.logger.error(f"PUT also failed: Status {put_response.status_code}")
                        return False
                        
                except Exception as e:
                    self.logger.error(f"Error during PUT: {str(e)}")
                    return False
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating test object: {str(e)}")
            return False
    
    def delete_test_object(self, endpoint: str, object_id: str) -> bool:
        """Delete the test object."""
        self.logger.info(f"Deleting test object {object_id} at {endpoint}...")
        
        url = f"{self.base_url}{endpoint}/{object_id}"
        try:
            auth = (self.api_username, self.api_password) if self.api_username and self.api_password else None
            headers = {"Accept": "application/json"}
            
            response = requests.delete(
                url,
                auth=auth,
                headers=headers,
                timeout=int(os.getenv('API_TIMEOUT', '60'))
            )
            
            self.logger.info(f"DELETE Status: {response.status_code}")
            
            if response.status_code in [200, 202, 204]:
                self.logger.info("Successfully deleted test object")
                return True
            else:
                self.logger.error(f"Failed to delete object: Status {response.status_code}")
                self.logger.error(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting test object: {str(e)}")
            return False
    
    def run_crud_tests(self, working_endpoints: List[str]) -> Dict[str, Dict[str, Any]]:
        """Run CRUD tests on the provided endpoints."""
        self.logger.info("Starting CRUD tests")
        
        crud_results = {}
        
        for endpoint in working_endpoints:
            self.logger.info(f"\n=== Testing CRUD operations on {endpoint} ===")
            
            endpoint_results = {
                "GET": False,
                "POST": False,
                "PATCH": False,
                "PUT": False,
                "DELETE": False,
                "object_id": None
            }
            
            # Step 1: Get object structure
            template = self.extract_object_structure(endpoint)
            
            if template:
                endpoint_results["GET"] = True
                self.logger.info(f"GET test successful on {endpoint}")
            else:
                self.logger.warning(f"GET test failed on {endpoint}")
                # Skip remaining tests if we can't get objects
                crud_results[endpoint] = endpoint_results
                continue
            
            # Skip modification operations if in read-only mode
            if self.read_only:
                self.logger.info("Skipping POST/PATCH/DELETE tests in read-only mode")
                crud_results[endpoint] = endpoint_results
                continue
                
            # Step 2: Create test object
            create_success, created_object, object_id = self.create_test_object(endpoint, template)
            
            if create_success and object_id:
                endpoint_results["POST"] = True
                endpoint_results["object_id"] = object_id
                self.logger.info(f"POST test successful on {endpoint}")
            else:
                self.logger.warning(f"POST test failed on {endpoint}")
                # Skip remaining tests if we can't create objects
                crud_results[endpoint] = endpoint_results
                continue
                
            # Step 3: Update test object
            update_success = self.update_test_object(endpoint, object_id, created_object)
            
            if update_success:
                # Determine which operation succeeded (PATCH or PUT)
                if "Successfully updated test object with PUT" in self.logger.handlers[0].formatter.format():
                    endpoint_results["PUT"] = True
                    self.logger.info(f"PUT test successful on {endpoint}")
                else:
                    endpoint_results["PATCH"] = True
                    self.logger.info(f"PATCH test successful on {endpoint}")
            else:
                self.logger.warning(f"UPDATE test failed on {endpoint}")
            
            # Step 4: Delete test object
            delete_success = self.delete_test_object(endpoint, object_id)
            
            if delete_success:
                endpoint_results["DELETE"] = True
                self.logger.info(f"DELETE test successful on {endpoint}")
            else:
                self.logger.warning(f"DELETE test failed on {endpoint}")
            
            crud_results[endpoint] = endpoint_results
            
        return crud_results

def main():
    """Main entry point for the API Contract Testing CLI."""
    logger = setup_logging()
    logger.info("Starting API Contract Testing CLI")
    
    parser = argparse.ArgumentParser(description="Test an API against its OpenAPI Specification")
    parser.add_argument("--oas", required=True, help="Path to the OpenAPI Specification file")
    parser.add_argument("--url", required=False, help="Base URL of the API")
    parser.add_argument("--tool", required=True, choices=["dredd", "schemathesis"], help="Testing tool to use")
    parser.add_argument("--username", help="API username (overrides .env)")
    parser.add_argument("--password", help="API password (overrides .env)")
    parser.add_argument("--token", help="API token (overrides .env)")
    parser.add_argument("--read-only", action="store_true", default=True, help="Only test GET methods (default)")
    parser.add_argument("--all-methods", action="store_false", dest="read_only", help="Test all HTTP methods (may modify data)")
    
    args = parser.parse_args()
    logger.info(f"Parsed arguments: OAS={args.oas}, URL={args.url if args.url else 'from .env'}, Tool={args.tool}")
    
    if not args.read_only:
        logger.warning("Testing ALL HTTP methods - this may modify data on the API server!")
    
    # Load environment variables with higher precedence for command-line args
    load_dotenv()
    
    # Use URL from .env if not provided in command line
    if not args.url:
        env_url = os.getenv('API_BASE_URL')
        if env_url:
            args.url = env_url
            logger.info(f"Using base URL from .env: {args.url}")
        else:
            logger.error("No URL provided and API_BASE_URL not found in .env")
            parser.print_help()
            sys.exit(1)
    
    # Create and run the API tester
    api_tester = APITester(args.oas, args.url, args.tool)
    
    # Set authentication details if provided via command line
    if args.username:
        api_tester.api_username = args.username
    if args.password:
        api_tester.api_password = args.password
    if args.token:
        api_tester.api_token = args.token
    
    # Set read-only mode
    api_tester.read_only = args.read_only
    
    # Run the tests
    success = api_tester.run_tests()
    
    if not success:
        logger.error("Tests failed. Check the report for details.")
        sys.exit(1)
    
    logger.info("Tests completed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main() 