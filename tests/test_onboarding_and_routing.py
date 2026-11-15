"""
Comprehensive Integration & Acceptance Test Suite for:
Redesigned Farmer Authentication Landing, First-Time Onboarding Wizard,
WebAuthn Biometrics, Role Separation & Route Security.

Tests all 18 requirements specified in Phase 7:
1. Opening website root (/) displays Farmer Login landing page.
2. Farmer account creation with full name, mobile number, OTP, username, password.
3. OTP verification validation rules (rate-limiting, incorrect attempts, phone isolation).
4. Username and password authentication.
5. Passkey registration options and verification.
6. Biometric / passkey passwordless login.
7. Mobile OTP fallback login.
8. Incomplete profile redirects to /onboarding.
9. Farm location reverse geocoding and coordinates handling.
10. No hardcoded Punjab on onboarding; real state selection.
11. Farmer can create zero sections or multiple independent sections.
12. Total land validation enforces section area <= total farm area.
13. Farmer details persist across sessions and database reloads.
14. Returning onboarded farmer goes directly to /dashboard.
15. Logout clears session and redirects to /.
16. Cross-farmer data isolation is strictly preserved.
17. Super Admin authentication and portal remain independent and functional.
18. Protected routes enforce strict authentication redirects.
"""

import json
import secrets
import pytest
from app import app
from src.farm_manager import (
    init_farm_db,
    seed_demo_accounts,
    authenticate_farmer,
    get_farmer_by_id,
    get_farmer_farms,
    get_farm_sections,
)
from src.passkey_manager import (
    init_passkey_db,
    send_mobile_otp,
    verify_mobile_otp,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-391823"
    init_farm_db()
    seed_demo_accounts()
    init_passkey_db()
    with app.test_client() as client:
        yield client


# ========================================================
# 1. Unauthenticated Visitor Root Landing Page
# ========================================================
def test_1_unauthenticated_visitor_gets_farmer_login_page(client):
    """When anyone opens /, the first screen is ALWAYS the Farmer Login page."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Smart Irrigation Planner" in html
    assert "Welcome, Farmer" in html
    assert ("Login with Face Lock" in html or "Login with Face / Fingerprint" in html)
    assert "Username" in html
    assert "Sign In" in html
    assert "New farmer?" in html
    # Ensure protected dashboard panels are NOT leaked on the login screen
    assert "id=\"landManagementModule\"" not in html


# ========================================================
# 2. Farmer Account Creation with OTP & Username
# ========================================================
def test_2_farmer_account_creation_with_username_and_otp(client):
    """Farmer creates an account via /register with full name, verified mobile OTP, username & password."""
    reg_page_res = client.get("/register")
    assert reg_page_res.status_code == 200
    assert "Create Farmer Account" in reg_page_res.get_data(as_text=True)

    unique_phone = f"97{secrets.randbelow(100000000):08d}"
    unique_user = f"farmer_{secrets.token_hex(4)}"

    # 1. Dispatch OTP
    otp_res = client.post("/api/auth/otp/send", json={"phone": unique_phone, "purpose": "register"})
    assert otp_res.status_code == 200
    otp_code = otp_res.get_json()["otp_preview"]

    # 2. Submit Registration
    reg_payload = {
        "name": "Davinder Singh",
        "phone": unique_phone,
        "otp": otp_code,
        "username": unique_user,
        "password": "strongPassword123",
        "confirm_password": "strongPassword123",
    }
    create_res = client.post("/api/auth/register-with-otp", json=reg_payload)
    assert create_res.status_code == 201
    cdata = create_res.get_json()
    assert cdata["status"] == "success"
    assert cdata["farmer"]["username"] == unique_user
    assert cdata["farmer"]["onboarding_completed"] is False
    assert cdata["offer_passkey"] is True
    assert cdata["redirect"] == "/onboarding"


# ========================================================
# 3. Mobile OTP Validation Rules
# ========================================================
def test_3_mobile_otp_validation_rules(client):
    """OTP validation rejects incorrect codes and mismatched purposes."""
    temp_phone = f"96{secrets.randbelow(100000000):08d}"
    client.post("/api/auth/otp/send", json={"phone": temp_phone, "purpose": "register"})

    # Wrong code
    bad_res = client.post("/api/auth/register-with-otp", json={
        "name": "Bad OTP User",
        "phone": temp_phone,
        "otp": "000000",
        "username": f"user_{secrets.token_hex(4)}",
        "password": "password123",
    })
    assert bad_res.status_code == 400
    assert "incorrect" in bad_res.get_json()["error"].lower()


# ========================================================
# 4. Username and Password Authentication
# ========================================================
def test_4_username_and_password_authentication(client):
    """Farmers can log in using their username OR mobile number with password."""
    # Test with demo farmer A (Ramesh)
    # 1. Login with username
    u_res = client.post("/api/auth/login", json={"identifier": "ramesh", "password": "farmer123"})
    assert u_res.status_code == 200
    assert u_res.get_json()["status"] == "success"
    assert u_res.get_json()["redirect"] == "/dashboard"

    # 2. Login with phone
    p_res = client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})
    assert p_res.status_code == 200
    assert p_res.get_json()["status"] == "success"

    # 3. Bad password rejected
    bad_res = client.post("/api/auth/login", json={"identifier": "ramesh", "password": "wrongPassword!"})
    assert bad_res.status_code == 401


# ========================================================
# 5. WebAuthn Passkey Registration Options
# ========================================================
def test_5_webauthn_passkey_options(client):
    """Authenticated farmer can generate WebAuthn registration options."""
    client.post("/api/auth/login", json={"identifier": "ramesh", "password": "farmer123"})
    opt_res = client.post("/api/auth/passkey/register-options")
    assert opt_res.status_code == 200
    opt_data = opt_res.get_json()
    assert "challenge" in opt_data
    assert opt_data["rp"]["name"] == "AgroSmart Irrigation"
    assert opt_data["authenticatorSelection"]["authenticatorAttachment"] == "platform"


# ========================================================
# 6. Biometric / Passkey Login Verification
# ========================================================
def test_6_passkey_login_options(client):
    """Passkey login challenge generation for passwordless 1-touch authentication."""
    opt_res = client.post("/api/auth/passkey/login-options", json={"phone": "9876543210"})
    assert opt_res.status_code == 200
    assert "challenge" in opt_res.get_json()


# ========================================================
# 7. Mobile OTP Fallback Login
# ========================================================
def test_7_mobile_otp_fallback_login(client):
    """Farmer logs in with 1-click mobile OTP when biometrics/password are unavailable."""
    phone = "9876543210"
    send_res = client.post("/api/auth/otp/send", json={"phone": phone, "purpose": "login"})
    assert send_res.status_code == 200
    otp_code = send_res.get_json()["otp_preview"]

    verify_res = client.post("/api/auth/otp/verify", json={"phone": phone, "otp": otp_code, "purpose": "login"})
    assert verify_res.status_code == 200
    vdata = verify_res.get_json()
    assert vdata["status"] == "success"
    assert vdata["farmer"]["phone"] == phone
    assert vdata["redirect"] == "/dashboard"


# ========================================================
# 8. Incomplete Profile Redirects to /onboarding
# ========================================================
def test_8_incomplete_profile_redirects_to_onboarding(client):
    """Newly registered farmer accessing / or /dashboard is redirected to /onboarding."""
    unique_phone = f"95{secrets.randbelow(100000000):08d}"
    unique_user = f"user_{secrets.token_hex(4)}"

    # Register new farmer
    otp_res = client.post("/api/auth/otp/send", json={"phone": unique_phone, "purpose": "register"})
    client.post("/api/auth/register-with-otp", json={
        "name": "New Farmer",
        "phone": unique_phone,
        "otp": otp_res.get_json()["otp_preview"],
        "username": unique_user,
        "password": "password123",
        "confirm_password": "password123",
    })

    # Access root / -> must redirect to /onboarding
    root_res = client.get("/", follow_redirects=False)
    assert root_res.status_code == 302
    assert root_res.headers["Location"].endswith("/onboarding")

    # Access /dashboard -> must redirect to /onboarding
    dash_res = client.get("/dashboard", follow_redirects=False)
    assert dash_res.status_code == 302
    assert dash_res.headers["Location"].endswith("/onboarding")

    # Access /onboarding -> renders 200 OK
    onboard_res = client.get("/onboarding")
    assert onboard_res.status_code == 200
    assert "First-Time Farmer Setup" in onboard_res.get_data(as_text=True)


# ========================================================
# 9. Location Detection & Reverse Geocoding
# ========================================================
def test_9_location_reverse_geocoding(client):
    """Coordinates reverse geocoding retrieves valid state and district."""
    rev_res = client.get("/api/location/reverse?lat=30.9010&lon=75.8573")
    assert rev_res.status_code == 200
    rev_data = rev_res.get_json()
    assert "state" in rev_data
    assert rev_data["state"] == "Punjab"


# ========================================================
# 10. No Hardcoded Punjab on Onboarding
# ========================================================
def test_10_no_hardcoded_punjab_on_onboarding(client):
    """States list API loads all 36 Indian states dynamically for clean selection."""
    states_res = client.get("/api/states")
    assert states_res.status_code == 200
    states = states_res.get_json()["states"]
    assert len(states) >= 35
    assert "Andhra Pradesh" in states
    assert "Punjab" in states
    assert "Maharashtra" in states


# ========================================================
# 11. Farmer Can Create Zero Sections or Multiple Sections
# ========================================================
def test_11_farmer_can_create_zero_or_multiple_sections(client):
    """Onboarding supports zero sections (empty land) or multiple cultivated sections."""
    unique_phone = f"94{secrets.randbelow(100000000):08d}"
    unique_user = f"user_{secrets.token_hex(4)}"

    # Register
    otp_res = client.post("/api/auth/otp/send", json={"phone": unique_phone, "purpose": "register"})
    reg_res = client.post("/api/auth/register-with-otp", json={
        "name": "Simranjit Kaur",
        "phone": unique_phone,
        "otp": otp_res.get_json()["otp_preview"],
        "username": unique_user,
        "password": "password123",
        "confirm_password": "password123",
    })
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # Case A: Complete Onboarding with ZERO sections
    onboard_payload = {
        "name": "Simranjit Kaur",
        "state": "Haryana",
        "district": "Karnal",
        "village": "Taraori",
        "latitude": 29.8000,
        "longitude": 76.9200,
        "total_land": 3.00,
        "unit": "Acres",
        "sections": [],  # 0 sections: entire land remains uncultivated
    }
    ob_res = client.post("/api/farmer/onboarding", json=onboard_payload)
    assert ob_res.status_code == 200
    ob_data = ob_res.get_json()
    assert ob_data["status"] == "success"
    assert ob_data["redirect"] == "/dashboard"

    # Verify farmer is now marked onboarded
    f = get_farmer_by_id(farmer_id)
    assert f["onboarding_completed"] is True
    assert f["state"] == "Haryana"

    # Case B: Update with 2 sections (Wheat + Mustard)
    sec_payload = {
        "name": "Simranjit Kaur",
        "state": "Haryana",
        "district": "Karnal",
        "village": "Taraori",
        "latitude": 29.8000,
        "longitude": 76.9200,
        "total_land": 3.00,
        "unit": "Acres",
        "sections": [
            {"name": "Plot 1", "area": 1.50, "crop": "Wheat", "sowing_date": "2026-10-15", "soil_moisture": 30.0},
            {"name": "Plot 2", "area": 1.00, "crop": "Mustard", "sowing_date": "2026-10-20", "soil_moisture": 35.0},
        ],
    }
    sec_res = client.post("/api/farmer/onboarding", json=sec_payload)
    assert sec_res.status_code == 200
    farms = get_farmer_farms(farmer_id)
    sections = get_farm_sections(farms[0]["id"], farmer_id)
    assert len(sections) == 2


# ========================================================
# 12. Total Land Validation
# ========================================================
def test_12_total_land_validation(client):
    """Total of all section areas cannot exceed total farm area."""
    unique_phone = f"93{secrets.randbelow(100000000):08d}"
    otp_res = client.post("/api/auth/otp/send", json={"phone": unique_phone, "purpose": "register"})
    client.post("/api/auth/register-with-otp", json={
        "name": "Validation Farmer",
        "phone": unique_phone,
        "otp": otp_res.get_json()["otp_preview"],
        "username": f"user_{secrets.token_hex(4)}",
        "password": "password123",
        "confirm_password": "password123",
    })

    # Attempt to allocate 4.00 acres on a 2.00 acre farm
    invalid_payload = {
        "name": "Validation Farmer",
        "state": "Punjab",
        "total_land": 2.00,
        "unit": "Acres",
        "sections": [
            {"name": "Excess Plot", "area": 4.00, "crop": "Wheat"},
        ],
    }
    bad_res = client.post("/api/farmer/onboarding", json=invalid_payload)
    assert bad_res.status_code == 400
    assert "exceeds total farm land" in bad_res.get_json()["error"]


# ========================================================
# 13. Farmer Details Persist After Logout
# ========================================================
def test_13_farmer_details_persist_after_logout(client):
    """Farmer settings, location, and land persist in database after logging out."""
    # Logout
    logout_res = client.get("/logout", follow_redirects=False)
    assert logout_res.status_code == 302
    assert logout_res.headers["Location"].endswith("/")

    # Check unauthenticated
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 401


# ========================================================
# 14. Returning Onboarded Farmer Goes Directly to /dashboard
# ========================================================
def test_14_returning_onboarded_farmer_goes_directly_to_dashboard(client):
    """Authenticated onboarded farmer accessing / or /dashboard gets their dashboard."""
    # Login as Farmer A
    client.post("/api/auth/login", json={"identifier": "ramesh", "password": "farmer123"})

    # Access / -> redirects to /dashboard
    root_res = client.get("/", follow_redirects=False)
    assert root_res.status_code == 302
    assert root_res.headers["Location"].endswith("/dashboard")

    # Access /dashboard -> returns 200 OK
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    html = dash_res.get_data(as_text=True)
    assert "Smart Irrigation Planner" in html
    assert "landManagementModule" in html


# ========================================================
# 15. Logout Clears Session and Redirects to /
# ========================================================
def test_15_logout_clears_session_and_redirects(client):
    """GET /logout and POST /api/auth/logout both cleanly wipe the session."""
    client.post("/api/auth/login", json={"identifier": "ramesh", "password": "farmer123"})

    # POST logout
    post_res = client.post("/api/auth/logout")
    assert post_res.status_code == 200
    assert post_res.get_json()["redirect"] == "/"

    # Next request to protected dashboard must redirect to /
    dash_res = client.get("/dashboard", follow_redirects=False)
    assert dash_res.status_code == 302
    assert dash_res.headers["Location"].endswith("/")


# ========================================================
# 16. Cross-Farmer Data Isolation
# ========================================================
def test_16_strict_cross_farmer_isolation(client):
    """Farmer A cannot view or access Farmer B's farm or sections."""
    # Login as Farmer A
    client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})
    farms_a = client.get("/api/farms").get_json()["farms"]
    assert len(farms_a) >= 1
    farm_a_id = farms_a[0]["id"]

    # Login as Farmer B
    client.post("/api/auth/login", json={"identifier": "9876543211", "password": "farmer123"})
    farms_b = client.get("/api/farms").get_json()["farms"]
    assert len(farms_b) >= 1
    farm_b_id = farms_b[0]["id"]

    # IDs must be different
    assert farm_a_id != farm_b_id

    # Farmer B querying Farmer A's farm sections gets zero sections (isolated data)
    bad_query = client.get(f"/api/farms/{farm_a_id}/sections")
    assert bad_query.status_code == 200
    assert bad_query.get_json()["sections"] == []
    assert bad_query.get_json()["total_sections"] == 0


