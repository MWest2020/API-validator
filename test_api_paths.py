import requests
import os
import argparse
import json
from dotenv import load_dotenv

def discover_api_paths(base_url, auth=None, paths=None, timeout=5):
    """
    Discover API paths by testing common endpoints and custom paths.
    
    Args:
        base_url (str): Base URL of the API
        auth (tuple): (username, password) tuple for authentication
        paths (list): Optional list of custom paths to test
        timeout (int): Request timeout in seconds
        
    Returns:
        dict: Dictionary of paths and their response info
    """
    # Common API path patterns to check if no custom paths provided
    default_paths = [
        # General API paths
        "/api",
        "/api/v1",
        "/api/v2",
        "/api/v3",
        
        # Documentation paths
        "/docs",
        "/swagger",
        "/swagger-ui",
        "/swagger-ui.html",
        "/swagger/index.html",
        "/redoc",
        "/apidocs",
        
        # OpenAPI specification paths
        "/openapi",
        "/openapi.json",
        "/openapi.yaml",
        "/oas",
        "/oas/v1",
        "/oas/v2",
        "/oas/v3",
        "/swagger.json",
        "/swagger.yaml",
        
        # Common versioning patterns
        "/v1",
        "/v2",
        "/v3"
    ]
    
    # Use provided paths or default paths
    test_paths = paths if paths else default_paths
    
    results = {}
    working_paths = []
    
    print(f"Testing API paths on base URL: {base_url}")
    print("=" * 80)
    
    for path in test_paths:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            # Try with authentication if provided
            if auth:
                response = requests.get(url, auth=auth, timeout=timeout)
            else:
                response = requests.get(url, timeout=timeout)
                
            status = response.status_code
            content_type = response.headers.get('Content-Type', 'unknown')
            content_length = len(response.content)
            
            # Detect if it's JSON
            is_json = False
            json_data = None
            json_preview = ""
            try:
                if 'json' in content_type.lower():
                    json_data = response.json()
                    is_json = True
                    json_preview = json.dumps(json_data, indent=2)[:200] + "..." if len(json.dumps(json_data, indent=2)) > 200 else json.dumps(json_data, indent=2)
            except:
                pass
                
            results[path] = {
                'status': status,
                'content_type': content_type,
                'content_length': content_length,
                'is_json': is_json,
                'json_data': json_data,
                'response_text': response.text[:500] if not is_json else None
            }
            
            # Print results
            print(f"\nPath: {path}")
            print(f"URL: {url}")
            print(f"Status: {status}")
            print(f"Content-Type: {content_type}")
            print(f"Content Length: {content_length} bytes")
            
            if is_json:
                print(f"JSON Preview:\n{json_preview}")
            elif status == 200 and content_length < 500:
                print(f"Content Preview:\n{response.text[:200]}")
                
            # Add to working paths if successful
            if status < 400:
                working_paths.append(path)
                
        except requests.RequestException as e:
            print(f"\nPath: {path}")
            print(f"URL: {url}")
            print(f"Error: {str(e)}")
            results[path] = {'error': str(e)}
    
    # Report working paths
    if working_paths:
        print("\nWorking Paths:")
        for path in working_paths:
            print(f"- {path} ({results[path]['status']})")
    else:
        print("\nNo working paths found.")
        
    return results

def load_paths_from_file(file_path):
    """Load paths from a text file, one path per line."""
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="API Path Discovery Tool")
    parser.add_argument("--url", help="Base URL of the API (overrides .env)")
    parser.add_argument("--username", help="Username for authentication (overrides .env)")
    parser.add_argument("--password", help="Password for authentication (overrides .env)")
    parser.add_argument("--paths", help="Comma-separated list of paths to test")
    parser.add_argument("--paths-file", help="Text file containing paths to test, one per line")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get config from env or args
    api_username = args.username or os.getenv("API_USERNAME")
    api_password = args.password or os.getenv("API_PASSWORD")
    base_url = args.url or os.getenv("API_BASE_URL")
    
    # Check if we have a base URL
    if not base_url:
        print("Error: No base URL provided. Set API_BASE_URL in .env or use --url")
        return 1
    
    # Set up authentication if provided
    auth = None
    if api_username and api_password:
        auth = (api_username, api_password)
        print(f"Using authentication with username: {api_username}")
    else:
        print("No authentication credentials provided")
    
    # Get paths if provided
    paths = None
    if args.paths_file:
        paths = load_paths_from_file(args.paths_file)
        print(f"Loaded {len(paths)} paths from {args.paths_file}")
    elif args.paths:
        paths = [p.strip() for p in args.paths.split(',')]
        print(f"Using {len(paths)} custom paths")
    
    # Run the discovery
    discover_api_paths(base_url, auth, paths, args.timeout)
    
    return 0

if __name__ == "__main__":
    exit(main()) 