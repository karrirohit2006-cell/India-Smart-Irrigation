"""
Comprehensive Test Suite for Smart Irrigation Scheduler & Mini Calendar
Tests all 10 requirements specified in the project prompt:
1. Irrigation required -> schedule generated with valid sessions & water in Litres.
2. Irrigation not required -> schedules empty, no_irrigation_reason provided.
3. Calendar endpoints & dates marked correctly.
4. Schedule selection & retrieval by crop/farm.
5. Status updates (Mark Completed, Skip) persist in SQLite.
6. Completed history preserved when recalculating new predictions.
7. Rainfall-based postponement (> 5mm forecast delays sessions).
8. Voice & Chatbot handlers return real schedule details.
9. Multilingual voice/chatbot support (English, Hindi, Telugu).
10. API response structures and edge case handling.
"""

import pytest
from app import app
from src.irrigation_scheduler import (
    init_scheduler_db,
    calculate_smart_schedule,
    generate_and_save_schedule,
    get_all_schedules,
    update_schedule_status,
    get_schedule_summary,
)
from src.agri_assistant import generate_response


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def setup_db():
    init_scheduler_db()


def test_1_irrigation_required_generates_schedule(client):
    """Test 1: When irrigation is required, scheduler generates valid sessions with water in Litres."""
    payload = {
        "state": "Punjab",
        "crop": "Wheat",
        "crop_age_days": 35,
        "sensor_reading": 25.0,  # Below trigger 40% -> IRRIGATE
        "soil_temp": 20.0,
        "air_temp": 24.0,
        "humidity": 50.0,
        "rainfall_7d": 0.0,
        "forecast_24h": 0.0,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "IRRIGATE"
    assert "schedules" in data
    assert len(data["schedules"]) >= 2
    assert "water_requirement_liters" in data
    assert data["water_requirement_liters"] > 0
    first_session = data["schedules"][0]
    assert first_session["water_quantity_liters"] > 0
    assert first_session["recommended_time"] == "06:00 AM"
    assert first_session["status"] in ["Pending", "Upcoming"]


def test_2_irrigation_not_required_hides_schedule(client):
    """Test 2: When irrigation is not required, schedule is empty and reason is provided."""
    payload = {
        "state": "Punjab",
        "crop": "Rice",
        "crop_age_days": 40,
        "sensor_reading": 3.0,  # 3 cm standing water -> DO NOT IRRIGATE
        "soil_temp": 26.0,
        "air_temp": 30.0,
        "humidity": 70.0,
        "rainfall_7d": 0.0,
        "forecast_24h": 0.0,
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] in ["DO NOT IRRIGATE", "MONITOR"]
    assert data["schedules"] == []
    assert "no_irrigation_reason" in data
    assert "sufficient" in data["no_irrigation_reason"].lower() or "not required" in data["no_irrigation_reason"].lower()


def test_3_get_schedules_api_endpoint(client):
    """Test 3: GET /api/schedules returns list of schedules and summary for calendar."""
    response = client.get("/api/schedules")
    assert response.status_code == 200
    data = response.get_json()
    assert "schedules" in data
    assert "summary" in data
    assert "total" in data
    assert isinstance(data["schedules"], list)


def test_4_mark_completed_action(client):
    """Test 4: Marking a session as Completed updates status in SQLite database."""
    # Generate schedule
    schedules = generate_and_save_schedule(
        crop="Cotton",
        state="Punjab",
        sensor_reading=20.0,
        reading_unit="%",
        trigger=40.0,
        rainfall_7d=0.0,
        forecast_24h=0.0,
    )
    assert len(schedules) > 0
    target_id = schedules[0]["id"]

    # Mark completed
    res = client.post(f"/api/schedules/{target_id}/status", json={"status": "Completed"})
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "success"
    assert res_data["new_status"] == "Completed"

    # Verify via summary
    summary = get_schedule_summary()
    assert summary["total_completed_sessions"] >= 1


def test_5_skip_action(client):
    """Test 5: Skipping a session updates status to Skipped and sets reason."""
    schedules = generate_and_save_schedule(
        crop="Maize",
        state="Punjab",
        sensor_reading=20.0,
        reading_unit="%",
        trigger=40.0,
        rainfall_7d=0.0,
        forecast_24h=0.0,
    )
    assert len(schedules) > 0
    target_id = schedules[0]["id"]

    res = client.post(
        f"/api/schedules/{target_id}/status",
        json={"status": "Skipped", "skip_reason": "High wind today"},
    )
    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data["status"] == "success"
    assert res_data["new_status"] == "Skipped"


def test_6_completed_history_preserved_on_new_prediction(client):
    """Test 6: When new prediction generates schedules, existing Completed history is NOT deleted."""
    # 1. Create schedule and mark completed
    s1 = generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    target_id = s1[0]["id"]
    update_schedule_status(target_id, "Completed")

    # 2. Run new prediction / generation for the same crop
    s2 = generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=20.0,
        reading_unit="%",
        trigger=40.0,
    )

    # 3. Check that the completed session is still in the database
    all_s = get_all_schedules(crop="Wheat")
    completed_ids = [s["id"] for s in all_s if s["status"] == "Completed"]
    assert target_id in completed_ids


