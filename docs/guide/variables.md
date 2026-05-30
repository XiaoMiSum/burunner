# Variables & Functions

burunner supports variable substitution and built-in function calls within YAML test files, enabling dynamic and reusable test cases.

## Variable Substitution

Use `${var}` syntax to reference variables defined in the `variables:` section:

```yaml
variables:
  base_url: "https://example.com"
  username: "testuser"
  password: "secret123"

cases:
  - name: Login test
    steps:
      - Navigate to ${base_url}/login
      - Enter "${username}" in the username field
      - Enter "${password}" in the password field
      - Click the login button
```

## Defining Variables

Variables are defined in a top-level `variables:` section:

```yaml
variables:
  base_url: "https://staging.example.com"
  api_endpoint: "https://api.example.com/v2"
  admin_email: "admin@example.com"
  timeout_message: "Operation timed out"
```

Variables can reference functions:

```yaml
variables:
  today: "${today()}"
  request_id: "${uuid()}"
  random_user_id: "${random_int(1000, 9999)}"
```

## Function Calls

Use `${func()}` syntax to invoke built-in functions:

```yaml
cases:
  - name: Dynamic data test
    steps:
      - Navigate to https://example.com/search
      - Enter "report_${today()}" in the search field
      - Verify results contain today's date
```

## Built-in Functions

| Function                | Description              | Example Return Value          |
| ----------------------- | ------------------------ | ----------------------------- |
| `${today()}`            | Current date             | `2024-12-25`                  |
| `${now()}`              | Unix timestamp (seconds) | `1700000000`                  |
| `${now_iso()}`          | Current time in ISO 8601 | `2024-12-25T10:30:00`         |
| `${uuid()}`             | Random UUID v4           | `550e8400-e29b-41d4-a716-...` |
| `${random_int(min,max)}`| Random integer in range  | `42`                          |

## Three Access Patterns

Variables support three equivalent access patterns:

| Pattern                    | Description                         |
| -------------------------- | ----------------------------------- |
| `${base_url}`              | Direct variable access              |
| `${env.base_url}`          | Access via `env` namespace          |
| `${env.current.base_url}` | Access current environment variable |

All three are interchangeable. The `env.current` pattern is particularly useful in multi-environment setups to make it explicit that the variable comes from the active environment.

### Example

```yaml
environments:
  dev:
    variables:
      base_url: "https://dev.example.com"
  prod:
    variables:
      base_url: "https://example.com"

cases:
  - name: Homepage check
    steps:
      # All three reference the same value
      - Navigate to ${base_url}
      - Navigate to ${env.base_url}
      - Navigate to ${env.current.base_url}
```

## Complete Example

```yaml
variables:
  base_url: "https://example.com"
  username: "user_${random_int(1, 1000)}"
  signup_date: "${today()}"
  trace_id: "${uuid()}"

cases:
  - name: User registration
    steps:
      - Navigate to ${base_url}/register
      - Enter "${username}" in the username field
      - Enter "${username}@test.com" in the email field
      - Enter "Password1!" in the password field
      - Click the "Register" button
      - Verify registration success message is displayed
      - Verify the welcome text includes "${username}"

  - name: Search with timestamp
    steps:
      - Navigate to ${base_url}/search
      - Enter "report_${now()}" in the search field
      - Click search
      - Verify the results page loads
```
