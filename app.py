"""
AI Smart Irrigation Planner - Flask Application.
Rebuilt to use the India State-Wise Crop Irrigation Ranges and ML model.
"""

import logging
import os
import sqlite3
import secrets
from math import isfinite
from pathlib import Path
from functools import wraps
from typing import Optional, Dict, Any, List
from datetime import datetime
from dotenv import load_dotenv
import io
import wave
import struct
import math
import hashlib
import urllib.parse
import urllib.request
from flask import Flask, jsonify, request, render_template, session, redirect, Response

# Load environment variables early
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
load_dotenv()

from src.irrigation_service import IrrigationService
from src.agri_assistant import generate_response, AgriAssistantError, validate_chat_history
from src.irrigation_scheduler import (
    init_scheduler_db,
    generate_and_save_schedule,
    get_all_schedules,
    update_schedule_status,
    get_schedule_summary,
)
from src.farm_manager import (
    init_farm_db,
    seed_demo_accounts,
    register_farmer,
    authenticate_farmer,
    get_farmer_by_id,
    get_farmer_farms,
    get_farm_by_id,
    get_farm_sections,
    get_section_by_id,
    get_land_summary,
    create_section,
    update_section,
    delete_section,
    predict_section_irrigation,
    schedule_section_irrigation,
    get_section_schedules,
    update_section_schedule_status,
    get_farmer_combined_calendar,
    update_farmer_onboarding,
    reset_farmer_password_by_phone,
    verify_farmer_password,
    update_farmer_language,
)
from src.admin_manager import (
    init_admin_db,
    bootstrap_super_admin,
    authenticate_admin,
    get_admin_by_id,
    log_admin_action,
    get_admin_dashboard_kpis,
    get_all_farmers_admin,
    get_farmer_details_admin,
    set_farmer_status,
    reset_farmer_password_admin,
    update_farmer_profile_admin,
    get_all_farms_admin,
    get_all_schedules_admin,
    get_admin_weather_overview,
    get_ai_system_status,
    get_admin_audit_logs,
)
from src.passkey_manager import (
    init_passkey_db,
    send_mobile_otp,
    verify_mobile_otp,
    get_rp_id_and_origins,
    generate_passkey_registration_options,
    verify_passkey_registration,
    generate_passkey_authentication_options,
    verify_passkey_authentication,
    get_farmer_registered_devices,
    delete_farmer_passkey,
    rename_farmer_passkey,
    disable_all_farmer_passkeys,
)
from src.weather_service import get_live_weather, reverse_geocode
from src.voice_command_engine import process_voice_command, APPROVED_VOICE_ACTIONS
from src.languages_registry import (
    list_all_languages,
    get_language_capabilities_matrix,
    get_language,
    register_new_language,
)
from src.translation_manager import (
    get_translations,
    get_all_translations,
    get_text,
    reload_translations,
)
from src.voice_providers import (
    get_tts_audio,
    sanitize_speech_text,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app")

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "agrisaathi-farmer-smart-irrigation-2026-key")

# Initialize Irrigation Service, Scheduler DB, Farm DB, Super Admin DB and Passkey DB at startup
irrigation_service = IrrigationService.get_instance()
init_scheduler_db()
init_farm_db()
seed_demo_accounts()
init_admin_db()
bootstrap_super_admin()
init_passkey_db()
logger.info(f"Loaded {len(irrigation_service.get_states())} Indian states. Seeded multi-farmer, Super Admin & WebAuthn database.")


# Landing / Login page: always open Farmer Login for unauthenticated visitors
@app.before_request
def standardize_localhost_domain():
    # Enforce standard http://localhost:5000 for WebAuthn domain compliance during local dev
    if not app.testing and (request.host.startswith("127.0.0.1") or request.host.startswith("0.0.0.0")):
        new_url = request.url.replace("://127.0.0.1", "://localhost", 1).replace("://0.0.0.0", "://localhost", 1)
        return redirect(new_url, code=302)


@app.after_request
def add_cache_headers(response):
    # Prevent browser back button from re-showing authenticated dashboard/onboarding after logout
    if request.path in ("/dashboard", "/onboarding", "/my-farms", "/api/auth/me"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET"])
def home():
    farmer_id = session.get("farmer_id")
    if farmer_id:
        farmer = get_farmer_by_id(farmer_id)
        if farmer and farmer.get("status") == "Active":
            if farmer.get("onboarding_completed"):
                return redirect("/dashboard")
            return redirect("/onboarding")
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register_page():
    farmer_id = session.get("farmer_id")
    if farmer_id:
        farmer = get_farmer_by_id(farmer_id)
        if farmer and farmer.get("status") == "Active":
            if farmer.get("onboarding_completed"):
                return redirect("/dashboard")
            return redirect("/onboarding")
    return render_template("register.html")


@app.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    return render_template("forgot_password.html")


@app.route("/onboarding", methods=["GET"])
def onboarding_page():
    farmer_id = session.get("farmer_id")
    if not farmer_id:
        return redirect("/")
    farmer = get_farmer_by_id(farmer_id)
    if not farmer or farmer.get("status") != "Active":
        session.clear()
        return redirect("/")
    if farmer.get("onboarding_completed"):
        return redirect("/dashboard")
    return render_template("onboarding.html", farmer=farmer)


@app.route("/dashboard", methods=["GET"])
def dashboard_page():
    farmer_id = session.get("farmer_id")
    if not farmer_id:
        return redirect("/")
    farmer = get_farmer_by_id(farmer_id)
    if not farmer or farmer.get("status") != "Active":
        session.clear()
        return redirect("/")
    if not farmer.get("onboarding_completed"):
        return redirect("/onboarding")
    return render_template("index.html", farmer=farmer)


@app.route("/logout", methods=["GET", "POST"])
def logout_handler():
    session.clear()
    return redirect("/")


# Health check: verify that the backend is running
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "project": "AI Smart Irrigation Planner",
        "states_count": len(irrigation_service.get_states()),
        "model_loaded": irrigation_service.model is not None,
    })


# States API: list all 36 Indian states and UTs
@app.route("/api/states", methods=["GET"])
def get_states():
    states = irrigation_service.get_states()
    return jsonify({
        "states": states,
        "total": len(states),
    })


# Crop metadata API: list crops for a given state
@app.route("/api/crops", methods=["GET"])
def get_crops():
    state = request.args.get("state", "").strip()
    if not state:
        # Return all unique crops if no state query provided
        all_states = irrigation_service.get_states()
        return jsonify({
            "error": "Please provide a state parameter, e.g. /api/crops?state=Punjab",
            "available_states": all_states,
        }), 400

    crops = irrigation_service.get_crops_for_state(state)
    if not crops:
        return jsonify({
            "error": f"State '{state}' was not found. Please choose from available states.",
            "crops": [],
            "total": 0,
        }), 404

    return jsonify({
        "state": state,
        "crops": crops,
        "total": len(crops),
    })


