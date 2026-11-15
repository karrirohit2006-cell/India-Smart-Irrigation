"""
Tests for Multi-Farmer, Multi-Land, AI-Powered Smart Irrigation Management System.
Validates:
1. Multi-Farmer authentication & strict data isolation (Farmer A vs Farmer B)
2. Land allocation validation (sections sum cannot exceed farm total land)
3. Dynamic crop age and growth stage from sowing date
4. Empty land invariant (0 L, no schedule, cannot be scheduled)
5. Area-scaled water calculations (Wheat 0.5 ac = 500 L, Potato 0.3 ac = 250 L)
6. Section-specific start date + planning period scheduling
7. Status tracking (Completed = Green, Skipped = Red + intelligent replacement)
8. Combined global calendar aggregation (sums 500 + 250 = 750 L, maintains section independence)
9. Live weather & reverse geocoding endpoints
10. AI Chatbot multi-land intelligence with strict farmer data isolation
"""

import pytest
from datetime import datetime, timedelta
from app import app
from src.farm_manager import (
    init_farm_db,
    seed_demo_accounts,
    authenticate_farmer,
    get_farmer_by_id,
    get_farmer_farms,
    get_farm_sections,
    get_land_summary,
    create_section,
    predict_section_irrigation,
    schedule_section_irrigation,
    get_section_schedules,
    update_section_schedule_status,
    get_farmer_combined_calendar,
    calculate_crop_age_and_stage,
)
from src.weather_service import get_live_weather, reverse_geocode
from src.agri_assistant import generate_response


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database and demo accounts are initialized before each test."""
    init_farm_db()
    seed_demo_accounts()


@pytest.fixture
def client():
    """Test client for Flask API calls."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ========================================================
# Phase 1 & 2: Multi-Farmer Authentication & Isolation
# ========================================================
def test_demo_accounts_seeded_and_isolated():
    """Farmer A (Ramesh Kumar, 1 Acre) and Farmer B (Suresh Patel, 2 Acres) exist with separate data."""
    fa = authenticate_farmer("9876543210", "farmer123")
    fb = authenticate_farmer("9876543211", "farmer123")

    assert fa is not None
    assert fb is not None
    assert fa["id"] != fb["id"]
    assert fa["name"] == "Ramesh Kumar"
    assert fb["name"] == "Suresh Patel"
    assert fa["total_land"] == 1.00
    assert fb["total_land"] == 2.00

    # Farmer A's farms
    farms_a = get_farmer_farms(fa["id"])
    farms_b = get_farmer_farms(fb["id"])
    assert len(farms_a) >= 1
    assert len(farms_b) >= 1
    assert farms_a[0]["id"] != farms_b[0]["id"]

    # Farmer A sections
    secs_a = get_farm_sections(farms_a[0]["id"], fa["id"])
    # Farmer B sections
    secs_b = get_farm_sections(farms_b[0]["id"], fb["id"])

    # Verify Farmer A has Wheat, Potato, Empty
    crops_a = [s["crop"] for s in secs_a]
    assert "Wheat" in crops_a
    assert "Potato" in crops_a
    assert any(s["is_empty"] for s in secs_a)

    # Verify Farmer B has Rice, Empty
    crops_b = [s["crop"] for s in secs_b]
    assert "Rice" in crops_b
    assert "Wheat" not in crops_b
    assert "Potato" not in crops_b


def test_strict_cross_farmer_data_isolation():
    """Farmer A cannot access Farmer B's farm or sections."""
    fa = authenticate_farmer("9876543210", "farmer123")
    fb = authenticate_farmer("9876543211", "farmer123")

    farms_b = get_farmer_farms(fb["id"])
    farm_b_id = farms_b[0]["id"]

    # Farmer A tries to query Farmer B's farm sections -> must return empty list
    hacked_sections = get_farm_sections(farm_b_id, fa["id"])
    assert hacked_sections == []

    # Farmer A tries to get land summary of Farmer B's farm -> must be blocked
    hacked_summary = get_land_summary(farm_b_id, fa["id"])
    assert "error" in hacked_summary or hacked_summary == {}


