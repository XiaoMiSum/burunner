# Writing Test Cases

## Basic Structure

Each test case is defined in YAML with the following fields:

```yaml
- name: Case name (required, must be unique)
  description: Short description (optional)
  tags: [smoke, login]    # Optional, for tag filtering
  steps:
    - First step in natural language
    - Second step in natural language
    - Third step...
  config:                 # Optional, per-case override
    headless: false
    max_steps: 50
```

### Required Fields

| Field   | Type   | Description                       |
| ------- | ------ | --------------------------------- |
| `name`  | string | Unique case name                  |
| `steps` | list   | Natural language step descriptions |

### Optional Fields

| Field         | Type   | Description                         |
| ------------- | ------ | ----------------------------------- |
| `description` | string | Brief description of the test case  |
| `tags`        | list   | String array for tag-based filtering |
| `preset`      | string | Name of a preset to inherit from    |
| `config`      | object | Per-case configuration override     |
| `cookies`     | list   | Case-level cookies to inject        |
| `data_driven` | object | Data-driven test configuration      |

## File Formats

### List Format (Simple)

The top level of the YAML file is a list of cases:

```yaml
- name: Test case A
  steps:
    - Navigate to https://example.com
    - Verify the title is correct

- name: Test case B
  steps:
    - Open the login page
    - Enter valid credentials
```

### Object Format (Advanced)

Use the `{cases: [...]}` format when you need top-level `config`, `presets`, `variables`, or `environments`:

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o
  parallel: 2

presets:
  logged_in:
    steps:
      - Navigate to login page
      - Enter credentials and sign in

variables:
  base_url: "https://example.com"

cases:
  - name: Test case A
    preset: logged_in
    steps:
      - Navigate to ${base_url}/dashboard
      - Verify the dashboard loads
```

## Writing Natural Language Steps

Steps are plain natural language instructions that the LLM-powered browser agent will execute:

```yaml
steps:
  - Navigate to https://example.com/login
  - Enter "testuser" in the username field
  - Enter "password123" in the password field
  - Click the "Sign In" button
  - Wait for the page to load
  - Verify the page displays "Welcome, testuser"
```

Tips for writing effective steps:
- Be specific about UI elements (use labels, placeholders, or visible text)
- Include verification steps to assert expected outcomes
- Each step should describe one action or assertion
- Use clear, unambiguous language

## Tags System

Tags enable selective test execution via filtering.

### Setting Tags

```yaml
- name: Login feature
  tags: [p1, smoke, login]
  steps:
    - Navigate to login page
    - Enter credentials and sign in

- name: Advanced search
  tags: [p2, regression]
  steps:
    - Navigate to search page
    - Perform advanced search
```

### Filtering by Tags

Use `-t` / `--tags` to run only cases matching specified tags:

```bash
# Run cases with tag "p1"
burunner run tests/*.yaml -t p1

# Run cases with tag "p1" OR "smoke" (OR logic)
burunner run tests/*.yaml -t "p1,smoke"

# Combine with name filter (both must match)
burunner run tests/*.yaml -k "login" -t "smoke"
```

### Tag Behavior

- Multiple tags are separated by commas
- Matching uses **OR logic** — a case is selected if it contains *any* of the specified tags
- Tag matching is **case-insensitive**
- Tags can be combined with `-k` name filter (both conditions must be satisfied)

## Per-Case Config Override

Override runtime settings for individual cases:

```yaml
- name: Visual test requiring headed browser
  config:
    headless: false
    max_steps: 50
  steps:
    - Navigate to the dashboard
    - Take a screenshot of the chart area
```

## Test Verdict Rules

burunner automatically appends a verdict prompt to each case. The agent must output a JSON conclusion: `{"success": true|false, "reason": "..."}` and call `done(success=...)`.

### Verdict Priority (5 levels)

| Priority | Condition                                              | Result         |
| -------- | ------------------------------------------------------ | -------------- |
| 1        | Agent returns `success=false` or text contains failure | **FAILED**     |
| 2        | `history.is_successful() == False`                     | **FAILED**     |
| 3        | Agent exceeded max steps without completing            | **INCOMPLETE** |
| 4        | Runtime exception (browser crash / LLM timeout / etc.) | **ERROR**      |
| 5        | All other cases                                        | **PASSED**     |

### Execution Results

| Status       | Meaning                                                              | Retried? |
| ------------ | -------------------------------------------------------------------- | -------- |
| **PASSED**   | The case completed successfully with all assertions met              | No       |
| **FAILED**   | The case ran but business assertions were not satisfied              | No       |
| **INCOMPLETE** | The agent exceeded the maximum step limit without finishing         | Yes      |
| **ERROR**    | The case could not complete due to infrastructure issues             | Yes      |

### INCOMPLETE Status

A case is marked **INCOMPLETE** when the browser-use agent reaches its maximum allowed steps without producing a final verdict. This typically means:

- The task is too complex for the allocated step budget
- The agent got stuck in a loop or navigated away from the target
- The page had unexpected loading delays

The maximum steps per case is dynamically calculated as `number_of_steps × 20` (minimum 20) by default, or can be set explicitly via `--max-steps` or `BURUNNER_MAX_STEPS`.

INCOMPLETE cases are automatically retried when `retry_count > 0`.
