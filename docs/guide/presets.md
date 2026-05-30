# Presets & Cookies

## Presets — Shared Step Inheritance

Presets allow you to define reusable sequences of steps that multiple test cases can inherit, eliminating duplication for common workflows like login or navigation.

### Defining Presets

Define presets in a top-level `presets:` section. Each preset has a name and a list of steps:

```yaml
presets:
  logged_in_user:
    steps:
      - Navigate to https://example.com/login
      - Enter "admin" in the username field
      - Enter "password123" in the password field
      - Click the "Sign In" button
      - Wait for the dashboard to load

  on_settings_page:
    steps:
      - Navigate to https://example.com/login
      - Enter credentials and sign in
      - Click the "Settings" link in the sidebar
```

### Using Presets in Cases

Reference a preset with the `preset` keyword in your test case:

```yaml
presets:
  logged_in_user:
    steps:
      - Navigate to https://example.com/login
      - Enter valid credentials and sign in

cases:
  - name: View profile
    preset: logged_in_user
    steps:
      - Click "My Profile" in the navigation
      - Verify the profile page displays the username

  - name: Change password
    preset: logged_in_user
    steps:
      - Navigate to account settings
      - Click "Change Password"
      - Enter new password and confirm
```

### Execution Order

When a case uses a preset, the steps are merged in order:

1. **Preset steps** execute first
2. **Case steps** execute after

The final step sequence for "View profile" above would be:
1. Navigate to https://example.com/login
2. Enter valid credentials and sign in
3. Click "My Profile" in the navigation
4. Verify the profile page displays the username

## Cookie Injection

Inject cookies into the browser context before test execution. This is useful for skipping login flows or setting authentication tokens directly.

### Global Cookies

Define cookies in the top-level `config:` section to apply them to all cases:

```yaml
config:
  cookies:
    - name: auth_token
      value: "eyJhbGciOiJIUzI1NiJ9..."
      domain: .example.com
    - name: user_id
      value: "1001"
      domain: .example.com

cases:
  - name: Access protected page
    steps:
      - Navigate to https://example.com/dashboard
      - Verify the dashboard loads without login prompt
```

### Case-Level Cookies

Define cookies on individual cases:

```yaml
cases:
  - name: Admin user access
    cookies:
      - name: session_id
        value: "admin-session-xyz"
        domain: .example.com
      - name: role
        value: "admin"
        domain: .example.com
    steps:
      - Navigate to https://example.com/admin
      - Verify the admin panel is accessible
```

### Cookie Fields

| Field    | Required | Description                                    |
| -------- | -------- | ---------------------------------------------- |
| `name`   | Yes      | Cookie name                                    |
| `value`  | Yes      | Cookie value                                   |
| `domain` | Yes      | Domain the cookie applies to (include leading dot for subdomains) |

### Merge Rules

When both global and case-level cookies are defined:

- **Case-level cookies take priority** over global cookies
- For cookies with the same `name` + `domain`, the case-level value wins
- All other cookies from both levels are merged together

### Complete Example

```yaml
config:
  cookies:
    - name: locale
      value: "en-US"
      domain: .example.com
    - name: session
      value: "global-session"
      domain: .example.com

presets:
  authenticated:
    steps:
      - Navigate to https://example.com
      - Verify the user is logged in

cases:
  - name: Regular user flow
    preset: authenticated
    steps:
      - Click on "My Orders"
      - Verify order history is displayed

  - name: VIP user flow
    preset: authenticated
    cookies:
      - name: session
        value: "vip-user-session"
        domain: .example.com
      - name: tier
        value: "vip"
        domain: .example.com
    steps:
      - Click on "VIP Benefits"
      - Verify exclusive offers are shown
```

In "VIP user flow":
- `locale` cookie comes from global config (inherited)
- `session` cookie uses the case-level value `"vip-user-session"` (overrides global)
- `tier` cookie is added from the case level