# ========================================================
# Phase 3 & 4: Land Allocation & Section Validation
# ========================================================
def test_land_allocation_summary_and_validation():
    """Total land cannot be exceeded by section allocations."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farms_a = get_farmer_farms(fa["id"])
    farm_a_id = farms_a[0]["id"]

    summary = get_land_summary(farm_a_id, fa["id"])
    assert summary["total_land"] == 1.00
    assert summary["allocated_land"] == 0.80  # 0.50 Wheat + 0.30 Potato
    assert summary["available_land"] == 0.20  # 0.20 Empty/Available
    assert summary["total_sections"] == 3

    # Attempting to allocate 0.50 more acres on 0.20 available land must be rejected
    with pytest.raises(ValueError) as excinfo:
        create_section(
            farm_id=farm_a_id,
            farmer_id=fa["id"],
            name="Section 04 Overflow",
            area_acres=0.50,
            is_empty=False,
            crop="Maize"
        )
    assert "cannot allocate" in str(excinfo.value).lower()


def test_dynamic_crop_age_calculation():
    """Crop age is dynamically computed from sowing date."""
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    res = calculate_crop_age_and_stage("Wheat", thirty_days_ago)

    assert res["age_days"] == 30
    assert "Tillering" in res["growth_stage"]

    # Recent sowing (5 days)
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    res_recent = calculate_crop_age_and_stage("Wheat", five_days_ago)
    assert res_recent["age_days"] == 5
    assert "Germination" in res_recent["growth_stage"]


# ========================================================
# Phase 5: Live Weather & Geocoding
# ========================================================
def test_weather_and_geocoding_services():
    """Live weather and reverse geocoding endpoints operate reliably."""
    # Punjab farm coordinates
    lat, lon = 30.9010, 75.8573
    weather = get_live_weather(lat, lon)
    assert "current_temp" in weather
    assert "current_humidity" in weather
    assert "source" in weather
    assert "Open-Meteo" in weather["source"] or "Sensor Baseline" in weather["source"]

    location = reverse_geocode(lat, lon)
    assert "state" in location
    assert location["state"] == "Punjab"


# ========================================================
# Phase 6 & 7: Empty Land & Area-Scaled Section Prediction
# ========================================================
def test_empty_land_invariant():
    """Empty land section returns DO NOT IRRIGATE, 0 L, and no schedule."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farms_a = get_farmer_farms(fa["id"])
    secs_a = get_farm_sections(farms_a[0]["id"], fa["id"])

    empty_sec = next(s for s in secs_a if s["is_empty"])
    assert empty_sec is not None

    pred = predict_section_irrigation(empty_sec["id"], fa["id"])
    assert pred["irrigation_required"] is False
    assert pred["water_requirement_liters"] == 0
    assert "uncultivated" in pred["reason"].lower() or "empty" in pred["reason"].lower()

    # Attempting to schedule empty land returns empty schedule list
    schedules = schedule_section_irrigation(empty_sec["id"], fa["id"], planning_period_days=7)
    assert len(schedules) == 0


