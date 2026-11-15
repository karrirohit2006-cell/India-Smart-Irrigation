"""
Generate crisp, high-resolution screenshots for:
1. Login Page (/)
2. Create Account Page (/register)
3. Biometric Passkey Login (Face ID / Fingerprint / PIN modal & button)
4. First-Time Setup Wizard (/onboarding) - 4-step clean wizard without sections
5. Farmer Dashboard (/dashboard) - Land Sections with Add, Edit, Remove & Dedicated Breadcrumb
6. Add Land Section Modal - Asks ONLY for Section Name, Plot Area, Crop Type
"""

import os
import subprocess
import shutil
import secrets
from app import app
from src.farm_manager import init_farm_db, seed_demo_accounts

edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(edge_path):
    edge_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

shots_dir = os.path.abspath("screenshots")
brain_shots_dir = r"C:\Users\karri\.gemini\antigravity\brain\c199eae1-839e-4bc7-8524-f83081371aa8\screenshots"
os.makedirs(shots_dir, exist_ok=True)
os.makedirs(brain_shots_dir, exist_ok=True)

init_farm_db()
seed_demo_accounts()

# Read static CSS files
style_css_path = os.path.abspath("static/style.css")
with open(style_css_path, "r", encoding="utf-8") as f:
    style_css = f.read()

static_dir_url = "file:///" + os.path.abspath("static").replace("\\", "/") + "/"

import re

def take_shot_from_html(html_str, filename, width=1280, height=850):
    # Embed style.css directly so no network/socket is required
    injected_html = re.sub(r'<link[^>]*style\.css[^>]*>', f'<style>{style_css}</style>', html_str, flags=re.IGNORECASE)
    injected_html = injected_html.replace('/static/', static_dir_url)

    tmp_file = os.path.join(shots_dir, f"tmp_{filename}.html")
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(injected_html)
    
    file_url = "file:///" + tmp_file.replace("\\", "/")
    target_path = os.path.join(shots_dir, filename)
    brain_path = os.path.join(brain_shots_dir, filename)
    
    subprocess.run([
        edge_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
        f"--window-size={width},{height}",
        f"--screenshot={target_path}",
        file_url
    ], check=True)
    
    if os.path.exists(target_path):
        shutil.copyfile(target_path, brain_path)
        print(f"Captured {filename}: {os.path.getsize(target_path)} bytes")
    
    try:
        os.remove(tmp_file)
    except Exception:
        pass

with app.test_client() as client:
    # 1. Login Page
    login_html = client.get("/").get_data(as_text=True)
    take_shot_from_html(login_html, "1_farmer_login_page.png")

    # 2. Register Page
    reg_html = client.get("/register").get_data(as_text=True)
    take_shot_from_html(reg_html, "2_farmer_create_account_page.png", height=950)

    # 3. Face Lock Setup Screen during registration
    bio_html = reg_html.replace('id="faceLockSetupModal" class="modal-overlay" style="display: none;"',
                                'id="faceLockSetupModal" class="modal-overlay" style="display: flex;"')
    take_shot_from_html(bio_html, "3_biometric_login.png")

    # 4. 4-Step Onboarding Wizard
    from src.farm_manager import get_db_connection, register_farmer
    conn = get_db_connection()
    ob_farmer = conn.execute("SELECT * FROM farmers WHERE onboarding_completed = 0 AND status = 'Active' LIMIT 1;").fetchone()
    if not ob_farmer:
        ob_farmer = register_farmer(username=f"onb_{secrets.token_hex(4)}", password="Password123!", onboarding_completed=0)
    farmer_id = ob_farmer["id"]
    conn.close()

    with client.session_transaction() as sess:
        sess["farmer_id"] = farmer_id
    
    ob_res = client.get("/onboarding")
    ob_html = ob_res.get_data(as_text=True)
    take_shot_from_html(ob_html, "4_first_time_onboarding.png", height=920)

    # 5. Farmer Dashboard (Ramesh Kumar - showing breadcrumb and section cards)
    client.post("/api/auth/login", json={"username": "ramesh", "password": "farmer123"})
    dash_html = client.get("/dashboard").get_data(as_text=True)
    take_shot_from_html(dash_html, "5_farmer_dashboard.png", height=900)

    # 6. Add/Edit Land Section Modal (showing ONLY Section Name, Plot Area, Crop Type)
    sec_modal_html = dash_html.replace('id="sectionModal" class="custom-modal" style="display: none;"',
                                       'id="sectionModal" class="custom-modal" style="display: flex;"')
    take_shot_from_html(sec_modal_html, "6_section_modal_simplified.png", height=900)

print("ALL SCREENSHOTS GENERATED SUCCESSFULLY!")
