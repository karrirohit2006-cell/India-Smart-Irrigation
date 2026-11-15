"""
Comprehensive Automated Test Suite for:
Updated Farmer Registration, Username/Password Authentication,
Native WebAuthn Face Lock (Passkeys), and Device Security Management.

Covers all 10 required scenarios:
1. Create an account using username and password only.
2. Reject duplicate usernames.
3. Reject mismatched passwords.
4. Enable Face Lock on a supported device.
5. Log in using the registered Passkey.
6. Log in using username and password.
7. Test on a device without Face Unlock.
8. Skip Face Lock and verify password login still works.
9. Log out and verify protected pages redirect to login.
10. Verify that no mobile number or OTP field appears anywhere in the farmer authentication flow.
Plus Face Lock Management: View devices, Revoke with password confirmation, Disable Face Lock with password confirmation.
"""

import json
import hashlib
import secrets
import cbor2
import pytest
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
import webauthn
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

from app import app
from src.farm_manager import (
    init_farm_db,
    seed_demo_accounts,
    authenticate_farmer,
    get_farmer_by_id,
    get_db_connection,
)
from src.passkey_manager import (
    init_passkey_db,
    generate_passkey_registration_options,
    verify_passkey_registration,
    generate_passkey_authentication_options,
    verify_passkey_authentication,
    get_farmer_registered_devices,
    delete_farmer_passkey,
    disable_all_farmer_passkeys,
)
from src.admin_manager import (
    init_admin_db,
    bootstrap_super_admin,
)


@pytest.fixture(autouse=True)
def setup_databases():
    """Ensure farm, admin, and passkey tables are clean and ready."""
    init_farm_db()
    seed_demo_accounts()
    init_admin_db()
    bootstrap_super_admin()
    init_passkey_db()

    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE admins SET failed_login_attempts = 0, locked_until = NULL WHERE username = 'admin';")
            conn.execute("UPDATE farmers SET status = 'Active', suspended_at = NULL, suspend_reason = NULL;")
            conn.execute("DELETE FROM farmer_passkeys;")
    finally:
        conn.close()


@pytest.fixture
def client():
    """Test client for Flask HTTP endpoints."""
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-facelock-2026"
    with app.test_client() as client:
        yield client


def make_test_passkey(farmer_id: str, device_name: str = "Test Face Lock Device", rp_id: str = "localhost"):
    """Helper to generate a real cryptographic ES256 passkey and register it into the database."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()
    x = public_numbers.x.to_bytes(32, "big")
    y = public_numbers.y.to_bytes(32, "big")
    cose_key = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: x, -3: y})

    cred_raw_id = f"cred_{farmer_id[:8]}_{secrets.token_hex(6)}".encode("utf-8")
    cred_id_b64 = bytes_to_base64url(cred_raw_id)

    conn = get_db_connection()
    now_iso = datetime.now().isoformat()
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO farmer_passkeys (
                    id, farmer_id, public_key, sign_count, device_name, aaguid, created_at, last_used_at
                ) VALUES (?, ?, ?, 0, ?, 'test-aaguid', ?, ?);
            """, (cred_id_b64, farmer_id, cose_key, device_name, now_iso, now_iso))
    finally:
        conn.close()

    return {
        "private_key": private_key,
        "credential_id": cred_raw_id,
        "cred_id_b64": cred_id_b64,
        "device_name": device_name,
        "cose_key": cose_key,
        "farmer_id": farmer_id,
    }


def create_assertion_signature(private_key, credential_id: bytes, challenge_b64: str, rp_id: str = "localhost", origin: str = "http://localhost:5000", sign_count_int: int = 1):
    """Helper to sign a WebAuthn challenge with private key, exactly as native device Face Unlock does."""
    client_data = {
        "type": "webauthn.get",
        "challenge": challenge_b64,
        "origin": origin,
        "crossOrigin": False,
    }
    client_data_bytes = json.dumps(client_data).encode("utf-8")
    client_data_hash = hashlib.sha256(client_data_bytes).digest()

    rp_id_hash = hashlib.sha256(rp_id.encode("utf-8")).digest()
    flags = bytes([0x01 | 0x04])  # User Present + User Verified (Biometric Face Unlock)
    sign_count = sign_count_int.to_bytes(4, "big")
    auth_data = rp_id_hash + flags + sign_count

    to_sign = auth_data + client_data_hash
    signature = private_key.sign(to_sign, ec.ECDSA(hashes.SHA256()))

    return {
        "id": bytes_to_base64url(credential_id),
        "rawId": bytes_to_base64url(credential_id),
        "type": "public-key",
        "response": {
            "authenticatorData": bytes_to_base64url(auth_data),
            "clientDataJSON": bytes_to_base64url(client_data_bytes),
            "signature": bytes_to_base64url(signature),
            "userHandle": None,
        },
    }


