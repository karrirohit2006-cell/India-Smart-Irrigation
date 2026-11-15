"""
Tests for Complete Voice-Controlled Website Integration.
Verifies all voice-driven actions, multilingual command understanding (Telugu, Hindi, Punjabi, English),
website navigation, farmer onboarding, land section management, irrigation planner execution,
dual calendar updates, weather queries, context awareness, and strict farmer-level data isolation.
"""

import pytest
import json
from app import app
from src.farm_manager import (
    register_farmer,
    get_farmer_farms,
    get_farm_sections,
    create_section,
    get_land_summary,
    get_section_schedules,
)
from src.voice_command_engine import (
    process_voice_command,
    APPROVED_VOICE_ACTIONS,
    extract_number,
    extract_ordinal,
    match_state,
    match_crop,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_farmer():
    """Create a verified test farmer with 2.0 Acres and 2 sections."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    farmer = register_farmer(
        name="Venkat Rao",
        phone=f"98{uuid.uuid4().int % 100000000:08d}",
        password="Farmer@123",
        state="Andhra Pradesh",
        district="Srikakulam",
        village="Narasannapeta",
        latitude=18.4167,
        longitude=84.0500,
        total_land=2.0,
        unit="Acres",
        username=f"venkat_{suffix}"
    )
    farmer_id = farmer["id"]
    farms = get_farmer_farms(farmer_id)
    farm_id = farms[0]["id"]

    # Add 2 sections
    sec1 = create_section(farm_id, farmer_id, "Section 01", 1.0, is_empty=False, crop="Rice")
    sec2 = create_section(farm_id, farmer_id, "Section 02", 0.5, is_empty=False, crop="Wheat")
    from src.farm_manager import schedule_section_irrigation
    schedule_section_irrigation(sec1["id"], farmer_id, planning_period_days=7)

    return {
        "farmer_id": farmer_id,
        "farm_id": farm_id,
        "sec1_id": sec1["id"],
        "sec2_id": sec2["id"],
    }


# ==============================================================================
# 1. Number, Ordinal, State, and Crop Multilingual Parsing
# ==============================================================================
def test_multilingual_entity_extraction():
    # Numbers in various languages
    assert extract_number("2 acres") == 2.0
    assert extract_number("half an acre") == 0.5
    assert extract_number("అర ఎకరం") == 0.5
    assert extract_number("రెండు ఎకరాలు") == 2.0
    assert extract_number("दो एकड़") == 2.0
    assert extract_number("ਦੋ ਏਕੜ") == 2.0

    # Ordinals
    assert extract_ordinal("first section") == 0
    assert extract_ordinal("మొదటి సెక్షన్") == 0
    assert extract_ordinal("पहला सेक्शन") == 0
    assert extract_ordinal("Section 02") == 1
    assert extract_ordinal("రెండవ సెక్షన్") == 1

    # States
    assert match_state("నా రాష్ట్రం ఆంధ్రప్రదేశ్") == "Andhra Pradesh"
    assert match_state("मेरा राज्य पंजाब") == "Punjab"
    assert match_state("select Haryana") == "Haryana"

    # Crops
    assert match_crop("గోధుమ పంట") == "Wheat"
    assert match_crop("వరి పంట") == "Rice"
    assert match_crop("आलू की खेती") == "Potato"
    assert match_crop("rice crop") == "Rice"


# ==============================================================================
# 2. Website Navigation Voice Commands (Section 3)
# ==============================================================================
def test_voice_navigation_commands(test_farmer):
    fid = test_farmer["farmer_id"]

    # Dashboard in Telugu & English
    res_te = process_voice_command(fid, "నా డాష్బోర్డ్ ఓపెన్ చేయి", language="te")
    assert res_te["status"] == "success"
    assert res_te["action"] == "navigate_to_page"
    assert res_te["action_payload"]["target"] == "dashboard"
    assert "డాష్బోర్డ్" in res_te["spoken_response"]

    res_en = process_voice_command(fid, "Open dashboard", language="en")
    assert res_en["action"] == "navigate_to_page"
    assert res_en["action_payload"]["target"] == "dashboard"

    # Land Sections
    res_sec = process_voice_command(fid, "Open Land Sections", language="en")
    assert res_sec["action"] == "navigate_to_page"
    assert res_sec["action_payload"]["target"] == "land_sections"

    # Irrigation Planner
    res_plan = process_voice_command(fid, "ఇరిగేషన్ ప్లానర్ తెరవండి", language="te")
    assert res_plan["action"] == "navigate_to_page"
    assert res_plan["action_payload"]["target"] == "irrigation_planner"

    # Combined Calendar
    res_cal = process_voice_command(fid, "Open combined calendar", language="en")
    assert res_cal["action"] == "navigate_to_page"
    assert res_cal["action_payload"]["target"] == "combined_calendar"

    # Irrigation History
    res_hist = process_voice_command(fid, "నా ఇరిగేషన్ హిస్టరీ చూపించు", language="te")
    assert res_hist["action"] == "navigate_to_page"
    assert res_hist["action_payload"]["target"] == "irrigation_history"

    # Log out
    res_logout = process_voice_command(fid, "Log out", language="en")
    assert res_logout["action"] == "navigate_to_page"
    assert res_logout["action_payload"]["target"] == "logout"


# ==============================================================================
# 3. Voice-Controlled Farmer Onboarding (Section 4)
# ==============================================================================
def test_voice_controlled_onboarding():
    # 1. State selection in Telugu
    res_state = process_voice_command("", "నా రాష్ట్రం ఆంధ్రప్రదేశ్", language="te", context={"page": "onboarding"})
    assert res_state["action"] == "set_onboarding_field"
    assert res_state["action_payload"]["field"] == "state"
    assert res_state["action_payload"]["value"] == "Andhra Pradesh"
    assert "ఆంధ్రప్రదేశ్" in res_state["spoken_response"]

    # 2. District in Telugu
    res_dist = process_voice_command("", "నా జిల్లా శ్రీకాకుళం", language="te", context={"page": "onboarding"})
    assert res_dist["action"] == "set_onboarding_field"
    assert res_dist["action_payload"]["field"] == "district"
    assert "శ్రీకాకుళం" in res_dist["action_payload"]["value"]

    # 3. Total land in Telugu
    res_land = process_voice_command("", "నా భూమి రెండు ఎకరాలు", language="te", context={"page": "onboarding"})
    assert res_land["action"] == "set_onboarding_field"
    assert res_land["action_payload"]["field"] == "total_land"
    assert res_land["action_payload"]["value"] == 2.0

    # 4. Step navigation in Hindi
    res_step = process_voice_command("", "अगला कदम", language="hi", context={"page": "onboarding"})
    assert res_step["action"] == "set_onboarding_field"
    assert res_step["action_payload"]["field"] == "step"
    assert res_step["action_payload"]["value"] == "next"


# ==============================================================================
# 4. Voice-Controlled Land Section Management (Section 5)
# ==============================================================================
def test_voice_land_section_management(test_farmer):
    fid = test_farmer["farmer_id"]
    ctx = {"farm_id": test_farmer["farm_id"]}

    # 1. Add a section
    res_add = process_voice_command(fid, "Add a new section with rice", language="en", context=ctx)
    assert res_add["action"] == "add_land_section"
    assert res_add["action_payload"]["crop"] == "Rice"

    # 2. Select first section in Telugu: "నా మొదటి సెక్షన్ చూపించు"
    res_sel = process_voice_command(fid, "నా మొదటి సెక్షన్ చూపించు", language="te", context=ctx)
    assert res_sel["action"] == "select_section"
    assert res_sel["action_payload"]["section_id"] == test_farmer["sec1_id"]
    assert "Section 01" in res_sel["spoken_response"]

    # 3. Edit Section 01: Set area to 0.75 acres
    res_edit = process_voice_command(fid, "Set Section 01 area to 0.75 acres", language="en", context=ctx)
    assert res_edit["action"] == "edit_land_section"
    assert res_edit["action_payload"]["section_id"] == test_farmer["sec1_id"]
    assert res_edit["action_payload"]["area_acres"] == 0.75

    # 4. Remove Section 02 - requires confirmation!
    res_rm = process_voice_command(fid, "Remove Section 02", language="en", context=ctx)
    assert res_rm["status"] == "pending_confirmation"
    assert res_rm["requires_confirmation"] is True
    assert res_rm["action"] == "remove_land_section"
    assert res_rm["action_payload"]["section_id"] == test_farmer["sec2_id"]
    assert "Confirm" in res_rm["confirmation_prompt"]

    # 5. Confirm removal via voice
    res_confirm = process_voice_command(
        fid,
        "Yes, confirm",
        language="en",
        context={"pending_action": {"action": "remove_land_section", "payload": res_rm["action_payload"]}}
    )
    assert res_confirm["status"] == "success"
    assert res_confirm["action"] == "remove_land_section"
    assert res_confirm["requires_confirmation"] is False

    # Verify section was actually deleted from database
    secs = get_farm_sections(test_farmer["farm_id"], fid)
    assert len(secs) == 1
    assert secs[0]["id"] == test_farmer["sec1_id"]


# ==============================================================================
# 5. Voice-Controlled Irrigation Planner (Section 6)
# ==============================================================================
def test_voice_irrigation_planner(test_farmer):
    fid = test_farmer["farmer_id"]
    ctx = {
        "farm_id": test_farmer["farm_id"],
        "active_section_id": test_farmer["sec1_id"]
    }

    # 1. Check irrigation in Telugu: "నీళ్లు పెట్టాలా?"
    res_pred = process_voice_command(fid, "నీళ్లు పెట్టాలా?", language="te", context=ctx)
    assert res_pred["action"] == "run_irrigation_prediction"
    assert res_pred["action_payload"]["section_id"] == test_farmer["sec1_id"]
    assert res_pred["action_payload"]["decision"] in ["IRRIGATE", "DO NOT IRRIGATE"]
    assert len(res_pred["spoken_response"]) > 10

    # 2. Calculate water requirement: "How much water does my crop need?"
    res_water = process_voice_command(fid, "How much water does my crop need?", language="en", context=ctx)
    assert res_water["action"] == "calculate_water_requirement"
    assert res_water["action_payload"]["section_id"] == test_farmer["sec1_id"]
    assert res_water["action_payload"]["liters"] > 0
    assert "Liters" in res_water["spoken_response"]

    # 3. Generate irrigation schedule
    res_sched = process_voice_command(fid, "Generate my irrigation schedule", language="en", context=ctx)
    assert res_sched["action"] == "generate_irrigation_schedule"
    assert res_sched["action_payload"]["section_id"] == test_farmer["sec1_id"]
    assert len(res_sched["action_payload"]["schedules"]) > 0


# ==============================================================================
# 6. Voice-Controlled Irrigation Calendar (Section 7)
# ==============================================================================
def test_voice_irrigation_calendar(test_farmer):
    fid = test_farmer["farmer_id"]
    ctx = {
        "farm_id": test_farmer["farm_id"],
        "active_section_id": test_farmer["sec1_id"]
    }

    # 1. Upcoming schedule check: "What should I irrigate today?"
    res_up = process_voice_command(fid, "What should I irrigate today?", language="en", context=ctx)
    assert res_up["action"] == "get_upcoming_schedule"

    # 2. Mark irrigation completed - requires confirmation!
    res_comp = process_voice_command(fid, "Mark Section 01 irrigation completed", language="en", context=ctx)
    assert res_comp["requires_confirmation"] is True
    assert res_comp["action"] == "update_irrigation_status"
    assert res_comp["action_payload"]["status"] == "Completed"

    # 3. Confirm mark completed
    res_comp_done = process_voice_command(
        fid,
        "Confirm",
        language="en",
        context={"pending_action": {"action": "update_irrigation_status", "payload": res_comp["action_payload"]}}
    )
    assert res_comp_done["status"] == "success"
    assert res_comp_done["action"] == "update_irrigation_status"


# ==============================================================================
# 7. Voice-Controlled Weather & Farm Information (Section 8)
# ==============================================================================
def test_voice_weather_and_farm_info(test_farmer):
    fid = test_farmer["farmer_id"]
    ctx = {"farm_id": test_farmer["farm_id"]}

    # Weather in Hindi: "मौसम दिखाओ"
    res_w = process_voice_command(fid, "मौसम दिखाओ", language="hi", context=ctx)
    assert res_w["action"] == "get_weather"
    assert "temperature" in res_w["action_payload"]
    assert "humidity" in res_w["action_payload"]
    assert "forecast_rainfall_24h" in res_w["action_payload"]

    # Farm info in Telugu: "నా భూమి ఎంత"
    res_f = process_voice_command(fid, "నా భూమి ఎంత", language="te", context=ctx)
    assert res_f["action"] == "get_farm_summary"
    assert res_f["action_payload"]["total_land"] == 2.0
    assert "భూమి" in res_f["spoken_response"]


# ==============================================================================
# 8. Context Awareness & Natural Follow-ups (Section 9)
# ==============================================================================
def test_voice_context_awareness(test_farmer):
    fid = test_farmer["farmer_id"]

    # 1. No section specified and none in context -> asks for clarification
    res_ambig = process_voice_command(fid, "Edit section", language="en", context={})
    assert res_ambig["action"] == "ask_clarification"
    assert "Which section" in res_ambig["spoken_response"]

    # 2. Natural Follow-up: Section selected in previous turn -> "Check irrigation for this"
    ctx_followup = {
        "farm_id": test_farmer["farm_id"],
        "active_section_id": test_farmer["sec1_id"]
    }
    res_follow = process_voice_command(fid, "Check irrigation for this", language="en", context=ctx_followup)
    assert res_follow["action"] == "run_irrigation_prediction"
    assert res_follow["action_payload"]["section_id"] == test_farmer["sec1_id"]


# ==============================================================================
# 9. Security, Data Isolation & Flask API Endpoints (Section 11)
# ==============================================================================
def test_flask_voice_endpoints_security(client, test_farmer):
    fid = test_farmer["farmer_id"]

    # Test /api/voice/command with session authentication
    with client.session_transaction() as sess:
        sess["farmer_id"] = fid

    res = client.post("/api/voice/command", json={
        "message": "నా డాష్బోర్డ్ ఓపెన్ చేయి",
        "language": "te",
        "context": {"farm_id": test_farmer["farm_id"]}
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["action"] == "navigate_to_page"
    assert data["action_payload"]["target"] == "dashboard"

    # Test /api/voice/action/execute directly
    res_exec = client.post("/api/voice/action/execute", json={
        "action": "edit_land_section",
        "payload": {
            "section_id": test_farmer["sec1_id"],
            "name": "Section 01 Renamed",
            "area_acres": 0.8
        }
    })
    assert res_exec.status_code == 200
    data_exec = res_exec.get_json()
    assert data_exec["status"] == "success"

    # Unauthorized action check
    res_unauth = client.post("/api/voice/action/execute", json={
        "action": "drop_all_tables_unauthorized"
    })
    assert res_unauth.status_code == 400

    # Cross-farmer isolation check: Farmer 2 cannot modify Farmer 1's section
    import uuid
    sfx2 = uuid.uuid4().hex[:6]
    farmer2 = register_farmer(
        name="Sunil Kumar",
        phone=f"97{uuid.uuid4().int % 100000000:08d}",
        password="Farmer@123",
        state="Punjab",
        username=f"sunil_{sfx2}"
    )
    with client.session_transaction() as sess:
        sess["farmer_id"] = farmer2["id"]

    # Try to delete Farmer 1's section as Farmer 2 -> must be rejected / not deleted
    res_cross = client.post("/api/voice/action/execute", json={
        "action": "remove_land_section",
        "payload": {"section_id": test_farmer["sec1_id"]}
    })
    # delete_section returns False for unauthorized farmer
    assert res_cross.get_json()["success"] is False
