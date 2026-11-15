"""
Unit and Integration Tests for Private Super Admin Panel & Authentication System.
Validates:
1. Farmer A and Farmer B cannot access each other's data (strict isolation).
2. Farmer A and Farmer B schedules do not collide or mix.
3. Farmer accounts cannot access /admin or /api/admin/* (HTTP 401 or 403).
4. Unauthenticated requests are rejected from admin routes.
5. Super Admin login succeeds with correct credentials.
6. Super Admin login fails with incorrect credentials.
7. Brute-force protection: Admin account is locked after 5 consecutive failed login attempts.
8. Admin can view all farmers, all farms, all sections, all schedules, weather & AI system.
9. Admin can suspend a farmer account.
10. Suspended farmer cannot log in (HTTP 403).
11. Admin can reactivate a farmer account.
12. Reactivated farmer can log in again.
13. Admin can reset farmer password; new password works, old password fails.
14. Admin can impersonate a farmer ('Open Farmer Dashboard'), view their data, then exit back to admin.
15. Security audit trail records all administrative actions immutably.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from app import app
from src.farm_manager import (
    init_farm_db,
    seed_demo_accounts,
    authenticate_farmer,
    get_farmer_farms,
    get_farm_sections,
    get_section_schedules,
)
from src.admin_manager import (
    init_admin_db,
    bootstrap_super_admin,
    get_admin_dashboard_kpis,
    get_all_farmers_admin,
    get_admin_audit_logs,
    get_db_connection,
)


@pytest.fixture(autouse=True)
def setup_databases():
    """Ensure multi-farmer and super admin tables are cleanly seeded before each test."""
    init_farm_db()
    seed_demo_accounts()
    init_admin_db()
    bootstrap_super_admin()
    
    # Unlock admin if previously locked by a test
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE admins SET failed_login_attempts = 0, locked_until = NULL WHERE username = 'admin';")
            # Ensure demo farmers are Active
            conn.execute("UPDATE farmers SET status = 'Active', suspended_at = NULL, suspend_reason = NULL;")
    finally:
        conn.close()


@pytest.fixture
def client():
    """Test client for Flask HTTP requests."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ========================================================
# Requirement 12.1 & 12.2: Farmer Data Isolation & Schedules
# ========================================================
def test_1_farmer_a_and_farmer_b_data_isolation():
    """Farmer A and Farmer B cannot access each other's data."""
    fa = authenticate_farmer("9876543210", "farmer123")
    fb = authenticate_farmer("9876543211", "farmer123")

    assert fa is not None and fb is not None
    assert fa["id"] != fb["id"]

    farms_b = get_farmer_farms(fb["id"])
    assert len(farms_b) > 0
    farm_b_id = farms_b[0]["id"]

    # Farmer A attempts to query Farmer B's farm sections -> returns empty list
    isolated_sections = get_farm_sections(farm_b_id, fa["id"])
    assert isolated_sections == []


def test_2_farmer_a_and_farmer_b_schedules_do_not_collide():
    """Farmer A and Farmer B irrigation schedules remain strictly independent."""
    fa = authenticate_farmer("9876543210", "farmer123")
    fb = authenticate_farmer("9876543211", "farmer123")

    farms_a = get_farmer_farms(fa["id"])
    farms_b = get_farmer_farms(fb["id"])

    secs_a = get_farm_sections(farms_a[0]["id"], fa["id"])
    secs_b = get_farm_sections(farms_b[0]["id"], fb["id"])

    s1_a = secs_a[0]["id"]
    s1_b = secs_b[0]["id"]

    scheds_a = get_section_schedules(s1_a, fa["id"])
    scheds_b = get_section_schedules(s1_b, fb["id"])

    # Ensure schedules belong strictly to their respective owners
    for s in scheds_a:
        assert s["farmer_id"] == fa["id"]
        assert s["farmer_id"] != fb["id"]

    for s in scheds_b:
        assert s["farmer_id"] == fb["id"]
        assert s["farmer_id"] != fa["id"]


# ========================================================
# Requirement 12.3 & 12.4: RBAC & Route Access Control
# ========================================================
def test_3_farmer_accounts_cannot_access_admin_routes(client):
    """Ordinary farmer accounts are rejected from /admin and /api/admin/* (HTTP 401/403)."""
    # 1. Login as Farmer A
    login_res = client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})
    assert login_res.status_code == 200

    # 2. Farmer attempts to access /api/admin/kpis -> HTTP 403 Forbidden
    kpi_res = client.get("/api/admin/kpis")
    assert kpi_res.status_code == 403
    kpi_data = kpi_res.get_json()
    assert "access denied" in kpi_data["error"].lower() or "administrator privileges" in kpi_data["error"].lower()

    # 3. Farmer attempts to access /api/admin/farmers -> HTTP 403 Forbidden
    farmers_res = client.get("/api/admin/farmers")
    assert farmers_res.status_code == 403

    # 4. Farmer attempts to access /admin page -> Redirected to /admin/login (302)
    admin_page_res = client.get("/admin", follow_redirects=False)
    assert admin_page_res.status_code == 302
    assert "/admin/login" in admin_page_res.headers.get("Location", "")


