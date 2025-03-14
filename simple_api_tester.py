#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import logging
from dotenv import load_dotenv

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def run_schemathesis(oas_path, base_url, username=None, password=None, all_methods=True):
    """Run Schemathesis tests against the API."""
    logger.info(f"Running Schemathesis against {base_url} with OAS {oas_path}")
    
    try:
        # Build the command
        cmd = ["schemathesis", "run", oas_path]
        
        # Extract domain to avoid path duplication
        if '/apps/' in base_url:
            base_domain = base_url.split('/apps/')[0]
            logger.info(f"Using domain-only base URL: {base_domain} to avoid path duplication")
            cmd.extend(["--base-url", base_domain])
        else:
            cmd.extend(["--base-url", base_url])
        
        # Add common options
        cmd.extend([
            "--checks=all",
            "--experimental=openapi-3.1",
            "--validate-schema=false",
            "--max-response-time=30000",
            "--hypothesis-max-examples=10"
        ])
        
        # Control HTTP methods
        if not all_methods:
            cmd.extend(["--method", "GET"])
            logger.info("Testing only GET operations")
        else:
            logger.info("Testing ALL HTTP methods - this may modify data!")
        
        # Add authentication if provided
        if username and password:
            cmd.extend(["--auth", f"{username}:{password}", "--auth-type", "basic"])
            logger.info(f"Using basic authentication with username: {username}")
        
        # Add standard headers
        cmd.extend(["--header", "Accept: application/json"])
        
        # Run the command
        logger.info(f"Running command: {' '.join([c if not password or password not in c else '******' for c in cmd])}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log the result
        logger.info(f"Schemathesis completed with exit code: {result.returncode}")
        print(result.stdout)
        
        if result.returncode != 0:
            logger.error("Tests failed")
        else:
            logger.info("Tests passed")
            
        return result.returncode == 0
        
    except FileNotFoundError:
        logger.error("Schemathesis is not installed. Install with: pip install schemathesis")
        return False
    except Exception as e:
        logger.error(f"Error running Schemathesis: {str(e)}")
        return False

def run_dredd(oas_path, base_url, username=None, password=None, all_methods=True):
    """Run Dredd tests against the API."""
    logger.info(f"Running Dredd against {base_url} with OAS {oas_path}")
    
    try:
        # Build the command
        cmd = ["dredd", "--verbose", oas_path, base_url]
        
        # Control HTTP methods
        if not all_methods:
            cmd.extend(["--method", "GET"])
            logger.info("Testing only GET operations")
        else:
            logger.info("Testing ALL HTTP methods - this may modify data!")
        
        # Add authentication if provided
        if username and password:
            cmd.extend(["--user", f"{username}:{password}"])
            logger.info(f"Using basic authentication with username: {username}")
        
        # Run the command
        logger.info(f"Running command: {' '.join([c if not password or password not in c else '******' for c in cmd])}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Log the result
        logger.info(f"Dredd completed with exit code: {result.returncode}")
        print(result.stdout)
        
        if result.returncode != 0:
            logger.error("Tests failed")
        else:
            logger.info("Tests passed")
            
        return result.returncode == 0
        
    except FileNotFoundError:
        logger.error("Dredd is not installed. Install with: npm install -g dredd")
        return False
    except Exception as e:
        logger.error(f"Error running Dredd: {str(e)}")
        return False

def main():
    # Load environment variables
    load_dotenv()
    
    # Get values from .env
    api_username = os.getenv('API_USERNAME')
    api_password = os.getenv('API_PASSWORD')
    api_base_url = os.getenv('API_BASE_URL')
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Simple API Tester")
    parser.add_argument("--oas", required=True, help="Path to the OpenAPI Specification file")
    parser.add_argument("--url", help="Base URL of the API (overrides .env)")
    parser.add_argument("--tool", required=True, choices=["dredd", "schemathesis"], help="Testing tool to use")
    parser.add_argument("--all-methods", action="store_true", help="Test all HTTP methods (may modify data)")
    parser.add_argument("--username", help="Username (overrides .env)")
    parser.add_argument("--password", help="Password (overrides .env)")
    
    args = parser.parse_args()
    
    # Override with command line arguments if provided
    if args.url:
        api_base_url = args.url
    if args.username:
        api_username = args.username
    if args.password:
        api_password = args.password
    
    # Check required values
    if not api_base_url:
        logger.error("No API base URL provided. Set API_BASE_URL in .env or use --url")
        sys.exit(1)
    
    # Log the configuration
    logger.info(f"Using OAS file: {args.oas}")
    logger.info(f"Using API URL: {api_base_url}")
    logger.info(f"Using tool: {args.tool}")
    
    # Run the tests
    if args.tool == "schemathesis":
        success = run_schemathesis(args.oas, api_base_url, api_username, api_password, args.all_methods)
    else:  # dredd
        success = run_dredd(args.oas, api_base_url, api_username, api_password, args.all_methods)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 