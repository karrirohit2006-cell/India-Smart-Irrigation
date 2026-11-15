"""
Smart Irrigation Scheduler - Database and Agricultural Scheduling Engine.
Provides prediction-driven irrigation session planning, SQLite persistence,
rainfall-aware rescheduling, and voice/chatbot integration.
"""

import sqlite3
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("irrigation_scheduler")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "irrigation_schedules.db"


def get_db_connection() -> sqlite3.Connection:
    """Create a connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_scheduler_db():
    """Initialize the SQLite schedules table if not present and handle migrations."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS smart_irrigation_schedules (
                    id TEXT PRIMARY KEY,
                    farm_id TEXT DEFAULT 'default_farm',
                    prediction_id TEXT,
                    crop TEXT NOT NULL,
                    state TEXT NOT NULL,
                    irrigation_date TEXT NOT NULL,
                    recommended_time TEXT NOT NULL,
                    water_quantity_liters REAL NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Upcoming',
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );
            """)
            # Check if completed_at column exists in an existing table
            cursor = conn.execute("PRAGMA table_info(smart_irrigation_schedules);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "completed_at" not in columns:
                conn.execute("ALTER TABLE smart_irrigation_schedules ADD COLUMN completed_at TEXT;")

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sched_crop_date 
                ON smart_irrigation_schedules (crop, irrigation_date);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sched_status 
                ON smart_irrigation_schedules (status);
            """)
        logger.info("Initialized smart_irrigation_schedules database table.")
    finally:
        conn.close()


# Crop irrigation intervals (days between watering sessions in dry periods)
CROP_INTERVALS = {
    "rice": 2,        # Alternate Wetting & Drying cycle
    "paddy": 2,
    "wheat": 3,
    "cotton": 4,
    "maize": 3,
    "sugarcane": 5,
    "tomato": 2,
    "chilli": 2,
    "groundnut": 4,
    "mustard": 4,
    "pulses": 4,
    "vegetables": 2,
}

# Crop benchmark session water volume (in Litres for standard demonstration plot)
CROP_BASE_LITERS = {
    "rice": 500.0,
    "paddy": 500.0,
    "wheat": 450.0,
    "cotton": 480.0,
    "maize": 420.0,
    "sugarcane": 600.0,
    "tomato": 350.0,
    "chilli": 350.0,
    "groundnut": 400.0,
    "mustard": 380.0,
    "pulses": 360.0,
    "vegetables": 350.0,
}