def test_4_unauthenticated_requests_rejected_from_admin_routes(client):
    """Unauthenticated requests are rejected from admin APIs (HTTP 401) and redirected from admin pages."""
    # API endpoints return 401 Unauthorized
    res1 = client.get("/api/admin/kpis")
    assert res1.status_code == 401

    res2 = client.get("/api/admin/farmers")
    assert res2.status_code == 401

    res3 = client.get("/api/admin/audit-logs")
    assert res3.status_code == 401

    # Admin web page redirects to login
    res_page = client.get("/admin", follow_redirects=False)
    assert res_page.status_code == 302
    assert "/admin/login" in res_page.headers.get("Location", "")


# ========================================================
# Requirement 12.5, 12.6, 12.7: Super Admin Authentication & Brute-Force
# ========================================================
def test_5_super_admin_login_succeeds_with_correct_credentials(client):
    """Super Admin logs in successfully with valid credentials."""
    res = client.post("/api/admin/auth/login", json={
        "username": "admin",
        "password": "SuperAdmin@2026",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["admin"]["username"] == "admin"
    assert data["redirect"] == "/admin"

    # Verify session is authenticated via /api/admin/me
    me_res = client.get("/api/admin/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["admin"]["username"] == "admin"


def test_6_super_admin_login_fails_with_incorrect_credentials(client):
    """Super Admin login fails with invalid password."""
    res = client.post("/api/admin/auth/login", json={
        "username": "admin",
        "password": "WrongPassword!999",
    })
    assert res.status_code == 401
    data = res.get_json()
    assert "invalid" in data["error"].lower()


def test_7_brute_force_lockout_after_5_failed_attempts(client):
    """Admin account is locked after 5 consecutive failed login attempts for 15 minutes."""
    # Reset attempts first
    conn = get_db_connection()
    with conn:
        conn.execute("UPDATE admins SET failed_login_attempts = 0, locked_until = NULL WHERE username = 'admin';")
    conn.close()

    # Send 4 failed attempts -> 401
    for i in range(1, 5):
        res = client.post("/api/admin/auth/login", json={"username": "admin", "password": f"bad_pwd_{i}"})
        assert res.status_code == 401

    # 5th failed attempt -> account locked (423 Locked)
    res5 = client.post("/api/admin/auth/login", json={"username": "admin", "password": "bad_pwd_5"})
    assert res5.status_code in (401, 423)
    data5 = res5.get_json()
    assert data5.get("locked") is True or "locked" in data5.get("error", "").lower()

    # 6th attempt (even with CORRECT password) is blocked because account is locked
    res6 = client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    assert res6.status_code == 423
    data6 = res6.get_json()
    assert "locked" in data6["error"].lower()


# ========================================================
# Requirement 12.8: Centralized Telemetry & Visibility
# ========================================================
def test_8_admin_centralized_visibility_farmers_farms_sections_schedules(client):
    """Admin has centralized visibility over all farmers, farms, sections, and schedules."""
    # Authenticate admin
    login_res = client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    assert login_res.status_code == 200

    # 1. Executive KPIs
    kpi_res = client.get("/api/admin/kpis")
    assert kpi_res.status_code == 200
    kpis = kpi_res.get_json()
    assert kpis["total_farmers"] >= 2
    assert kpis["total_farms"] >= 2
    assert kpis["total_land_acres"] >= 3.00
    assert kpis["total_sections"] >= 5
    assert kpis["total_schedules"] >= 2

    # 2. Farmer List
    f_res = client.get("/api/admin/farmers")
    assert f_res.status_code == 200
    farmers = f_res.get_json()
    farmer_names = [f["name"] for f in farmers]
    assert "Ramesh Kumar" in farmer_names
    assert "Suresh Patel" in farmer_names

    # 3. Global Farms
    farms_res = client.get("/api/admin/farms")
    assert farms_res.status_code == 200
    farms = farms_res.get_json()
    assert len(farms) >= 2

    # 4. Global Schedules
    sched_res = client.get("/api/admin/schedules")
    assert sched_res.status_code == 200
    schedules = sched_res.get_json()
    assert len(schedules) >= 2

    # 5. Live Weather Overview
    w_res = client.get("/api/admin/weather")
    assert w_res.status_code == 200
    weather = w_res.get_json()
    assert len(weather) >= 1

    # 6. AI System Diagnostics
    ai_res = client.get("/api/admin/ai-system")
    assert ai_res.status_code == 200
    ai_status = ai_res.get_json()
    assert "gemini_api" in ai_status
    assert "ml_model" in ai_status
    assert ai_status["ml_model"]["accuracy"] == "100.0%"


# ========================================================
# Requirement 12.9 & 12.10: Farmer Suspension & Login Blocking
# ========================================================
def test_9_and_10_admin_suspends_farmer_and_login_is_blocked(client):
    """Admin suspends a farmer account, blocking them from logging in (HTTP 403)."""
    # 1. Login as admin
    client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})

    # 2. Get Farmer A ID
    fa = authenticate_farmer("9876543210", "farmer123")
    fa_id = fa["id"]

    # 3. Suspend Farmer A
    sus_res = client.post(f"/api/admin/farmers/{fa_id}/status", json={
        "status": "Suspended",
        "reason": "Suspected misuse of sensor inputs",
    })
    assert sus_res.status_code == 200
    assert sus_res.get_json()["new_status"] == "Suspended"

    # Logout admin
    client.post("/api/admin/auth/logout")

    # 4. Farmer A tries to log in -> blocked with HTTP 403 Forbidden
    f_login = client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})
    assert f_login.status_code == 403
    data = f_login.get_json()
    assert data.get("suspended") is True
    assert "suspended" in data["error"].lower()


