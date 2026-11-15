"""
Farm Manager: Multi-Farmer, Multi-Farm, Multi-Section Agricultural Data Management.
Supports secure farmer authentication, land partitioning, section-wise crop records,
independent predictions, and combined farmer calendar aggregation.
"""

import sqlite3
import logging
import uuid
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger("farm_manager")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "irrigation_schedules.db"

# Unit Conversion to Canonical Acres
LAND_UNIT_TO_ACRES = {
    "acres": 1.0,
    "acre": 1.0,
    "hectares": 2.47105,
    "hectare": 2.47105,
    "bigha": 0.625,
    "bighas": 0.625,
    "guntha": 0.025,
    "gunthas": 0.025,
}

# Crop Base Litres Per Acre for standard deep irrigation session
CROP_BASE_LITERS_PER_ACRE = {
    "wheat": 1000.0,
    "rice": 1200.0,
    "paddy": 1200.0,
    "potato": 833.3,
    "cotton": 1000.0,
    "maize": 900.0,
    "sugarcane": 1400.0,
    "tomato": 750.0,
    "chilli": 750.0,
    "groundnut": 800.0,
    "mustard": 750.0,
    "pulses": 700.0,
    "vegetables": 700.0,
}

# Crop dry-down intervals (days between irrigation sessions in dry weather)
CROP_INTERVALS = {
    "rice": 2,
    "paddy": 2,
    "wheat": 3,
    "potato": 3,
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


def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_farm_db():
    """Initialize database tables for multi-farmer and multi-section architecture."""
    conn = get_db_connection()
    try:
        with conn:
            # 1. Farmers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farmers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT UNIQUE,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT '',
                    district TEXT,
                    village TEXT,
                    latitude REAL,
                    longitude REAL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'Active',
                    suspended_at TEXT,
                    suspend_reason TEXT,
                    last_login_at TEXT,
                    username TEXT UNIQUE,
                    onboarding_completed INTEGER DEFAULT 0,
                    preferred_language TEXT DEFAULT 'en'
                );
            """)

            # 2. Farms table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farms (
                    id TEXT PRIMARY KEY,
                    farmer_id TEXT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    total_area_acres REAL NOT NULL,
                    unit TEXT NOT NULL DEFAULT 'Acres',
                    state TEXT NOT NULL,
                    district TEXT,
                    village TEXT,
                    latitude REAL,
                    longitude REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # 3. Farm sections table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS farm_sections (
                    id TEXT PRIMARY KEY,
                    farm_id TEXT NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
                    farmer_id TEXT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    area_acres REAL NOT NULL,
                    is_empty INTEGER NOT NULL DEFAULT 0,
                    crop TEXT,
                    crop_variety TEXT,
                    sowing_date TEXT,
                    soil_type TEXT DEFAULT 'Loamy',
                    soil_moisture REAL DEFAULT 35.0,
                    soil_temp REAL DEFAULT 22.0,
                    air_temp REAL DEFAULT 26.0,
                    humidity REAL DEFAULT 55.0,
                    rainfall_7d REAL DEFAULT 0.0,
                    forecast_24h REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            # 4. Weather Cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weather_cache (
                    id TEXT PRIMARY KEY,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    current_temp REAL,
                    current_humidity REAL,
                    current_weather TEXT,
                    current_rainfall REAL,
                    forecast_rainfall_24h REAL,
                    forecast_temp REAL,
                    forecast_humidity REAL,
                    weather_json TEXT,
                    fetched_at TEXT NOT NULL
                );
            """)

            # 5. Smart Irrigation Schedules table migration for multi-farmer & section support
            conn.execute("""
                CREATE TABLE IF NOT EXISTS smart_irrigation_schedules (
                    id TEXT PRIMARY KEY,
                    farm_id TEXT DEFAULT 'default_farm',
                    farmer_id TEXT DEFAULT 'default_farmer',
                    section_id TEXT DEFAULT 'default_section',
                    prediction_id TEXT,
                    crop TEXT NOT NULL,
                    state TEXT NOT NULL,
                    irrigation_date TEXT NOT NULL,
                    recommended_time TEXT NOT NULL,
                    water_quantity_liters REAL NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Upcoming',
                    reason TEXT,
                    planning_period_days INTEGER DEFAULT 7,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                );
            """)

            # Handle column migrations if older table exists
            cursor = conn.execute("PRAGMA table_info(smart_irrigation_schedules);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "farmer_id" not in columns:
                conn.execute("ALTER TABLE smart_irrigation_schedules ADD COLUMN farmer_id TEXT DEFAULT 'default_farmer';")
            if "section_id" not in columns:
                conn.execute("ALTER TABLE smart_irrigation_schedules ADD COLUMN section_id TEXT DEFAULT 'default_section';")
            if "planning_period_days" not in columns:
                conn.execute("ALTER TABLE smart_irrigation_schedules ADD COLUMN planning_period_days INTEGER DEFAULT 7;")

            # Farmers table migrations for username and onboarding
            cursor_f = conn.execute("PRAGMA table_info(farmers);")
            f_cols_info = {row["name"]: dict(row) for row in cursor_f.fetchall()}
            if "username" not in f_cols_info:
                conn.execute("ALTER TABLE farmers ADD COLUMN username TEXT;")
            if "onboarding_completed" not in f_cols_info:
                conn.execute("ALTER TABLE farmers ADD COLUMN onboarding_completed INTEGER DEFAULT 0;")
            if "preferred_language" not in f_cols_info:
                conn.execute("ALTER TABLE farmers ADD COLUMN preferred_language TEXT DEFAULT 'en';")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_farmers_username ON farmers(username) WHERE username IS NOT NULL;")

            # Migrate phone to nullable if previously NOT NULL
            if "phone" in f_cols_info and f_cols_info["phone"]["notnull"] == 1:
                conn.execute("PRAGMA foreign_keys = OFF;")
                conn.execute("""
                    CREATE TABLE farmers_new (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        phone TEXT UNIQUE,
                        email TEXT UNIQUE,
                        password_hash TEXT NOT NULL,
                        state TEXT NOT NULL DEFAULT '',
                        district TEXT,
                        village TEXT,
                        latitude REAL,
                        longitude REAL,
                        created_at TEXT NOT NULL,
                        status TEXT DEFAULT 'Active',
                        suspended_at TEXT,
                        suspend_reason TEXT,
                        last_login_at TEXT,
                        username TEXT UNIQUE,
                        onboarding_completed INTEGER DEFAULT 0
                    );
                """)
                avail_cols = [c for c in ["id", "name", "phone", "email", "password_hash", "state", "district", "village", "latitude", "longitude", "created_at", "status", "suspended_at", "suspend_reason", "last_login_at", "username", "onboarding_completed"] if c in f_cols_info]
                col_names = ", ".join(avail_cols)
                conn.execute(f"INSERT INTO farmers_new ({col_names}) SELECT {col_names} FROM farmers;")
                conn.execute("DROP TABLE farmers;")
                conn.execute("ALTER TABLE farmers_new RENAME TO farmers;")
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_farmers_username ON farmers(username) WHERE username IS NOT NULL;")
                conn.execute("PRAGMA foreign_keys = ON;")

            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sec_farm ON farm_sections(farm_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sec_farmer ON farm_sections(farmer_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sched_sec ON smart_irrigation_schedules(section_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sched_farmer ON smart_irrigation_schedules(farmer_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sched_date ON smart_irrigation_schedules(irrigation_date);")

        logger.info("Initialized farm management database tables and indexes.")
    finally:
        conn.close()


# ----------------------------------------------------
# Farmer Authentication & Registration
# ----------------------------------------------------
def register_farmer(
    username: Optional[str] = None,
    password: str = "",
    name: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    state: str = "",
    district: Optional[str] = None,
    village: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    total_land: float = 1.0,
    unit: str = "Acres",
    onboarding_completed: int = 0,
    preferred_language: str = "en",
) -> Dict[str, Any]:
    """Register a new farmer account and automatically create their primary farm."""
    init_farm_db()

    # Determine unique username
    clean_username = (username or "").strip().lower()
    if not clean_username:
        if phone and phone.strip():
            clean_username = f"farmer_{phone.strip()}"
        elif name and name.strip():
            clean_username = name.strip().lower().replace(" ", "")
        else:
            raise ValueError("Username is required and cannot be empty.")

    if len(clean_username) < 3:
        raise ValueError("Username must be at least 3 characters long.")

    clean_password = (password or "").strip()
    if not clean_password:
        raise ValueError("Password is required and cannot be empty.")
    if len(clean_password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    conn = get_db_connection()
    try:
        # Check duplicate username
        dup = conn.execute("SELECT id FROM farmers WHERE LOWER(username) = ?;", (clean_username,)).fetchone()
        if dup:
            raise ValueError(f"The username '{clean_username}' is already taken. Please choose another username.")

        now_iso = datetime.now().isoformat()
        farmer_id = f"farmer_{uuid.uuid4().hex[:10]}"
        pwd_hash = generate_password_hash(clean_password)
        phone_clean = phone.strip() if phone and phone.strip() else None
        email_clean = email.strip().lower() if email and email.strip() else None
        name_clean = name.strip() if name and name.strip() else clean_username.capitalize()

        # Canonical land area in acres
        factor = LAND_UNIT_TO_ACRES.get((unit or "Acres").strip().lower(), 1.0)
        total_acres = round(float(total_land) * factor, 2)

        with conn:
            # 1. Insert farmer
            conn.execute("""
                INSERT INTO farmers (
                    id, name, phone, email, username, password_hash,
                    state, district, village, latitude, longitude, created_at, onboarding_completed, status, preferred_language
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?);
            """, (
                farmer_id, name_clean, phone_clean, email_clean, clean_username, pwd_hash,
                state.strip() if state else "", district, village, latitude, longitude, now_iso, onboarding_completed,
                (preferred_language or "en").strip().lower()
            ))

            # 2. Insert primary farm
            farm_id = f"farm_{uuid.uuid4().hex[:10]}"
            farm_name = f"{name_clean}'s Farm"
            conn.execute("""
                INSERT INTO farms (
                    id, farmer_id, name, total_area_acres, unit,
                    state, district, village, latitude, longitude, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                farm_id, farmer_id, farm_name, total_acres, unit.capitalize(),
                state.strip() if state else "", district, village, latitude, longitude, now_iso, now_iso
            ))

        return {
            "id": farmer_id,
            "name": name_clean,
            "phone": phone_clean,
            "email": email_clean,
            "username": clean_username,
            "state": state,
            "district": district,
            "village": village,
            "latitude": latitude,
            "longitude": longitude,
            "farm_id": farm_id,
            "total_area_acres": total_acres,
            "unit": unit.capitalize(),
            "onboarding_completed": bool(onboarding_completed),
            "preferred_language": (preferred_language or "en").strip().lower(),
            "status": "Active",
        }
    finally:
        conn.close()


def authenticate_farmer(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a farmer via username, phone number or email."""
    init_farm_db()
    conn = get_db_connection()
    try:
        clean_id = identifier.strip().lower()
        row = conn.execute("""
            SELECT * FROM farmers 
            WHERE LOWER(phone) = ? OR LOWER(email) = ? OR LOWER(username) = ?;
        """, (clean_id, clean_id, clean_id)).fetchone()

        if not row:
            return None

        farmer = dict(row)
        if not check_password_hash(farmer["password_hash"], password.strip()):
            return None

        # Return sanitized farmer info with primary farm details
        farmer.pop("password_hash", None)
        farmer["onboarding_completed"] = bool(farmer.get("onboarding_completed", 0))
        farmer["preferred_language"] = farmer.get("preferred_language") or "en"
        p_farm = conn.execute("SELECT id, total_area_acres, unit FROM farms WHERE farmer_id = ? ORDER BY created_at ASC LIMIT 1;", (farmer["id"],)).fetchone()
        if p_farm:
            farmer["farm_id"] = p_farm["id"]
            farmer["total_area_acres"] = p_farm["total_area_acres"]
            farmer["total_land"] = p_farm["total_area_acres"]
            farmer["unit"] = p_farm["unit"]
        return farmer
    finally:
        conn.close()


def verify_farmer_password(farmer_id: str, password: str) -> bool:
    """Verify farmer password for sensitive actions like revoking passkeys or disabling Face Lock."""
    init_farm_db()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT password_hash FROM farmers WHERE id = ?;", (farmer_id,)).fetchone()
        if not row:
            return False
        return check_password_hash(row["password_hash"], (password or "").strip())
    finally:
        conn.close()


def get_farmer_by_id(farmer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve farmer profile by ID."""
    init_farm_db()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM farmers WHERE id = ?;", (farmer_id,)).fetchone()
        if not row:
            return None
        farmer = dict(row)
        farmer.pop("password_hash", None)
        farmer["onboarding_completed"] = bool(farmer.get("onboarding_completed", 0))
        farmer["preferred_language"] = farmer.get("preferred_language") or "en"
        p_farm = conn.execute("SELECT id, total_area_acres, unit FROM farms WHERE farmer_id = ? ORDER BY created_at ASC LIMIT 1;", (farmer["id"],)).fetchone()
        if p_farm:
            farmer["farm_id"] = p_farm["id"]
            farmer["total_area_acres"] = p_farm["total_area_acres"]
            farmer["total_land"] = p_farm["total_area_acres"]
            farmer["unit"] = p_farm["unit"]
        return farmer
    finally:
        conn.close()


def update_farmer_language(farmer_id: str, language: str) -> bool:
    """Update a farmer's preferred language."""
    init_farm_db()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE farmers SET preferred_language = ? WHERE id = ?;", (str(language).strip().lower(), farmer_id))
        return True
    except Exception as e:
        logger.error(f"Error updating farmer language: {e}")
        return False
    finally:
        conn.close()


def update_farmer_onboarding(
    farmer_id: str,
    name: str,
    state: str,
    district: Optional[str] = None,
    village: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    total_land: float = 1.0,
    unit: str = "Acres",
    sections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Complete first-time onboarding for a farmer:
    Persists real farmer location, land holdings, and independent land sections.
    Marks onboarding as complete.
    """
    init_farm_db()
    conn = get_db_connection()
    try:
        now_iso = datetime.now().isoformat()
        factor = LAND_UNIT_TO_ACRES.get((unit or "Acres").strip().lower(), 1.0)
        total_acres = round(float(total_land) * factor, 2)

        with conn:
            # 1. Update farmer profile
            conn.execute("""
                UPDATE farmers
                SET name = ?, state = ?, district = ?, village = ?,
                    latitude = ?, longitude = ?, onboarding_completed = 1
                WHERE id = ?;
            """, (name.strip(), state.strip(), district, village, latitude, longitude, farmer_id))

            # 2. Get or create farm
            farm_row = conn.execute("SELECT id FROM farms WHERE farmer_id = ? ORDER BY created_at ASC LIMIT 1;", (farmer_id,)).fetchone()
            if farm_row:
                farm_id = farm_row["id"]
                conn.execute("""
                    UPDATE farms
                    SET name = ?, total_area_acres = ?, unit = ?, state = ?,
                        district = ?, village = ?, latitude = ?, longitude = ?, updated_at = ?
                    WHERE id = ?;
                """, (f"{name.strip().split()[0]}'s Farm", total_acres, (unit or "Acres").capitalize(),
                      state.strip(), district, village, latitude, longitude, now_iso, farm_id))
            else:
                farm_id = f"farm_{uuid.uuid4().hex[:10]}"
                conn.execute("""
                    INSERT INTO farms (
                        id, farmer_id, name, total_area_acres, unit, state, district, village, latitude, longitude, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (farm_id, farmer_id, f"{name.strip().split()[0]}'s Farm", total_acres, (unit or "Acres").capitalize(),
                      state.strip(), district, village, latitude, longitude, now_iso, now_iso))

            # 3. Add sections if provided
            if sections is not None:
                # Remove existing sections if replacing during onboarding
                conn.execute("DELETE FROM farm_sections WHERE farm_id = ?;", (farm_id,))

                # Check total section area
                total_sec_acres = 0.0
                for sec in sections:
                    s_area = round(float(sec.get("area", 0.0)) * factor, 2)
                    total_sec_acres += s_area

                if total_sec_acres > (total_acres + 0.001):
                    raise ValueError(f"Total section area ({total_sec_acres} {unit}) exceeds total farm land ({total_acres} {unit}).")

                for i, sec in enumerate(sections, 1):
                    s_id = f"sec_{uuid.uuid4().hex[:10]}"
                    s_name = sec.get("name", f"Section {i:02d}").strip()
                    s_area = round(float(sec.get("area", 0.0)) * factor, 2)
                    crop = sec.get("crop", "").strip() or None
                    is_empty = 1 if not crop or crop.lower() in ("empty", "none", "uncultivated") else 0
                    crop_variety = sec.get("crop_variety", "").strip() or None
                    sowing_date = sec.get("sowing_date") or None
                    soil_type = sec.get("soil_type", "Loamy")
                    soil_moisture = float(sec.get("soil_moisture", 35.0))
                    soil_temp = float(sec.get("soil_temp", 22.0))
                    air_temp = float(sec.get("air_temp", 26.0))
                    humidity = float(sec.get("humidity", 55.0))

                    conn.execute("""
                        INSERT INTO farm_sections (
                            id, farm_id, farmer_id, name, area_acres, is_empty,
                            crop, crop_variety, sowing_date, soil_type,
                            soil_moisture, soil_temp, air_temp, humidity,
                            rainfall_7d, forecast_24h, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?);
                    """, (
                        s_id, farm_id, farmer_id, s_name, s_area, is_empty,
                        crop, crop_variety, sowing_date, soil_type,
                        soil_moisture, soil_temp, air_temp, humidity,
                        now_iso, now_iso
                    ))

        return {
            "status": "success",
            "farmer_id": farmer_id,
            "farm_id": farm_id,
            "onboarding_completed": True,
        }
    finally:
        conn.close()


def reset_farmer_password_by_phone(phone: str, new_password: str) -> bool:
    """Reset farmer password securely following mobile OTP verification."""
    init_farm_db()
    conn = get_db_connection()
    try:
        clean_phone = phone.strip()
        pwd_hash = generate_password_hash(new_password.strip())
        with conn:
            cur = conn.execute("UPDATE farmers SET password_hash = ? WHERE phone = ?;", (pwd_hash, clean_phone))
            return cur.rowcount > 0
    finally:
        conn.close()


# ----------------------------------------------------
# Farm & Land Management
# ----------------------------------------------------
def get_farmer_farms(farmer_id: str) -> List[Dict[str, Any]]:
    """Retrieve all farms belonging to a farmer."""
    init_farm_db()
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM farms WHERE farmer_id = ? ORDER BY created_at ASC;
        """, (farmer_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_farm_by_id(farm_id: str, farmer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve specific farm with ownership validation."""
    init_farm_db()
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT * FROM farms WHERE id = ? AND farmer_id = ?;
        """, (farm_id, farmer_id)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def calculate_crop_age_and_stage(crop: Optional[str], sowing_date: Optional[str], is_empty: bool = False) -> Dict[str, Any]:
    """Calculate crop age in days and agronomic growth stage from sowing date."""
    if is_empty or not crop or crop.lower() in ("empty", "none"):
        return {"age_days": 0, "growth_stage": "Empty Land"}

    today = date.today()
    age = 30
    if sowing_date:
        try:
            s_date = datetime.strptime(sowing_date, "%Y-%m-%d").date()
            age = max(1, (today - s_date).days)
        except Exception:
            age = 30

    crop_lower = (crop or "").lower()
    if age <= 20:
        stage = "Initial / Seedling (Germination)"
    elif age <= 50:
        stage = "Vegetative / Tillering" if crop_lower in ("wheat", "rice") else "Vegetative Development"
    elif age <= 80:
        stage = "Flowering / Heading (Reproductive)" if crop_lower in ("wheat", "rice") else "Tuber Initiation / Flowering"
    else:
        stage = "Maturity / Ripening"

    return {"age_days": age, "growth_stage": stage}


def get_farm_sections(farm_id: str, farmer_id: str) -> List[Dict[str, Any]]:
    """Retrieve all sections of a farm belonging to a farmer."""
    init_farm_db()
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM farm_sections 
            WHERE farm_id = ? AND farmer_id = ? 
            ORDER BY name ASC;
        """, (farm_id, farmer_id)).fetchall()

        results = []
        for r in rows:
            sec = dict(r)
            calc = calculate_crop_age_and_stage(
                crop=sec.get("crop"),
                sowing_date=sec.get("sowing_date"),
                is_empty=bool(sec.get("is_empty"))
            )
            sec["crop_age_days"] = calc["age_days"]
            sec["growth_stage"] = calc["growth_stage"]
            results.append(sec)
        return results
    finally:
        conn.close()


def get_section_by_id(section_id: str, farmer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single farm section ensuring farmer authorization."""
    init_farm_db()
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT * FROM farm_sections 
            WHERE id = ? AND farmer_id = ?;
        """, (section_id, farmer_id)).fetchone()
        if not row:
            return None
        sec = dict(row)
        calc = calculate_crop_age_and_stage(
            crop=sec.get("crop"),
            sowing_date=sec.get("sowing_date"),
            is_empty=bool(sec.get("is_empty"))
        )
        sec["crop_age_days"] = calc["age_days"]
        sec["growth_stage"] = calc["growth_stage"]
        return sec
    finally:
        conn.close()


def get_land_summary(farm_id: str, farmer_id: str) -> Dict[str, Any]:
    """Calculate allocated and available land for a farm."""
    farm = get_farm_by_id(farm_id, farmer_id)
    if not farm:
        return {"error": "Farm not found"}

    sections = get_farm_sections(farm_id, farmer_id)
    total_acres = farm["total_area_acres"]

    active_sections = [s for s in sections if not s.get("is_empty")]
    empty_sections = [s for s in sections if s.get("is_empty")]
    cultivated_acres = sum(s["area_acres"] for s in active_sections)
    empty_acres = sum(s["area_acres"] for s in empty_sections)
    unassigned_acres = max(0.0, round(total_acres - sum(s["area_acres"] for s in sections), 3))
    available_acres = round(empty_acres + unassigned_acres, 3)

    return {
        "farm_id": farm_id,
        "farm_name": farm["name"],
        "total_land_acres": total_acres,
        "total_land": total_acres,
        "allocated_acres": round(cultivated_acres, 3),
        "allocated_land": round(cultivated_acres, 3),
        "available_acres": available_acres,
        "available_land": available_acres,
        "unassigned_acres": unassigned_acres,
        "unit": farm.get("unit", "Acres"),
        "total_sections": len(sections),
        "active_sections_count": len(active_sections),
        "empty_sections_count": len(empty_sections),
        "is_fully_allocated": unassigned_acres <= 0.001,
    }


def create_section(
    farm_id: str,
    farmer_id: str,
    name: str,
    area_acres: float,
    is_empty: bool = False,
    crop: Optional[str] = None,
    crop_variety: Optional[str] = None,
    sowing_date: Optional[str] = None,
    soil_type: str = "Loamy",
    soil_moisture: float = 35.0,
    soil_temp: float = 22.0,
    air_temp: float = 26.0,
    humidity: float = 55.0,
    rainfall_7d: float = 0.0,
    forecast_24h: float = 0.0,
) -> Dict[str, Any]:
    """Create a new land section with strict total area validation."""
    init_farm_db()
    summary = get_land_summary(farm_id, farmer_id)
    if "error" in summary:
        raise ValueError(summary["error"])

    area_req = round(float(area_acres), 3)
    if area_req <= 0:
        raise ValueError("Section area must be greater than zero.")

    avail = summary.get("unassigned_acres", summary["available_acres"])
    if area_req > (avail + 0.001):
        raise ValueError(
            f"Cannot allocate {area_req} acres. Only {avail} acres available out of {summary['total_land_acres']} acres total."
        )

    now_iso = datetime.now().isoformat()
    sec_id = f"sec_{uuid.uuid4().hex[:10]}"
    empty_val = 1 if is_empty or not crop or crop.lower() == "empty" else 0
    actual_crop = None if empty_val else crop.strip()

    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO farm_sections (
                    id, farm_id, farmer_id, name, area_acres, is_empty,
                    crop, crop_variety, sowing_date, soil_type,
                    soil_moisture, soil_temp, air_temp, humidity,
                    rainfall_7d, forecast_24h, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                sec_id, farm_id, farmer_id, name.strip(), area_req, empty_val,
                actual_crop, crop_variety, sowing_date, soil_type,
                soil_moisture, soil_temp, air_temp, humidity,
                rainfall_7d, forecast_24h, now_iso, now_iso
            ))
        return get_section_by_id(sec_id, farmer_id)
    finally:
        conn.close()


def update_section(
    section_id: str,
    farmer_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Update section details with area constraint validation."""
    init_farm_db()
    existing = get_section_by_id(section_id, farmer_id)
    if not existing:
        raise ValueError("Section not found or unauthorized.")

    farm_id = existing["farm_id"]
    summary = get_land_summary(farm_id, farmer_id)
    new_area = float(data.get("area_acres", existing["area_acres"]))

    # Check if area changed and if new area fits
    if abs(new_area - existing["area_acres"]) > 0.001:
        available_if_freed = summary["available_acres"] + existing["area_acres"]
        if new_area > (available_if_freed + 0.001):
            raise ValueError(
                f"Cannot update to {new_area} acres. Maximum allocatable is {available_if_freed} acres."
            )

    is_empty = bool(data.get("is_empty", existing["is_empty"]))
    crop = data.get("crop", existing["crop"])
    if is_empty or not crop or str(crop).lower() == "empty":
        is_empty = True
        crop = None

    now_iso = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                UPDATE farm_sections SET
                    name = ?,
                    area_acres = ?,
                    is_empty = ?,
                    crop = ?,
                    crop_variety = ?,
                    sowing_date = ?,
                    soil_type = ?,
                    soil_moisture = ?,
                    soil_temp = ?,
                    air_temp = ?,
                    humidity = ?,
                    rainfall_7d = ?,
                    forecast_24h = ?,
                    updated_at = ?
                WHERE id = ? AND farmer_id = ?;
            """, (
                data.get("name", existing["name"]),
                round(new_area, 3),
                1 if is_empty else 0,
                crop,
                data.get("crop_variety", existing["crop_variety"]),
                data.get("sowing_date", existing["sowing_date"]),
                data.get("soil_type", existing["soil_type"]),
                float(data.get("soil_moisture", existing["soil_moisture"])),
                float(data.get("soil_temp", existing["soil_temp"])),
                float(data.get("air_temp", existing["air_temp"])),
                float(data.get("humidity", existing["humidity"])),
                float(data.get("rainfall_7d", existing["rainfall_7d"])),
                float(data.get("forecast_24h", existing["forecast_24h"])),
                now_iso,
                section_id,
                farmer_id,
            ))
        return get_section_by_id(section_id, farmer_id)
    finally:
        conn.close()


def delete_section(section_id: str, farmer_id: str) -> bool:
    """Delete a section and its schedules."""
    init_farm_db()
    conn = get_db_connection()
    try:
        with conn:
            # Delete schedules for section
            conn.execute("DELETE FROM smart_irrigation_schedules WHERE section_id = ? AND farmer_id = ?;", (section_id, farmer_id))
            cur = conn.execute("DELETE FROM farm_sections WHERE id = ? AND farmer_id = ?;", (section_id, farmer_id))
            return cur.rowcount > 0
    finally:
        conn.close()


# ----------------------------------------------------
# Section-Wise Irrigation Prediction & Area-Scaled Water
# ----------------------------------------------------
def predict_section_irrigation(
    section_id: str,
    farmer_id: str,
    override_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run prediction specifically for an individual section.
    If section is empty, returns NO_IRRIGATION without running the model.
    Scales water requirement precisely by section land area.
    """
    sec = get_section_by_id(section_id, farmer_id)
    if not sec:
        raise ValueError("Section not found.")

    if sec.get("is_empty") or not sec.get("crop"):
        return {
            "section_id": section_id,
            "section_name": sec["name"],
            "area_acres": sec["area_acres"],
            "status": "DO NOT IRRIGATE",
            "is_empty": True,
            "crop": "Empty",
            "irrigation_required": False,
            "water_requirement_liters": 0.0,
            "reason": "This land section is uncultivated / empty. No irrigation is needed.",
            "schedules": [],
        }

    farm = get_farm_by_id(sec["farm_id"], farmer_id)
    state = farm["state"] if farm else "Punjab"

    # Merge section parameters with any user-provided live overrides
    moisture = float(override_data.get("soil_moisture") if override_data and "soil_moisture" in override_data else sec["soil_moisture"])
    if sec.get("crop") and sec["crop"].lower() in ("rice", "paddy"):
        if moisture < -25.0 or moisture > 5.0:
            moisture = -10.0
    soil_temp = float(override_data.get("soil_temp") if override_data and "soil_temp" in override_data else sec["soil_temp"])
    air_temp = float(override_data.get("air_temp") if override_data and "air_temp" in override_data else sec["air_temp"])
    humidity = float(override_data.get("humidity") if override_data and "humidity" in override_data else sec["humidity"])
    rainfall_7d = float(override_data.get("rainfall_7d") if override_data and "rainfall_7d" in override_data else sec["rainfall_7d"])
    forecast_24h = float(override_data.get("forecast_24h") if override_data and "forecast_24h" in override_data else sec["forecast_24h"])

    from src.irrigation_service import IrrigationService
    service = IrrigationService.get_instance()

    pred_input = {
        "state": state,
        "crop": sec["crop"],
        "crop_age_days": sec.get("crop_age_days", 35),
        "sensor_reading": moisture,
        "soil_temp": soil_temp,
        "air_temp": air_temp,
        "humidity": humidity,
        "rainfall_7d": rainfall_7d,
        "forecast_24h": forecast_24h,
    }
    result = service.predict(pred_input)

    # Area scaling calculation
    crop_lower = sec["crop"].lower().strip()
    base_per_acre = CROP_BASE_LITERS_PER_ACRE.get(crop_lower, 900.0)
    area = sec["area_acres"]

    # Calculate deficit severity
    trigger = float(result.get("irrigation_trigger") or 40.0)
    deficit_multiplier = 1.0
    if result.get("reading_unit") == "%" and trigger > 0 and moisture < (trigger * 0.75):
        deficit_multiplier = 1.15
    elif result.get("reading_unit") == "cm" and moisture <= -20.0:
        deficit_multiplier = 1.15

    scaled_water_liters = round(base_per_acre * area * deficit_multiplier, 0)
    duration_mins = max(20, min(120, int(scaled_water_liters / 10)))

    result["section_id"] = section_id
    result["section_name"] = sec["name"]
    result["area_acres"] = area
    result["water_requirement_liters"] = scaled_water_liters if result.get("status") == "IRRIGATE" else 0.0
    result["duration_minutes"] = duration_mins if result.get("status") == "IRRIGATE" else 0
    result["is_empty"] = False
    result["schedules"] = get_section_schedules(section_id, farmer_id)
    return result


# ----------------------------------------------------
# Section-Wise Spaced Scheduling Engine
# ----------------------------------------------------
def schedule_section_irrigation(
    section_id: str,
    farmer_id: str,
    start_date: Optional[str] = None,
    planning_period_days: int = 7,
    forecast_24h: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Generate an independent multi-day schedule for a specific section.
    Allows farmer to choose start_date and planning period (e.g. 7 days).
    Does NOT schedule every day; spaces sessions by crop interval.
    """
    sec = get_section_by_id(section_id, farmer_id)
    if not sec or sec.get("is_empty") or not sec.get("crop"):
        return []

    farm = get_farm_by_id(sec["farm_id"], farmer_id)
    state = farm["state"] if farm else "Punjab"

    crop = sec["crop"]
    crop_lower = crop.lower().strip()
    interval_days = CROP_INTERVALS.get(crop_lower, 3)
    base_per_acre = CROP_BASE_LITERS_PER_ACRE.get(crop_lower, 900.0)
    area = sec["area_acres"]
    water_liters = round(base_per_acre * area, 0)
    duration_mins = max(20, min(120, int(water_liters / 10)))

    # Parse starting date
    base_dt = datetime.now()
    if start_date:
        try:
            base_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except Exception:
            base_dt = datetime.now()

    # Determine spaced sessions within the planning period
    rain_delay = 2 if forecast_24h >= 5.0 else 0
    sessions = []
    current_day_offset = rain_delay

    while current_day_offset < planning_period_days:
        session_date = base_dt + timedelta(days=current_day_offset)
        date_str = session_date.strftime("%Y-%m-%d")

        is_first = (len(sessions) == 0)
        status = "Rescheduled" if (is_first and rain_delay > 0) else ("Pending" if is_first else "Upcoming")

        if is_first:
            reason = f"Initial root-zone replenishment for {sec['name']} ({crop}, {area} ac)."
            if rain_delay > 0:
                reason += f" Delayed by {rain_delay} days due to {forecast_24h:.1f} mm rain forecast."
        else:
            reason = f"Spaced cycle maintenance for {sec['name']} to maintain field capacity without overwatering."

        sessions.append({
            "section_id": section_id,
            "farm_id": sec["farm_id"],
            "farmer_id": farmer_id,
            "crop": crop,
            "state": state,
            "irrigation_date": date_str,
            "date_display": session_date.strftime("%B %d"),
            "recommended_time": "06:00 AM",
            "water_quantity_liters": water_liters,
            "duration_minutes": duration_mins,
            "status": status,
            "reason": reason,
            "planning_period_days": planning_period_days,
        })

        # Advance by crop interval days
        current_day_offset += interval_days

    # Persist sessions into database, preserving completed history for this section
    init_farm_db()
    conn = get_db_connection()
    now_iso = datetime.now().isoformat()
    saved = []
    try:
        with conn:
            # Delete old Upcoming/Pending/Rescheduled for this specific section only
            conn.execute("""
                DELETE FROM smart_irrigation_schedules 
                WHERE section_id = ? AND status IN ('Upcoming', 'Pending', 'Rescheduled');
            """, (section_id,))

            for idx, s in enumerate(sessions):
                sched_id = f"sched_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}_{idx+1}"
                conn.execute("""
                    INSERT INTO smart_irrigation_schedules (
                        id, farm_id, farmer_id, section_id, crop, state,
                        irrigation_date, recommended_time, water_quantity_liters,
                        duration_minutes, status, reason, planning_period_days,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    sched_id, s["farm_id"], s["farmer_id"], s["section_id"], s["crop"], s["state"],
                    s["irrigation_date"], s["recommended_time"], s["water_quantity_liters"],
                    s["duration_minutes"], s["status"], s["reason"], s["planning_period_days"],
                    now_iso, now_iso
                ))
                s["id"] = sched_id
                saved.append(s)
        return saved
    finally:
        conn.close()


def get_section_schedules(section_id: str, farmer_id: str) -> List[Dict[str, Any]]:
    """Retrieve all schedules for a specific section."""
    init_farm_db()
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM smart_irrigation_schedules 
            WHERE section_id = ? AND farmer_id = ? 
            ORDER BY irrigation_date ASC;
        """, (section_id, farmer_id)).fetchall()

        results = []
        for r in rows:
            dt = datetime.strptime(r["irrigation_date"], "%Y-%m-%d")
            results.append({
                "id": r["id"],
                "section_id": r["section_id"],
                "farm_id": r["farm_id"],
                "farmer_id": r["farmer_id"],
                "crop": r["crop"],
                "state": r["state"],
                "irrigation_date": r["irrigation_date"],
                "date_display": dt.strftime("%B %d"),
                "recommended_time": r["recommended_time"],
                "water_quantity_liters": r["water_quantity_liters"],
                "duration_minutes": r["duration_minutes"],
                "status": r["status"],
                "reason": r["reason"],
                "completed_at": r["completed_at"],
                "updated_at": r["updated_at"],
            })
        return results
    finally:
        conn.close()


def update_section_schedule_status(
    schedule_id: str,
    farmer_id: str,
    new_status: str,
    skip_reason: Optional[str] = None,
    forecast_24h: float = 0.0,
) -> Dict[str, Any]:
    """
    Update status of an individual section's schedule.
    Mark Completed: saves timestamp, turns green.
    Skip: marks red, triggers AI reassessment to reschedule session to following dry date.
    """
    init_farm_db()
    conn = get_db_connection()
    now_iso = datetime.now().isoformat()
    try:
        with conn:
            row = conn.execute("""
                SELECT * FROM smart_irrigation_schedules 
                WHERE id = ? AND farmer_id = ?;
            """, (schedule_id, farmer_id)).fetchone()
            if not row:
                return {"success": False, "error": "Schedule not found or unauthorized"}

            sess = dict(row)

            if new_status == "Completed":
                conn.execute("""
                    UPDATE smart_irrigation_schedules 
                    SET status = 'Completed', completed_at = ?, updated_at = ?
                    WHERE id = ?;
                """, (now_iso, now_iso, schedule_id))
                return {
                    "success": True,
                    "action": "completed",
                    "schedule_id": schedule_id,
                    "status": "Completed",
                }

            elif new_status == "Skipped":
                reason_suf = f" [Skipped: {skip_reason}]" if skip_reason else " [Skipped by farmer]"
                conn.execute("""
                    UPDATE smart_irrigation_schedules 
                    SET status = 'Skipped', reason = reason || ?, updated_at = ?
                    WHERE id = ?;
                """, (reason_suf, now_iso, schedule_id))

                # Reassess: calculate new recommended date
                old_dt = datetime.strptime(sess["irrigation_date"], "%Y-%m-%d")
                today = datetime.now().date()
                base_resched = max(old_dt.date(), today)
                delay = 2 if forecast_24h >= 5.0 else 1
                new_date = base_resched + timedelta(days=delay)

                # Avoid date conflicts on this specific section
                existing_dates = set(r["irrigation_date"] for r in conn.execute("""
                    SELECT irrigation_date FROM smart_irrigation_schedules
                    WHERE section_id = ? AND status IN ('Upcoming', 'Pending', 'Rescheduled');
                """, (sess["section_id"],)).fetchall())

                while new_date.strftime("%Y-%m-%d") in existing_dates:
                    new_date += timedelta(days=1)

                new_date_str = new_date.strftime("%Y-%m-%d")
                new_id = f"sched_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}_resched"
                resched_reason = (
                    f"AI Reassessment: Rescheduled from {old_dt.strftime('%B %d')} (skipped). "
                    f"Preserves crop water quota without double-counting."
                )

                conn.execute("""
                    INSERT INTO smart_irrigation_schedules (
                        id, farm_id, farmer_id, section_id, crop, state,
                        irrigation_date, recommended_time, water_quantity_liters,
                        duration_minutes, status, reason, planning_period_days,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    new_id, sess["farm_id"], sess["farmer_id"], sess["section_id"], sess["crop"], sess["state"],
                    new_date_str, sess["recommended_time"], sess["water_quantity_liters"],
                    sess["duration_minutes"], "Rescheduled", resched_reason, sess.get("planning_period_days", 7),
                    now_iso, now_iso
                ))

                return {
                    "success": True,
                    "action": "rescheduled",
                    "skipped_id": schedule_id,
                    "rescheduled_id": new_id,
                    "new_date": new_date_str,
                }
            else:
                conn.execute("""
                    UPDATE smart_irrigation_schedules 
                    SET status = ?, updated_at = ?
                    WHERE id = ?;
                """, (new_status, now_iso, schedule_id))
                return {"success": True, "schedule_id": schedule_id, "status": new_status}
    finally:
        conn.close()


# ----------------------------------------------------
# Global Combined Farmer Calendar
# ----------------------------------------------------
def get_farmer_combined_calendar(farmer_id: str, year: int, month: int) -> Dict[str, Any]:
    """
    Combined view aggregating all irrigation schedules across all sections for a farmer.
    Does NOT merge or modify the underlying section records.
    """
    init_farm_db()
    conn = get_db_connection()
    try:
        month_str = f"{year:04d}-{month:02d}-%"
        rows = conn.execute("""
            SELECT s.*, sec.name as section_name, sec.area_acres 
            FROM smart_irrigation_schedules s
            LEFT JOIN farm_sections sec ON s.section_id = sec.id
            WHERE s.farmer_id = ? AND s.irrigation_date LIKE ?
            ORDER BY s.irrigation_date ASC, s.recommended_time ASC;
        """, (farmer_id, month_str)).fetchall()

        daily_map: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            date_key = r["irrigation_date"]
            if date_key not in daily_map:
                dt = datetime.strptime(date_key, "%Y-%m-%d")
                daily_map[date_key] = {
                    "date": date_key,
                    "date_display": dt.strftime("%B %d"),
                    "sections_count": 0,
                    "total_water_liters": 0.0,
                    "items": [],
                    "has_upcoming": False,
                    "has_completed": False,
                    "has_skipped": False,
                }

            entry = daily_map[date_key]
            entry["sections_count"] += 1
            entry["total_water_liters"] += r["water_quantity_liters"]
            st = r["status"]
            if st in ("Upcoming", "Pending", "Rescheduled"):
                entry["has_upcoming"] = True
            elif st == "Completed":
                entry["has_completed"] = True
            elif st == "Skipped":
                entry["has_skipped"] = True

            entry["items"].append({
                "schedule_id": r["id"],
                "section_id": r["section_id"],
                "section_name": r["section_name"] or "Section",
                "crop": r["crop"],
                "area_acres": r["area_acres"] or 0.0,
                "water_quantity_liters": r["water_quantity_liters"],
                "recommended_time": r["recommended_time"],
                "status": r["status"],
                "reason": r["reason"],
            })

        # Determine dominant day color status for calendar display
        for d, data in daily_map.items():
            if data["has_upcoming"]:
                data["day_status"] = "upcoming"  # Blue
            elif data["has_completed"] and not data["has_skipped"]:
                data["day_status"] = "completed"  # Green
            elif data["has_skipped"] and not data["has_completed"]:
                data["day_status"] = "skipped"  # Red
            elif data["has_completed"] and data["has_skipped"]:
                data["day_status"] = "mixed"
            else:
                data["day_status"] = "none"

        f_row = conn.execute("SELECT name FROM farmers WHERE id = ?;", (farmer_id,)).fetchone()
        farmer_name = f_row["name"] if f_row else "Farmer"

        return {
            "farmer_id": farmer_id,
            "farmer_name": farmer_name,
            "year": year,
            "month": month,
            "days": daily_map,
            "daily_schedule": daily_map,
            "total_sessions": len(rows),
        }
    finally:
        conn.close()


# ----------------------------------------------------
# Pre-Seeding Demo Accounts (Farmer A & Farmer B)
# ----------------------------------------------------
def seed_demo_accounts():
    """Seed test and demonstration farmer accounts if not already present."""
    init_farm_db()
    conn = get_db_connection()
    try:
        # Check if Farmer A exists
        row_a = conn.execute("SELECT id FROM farmers WHERE phone = '9876543210';").fetchone()
        fa_id = row_a["id"] if row_a else None
        farm_a_id = None
        if fa_id:
            farm_row = conn.execute("SELECT id FROM farms WHERE farmer_id = ? LIMIT 1;", (fa_id,)).fetchone()
            farm_a_id = farm_row["id"] if farm_row else None

        sec_count_a = conn.execute("SELECT COUNT(*) FROM farm_sections WHERE farmer_id = ?;", (fa_id,)).fetchone()[0] if fa_id else 0

        if not row_a or sec_count_a == 0:
            if not row_a:
                fa = register_farmer(
                    name="Ramesh Kumar",
                    phone="9876543210",
                    password="farmer123",
                    email="ramesh@krishi.in",
                    state="Punjab",
                    district="Ludhiana",
                    village="Sahnewal",
                    latitude=30.9010,
                    longitude=75.8573,
                    total_land=1.00,
                    unit="Acres",
                )
                fa_id = fa["id"]
                farm_a_id = fa["farm_id"]
            
            # If farmer exists but farm missing
            if not farm_a_id:
                farm_row = conn.execute("SELECT id FROM farms WHERE farmer_id = ? LIMIT 1;", (fa_id,)).fetchone()
                farm_a_id = farm_row["id"] if farm_row else None

            # Create Section 1 (0.50 Acre Wheat)
            s1 = create_section(
                farm_id=farm_a_id,
                farmer_id=fa_id,
                name="Section 01",
                area_acres=0.50,
                is_empty=False,
                crop="Wheat",
                crop_variety="HD-3086",
                sowing_date=(datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d"),
                soil_type="Alluvial Loam",
                soil_moisture=25.0,  # Below trigger 40% -> IRRIGATE
                soil_temp=20.0,
                air_temp=24.0,
                humidity=50.0,
            )
            # Create Section 2 (0.30 Acre Potato)
            s2 = create_section(
                farm_id=farm_a_id,
                farmer_id=fa_id,
                name="Section 02",
                area_acres=0.30,
                is_empty=False,
                crop="Potato",
                crop_variety="Kufri Jyoti",
                sowing_date=(datetime.now() - timedelta(days=25)).strftime("%Y-%m-%d"),
                soil_type="Sandy Loam",
                soil_moisture=30.0,  # Needs irrigation
                soil_temp=22.0,
                air_temp=25.0,
                humidity=55.0,
            )
            # Create Section 3 (0.20 Acre Empty)
            create_section(
                farm_id=farm_a_id,
                farmer_id=fa_id,
                name="Section 03",
                area_acres=0.20,
                is_empty=True,
                crop="Empty",
            )
            # Generate initial schedules for Section 1 and Section 2
            schedule_section_irrigation(s1["id"], fa_id, planning_period_days=7)
            schedule_section_irrigation(s2["id"], fa_id, planning_period_days=7)
            logger.info("Seeded Demo Farmer A (Ramesh Kumar - 1 Acre: Wheat, Potato, Empty).")

        # Check if Farmer B exists
        row_b = conn.execute("SELECT id FROM farmers WHERE phone = '9876543211';").fetchone()
        fb_id = row_b["id"] if row_b else None
        farm_b_id = None
        if fb_id:
            farm_row_b = conn.execute("SELECT id FROM farms WHERE farmer_id = ? LIMIT 1;", (fb_id,)).fetchone()
            farm_b_id = farm_row_b["id"] if farm_row_b else None

        sec_count_b = conn.execute("SELECT COUNT(*) FROM farm_sections WHERE farmer_id = ?;", (fb_id,)).fetchone()[0] if fb_id else 0

        if not row_b or sec_count_b == 0:
            if not row_b:
                fb = register_farmer(
                    name="Suresh Patel",
                    phone="9876543211",
                    password="farmer123",
                    email="suresh@krishi.in",
                    state="Andhra Pradesh",
                    district="Guntur",
                    village="Tenali",
                    latitude=16.2437,
                    longitude=80.6400,
                    total_land=2.00,
                    unit="Acres",
                )
                fb_id = fb["id"]
                farm_b_id = fb["farm_id"]

            if not farm_b_id:
                farm_row_b = conn.execute("SELECT id FROM farms WHERE farmer_id = ? LIMIT 1;", (fb_id,)).fetchone()
                farm_b_id = farm_row_b["id"] if farm_row_b else None

            # Section 1: 1.00 Acre Rice
            s1_b = create_section(
                farm_id=farm_b_id,
                farmer_id=fb_id,
                name="Section 01",
                area_acres=1.00,
                is_empty=False,
                crop="Rice",
                crop_variety="BPT 5204 (Samba Mahsuri)",
                sowing_date=(datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d"),
                soil_type="Clayey Loam",
                soil_moisture=-18.0,  # Below -15 cm AWD trigger -> IRRIGATE
                soil_temp=26.0,
                air_temp=30.0,
                humidity=70.0,
            )
            # Section 2: 1.00 Acre Empty
            create_section(
                farm_id=farm_b_id,
                farmer_id=fb_id,
                name="Section 02",
                area_acres=1.00,
                is_empty=True,
                crop="Empty",
            )
            schedule_section_irrigation(s1_b["id"], fb_id, planning_period_days=7)
            logger.info("Seeded Demo Farmer B (Suresh Patel - 2 Acres: Rice, Empty).")

        # Ensure demo farmers have usernames and completed onboarding
        conn.execute("UPDATE farmers SET username = 'ramesh', onboarding_completed = 1 WHERE phone = '9876543210' AND (username IS NULL OR onboarding_completed = 0);")
        conn.execute("UPDATE farmers SET username = 'suresh', onboarding_completed = 1 WHERE phone = '9876543211' AND (username IS NULL OR onboarding_completed = 0);")
        conn.commit()
    finally:
        conn.close()