# Unified Prediction API: receive data and return model prediction & rule evaluation
@app.route("/predict", methods=["POST"])
@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Please send input as a JSON object."
        }), 400

    try:
        result = irrigation_service.predict(data)
        if result.get("status") == "IRRIGATE":
            crop_name = data.get("crop") or data.get("crop_name") or "Crop"
            state_name = data.get("state") or "Punjab"
            reading = float(data.get("sensor_reading") or 0.0)
            unit = result.get("reading_unit", "%")
            trigger = float(result.get("irrigation_trigger") or 40.0)
            rainfall_7d = float(data.get("rainfall_7d") or 0.0)
            forecast_24h = float(data.get("forecast_24h") or 0.0)
            schedules = generate_and_save_schedule(
                crop=crop_name,
                state=state_name,
                sensor_reading=reading,
                reading_unit=unit,
                trigger=trigger,
                rainfall_7d=rainfall_7d,
                forecast_24h=forecast_24h,
            )
            result["schedules"] = schedules
            result["water_requirement_liters"] = schedules[0]["water_quantity_liters"] if schedules else 450.0
            result["schedule_count"] = len(schedules)
        else:
            result["schedules"] = []
            result["no_irrigation_reason"] = (
                "Current soil conditions are sufficient. Your next irrigation recommendation will be generated when conditions change."
            )
        return jsonify(result), 200
    except ValueError as e:
        logger.warning(f"Validation error in predict: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error",
        }), 400
    except Exception as e:
        logger.exception("Unexpected error during irrigation prediction")
        return jsonify({
            "error": f"Prediction failed: {str(e)}",
            "status": "error",
        }), 500


# Smart Irrigation Schedules API
@app.route("/api/schedules", methods=["GET"])
def get_schedules_endpoint():
    crop = request.args.get("crop")
    schedules = get_all_schedules(crop=crop)
    summary = get_schedule_summary()
    return jsonify({
        "schedules": schedules,
        "summary": summary,
        "total": len(schedules),
    })


@app.route("/api/schedules/generate", methods=["POST"])
def generate_schedule_endpoint():
    data = request.get_json(silent=True) or {}
    crop = data.get("crop", "Wheat")
    state = data.get("state", "Punjab")
    reading = float(data.get("sensor_reading", 30.0))
    unit = data.get("reading_unit", "%")
    trigger = float(data.get("trigger", 40.0))
    rainfall_7d = float(data.get("rainfall_7d", 0.0))
    forecast_24h = float(data.get("forecast_24h", 0.0))

    schedules = generate_and_save_schedule(
        crop=crop,
        state=state,
        sensor_reading=reading,
        reading_unit=unit,
        trigger=trigger,
        rainfall_7d=rainfall_7d,
        forecast_24h=forecast_24h,
    )
    return jsonify({"schedules": schedules, "status": "success"}), 200


@app.route("/api/schedules/<schedule_id>/status", methods=["POST"])
def update_schedule_status_endpoint(schedule_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "Completed")
    skip_reason = data.get("skip_reason")
    success = update_schedule_status(schedule_id, new_status, skip_reason)
    if not success:
        return jsonify({"error": "Schedule not found or update failed.", "status": "error"}), 404
    schedules = get_all_schedules()
    summary = get_schedule_summary()
    return jsonify({
        "status": "success",
        "schedule_id": schedule_id,
        "new_status": new_status,
        "schedules": schedules,
        "summary": summary,
    }), 200


@app.route("/api/schedules/summary", methods=["GET"])
def get_schedule_summary_endpoint():
    summary = get_schedule_summary()
    return jsonify(summary), 200


# ========================================================
# Phase 1: Multi-Farmer Authentication & Profiles
# ========================================================
def get_authenticated_farmer_id() -> Optional[str]:
    """Retrieve logged-in farmer ID from session, header or parameter."""
    fid = session.get("farmer_id")
    if not fid:
        fid = request.headers.get("X-Farmer-Id") or request.args.get("farmer_id")
    if not fid and request.is_json:
        data = request.get_json(silent=True) or {}
        fid = data.get("farmer_id")
    return fid


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    confirm_password = data.get("confirm_password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required.", "status": "error"}), 400

    if "confirm_password" in data and password != confirm_password:
        return jsonify({"error": "Passwords do not match.", "status": "error"}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters long.", "status": "error"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long.", "status": "error"}), 400

    name = data.get("name", "").strip() or username.capitalize()
    phone = data.get("phone", "").strip() or None
    email = data.get("email")

    try:
        farmer = register_farmer(
            username=username,
            password=password,
            name=name,
            phone=phone,
            email=email,
            onboarding_completed=0,
        )
        session["farmer_id"] = farmer["id"]
        return jsonify({
            "status": "success",
            "message": "Farmer account created successfully.",
            "farmer": farmer,
            "offer_passkey": True,
            "redirect": "/onboarding",
        }), 201
    except ValueError as ve:
        return jsonify({"error": str(ve), "status": "error"}), 409
    except sqlite3.IntegrityError:
        return jsonify({"error": f"The username '{username}' is already taken. Please choose another username.", "status": "error"}), 409
    except Exception as e:
        logger.exception("Registration failed")
        return jsonify({"error": f"Registration failed: {str(e)}", "status": "error"}), 500


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or data.get("identifier") or "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Username and password are required.", "status": "error"}), 400

    farmer = authenticate_farmer(username, password)
    if not farmer:
        return jsonify({"error": "Invalid username or password.", "status": "error"}), 401

    if farmer.get("status") == "Suspended":
        reason = farmer.get("suspend_reason") or "Administrative decision."
        return jsonify({
            "error": f"Your farmer account has been suspended by the administrator. Reason: {reason}",
            "status": "error",
            "suspended": True,
        }), 403

    session["farmer_id"] = farmer["id"]
    redirect_url = "/dashboard" if farmer.get("onboarding_completed") else "/onboarding"
    return jsonify({"status": "success", "farmer": farmer, "redirect": redirect_url}), 200


@app.route("/api/auth/demo-login", methods=["POST"])
def auth_demo_login():
    """One-click instant login for evaluation/demonstration."""
    data = request.get_json(silent=True) or {}
    demo_type = data.get("demo_user", "farmer_a").lower()
    username = "ramesh" if demo_type in ("farmer_a", "a") else "suresh"
    farmer = authenticate_farmer(username, "farmer123")
    if not farmer:
        seed_demo_accounts()
        farmer = authenticate_farmer(username, "farmer123")
    if farmer:
        if farmer.get("status") == "Suspended":
            return jsonify({
                "error": "This demo account has been suspended by the administrator.",
                "status": "error",
                "suspended": True,
            }), 403
        session["farmer_id"] = farmer["id"]
        return jsonify({"status": "success", "farmer": farmer, "demo_type": demo_type, "redirect": "/dashboard"}), 200
    return jsonify({"error": "Demo account could not be initialized.", "status": "error"}), 500


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully.", "redirect": "/"}), 200


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"authenticated": False, "error": "Not authenticated"}), 401

    farmer = get_farmer_by_id(farmer_id)
    if not farmer:
        session.pop("farmer_id", None)
        return jsonify({"authenticated": False, "error": "Farmer profile not found"}), 404

    if farmer.get("status") == "Suspended":
        session.pop("farmer_id", None)
        return jsonify({
            "authenticated": False,
            "error": "Your farmer account has been suspended by the administrator.",
            "suspended": True,
        }), 403

    farms = get_farmer_farms(farmer_id)
    primary_farm = farms[0] if farms else None
    land_summary = get_land_summary(primary_farm["id"], farmer_id) if primary_farm else None

    is_impersonating = bool(session.get("impersonating_admin_id"))
    admin_username = session.get("impersonating_admin_username")

    devices = get_farmer_registered_devices(farmer_id)

    return jsonify({
        "authenticated": True,
        "farmer": farmer,
        "farms": farms,
        "primary_farm": primary_farm,
        "land_summary": land_summary,
        "is_impersonating": is_impersonating,
        "admin_username": admin_username,
        "has_passkeys": len(devices) > 0,
        "passkeys_count": len(devices),
        "devices": devices,
    }), 200


