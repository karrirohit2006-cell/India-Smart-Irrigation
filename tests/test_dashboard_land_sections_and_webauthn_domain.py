"""
Tests for:
1. WebAuthn Domain Error Fix:
   - RP_ID configured as 'localhost' without port for local development.
   - Expected origin configured as 'http://localhost:5000'.
   - 127.0.0.1 normalized to localhost.
   - Production domains supported via WEBAUTHN_RP_ID and WEBAUTHN_ORIGIN.
   - Zero biometric templates or facial photographs uploaded or stored.
2. 4-Step Onboarding Wizard:
   - 1. Farmer Name, 2. Farm Location, 3. Total Land, 4. Review & Save.
   - No land sections required during onboarding.
   - Marks onboarding_completed = 1 and redirects to /dashboard.
3. Dashboard Land Sections CRUD:
   - Add Section (asks ONLY for Name, Plot Area, Crop Type).
   - Edit Section.
   - Remove / Delete Section.
   - View All Sections.
   - Uses existing farm total land and location automatically.
4. Database Persistence & Isolation:
   - Saved in SQLite data/irrigation_schedules.db with farmer_id, farm_id, section_id.
   - Survives logout/login and page reloads.
   - Strict cross-farmer isolation.
5. Land Validation & Unit Conversions:
   - Allocated + Available land balance.
   - Enforces total area constraint.
   - Supports Acres, Hectares, Bighas, Gunthas.
   - Empty sections bypass irrigation scheduling.
"""