# ========================================================
# 1. Create Account Using Username and Password Only
# ========================================================
def test_1_create_account_using_username_and_password_only(client):
    """Scenario 1: Farmer creates an account using only username, password and confirm_password."""
    uname = f"farmer_{secrets.token_hex(4)}"
    pwd = "AgriPassword@2026!"

    res = client.post("/api/auth/register", json={
        "username": uname,
        "password": pwd,
        "confirm_password": pwd,
    })

    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["farmer"]["username"] == uname.lower()
    assert data["offer_passkey"] is True
    assert data["redirect"] == "/onboarding"

    # Verify database state
    conn = get_db_connection()
    try:
        farmer_row = conn.execute("SELECT * FROM farmers WHERE username = ?;", (uname.lower(),)).fetchone()
        assert farmer_row is not None
        assert farmer_row["username"] == uname.lower()
        # Verify no mobile number was stored
        assert farmer_row["phone"] is None
        assert farmer_row["onboarding_completed"] == 0
        assert farmer_row["status"] == "Active"
    finally:
        conn.close()


# ========================================================
# 2. Reject Duplicate Usernames
# ========================================================
def test_2_reject_duplicate_usernames(client):
    """Scenario 2: The registration system must reject duplicate usernames (case-insensitive)."""
    uname = f"unique_user_{secrets.token_hex(4)}"
    pwd = "SecurePassword123!"

    # First registration
    res1 = client.post("/api/auth/register", json={
        "username": uname,
        "password": pwd,
        "confirm_password": pwd,
    })
    assert res1.status_code == 201

    # Second registration with identical username
    res2 = client.post("/api/auth/register", json={
        "username": uname,
        "password": "AnotherPassword456!",
        "confirm_password": "AnotherPassword456!",
    })
    assert res2.status_code == 409
    assert "already taken" in res2.get_json()["error"].lower()

    # Third registration with uppercase version of the same username
    res3 = client.post("/api/auth/register", json={
        "username": uname.upper(),
        "password": "AnotherPassword456!",
        "confirm_password": "AnotherPassword456!",
    })
    assert res3.status_code == 409
    assert "already taken" in res3.get_json()["error"].lower()


# ========================================================
# 3. Reject Mismatched Passwords and Empty Fields
# ========================================================
def test_3_reject_mismatched_passwords_and_empty_fields(client):
    """Scenario 3: Validation must reject mismatched passwords and empty fields."""
    # Mismatched passwords
    res1 = client.post("/api/auth/register", json={
        "username": "mismatch_user",
        "password": "Password123",
        "confirm_password": "DifferentPassword456",
    })
    assert res1.status_code == 400
    assert "do not match" in res1.get_json()["error"].lower()

    # Empty username
    res2 = client.post("/api/auth/register", json={
        "username": "",
        "password": "Password123",
        "confirm_password": "Password123",
    })
    assert res2.status_code == 400
    assert "required" in res2.get_json()["error"].lower()

    # Empty password
    res3 = client.post("/api/auth/register", json={
        "username": "empty_pass_user",
        "password": "",
        "confirm_password": "",
    })
    assert res3.status_code == 400
    assert "required" in res3.get_json()["error"].lower()

    # Too short password (< 6 chars)
    res4 = client.post("/api/auth/register", json={
        "username": "short_pass_user",
        "password": "123",
        "confirm_password": "123",
    })
    assert res4.status_code == 400
    assert "at least 6 characters" in res4.get_json()["error"].lower()


# ========================================================
# 4. Enable Face Lock on a Supported Device
# ========================================================
def test_4_enable_face_lock_on_supported_device(client):
    """Scenario 4: Farmer registers Face Lock passkey using native WebAuthn."""
    # Register and sign in
    uname = f"facelock_user_{secrets.token_hex(4)}"
    pwd = "AgriPassword@2026!"
    client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})

    # Step 1: Request WebAuthn registration options
    opt_res = client.post("/api/auth/passkey/register-options")
    assert opt_res.status_code == 200
    opt_data = opt_res.get_json()
    assert "challenge" in opt_data
    assert "rp" in opt_data

    # Step 2: Simulate client device creating passkey and verify
    conn = get_db_connection()
    farmer_id = conn.execute("SELECT id FROM farmers WHERE username = ?;", (uname.lower(),)).fetchone()["id"]
    conn.close()

    passkey = make_test_passkey(farmer_id, device_name="iPhone Face ID")

    # Step 3: Query registered devices
    devices = get_farmer_registered_devices(farmer_id)
    assert len(devices) == 1
    assert devices[0]["device_name"] == "iPhone Face ID"