VALID_LANGUAGES = {
    "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok",
    "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat",
    "sd", "ta", "te", "ur", "en"
}


@app.route("/api/farmer/language", methods=["GET", "POST"])
def farmer_language():
    """Get or persist farmer preferred language across sessions and devices."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        lang = str(data.get("language", "en")).strip().lower()
        if lang not in VALID_LANGUAGES:
            lang = "en"
        session["language"] = lang
        farmer_id = get_authenticated_farmer_id()
        if farmer_id:
            update_farmer_language(farmer_id, lang)
        return jsonify({"status": "success", "language": lang}), 200
    else:
        lang = session.get("language")
        farmer_id = get_authenticated_farmer_id()
        if farmer_id and not lang:
            farmer = get_farmer_by_id(farmer_id)
            if farmer:
                lang = farmer.get("preferred_language")
        return jsonify({"status": "success", "language": lang or "en"}), 200


@app.route("/api/languages", methods=["GET"])
def get_languages_list():
    """Returns the full list of all 23 supported languages (22 Indian scheduled + English)."""
    return jsonify({"status": "success", "languages": list_all_languages()}), 200


@app.route("/api/languages/capabilities", methods=["GET"])
def get_language_capabilities():
    """
    Transparent Language Capability Matrix.
    Provides STT, TTS, script family, direction (LTR/RTL), and provider status for all 23 languages.
    """
    return jsonify({"status": "success", "capabilities": get_language_capabilities_matrix()}), 200


@app.route("/api/translations/<lang>", methods=["GET"])
def get_language_translations(lang: str):
    """Returns the complete JSON dictionary for the specified language."""
    lang_clean = lang.strip().lower()
    translations = get_translations(lang_clean)
    if not translations:
        translations = get_translations("en")
    return jsonify({"status": "success", "language": lang_clean, "translations": translations}), 200


@app.route("/api/voice/tts", methods=["GET", "POST"])
def voice_tts():
    """
    Multilingual Text-to-Speech audio provider.
    Provides native speech audio for all 23 languages using composite voice provider.
    Sanitizes credentials and returns cached MP3 or offline waveform.
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        text = str(data.get("text", "")).strip()
        lang = str(data.get("lang") or data.get("language") or "en").strip().lower()
    else:
        text = str(request.args.get("text", "")).strip()
        lang = str(request.args.get("lang") or request.args.get("language") or "en").strip().lower()

    if not text:
        return jsonify({"error": "Text parameter is required."}), 400

    if lang not in VALID_LANGUAGES:
        lang = "en"

    audio_bytes, mime_type, _, _ = get_tts_audio(text, lang)
    return Response(audio_bytes, mimetype=mime_type, status=200)


@app.route("/api/voice/command", methods=["POST"])
def voice_command_endpoint():
    """
    Secure voice-controlled website action dispatcher.
    Parses natural speech commands, maps to whitelisted website actions, validates farmer permissions,
    and returns structured action payload along with localized verbal response.
    """
    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or data.get("text") or "").strip()
    language = str(data.get("language") or "en").strip().lower()
    if language not in VALID_LANGUAGES and language != "auto":
        language = "en"

    if not message:
        return jsonify({"error": "Voice command text cannot be empty.", "status": "error"}), 400

    context = data.get("context") or {}
    history = data.get("history") or []
    farmer_id = get_authenticated_farmer_id()
    if farmer_id:
        context["farmer_id"] = farmer_id

    try:
        # 1. Process voice command via VoiceCommandEngine
        result = process_voice_command(
            farmer_id=farmer_id or "",
            raw_text=message,
            language=language if language != "auto" else "en",
            context=context,
        )

        # 2. If it's a general question, run through Gemini / Grounded knowledge engine
        if result.get("action") == "general_query":
            try:
                gen_res = generate_response(
                    prompt=message,
                    context=context,
                    language=language,
                    history=history,
                )
                result["spoken_response"] = gen_res["reply"]
                result["display_text"] = gen_res["reply"]
                result["model"] = gen_res.get("model", "")
            except Exception as e:
                logger.warning(f"Fallback generation for general query: {e}")

        # Attach transparent language capability metadata
        lang_def = get_language(language if language != "auto" else "en")
        if lang_def:
            result["language_capability"] = {
                "code": lang_def.code,
                "name": lang_def.name,
                "stt_supported": lang_def.stt_supported,
                "tts_supported": lang_def.tts_supported,
                "direction": lang_def.direction,
                "provider_notes": lang_def.provider_notes,
            }

        logger.info(f"Voice command executed: farmer={farmer_id}, action={result.get('action')}, lang={language}")
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Voice command dispatcher error: {e}")
        return jsonify({
            "status": "error",
            "error": "Unable to process voice command at this time. Please try speaking again."
        }), 500


