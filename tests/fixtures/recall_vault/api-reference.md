## Overview

The API reference documents service endpoint behavior, authentication requirements, and the default rate limit policy. It is written for callers who already completed setup and now need request details.

### GET /users

The `GET /users` endpoint returns a deterministic list of user records. Requests must include authentication headers, and clients should respect the shared rate limit before retrying pagination.

### POST /notes

The `POST /notes` endpoint creates a note for the authenticated user. The request body contains a title and text field, and failed authentication returns a stable error shape for tests.