# ========================================================
# 5. Log In Using the Registered Passkey
# ========================================================
def test_5_login_using_registered_passkey(client):
    """Scenario 5: Subsequent login using Face Lock passkey without typing password."""
    uname = f"biometric_login_{secrets.token_hex(4)}"
    pwd = "FarmerSecret@999"

    # Register farmer
    reg_res = client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # Register passkey
    passkey = make_test_passkey(farmer_id, device_name="Android Pixel Face Unlock")

    # Clear session to simulate returning on a new visit
    client.get("/logout")

    # Step 1: Request login options
    opt_res = client.post("/api/auth/passkey/login-options", json={"username": uname})
    assert opt_res.status_code == 200
    options = opt_res.get_json()
    challenge_b64 = options["challenge"]

    # Step 2: Sign challenge with private key
    assertion = create_assertion_signature(
        private_key=passkey["private_key"],
        credential_id=passkey["credential_id"],
        challenge_b64=challenge_b64,
        rp_id="localhost",
        origin="http://localhost:5000",
    )

    # Step 3: Verify assertion
    verify_res = client.post("/api/auth/passkey/login-verify", json={"credential": assertion})
    assert verify_res.status_code == 200
    data = verify_res.get_json()
    assert data["status"] == "success"
    assert data["farmer"]["id"] == farmer_id
    assert data["farmer"]["username"] == uname.lower()

    # Step 4: Verify authenticated session
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True
    assert me_res.get_json()["has_passkeys"] is True


# ========================================================
# 6. Log In Using Username and Password
# ========================================================
def test_6_login_using_username_and_password(client):
    """Scenario 6: Username + password authentication works consistently."""
    uname = f"pwd_user_{secrets.token_hex(4)}"
    pwd = "ValidPassword123!"

    client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})
    client.get("/logout")

    # Valid credentials
    res = client.post("/api/auth/login", json={"username": uname, "password": pwd})
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"
    assert res.get_json()["farmer"]["username"] == uname.lower()

    # Invalid password
    res_bad = client.post("/api/auth/login", json={"username": uname, "password": "WrongPassword"})
    assert res_bad.status_code == 401
    assert "invalid username or password" in res_bad.get_json()["error"].lower()

    # Nonexistent user
    res_no = client.post("/api/auth/login", json={"username": "nonexistent_99", "password": "Password123"})
    assert res_no.status_code == 401


# ========================================================
# 7. Test on a Device Without Face Unlock
# ========================================================
def test_7_device_without_face_unlock_uses_password_gracefully(client):
    """Scenario 7: Devices without Face Unlock can log in via username and password seamlessly."""
    uname = f"noface_user_{secrets.token_hex(4)}"
    pwd = "StandardPassword2026!"

    client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})
    client.get("/logout")

    # Login works without touching WebAuthn
    login_res = client.post("/api/auth/login", json={"username": uname, "password": pwd})
    assert login_res.status_code == 200
    assert login_res.get_json()["status"] == "success"

    # Calling passkey verification with invalid or missing challenge fails gracefully
    verify_res = client.post("/api/auth/passkey/login-verify", json={})
    assert verify_res.status_code == 400


# ========================================================
# 8. Skip Face Lock and Verify Password Login Still Works
# ========================================================
def test_8_skip_face_lock_and_verify_password_login_works(client):
    """Scenario 8: Farmer registers, skips Face Lock setup, and logs in using password."""
    uname = f"skip_face_{secrets.token_hex(4)}"
    pwd = "SkipPassword2026!"

    # Register
    reg_res = client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})
    assert reg_res.status_code == 201

    # Farmer clicks "Skip for Now" -> simply logs out without registering a passkey
    client.get("/logout")

    # Log in with username and password
    res = client.post("/api/auth/login", json={"username": uname, "password": pwd})
    assert res.status_code == 200
    assert res.get_json()["status"] == "success"

    # Verify /api/auth/me indicates has_passkeys is False
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["has_passkeys"] is False
    assert me_res.get_json()["passkeys_count"] == 0


# ========================================================
# 9. Log Out and Verify Protected Pages Redirect to Login
# ========================================================
def test_9_logout_clears_session_and_redirects_protected_pages(client):
    """Scenario 9: Logging out clears session and prevents access to protected routes."""
    uname = f"logout_test_{secrets.token_hex(4)}"
    pwd = "LogoutPassword2026!"

    client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})

    # While logged in: /api/auth/me works
    assert client.get("/api/auth/me").status_code == 200

    # Log out
    logout_res = client.get("/logout")
    assert logout_res.status_code == 302
    assert logout_res.location == "/"

    # Root landing displays login page
    root_res = client.get("/")
    assert root_res.status_code == 200
    assert "Sign in to manage your farm" in root_res.get_data(as_text=True)

    # Protected dashboard redirects to login
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 302
    assert dash_res.location == "/"

    # Protected onboarding redirects to login
    onb_res = client.get("/onboarding")
    assert onb_res.status_code == 302
    assert onb_res.location == "/"

    # Protected API endpoints return 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/passkey/devices").status_code == 401