@app.route("/api/voice/action/execute", methods=["POST"])
def voice_action_execute_endpoint():
    """
    Directly execute a confirmed website action securely on the Flask backend.
    Enforces farmer-level data isolation and validates inputs.
    """
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"status": "error", "error": "Authentication required."}), 401

    data = request.get_json(silent=True) or {}
    action = str(data.get("action", "")).strip()
    payload = data.get("payload") or {}

    if action not in APPROVED_VOICE_ACTIONS:
        return jsonify({"status": "error", "error": f"Unauthorized action: {action}"}), 400

    try:
        if action == "remove_land_section":
            sec_id = payload.get("section_id")
            if not sec_id:
                return jsonify({"status": "error", "error": "Section ID required."}), 400
            success = delete_section(sec_id, farmer_id)
            return jsonify({"status": "success", "action": action, "success": success}), 200

        elif action == "update_irrigation_status":
            sched_id = payload.get("schedule_id")
            new_status = payload.get("status", "Completed")
            if not sched_id:
                return jsonify({"status": "error", "error": "Schedule ID required."}), 400
            success = update_section_schedule_status(sched_id, farmer_id, new_status)
            return jsonify({"status": "success", "action": action, "status": new_status, "success": success}), 200

        elif action == "add_land_section":
            farm_id = payload.get("farm_id")
            if not farm_id:
                farms = get_farmer_farms(farmer_id)
                farm_id = farms[0]["id"] if farms else None
            if not farm_id:
                return jsonify({"status": "error", "error": "Farm not found."}), 404
            name = payload.get("name", "New Section")
            area = float(payload.get("area_acres", 0.5))
            crop = payload.get("crop", "Wheat")
            is_empty = bool(payload.get("is_empty", crop == "Empty"))
            sec = create_section(farm_id, farmer_id, name, area, is_empty=is_empty, crop=crop)
            return jsonify({"status": "success", "action": action, "section": sec}), 200

        elif action == "edit_land_section":
            sec_id = payload.get("section_id")
            if not sec_id:
                return jsonify({"status": "error", "error": "Section ID required."}), 400
            sec = update_section(sec_id, farmer_id, payload)
            return jsonify({"status": "success", "action": action, "section": sec}), 200

        return jsonify({"status": "success", "action": action}), 200
    except Exception as e:
        logger.error(f"Voice action execution error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 400


@app.route("/api/voice/assistant", methods=["POST"])
def voice_assistant_endpoint():
    """
    Dedicated voice assistant endpoint.
    Processes voice command text or audio transcript, checks for actionable website commands,
    executes them, and returns spoken reply with action payload.
    """
    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or data.get("text") or "").strip()
    language = str(data.get("language") or "en").strip().lower()
    if language not in VALID_LANGUAGES and language != "auto":
        language = "auto"

    if not message:
        return jsonify({"error": "Voice command cannot be empty.", "status": "error"}), 400

    context = data.get("context") or {}
    history = data.get("history") or []
    farmer_id = get_authenticated_farmer_id()
    if farmer_id:
        context["farmer_id"] = farmer_id

    try:
        # Check if this is an actionable website voice command
        cmd_res = process_voice_command(
            farmer_id=farmer_id or "",
            raw_text=message,
            language=language if language != "auto" else "en",
            context=context,
        )

        if cmd_res.get("action") != "general_query":
            return jsonify({
                "status": "success",
                "reply": cmd_res.get("spoken_response") or cmd_res.get("display_text"),
                "spoken_response": cmd_res.get("spoken_response"),
                "action": cmd_res.get("action"),
                "action_payload": cmd_res.get("action_payload", {}),
                "requires_confirmation": cmd_res.get("requires_confirmation", False),
                "confirmation_prompt": cmd_res.get("confirmation_prompt"),
                "language": language,
                "tool_executed": True,
            }), 200

        # General agronomic question: use Gemini / Grounded knowledge engine
        result = generate_response(
            prompt=message,
            context=context,
            language=language,
            history=history,
        )
        return jsonify({
            "status": "success",
            "reply": result["reply"],
            "spoken_response": result["reply"],
            "model": result.get("model", ""),
            "language": language,
            "tool_executed": result.get("tool_executed", False),
            "tool_calls": result.get("tool_calls", [])
        }), 200
    except Exception as e:
        logger.error(f"Voice assistant processing error: {e}")
        return jsonify({
            "status": "error",
            "error": "Unable to process voice command at this time. Please try speaking again."
        }), 500


@app.route("/api/voice/transcribe", methods=["POST"])
def voice_transcribe():
    """
    Multilingual speech audio transcription fallback endpoint.
    Accepts audio data / simulated speech transcript and returns recognized text.
    """
    data = request.get_json(silent=True) or {}
    lang = str(data.get("language", "en")).strip().lower()
    if lang not in VALID_LANGUAGES:
        lang = "en"
    audio_text = str(data.get("audio") or data.get("text") or "").strip()
    return jsonify({
        "status": "success",
        "text": audio_text,
        "language": lang
    }), 200


# ========================================================
# Phase 11: WebAuthn Passkeys & Mobile OTP Passwordless Engine
# ========================================================
@app.route("/api/auth/otp/send", methods=["POST"])
def auth_otp_send():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "").strip()
    purpose = data.get("purpose", "login").strip().lower()
    if not phone:
        return jsonify({"error": "Mobile phone number is required.", "status": "error"}), 400

    res = send_mobile_otp(phone, purpose=purpose)
    if not res.get("success"):
        status_code = 403 if res.get("suspended") else (409 if res.get("account_exists") else 400)
        return jsonify(res), status_code
    return jsonify(res), 200


@app.route("/api/auth/otp/verify", methods=["POST"])
def auth_otp_verify():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "").strip()
    otp = data.get("otp", "").strip()
    purpose = data.get("purpose", "login").strip().lower()

    if not phone or not otp:
        return jsonify({"error": "Mobile phone number and OTP code are required.", "status": "error"}), 400

    success, message, farmer = verify_mobile_otp(phone, otp, purpose=purpose)
    if not success:
        return jsonify({"error": message, "status": "error"}), 400

    if not farmer:
        return jsonify({"error": "Farmer account not found for this mobile number.", "status": "error"}), 404

    if farmer.get("status") == "Suspended":
        return jsonify({
            "error": "Your farmer account has been suspended by the administrator.",
            "status": "error",
            "suspended": True,
        }), 403

    session["farmer_id"] = farmer["id"]
    devices = get_farmer_registered_devices(farmer["id"])
    redirect_target = "/dashboard" if farmer.get("onboarding_completed") else "/onboarding"

    return jsonify({
        "status": "success",
        "message": message,
        "farmer": farmer,
        "redirect": redirect_target,
        "has_passkeys": len(devices) > 0,
        "passkeys_count": len(devices),
        "offer_passkey": len(devices) == 0,
    }), 200


@app.route("/api/auth/register-with-otp", methods=["POST"])
def auth_register_with_otp():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    otp = data.get("otp", "").strip()
    username = data.get("username", "").strip() or None
    password = data.get("password", "").strip()
    confirm_password = data.get("confirm_password", "").strip()

    if not name or not phone or not otp:
        return jsonify({"error": "Name, mobile number and OTP verification code are required.", "status": "error"}), 400

    if password:
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters long.", "status": "error"}), 400
        if confirm_password and password != confirm_password:
            return jsonify({"error": "Passwords do not match.", "status": "error"}), 400
    else:
        password = f"passkey_farmer_{secrets.token_hex(16)}"

    success, message, _ = verify_mobile_otp(phone, otp, purpose="register")
    if not success:
        return jsonify({"error": message, "status": "error"}), 400

    email = data.get("email")
    state = data.get("state", "").strip()
    district = data.get("district")
    village = data.get("village")
    latitude = float(data.get("latitude")) if data.get("latitude") is not None else None
    longitude = float(data.get("longitude")) if data.get("longitude") is not None else None
    total_land = float(data.get("total_land", 0.0))
    unit = data.get("unit", "Acres")

    try:
        farmer = register_farmer(
            name=name,
            phone=phone,
            password=password,
            email=email,
            username=username,
            state=state,
            district=district,
            village=village,
            latitude=latitude,
            longitude=longitude,
            total_land=total_land,
            unit=unit,
            onboarding_completed=0,
        )
        session["farmer_id"] = farmer["id"]
        return jsonify({
            "status": "success",
            "message": "Account created successfully with verified mobile number.",
            "farmer": farmer,
            "offer_passkey": True,
            "redirect": "/onboarding",
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "A farmer with this phone number, username, or email is already registered.", "status": "error"}), 409
    except Exception as e:
        logger.exception("Registration with OTP failed")
        return jsonify({"error": f"Registration failed: {str(e)}", "status": "error"}), 500


