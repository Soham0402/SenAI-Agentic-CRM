# Technical API Documentation

## API Versioning and Deprecation
* API v1 is officially deprecated and scheduled to be completely sunset on December 31, 2023.
* All external integrations must migrate fully to API v2 before this deadline to avoid service disruption.

## API Breakages and V2 Modifications
* API v2 introduces mandatory workspace parameters. All requests to v2 endpoints (e.g., `POST /v2/events`) must explicitly supply the custom `X-Workspace-ID` in the request header.
* API v2 mandates structured, token-paginated payloads and webhook signature validation to ensure secure downstream operations.

## Rate Limits
* Standard rate ceilings are restricted to 1,000 requests per minute.
* Enterprise upgrades allow custom ceilings up to 5,000 or 10,000 requests per minute based on subscription agreements.