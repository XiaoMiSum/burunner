# Data-Driven Testing

Data-driven testing allows a single test case template to be automatically expanded into multiple test instances using external or inline data.

## Overview

Use the `data_driven` field on a case to specify a data source. Each row/record in the data becomes a separate test case instance, with fields accessible as `${field_name}` variables.

```yaml
cases:
  - name: Search feature
    data_driven:
      source: data/keywords.csv
    steps:
      - Navigate to the search page
      - Enter "${keyword}" in the search box
      - Click the search button
      - Verify results contain "${expected}"
```

## Data Sources

burunner supports four data source types:

### 1. CSV Files

```yaml
cases:
  - name: Search test
    data_driven:
      source: data/search.csv
    steps:
      - Enter "${keyword}" in the search box
      - Verify results contain "${expected}"
```

CSV file format (`data/search.csv`):

```csv
keyword,expected
Python,Python tutorial
Java,Java basics
Go,Go language
```

- First row is the header (defines variable names)
- Each subsequent row becomes one test instance

### 2. JSON Files

```yaml
cases:
  - name: User login
    data_driven:
      source: data/users.json
    steps:
      - Enter "${username}" in the username field
      - Enter "${password}" in the password field
      - Click login
      - Verify the result shows "${result}"
```

JSON file format (`data/users.json`):

```json
[
  { "username": "alice", "password": "pass123", "result": "success" },
  { "username": "bob", "password": "wrong", "result": "failure" },
  { "username": "", "password": "", "result": "validation error" }
]
```

- Must be a JSON array of objects
- Each object becomes one test instance
- Object keys become variable names

### 3. YAML Files

```yaml
cases:
  - name: Product page test
    data_driven:
      source: data/products.yaml
    steps:
      - Navigate to product page for "${product_id}"
      - Verify the price shows "${price}"
```

YAML file format (`data/products.yaml`):

```yaml
- product_id: "P001"
  price: "$29.99"
- product_id: "P002"
  price: "$49.99"
- product_id: "P003"
  price: "$99.99"
```

- Must be a YAML list of objects
- Each object becomes one test instance

### 4. Inline Data

Define data directly in the test file without external files:

```yaml
cases:
  - name: Registration validation
    data_driven:
      data:
        - { email: "user@test.com", expect: "success" }
        - { email: "", expect: "email required" }
        - { email: "invalid", expect: "invalid format" }
    steps:
      - Navigate to the registration page
      - Enter "${email}" in the email field
      - Click submit
      - Verify the message contains "${expect}"
```

## Variable Reference

Access data fields using `${field_name}` syntax in your steps:

```yaml
cases:
  - name: Form submission
    data_driven:
      data:
        - { name: "Alice", age: "30", city: "New York" }
        - { name: "Bob", age: "25", city: "London" }
    steps:
      - Enter "${name}" in the name field
      - Enter "${age}" in the age field
      - Select "${city}" from the city dropdown
      - Click submit
      - Verify confirmation shows "Hello, ${name}"
```

## Case Expansion Logic

One template case with N data records expands into N independent test instances:

```yaml
cases:
  - name: Login test
    data_driven:
      data:
        - { user: "admin", pass: "admin123" }
        - { user: "guest", pass: "guest456" }
        - { user: "new_user", pass: "new789" }
    steps:
      - Enter "${user}" in the username field
      - Enter "${pass}" in the password field
      - Click login
```

This expands to 3 test instances at runtime:
- `Login test [1/3]` — with user=admin, pass=admin123
- `Login test [2/3]` — with user=guest, pass=guest456
- `Login test [3/3]` — with user=new_user, pass=new789

Each instance runs independently with its own browser session and produces its own result.

## Complete Example

```yaml
config:
  llm_provider: openai
  llm_model: gpt-4o
  parallel: 3

variables:
  base_url: "https://example.com"

cases:
  - name: Product search
    data_driven:
      source: test_data/products.csv
    steps:
      - Navigate to ${base_url}/search
      - Enter "${product_name}" in the search box
      - Click the search button
      - Verify results show "${product_name}"
      - Verify the price displays "${expected_price}"

  - name: Checkout flow
    data_driven:
      data:
        - { item: "Widget A", qty: "1", total: "$10.00" }
        - { item: "Widget B", qty: "3", total: "$45.00" }
    steps:
      - Navigate to ${base_url}/shop
      - Add "${item}" to cart with quantity ${qty}
      - Go to checkout
      - Verify the total is "${total}"
```

## File Path Resolution

Data source file paths (in the `source` field) are resolved relative to the YAML test file location:

```
project/
├── tests/
│   ├── search.yaml          # source: data/keywords.csv
│   └── data/
│       └── keywords.csv     # resolved relative to search.yaml
```