@app.route("/api/auth/forgot-password/reset", methods=["POST"])
def auth_forgot_password_reset():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "").strip()
    otp = data.get("otp", "").strip()
    new_password = data.get("new_password", "").strip()
    confirm_password = data.get("confirm_password", "").strip()

    if not phone or not otp or not new_password:
        return jsonify({"error": "Mobile number, OTP code and new password are required.", "status": "error"}), 400

    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long.", "status": "error"}), 400

    if confirm_password and new_password != confirm_password:
        return jsonify({"error": "Passwords do not match.", "status": "error"}), 400

    success, message, _ = verify_mobile_otp(phone, otp, purpose="forgot_password")
    if not success:
        return jsonify({"error": message, "status": "error"}), 400

    ok = reset_farmer_password_by_phone(phone, new_password)
    if not ok:
        return jsonify({"error": "Could not reset password. Account not found.", "status": "error"}), 404

    return jsonify({
        "status": "success",
        "message": "Password reset successfully. Please log in with your new password.",
        "redirect": "/",
    }), 200


@app.route("/api/farmer/onboarding", methods=["POST"])
def api_farmer_onboarding():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required. Please log in first.", "status": "error"}), 401

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    state = data.get("state", "").strip()
    if not name or not state:
        return jsonify({"error": "Farmer name and State are required.", "status": "error"}), 400

    district = data.get("district", "").strip() or None
    village = data.get("village", "").strip() or None
    latitude = float(data.get("latitude")) if data.get("latitude") is not None else None
    longitude = float(data.get("longitude")) if data.get("longitude") is not None else None
    total_land = float(data.get("total_land", 1.0))
    unit = data.get("unit", "Acres")
    sections = data.get("sections", [])

    try:
        res = update_farmer_onboarding(
            farmer_id=farmer_id,
            name=name,
            state=state,
            district=district,
            village=village,
            latitude=latitude,
            longitude=longitude,
            total_land=total_land,
            unit=unit,
            sections=sections,
        )
        return jsonify({
            "status": "success",
            "message": "Onboarding completed successfully.",
            "redirect": "/dashboard",
            "details": res,
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve), "status": "error"}), 400
    except Exception as e:
        logger.exception("Onboarding processing failed")
        return jsonify({"error": f"Failed to complete onboarding: {str(e)}", "status": "error"}), 500


@app.route("/api/auth/passkey/register-options", methods=["POST"])
def passkey_register_options():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Please log in first to register a biometric passkey.", "authenticated": False}), 401

    rp_id, _ = get_rp_id_and_origins(request_host=request.host, request_origin=request.origin)
    try:
        res = generate_passkey_registration_options(farmer_id, rp_id=rp_id, rp_name="AgroSmart Irrigation")
        session["webauthn_reg_challenge"] = res["challenge_b64"]
        session["webauthn_reg_farmer_id"] = farmer_id
        return res["options"], 200, {"Content-Type": "application/json"}
    except Exception as e:
        logger.exception("Failed to generate registration options: %s", e)
        return jsonify({"error": f"Failed to generate passkey options: {str(e)}"}), 500


@app.route("/api/auth/passkey/register-verify", methods=["POST"])
def passkey_register_verify():
    expected_challenge = session.get("webauthn_reg_challenge")
    farmer_id = session.get("webauthn_reg_farmer_id") or get_authenticated_farmer_id()
    if not expected_challenge or not farmer_id:
        return jsonify({"error": "Registration session expired or missing challenge. Please try again."}), 400

    data = request.get_json(silent=True) or {}
    credential = data.get("credential") or data
    device_name = data.get("device_name")
    if not device_name:
        ua = request.headers.get("User-Agent", "")
        if "Android" in ua:
            device_name = "Android Biometric Sensor"
        elif "iPhone" in ua or "iPad" in ua:
            device_name = "Apple Face ID / Touch ID"
        elif "Windows" in ua:
            device_name = "Windows Hello Authenticator"
        elif "Macintosh" in ua:
            device_name = "Mac Touch ID"
        else:
            device_name = "Biometric Passkey Device"

    rp_id, allowed_origins = get_rp_id_and_origins(request_host=request.host, request_origin=request.origin)

    try:
        res = verify_passkey_registration(
            farmer_id=farmer_id,
            credential_data=credential,
            expected_challenge_b64=expected_challenge,
            expected_rp_id=rp_id,
            allowed_origins=allowed_origins,
            device_name=device_name,
        )
        session.pop("webauthn_reg_challenge", None)
        session.pop("webauthn_reg_farmer_id", None)
        session["farmer_id"] = farmer_id
        return jsonify({
            "status": "success",
            "message": "Face/Fingerprint Login successfully enabled on this device!",
            "credential_id": res["credential_id"],
            "device_name": res["device_name"],
        }), 200
    except Exception as e:
        logger.exception("Passkey registration verification failed: %s", e)
        return jsonify({"error": f"Biometric passkey registration failed: {str(e)}"}), 400


@app.route("/api/auth/passkey/login-options", methods=["POST"])
def passkey_login_options():
    data = request.get_json(silent=True) or {}
    username = data.get("username") or data.get("identifier")
    phone = data.get("phone")
    rp_id, _ = get_rp_id_and_origins(request_host=request.host, request_origin=request.origin)

    try:
        res = generate_passkey_authentication_options(rp_id=rp_id, username=username, phone=phone)
        session["webauthn_auth_challenge"] = res["challenge_b64"]
        return res["options"], 200, {"Content-Type": "application/json"}
    except Exception as e:
        logger.exception("Failed to generate authentication options: %s", e)
        return jsonify({"error": f"Failed to generate biometric login options: {str(e)}"}), 500


@app.route("/api/auth/passkey/login-verify", methods=["POST"])
def passkey_login_verify():
    expected_challenge = session.get("webauthn_auth_challenge")
    if not expected_challenge:
        return jsonify({"error": "Biometric authentication session expired. Please try again."}), 400

    data = request.get_json(silent=True) or {}
    credential = data.get("credential") or data
    rp_id, allowed_origins = get_rp_id_and_origins(request_host=request.host, request_origin=request.origin)

    res = verify_passkey_authentication(
        credential_data=credential,
        expected_challenge_b64=expected_challenge,
        expected_rp_id=rp_id,
        allowed_origins=allowed_origins,
    )

    if not res.get("success"):
        status_code = 403 if res.get("suspended") else 401
        return jsonify(res), status_code

    session.pop("webauthn_auth_challenge", None)
    farmer = res["farmer"]
    session["farmer_id"] = farmer["id"]
    redirect_target = "/dashboard" if farmer.get("onboarding_completed") else "/onboarding"

    return jsonify({
        "status": "success",
        "message": "Biometric authentication successful.",
        "farmer": farmer,
        "device_name": res.get("device_name"),
        "redirect": redirect_target,
    }), 200


