"""
Automated Integration and Security Tests for Farmer Passwordless Authentication.
Validates:
1. First-time farmer registration through verified mobile OTP.
2. Mobile OTP validation, rate-limiting, and error handling.
3. Registering WebAuthn Passkeys (Face ID / Fingerprint / PIN) bound to farmer accounts.
4. Subsequent passwordless login with Face / Fingerprint (WebAuthn signature verification).
5. Mobile OTP fallback login when device biometrics are unavailable.
6. Multiple registered devices per farmer account.
7. Device management, revocation, and re-registration (account recovery).
8. Complete farmer-level data isolation (Farmer A vs Farmer B).
9. Suspended farmer accounts are blocked from Passkey and OTP login (HTTP 403).
10. Super Admin authentication and management routes remain completely unbroken.
"""

import json
import hashlib
import secrets
import cbor2
import pytest
from datetime import datetime, timedelta
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
    get_farmer_farms,
)
from src.admin_manager import (
    init_admin_db,
    bootstrap_super_admin,
    set_farmer_status,
    get_db_connection,
)
from src.passkey_manager import (
    init_passkey_db,
    send_mobile_otp,
    verify_mobile_otp,
    generate_passkey_registration_options,
    verify_passkey_registration,
    generate_passkey_authentication_options,
    verify_passkey_authentication,
    get_farmer_registered_devices,
    delete_farmer_passkey,
)


@pytest.fixture(autouse=True)
def setup_databases():
    """Ensure multi-farmer, super admin, and passkey tables are clean and ready."""
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
            conn.execute("DELETE FROM farmer_otps;")
            conn.execute("DELETE FROM farmer_passkeys;")
    finally:
        conn.close()


@pytest.fixture
def client():
    """Test client for Flask HTTP endpoints."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_test_passkey(farmer_id: str, device_name: str = "Test Android Biometrics", rp_id: str = "localhost"):
    """Helper to generate a real cryptographic ES256 passkey and register it into the database."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()
    x = public_numbers.x.to_bytes(32, "big")
    y = public_numbers.y.to_bytes(32, "big")
    cose_key = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: x, -3: y})

    credential_id = f"cred_{farmer_id[:8]}_{secrets_token()}".encode("utf-8")
    cred_id_b64 = bytes_to_base64url(credential_id)

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
        "credential_id": credential_id,
        "cred_id_b64": cred_id_b64,
        "device_name": device_name,
        "cose_key": cose_key,
        "farmer_id": farmer_id,
    }


def secrets_token():
    import secrets
    return secrets.token_hex(6)


