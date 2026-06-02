# Variables & Functions

burunner supports variable substitution and built-in function calls within YAML test files, enabling dynamic and reusable test cases.

## Template Engine

Under the hood, burunner uses the [Mako](https://www.makotemplates.org/) template engine for variable rendering. The familiar `${...}` syntax is fully supported, and you also gain access to Mako's powerful expression capabilities.

> **Note**: The template syntax remains `${var}` and `${func()}` — no migration is needed for existing test files.

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
  today: "${date()}"
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
      - Enter "report_${date()}" in the search field
      - Verify results contain today's date
```

## Built-in Functions

| Function                | Description              | Example Return Value          |
| ----------------------- | ------------------------ | ----------------------------- |
| `${date()}`             | Current date             | `2024-12-25`                  |
| `${datetime()}`         | Current date & time      | `2024-12-25 14:30:00`         |
| `${utc_datetime()}`     | UTC date & time          | `2024-12-25 06:30:00`         |
| `${timestamp()}`        | Unix timestamp (seconds) | `1700000000`                  |
| `${uuid()}`             | UUID v4                  | `550e8400-e29b-41d4-a716-...` |
| `${random_int()}`       | Random int (0-9999)      | `4231`                        |
| `${random_int(max)}`    | Random int (0-max)       | `42`                          |
| `${random_int(min,max)}`| Random int [min, max]    | `50`                          |
| `${random_string()}`    | Random string (len 8)    | `aB3xK9mP`                    |
| `${random_string(n)}`   | Random string (len n)    | `xY7zQ2`                      |
| `${env(VAR)}`           | Environment variable     | `/usr/bin`                    |
| `${env(VAR, default)}`  | Env var with default     | `default`                     |
| `${calc(expr)}`         | Math expression          | `80`                          |

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

## Expressions

Since burunner uses Mako, you can use Python expressions directly inside `${...}`:

### Conditional Expressions

```yaml
variables:
  env: "prod"
  base_url: "${('https://api.example.com' if env == 'prod' else 'https://staging.example.com')}"
  timeout: "${30 if env == 'prod' else 60}"
```

### Inline Python Expressions

```yaml
variables:
  username: "user_${random_int(1, 100)}"
  uppercased: "${username.upper()}"
  short_id: "${uuid()[:8]}"
  padded_id: "${str(random_int(1, 99)).zfill(4)}"
```

### String Operations

```yaml
steps:
  - Enter "${'report_' + date().replace('-', '')}" in the search field
```

## Security

For safety, the template rendering environment is sandboxed:

- **Forbidden operations**: `import`, `eval`, `exec`, `open`, `__import__`, `compile`, `getattr`, `setattr`, `delattr`
- **No file system access**: Templates cannot read or write files
- **No network access**: Templates cannot make network requests
- **No arbitrary code**: Only pre-registered functions and basic Python expressions are allowed

Attempting to use forbidden operations will raise a `VariableRenderError`:

```yaml
# ❌ These will FAIL
variables:
  bad1: "${__import__('os').system('rm -rf /')}"
  bad2: "${eval('malicious code')}"
  bad3: "${open('/etc/passwd').read()}"
```

## Complete Example

```yaml
variables:
  base_url: "https://example.com"
  username: "user_${random_int(1, 1000)}"
  signup_date: "${date()}"
  trace_id: "${uuid()}"
  env: "staging"
  api_url: "${('https://api.example.com' if env == 'prod' else 'https://staging-api.example.com')}"

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
      - Enter "report_${timestamp()}" in the search field
      - Click search
      - Verify the results page loads
```
