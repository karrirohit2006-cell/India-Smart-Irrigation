"""
Automated Verification Suite for Admin Panel: Registered Farmers Management.
Tests all requirements from the Antigravity Prompt:
1. Log in as admin.
2. Check that the farmer count matches the actual database.
3. Register a new farmer using Create Account.
4. Log in again as admin.
5. Confirm that the new farmer appears in the Registered Farmers table.
6. Confirm that the total count increases by exactly one.
7. Open the farmer's details and verify the actual registration information.
8. Confirm that admin accounts are excluded from the registered farmers list and count.
9. Confirm that duplicate farmer records are not displayed.
10. Log in as a normal farmer and verify that the admin panel and registered farmer information are inaccessible (401/403/redirect).
"""

import uuid
import pytest
from app import app
from src.farm_manager import (
    init_farm_db,
    seed_demo_accounts,
    authenticate_farmer,
)
from src.admin_manager import (
    init_admin_db,
    bootstrap_super_admin,
    get_db_connection,
)


@pytest.fixture(autouse=True)
def setup_databases():
    """Ensure multi-farmer and super admin tables are cleanly seeded before each test."""
    init_farm_db()
    seed_demo_accounts()
    init_admin_db()
    bootstrap_super_admin()
    
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE admins SET failed_login_attempts = 0, locked_until = NULL WHERE username IN ('admin', 'kamal');")
            conn.execute("UPDATE farmers SET status = 'Active', suspended_at = NULL, suspend_reason = NULL;")
    finally:
        conn.close()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_1_admin_login_and_accurate_farmer_count_matches_database(client):
    """Admin logs in and Total Registered Farmers counter strictly matches actual database records."""
    # 1. Direct database count of registered farmers
    conn = get_db_connection()
    try:
        registered_filter = """
            f.username IS NOT NULL AND TRIM(f.username) != ''
            AND f.password_hash IS NOT NULL AND TRIM(f.password_hash) != ''
            AND LOWER(TRIM(f.username)) NOT IN (SELECT LOWER(TRIM(username)) FROM admins WHERE username IS NOT NULL)
            AND f.id NOT IN (SELECT id FROM admins)
        """
        expected_total = conn.execute(f"SELECT COUNT(DISTINCT f.id) FROM farmers f WHERE {registered_filter};").fetchone()[0]
        expected_active = conn.execute(f"SELECT COUNT(DISTINCT f.id) FROM farmers f WHERE {registered_filter} AND (f.status IS NULL OR f.status = 'Active');").fetchone()[0]
        expected_suspended = conn.execute(f"SELECT COUNT(DISTINCT f.id) FROM farmers f WHERE {registered_filter} AND f.status = 'Suspended';").fetchone()[0]
    finally:
        conn.close()

    # 2. Login as admin
    login_res = client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})
    assert login_res.status_code == 200, f"Admin login failed: {login_res.get_json()}"

    # 3. Check /api/admin/kpis
    kpi_res = client.get("/api/admin/kpis")
    assert kpi_res.status_code == 200
    kpis = kpi_res.get_json()
    assert kpis["total_farmers"] == expected_total
    assert kpis["active_farmers"] == expected_active
    assert kpis["suspended_farmers"] == expected_suspended