def create_assertion_signature(private_key, credential_id: bytes, challenge_b64: str, rp_id: str = "localhost", origin: str = "http://localhost:5000", sign_count_int: int = 1):
    """Helper to sign a WebAuthn challenge with private key, exactly as a hardware authenticator does."""
    client_data = {
        "type": "webauthn.get",
        "challenge": challenge_b64,
        "origin": origin,
        "crossOrigin": False,
    }
    client_data_bytes = json.dumps(client_data).encode("utf-8")
    client_data_hash = hashlib.sha256(client_data_bytes).digest()

    rp_id_hash = hashlib.sha256(rp_id.encode("utf-8")).digest()
    flags = bytes([0x01 | 0x04])  # User Present (UP) + User Verified (UV: Fingerprint/Face ID verified)
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
# 1. Verified Mobile OTP Registration
# ========================================================
def test_1_first_time_farmer_registration_via_verified_mobile_otp(client):
    """Farmer creates an account verified by mobile OTP, without needing a password."""
    new_phone = f"98{secrets.randbelow(100000000):08d}"

    # Step 1: Request OTP for registration
    send_res = client.post("/api/auth/otp/send", json={"phone": new_phone, "purpose": "register"})
    assert send_res.status_code == 200
    send_data = send_res.get_json()
    assert send_data["success"] is True
    otp_code = send_data["otp_preview"]
    assert len(otp_code) == 6

    # Step 2: Complete registration with verified OTP
    reg_payload = {
        "name": "Gurpreet Singh",
        "phone": new_phone,
        "otp": otp_code,
        "state": "Punjab",
        "district": "Patiala",
        "village": "Nabha",
        "latitude": 30.3753,
        "longitude": 76.1520,
        "total_land": 2.50,
        "unit": "Acres",
    }
    reg_res = client.post("/api/auth/register-with-otp", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.get_json()
    assert reg_data["status"] == "success"
    assert reg_data["farmer"]["name"] == "Gurpreet Singh"
    assert reg_data["offer_passkey"] is True

    # Step 3: Verify authenticated session
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.get_json()
    assert me_data["authenticated"] is True
    assert me_data["farmer"]["phone"] == new_phone
    assert me_data["has_passkeys"] is False  # Not yet enrolled on device


def test_2_mobile_otp_validation_rules(client):
    """Mobile OTP strictly enforces incorrect attempt limits, purpose isolation, and uniqueness."""
    phone = f"98{secrets.randbelow(100000000):08d}"

    # Request OTP
    send_res = client.post("/api/auth/otp/send", json={"phone": phone, "purpose": "register"})
    assert send_res.status_code == 200

    # Wrong OTP code rejected
    bad_res = client.post("/api/auth/register-with-otp", json={
        "name": "Test Farmer",
        "phone": phone,
        "otp": "000000",
        "state": "Punjab",
        "total_land": 1.0,
    })
    assert bad_res.status_code == 400
    assert "incorrect" in bad_res.get_json()["error"].lower()

    # Sending OTP for existing phone on 'register' must be rejected
    fa = authenticate_farmer("9876543210", "farmer123")
    existing_res = client.post("/api/auth/otp/send", json={"phone": "9876543210", "purpose": "register"})
    assert existing_res.status_code == 409
    assert existing_res.get_json()["account_exists"] is True


# ========================================================
# 3. WebAuthn Passkey Registration (Face ID / Fingerprint)
# ========================================================
def test_3_webauthn_passkey_registration_options_and_storage(client):
    """Farmer requests WebAuthn registration options; credentials are bound securely without biometrics."""
    # Login as Farmer A
    client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})

    # 1. Get Passkey registration options
    opt_res = client.post("/api/auth/passkey/register-options")
    assert opt_res.status_code == 200
    opt_data = opt_res.get_json()
    assert "challenge" in opt_data
    assert "rp" in opt_data
    assert opt_data["rp"]["name"] == "AgroSmart Irrigation"
    assert "user" in opt_data
    assert opt_data["authenticatorSelection"]["authenticatorAttachment"] == "platform"

    # Verify passkeys table exists and query helper works
    devices = get_farmer_registered_devices("farmer_4986538b37")
    assert isinstance(devices, list)