def calculate_smart_schedule(
    crop: str,
    state: str,
    sensor_reading: float,
    reading_unit: str = "%",
    trigger: float = 40.0,
    rainfall_7d: float = 0.0,
    forecast_24h: float = 0.0,
    start_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate an agricultural, prediction-driven schedule.
    Returns 2 or 3 specific recommended irrigation dates.
    """
    base_date = start_date or datetime.now()
    crop_lower = crop.lower().strip()
    interval_days = CROP_INTERVALS.get(crop_lower, 3)
    base_liters = CROP_BASE_LITERS.get(crop_lower, 450.0)

    # Determine severity of deficit
    # If moisture is severely depressed, schedule 3 sessions; otherwise 2 sessions
    is_severe = False
    if reading_unit == "%" and trigger > 0:
        if sensor_reading < (trigger * 0.75):
            is_severe = True
    elif reading_unit == "cm":  # Rice standing water
        if sensor_reading <= -20.0:
            is_severe = True

    num_sessions = 3 if is_severe else 2

    # Adjust water volume based on reading deficit
    water_multiplier = 1.15 if is_severe else 1.0
    water_liters = round(base_liters * water_multiplier, 0)

    # Duration: approx 10 mins per 100 Litres (drip/furrow rate)
    duration_mins = max(30, min(75, int(water_liters / 10)))

    # Preferred timing: 6:00 AM for summer/hot crops; 5:30 PM for chill/winter
    preferred_time = "06:00 AM"

    # Check rainfall forecast rescheduling
    rain_postpone_days = 0
    rain_note = ""
    if forecast_24h >= 5.0:
        rain_postpone_days = 2
        rain_note = f" (Postponed by 2 days due to {forecast_24h:.1f} mm rain forecast)"
    elif rainfall_7d >= 10.0:
        rain_postpone_days = 1
        rain_note = f" (Adjusted due to recent {rainfall_7d:.1f} mm rainfall)"

    sessions = []
    for i in range(num_sessions):
        # Specific spaced dates (Prediction-driven, NOT daily!)
        day_offset = (i * interval_days) + 1 + rain_postpone_days
        session_dt = base_date + timedelta(days=day_offset)
        date_str = session_dt.strftime("%Y-%m-%d")

        status = "Rescheduled" if (i == 0 and rain_postpone_days > 0) else ("Pending" if i == 0 else "Upcoming")

        if i == 0:
            reason = f"Immediate root-zone replenishment for {crop} up to field capacity{rain_note}."
        elif i == 1:
            reason = f"Mid-interval maintenance watering to sustain active tillering/foliage."
        else:
            reason = f"Pre-canopy closure stabilization to prevent subsoil moisture depletion."

        sessions.append({
            "crop": crop,
            "state": state,
            "irrigation_date": date_str,
            "date_display": session_dt.strftime("%B %d"),
            "recommended_time": preferred_time,
            "water_quantity_liters": water_liters,
            "duration_minutes": duration_mins,
            "status": status,
            "reason": reason,
        })

    return sessions


def generate_and_save_schedule(
    crop: str,
    state: str,
    sensor_reading: float,
    reading_unit: str = "%",
    trigger: float = 40.0,
    rainfall_7d: float = 0.0,
    forecast_24h: float = 0.0,
    prediction_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Generate new schedule sessions and persist to SQLite database.
    Preserves existing 'Completed' sessions, removes outdated 'Upcoming'/'Pending' entries.
    """
    init_scheduler_db()
    sessions = calculate_smart_schedule(
        crop=crop,
        state=state,
        sensor_reading=sensor_reading,
        reading_unit=reading_unit,
        trigger=trigger,
        rainfall_7d=rainfall_7d,
        forecast_24h=forecast_24h,
    )

    now_iso = datetime.now().isoformat()
    conn = get_db_connection()
    saved_records = []
    try:
        with conn:
            # Clean up old Upcoming / Pending records for this crop so new predictions update cleanly
            conn.execute("""
                DELETE FROM smart_irrigation_schedules 
                WHERE crop = ? AND status IN ('Upcoming', 'Pending', 'Rescheduled');
            """, (crop,))

            for idx, s in enumerate(sessions):
                sched_id = f"sched_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}_{idx+1}"
                conn.execute("""
                    INSERT OR REPLACE INTO smart_irrigation_schedules (
                        id, farm_id, prediction_id, crop, state,
                        irrigation_date, recommended_time, water_quantity_liters,
                        duration_minutes, status, reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    sched_id, "default_farm", prediction_id, s["crop"], s["state"],
                    s["irrigation_date"], s["recommended_time"], s["water_quantity_liters"],
                    s["duration_minutes"], s["status"], s["reason"], now_iso, now_iso
                ))
                s["id"] = sched_id
                saved_records.append(s)
        return saved_records
    finally:
        conn.close()


def get_all_schedules(crop: Optional[str] = None, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all schedules ordered by irrigation_date, optionally filtered by farmer_id and crop."""
    init_scheduler_db()
    conn = get_db_connection()
    try:
        query = "SELECT * FROM smart_irrigation_schedules"
        conditions = []
        params = []
        if farmer_id:
            conditions.append("farmer_id = ?")
            params.append(farmer_id)
        if crop:
            conditions.append("LOWER(crop) = LOWER(?)")
            params.append(crop.strip())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY irrigation_date ASC;"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            dt = datetime.strptime(r["irrigation_date"], "%Y-%m-%d")
            completed_at = r["completed_at"] if "completed_at" in r.keys() else None
            results.append({
                "id": r["id"],
                "farm_id": r["farm_id"],
                "prediction_id": r["prediction_id"],
                "crop": r["crop"],
                "state": r["state"],
                "irrigation_date": r["irrigation_date"],
                "date_display": dt.strftime("%B %d"),
                "recommended_time": r["recommended_time"],
                "water_quantity_liters": r["water_quantity_liters"],
                "duration_minutes": r["duration_minutes"],
                "status": r["status"],
                "reason": r["reason"],
                "created_at": r["created_at"],
                "completed_at": completed_at,
                "updated_at": r["updated_at"],
            })
        return results
    finally:
        conn.close()


def mark_session_completed(schedule_id: str) -> Dict[str, Any]:
    """
    Mark an irrigation session as Completed (GREEN).
    Stores completion timestamp and updates record.
    """
    init_scheduler_db()
    conn = get_db_connection()
    try:
        now_iso = datetime.now().isoformat()
        with conn:
            cursor = conn.execute("""
                UPDATE smart_irrigation_schedules 
                SET status = 'Completed', completed_at = ?, updated_at = ?
                WHERE id = ?;
            """, (now_iso, now_iso, schedule_id))
            if cursor.rowcount > 0:
                row = conn.execute("SELECT * FROM smart_irrigation_schedules WHERE id = ?;", (schedule_id,)).fetchone()
                return {
                    "success": True,
                    "session": dict(row) if row else None,
                    "message": "Session marked as Completed."
                }
            return {"success": False, "error": f"Session ID {schedule_id} not found."}
    finally:
        conn.close()


def skip_and_reschedule_session(
    schedule_id: str,
    skip_reason: Optional[str] = None,
    forecast_24h: float = 0.0,
) -> Dict[str, Any]:
    """
    Mark session as Skipped (RED) and perform AI intelligent schedule reassessment:
    - Moves the session to following day (or next dry day if rain expected).
    - Avoids duplicate sessions on the same date.
    - Adds new session in BLUE ('Rescheduled').
    - Preserves remaining water requirements without artificial inflation.
    - Returns updated sessions and rationale.
    """
    init_scheduler_db()
    conn = get_db_connection()
    try:
        now_iso = datetime.now().isoformat()
        with conn:
            row = conn.execute("SELECT * FROM smart_irrigation_schedules WHERE id = ?;", (schedule_id,)).fetchone()
            if not row:
                return {"success": False, "error": f"Session {schedule_id} not found."}

            session = dict(row)
            reason_suffix = f" [Skipped: {skip_reason}]" if skip_reason else " [Skipped by farmer]"
            conn.execute("""
                UPDATE smart_irrigation_schedules 
                SET status = 'Skipped', reason = reason || ?, updated_at = ?
                WHERE id = ?;
            """, (reason_suffix, now_iso, schedule_id))

            # Reassess: calculate new recommended date
            old_dt = datetime.strptime(session["irrigation_date"], "%Y-%m-%d")
            today = datetime.now().date()
            base_resched = max(old_dt.date(), today)
            
            # Postpone by 1 day (or 2 days if rain forecast >= 5mm)
            delay = 2 if forecast_24h >= 5.0 else 1
            new_date = base_resched + timedelta(days=delay)

            # Check if this crop already has an active session on new_date
            existing_dates = set(r["irrigation_date"] for r in conn.execute("""
                SELECT irrigation_date FROM smart_irrigation_schedules
                WHERE crop = ? AND status IN ('Upcoming', 'Pending', 'Rescheduled');
            """, (session["crop"],)).fetchall())

            while new_date.strftime("%Y-%m-%d") in existing_dates:
                new_date += timedelta(days=1)

            new_date_str = new_date.strftime("%Y-%m-%d")
            new_id = f"sched_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}_resched"

            resched_reason = (
                f"AI Reassessment: Rescheduled from {old_dt.strftime('%B %d')} (skipped). "
                f"Maintains root-zone moisture threshold without increasing total water requirement."
            )
            if forecast_24h >= 5.0:
                resched_reason += f" Delayed by {delay} days due to forecast rain ({forecast_24h:.1f} mm)."

            conn.execute("""
                INSERT INTO smart_irrigation_schedules (
                    id, farm_id, prediction_id, crop, state,
                    irrigation_date, recommended_time, water_quantity_liters,
                    duration_minutes, status, reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                new_id, session["farm_id"], session["prediction_id"], session["crop"], session["state"],
                new_date_str, session["recommended_time"], session["water_quantity_liters"],
                session["duration_minutes"], "Rescheduled", resched_reason, now_iso, now_iso
            ))

            new_session_row = conn.execute("SELECT * FROM smart_irrigation_schedules WHERE id = ?;", (new_id,)).fetchone()

            return {
                "success": True,
                "skipped_id": schedule_id,
                "rescheduled_id": new_id,
                "new_date": new_date_str,
                "new_session": dict(new_session_row) if new_session_row else None,
                "reason": resched_reason,
            }
    finally:
        conn.close()


def update_schedule_status(schedule_id: str, new_status: str, skip_reason: Optional[str] = None) -> bool:
    """Update a schedule session's status (e.g. Completed, Skipped, Rescheduled)."""
    if new_status == "Completed":
        res = mark_session_completed(schedule_id)
        return res.get("success", False)
    elif new_status == "Skipped":
        res = skip_and_reschedule_session(schedule_id, skip_reason=skip_reason)
        return res.get("success", False)
    else:
        init_scheduler_db()
        conn = get_db_connection()
        try:
            now_iso = datetime.now().isoformat()
            with conn:
                cursor = conn.execute("""
                    UPDATE smart_irrigation_schedules 
                    SET status = ?, updated_at = ?
                    WHERE id = ?;
                """, (new_status, now_iso, schedule_id))
                return cursor.rowcount > 0
        finally:
            conn.close()


def get_schedule_summary(farmer_id: Optional[str] = None) -> Dict[str, Any]:
    """Provide a structured summary for the voice assistant and chatbot, optionally filtered by farmer_id."""
    schedules = get_all_schedules(farmer_id=farmer_id)
    active = [s for s in schedules if s["status"] in ("Upcoming", "Pending", "Rescheduled")]
    completed = [s for s in schedules if s["status"] == "Completed"]
    skipped = [s for s in schedules if s["status"] == "Skipped"]

    next_session = active[0] if active else None
    total_water = sum(s["water_quantity_liters"] for s in active)

    completed_dates = [s["irrigation_date"] for s in completed]
    skipped_dates = [s["irrigation_date"] for s in skipped]
    upcoming_dates = [s["irrigation_date"] for s in active]

    return {
        "has_active_schedule": len(active) > 0,
        "total_active_sessions": len(active),
        "total_completed_sessions": len(completed),
        "total_skipped_sessions": len(skipped),
        "total_water_required_liters": total_water,
        "next_session": next_session,
        "active_schedules": active,
        "completed_schedules": completed,
        "skipped_schedules": skipped,
        "completed_dates": completed_dates,
        "skipped_dates": skipped_dates,
        "upcoming_dates": upcoming_dates,
    }