def test_2_and_3_register_new_farmer_increases_count_and_appears_in_table(client):
    """Registering a new farmer increases Total Registered Farmers by exactly one and appears in table."""
    # 1. Login as admin to get initial count
    login_res = client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})
    assert login_res.status_code == 200
    initial_kpis = client.get("/api/admin/kpis").get_json()
    initial_count = initial_kpis["total_farmers"]
    client.post("/api/admin/auth/logout")

    # 2. Register a new farmer using the public Create Account endpoint (/api/auth/register)
    unique_suffix = uuid.uuid4().hex[:6]
    new_username = f"farmer_{unique_suffix}"
    new_name = f"Rajesh Test {unique_suffix}"
    new_phone = f"987{unique_suffix[:7]}"
    new_email = f"rajesh_{unique_suffix}@krishi.in"
    new_password = "SecurePassword@2026"

    reg_res = client.post("/api/auth/register", json={
        "username": new_username,
        "password": new_password,
        "confirm_password": new_password,
        "name": new_name,
        "phone": new_phone,
        "email": new_email,
    })
    assert reg_res.status_code == 201, f"Registration failed: {reg_res.get_json()}"
    reg_data = reg_res.get_json()
    new_farmer_id = reg_data["farmer"]["id"]

    # 3. Log back in as admin
    login_again = client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})
    assert login_again.status_code == 200

    # 4. Check total count increased by exactly one
    updated_kpis = client.get("/api/admin/kpis").get_json()
    assert updated_kpis["total_farmers"] == initial_count + 1

    # 5. Check that the new farmer appears in the Registered Farmers table (/api/admin/farmers)
    farmers_res = client.get("/api/admin/farmers")
    assert farmers_res.status_code == 200
    farmers_list = farmers_res.get_json()
    matching = [f for f in farmers_list if f["id"] == new_farmer_id]
    assert len(matching) == 1, f"New farmer {new_farmer_id} not found in farmers list"
    
    farmer_entry = matching[0]
    assert farmer_entry["name"] == new_name
    assert farmer_entry["username"] == new_username
    assert farmer_entry["email"] == new_email
    assert farmer_entry["phone"] == new_phone
    assert farmer_entry["status"] == "Active"
    assert "password_hash" not in farmer_entry, "password_hash must never be exposed in farmers table"


def test_4_farmer_details_endpoint_returns_actual_registration_and_profile_info(client):
    """Inspecting a farmer returns registered account information and profile details without sensitive credentials."""
    # 1. Login as admin
    client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})

    # 2. Create farmer account
    unique_suffix = uuid.uuid4().hex[:6]
    new_username = f"profile_{unique_suffix}"
    reg_res = client.post("/api/auth/register", json={
        "username": new_username,
        "password": "Password123!",
        "confirm_password": "Password123!",
        "name": f"Surinder Kaur {unique_suffix}",
        "phone": f"982{unique_suffix[:7]}",
        "email": f"surinder_{unique_suffix}@krishi.in",
    })
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # 3. Fetch farmer details via admin endpoint
    client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})
    detail_res = client.get(f"/api/admin/farmers/{farmer_id}")
    assert detail_res.status_code == 200
    details = detail_res.get_json()

    # Verify registered account fields
    farmer_info = details["farmer"]
    assert farmer_info["id"] == farmer_id
    assert farmer_info["username"] == new_username
    assert farmer_info["name"] == f"Surinder Kaur {unique_suffix}"
    assert farmer_info["email"] == f"surinder_{unique_suffix}@krishi.in"
    assert farmer_info["status"] == "Active"
    assert "created_at" in farmer_info

    # Verify sensitive fields are NEVER leaked
    assert "password_hash" not in farmer_info
    assert "password" not in farmer_info

    # Verify separate profile sections exist
    assert "farms" in details
    assert "sections" in details
    assert "schedules" in details


def test_5_admin_accounts_are_strictly_excluded_from_registered_farmers(client):
    """Admin accounts (kamal, admin) are never returned in registered farmers list or count."""
    client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})

    # Check farmers list
    farmers_res = client.get("/api/admin/farmers")
    assert farmers_res.status_code == 200
    farmers = farmers_res.get_json()

    admin_usernames = {"kamal", "admin"}
    for f in farmers:
        assert (f.get("username") or "").lower() not in admin_usernames, f"Admin account {f.get('username')} found in registered farmers list!"

    # Trying to inspect an admin account as a farmer returns 404
    conn = get_db_connection()
    admin_id = conn.execute("SELECT id FROM admins WHERE username = 'kamal';").fetchone()[0]
    conn.close()

    admin_inspect_res = client.get(f"/api/admin/farmers/{admin_id}")
    assert admin_inspect_res.status_code == 404, "Admin account should not be accessible as a farmer"


def test_6_duplicate_farmer_records_are_not_displayed(client):
    """Each farmer record appears only once; no duplicates exist in the registered farmers table."""
    client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})

    farmers_res = client.get("/api/admin/farmers")
    assert farmers_res.status_code == 200
    farmers = farmers_res.get_json()

    farmer_ids = [f["id"] for f in farmers]
    usernames = [f["username"] for f in farmers if f.get("username")]

    assert len(farmer_ids) == len(set(farmer_ids)), "Duplicate farmer IDs found in registered farmers table"
    assert len(usernames) == len(set(usernames)), "Duplicate usernames found in registered farmers table"


