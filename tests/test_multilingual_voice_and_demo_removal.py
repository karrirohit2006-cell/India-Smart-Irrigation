import json
import re
import pytest
from app import app
from src.farm_manager import (
    init_farm_db,
    register_farmer,
    get_farmer_by_id,
    update_farmer_language,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_01_demo_removal_from_index_and_login_templates():
    """Verify complete removal of evaluation demo switchers and demo banners."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        index_html = f.read()

    with open("templates/login.html", "r", encoding="utf-8") as f:
        login_html = f.read()

    # index.html checks
    assert "btnSwitchFarmerDemo" not in index_html, "Switch Demo Farmer button must be removed from index.html"
    assert "btn-demo-switch" not in index_html, "Demo switch buttons must be removed from profile dropdown"
    assert "EVALUATION DEMO ACCOUNTS:" not in index_html, "Demo accounts header must be removed"
    assert "demo-login-banner" not in index_html, "Demo quick login banner must be removed"

    # login.html checks
    assert "btnQuickFarmerA" not in login_html, "Quick Farmer A demo shortcut must be removed from login.html"
    assert "btnQuickFarmerB" not in login_html, "Quick Farmer B demo shortcut must be removed from login.html"
    assert "demo-bar" not in login_html, "Demo bar container must be removed from login.html"


def test_02_no_cache_headers_prevent_back_button_reentry(client):
    """Verify Cache-Control headers prevent browser Back navigation after logout."""
    res_dash = client.get("/dashboard")
    assert "no-store" in res_dash.headers.get("Cache-Control", ""), "Dashboard must enforce no-store"
    assert "no-cache" in res_dash.headers.get("Cache-Control", "")

    res_onboard = client.get("/onboarding")
    assert "no-store" in res_onboard.headers.get("Cache-Control", ""), "Onboarding must enforce no-store"

    res_me = client.get("/api/auth/me")
    assert "no-store" in res_me.headers.get("Cache-Control", ""), "Auth me API must enforce no-store"


def test_03_sowing_date_removed_from_crop_details_form():
    """Verify that visible sowing date input is removed from dashboard crop details."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        index_html = f.read()

    # Should NOT have visible date input for sowing_date
    assert not re.search(r'<input\s+[^>]*type=["\']date["\'][^>]*id=["\']sowing_date["\']', index_html), \
        "Visible sowing date input (<input type='date' id='sowing_date'>) must not exist on dashboard"

    # Should have hidden input for backward compatibility
    assert '<input type="hidden" id="sowing_date"' in index_html or '<input id="sowing_date" type="hidden"' in index_html, \
        "Hidden input for sowing_date should exist for backward compatibility"

    # Crop stage & age badge should still exist
    assert "calculatedCropAgeBadge" in index_html, "Dynamic crop age badge must remain on dashboard"


def test_04_multilingual_23_languages_persistence(client):
    """Verify API supports and persists all 22 Scheduled Indian Languages + English."""
    all_23_languages = [
        "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok",
        "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat",
        "sd", "ta", "te", "ur", "en"
    ]

    init_farm_db()

    # 1. Register a test farmer
    username = f"langtest_{app.testing}"
    try:
        farmer = register_farmer(
            username=username,
            password="testPassword123",
            name="Language Tester",
            state="Telangana",
            total_land=2.5,
            onboarding_completed=1
        )
    except ValueError:
        farmer = get_farmer_by_id(f"farmer_{username}") or {}

    with client.session_transaction() as sess:
        sess["farmer_id"] = farmer.get("id")

    for lang in all_23_languages:
        # POST language
        res = client.post("/api/farmer/language", json={"language": lang})
        assert res.status_code == 200, f"Failed to set language {lang}"
        data = res.get_json()
        assert data.get("language") == lang

        # GET language
        res_get = client.get("/api/farmer/language")
        assert res_get.status_code == 200
        assert res_get.get_json().get("language") == lang


def test_05_voice_transcribe_and_script_assets(client):
    """Verify voice transcription API and static voice assets exist."""
    # Transcription API endpoint
    res = client.post("/api/voice/transcribe", json={"text": "ఆంధ్రప్రదేశ్", "language": "te"})
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("status") == "success"
    assert data.get("text") == "ఆంధ్రప్రదేశ్"
    assert data.get("language") == "te"

    # Verify i18n.js and voice_controller.js exist
    with open("static/i18n.js", "r", encoding="utf-8") as f:
        i18n_content = f.read()
    assert "SUPPORTED_LANGUAGES" in i18n_content
    assert "I18N_DICTIONARY" in i18n_content
    assert "te" in i18n_content
    assert "hi" in i18n_content
    assert "ur" in i18n_content
    assert "dir: \"rtl\"" in i18n_content

    with open("static/voice_controller.js", "r", encoding="utf-8") as f:
        voice_content = f.read()
    assert "AgriVoiceController" in voice_content
    assert "processVoiceCommand" in voice_content
    assert "SpeechRecognition" in voice_content


def test_06_dashboard_container_width_and_clean_layout():
    """Verify 1240px container layout without charts/graphs."""
    with open("static/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert "max-width: 1240px" in css, "Dashboard and land module must use max-width: 1240px"

    with open("templates/index.html", "r", encoding="utf-8") as f:
        index_html = f.read()

    # No canvas or svg graph elements
    assert "<canvas" not in index_html, "Dashboard must not use graph canvas elements"
    assert "Chart.js" not in index_html, "Dashboard must not use Chart.js"