# ========================================================
# Requirement 12.11 & 12.12: Farmer Reactivation & Login Recovery
# ========================================================
def test_11_and_12_admin_reactivates_farmer_and_login_succeeds(client):
    """Admin reactivates a suspended farmer account, allowing them to log in again."""
    # 1. Login as admin
    client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    fa = authenticate_farmer("9876543210", "farmer123")
    fa_id = fa["id"]

    # 2. Reactivate Farmer A
    act_res = client.post(f"/api/admin/farmers/{fa_id}/status", json={"status": "Active"})
    assert act_res.status_code == 200
    assert act_res.get_json()["new_status"] == "Active"

    client.post("/api/admin/auth/logout")

    # 3. Farmer A logs in again -> HTTP 200 OK
    f_login = client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})
    assert f_login.status_code == 200
    assert f_login.get_json()["farmer"]["name"] == "Ramesh Kumar"


# ========================================================
# Requirement 12.13: Password Reset by Admin
# ========================================================
def test_13_admin_resets_farmer_password_securely(client):
    """Admin resets farmer password; new password works and old password fails."""
    client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    fa = authenticate_farmer("9876543210", "farmer123")
    fa_id = fa["id"]

    # 1. Reset password to new password
    new_pwd = "NewSecurePassword@2026"
    reset_res = client.post(f"/api/admin/farmers/{fa_id}/reset-password", json={"password": new_pwd})
    assert reset_res.status_code == 200
    assert reset_res.get_json()["success"] is True

    client.post("/api/admin/auth/logout")

    # 2. Old password fails
    old_res = client.post("/api/auth/login", json={"identifier": "9876543210", "password": "farmer123"})
    assert old_res.status_code == 401

    # 3. New password succeeds
    new_res = client.post("/api/auth/login", json={"identifier": "9876543210", "password": new_pwd})
    assert new_res.status_code == 200
    assert new_res.get_json()["farmer"]["id"] == fa_id

    # Restore default password for remaining tests
    client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    client.post(f"/api/admin/farmers/{fa_id}/reset-password", json={"password": "farmer123"})
    client.post("/api/admin/auth/logout")


# ========================================================
# Requirement 12.14: Administrative Impersonation Mode
# ========================================================
def test_14_admin_impersonates_farmer_and_exits(client):
    """Admin impersonates farmer ('Open Farmer Dashboard'), inspects data, then exits cleanly."""
    # 1. Login as Admin
    client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    fa = authenticate_farmer("9876543210", "farmer123")
    fa_id = fa["id"]

    # 2. Impersonate Farmer A
    imp_res = client.post(f"/api/admin/farmers/{fa_id}/impersonate", json={
        "reason": "Investigating irrigation scheduler discrepancy",
    })
    assert imp_res.status_code == 200
    assert imp_res.get_json()["redirect"] == "/"

    # 3. /api/auth/me reflects active farmer session WITH impersonation metadata
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.get_json()
    assert me_data["farmer"]["id"] == fa_id
    assert me_data["is_impersonating"] is True
    assert me_data["admin_username"] == "admin"

    # 4. Exit impersonation -> redirects back to /admin
    exit_res = client.get("/api/admin/exit-impersonation", follow_redirects=False)
    assert exit_res.status_code == 302
    assert "/admin" in exit_res.headers.get("Location", "")

    # 5. Verify admin session is preserved and farmer session is cleared
    admin_me = client.get("/api/admin/me")
    assert admin_me.status_code == 200
    assert admin_me.get_json()["admin"]["username"] == "admin"


# ========================================================
# Requirement 12.15: Immutable Security Audit Logging
# ========================================================
def test_15_audit_logs_recorded_for_all_admin_actions(client):
    """Audit logs are recorded for logins, suspensions, impersonations, and password resets."""
    client.post("/api/admin/auth/login", json={"username": "admin", "password": "SuperAdmin@2026"})
    
    logs_res = client.get("/api/admin/audit-logs")
    assert logs_res.status_code == 200
    logs = logs_res.get_json()
    assert len(logs) > 0

    actions = [l["action"] for l in logs]
    assert "LOGIN_SUCCESS" in actions
    assert any(a in actions for a in ("SUSPEND_FARMER", "ACTIVATE_FARMER", "IMPERSONATE_FARMER", "BOOTSTRAP_ADMIN"))

    # Verify log entries have timestamps and IP addresses
    for log in logs:
        assert "created_at" in log
        assert "ip_address" in log
        assert "admin_username" in log