def test_7_normal_farmer_cannot_access_admin_panel_or_registered_farmers_api(client):
    """A regular logged-in farmer cannot access /admin (redirects) or /api/admin/* (HTTP 403)."""
    # 1. Login as normal farmer
    fa = authenticate_farmer("9876543210", "farmer123")
    assert fa is not None

    with client.session_transaction() as sess:
        sess["farmer_id"] = fa["id"]
        sess["farmer_name"] = fa["name"]
        sess["is_admin"] = False
        sess.pop("admin_id", None)

    # 2. Accessing /admin page redirects away from admin
    page_res = client.get("/admin", follow_redirects=False)
    assert page_res.status_code == 302
    assert "/admin/login" in page_res.headers.get("Location", "")

    # 3. Accessing /api/admin/kpis returns 403
    kpi_res = client.get("/api/admin/kpis")
    assert kpi_res.status_code == 403

    # 4. Accessing /api/admin/farmers returns 403
    farmers_res = client.get("/api/admin/farmers")
    assert farmers_res.status_code == 403

    # 5. Accessing a specific farmer detail returns 403
    detail_res = client.get(f"/api/admin/farmers/{fa['id']}")
    assert detail_res.status_code == 403


def test_8_unauthenticated_visitor_cannot_access_admin_panel_or_apis(client):
    """Unauthenticated visitor is rejected from /api/admin/* (HTTP 401) and redirected from /admin."""
    # Web page redirects to login
    page_res = client.get("/admin", follow_redirects=False)
    assert page_res.status_code == 302
    assert "/admin/login" in page_res.headers.get("Location", "")

    # APIs return 401 Unauthorized
    assert client.get("/api/admin/kpis").status_code == 401
    assert client.get("/api/admin/farmers").status_code == 401
    assert client.get("/api/admin/farmers/farmer_random").status_code == 401


def test_9_admin_can_edit_and_delete_farmer_account(client):
    """Admin can edit farmer profile details and permanently delete the farmer account."""
    client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})

    # 1. Register a test farmer
    unique_suffix = uuid.uuid4().hex[:6]
    username = f"crud_{unique_suffix}"
    reg_res = client.post("/api/auth/register", json={
        "username": username,
        "password": "Password123!",
        "name": f"Original Name {unique_suffix}",
        "phone": f"989{unique_suffix[:7]}",
        "email": f"orig_{unique_suffix}@krishi.in",
    })
    assert reg_res.status_code == 201
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # Re-login admin
    client.post("/api/admin/auth/login", json={"username": "kamal", "password": "kamal@2007"})
    initial_count = client.get("/api/admin/kpis").get_json()["total_farmers"]

    # 2. Edit farmer profile via PUT /api/admin/farmers/<id>
    edit_res = client.put(f"/api/admin/farmers/{farmer_id}", json={
        "name": f"Updated Name {unique_suffix}",
        "phone": f"989{unique_suffix[:7]}",
        "email": f"updated_{unique_suffix}@krishi.in",
        "state": "Haryana",
        "district": "Karnal",
        "village": "Taraori",
    })
    assert edit_res.status_code == 200

    # Verify changes
    detail_res = client.get(f"/api/admin/farmers/{farmer_id}")
    assert detail_res.status_code == 200
    f_data = detail_res.get_json()["farmer"]
    assert f_data["name"] == f"Updated Name {unique_suffix}"
    assert f_data["email"] == f"updated_{unique_suffix}@krishi.in"
    assert f_data["state"] == "Haryana"

    # 3. Delete farmer via DELETE /api/admin/farmers/<id>
    del_res = client.delete(f"/api/admin/farmers/{farmer_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # 4. Verify farmer is deleted and count decrements by 1
    after_del_kpis = client.get("/api/admin/kpis").get_json()
    assert after_del_kpis["total_farmers"] == initial_count - 1

    # Fetching deleted farmer returns 404
    assert client.get(f"/api/admin/farmers/{farmer_id}").status_code == 404