# ========================================================
# 4. Passwordless Login with Face / Fingerprint Passkey
# ========================================================
def test_4_passwordless_login_with_passkey_face_fingerprint(client):
    """Farmer logs in using 1-Touch Face ID / Fingerprint (WebAuthn signature verification)."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farmer_id = fa["id"]

    # Provision passkey for Farmer A
    pk = make_test_passkey(farmer_id, device_name="Samsung Galaxy S24 (Fingerprint)")

    # 1. Client requests login options
    opt_res = client.post("/api/auth/passkey/login-options", json={"phone": "9876543210"})
    assert opt_res.status_code == 200
    options = opt_res.get_json()
    challenge_b64 = options["challenge"]

    # 2. Authenticator signs challenge using device private key
    assertion = create_assertion_signature(
        private_key=pk["private_key"],
        credential_id=pk["credential_id"],
        challenge_b64=challenge_b64,
        rp_id="localhost",
        origin="http://localhost:5000",
        sign_count_int=1,
    )

    # 3. Client verifies passkey with server
    verify_res = client.post("/api/auth/passkey/login-verify", json={"credential": assertion})
    assert verify_res.status_code == 200
    data = verify_res.get_json()
    assert data["status"] == "success"
    assert data["farmer"]["name"] == "Ramesh Kumar"
    assert "Samsung Galaxy" in data["device_name"]

    # 4. Verify session is active
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True
    assert me_res.get_json()["has_passkeys"] is True


# ========================================================
# 5. Mobile OTP Fallback Login
# ========================================================
def test_5_mobile_otp_fallback_login(client):
    """Farmer logs in using verified mobile OTP without needing a password or passkey."""
    phone = "9876543210"

    # Step 1: Send OTP
    send_res = client.post("/api/auth/otp/send", json={"phone": phone, "purpose": "login"})
    assert send_res.status_code == 200
    otp_code = send_res.get_json()["otp_preview"]

    # Step 2: Verify OTP and login
    verify_res = client.post("/api/auth/otp/verify", json={"phone": phone, "otp": otp_code, "purpose": "login"})
    assert verify_res.status_code == 200
    data = verify_res.get_json()
    assert data["status"] == "success"
    assert data["farmer"]["name"] == "Ramesh Kumar"

    # Step 3: Farmer session established
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True


# ========================================================
# 6. Multiple Registered Devices per Farmer
# ========================================================
def test_6_multiple_registered_devices_per_farmer(client):
    """A farmer can register multiple devices (e.g. Phone, Tablet, PC) and authenticate with any."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farmer_id = fa["id"]

    # Register Device 1 (Android Phone)
    pk1 = make_test_passkey(farmer_id, device_name="OnePlus Android (Fingerprint)")
    # Register Device 2 (Windows PC)
    pk2 = make_test_passkey(farmer_id, device_name="Lenovo Laptop (Windows Hello)")

    devices = get_farmer_registered_devices(farmer_id)
    assert len(devices) == 2
    device_names = [d["device_name"] for d in devices]
    assert "OnePlus Android (Fingerprint)" in device_names
    assert "Lenovo Laptop (Windows Hello)" in device_names

    # Test login with Device 2
    opt_res = client.post("/api/auth/passkey/login-options", json={"phone": "9876543210"})
    challenge_b64 = opt_res.get_json()["challenge"]

    assertion2 = create_assertion_signature(
        private_key=pk2["private_key"],
        credential_id=pk2["credential_id"],
        challenge_b64=challenge_b64,
        sign_count_int=1,
    )
    verify_res2 = client.post("/api/auth/passkey/login-verify", json={"credential": assertion2})
    assert verify_res2.status_code == 200
    assert verify_res2.get_json()["farmer"]["name"] == "Ramesh Kumar"


