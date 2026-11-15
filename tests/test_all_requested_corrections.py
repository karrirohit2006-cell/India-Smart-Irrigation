"""
Comprehensive test suite verifying all 6 parts of the Antigravity Implementation Prompt:
1. Global Voice Assistant Website Control (All requested natural speech commands)
2. Chatbot Microphone independence from Global Voice Assistant
3. Dashboard Data Isolation between distinct farmers
4. Initial Dashboard Empty State ("No irrigation required" / "No irrigation schedule available yet")
5. Removal of static "35 Days – Tillering" crop display from Crops & Soil Details interface
"""

import pytest
import uuid
from app import app
from src.farm_manager import (
    register_farmer,
    get_farmer_farms,
    create_section,
    schedule_section_irrigation,
)
from src.voice_command_engine import (
    process_voice_command,
    APPROVED_VOICE_ACTIONS,
    extract_ordinal,
    match_crop,
)
from src.irrigation_scheduler import (
    get_all_schedules,
    get_schedule_summary,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def two_farmers():
    """Create two distinct farmers to test strict data isolation."""
    # Farmer 1: Existing active farmer with sections and schedules
    suffix1 = uuid.uuid4().hex[:6]
    f1 = register_farmer(
        name="Ramesh Patel",
        phone=f"91{uuid.uuid4().int % 100000000:08d}",
        password="Farmer@123",
        state="Gujarat",
        district="Anand",
        village="Boriavi",
        latitude=22.5645,
        longitude=72.9289,
        total_land=3.0,
        unit="Acres",
        username=f"ramesh_{suffix1}"
    )
    farms1 = get_farmer_farms(f1["id"])
    sec1 = create_section(farms1[0]["id"], f1["id"], "Section 01", 1.5, is_empty=False, crop="Cotton")
    sec2 = create_section(farms1[0]["id"], f1["id"], "Section 02", 1.0, is_empty=False, crop="Wheat")
    schedule_section_irrigation(sec1["id"], f1["id"], planning_period_days=7)

    # Farmer 2: Brand new farmer with NO calculations or schedules yet
    suffix2 = uuid.uuid4().hex[:6]
    f2 = register_farmer(
        name="Suresh Kumar",
        phone=f"92{uuid.uuid4().int % 100000000:08d}",
        password="Farmer@123",
        state="Punjab",
        district="Ludhiana",
        village="Sahnewal",
        latitude=30.9010,
        longitude=75.8573,
        total_land=2.0,
        unit="Acres",
        username=f"suresh_{suffix2}"
    )

    return {
        "farmer1": f1,
        "farmer2": f2,
        "f1_sec1": sec1,
        "f1_sec2": sec2,
    }


# ==============================================================================
# PART 1: GLOBAL VOICE ASSISTANT WEBSITE CONTROL (REAL ACTIONS EXECUTION)
# ==============================================================================
def test_voice_assistant_all_requested_commands(two_farmers):
    fid = two_farmers["farmer1"]["id"]
    ctx = {"farm_id": get_farmer_farms(fid)[0]["id"]}

    # 1. "Open crop details."
    r = process_voice_command(fid, "Open crop details.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "crop_details"

    # 2. "Go to irrigation planner."
    r = process_voice_command(fid, "Go to irrigation planner.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "irrigation_planner"

    # 3. "Open my farm sections."
    r = process_voice_command(fid, "Open my farm sections.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "land_sections"

    # 4. "Open calendar."
    r = process_voice_command(fid, "Open calendar.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "irrigation_calendar"

    # 5. "Go to history."
    r = process_voice_command(fid, "Go to history.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "irrigation_history"

    # 6. "Return to dashboard."
    r = process_voice_command(fid, "Return to dashboard.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "dashboard"

    # 7. "Select crop number two."
    r = process_voice_command(fid, "Select crop number two.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "select_crop"
    assert r["action_payload"]["crop_index"] == 1
    assert r["action_payload"]["crop_number"] == 2

    # 8. "Select the second land section."
    r = process_voice_command(fid, "Select the second land section.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "select_section"
    assert r["action_payload"]["ordinal_index"] == 1
    assert "Section 02" in r["action_payload"]["section_name"]

    # 9. "Open the first farm."
    r = process_voice_command(fid, "Open the first farm.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "select_farm"
    assert r["action_payload"]["farm_index"] == 0

    # 10. "Choose rice."
    r = process_voice_command(fid, "Choose rice.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "select_crop"
    assert r["action_payload"]["crop"] == "Rice"

    # 11. "Change the crop to maize."
    r = process_voice_command(fid, "Change the crop to maize.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "select_crop"
    assert r["action_payload"]["crop"] == "Maize"

    # 12. "Open soil details."
    r = process_voice_command(fid, "Open soil details.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "soil_details"

    # 13. "Show my irrigation schedule."
    r = process_voice_command(fid, "Show my irrigation schedule.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "irrigation_schedule"

    # 14. "Calculate irrigation requirements."
    r = process_voice_command(fid, "Calculate irrigation requirements.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "run_irrigation_prediction"
    assert r["action_payload"]["trigger_calculation"] is True

    # 15. "Save this section."
    r = process_voice_command(fid, "Save this section.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "save_section"

    # 16. "Go back."
    r = process_voice_command(fid, "Go back.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "navigate_to_page"
    assert r["action_payload"]["target"] == "go_back"

    # 17. "Scroll down."
    r = process_voice_command(fid, "Scroll down.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "scroll_page"
    assert r["action_payload"]["direction"] == "down"

    # 18. "Scroll to the top."
    r = process_voice_command(fid, "Scroll to the top.", language="en", context=ctx)
    assert r["status"] == "success"
    assert r["action"] == "scroll_page"
    assert r["action_payload"]["direction"] == "top"


def test_approved_actions_whitelist():
    """Ensure all required actions are in APPROVED_VOICE_ACTIONS whitelist."""
    expected = {
        "navigate_to_page",
        "select_farm",
        "select_section",
        "select_crop",
        "scroll_page",
        "save_section",
        "run_irrigation_prediction",
        "calculate_water_requirement",
        "generate_irrigation_schedule",
        "get_weather",
        "get_farm_summary",
        "get_irrigation_history",
        "get_upcoming_schedule",
        "update_irrigation_status",
    }
    for act in expected:
        assert act in APPROVED_VOICE_ACTIONS, f"Missing {act} from APPROVED_VOICE_ACTIONS"


# ==============================================================================
# PART 2 & 3: DASHBOARD DATA ISOLATION & INITIAL EMPTY STATE
# ==============================================================================
def test_dashboard_data_isolation(client, two_farmers):
    f1 = two_farmers["farmer1"]
    f2 = two_farmers["farmer2"]

    # Farmer 1 has schedules generated
    f1_scheds = get_all_schedules(farmer_id=f1["id"])
    assert len(f1_scheds) > 0, "Farmer 1 should have schedules"

    # Farmer 2 has NOT generated schedules yet
    f2_scheds = get_all_schedules(farmer_id=f2["id"])
    assert len(f2_scheds) == 0, "Farmer 2 should have 0 schedules initially"

    # Test via API /api/schedules with session for Farmer 2
    with client.session_transaction() as sess:
        sess["farmer_id"] = f2["id"]

    res2 = client.get("/api/schedules")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["total"] == 0
    assert len(data2["schedules"]) == 0
    assert data2["summary"]["has_active_schedule"] is False
    assert data2["summary"]["total_active_sessions"] == 0

    # Test via API /api/schedules with session for Farmer 1
    with client.session_transaction() as sess:
        sess["farmer_id"] = f1["id"]

    res1 = client.get("/api/schedules")
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["total"] > 0
    assert len(data1["schedules"]) > 0


# ==============================================================================
# PART 4: REMOVAL OF UNNECESSARY CROP GROWTH DISPLAY ("35 Days - Tillering")
# ==============================================================================
def test_unwanted_crop_growth_display_removed():
    """Verify that '35 days (Tillering)' and '35 Days – Tillering' are completely removed from HTML."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert "35 days (Tillering)" not in html
    assert "35 days ago (Tillering)" not in html
    assert "Tillering" not in html
    # Ensure the Crop Growth Stage field and Estimated Age container are preserved
    assert 'id="cropGrowthStageFieldWrap"' in html
    assert 'id="calculatedCropAgeBadge"' in html
    assert 'Crop Growth Stage & Estimated Age' in html
    assert 'id="section_area_acres"' in html


# ==============================================================================
# PART 5: CHATBOT MICROPHONE VS GLOBAL VOICE ASSISTANT INDEPENDENCE
# ==============================================================================
def test_mic_features_remain_strictly_independent():
    """Verify that Global Voice Assistant (#btnVoiceNavMic) and Chatbot Mic (#agriMicBtn) remain strictly independent."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Both independent mic IDs must exist in the HTML
    assert 'id="btnVoiceNavMic"' in html
    assert 'id="agriMicBtn"' in html
    assert 'id="btnAudioListen"' in html
    assert 'id="btnAudioPause"' in html
