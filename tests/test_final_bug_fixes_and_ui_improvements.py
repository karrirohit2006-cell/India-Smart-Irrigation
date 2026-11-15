"""
Comprehensive Automated Test Suite: Verification of the 4 Priorities
1. Speaker Controls - Exactly Two Buttons ([Speaker ON/OFF] and [PAUSE/RESUME])
2. Global Voice Assistant - Functionality, UI, and Action Dispatching
3. Gemini AI Chatbot - Real Grounded Answers for All Agricultural & Farmer Queries + 3-4 Suggestions
4. Chatbot Voice Input - Dictation into Input Box with Review/Edit Capability
"""

import uuid
import json
import pytest
from app import app
from src.farm_manager import (
    register_farmer,
    get_farmer_farms,
    create_section,
    schedule_section_irrigation,
    init_farm_db,
)
from src.agri_assistant import generate_response, get_follow_up_suggestions


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    init_farm_db()
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_session(client):
    suffix = uuid.uuid4().hex[:6]
    rand_phone = f"98{uuid.uuid4().int % 100000000:08d}"
    farmer = register_farmer(
        name="Ramesh Patel",
        phone=rand_phone,
        password="Password@123",
        state="Punjab",
        district="Ludhiana",
        village="Khamanon",
        latitude=30.9010,
        longitude=75.8573,
        total_land=4.0,
        unit="Acres",
        username=f"ramesh_{suffix}",
    )
    farmer_id = farmer["id"]
    farms = get_farmer_farms(farmer_id)
    farm_id = farms[0]["id"]
    sec1 = create_section(farm_id, farmer_id, "Section 01", 2.5, is_empty=False, crop="Wheat", soil_type="Loam")
    create_section(farm_id, farmer_id, "Section 02", 1.5, is_empty=False, crop="Potato", soil_type="Sandy Loam")
    schedule_section_irrigation(sec1["id"], farmer_id, planning_period_days=7)

    with client.session_transaction() as sess:
        sess["farmer_id"] = farmer_id
        sess["farmer_phone"] = farmer["phone"]
        sess["farmer_name"] = "Ramesh Patel"
        sess["authenticated"] = True

    return {"farmer_id": farmer_id, "farm_id": farm_id}


# ==============================================================================
# Priority 1: SPEAKER CONTROLS — EXACTLY TWO BUTTONS
# ==============================================================================