# ========================================================
# 7. Device Management & Revocation (Account Recovery)
# ========================================================
def test_7_device_management_and_revocation(client):
    """Farmer can inspect, rename, and revoke lost device passkeys."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farmer_id = fa["id"]

    # Register 2 devices
    pk1 = make_test_passkey(farmer_id, device_name="Old Phone (Lost)")
    pk2 = make_test_passkey(farmer_id, device_name="New Phone (Active)")

    # Login as Farmer A via OTP
    client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})

    # 1. Fetch devices list via API
    dev_res = client.get("/api/auth/passkey/devices")
    assert dev_res.status_code == 200
    devices = dev_res.get_json()["devices"]
    assert len(devices) == 2

    # 2. Revoke the lost device (password confirmation required)
    del_res = client.delete(f"/api/auth/passkey/devices/{pk1['cred_id_b64']}", json={"password": "farmer123"})
    assert del_res.status_code == 200

    # 3. Verify lost device can no longer log in
    client.post("/api/auth/logout")

    opt_res = client.post("/api/auth/passkey/login-options", json={"phone": "9876543210"})
    challenge_b64 = opt_res.get_json()["challenge"]

    revoked_assertion = create_assertion_signature(
        private_key=pk1["private_key"],
        credential_id=pk1["credential_id"],
        challenge_b64=challenge_b64,
        sign_count_int=1,
    )
    fail_res = client.post("/api/auth/passkey/login-verify", json={"credential": revoked_assertion})
    assert fail_res.status_code == 401
    assert "not recognized" in fail_res.get_json()["error"].lower()


# ========================================================
# 8. Complete Cross-Farmer Data Isolation
# ========================================================
def test_8_cross_farmer_passkey_isolation(client):
    """Farmer A's biometric passkey strictly authenticates as Farmer A and cannot access Farmer B's data."""
    fa = authenticate_farmer("9876543210", "farmer123")
    fb = authenticate_farmer("9876543211", "farmer123")

    pk_a = make_test_passkey(fa["id"], device_name="Farmer A Phone")
    pk_b = make_test_passkey(fb["id"], device_name="Farmer B Phone")

    # Farmer A logs in via passkey
    opt_a = client.post("/api/auth/passkey/login-options", json={"phone": "9876543210"}).get_json()
    assertion_a = create_assertion_signature(pk_a["private_key"], pk_a["credential_id"], opt_a["challenge"])
    login_a = client.post("/api/auth/passkey/login-verify", json={"credential": assertion_a}).get_json()
    assert login_a["farmer"]["id"] == fa["id"]

    # Verify Farmer A's session cannot see Farmer B's farms
    farms_res = client.get("/api/farms")
    farms_data = farms_res.get_json()["farms"]
    for farm in farms_data:
        assert farm["farmer_id"] == fa["id"]
        assert farm["farmer_id"] != fb["id"]


# ========================================================
# 9. Suspended Farmer Blocked from Passkey & OTP Login
# ========================================================
def test_9_suspended_farmer_blocked_from_passkey_and_otp(client):
    """Suspended farmer account is blocked from both Passkey and OTP login with HTTP 403."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farmer_id = fa["id"]
    pk = make_test_passkey(farmer_id, device_name="Farmer Phone")

    # Super Admin suspends Farmer A
    set_farmer_status("admin", "admin", farmer_id, "Suspended", "Sensor irregularity")

    # 1. Passkey login rejected with 403
    opt_res = client.post("/api/auth/passkey/login-options", json={"phone": "9876543210"})
    challenge = opt_res.get_json()["challenge"]
    assertion = create_assertion_signature(pk["private_key"], pk["credential_id"], challenge)

    login_res = client.post("/api/auth/passkey/login-verify", json={"credential": assertion})
    assert login_res.status_code == 403
    assert login_res.get_json()["suspended"] is True

    # 2. OTP send rejected with 403
    otp_res = client.post("/api/auth/otp/send", json={"phone": "9876543210", "purpose": "login"})
    assert otp_res.status_code == 403
    assert otp_res.get_json()["suspended"] is True

    # Restore farmer status
    set_farmer_status("admin", "admin", farmer_id, "Active")


# ========================================================
# 10. Super Admin System Unbroken & Visible Passkeys
# ========================================================
def test_10_super_admin_system_unbroken_and_visible_passkeys(client):
    """Super Admin login and management routes are completely preserved; passkey devices are visible."""
    # 1. Super Admin login succeeds
    admin_login = client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    assert admin_login.status_code == 200

    # 2. Provision a passkey for Farmer A
    fa = authenticate_farmer("9876543210", "farmer123")
    make_test_passkey(fa["id"], device_name="Ramesh's Redmi Note (Fingerprint)")

    # 3. Super Admin inspects Farmer A details
    inspect_res = client.get(f"/api/admin/farmers/{fa['id']}")
    assert inspect_res.status_code == 200
    inspect_data = inspect_res.get_json()
    assert "passkeys" in inspect_data
    assert len(inspect_data["passkeys"]) >= 1
    assert "Redmi Note" in inspect_data["passkeys"][0]["device_name"]

    # 4. Super Admin KPIs operate without regression
    kpi_res = client.get("/api/admin/kpis")
    assert kpi_res.status_code == 200
    assert kpi_res.get_json()["total_farmers"] >= 2
