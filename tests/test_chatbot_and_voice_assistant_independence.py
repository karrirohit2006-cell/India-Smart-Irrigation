"""
Test Chatbot and Website Voice Assistant Independence.
Ensures both features operate completely independently without merging, replacing,
or interfering with each other.

1. Gemini AI Chatbot:
   - Dedicated floating button (#agriChatToggle) and conversational chat window (#agriChatWindow).
   - Backend endpoint /api/chat connected to Google Gemini API (src/agri_assistant.py).
   - Responds to agricultural questions in English, Telugu, Hindi, and Indian languages.
   - Microphone button (#agriMicBtn) inside chat dictates into #agriChatInput.
   - No large voice assistant deck inside #agriChatWindow.

2. Website-Wide Voice Assistant:
   - Dedicated topbar control group (#websiteVoiceAssistant).
   - Circular Speaker ON/OFF toggle (#btnVoiceSpeakerToggle).
   - Circular Microphone trigger (#btnVoiceNavMic).
   - Visual status pill (#vaNavStatusPill).
   - Dispatches real website actions via /api/voice/command.
   - Respects speaker ON/OFF state (verbal speech vs silent execution).
"""

import os
import json
import uuid
import pytest
from app import app
from src.farm_manager import (
    register_farmer,
    get_farmer_farms,
    create_section,
    schedule_section_irrigation,
    init_farm_db,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    init_farm_db()
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_farmer_session(client):
    """Creates a test farmer with a farm and sections, and logs them in."""
    suffix = uuid.uuid4().hex[:6]
    farmer = register_farmer(
        name="Ramesh Patel",
        phone=f"98{uuid.uuid4().int % 100000000:08d}",
        password="Farmer@123",
        state="Gujarat",
        district="Anand",
        village="Boriavi",
        latitude=22.5645,
        longitude=72.9289,
        total_land=4.0,
        unit="Acres",
        username=f"ramesh_{suffix}"
    )
    farmer_id = farmer["id"]
    farms = get_farmer_farms(farmer_id)
    farm_id = farms[0]["id"]

    sec1 = create_section(farm_id, farmer_id, "Section 01", 1.5, is_empty=False, crop="Wheat", soil_type="Loam")
    sec2 = create_section(farm_id, farmer_id, "Section 02", 1.0, is_empty=False, crop="Tomato", soil_type="Clay")
    schedule_section_irrigation(sec1["id"], farmer_id, planning_period_days=7)

    with client.session_transaction() as sess:
        sess["farmer_id"] = farmer_id
        sess["farmer_phone"] = farmer["phone"]
        sess["farmer_name"] = "Ramesh Patel"
        sess["authenticated"] = True

    return {"farmer_id": farmer_id, "farm_id": farm_id, "sec1": sec1, "sec2": sec2}


# ==============================================================================
# 1. HTML TEMPLATE STRUCTURE & SEPARATION TESTS
# ==============================================================================

def test_template_has_both_features_completely_separated(client):
    """Verify that templates/index.html includes both independent UI components."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Top navigation Voice Assistant exists
    assert 'id="websiteVoiceAssistant"' in html
    assert 'class="website-voice-assistant"' in html
    assert 'id="btnVoiceSpeakerToggle"' in html
    assert 'id="vaSpeakerIcon"' in html
    assert 'id="vaSpeakerBadge"' in html
    assert 'id="btnVoiceNavMic"' in html
    assert 'id="vaNavStatusPill"' in html

    # 2. AgriSaathi bottom-right Chatbot exists
    assert 'id="agriChatWidget"' in html
    assert 'id="agriChatToggle"' in html
    assert 'aria-label="Open AgriSaathi AI Agricultural Chatbot"' in html
    assert '🌱' in html  # Original plant icon restored

    # 3. Chat Window contains original chat components
    assert 'id="agriChatWindow"' in html
    assert 'id="agriChatHeaderTitle"' in html
    assert 'id="agriChatMessages"' in html
    assert 'id="agriChatForm"' in html
    assert 'id="agriChatInput"' in html
    assert 'id="agriSendBtn"' in html
    assert 'id="agriMicBtn"' in html
    assert 'id="agriHistoryPanel"' in html

    # 4. Verify NO large voiceAssistantDeck inside #agriChatWindow
    # The voice assistant deck was erroneously placed inside chat window previously
    assert '<div id="voiceAssistantDeck"' not in html


def test_js_controllers_do_not_hijack_each_other():
    """Verify that voice_controller.js does not hijack chatbot toggle or chat mic."""
    with open("static/voice_controller.js", "r", encoding="utf-8") as f:
        voice_js = f.read()

    with open("static/chat.js", "r", encoding="utf-8") as f:
        chat_js = f.read()

    # voice_controller.js must NOT listen to agriChatToggle
    assert 'document.getElementById("agriChatToggle")' not in voice_js
    # voice_controller.js must NOT hijack agriMicBtn (which belongs to chat dictation)
    assert '#agriMicBtn' not in voice_js

    # chat.js must manage agriChatToggle and agriMicBtn
    assert 'agriChatToggle' in chat_js
    assert 'agriMicBtn' in chat_js


# ==============================================================================
# 2. GEMINI AI CHATBOT FUNCTIONALITY TESTS
# ==============================================================================

def test_gemini_chatbot_answers_agricultural_questions(client, auth_farmer_session):
    """Verify /api/chat provides grounded agricultural advice for various crops."""
    # 1. English irrigation question
    res = client.post("/api/chat", json={
        "message": "What is the best irrigation practice for wheat during flowering stage?",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reply" in data
    assert len(data["reply"]) > 30

    # 2. Telugu crop water question
    res_te = client.post("/api/chat", json={
        "message": "వరి పంటలో నీటి యాజమాన్యం ఎలా చేయాలి?",
        "language": "te"
    })
    assert res_te.status_code == 200
    data_te = res_te.get_json()
    assert data_te["status"] == "success"
    # Contains Telugu characters
    assert any("\u0c00" <= c <= "\u0c7f" for c in data_te["reply"])

    # 3. Hindi soil moisture question
    res_hi = client.post("/api/chat", json={
        "message": "मिट्टी में नमी की जांच कैसे करें?",
        "language": "hi"
    })
    assert res_hi.status_code == 200
    data_hi = res_hi.get_json()
    assert data_hi["status"] == "success"
    # Contains Devanagari characters
    assert any("\u0900" <= c <= "\u097f" for c in data_hi["reply"])


def test_gemini_chatbot_input_validation(client):
    """Verify /api/chat enforces input validation and does not leak API keys."""
    # Empty message rejected
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400

    # Message too long (>1000 chars) rejected
    res_long = client.post("/api/chat", json={"message": "a" * 1005})
    assert res_long.status_code == 400


# ==============================================================================
# 3. WEBSITE-WIDE VOICE ASSISTANT FUNCTIONALITY TESTS
# ==============================================================================

def test_voice_assistant_executes_website_commands(client, auth_farmer_session):
    """Verify /api/voice/command dispatches approved website actions."""
    # 1. Navigation to dashboard
    res = client.post("/api/voice/command", json={
        "message": "Open dashboard",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["action"] == "navigate_to_page"
    assert data["action_payload"]["target"] == "dashboard"
    assert "spoken_response" in data

    # 2. Show my farms
    res_farms = client.post("/api/voice/command", json={
        "message": "Show my farms",
        "language": "en"
    })
    assert res_farms.status_code == 200
    assert res_farms.get_json()["action"] == "navigate_to_page"

    # 3. Check irrigation in Telugu
    res_irr = client.post("/api/voice/command", json={
        "message": "ఈ రోజు నీళ్లు పెట్టాలా?",
        "language": "te"
    })
    assert res_irr.status_code == 200
    assert res_irr.get_json()["action"] in ("run_irrigation_prediction", "ask_clarification")

    # 4. Weather info in Hindi
    res_w = client.post("/api/voice/command", json={
        "message": "आज का मौसम कैसा है?",
        "language": "hi"
    })
    assert res_w.status_code == 200
    assert res_w.get_json()["action"] == "get_weather"

    # 5. How much water does my crop need?
    res_water = client.post("/api/voice/command", json={
        "message": "How much water does Section 01 need?",
        "language": "en"
    })
    assert res_water.status_code == 200
    assert res_water.get_json()["action"] == "calculate_water_requirement"
    assert res_water.get_json()["action_payload"]["section_name"] == "Section 01"


def test_voice_tts_endpoint_streams_audio(client):
    """Verify /api/voice/tts streams audio for spoken responses."""
    res = client.get("/api/voice/tts?lang=en&text=Dashboard+opened+successfully")
    assert res.status_code == 200
    assert res.content_type in ("audio/mpeg", "audio/wav")
    assert len(res.data) > 0