@app.route("/api/auth/passkey/devices", methods=["GET"])
def passkey_list_devices():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    devices = get_farmer_registered_devices(farmer_id)
    return jsonify({"devices": devices, "total": len(devices)}), 200


@app.route("/api/auth/passkey/devices/<credential_id>", methods=["DELETE"])
def passkey_delete_device(credential_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json(silent=True) or {}
    password = data.get("password", "").strip()
    if not password:
        return jsonify({"error": "Password confirmation is required to revoke a biometric device.", "status": "error"}), 400

    if not verify_farmer_password(farmer_id, password):
        return jsonify({"error": "Incorrect password. Cannot revoke device.", "status": "error"}), 401

    success = delete_farmer_passkey(farmer_id, credential_id)
    if not success:
        return jsonify({"error": "Device passkey not found or already deleted."}), 404
    return jsonify({"status": "success", "message": "Biometric device passkey removed."}), 200


@app.route("/api/auth/passkey/disable", methods=["POST"])
def passkey_disable_all():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json(silent=True) or {}
    password = data.get("password", "").strip()
    if not password:
        return jsonify({"error": "Password confirmation is required to disable Face Lock.", "status": "error"}), 400

    if not verify_farmer_password(farmer_id, password):
        return jsonify({"error": "Incorrect password. Cannot disable Face Lock.", "status": "error"}), 401

    count = disable_all_farmer_passkeys(farmer_id)
    return jsonify({
        "status": "success",
        "message": "Face Lock has been disabled and all registered passkeys removed.",
        "removed_count": count
    }), 200


@app.route("/api/auth/passkey/devices/<credential_id>", methods=["PUT"])
def passkey_rename_device(credential_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    new_name = data.get("device_name") or data.get("name")
    if not new_name:
        return jsonify({"error": "Device name is required."}), 400
    success = rename_farmer_passkey(farmer_id, credential_id, new_name)
    if not success:
        return jsonify({"error": "Device passkey not found."}), 404
    return jsonify({"status": "success", "message": "Device renamed successfully."}), 200


# ========================================================
# Phase 2 & 5: Geocoding & Live Weather Integration
# ========================================================
@app.route("/api/location/reverse", methods=["GET"])
def location_reverse():
    try:
        lat = float(request.args.get("lat", 30.9010))
        lon = float(request.args.get("lon", 75.8573))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid latitude or longitude."}), 400

    info = reverse_geocode(lat, lon)
    return jsonify(info), 200


@app.route("/api/weather/live", methods=["GET"])
def weather_live():
    try:
        lat = float(request.args.get("lat", 30.9010))
        lon = float(request.args.get("lon", 75.8573))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid coordinates."}), 400

    w = get_live_weather(lat, lon)
    return jsonify(w), 200


# ========================================================
# Phase 3 & 4: Farms & Land Section Management
# ========================================================
@app.route("/api/farms", methods=["GET"])
def list_farms():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    farms = get_farmer_farms(farmer_id)
    return jsonify({"farms": farms, "total": len(farms)}), 200


@app.route("/api/farms/<farm_id>/sections", methods=["GET"])
def list_farm_sections(farm_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401

    sections = get_farm_sections(farm_id, farmer_id)
    summary = get_land_summary(farm_id, farmer_id)
    return jsonify({
        "farm_id": farm_id,
        "sections": sections,
        "summary": summary,
        "total_sections": len(sections),
    }), 200


@app.route("/api/farms/<farm_id>/sections", methods=["POST"])
def add_farm_section(farm_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401

    data = request.get_json(silent=True) or {}
    name = data.get("name", "Section").strip()
    try:
        area = float(data.get("area_acres", 0.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid land area."}), 400

    is_empty = bool(data.get("is_empty", False))
    crop = data.get("crop")
    crop_variety = data.get("crop_variety")
    sowing_date = data.get("sowing_date")
    soil_type = data.get("soil_type", "Loamy")
    soil_moisture = float(data.get("soil_moisture", 35.0))
    soil_temp = float(data.get("soil_temp", 22.0))
    air_temp = float(data.get("air_temp", 26.0))
    humidity = float(data.get("humidity", 55.0))
    rainfall_7d = float(data.get("rainfall_7d", 0.0))
    forecast_24h = float(data.get("forecast_24h", 0.0))

    try:
        sec = create_section(
            farm_id=farm_id,
            farmer_id=farmer_id,
            name=name,
            area_acres=area,
            is_empty=is_empty,
            crop=crop,
            crop_variety=crop_variety,
            sowing_date=sowing_date,
            soil_type=soil_type,
            soil_moisture=soil_moisture,
            soil_temp=soil_temp,
            air_temp=air_temp,
            humidity=humidity,
            rainfall_7d=rainfall_7d,
            forecast_24h=forecast_24h,
        )
        summary = get_land_summary(farm_id, farmer_id)
        return jsonify({"status": "success", "section": sec, "summary": summary}), 201
    except ValueError as e:
        return jsonify({"error": str(e), "status": "error"}), 400
    except Exception as e:
        logger.exception("Failed to create section")
        return jsonify({"error": f"Failed to create section: {str(e)}"}), 500


@app.route("/api/sections/<section_id>", methods=["GET"])
def get_section_details(section_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    sec = get_section_by_id(section_id, farmer_id)
    if not sec:
        return jsonify({"error": "Section not found."}), 404
    schedules = get_section_schedules(section_id, farmer_id)
    return jsonify({"section": sec, "schedules": schedules}), 200


@app.route("/api/sections/<section_id>", methods=["PUT"])
def update_section_details(section_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    try:
        sec = update_section(section_id, farmer_id, data)
        summary = get_land_summary(sec["farm_id"], farmer_id)
        return jsonify({"status": "success", "section": sec, "summary": summary}), 200
    except ValueError as e:
        return jsonify({"error": str(e), "status": "error"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to update section: {str(e)}"}), 500


@app.route("/api/sections/<section_id>", methods=["DELETE"])
def delete_section_endpoint(section_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    sec = get_section_by_id(section_id, farmer_id)
    if not sec:
        return jsonify({"error": "Section not found."}), 404
    farm_id = sec["farm_id"]
    delete_section(section_id, farmer_id)
    summary = get_land_summary(farm_id, farmer_id)
    return jsonify({"status": "success", "summary": summary}), 200


# ========================================================
# Phase 6 & 7: Section-Wise Prediction & Planning
# ========================================================
@app.route("/api/sections/<section_id>/predict", methods=["POST"])
def predict_section_endpoint(section_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    try:
        pred = predict_section_irrigation(section_id, farmer_id, override_data=data)
        return jsonify(pred), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Section prediction failed")
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500


@app.route("/api/sections/<section_id>/schedule", methods=["POST"])
def schedule_section_endpoint(section_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    start_date = data.get("start_date")
    planning_period = int(data.get("planning_period_days", 7))
    forecast_24h = float(data.get("forecast_24h", 0.0))

    try:
        schedules = schedule_section_irrigation(
            section_id=section_id,
            farmer_id=farmer_id,
            start_date=start_date,
            planning_period_days=planning_period,
            forecast_24h=forecast_24h,
        )
        return jsonify({"status": "success", "schedules": schedules, "count": len(schedules)}), 200
    except Exception as e:
        logger.exception("Scheduling failed")
        return jsonify({"error": f"Scheduling failed: {str(e)}"}), 500


@app.route("/api/sections/<section_id>/schedules", methods=["GET"])
def get_section_schedules_endpoint(section_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    schedules = get_section_schedules(section_id, farmer_id)
    return jsonify({"schedules": schedules, "total": len(schedules)}), 200


@app.route("/api/sections/<section_id>/schedules/<schedule_id>/status", methods=["POST"])
def update_section_schedule_status_endpoint(section_id, schedule_id):
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "Completed")
    skip_reason = data.get("skip_reason")
    forecast_24h = float(data.get("forecast_24h", 0.0))

    result = update_section_schedule_status(
        schedule_id=schedule_id,
        farmer_id=farmer_id,
        new_status=new_status,
        skip_reason=skip_reason,
        forecast_24h=forecast_24h,
    )
    if not result.get("success"):
        return jsonify(result), 400

    schedules = get_section_schedules(section_id, farmer_id)
    result["schedules"] = schedules
    return jsonify(result), 200


# ========================================================
# Phase 9: Global Combined Farmer Calendar View
# ========================================================
@app.route("/api/farmer/calendar", methods=["GET"])
def get_combined_calendar_endpoint():
    farmer_id = get_authenticated_farmer_id()
    if not farmer_id:
        return jsonify({"error": "Authentication required."}), 401

    now = datetime.now()
    year = int(request.args.get("year", now.year))
    month = int(request.args.get("month", now.month))

    cal = get_farmer_combined_calendar(farmer_id, year, month)
    return jsonify(cal), 200


# Chat API: receive farmer query and return AgriSaathi response from Gemini or Website Action Dispatcher
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Please send input as a JSON object."
        }), 400

    raw_message = data.get("message")
    if not raw_message or not isinstance(raw_message, str) or not raw_message.strip():
        return jsonify({
            "error": "Message cannot be empty."
        }), 400

    message = raw_message.strip()
    if len(message) > 1000:
        return jsonify({
            "error": "Message is too long. Please limit your question to 1000 characters."
        }), 400

    language = str(data.get("language", "auto")).strip().lower()
    if language not in VALID_LANGUAGES and language != "auto":
        language = "auto"

    context = data.get("context")
    if not isinstance(context, dict):
        context = {}
    farmer_id = context.get("farmer_id") or get_authenticated_farmer_id()
    if farmer_id:
        context["farmer_id"] = farmer_id

    raw_history = data.get("history")
    validated_history = validate_chat_history(raw_history)

    # 1. Process voice / text command via VoiceCommandEngine
    # If the user issued a website action (navigation, section management, irrigation run, form fill, etc.),
    # dispatch it and return structured action payload with verbal confirmation.
    try:
        cmd_result = process_voice_command(
            farmer_id=farmer_id or "",
            raw_text=message,
            language=language if language != "auto" else "en",
            context=context,
        )
        if cmd_result and cmd_result.get("status") in ("success", "pending_confirmation") and cmd_result.get("action") not in ("general_query", "get_farm_summary", None):
            reply_text = cmd_result.get("confirmation_prompt") or cmd_result.get("spoken_response") or cmd_result.get("display_text") or "Command executed."
            return jsonify({
                "status": "success",
                "reply": reply_text,
                "action": cmd_result.get("action"),
                "action_payload": cmd_result.get("action_payload", {}),
                "requires_confirmation": cmd_result.get("requires_confirmation", False),
                "confirmation_prompt": cmd_result.get("confirmation_prompt"),
                "model": "gemini_action_intent",
                "suggestions": [
                    "💧 How can I save irrigation water?",
                    "🪴 How do I test soil moisture?",
                    "🌾 Which crops are best suited for my region?",
                    "📊 Help me explain my latest irrigation prediction."
                ],
            })
    except Exception as e:
        logger.warning(f"Voice action dispatch check error in /api/chat: {e}")

    # 2. General Agricultural Query / Follow-up: Generate response using Grounded Gemini engine
    try:
        result = generate_response(
            prompt=message,
            context=context,
            language=language,
            history=validated_history,
        )
        return jsonify({
            "reply": result["reply"],
            "model": result.get("model", ""),
            "status": "success",
            "action": "general_query",
            "action_payload": {},
            "suggestions": result.get("suggestions", []),
        })
    except AgriAssistantError as e:
        status_code = 400 if e.code in ("invalid_request", "missing_api_key") else 500
        return jsonify({
            "error": e.message,
            "code": e.code,
            "status": "error",
        }), status_code
    except Exception as e:
        return jsonify({
            "error": "Unable to process your request with AgriSaathi at this time.",
            "status": "error",
        }), 500


# ========================================================
# Phase 10: Private Super Admin Panel & Management APIs
# ========================================================
def get_client_ip() -> str:
    """Safely extract remote client IP address, respecting reverse proxies."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_admin = session.get("is_admin")
        admin_id = session.get("admin_id")
        if not is_admin or not admin_id:
            # Administrative API routes
            if request.path.startswith("/api/admin"):
                if session.get("farmer_id"):
                    return jsonify({"error": "Access denied. Administrator privileges required.", "status": "forbidden"}), 403
                return jsonify({"error": "Administrative authentication required.", "authenticated": False}), 401
            
            # Browser page routes (e.g. /admin)
            if session.get("farmer_id"):
                return redirect("/admin/login?error=forbidden"), 302
            return redirect("/admin/login"), 302
        return f(*args, **kwargs)
    return decorated_function


# Web Pages
@app.route("/admin/login", methods=["GET"])
def admin_login_page():
    if session.get("is_admin") and session.get("admin_id"):
        return redirect("/admin")
    return render_template("admin_login.html")


@app.route("/admin", methods=["GET"])
@admin_required
def admin_dashboard_page():
    return render_template("admin.html")


# Authentication APIs
@app.route("/api/admin/auth/login", methods=["POST"])
def admin_auth_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    if not username or not password:
        return jsonify({"error": "Administrator username and password are required.", "status": "error"}), 400

    ip = get_client_ip()
    result = authenticate_admin(username, password, ip_address=ip)
    if not result.get("authenticated"):
        status_code = 423 if result.get("locked") else 401
        return jsonify({
            "error": result.get("error", "Authentication failed."),
            "status": "error",
            "locked": result.get("locked", False),
        }), status_code

    admin = result["admin"]
    session["admin_id"] = admin["id"]
    session["admin_username"] = admin["username"]
    session["is_admin"] = True

    return jsonify({
        "status": "success",
        "admin": admin,
        "redirect": "/admin",
    }), 200


@app.route("/api/admin/auth/logout", methods=["POST"])
def admin_auth_logout():
    admin_id = session.get("admin_id")
    admin_user = session.get("admin_username", "admin")
    if admin_id:
        log_admin_action(
            admin_id=admin_id,
            admin_username=admin_user,
            action="LOGOUT",
            target_type="admin",
            target_id=admin_id,
            details="Super Admin ended active session.",
            ip_address=get_client_ip(),
        )
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    session.pop("is_admin", None)
    session.pop("impersonating_admin_id", None)
    session.pop("impersonating_admin_username", None)
    return jsonify({"status": "success", "message": "Admin session terminated."}), 200


@app.route("/api/admin/me", methods=["GET"])
@admin_required
def admin_auth_me():
    admin = get_admin_by_id(session["admin_id"])
    if not admin:
        session.pop("admin_id", None)
        session.pop("is_admin", None)
        return jsonify({"authenticated": False, "error": "Admin record not found."}), 404
    return jsonify({"authenticated": True, "admin": admin}), 200


# Central KPIs
@app.route("/api/admin/kpis", methods=["GET"])
@admin_required
def admin_kpis_endpoint():
    kpis = get_admin_dashboard_kpis()
    return jsonify(kpis), 200


# Farmer Management APIs
@app.route("/api/admin/farmers", methods=["GET"])
@admin_required
def admin_farmers_list():
    search = request.args.get("search")
    state = request.args.get("state")
    district = request.args.get("district")
    status = request.args.get("status")
    farmers = get_all_farmers_admin(search_query=search, state=state, district=district, status=status)
    return jsonify(farmers), 200


@app.route("/api/admin/farmers/<farmer_id>", methods=["GET"])
@admin_required
def admin_farmer_detail(farmer_id):
    details = get_farmer_details_admin(farmer_id)
    if not details:
        return jsonify({"error": "Farmer not found."}), 404
    return jsonify(details), 200


@app.route("/api/admin/farmers/<farmer_id>/status", methods=["POST"])
@admin_required
def admin_set_farmer_status(farmer_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    reason = data.get("reason")
    if not new_status:
        return jsonify({"error": "Status is required."}), 400

    res = set_farmer_status(
        admin_id=session["admin_id"],
        admin_username=session["admin_username"],
        farmer_id=farmer_id,
        new_status=new_status,
        reason=reason,
        ip_address=get_client_ip(),
    )
    if not res.get("success"):
        return jsonify(res), 400
    return jsonify(res), 200


@app.route("/api/admin/farmers/<farmer_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_farmer_password(farmer_id):
    data = request.get_json(silent=True) or {}
    pwd = data.get("password", "").strip()
    if not pwd or len(pwd) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    res = reset_farmer_password_admin(
        admin_id=session["admin_id"],
        admin_username=session["admin_username"],
        farmer_id=farmer_id,
        new_password=pwd,
        ip_address=get_client_ip(),
    )
    if not res.get("success"):
        return jsonify(res), 400
    return jsonify(res), 200


@app.route("/api/admin/farmers/<farmer_id>", methods=["PUT"])
@admin_required
def admin_update_farmer(farmer_id):
    data = request.get_json(silent=True) or {}
    res = update_farmer_profile_admin(
        admin_id=session["admin_id"],
        admin_username=session["admin_username"],
        farmer_id=farmer_id,
        data=data,
        ip_address=get_client_ip(),
    )
    if not res.get("success"):
        return jsonify(res), 400
    return jsonify(res), 200


# Administrative Impersonation
@app.route("/api/admin/farmers/<farmer_id>/impersonate", methods=["POST"])
@admin_required
def admin_impersonate_farmer(farmer_id):
    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Administrative inspection").strip()
    farmer = get_farmer_by_id(farmer_id)
    if not farmer:
        return jsonify({"error": "Farmer not found."}), 404

    # Log impersonation action in audit trail
    log_admin_action(
        admin_id=session["admin_id"],
        admin_username=session["admin_username"],
        action="IMPERSONATE_FARMER",
        target_type="farmer",
        target_id=farmer_id,
        details=f"Admin initiated dashboard inspection mode for {farmer.get('name')} ({farmer_id}). Reason: {reason}",
        ip_address=get_client_ip(),
    )

    # Establish farmer session with admin impersonation flags
    session["farmer_id"] = farmer_id
    session["impersonating_admin_id"] = session["admin_id"]
    session["impersonating_admin_username"] = session["admin_username"]

    return jsonify({
        "status": "success",
        "redirect": "/",
        "farmer_id": farmer_id,
        "farmer_name": farmer.get("name"),
    }), 200


@app.route("/api/admin/exit-impersonation", methods=["GET"])
def admin_exit_impersonation():
    admin_id = session.get("impersonating_admin_id") or session.get("admin_id")
    admin_user = session.get("impersonating_admin_username") or session.get("admin_username", "admin")
    farmer_id = session.get("farmer_id")

    if admin_id and farmer_id:
        log_admin_action(
            admin_id=admin_id,
            admin_username=admin_user,
            action="EXIT_IMPERSONATION",
            target_type="farmer",
            target_id=farmer_id,
            details=f"Admin exited inspection mode for farmer {farmer_id}.",
            ip_address=get_client_ip(),
        )

    session.pop("impersonating_admin_id", None)
    session.pop("impersonating_admin_username", None)
    session.pop("farmer_id", None)
    return redirect("/admin")


# Global Holdings & Telemetry APIs
@app.route("/api/admin/farms", methods=["GET"])
@admin_required
def admin_farms_list():
    state = request.args.get("state")
    district = request.args.get("district")
    village = request.args.get("village")
    farms = get_all_farms_admin(state=state, district=district, village=village)
    return jsonify(farms), 200


@app.route("/api/admin/schedules", methods=["GET"])
@admin_required
def admin_schedules_list():
    status = request.args.get("status")
    crop = request.args.get("crop")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    farmer_id = request.args.get("farmer_id")
    limit = int(request.args.get("limit", 200))
    schedules = get_all_schedules_admin(
        status=status,
        crop=crop,
        date_from=date_from,
        date_to=date_to,
        farmer_id=farmer_id,
        limit=limit,
    )
    return jsonify(schedules), 200


@app.route("/api/admin/weather", methods=["GET"])
@admin_required
def admin_weather_overview():
    weather_list = get_admin_weather_overview()
    return jsonify(weather_list), 200


@app.route("/api/admin/ai-system", methods=["GET"])
@admin_required
def admin_ai_status():
    status = get_ai_system_status()
    return jsonify(status), 200


@app.route("/api/admin/audit-logs", methods=["GET"])
@admin_required
def admin_audit_logs():
    limit = int(request.args.get("limit", 100))
    action = request.args.get("action")
    logs = get_admin_audit_logs(limit=limit, action=action)
    return jsonify(logs), 200


# Start the local development server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