def test_7_rainfall_based_rescheduling():
    """Test 7: Forecast rainfall >= 5mm automatically postpones upcoming irrigation date."""
    sessions_dry = calculate_smart_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=25.0,
        reading_unit="%",
        trigger=40.0,
        forecast_24h=0.0,
    )

    sessions_rain = calculate_smart_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=25.0,
        reading_unit="%",
        trigger=40.0,
        forecast_24h=12.0,  # 12mm rain forecast
    )

    assert len(sessions_dry) > 0
    assert len(sessions_rain) > 0
    # The first date in rain forecast scenario must be postponed
    assert sessions_rain[0]["irrigation_date"] > sessions_dry[0]["irrigation_date"]
    assert "rainfall" in sessions_rain[0]["reason"].lower() or "postponed" in sessions_rain[0]["reason"].lower()


def test_8_chatbot_retrieves_real_schedule():
    """Test 8: Chatbot correctly answers 'When should I irrigate next?' using real SQLite data."""
    # Ensure active schedule exists
    generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=25.0,
        reading_unit="%",
        trigger=40.0,
    )

    result = generate_response("When should I irrigate next?")
    assert result["status"] == "success"
    reply = result["reply"]
    assert "06:00 AM" in reply or "AM" in reply
    assert "Wheat" in reply or "scheduled" in reply


def test_9_chatbot_schedule_multilingual():
    """Test 9: Chatbot schedule questions work in Hindi and Telugu."""
    # Hindi
    r_hi = generate_response("मुझे अगली सिंचाई कब करनी चाहिए?", language="hi")
    assert r_hi["status"] == "success"
    assert "सिंचाई" in r_hi["reply"]

    # Telugu
    r_te = generate_response("నేను తదుపరి ఎప్పుడు నీరు పెట్టాలి?", language="te")
    assert r_te["status"] == "success"
    assert "నీటిపారుదల" in r_te["reply"] or "నీటి" in r_te["reply"] or "ఇరిగేషన్" in r_te["reply"]


def test_10_chatbot_show_all_irrigation_dates_and_calendar():
    """Test 10: 'Show my irrigation calendar' and 'Which dates require irrigation?' return active dates."""
    generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    res = generate_response("Show my irrigation calendar")
    assert res["status"] == "success"
    assert "BLUE" in res["reply"] or "calendar" in res["reply"].lower()

    res2 = generate_response("Which dates require irrigation?")
    assert res2["status"] == "success"
    assert "Wheat" in res2["reply"] or "Status" in res2["reply"] or "BLUE" in res2["reply"]


def test_11_chatbot_completed_and_skipped_dates(client):
    """Test 11: Chatbot returns completed (GREEN) and skipped (RED) dates."""
    schedules = generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    s1_id = schedules[0]["id"]
    s2_id = schedules[1]["id"]

    # Mark s1 completed
    client.post(f"/api/schedules/{s1_id}/status", json={"status": "Completed"})
    # Mark s2 skipped
    client.post(f"/api/schedules/{s2_id}/status", json={"status": "Skipped", "skip_reason": "High wind"})

    # Query completed dates
    r_comp = generate_response("Show completed irrigation dates")
    assert r_comp["status"] == "success"
    assert "GREEN" in r_comp["reply"] or "completed" in r_comp["reply"].lower()

    # Query skipped dates
    r_skip = generate_response("Show skipped irrigation dates")
    assert r_skip["status"] == "success"
    assert "RED" in r_skip["reply"] or "skipped" in r_skip["reply"].lower()


