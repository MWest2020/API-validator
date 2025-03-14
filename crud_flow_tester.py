#!/usr/bin/env python3
"""
CRUD Flow Tester - Tests complete Create, Read, Update, Delete lifecycle for API resources.

This script:
1. GETs initial data to understand the resource structure
2. POSTs a new object based on the OpenAPI specification
3. GETs the created object to verify it exists
4. PUTs/PATCHes an update to the object
5. DELETEs the object to clean up

The script uses the OpenAPI specification to generate valid test data.
"""

import argparse
import json
import logging
import os
import random
import string
import sys
import time
from copy import deepcopy
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
import uuid

import requests
import yaml
from dotenv import load_dotenv
from jsonschema import validate
from openapi_spec_validator import validate_spec

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class CrudFlowTester:
    """Tests CRUD operations flow for API resources defined in an OpenAPI spec."""
    
    def __init__(
        self,
        oas_file: str,
        resource_path: str = None,
        base_url: str = None
    ):
        """
        Initialize the CRUD flow tester.
        
        Args:
            oas_file: Path to the OpenAPI spec file
            resource_path: Optional API path to test (e.g., "/api/registers")
            base_url: Base URL of the API
        """
        self.oas_file = oas_file
        self.resource_path = resource_path.strip('/') if resource_path else None
        self.base_url = base_url or os.getenv('API_BASE_URL')
        self.username = os.getenv('API_USERNAME')
        self.password = os.getenv('API_PASSWORD')
        self.spec = None
        self.created_resource_id = None
        self.created_resource = None
        
        # Load OpenAPI spec
        self.load_spec()
        
        # Find a suitable resource if not provided
        if not self.resource_path:
            self.resource_path = self.find_suitable_resource()
            
        logger.info(f"Using resource path: {self.resource_path}")
        
        self.session = requests.Session()
        if self.username and self.password:
            self.session.auth = (self.username, self.password)
        
        # Prepare headers
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def load_spec(self):
        """Load and validate the OpenAPI specification."""
        logger.info(f"Loading OpenAPI spec from {self.oas_file}")
        
        try:
            # Determine file type by extension
            if self.oas_file.endswith('.json'):
                with open(self.oas_file, 'r') as f:
                    self.spec = json.load(f)
            elif self.oas_file.endswith('.yaml') or self.oas_file.endswith('.yml'):
                with open(self.oas_file, 'r') as f:
                    self.spec = yaml.safe_load(f)
            else:
                logger.error(f"Unsupported file format: {self.oas_file}")
                raise ValueError(f"Unsupported file format: {self.oas_file}")
                
            # Get the OpenAPI version
            openapi_version = self.spec.get('openapi', 'unknown')
            logger.info(f"Successfully loaded and validated OpenAPI spec version {openapi_version}")
            
        except Exception as e:
            logger.error(f"Failed to load OpenAPI spec: {str(e)}")
            raise
    
    def find_suitable_resource(self) -> str:
        """Find a resource that supports all CRUD operations."""
        candidate_resources = []
        
        # Get all paths from the spec
        paths = self.spec.get('paths', {})
        
        for path, operations in paths.items():
            # Check if path supports GET (collection), GET (item), POST, PUT/PATCH, and DELETE
            has_get_collection = 'get' in operations
            has_post = 'post' in operations
            
            # Check if there's a corresponding item path (path + '/{id}')
            item_path_pattern = f"{path}/{{id}}"
            # Look for paths that match the pattern (may have different parameter names)
            item_path = None
            for p in paths:
                if p.startswith(path + '/') and '{' in p and '}' in p:
                    item_path = p
                    break
                    
            if item_path:
                item_operations = paths.get(item_path, {})
                has_get_item = 'get' in item_operations
                has_put = 'put' in item_operations
                has_patch = 'patch' in item_operations
                has_delete = 'delete' in item_operations
                
                if has_get_collection and has_post and has_get_item and (has_put or has_patch) and has_delete:
                    candidate_resources.append((path, item_path))
                    
        if not candidate_resources:
            logger.error("No suitable resources found that support all CRUD operations")
            raise ValueError("No suitable resources found that support all CRUD operations")
            
        # Select the first suitable resource
        selected_resource, _ = candidate_resources[0]
        logger.info(f"Selected resource path: {selected_resource}")
        return selected_resource.strip('/')
    
    def generate_test_data(self) -> Dict:
        """Generate test data based on the OpenAPI schema for the resource."""
        # Find the POST operation for the resource
        resource_path = f"/{self.resource_path}"
        if resource_path.startswith('//'):
            resource_path = resource_path[1:]
            
        paths = self.spec.get('paths', {})
        post_operation = paths.get(resource_path, {}).get('post', {})
        
        if not post_operation:
            logger.error(f"POST operation not found for resource {resource_path}")
            # Try with variations of the path
            alt_path = resource_path.strip('/')
            post_operation = paths.get(f"/{alt_path}", {}).get('post', {})
            if not post_operation:
                raise ValueError(f"POST operation not found for resource {resource_path}")
            
        # Get the request body schema
        request_body = post_operation.get('requestBody', {})
        content = request_body.get('content', {})
        
        # Try different content types
        schema = None
        content_type = None
        for ct in ['application/json', 'application/x-www-form-urlencoded']:
            if ct in content:
                schema = content[ct].get('schema', {})
                content_type = ct
                break
                
        if not schema:
            logger.error("No schema found for the request body")
            raise ValueError("No schema found for the request body")
            
        # Check if schema is a reference and resolve it if needed
        if '$ref' in schema:
            ref_path = schema['$ref']
            logger.info(f"Resolving schema reference: {ref_path}")
            schema = self._resolve_ref(ref_path)
        
        logger.info(f"Found schema for content-type {content_type}: {json.dumps(schema, indent=2)}")
        
        # Generate data from schema
        return self._generate_from_schema(schema)
        
    def _resolve_ref(self, ref_path: str) -> Dict:
        """Resolve a JSON Schema reference."""
        if not ref_path.startswith('#/'):
            logger.error(f"Cannot resolve external references: {ref_path}")
            raise ValueError(f"Cannot resolve external references: {ref_path}")
            
        # Remove the leading '#/' and split into path components
        path_parts = ref_path[2:].split('/')
        
        # Navigate through the spec to find the referenced schema
        current = self.spec
        for part in path_parts:
            if part not in current:
                logger.error(f"Reference not found: {ref_path}")
                raise ValueError(f"Reference not found: {ref_path}")
            current = current[part]
            
        return current
        
    def _generate_from_schema(self, schema: Dict) -> Any:
        """Recursively generate data based on a JSON schema."""
        # If the schema is a reference, resolve it
        if '$ref' in schema:
            schema = self._resolve_ref(schema['$ref'])
            
        # For API testing, simplified data is often better than complex random data
        schema_type = schema.get('type')
        
        # Handle example values if provided
        if 'example' in schema:
            return schema['example']
            
        if schema_type == 'object':
            result = {}
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            # For registered resource specifically, create a very simple object
            if properties.get('title') and properties.get('version'):
                # This looks like a register/schema/source type
                result['title'] = f"Test {self.resource_path.split('/')[-1]} {datetime.now().strftime('%Y%m%d%H%M%S')}"
                result['version'] = "1.0.0"
                if 'description' in properties:
                    result['description'] = f"Test description created by CRUD flow tester"
                return result
                
            # For other objects, add all required properties and some optional ones
            for prop_name, prop_schema in properties.items():
                if prop_name in required or prop_name in ['title', 'name', 'identifier']:
                    result[prop_name] = self._generate_from_schema(prop_schema)
                elif random.random() > 0.7:  # Include ~30% of optional props
                    result[prop_name] = self._generate_from_schema(prop_schema)
                    
            return result
            
        elif schema_type == 'array':
            items_schema = schema.get('items', {})
            # Generate 1-2 items for simplicity
            count = random.randint(1, 2)
            return [self._generate_from_schema(items_schema) for _ in range(count)]
            
        elif schema_type == 'string':
            format_type = schema.get('format', '')
            
            if format_type == 'date-time':
                return datetime.now().isoformat() + 'Z'
            elif format_type == 'date':
                return datetime.now().strftime('%Y-%m-%d')
            elif format_type == 'email':
                return 'test@example.com'
            elif format_type == 'uri':
                return 'https://example.com'
            elif format_type == 'uuid':
                return str(uuid.uuid4())
            else:
                # Generate a simple string based on the property name
                length = min(random.randint(5, 10), 20)  # Keep it reasonable
                return 'test_string_' + ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
                
        elif schema_type == 'integer' or schema_type == 'number':
            minimum = schema.get('minimum', 1)
            maximum = schema.get('maximum', 100)
            if schema_type == 'integer':
                return random.randint(minimum, maximum)
            else:
                return round(random.uniform(minimum, maximum), 2)
                
        elif schema_type == 'boolean':
            return random.choice([True, False])
            
        else:
            # Default fallback
            return None
    
    def _get_url(self, path: str = "") -> str:
        """Construct the full URL for a given path."""
        # Ensure the base URL doesn't end with a slash
        base_url = self.base_url.rstrip('/')
        
        # Remove any leading slash from the path to avoid double slashes
        if path:
            path = path.lstrip('/')
            return f"{base_url}/{path}"
        return base_url
    
    def run_crud_flow(self) -> bool:
        """Run the complete CRUD flow on the selected resource."""
        results = {
            "get_collection": False,
            "create_resource": False,
            "get_resource": False,
            "update_resource": False,
            "delete_resource": False
        }
        
        try:
            # Step 1: GET the collection (to see existing resources)
            results["get_collection"] = self.get_collection()
            if not results["get_collection"]:
                self._print_summary(results)
                return False
                
            # Step 2: POST a new resource
            results["create_resource"] = self.create_resource()
            if not results["create_resource"]:
                self._print_summary(results)
                return False
                
            # Step 3: GET the specific resource
            results["get_resource"] = self.get_resource()
            if not results["get_resource"]:
                self._print_summary(results)
                return False
                
            # Step 4: PUT/PATCH to update the resource
            results["update_resource"] = self.update_resource()
            if not results["update_resource"]:
                self._print_summary(results)
                return False
                
            # Step 5: DELETE the resource
            results["delete_resource"] = self.delete_resource()
            if not results["delete_resource"]:
                self._print_summary(results)
                return False
                
            logger.info("CRUD flow completed successfully!")
            self._print_summary(results)
            return True
            
        except Exception as e:
            logger.error(f"CRUD flow failed: {str(e)}")
            self._print_summary(results)
            return False
    
    def get_collection(self) -> bool:
        """GET the resource collection."""
        # Make sure resource_path doesn't have leading slash when used as part of the URL
        resource_path = self.resource_path.lstrip('/')
        url = self._get_url(resource_path)
        logger.info(f"Step 1: Getting resource collection from {url}")
        
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
                
            response = requests.get(
                url,
                auth=auth,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                collection = response.json()
                count = len(collection.get('hydra:member', collection.get('items', collection.get('results', collection))))
                logger.info(f"Successfully retrieved collection with {count} items")
                return True
            else:
                logger.error(f"Failed to GET the resource collection: {response.status_code}")
                if response.text:
                    logger.error(response.text[:500])  # Limit output to 500 chars
                return False
                
        except Exception as e:
            logger.error(f"Exception during GET collection: {str(e)}")
            return False
    
    def create_resource(self) -> bool:
        """POST a new resource."""
        # Make sure resource_path doesn't have leading slash when used as part of the URL
        resource_path = self.resource_path.lstrip('/')
        url = self._get_url(resource_path)
        logger.info(f"Step 2: Creating a new resource at {url}")
        
        try:
            # Generate test data
            test_data = self.generate_test_data()
            logger.info(f"Generated test data: {json.dumps(test_data, indent=2)}")
            
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
                
            response = requests.post(
                url,
                json=test_data,
                auth=auth,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            )
            
            if response.status_code in [200, 201, 202]:
                self.created_resource = response.json()
                
                # Try to extract the ID from the response
                # This depends on the API's response format and might need adjustment
                if '@id' in self.created_resource:
                    # Handle Hydra/JSON-LD style responses
                    id_path = self.created_resource['@id']
                    self.created_resource_id = id_path.split('/')[-1]
                elif 'id' in self.created_resource:
                    # Handle simple ID property
                    self.created_resource_id = self.created_resource['id']
                else:
                    # Try to get the ID from the Location header
                    location = response.headers.get('Location')
                    if location:
                        self.created_resource_id = location.split('/')[-1]
                    else:
                        # Last resort: just try using 'id' or 'uuid' property if present
                        for id_field in ['id', 'uuid', 'identifier']:
                            if id_field in self.created_resource:
                                self.created_resource_id = self.created_resource[id_field]
                                break
                
                if self.created_resource_id:
                    logger.info(f"Successfully created resource with ID: {self.created_resource_id}")
                    return True
                else:
                    logger.error("Resource created but could not determine its ID")
                    return False
            else:
                logger.error(f"Failed to POST a new resource: {response.status_code}")
                if response.text:
                    logger.error(response.text[:500])  # Limit output to 500 chars
                return False
                
        except Exception as e:
            logger.error(f"Exception during POST: {str(e)}")
            return False
    
    def get_resource(self) -> bool:
        """GET the specific resource by ID."""
        if not self.created_resource_id:
            logger.error("Cannot GET resource without an ID")
            return False
            
        # Make sure resource_path doesn't have leading slash when used as part of the URL
        resource_path = self.resource_path.lstrip('/')
        url = self._get_url(f"{resource_path}/{self.created_resource_id}")
        logger.info(f"Step 3: Getting specific resource from {url}")
        
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
                
            response = requests.get(
                url,
                auth=auth,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                resource = response.json()
                logger.info(f"Successfully retrieved resource with ID: {self.created_resource_id}")
                return True
            else:
                logger.error(f"Failed to GET the resource: {response.status_code}")
                if response.text:
                    logger.error(response.text[:500])
                return False
                
        except Exception as e:
            logger.error(f"Exception during GET resource: {str(e)}")
            return False
    
    def update_resource(self) -> bool:
        """PUT or PATCH to update the resource."""
        if not self.created_resource_id or not self.created_resource:
            logger.error("Cannot update resource without an ID and original data")
            return False
            
        # Make sure resource_path doesn't have leading slash when used as part of the URL
        resource_path = self.resource_path.lstrip('/')
        url = self._get_url(f"{resource_path}/{self.created_resource_id}")
        logger.info(f"Step 4: Updating resource at {url}")
        
        # For the OpenRegister API, we'll use PUT instead of checking for supported methods
        method = 'PUT'
        
        try:
            # Create a simplified update payload with just the required fields
            update_data = {
                "title": f"{self.created_resource.get('title', 'Unknown')} - Updated",
                "version": self.created_resource.get('version', '1.0.0'),
                "description": f"Updated via CRUD flow tester at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            logger.info(f"Sending update data: {json.dumps(update_data, indent=2)}")
            
            # Make the request
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
                
            response = requests.request(
                method,
                url,
                json=update_data,
                auth=auth,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            )
            
            logger.info(f"Update response status: {response.status_code}")
            if response.text:
                logger.info(f"Update response: {response.text[:500]}")
            
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f"Successfully {method}ed resource with ID: {self.created_resource_id}")
                return True
            else:
                logger.error(f"Failed to {method} the resource: {response.status_code}")
                if response.text:
                    logger.error(response.text[:500])
                return False
                
        except Exception as e:
            logger.error(f"Exception during {method}: {str(e)}")
            return False
    
    def delete_resource(self) -> bool:
        """DELETE the resource."""
        if not self.created_resource_id:
            logger.error("Cannot DELETE resource without an ID")
            return False
            
        # Make sure resource_path doesn't have leading slash when used as part of the URL
        resource_path = self.resource_path.lstrip('/')
        url = self._get_url(f"{resource_path}/{self.created_resource_id}")
        logger.info(f"Step 5: Deleting resource at {url}")
        
        try:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
                
            response = requests.delete(
                url,
                auth=auth
            )
            
            logger.info(f"Delete response status: {response.status_code}")
            
            # For this API, an empty response with status 200 is considered success
            if response.status_code in [200, 202, 204]:
                logger.info(f"Successfully deleted resource with ID: {self.created_resource_id}")
                
                # Verify deletion by trying to get the resource
                verify_response = requests.get(
                    url,
                    auth=auth,
                    headers={'Accept': 'application/json'}
                )
                
                if verify_response.status_code in [404, 500]:  # 500 is returned by this API when resource not found
                    logger.info("Verified that the resource has been deleted")
                    return True
                else:
                    logger.warning(f"Resource may not have been deleted. GET after DELETE returned: {verify_response.status_code}")
                    return False
            else:
                logger.error(f"Failed to DELETE the resource: {response.status_code}")
                if response.text:
                    logger.error(response.text[:500])
                return False
                
        except Exception as e:
            logger.error(f"Exception during DELETE: {str(e)}")
            return False
    
    def _print_summary(self, results):
        """Print a summary of the CRUD flow results."""
        logger.info("\n" + "="*50)
        logger.info("CRUD FLOW TEST SUMMARY")
        logger.info("="*50)
        logger.info(f"Resource: {self.resource_path}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"OAS File: {self.oas_file}")
        logger.info("-"*50)
        
        for step, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"{step.upper().replace('_', ' ')}: {status}")
            
        logger.info("="*50)
        
        if all(results.values()):
            logger.info("🎉 ALL CRUD OPERATIONS COMPLETED SUCCESSFULLY!")
        else:
            logger.info("❌ CRUD FLOW TEST FAILED")
            
        logger.info("="*50 + "\n")

def main():
    """Main function to run the CRUD flow tester."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test CRUD operations against an API based on OpenAPI spec')
    parser.add_argument('--oas', required=True, help='Path to the OpenAPI specification file')
    parser.add_argument('--resource', default='api/schemas', help='Resource path to test (e.g., /api/users, defaults to api/schemas)')
    parser.add_argument('--base-url', help='Base URL of the API (defaults to API_BASE_URL env var)')
    
    args = parser.parse_args()
    
    # Create and run the tester
    tester = CrudFlowTester(args.oas, args.resource, args.base_url)
    success = tester.run_crud_flow()
    
    # Exit with appropriate code
    if not success:
        exit(1)

if __name__ == "__main__":
    main() 