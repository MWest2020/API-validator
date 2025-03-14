# API Validator

A generic tool for validating APIs against their OpenAPI specifications. This repository contains reusable tools to test the conformance of any API implementation to its OpenAPI specification.

## Features

- **OpenAPI Validation**: Test APIs against their OpenAPI 3.0/3.1 specifications
- **Authentication Support**: Basic auth, API key, and token-based authentication
- **HTTP Method Testing**: Test GET, POST, PUT, PATCH, DELETE methods
- **Test Report Generation**: Detailed reports of test results
- **Endpoint Discovery**: Find and test available API endpoints
- **CRUD Flow Testing**: Test the complete Create, Read, Update, Delete lifecycle for API resources
- **Multiple Testing Tools**: Support for Schemathesis and Dredd
- **Customizable**: Add your own API specifications and test paths

## Repository Structure

```
API-validator/
├── specs/                     # Directory for OpenAPI specifications
│   └── open-register.json     # Example OAS for OpenRegister API
├── .env                       # Environment configuration (API credentials)
├── .env.example               # Example environment configuration
├── simple_api_tester.py       # Generic API testing tool
├── test_api_paths.py          # Generic API endpoint discovery tool
├── api_test_summary.md        # Example test results for OpenRegister API
└── README.md                  # Project documentation
```

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API credentials (based on `.env.example`)

## Usage

### Testing an API against its OpenAPI specification

```bash
python simple_api_tester.py --oas specs/open-register.json --tool schemathesis --all-methods
```

This will test all endpoints defined in the OpenAPI specification against the API.

### Discovering API endpoints

```bash
python test_api_paths.py --url https://opencatalogi.test.commonground.nu/apps/openregister --paths-file example-paths.txt
```

This will test all paths listed in the example-paths.txt file against the API.

### Testing CRUD operations

```bash
python crud_flow_tester.py --oas specs/open-register.json --resource api/schemas
```

This will test the complete CRUD (Create, Read, Update, Delete) flow for the specified resource:

1. GET the collection to see existing resources
2. POST a new resource based on the OpenAPI schema
3. GET the specific resource by ID
4. PUT/PATCH to update the resource
5. DELETE the resource

The CRUD flow tester will provide a detailed summary of the results at the end.

## Example: OpenRegister API Test Results

The following results are from testing the OpenRegister API, included as an example of the tool's output.

### Working Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/registers` | GET | ✅ Working |
| `/api/registers/{id}` | PATCH | ✅ Working |
| `/api/schemas` | GET | ✅ Working |
| `/api/schemas/{id}` | PATCH | ✅ Working |
| `/api/sources` | GET | ✅ Working |
| `/api/sources/{id}` | PATCH | ✅ Working |

### Non-Working Endpoints

| Endpoint | Method | Problem |
|----------|--------|---------|
| `/api/registers` | POST | ❌ Returns 500 Internal Server Error |
| `/api/registers/{id}` | GET | ❌ Failing |
| `/api/registers/{id}` | DELETE | ❌ Failing |
| `/api/schemas` | POST | ❌ Failing |
| `/api/schemas/{id}` | GET | ❌ Failing |
| `/api/schemas/{id}` | DELETE | ❌ Failing |
| `/api/sources` | POST | ❌ Failing |
| `/api/sources/{id}` | GET | ❌ Failing |
| `/api/sources/{id}` | DELETE | ❌ Failing |

For more detailed information, see [api_test_summary.md](api_test_summary.md).

## Adding Your Own API Specifications

To test your own API:

1. Add your OpenAPI specification file to the `specs/` directory
2. Create a custom paths file if needed
3. Run the tools with your specification file

```bash
python simple_api_tester.py --oas specs/your-api-spec.json --tool schemathesis
python test_api_paths.py --url https://your-api-url --paths-file your-paths.txt
python crud_flow_tester.py --oas specs/your-api-spec.json --resource api/your-resource
```

## License

This project is licensed under the MIT License. 