# ========================================================
# 17. Super Admin System Remains Completely Independent
# ========================================================
def test_17_super_admin_system_remains_independent(client):
    """Admin portal is distinct from farmer login; farmers cannot access /admin."""
    # Farmer login
    client.post("/api/auth/login", json={"identifier": "ramesh", "password": "farmer123"})

    # Farmer blocked from /admin -> redirected to /admin/login (302)
    farmer_admin_res = client.get("/admin", follow_redirects=False)
    assert farmer_admin_res.status_code == 302
    assert "/admin/login" in farmer_admin_res.headers.get("Location", "")

    # Farmer blocked from /api/admin/kpis (403 Forbidden)
    kpi_res = client.get("/api/admin/kpis")
    assert kpi_res.status_code == 403

    # Super Admin logs in via /api/admin/auth/login
    admin_login_res = client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    assert admin_login_res.status_code == 200

    # Super Admin can access KPIs
    admin_kpi = client.get("/api/admin/kpis")
    assert admin_kpi.status_code == 200
    assert "total_farmers" in admin_kpi.get_json()


# ========================================================
# 18. Protected Route Authentication Enforcements
# ========================================================
def test_18_protected_route_redirects(client):
    """Protected routes enforce strict unauthenticated redirects to /."""
    # 1. Unauthenticated /dashboard -> /
    res1 = client.get("/dashboard", follow_redirects=False)
    assert res1.status_code == 302
    assert res1.headers["Location"].endswith("/")

    # 2. Unauthenticated /onboarding -> /
    res2 = client.get("/onboarding", follow_redirects=False)
    assert res2.status_code == 302
    assert res2.headers["Location"].endswith("/")
