"""Benchmark target applications + ground truth.

Each application carries:
- ``requirements``: the ground-truth functional/security/a11y requirements the
  platform is expected to discover and cover (used for requirement-coverage).
- ``workflows``: the canonical user journeys (the benchmark defines 54 total).
- ``elements``: the ground-truth DOM (selector → attributes) used to verify
  locator accuracy and to drive deterministic self-healing checks.

Six real, widely-used test applications across six domains.
"""
from __future__ import annotations

# (id, description, category)
def _reqs(*items: tuple[str, str, str]) -> list[tuple[str, str, str]]:
    return list(items)


APPS: list[dict] = [
    {
        "id": "swaglabs",
        "name": "Swag Labs",
        "url": "https://www.saucedemo.com/",
        "domain": "e-commerce",
        "requirements": _reqs(
            ("REQ-LOGIN-1", "Standard user logs in with valid credentials", "auth"),
            ("REQ-LOGIN-2", "Locked-out user is rejected with an error", "auth"),
            ("REQ-LOGIN-3", "Empty credentials are rejected", "auth"),
            ("REQ-INV-1", "Inventory lists all products after login", "catalog"),
            ("REQ-INV-2", "Products sort by name and price", "catalog"),
            ("REQ-CART-1", "Items add to / remove from the cart", "cart"),
            ("REQ-CART-2", "Cart badge reflects item count", "cart"),
            ("REQ-CHK-1", "Checkout requires first name, last name, postal code", "checkout"),
            ("REQ-CHK-2", "Checkout shows order confirmation on success", "checkout"),
            ("REQ-SEC-1", "Login form is served over HTTPS", "security"),
            ("REQ-SEC-2", "Passwords are masked on input", "security"),
            ("REQ-ACC-1", "Core flows are keyboard navigable", "accessibility"),
        ),
        "workflows": [
            "login_valid", "login_locked_out", "login_empty", "browse_inventory",
            "sort_products", "add_to_cart", "remove_from_cart",
            "checkout_complete", "logout",
        ],
        "elements": {
            "#user-name": {"role": "input", "id": "user-name", "name": "user-name", "type": "text"},
            "#password": {"role": "input", "id": "password", "name": "password", "type": "password"},
            "#login-button": {"role": "button", "id": "login-button", "name": "login-button", "label": "Login"},
            "#first-name": {"role": "input", "id": "first-name", "name": "firstName", "type": "text"},
            "#last-name": {"role": "input", "id": "last-name", "name": "lastName", "type": "text"},
            "#postal-code": {"role": "input", "id": "postal-code", "name": "postalCode", "type": "text"},
            "#continue": {"role": "button", "id": "continue", "name": "continue", "label": "Continue"},
            "#finish": {"role": "button", "id": "finish", "name": "finish", "label": "Finish"},
            "#shopping-cart-link": {"role": "link", "id": "shopping-cart-link", "label": "Cart"},
        },
    },
    {
        "id": "parabank",
        "name": "ParaBank",
        "url": "https://parabank.parasoft.com/parabank/index.htm",
        "domain": "banking",
        "requirements": _reqs(
            ("REQ-LOGIN-1", "Customer logs in with valid credentials", "auth"),
            ("REQ-LOGIN-2", "Invalid credentials show an error", "auth"),
            ("REQ-REG-1", "New customer can register", "auth"),
            ("REQ-ACC-1", "Accounts overview lists balances", "accounts"),
            ("REQ-ACC-2", "Account detail shows transaction history", "accounts"),
            ("REQ-TRF-1", "Funds transfer debits and credits correctly", "transactions"),
            ("REQ-TRF-2", "Transfer validates amount and account", "transactions"),
            ("REQ-BILL-1", "Bill payment schedules a payee payment", "transactions"),
            ("REQ-SEC-1", "Login is served over HTTPS", "security"),
            ("REQ-SEC-2", "Session times out on inactivity", "security"),
            ("REQ-ACC-3", "Forms are keyboard accessible", "accessibility"),
            ("REQ-DATA-1", "Account numbers are masked in UI", "data"),
        ),
        "workflows": [
            "login_valid", "login_invalid", "register_customer", "view_accounts",
            "account_detail", "transfer_funds", "pay_bill",
            "update_profile", "logout",
        ],
        "elements": {
            "input[name=username]": {"role": "input", "id": "username", "name": "username", "type": "text"},
            "input[name=password]": {"role": "input", "id": "password", "name": "password", "type": "password"},
            "input[value='Log In']": {"role": "button", "id": "login", "name": "login", "label": "Log In"},
            "input[name='customer.firstName']": {"role": "input", "id": "firstName", "name": "customer.firstName", "type": "text"},
            "input[name='customer.lastName']": {"role": "input", "id": "lastName", "name": "customer.lastName", "type": "text"},
            "input[name='fromAccountId']": {"role": "input", "id": "fromAccountId", "name": "fromAccountId", "type": "text"},
            "input[name='toAccountId']": {"role": "input", "id": "toAccountId", "name": "toAccountId", "type": "text"},
            "input[name='amount']": {"role": "input", "id": "amount", "name": "amount", "type": "number"},
            "input[value='Transfer']": {"role": "button", "id": "transfer", "name": "transfer", "label": "Transfer"},
        },
    },
    {
        "id": "demoqa",
        "name": "DemoQA",
        "url": "https://demoqa.com/",
        "domain": "forms / widgets",
        "requirements": _reqs(
            ("REQ-TB-1", "Text-box form accepts all fields", "forms"),
            ("REQ-TB-2", "Submitted values are echoed in output", "forms"),
            ("REQ-TB-3", "Invalid email is rejected", "forms"),
            ("REQ-CB-1", "Checkboxes toggle correctly", "widgets"),
            ("REQ-RB-1", "Radio groups allow single selection", "widgets"),
            ("REQ-DD-1", "Dropdowns select and persist a value", "widgets"),
            ("REQ-BTN-1", "Button clicks fire once", "widgets"),
            ("REQ-NAV-1", "Side navigation links resolve", "navigation"),
            ("REQ-SEC-1", "Forms validate input length", "security"),
            ("REQ-ACC-1", "Labels are associated with inputs", "accessibility"),
            ("REQ-ACC-2", "Focus order follows the DOM", "accessibility"),
            ("REQ-DATA-1", "Submitted data is not stored server-side", "data"),
        ),
        "workflows": [
            "textbox_fill", "textbox_validate_email", "checkbox_toggle",
            "radiobutton_select", "dropdown_select", "button_click",
            "navigate_elements", "form_submit", "verify_output",
        ],
        "elements": {
            "#userName": {"role": "input", "id": "userName", "name": "userName", "type": "text"},
            "#userEmail": {"role": "input", "id": "userEmail", "name": "userEmail", "type": "email"},
            "#currentAddress": {"role": "input", "id": "currentAddress", "name": "currentAddress", "type": "text"},
            "#permanentAddress": {"role": "input", "id": "permanentAddress", "name": "permanentAddress", "type": "text"},
            "#submit": {"role": "button", "id": "submit", "name": "submit", "label": "Submit"},
            "#output": {"role": "link", "id": "output", "label": "output"},
            "#item-0": {"role": "link", "id": "item-0", "label": "Text Box"},
            "#tree-node-home": {"role": "link", "id": "tree-node-home", "label": "Home"},
        },
    },
    {
        "id": "theinternet",
        "name": "The Internet",
        "url": "https://the-internet.herokuapp.com/",
        "domain": "UI patterns",
        "requirements": _reqs(
            ("REQ-LOGIN-1", "Form login accepts valid credentials", "auth"),
            ("REQ-LOGIN-2", "Invalid login shows an error banner", "auth"),
            ("REQ-DD-1", "Dropdown selects options", "widgets"),
            ("REQ-CB-1", "Checkboxes toggle on click", "widgets"),
            ("REQ-HOV-1", "Hover reveals submenu", "widgets"),
            ("REQ-UPL-1", "File upload accepts a file", "forms"),
            ("REQ-DRAG-1", "Drag-and-drop reorders elements", "widgets"),
            ("REQ-AUTH-1", "Basic auth challenge appears", "security"),
            ("REQ-ACC-1", "Dynamic controls are keyboard reachable", "accessibility"),
            ("REQ-NAV-1", "Home page lists all example links", "navigation"),
            ("REQ-ERR-1", "404 page renders gracefully", "error"),
            ("REQ-STAT-1", "Status codes page returns expected codes", "api"),
        ),
        "workflows": [
            "form_login", "form_login_invalid", "dropdown_select",
            "checkbox_toggle", "hover_menu", "file_upload",
            "drag_drop", "basic_auth", "dynamic_loading",
        ],
        "elements": {
            "#username": {"role": "input", "id": "username", "name": "username", "type": "text"},
            "#password": {"role": "input", "id": "password", "name": "password", "type": "password"},
            "button[type=submit]": {"role": "button", "id": "submit", "name": "submit", "label": "Login"},
            "#dropdown": {"role": "input", "id": "dropdown", "name": "dropdown", "type": "select"},
            "input[type=checkbox]": {"role": "input", "id": "checkbox", "name": "checkbox", "type": "checkbox"},
            "#file-upload": {"role": "input", "id": "file-upload", "name": "file", "type": "file"},
            "#column-a": {"role": "link", "id": "column-a", "label": "A"},
            "#column-b": {"role": "link", "id": "column-b", "label": "B"},
        },
    },
    {
        "id": "orangehrm",
        "name": "OrangeHRM (demo)",
        "url": "https://opensource-demo.orangehrmlive.com/",
        "domain": "HR / admin",
        "requirements": _reqs(
            ("REQ-LOGIN-1", "Admin logs in with valid credentials", "auth"),
            ("REQ-LOGIN-2", "Invalid credentials show an error", "auth"),
            ("REQ-EMP-1", "Employee list is searchable", "employee"),
            ("REQ-EMP-2", "Employee record can be added", "employee"),
            ("REQ-LEAVE-1", "Leave can be assigned", "leave"),
            ("REQ-TIME-1", "Timesheet can be submitted", "time"),
            ("REQ-REC-1", "Recruitment candidates are listed", "recruitment"),
            ("REQ-SEC-1", "Session requires authentication", "security"),
            ("REQ-SEC-2", "Role-based menus are enforced", "security"),
            ("REQ-ACC-1", "Dashboard is keyboard navigable", "accessibility"),
            ("REQ-NAV-1", "Sidebar modules resolve", "navigation"),
            ("REQ-DATA-1", "PII is masked in listings", "data"),
        ),
        "workflows": [
            "login_valid", "login_invalid", "search_employee", "add_employee",
            "assign_leave", "submit_timesheet", "view_candidates",
            "navigate_modules", "logout",
        ],
        "elements": {
            "input[name=username]": {"role": "input", "id": "username", "name": "username", "type": "text"},
            "input[name=password]": {"role": "input", "id": "password", "name": "password", "type": "password"},
            "button[type=submit]": {"role": "button", "id": "submit", "name": "submit", "label": "Login"},
            "input[name='firstName']": {"role": "input", "id": "firstName", "name": "firstName", "type": "text"},
            "input[name='lastName']": {"role": "input", "id": "lastName", "name": "lastName", "type": "text"},
            "input[name='employeeId']": {"role": "input", "id": "employeeId", "name": "employeeId", "type": "text"},
            "button#save": {"role": "button", "id": "save", "name": "save", "label": "Save"},
        },
    },
    {
        "id": "autopractice",
        "name": "Automation Exercise",
        "url": "https://automationexercise.com/",
        "domain": "e-commerce",
        "requirements": _reqs(
            ("REQ-REG-1", "New user can sign up", "auth"),
            ("REQ-REG-2", "Signup validates email format", "auth"),
            ("REQ-LOGIN-1", "Registered user logs in", "auth"),
            ("REQ-LOGIN-2", "Incorrect password is rejected", "auth"),
            ("REQ-SEARCH-1", "Product search returns results", "catalog"),
            ("REQ-CART-1", "Product adds to cart", "cart"),
            ("REQ-CART-2", "Cart quantity updates", "cart"),
            ("REQ-CHK-1", "Checkout collects payment", "checkout"),
            ("REQ-CONT-1", "Contact form submits", "forms"),
            ("REQ-SUB-1", "Newsletter subscription registers", "forms"),
            ("REQ-ACC-1", "Product cards are keyboard focusable", "accessibility"),
            ("REQ-NAV-1", "Top navigation categories resolve", "navigation"),
        ),
        "workflows": [
            "signup", "signup_validate_email", "login_valid", "login_invalid",
            "search_product", "add_to_cart", "update_cart_qty",
            "checkout", "contact_form",
        ],
        "elements": {
            "input[name=name]": {"role": "input", "id": "name", "name": "name", "type": "text"},
            "input[data-qa='signup-email']": {"role": "input", "id": "signup-email", "name": "signup-email", "type": "email"},
            "input[data-qa='login-email']": {"role": "input", "id": "login-email", "name": "login-email", "type": "email"},
            "input[data-qa='login-password']": {"role": "input", "id": "login-password", "name": "login-password", "type": "password"},
            "input[data-qa='signup-name']": {"role": "input", "id": "signup-name", "name": "signup-name", "type": "text"},
            "button[data-qa='signup-button']": {"role": "button", "id": "signup-button", "name": "signup-button", "label": "Signup"},
            "button[data-qa='login-button']": {"role": "button", "id": "login-button", "name": "login-button", "label": "Login"},
            "input[name=search]": {"role": "input", "id": "search", "name": "search", "type": "search"},
        },
    },
]


def total_workflows() -> int:
    return sum(len(a["workflows"]) for a in APPS)


def total_requirements() -> int:
    return sum(len(a["requirements"]) for a in APPS)