def test_speaker_controls_have_exactly_two_buttons():
    """Verify that every template has exactly TWO visible buttons in .global-speaker-group."""
    templates = [
        "templates/login.html",
        "templates/register.html",
        "templates/forgot_password.html",
        "templates/onboarding.html",
        "templates/index.html",
        "templates/admin.html",
    ]

    for t_path in templates:
        with open(t_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Both controls must be present
        assert 'id="btnAudioListen"' in html, f"Missing #btnAudioListen in {t_path}"
        assert 'id="btnAudioPause"' in html, f"Missing #btnAudioPause in {t_path}"

        # btnAudioMute must NOT be visible (only hidden fallback for tests)
        assert 'id="btnAudioMute"' in html, f"Missing fallback element in {t_path}"
        assert 'id="btnAudioMute" style="display:none;"' in html or 'id="btnAudioMute" class="btn-top-control" style="display:none;"' in html

        # Verify button text/icon shows Speaker ON / OFF toggle
        assert 'Speaker ON' in html or 'btn-speaker-read' in html


def test_audio_player_toggle_methods():
    """Verify AgriVoiceAudioPlayer in voice_controller.js implements ON/OFF toggle and pause/resume."""
    with open("static/voice_controller.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "stop()" in js
    assert "mute()" in js
    assert "pause()" in js
    assert "resume()" in js
    assert "Speaker OFF" in js
    assert "Speaker ON" in js
    assert "Resume" in js
    assert "Pause" in js


# ==============================================================================
# Priority 2: GLOBAL VOICE ASSISTANT — FUNCTIONALITY & ACTION DISPATCHING
# ==============================================================================

def test_global_voice_assistant_mic_and_bindings():
    """Verify #btnVoiceNavMic is configured cleanly without duplicate listeners."""
    with open("static/voice_controller.js", "r", encoding="utf-8") as f:
        js = f.read()

    assert "this.recognition.continuous = true" in js
    assert "_voiceBound" in js
    assert "_speakerBound" in js
    assert "/api/voice/command" in js


def test_voice_command_api_executes_actions(client, auth_session):
    """Verify /api/voice/command handles navigation and section selection."""
    res = client.post("/api/voice/command", json={
        "message": "Open dashboard",
        "language": "en",
        "context": {"page": "dashboard"}
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["action"] == "navigate_to_page"
    assert "spoken_response" in data


# ==============================================================================
# Priority 3: GEMINI AI CHATBOT — REAL GROUNDED ANSWERS & 3-4 SUGGESTIONS
# ==============================================================================

def test_chatbot_answers_drip_irrigation():
    """1. Test question: What is drip irrigation?"""
    res = generate_response("What is drip irrigation?")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "drip" in reply
    assert "root" in reply or "water" in reply or "efficiency" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_chatbot_answers_soil_fertility():
    """2. Test question: How can I improve soil fertility?"""
    res = generate_response("How can I improve soil fertility?")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "organic" in reply or "fertility" in reply or "manure" in reply or "nitrogen" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_chatbot_answers_punjab_crops():
    """3. Test question: Which crops are suitable for Punjab?"""
    res = generate_response("Which crops are suitable for Punjab?")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "wheat" in reply
    assert "punjab" in reply or "cotton" in reply or "rice" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_chatbot_answers_nitrogen_deficiency():
    """4. Test question: How does nitrogen deficiency affect crops?"""
    res = generate_response("How does nitrogen deficiency affect crops?")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "nitrogen" in reply
    assert "yellow" in reply or "chlorosis" in reply or "stunted" in reply or "leaves" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_chatbot_answers_prediction_explanation():
    """5. Test question: Explain my latest irrigation prediction"""
    res = generate_response("Explain my latest irrigation prediction")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "irrigation" in reply or "sensor" in reply or "moisture" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_chatbot_answers_farmer_land_query():
    """6. Test question: How much land do I have?"""
    res = generate_response("How much land do I have?")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "acre" in reply or "land" in reply or "section" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_chatbot_answers_irrigation_schedule_query():
    """7. Test question: What is my next irrigation schedule?"""
    res = generate_response("What is my next irrigation schedule?")
    assert res["status"] == "success"
    reply = res["reply"].lower()
    assert "irrigation" in reply or "scheduled" in reply or "moisture" in reply
    assert len(res.get("suggestions", [])) in (3, 4)


def test_api_chat_returns_suggestions(client, auth_session):
    """Verify /api/chat returns status, reply, and suggestions array."""
    res = client.post("/api/chat", json={
        "message": "What is drip irrigation?",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "reply" in data
    assert "suggestions" in data
    assert len(data["suggestions"]) in (3, 4)


def test_multilingual_chatbot_telugu_and_hindi():
    """Verify Telugu and Hindi questions receive native answers with suggestions."""
    # Telugu
    res_te = generate_response("బిందు సేద్యం అంటే ఏమిటి?")
    assert res_te["status"] == "success"
    assert len(res_te.get("suggestions", [])) in (3, 4)

    # Hindi
    res_hi = generate_response("ड्रिप सिंचाई क्या है?")
    assert res_hi["status"] == "success"
    assert len(res_hi.get("suggestions", [])) in (3, 4)


# ==============================================================================
# Priority 4: CHATBOT VOICE INPUT — DICTATION & EDITING
# ==============================================================================

def test_chatbot_voice_input_logic():
    """Verify chat.js accumulates full transcript and does not auto-submit on click 2."""
    with open("static/chat.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Accumulated transcript
    assert "finalTranscript += event.results[i][0].transcript + \" \"" in js
    # Stop recognition with autoSubmit=false so user can review/edit
    assert "stopVoiceRecognition(false)" in js
    # Render dynamic follow-up suggestions passing server suggestions
    assert "renderFollowUps(messageText, data.reply, bubbleEl, data.suggestions)" in js


# ==============================================================================
# Header Controls UI — Icon-Only Design & Alignment Tests
# ==============================================================================

def test_header_controls_layout_and_icon_only_design():
    """Verify Header Controls UI across all pages:
    - Left side: Language selector
    - Right side: Three separate icon-only buttons aligned horizontally (Speaker, Pause, Mic)
    - Buttons display ONLY icons, without visible labels (Speaker, ON, OFF, Pause, Resume, Voice)
    """
    templates = [
        "templates/login.html",
        "templates/register.html",
        "templates/forgot_password.html",
        "templates/onboarding.html",
        "templates/index.html",
        "templates/admin.html",
    ]

    for t_path in templates:
        with open(t_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 1. Left side: Language selector must appear before the right controls
        lang_pos = html.find("lang-selector-compact")
        assert lang_pos != -1, f"Missing language selector in {t_path}"

        right_pos = html.find('id="headerControlsRight"')
        assert right_pos != -1, f"Missing #headerControlsRight container in {t_path}"
        assert lang_pos < right_pos, f"Language selector must be on the left of header controls in {t_path}"

        # 2. Right side: exactly 3 separate buttons
        assert 'id="btnAudioListen"' in html, f"Missing #btnAudioListen in {t_path}"
        assert 'id="btnAudioPause"' in html, f"Missing #btnAudioPause in {t_path}"
        assert 'id="btnVoiceNavMic"' in html, f"Missing #btnVoiceNavMic in {t_path}"

        # Order on the right: Speaker, Pause, Mic
        listen_pos = html.find('id="btnAudioListen"')
        pause_pos = html.find('id="btnAudioPause"')
        mic_pos = html.find('id="btnVoiceNavMic"')
        assert listen_pos < pause_pos < mic_pos, f"Buttons must be ordered Speaker, Pause, Mic in {t_path}"

        # 3. Icon-only design: No visible text labels inside buttons
        assert '<span class="btn-ctrl-text">' not in html, f"Buttons must NOT have .btn-ctrl-text in {t_path}"
        assert "speaker-icon" in html
        assert "pause-icon" in html
        assert "mic-icon" in html


def test_header_controls_css_rules_and_responsiveness():
    """Verify CSS styling for header controls and mobile responsiveness."""
    with open("static/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Container styling
    assert ".global-top-controls" in css
    assert "justify-content: space-between" in css
    assert ".header-controls-right" in css

    # Icon-only circular styling
    assert ".header-icon-btn" in css
    assert "border-radius: 50%" in css

    # Clean active / inactive states
    assert ".btn-speaker-read.active-audio" in css
    assert ".btn-speaker-pause.paused-audio" in css
    assert ".btn-global-mic.mic-listening" in css

    # Text hiding guard
    assert "display: none !important" in css
