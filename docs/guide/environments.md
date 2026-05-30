# Multi-Environment

burunner supports defining multiple environments in a single YAML file, allowing the same test cases to run against different configurations (dev, staging, prod) without modification.

## Environment Structure

Define environments in a top-level `environments:` section. Each environment can specify its own `variables`, `config`, and `cookies`:

```yaml
environments:
  dev:
    variables:
      base_url: "https://dev.example.com"
      username: "dev_user"
    config:
      headless: false
      max_steps: 50
    cookies:
      - name: env_token
        value: "dev-token-abc"
        domain: ".dev.example.com"

  staging:
    variables:
      base_url: "https://staging.example.com"
      username: "staging_user"
    config:
      headless: true
      max_steps: 40

  prod:
    variables:
      base_url: "https://example.com"
      username: "prod_user"
    config:
      headless: true
      max_steps: 30
```

## Environment Fields

Each environment supports three sections:

| Section     | Description                                          |
| ----------- | ---------------------------------------------------- |
| `variables` | Key-value pairs accessible via `${var}` in steps     |
| `config`    | Runtime configuration overrides (same as top-level)  |
| `cookies`   | Cookies to inject into the browser context           |

## Activating an Environment

### Via CLI Flag

```bash
burunner run tests.yaml --env dev
burunner run tests.yaml --env staging
burunner run tests.yaml --env prod
```

### Via Environment Variable

```bash
export BURUNNER_ENV=dev
burunner run tests.yaml
```

### Priority

CLI `--env` flag takes priority over the `BURUNNER_ENV` environment variable.

If no environment is specified, burunner runs with the default configuration (top-level `variables` and `config`).

## Independent Environments

Each environment is completely independent — **there is no inheritance between environments**. Every environment must define all the variables and settings it needs.

```yaml
environments:
  dev:
    variables:
      base_url: "https://dev.example.com"
      api_key: "dev-key-123"
  prod:
    variables:
      base_url: "https://example.com"
      api_key: "prod-key-456"
```

If `dev` defines `base_url` but `prod` does not, then `${base_url}` will be undefined when running with `--env prod`.

## Complete Example

```yaml
# Global variables (used when no environment is active)
variables:
  base_url: "https://localhost:3000"
  app_name: "MyApp"

# Environment-specific overrides
environments:
  dev:
    variables:
      base_url: "https://dev.example.com"
      app_name: "MyApp (Dev)"
      debug_mode: "true"
    config:
      headless: false
      max_steps: 50
      parallel: 1
    cookies:
      - name: dev_auth
        value: "dev-session-token"
        domain: ".dev.example.com"

  staging:
    variables:
      base_url: "https://staging.example.com"
      app_name: "MyApp (Staging)"
    config:
      headless: true
      max_steps: 40
      parallel: 2

  prod:
    variables:
      base_url: "https://example.com"
      app_name: "MyApp"
    config:
      headless: true
      max_steps: 30
      parallel: 4
    cookies:
      - name: monitoring
        value: "enabled"
        domain: ".example.com"

# Test cases use variables regardless of environment
cases:
  - name: Homepage loads correctly
    steps:
      - Navigate to ${base_url}
      - Verify the page title contains "${app_name}"
      - Verify the page loads within 5 seconds

  - name: User login flow
    steps:
      - Navigate to ${base_url}/login
      - Enter valid credentials
      - Verify redirect to dashboard
      - Verify the header shows "${app_name}"
```

### Running

```bash
# Run against dev environment
burunner run tests.yaml --env dev

# Run against staging with parallel execution
burunner run tests.yaml --env staging

# Run against production
burunner run tests.yaml --env prod

# Run without environment (uses top-level variables)
burunner run tests.yaml
```
