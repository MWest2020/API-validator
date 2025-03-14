# OpenRegister API Test Summary

## Overview
This report summarizes the results of testing the OpenRegister API against the OpenAPI 3.1.0 specification.

## Test Environment
- **Base URL**: `https://opencatalogi.test.commonground.nu/apps/openregister`
- **Credentials**: Using the credentials from the `.env` file
- **Testing Tool**: Schemathesis with OpenAPI 3.1.0 experimental support
- **Tested Methods**: GET, POST, PATCH, DELETE

## Working Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/registers` | GET | ✅ Working |
| `/api/registers/{id}` | PATCH | ✅ Working |
| `/api/schemas` | GET | ✅ Working |
| `/api/schemas/{id}` | PATCH | ✅ Working |
| `/api/sources` | GET | ✅ Working |
| `/api/sources/{id}` | PATCH | ✅ Working |

## Non-Working Endpoints

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

## Observations

1. **GET Collection Endpoints Work**: All GET endpoints for collections (`/api/registers`, `/api/schemas`, `/api/sources`) are working correctly.

2. **PATCH Endpoints Work**: All PATCH operations for updating resources are working correctly.

3. **POST Operations Fail**: All POST operations for creating new resources fail, with at least one confirmed to return a 500 Internal Server Error.

4. **GET Individual Resource Fails**: All GET operations for retrieving individual resources by ID fail.

5. **DELETE Operations Fail**: All DELETE operations for removing resources fail.

## Recommendations

1. **Focus on GET and PATCH**: For the most reliable operations, focus on using the GET collection endpoints and PATCH operations, as these appear to be working correctly.

2. **Investigate POST Failures**: The server returns 500 Internal Server Error for POST operations, suggesting there might be an issue with the implementation of resource creation.

3. **Review Individual Resource Access**: The inability to access individual resources by ID suggests there might be a mismatch between how resource IDs are expected in the API versus how they are implemented.

4. **Consider Restricting DELETE**: Since DELETE operations fail, consider restricting these operations in the API specification or fixing the implementation.

5. **Update OpenAPI Specification**: Consider updating the OpenAPI specification to better match the actual behavior of the API, particularly by documenting the 500 error responses for POST operations.

## Conclusion

The OpenRegister API implementation only partially conforms to the OpenAPI specification. Collection retrieval (GET) and resource updates (PATCH) work correctly, but resource creation (POST), individual resource retrieval (GET by ID), and resource deletion (DELETE) do not work as expected.

For reliable API consumption, clients should focus on the working endpoints and be prepared to handle errors for the non-working operations. 