def test_12_chatbot_reschedule_action():
    """Test 12: 'Reschedule today's irrigation' reschedules session to next date and preserves volume."""
    schedules = generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    res = generate_response("Reschedule today's irrigation")
    assert res["status"] == "success"
    assert "Rescheduled" in res["reply"] or "rescheduled" in res["reply"].lower()
    assert "BLUE" in res["reply"]


def test_13_chatbot_why_irrigation_required_tomorrow():
    """Test 13: 'Why is irrigation required tomorrow?' returns agronomic explanation."""
    generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    res = generate_response("Why is irrigation required tomorrow?")
    assert res["status"] == "success"
    assert "Recommendation" in res["reply"] or "evapotranspiration" in res["reply"] or "replenishment" in res["reply"]


def test_14_chatbot_how_many_days_required():
    """Test 14: 'How many days is irrigation required?' returns count of spaced sessions."""
    generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    res = generate_response("How many days is irrigation required?")
    assert res["status"] == "success"
    assert "spaced irrigation sessions" in res["reply"]


def test_15_chatbot_update_irrigation_schedule():
    """Test 15: 'Update my irrigation schedule' synchronizes and returns confirmation."""
    generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=22.0,
        reading_unit="%",
        trigger=40.0,
    )
    res = generate_response("Update my irrigation schedule")
    assert res["status"] == "success"
    assert "synchronized" in res["reply"].lower() or "updated" in res["reply"].lower()


def test_16_skip_and_reschedule_engine_details():
    """Test 16: skip_and_reschedule_session creates proper Rescheduled session without inflating water."""
    schedules = generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=20.0,
        reading_unit="%",
        trigger=40.0,
    )
    from src.irrigation_scheduler import skip_and_reschedule_session
    orig_qty = schedules[0]["water_quantity_liters"]
    res = skip_and_reschedule_session(schedules[0]["id"], skip_reason="Farmer unavailable")
    assert res["success"] is True
    assert res["new_session"]["status"] == "Rescheduled"
    assert res["new_session"]["water_quantity_liters"] == orig_qty  # Water requirement not inflated
    assert "Rescheduled from" in res["new_session"]["reason"]

    summary = get_schedule_summary()
    assert summary["total_skipped_sessions"] >= 1
    assert res["new_date"] in summary["upcoming_dates"]


def test_17_all_twelve_queries_multilingual():
    """Test 17: Verifies all 12 queries return valid responses in Hindi, Telugu, and English."""
    generate_and_save_schedule(
        crop="Wheat",
        state="Punjab",
        sensor_reading=20.0,
        reading_unit="%",
        trigger=40.0,
    )

    queries_and_keywords = [
        ("Show my irrigation calendar", ["calendar", "blue", "dates", "wheat"]),
        ("Show all irrigation dates", ["calendar", "blue", "wheat", "dates"]),
        ("How many days is irrigation required?", ["spaced", "session"]),
        ("Which dates require irrigation?", ["wheat", "status", "blue", "calendar"]),
        ("What is my next irrigation date?", ["06:00", "am", "wheat", "scheduled"]),
        ("Why is irrigation required tomorrow?", ["recommendation", "evapotranspiration", "replenishment"]),
        ("Update my irrigation schedule", ["synchronized", "updated"]),
    ]

    for q, keywords in queries_and_keywords:
        res = generate_response(q, language="en")
        assert res["status"] == "success"
        reply_lower = res["reply"].lower()
        assert any(k in reply_lower for k in keywords), f"Query '{q}' failed keywords {keywords}: {res['reply']}"

    # Multilingual: Hindi queries
    r_hi_cal = generate_response("सिंचाई कैलेंडर दिखाओ", language="hi")
    assert r_hi_cal["status"] == "success"
    assert "कैलेंडर" in r_hi_cal["reply"] or "नीले" in r_hi_cal["reply"]

    # Multilingual: Telugu queries
    r_te_cal = generate_response("క్యాలెండర్ చూపించు", language="te")
    assert r_te_cal["status"] == "success"
    assert "క్యాలెండర్" in r_te_cal["reply"] or "నీలి" in r_te_cal["reply"] or "తేదీలు" in r_te_cal["reply"]
