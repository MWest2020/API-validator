#!/bin/bash

# Remove old test files
rm -f test_crud.py
rm -f test_endpoint.py
rm -f test_nextcloud.py
rm -rf api/

# Remove old logs and reports
rm -f crud_test.log
rm -f api_test.log
rm -f api_test_report.md
rm -f api_auth_note.md
rm -f api_oas_mismatch.md
rm -f api_working_endpoints.md

# Remove old testing tools
rm -f api_tester.py
rm -f crud_tester.py

# Keep only the essential files
# - open-register.json (OpenAPI spec)
# - api_test_summary.md (Test results)
# - simple_api_tester.py (Main testing tool)
# - test_api_paths.py (Tool to discover API paths)
# - .env (Configuration)
# - requirements.txt
# - install scripts
# - README.md

echo "Cleanup complete. Essential files have been kept." 