import os
import json
import secrets
import pytest
from app import app
from src.passkey_manager import get_rp_id_and_origins, get_db_connection
from src.farm_manager import (
    get_farmer_by_id,
    get_farmer_farms,
    get_farm_sections,
    get_section_by_id,
    get_land_summary,
    create_section,
    update_section,
    delete_section,
    update_farmer_onboarding,
    LAND_UNIT_TO_ACRES,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess.clear()
        yield c


# ========================================================
# PART 1: WebAuthn Domain Error Fix & Standardized Localhost
# ========================================================
def test_webauthn_rp_id_standardized_to_localhost_without_port():
    """RP_ID must be 'localhost' without port and not an IP address like 127.0.0.1."""
    # When request comes from 127.0.0.1:5000
    rp_id, allowed_origins = get_rp_id_and_origins(request_host="127.0.0.1:5000", request_origin="http://127.0.0.1:5000")
    assert rp_id == "localhost", "RP_ID must be 'localhost' for local development, never 127.0.0.1"
    assert ":" not in rp_id, "RP_ID must never contain a port number"
    assert "http://localhost:5000" in allowed_origins

    # When request comes from localhost:5000
    rp_id2, origins2 = get_rp_id_and_origins(request_host="localhost:5000", request_origin="http://localhost:5000")
    assert rp_id2 == "localhost"
    assert "http://localhost:5000" in origins2


def test_webauthn_production_domain_env_override(monkeypatch):
    """Production domains and origins can be configured via environment variables."""
    monkeypatch.setenv("WEBAUTHN_RP_ID", "smartirrigation.in")
    monkeypatch.setenv("WEBAUTHN_ORIGIN", "https://smartirrigation.in")

    rp_id, origins = get_rp_id_and_origins(request_host="smartirrigation.in:443", request_origin="https://smartirrigation.in")
    assert rp_id == "smartirrigation.in"
    assert "https://smartirrigation.in" in origins


def test_no_facial_images_or_biometric_templates_stored():
    """System must never store camera captures, face photos, or biometric templates."""
    conn = get_db_connection()
    try:
        # Check table columns in farmer_passkeys
        cols = [c["name"].lower() for c in conn.execute("PRAGMA table_info(farmer_passkeys);").fetchall()]
        forbidden = ["face_image", "photo", "biometric_template", "camera", "image_data", "fingerprint_image"]
        for f in forbidden:
            assert f not in cols, f"Forbidden column '{f}' found in farmer_passkeys table!"
    finally:
        conn.close()


# ========================================================
# PART 2: 4-Step Onboarding Flow (No Sections Required)
# ========================================================
def test_4_step_onboarding_wizard_without_land_sections(client):
    """
    Onboarding contains exactly 4 steps: Name, Location, Total Land, Review & Save.
    Farmer can complete onboarding with 0 sections and enters dashboard immediately.
    """
    unique_user = f"farmer_{secrets.token_hex(4)}"
    reg_res = client.post("/api/auth/register", json={
        "username": unique_user,
        "password": "FarmerPassword123",
        "confirm_password": "FarmerPassword123",
    })
    assert reg_res.status_code == 201
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # Verify initial state: onboarding not completed
    f_initial = get_farmer_by_id(farmer_id)
    assert not f_initial["onboarding_completed"]

    # Post 4-Step Onboarding payload (Zero sections created during onboarding)
    onboard_payload = {
        "name": "Paramjit Singh",
        "state": "Punjab",
        "district": "Ludhiana",
        "village": "Jagraon",
        "latitude": 30.7800,
        "longitude": 75.4800,
        "total_land": 5.00,
        "unit": "Acres",
        "sections": [],  # No land sections required!
    }

    ob_res = client.post("/api/farmer/onboarding", json=onboard_payload)
    assert ob_res.status_code == 200
    ob_data = ob_res.get_json()
    assert ob_data["status"] == "success"
    assert ob_data["redirect"] == "/dashboard"

    # Verify farmer profile updated and onboarding completed
    f_updated = get_farmer_by_id(farmer_id)
    assert f_updated["onboarding_completed"] is True
    assert f_updated["name"] == "Paramjit Singh"
    assert f_updated["state"] == "Punjab"
    assert f_updated["district"] == "Ludhiana"

    # Verify farm created with full 5.00 acres available
    farms = get_farmer_farms(farmer_id)
    assert len(farms) == 1
    farm_id = farms[0]["id"]
    assert farms[0]["total_area_acres"] == 5.00

    sections = get_farm_sections(farm_id, farmer_id)
    assert len(sections) == 0, "No sections should exist right after 4-step onboarding"

    # Verify dashboard now opens (status 200, no redirect back to /onboarding)
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200


# ========================================================
# PART 3: Move Land Sections into Farmer Dashboard (CRUD)
# ========================================================
def test_dashboard_section_management_crud(client):
    """
    Farmer can Add, Edit, Remove, and View sections from Dashboard -> My Farms -> Land Sections.
    When adding/editing, asks ONLY for: Section Name, Plot Area, Crop Type.
    Uses existing farm total land and location automatically.
    """
    unique_user = f"crud_farmer_{secrets.token_hex(4)}"
    reg_res = client.post("/api/auth/register", json={
        "username": unique_user,
        "password": "Password123",
        "confirm_password": "Password123",
    })
    farmer_id = reg_res.get_json()["farmer"]["id"]

    # Complete 4-step onboarding with 4.00 acres
    client.post("/api/farmer/onboarding", json={
        "name": "Balwinder Kaur",
        "state": "Punjab",
        "district": "Amritsar",
        "village": "Majitha",
        "total_land": 4.00,
        "unit": "Acres",
        "sections": [],
    })

    farms = get_farmer_farms(farmer_id)
    farm_id = farms[0]["id"]

    # 1. Add Land Section 1: asks only for Name, Area, Crop Type
    sec1_res = client.post(f"/api/farms/{farm_id}/sections", json={
        "name": "North Field",
        "area_acres": 2.00,
        "crop": "Wheat",
        "is_empty": False,
    })
    assert sec1_res.status_code == 201
    sec1_data = sec1_res.get_json()["section"]
    sec1_id = sec1_data["id"]
    assert sec1_data["name"] == "North Field"
    assert sec1_data["area_acres"] == 2.00
    assert sec1_data["crop"] == "Wheat"
    assert sec1_data["farmer_id"] == farmer_id
    assert sec1_data["farm_id"] == farm_id

    # 2. Add Land Section 2: Empty / Uncultivated plot
    sec2_res = client.post(f"/api/farms/{farm_id}/sections", json={
        "name": "East Fallow Plot",
        "area_acres": 1.50,
        "crop": "Empty",
        "is_empty": True,
    })
    assert sec2_res.status_code == 201
    sec2_data = sec2_res.get_json()["section"]
    sec2_id = sec2_data["id"]
    assert sec2_data["is_empty"] == 1

    # 3. View All Land Sections via GET
    list_res = client.get(f"/api/farms/{farm_id}/sections")
    assert list_res.status_code == 200
    sections = list_res.get_json()["sections"]
    assert len(sections) == 2
    sec_names = [s["name"] for s in sections]
    assert "North Field" in sec_names
    assert "East Fallow Plot" in sec_names

    # Check land summary
    summary = list_res.get_json()["summary"]
    assert summary["total_land"] == 4.00
    assert summary["allocated_land"] == 2.00  # only cultivated counts as active
    assert summary["available_land"] == 2.00   # 1.5 empty + 0.5 unassigned

    # 4. Edit Land Section 1: rename and change crop to Potato
    edit_res = client.put(f"/api/sections/{sec1_id}", json={
        "name": "North Potato Field",
        "area_acres": 2.20,
        "crop": "Potato",
        "is_empty": False,
    })
    assert edit_res.status_code == 200
    updated_sec1 = get_section_by_id(sec1_id, farmer_id)
    assert updated_sec1["name"] == "North Potato Field"
    assert updated_sec1["crop"] == "Potato"
    assert updated_sec1["area_acres"] == 2.20

    # 5. Remove / Delete Section 2
    del_res = client.delete(f"/api/sections/{sec2_id}")
    assert del_res.status_code == 200

    # Verify Section 2 deleted
    assert get_section_by_id(sec2_id, farmer_id) is None
    remaining = get_farm_sections(farm_id, farmer_id)
    assert len(remaining) == 1
    assert remaining[0]["id"] == sec1_id


# ========================================================
# PART 4: Persistence in Database & Cross-Farmer Isolation
# ========================================================
def test_sections_persist_across_sessions_and_cross_farmer_isolation(client):
    """
    Sections persist across page reloads and logout/login.
    Strict isolation: Farmer A cannot view, edit, or delete Farmer B's sections.
    """
    # Create Farmer A
    user_a = f"farmer_a_{secrets.token_hex(4)}"
    client.post("/api/auth/register", json={
        "username": user_a,
        "password": "PasswordA123",
        "confirm_password": "PasswordA123",
    })
    client.post("/api/farmer/onboarding", json={
        "name": "Farmer Alpha",
        "state": "Punjab",
        "total_land": 5.00,
        "unit": "Acres",
        "sections": [],
    })
    farms_a = client.get("/api/farms").get_json()["farms"]
    farm_a_id = farms_a[0]["id"]
    sec_a_res = client.post(f"/api/farms/{farm_a_id}/sections", json={
        "name": "Alpha Wheat Section",
        "area_acres": 3.00,
        "crop": "Wheat",
    })
    sec_a_id = sec_a_res.get_json()["section"]["id"]

    # Logout Farmer A
    client.get("/logout")

    # Create Farmer B
    user_b = f"farmer_b_{secrets.token_hex(4)}"
    client.post("/api/auth/register", json={
        "username": user_b,
        "password": "PasswordB123",
        "confirm_password": "PasswordB123",
    })
    client.post("/api/farmer/onboarding", json={
        "name": "Farmer Beta",
        "state": "Haryana",
        "total_land": 3.00,
        "unit": "Acres",
        "sections": [],
    })
    farms_b = client.get("/api/farms").get_json()["farms"]
    farm_b_id = farms_b[0]["id"]

    # Farmer B querying Farmer A's farm sections gets zero sections (isolated data)
    rogue_list = client.get(f"/api/farms/{farm_a_id}/sections")
    assert rogue_list.status_code == 200
    assert rogue_list.get_json()["sections"] == []

    rogue_edit = client.put(f"/api/sections/{sec_a_id}", json={"name": "Hacked Plot"})
    assert rogue_edit.status_code in (400, 403, 404)

    rogue_del = client.delete(f"/api/sections/{sec_a_id}")
    assert rogue_del.status_code in (403, 404)

    # Logout Farmer B, log back in as Farmer A
    client.get("/logout")
    login_res = client.post("/api/auth/login", json={
        "username": user_a,
        "password": "PasswordA123",
    })
    assert login_res.status_code == 200

    # Verify Farmer A's section is completely intact in database
    list_a = client.get(f"/api/farms/{farm_a_id}/sections").get_json()["sections"]
    assert len(list_a) == 1
    assert list_a[0]["id"] == sec_a_id
    assert list_a[0]["name"] == "Alpha Wheat Section"
    assert list_a[0]["area_acres"] == 3.00


# ========================================================
# PART 5: Land Validation & Acreage Constraints
# ========================================================
def test_land_allocation_cannot_exceed_total_farm_area(client):
    """Cannot allocate more land than total available farm area."""
    unique_user = f"val_farmer_{secrets.token_hex(4)}"
    client.post("/api/auth/register", json={
        "username": unique_user,
        "password": "Password123",
        "confirm_password": "Password123",
    })
    client.post("/api/farmer/onboarding", json={
        "name": "Jaspreet Singh",
        "state": "Punjab",
        "total_land": 2.00,
        "unit": "Acres",
        "sections": [],
    })
    farms = client.get("/api/farms").get_json()["farms"]
    farm_id = farms[0]["id"]

    # Add 1.50 acres
    sec1 = client.post(f"/api/farms/{farm_id}/sections", json={
        "name": "Plot 1",
        "area_acres": 1.50,
        "crop": "Wheat",
    })
    assert sec1.status_code == 201

    # Attempt to add 1.00 acre (1.50 + 1.00 = 2.50 > 2.00 total) -> must fail with 400
    excess_res = client.post(f"/api/farms/{farm_id}/sections", json={
        "name": "Excess Plot",
        "area_acres": 1.00,
        "crop": "Potato",
    })
    assert excess_res.status_code == 400
    assert "available" in excess_res.get_json()["error"].lower()

    # Adding 0.50 acre (1.50 + 0.50 = 2.00 == total) -> must succeed
    fit_res = client.post(f"/api/farms/{farm_id}/sections", json={
        "name": "Fitting Plot",
        "area_acres": 0.50,
        "crop": "Potato",
    })
    assert fit_res.status_code == 201


def test_unit_conversions_hectares_bighas_gunthas():
    """Converts various Indian land units accurately into acres."""
    assert LAND_UNIT_TO_ACRES["acre"] == 1.0
    assert round(LAND_UNIT_TO_ACRES["hectares"], 2) == 2.47
    assert round(LAND_UNIT_TO_ACRES["bigha"], 3) == 0.625
    assert round(LAND_UNIT_TO_ACRES["bighas"], 3) == 0.625
    assert round(LAND_UNIT_TO_ACRES["guntha"], 3) == 0.025
    assert round(LAND_UNIT_TO_ACRES["gunthas"], 3) == 0.025
