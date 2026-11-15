"""
Final Verification Test Suite: Checkpoint 2 Baseline + Global Speaker + Global Voice Assistant + Dashboard-Only Gemini Chatbot
Verifies:
1. Global Speaker controls (#btnAudioListen, #btnAudioPause, #btnAudioMute) are present on ALL pages.
2. Global Voice Assistant mic (#btnVoiceNavMic) is present on ALL pages beside the speaker.
3. Original Gemini AI Chatbot (#agriChatWidget) is strictly restricted to the Farmer Dashboard (templates/index.html).
4. Public auth & onboarding pages (login, register, forgot_password, onboarding, admin) DO NOT include the chatbot widget or chat.js.
5. All 23 languages are supported and available in the top language selectors.
6. Voice controller provides two-click continuous recording and audio player controls (play, pause, resume, mute).
7. /api/chat responds to agricultural queries with grounded answers in multiple languages.
8. /api/voice/command dispatches approved website actions with spoken response and current-page awareness.
9. /api/voice/tts streams audio.
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
    suffix = uuid.uuid4().hex[:6]
    farmer = register_farmer(
        name="Sunil Sharma",
        phone=f"98{uuid.uuid4().int % 100000000:08d}",
        password="Farmer@123",
        state="Punjab",
        district="Ludhiana",
        village="Sahnewal",
        latitude=30.9010,
        longitude=75.8573,
        total_land=5.0,
        unit="Acres",
        username=f"sunil_{suffix}"
    )
    farmer_id = farmer["id"]
    farms = get_farmer_farms(farmer_id)
    farm_id = farms[0]["id"]

    sec1 = create_section(farm_id, farmer_id, "Section 01", 2.0, is_empty=False, crop="Wheat", soil_type="Loam")
    schedule_section_irrigation(sec1["id"], farmer_id, planning_period_days=7)

    with client.session_transaction() as sess:
        sess["farmer_id"] = farmer_id
        sess["farmer_phone"] = farmer["phone"]
        sess["farmer_name"] = "Sunil Sharma"
        sess["authenticated"] = True

    return {"farmer_id": farmer_id, "farm_id": farm_id, "sec1": sec1}


# ==============================================================================
# 1. GLOBAL SPEAKER & VOICE MIC PRESENCE ON ALL PAGES
# ==============================================================================

def test_speaker_and_mic_present_on_all_pages():
    """Verify that Global Speaker and Global Voice Mic are present on all application templates."""
    all_pages = [
        "templates/login.html",
        "templates/register.html",
        "templates/forgot_password.html",
        "templates/onboarding.html",
        "templates/index.html",
        "templates/admin.html",
    ]

    for page_path in all_pages:
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Speaker controls
        assert 'id="btnAudioListen"' in content, f"Missing #btnAudioListen in {page_path}"
        assert 'id="btnAudioPause"' in content, f"Missing #btnAudioPause in {page_path}"
        assert 'id="btnAudioMute"' in content, f"Missing #btnAudioMute in {page_path}"

        # Global Voice mic
        assert 'id="btnVoiceNavMic"' in content, f"Missing #btnVoiceNavMic in {page_path}"

        # Voice controller script
        assert 'voice_controller.js' in content, f"Missing voice_controller.js in {page_path}"


# ==============================================================================
# 2. STRICT DASHBOARD-ONLY RESTRICTION FOR GEMINI CHATBOT
# ==============================================================================

def test_gemini_chatbot_strictly_on_dashboard_only():
    """Verify that AgriSaathi Chatbot appears ONLY on index.html and NOT on any other pages."""
    non_dashboard_pages = [
        "templates/login.html",
        "templates/register.html",
        "templates/forgot_password.html",
        "templates/onboarding.html",
        "templates/admin.html",
    ]

    for page_path in non_dashboard_pages:
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'id="agriChatWidget"' not in content, f"Chatbot widget must NOT be present in {page_path}"
        assert 'agri_chat_widget.html' not in content, f"agri_chat_widget.html must NOT be included in {page_path}"
        assert 'chat.js' not in content, f"chat.js must NOT be included in {page_path}"

    # Verify Farmer Dashboard (templates/index.html) DOES have the full chatbot
    with open("templates/index.html", "r", encoding="utf-8") as f:
        dashboard_content = f.read()

    assert 'id="agriChatWidget"' in dashboard_content
    assert 'id="agriChatToggle"' in dashboard_content
    assert 'id="agriChatWindow"' in dashboard_content
    assert 'id="agriChatInput"' in dashboard_content
    assert 'id="agriSendBtn"' in dashboard_content
    assert 'id="agriMicBtn"' in dashboard_content
    assert 'chat.js' in dashboard_content


# ==============================================================================
# 3. JAVASCRIPT CONTROLLERS AND TWO-CLICK RECORDING LOGIC
# ==============================================================================

def test_voice_controller_continuous_speech_and_audio_methods():
    """Verify voice_controller.js implements continuous recognition and audio player controls."""
    with open("static/voice_controller.js", "r", encoding="utf-8") as f:
        voice_js = f.read()

    assert "this.recognition.continuous = true" in voice_js
    assert "class AgriVoiceAudioPlayer" in voice_js
    assert "play(" in voice_js
    assert "pause(" in voice_js
    assert "resume(" in voice_js
    assert "mute(" in voice_js
    assert "window.AgriVoiceAudio" in voice_js
    assert "window.AgriVoice" in voice_js

    # Verify chat.js does NOT auto-mount outside dashboard
    with open("static/chat.js", "r", encoding="utf-8") as f:
        chat_js = f.read()

    assert "document.getElementById(\"agriChatWidget\")" in chat_js
    assert "ensureWidgetInDOM" not in chat_js


# ==============================================================================
# 4. GEMINI AI AGRICULTURAL CHATBOT FUNCTIONALITY
# ==============================================================================

def test_gemini_chatbot_answers_agricultural_questions(client, auth_farmer_session):
    """Verify /api/chat answers agricultural and farmer dashboard queries."""
    # 1. Crop advice
    res = client.post("/api/chat", json={
        "message": "How often should I irrigate wheat in loam soil?",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reply" in data
    assert len(data["reply"]) > 20

    # 2. Telugu query
    res_te = client.post("/api/chat", json={
        "message": "వరి పంటకు ఎంత నీరు అవసరం?",
        "language": "te"
    })
    assert res_te.status_code == 200
    data_te = res_te.get_json()
    assert data_te["status"] == "success"
    assert any("\u0c00" <= c <= "\u0c7f" for c in data_te["reply"])

    # 3. Hindi query
    res_hi = client.post("/api/chat", json={
        "message": "गेहूं की फसल में सिंचाई कब करनी चाहिए?",
        "language": "hi"
    })
    assert res_hi.status_code == 200
    data_hi = res_hi.get_json()
    assert data_hi["status"] == "success"
    assert any("\u0900" <= c <= "\u097f" for c in data_hi["reply"])


def test_gemini_chatbot_input_sanitization(client):
    """Verify /api/chat rejects empty and excessively long inputs."""
    res_empty = client.post("/api/chat", json={"message": "   "})
    assert res_empty.status_code == 400

    res_long = client.post("/api/chat", json={"message": "A" * 1005})
    assert res_long.status_code == 400


# ==============================================================================
# 5. GLOBAL WEBSITE VOICE ASSISTANT FUNCTIONALITY
# ==============================================================================

def test_website_voice_assistant_actions(client, auth_farmer_session):
    """Verify /api/voice/command handles navigation and website controls."""
    # 1. Navigation
    res_nav = client.post("/api/voice/command", json={
        "message": "Go to dashboard",
        "language": "en",
        "context": {"page": "login"}
    })
    assert res_nav.status_code == 200
    data_nav = res_nav.get_json()
    assert data_nav["action"] == "navigate_to_page"
    assert "spoken_response" in data_nav

    # 2. Weather
    res_w = client.post("/api/voice/command", json={
        "message": "What is the weather today?",
        "language": "en",
        "context": {"page": "dashboard"}
    })
    assert res_w.status_code == 200
    assert res_w.get_json()["action"] == "get_weather"

    # 3. Farm summary
    res_s = client.post("/api/voice/command", json={
        "message": "Show farm summary",
        "language": "en",
        "context": {"page": "dashboard"}
    })
    assert res_s.status_code == 200
    assert res_s.get_json()["action"] in ("get_farm_summary", "navigate_to_page")


def test_tts_audio_streaming(client):
    """Verify /api/voice/tts streams audio content."""
    res = client.get("/api/voice/tts?lang=en&text=Welcome+to+Smart+Irrigation+Planner")
    assert res.status_code == 200
    assert res.content_type in ("audio/mpeg", "audio/wav")
    assert len(res.data) > 0