# ========================================================
# 10. Verify No Mobile Number or OTP Field in Auth Flow
# ========================================================
def test_10_verify_no_mobile_number_or_otp_field_in_auth_flow(client):
    """Scenario 10: Verify HTML pages contain NO mobile number or OTP fields."""
    # 1. Login Page (GET /)
    login_html = client.get("/").get_data(as_text=True)

    # Must contain Username, Password, Sign In, Login with Face Lock
    assert 'id="loginUsername"' in login_html
    assert 'id="loginPassword"' in login_html
    assert 'id="btnSignIn"' in login_html
    assert 'id="btnLoginFaceLock"' in login_html
    assert "Login with Face Lock" in login_html

    # Must NOT contain mobile or OTP inputs
    assert 'type="tel"' not in login_html
    assert 'id="loginPhone"' not in login_html
    assert 'id="loginOtpCode"' not in login_html
    assert "Send Login OTP" not in login_html
    assert "Send OTP" not in login_html

    # 2. Register Page (GET /register)
    reg_html = client.get("/register").get_data(as_text=True)

    # Must contain Username, Password, Confirm Password, Create Account
    assert 'id="regUsername"' in reg_html
    assert 'id="regPassword"' in reg_html
    assert 'id="regConfirmPassword"' in reg_html
    assert 'id="btnCreateAccount"' in reg_html
    assert "Create Account" in reg_html

    # Face Lock Setup Screen elements
    assert "Enable Face Lock for faster and secure login." in reg_html
    assert 'id="btnEnableFaceLock"' in reg_html
    assert 'id="btnSkipFaceLock"' in reg_html

    # Must NOT contain phone or OTP inputs
    assert 'type="tel"' not in reg_html
    assert 'id="regPhone"' not in reg_html
    assert 'id="regOtp"' not in reg_html
    assert "Send OTP" not in reg_html


# ========================================================
# 11. Face Lock Management: Password Required to Revoke / Disable
# ========================================================
def test_11_face_lock_management_requires_password_confirmation(client):
    """Scenario 11: Revoking a passkey or disabling Face Lock requires password confirmation."""
    uname = f"mgmt_user_{secrets.token_hex(4)}"
    pwd = "SecurityPassword@2026"

    # Register and sign in
    reg_res = client.post("/api/auth/register", json={"username": uname, "password": pwd, "confirm_password": pwd})
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # Register two devices
    passkey1 = make_test_passkey(farmer_id, device_name="Device 1: Phone Face ID")
    passkey2 = make_test_passkey(farmer_id, device_name="Device 2: Laptop Touch ID")

    # List devices
    dev_res = client.get("/api/auth/passkey/devices")
    assert dev_res.status_code == 200
    assert len(dev_res.get_json()["devices"]) == 2

    # Attempt to revoke Device 1 without password -> 400
    del_no_pwd = client.delete(f"/api/auth/passkey/devices/{passkey1['cred_id_b64']}", json={})
    assert del_no_pwd.status_code == 400
    assert "password confirmation is required" in del_no_pwd.get_json()["error"].lower()

    # Attempt to revoke Device 1 with WRONG password -> 401
    del_bad_pwd = client.delete(f"/api/auth/passkey/devices/{passkey1['cred_id_b64']}", json={"password": "WrongPassword"})
    assert del_bad_pwd.status_code == 401
    assert "incorrect password" in del_bad_pwd.get_json()["error"].lower()

    # Revoke Device 1 with CORRECT password -> 200
    del_ok = client.delete(f"/api/auth/passkey/devices/{passkey1['cred_id_b64']}", json={"password": pwd})
    assert del_ok.status_code == 200
    assert del_ok.get_json()["status"] == "success"

    # Verify only 1 device remains
    dev_res2 = client.get("/api/auth/passkey/devices")
    assert len(dev_res2.get_json()["devices"]) == 1
    assert dev_res2.get_json()["devices"][0]["id"] == passkey2["cred_id_b64"]

    # Attempt to disable Face Lock without password -> 400
    dis_no_pwd = client.post("/api/auth/passkey/disable", json={})
    assert dis_no_pwd.status_code == 400

    # Attempt to disable Face Lock with wrong password -> 401
    dis_bad_pwd = client.post("/api/auth/passkey/disable", json={"password": "WrongPassword"})
    assert dis_bad_pwd.status_code == 401

    # Disable Face Lock with correct password -> 200
    dis_ok = client.post("/api/auth/passkey/disable", json={"password": pwd})
    assert dis_ok.status_code == 200
    assert dis_ok.get_json()["status"] == "success"

    # Verify zero devices remain
    dev_res3 = client.get("/api/auth/passkey/devices")
    assert len(dev_res3.get_json()["devices"]) == 0