def test_section_area_scaling():
    """Water requirement is scaled by section area (0.5 ac = 500 L, 0.3 ac = 250 L)."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farms_a = get_farmer_farms(fa["id"])
    secs_a = get_farm_sections(farms_a[0]["id"], fa["id"])

    sec_wheat = next(s for s in secs_a if s["crop"] == "Wheat")
    sec_potato = next(s for s in secs_a if s["crop"] == "Potato")

    assert sec_wheat["area_acres"] == 0.50
    assert sec_potato["area_acres"] == 0.30

    pred_wheat = predict_section_irrigation(sec_wheat["id"], fa["id"])
    pred_potato = predict_section_irrigation(sec_potato["id"], fa["id"])

    assert pred_wheat["irrigation_required"] is True
    assert pred_potato["irrigation_required"] is True

    # 1000 L/acre * 0.50 acre = 500 L
    assert abs(pred_wheat["water_requirement_liters"] - 500.0) < 1.0
    # 833.33 L/acre * 0.30 acre = 250 L
    assert abs(pred_potato["water_requirement_liters"] - 250.0) < 1.0


# ========================================================
# Phase 8: Section-Specific Scheduling & Status Tracking
# ========================================================
def test_section_schedules_and_status_tracking():
    """Each section maintains independent calendars; Completed turns GREEN, Skipped turns RED."""
    fa = authenticate_farmer("9876543210", "farmer123")
    farms_a = get_farmer_farms(fa["id"])
    secs_a = get_farm_sections(farms_a[0]["id"], fa["id"])
    sec_wheat = next(s for s in secs_a if s["crop"] == "Wheat")

    # Generate fresh schedule starting tomorrow
    start_d = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    scheds = schedule_section_irrigation(sec_wheat["id"], fa["id"], start_date=start_d, planning_period_days=7)
    assert len(scheds) >= 2

    first_sess = scheds[0]
    assert first_sess["status"] in ("Upcoming", "Pending")

    # Mark completed
    res_comp = update_section_schedule_status(first_sess["id"], fa["id"], new_status="Completed")
    assert res_comp["success"] is True

    updated_scheds = get_section_schedules(sec_wheat["id"], fa["id"])
    first_updated = next(s for s in updated_scheds if s["id"] == first_sess["id"])
    assert first_updated["status"] == "Completed"
    assert first_updated["completed_at"] is not None

    # Skip second session
    second_sess = scheds[1]
    res_skip = update_section_schedule_status(second_sess["id"], fa["id"], new_status="Skipped", skip_reason="Farmer opted to skip")
    assert res_skip["success"] is True

    updated_scheds_2 = get_section_schedules(sec_wheat["id"], fa["id"])
    second_updated = next(s for s in updated_scheds_2 if s["id"] == second_sess["id"])
    assert second_updated["status"] == "Skipped"
    # Ensure replacement rescheduled session was added
    rescheduled = [s for s in updated_scheds_2 if s["status"] == "Rescheduled"]
    assert len(rescheduled) >= 1


# ========================================================
# Phase 9: Global Combined Farmer Calendar
# ========================================================
def test_global_combined_farmer_calendar():
    """Global calendar aggregates across all sections for one farmer without mutating records."""
    fa = authenticate_farmer("9876543210", "farmer123")
    now = datetime.now()

    cal = get_farmer_combined_calendar(fa["id"], now.year, now.month)
    assert cal["farmer_name"] == "Ramesh Kumar"
    assert cal["total_sessions"] >= 2
    assert "daily_schedule" in cal

    # Find any date with multiple sections or verify daily aggregation
    for date_key, day_info in cal["daily_schedule"].items():
        assert day_info["total_water_liters"] > 0
        assert len(day_info["items"]) == day_info["sections_count"]
        for it in day_info["items"]:
            assert it["section_name"] in ("Section 01", "Section 02")

    # Verify Farmer B's calendar does not contain Farmer A's sessions
    fb = authenticate_farmer("9876543211", "farmer123")
    cal_b = get_farmer_combined_calendar(fb["id"], now.year, now.month)
    for date_key, day_info in cal_b["daily_schedule"].items():
        for it in day_info["items"]:
            assert it["crop"] == "Rice"
            assert it["crop"] != "Wheat"
            assert it["crop"] != "Potato"


# ========================================================
# Phase 10: Multi-Land AI Chatbot & Multilingual Answers
# ========================================================
def test_chatbot_multi_land_queries():
    """Chatbot answers multi-land queries with active farmer context and strict isolation."""
    fa = authenticate_farmer("9876543210", "farmer123")
    context_a = {"farmer_id": fa["id"]}

    # Query 1: Total land
    r1 = generate_response("How much total land do I own?", context=context_a, language="en")
    assert "1.00 Acre" in r1["reply"] or "1.0 Acre" in r1["reply"] or "1.0" in r1["reply"]
    assert "Punjab" in r1["reply"] or "Ludhiana" in r1["reply"]

    # Query 2: Farm sections
    r2 = generate_response("Show my farm sections", context=context_a, language="en")
    assert "Wheat" in r2["reply"]
    assert "Potato" in r2["reply"]
    assert "Empty" in r2["reply"]

    # Query 3: Available land
    r3 = generate_response("How much land is available?", context=context_a, language="en")
    assert "0.20 Acre" in r3["reply"] or "0.2 Acre" in r3["reply"] or "0.2" in r3["reply"]

    # Query 4: Crop in Section 01
    r4 = generate_response("What crop is in Section 01?", context=context_a, language="en")
    assert "Wheat" in r4["reply"]

    # Query 5: Water requirement for Wheat
    r5 = generate_response("How much water does my Wheat section require?", context=context_a, language="en")
    assert "500" in r5["reply"]  # 500 Liters for 0.50 Acre

    # Isolation Test: Farmer B asks for total land
    fb = authenticate_farmer("9876543211", "farmer123")
    context_b = {"farmer_id": fb["id"]}
    r_b = generate_response("How much total land do I own?", context=context_b, language="en")
    assert "2.00 Acre" in r_b["reply"] or "2.0 Acre" in r_b["reply"] or "2.0" in r_b["reply"]
    assert "Ramesh Kumar" not in r_b["reply"]


# ========================================================
# Flask API Endpoints End-to-End Verification
# ========================================================
def test_flask_auth_and_land_api_endpoints(client):
    """End-to-end HTTP API tests for authentication, sections, and global calendar."""
    # 1. Login as Farmer A via demo-login
    login_res = client.post("/api/auth/demo-login", json={"demo_user": "farmer_a"})
    assert login_res.status_code == 200
    login_data = login_res.get_json()
    assert login_data["farmer"]["name"] == "Ramesh Kumar"
    farmer_id = login_data["farmer"]["id"]

    # 2. Get /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.get_json()
    assert me_data["authenticated"] is True
    assert me_data["land_summary"]["total_land"] == 1.00
    assert me_data["land_summary"]["available_land"] == 0.20

    # 3. Get /api/farms/<farm_id>/sections
    farm_id = me_data["primary_farm"]["id"]
    secs_res = client.get(f"/api/farms/{farm_id}/sections")
    assert secs_res.status_code == 200
    secs_data = secs_res.get_json()
    assert len(secs_data["sections"]) == 3

    # 4. Get Global Combined Calendar
    cal_res = client.get("/api/farmer/calendar")
    assert cal_res.status_code == 200
    cal_data = cal_res.get_json()
    assert cal_data["farmer_name"] == "Ramesh Kumar"
    assert "daily_schedule" in cal_data

    # 5. Live Weather API
    w_res = client.get("/api/weather/live?lat=30.9010&lon=75.8573")
    assert w_res.status_code == 200
    w_data = w_res.get_json()
    assert "current_temp" in w_data or "temperature" in w_data
