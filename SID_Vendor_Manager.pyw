#!/usr/bin/env python3
"""SID Vendor Manager — GUI for adding and removing vendor portals."""

import tkinter as tk
from tkinter import messagebox, ttk
import os
import subprocess
import shutil
import re
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Brand colors ──
BG = "#f0ecf6"
CARD = "#ffffff"
PURPLE = "#7860a8"
PURPLE_LT = "#9b7ed8"
GREEN = "#5cb88a"
RED = "#d06060"
TEXT = "#1a1a2e"
GRAY = "#64748b"
BORDER = "#ddd8ec"
BLUE = "#5b8dcf"

ANNOUNCEMENTS_FILE = "announcements.json"


def make_button(parent, text, bg_color, hover_color, command, font_size=14, pady=10):
    """Create a macOS-friendly colored button using a Label (tk.Button ignores bg on macOS)."""
    frame = tk.Frame(parent, bg=bg_color, cursor="hand2", bd=0)
    label = tk.Label(frame, text=text, font=("Helvetica Neue", font_size, "bold"),
                     bg=bg_color, fg="white", pady=pady, cursor="hand2")
    label.pack(fill="x")

    def on_enter(e):
        frame.config(bg=hover_color)
        label.config(bg=hover_color)

    def on_leave(e):
        frame.config(bg=bg_color)
        label.config(bg=bg_color)

    def on_click(e):
        command()

    for widget in (frame, label):
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        widget.bind("<Button-1>", on_click)

    return frame


def get_vendors():
    """Return list of (folder_name, display_name) tuples for existing vendors."""
    vendors = []
    for item in sorted(os.listdir(SCRIPT_DIR)):
        d = os.path.join(SCRIPT_DIR, item)
        idx = os.path.join(d, "index.html")
        guide = os.path.join(d, "guide.html")
        if os.path.isdir(d) and os.path.isfile(idx) and os.path.isfile(guide):
            # Try to read display name from the portal's <title>
            try:
                with open(idx, "r") as f:
                    html = f.read(2000)
                m = re.search(r"<title>(.*?) - SID Vendor Portal</title>", html)
                display = m.group(1) if m else item
            except Exception:
                display = item
            vendors.append((item, display))
    return vendors


def get_bulletin_path(folder_name):
    """Return the path to the bulletin JSON file for a vendor."""
    return os.path.join(SCRIPT_DIR, f"bulletin_{folder_name}.json")


def load_bulletin(folder_name):
    """Load today's bulletin for a vendor. Returns dict with date, tasks, notes."""
    path = get_bulletin_path(folder_name)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Return bulletin only if it's from today
            if data.get("date") == today:
                return data
        except Exception:
            pass
    
    return {"date": today, "tasks": [], "notes": ""}


def save_bulletin(folder_name, tasks, notes):
    """Save bulletin for a vendor (overwrites any existing data for today)."""
    today = datetime.now().strftime("%Y-%m-%d")
    path = get_bulletin_path(folder_name)
    data = {
        "date": today,
        "tasks": [t.strip() for t in tasks if t.strip()],
        "notes": notes.strip()
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def has_todays_tasks(folder_name):
    """Check if a vendor has tasks posted for today."""
    bulletin = load_bulletin(folder_name)
    today = datetime.now().strftime("%Y-%m-%d")
    return bulletin.get("date") == today and len(bulletin.get("tasks", [])) > 0


def get_postings_path(folder_name):
    """Return the path to the postings JSON file for a vendor."""
    return os.path.join(SCRIPT_DIR, f"postings_{folder_name}.json")


def load_postings(folder_name):
    """Load job postings for a vendor. Returns dict with categories."""
    path = get_postings_path(folder_name)
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return data
        except Exception:
            pass
    
    return {"categories": {}}


def save_postings(folder_name, data):
    """Save postings for a vendor."""
    path = get_postings_path(folder_name)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def generate_portal(display_name, folder_name, upload_url):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{display_name} - SID Vendor Portal</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Cpath d='M38 12Q36 2 32 5Q34 10 38 14Z' fill='%237a5c3a'/%3E%3Cpath d='M50 8Q50-2 46 2Q48 7 50 12Z' fill='%237a5c3a'/%3E%3Cpath d='M62 12Q64 2 68 5Q66 10 62 14Z' fill='%237a5c3a'/%3E%3Cellipse cx='50' cy='52' rx='38' ry='40' fill='%23d4a96a'/%3E%3Cellipse cx='50' cy='58' rx='28' ry='28' fill='%23e8c88a'/%3E%3Cellipse cx='38' cy='46' rx='10' ry='11' fill='white'/%3E%3Cellipse cx='62' cy='46' rx='10' ry='11' fill='white'/%3E%3Ccircle cx='39' cy='46' r='6' fill='%233b8ed0'/%3E%3Ccircle cx='63' cy='46' r='6' fill='%233b8ed0'/%3E%3Ccircle cx='40' cy='45' r='3' fill='%231a1a2e'/%3E%3Ccircle cx='64' cy='45' r='3' fill='%231a1a2e'/%3E%3Ccircle cx='41' cy='43' r='1.5' fill='white'/%3E%3Ccircle cx='65' cy='43' r='1.5' fill='white'/%3E%3Cellipse cx='50' cy='60' rx='8' ry='6' fill='%238b6baa'/%3E%3Cpath d='M43 68Q50 76 57 68' stroke='%237a5c3a' stroke-width='2' fill='none' stroke-linecap='round'/%3E%3Cellipse cx='18' cy='38' rx='8' ry='10' fill='%23d4a96a'/%3E%3Cellipse cx='82' cy='38' rx='8' ry='10' fill='%23d4a96a'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  /* Color Variables - Light/Dark Mode Support */
  :root {{{{
    --bg-gradient-1: #faf8fd;
    --bg-gradient-2: #f0ecf6;
    --bg-gradient-3: #e8f0fa;
    --bg-gradient-4: #f8fafc;
    --card-bg: #fff;
    --card-border: #ece8f4;
    --card-shadow-1: rgba(120,96,168,0.10);
    --card-shadow-2: rgba(0,0,0,0.04);
    --text-primary: #1a1a2e;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --accent: #9b7ed8;
    --divider: #ece8f4;
    --footer-text: #b0a8c0;
    --help-link: #7860a8;
    --checklist-bg: #f8f6fc;
    --checklist-border: #ece8f4;
    --check-done: #5cb88a;
    --check-pending: #d0d5dd;
  }}}}

  html.dark {{{{
    --bg-gradient-1: #1a1a2e;
    --bg-gradient-2: #1e1e35;
    --bg-gradient-3: #1a2235;
    --bg-gradient-4: #1a1a2e;
    --card-bg: #252540;
    --card-border: #3a3a5c;
    --card-shadow-1: rgba(0,0,0,0.30);
    --card-shadow-2: rgba(0,0,0,0.15);
    --text-primary: #e8e6f0;
    --text-secondary: #a0a8bc;
    --text-muted: #7a8296;
    --accent: #b89ae8;
    --divider: #3a3a5c;
    --footer-text: #6a6a8c;
    --help-link: #b89ae8;
    --checklist-bg: #2a2a48;
    --checklist-border: #3a3a5c;
    --check-done: #5cb88a;
    --check-pending: #4a4a6c;
  }}}}

  /* Reset & Base Styles */
  * {{{{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}}}

  body {{{{
    font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(160deg, var(--bg-gradient-1) 0%, var(--bg-gradient-2) 30%, var(--bg-gradient-3) 70%, var(--bg-gradient-4) 100%);
    padding: 40px 20px;
    transition: background 0.3s, color 0.3s;
  }}}}

  a {{{{
    text-decoration: none;
    color: inherit;
  }}}}

  /* Announcement Banner */
  .announcement {{{{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, #7860a8, #9b7ed8);
    color: #fff;
    text-align: center;
    padding: 10px 40px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
    z-index: 100;
    transform: translateY(-100%);
    transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }}}}

  .announcement.visible {{{{
    transform: translateY(0);
  }}}}

  .announcement .close-btn {{{{
    position: absolute;
    right: 14px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: rgba(255,255,255,0.7);
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
    transition: color 0.2s;
  }}}}

  .announcement .close-btn:hover {{{{
    color: #fff;
  }}}}

  /* Dark Mode Toggle */
  .dark-toggle {{{{
    position: fixed;
    top: 14px;
    right: 14px;
    z-index: 101;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 50%;
    width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: all 0.3s;
  }}}}

  .dark-toggle:hover {{{{
    transform: scale(1.1);
  }}}}

  /* Main Card Container */
  .card {{{{
    background: var(--card-bg);
    border-radius: 24px;
    padding: 48px 40px;
    max-width: 480px;
    width: 100%;
    text-align: center;
    box-shadow: 0 8px 40px var(--card-shadow-1), 0 2px 12px var(--card-shadow-2);
    border: 1px solid var(--card-border);
    transition: background 0.3s, border-color 0.3s, box-shadow 0.3s;
  }}}}

  /* SID Mascot */
  .sid-face {{{{
    margin-bottom: 20px;
    display: inline-block;
  }}}}

  .sid-svg .blink-group {{{{
    animation: blink 4s ease-in-out infinite;
    transform-origin: center;
  }}}}

  .sid-svg .blink-group:nth-child(2) {{{{
    animation-delay: 0.05s;
  }}}}

  @keyframes blink {{{{
    0%, 90%, 100% {{ transform: scaleY(1); }}
    95% {{ transform: scaleY(0.05); }}
  }}}}

  /* Header Text */
  .welcome {{{{
    font-size: 13px;
    color: var(--accent);
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}}}

  h1 {{{{
    font-family: 'Outfit', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 8px;
    letter-spacing: 0.04em;
    transition: color 0.3s;
  }}}}

  .subtitle {{{{
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 28px;
    line-height: 1.7;
    transition: color 0.3s;
  }}}}

  /* Checklist Card */
  .checklist {{{{
    background: var(--checklist-bg);
    border: 1px solid var(--checklist-border);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 24px;
    text-align: left;
    transition: background 0.3s, border-color 0.3s;
  }}}}

  .checklist-title {{{{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--accent);
    margin-bottom: 12px;
  }}}}

  .checklist-item {{{{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 13px;
    color: var(--text-secondary);
    transition: color 0.3s;
  }}}}

  .checklist-item.done {{{{
    color: var(--check-done);
  }}}}

  .checklist-item .check {{{{
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--check-pending);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.3s;
  }}}}

  .checklist-item.done .check {{{{
    background: var(--check-done);
    border-color: var(--check-done);
  }}}}

  .checklist-item.done .check::after {{{{
    content: '\2713';
    color: #fff;
    font-size: 12px;
    font-weight: 700;
  }}}}

  .checklist-item.done .label {{{{
    text-decoration: line-through;
    opacity: 0.7;
  }}}}

  .progress-bar {{{{
    height: 4px;
    background: var(--check-pending);
    border-radius: 2px;
    margin-top: 12px;
    overflow: hidden;
  }}}}

  .progress-fill {{{{
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--check-done));
    border-radius: 2px;
    transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  }}}}

  .checklist.completed {{{{
    animation: checklistDone 0.6s 1.2s forwards;
  }}}}

  @keyframes checklistDone {{{{
    0% {{ opacity: 1; max-height: 200px; margin-bottom: 24px; padding: 18px 20px; }}
    100% {{ opacity: 0; max-height: 0; margin-bottom: 0; padding: 0 20px; overflow: hidden; }}
  }}}}

  .checklist.hidden {{{{
    display: none;
  }}}}

  /* Action Buttons */
  .action {{{{
    display: block;
    width: 100%;
    padding: 16px 24px;
    border-radius: 14px;
    font-size: 14px;
    font-weight: 700;
    font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.5px;
    transition: all 0.2s;
    cursor: pointer;
    border: none;
    margin-bottom: 14px;
  }}}}

  .action.upload {{{{
    background: linear-gradient(135deg, #78cca0, #64bc90);
    color: #fff;
  }}}}

  .action.upload:hover {{{{
    box-shadow: 0 6px 24px rgba(120,204,160,0.35);
    transform: translateY(-2px);
  }}}}

  .action.guide {{{{
    background: linear-gradient(135deg, #9b7ed8, #b89ae8);
    color: #fff;
  }}}}

  .action.guide:hover {{{{
    box-shadow: 0 6px 24px rgba(155,126,216,0.35);
    transform: translateY(-2px);
  }}}}

  .action.install {{{{
    background: linear-gradient(135deg, #6a9cd8, #5b8dcf);
    color: #fff;
  }}}}

  .action.install:hover {{{{
    box-shadow: 0 6px 24px rgba(106,156,216,0.35);
    transform: translateY(-2px);
  }}}}

  .action.installed {{{{
    background: linear-gradient(135deg, #6a9cd8, #5b8dcf);
    color: #fff;
    cursor: default;
    pointer-events: none;
    opacity: 0.9;
  }}}}

  /* Bulletin Board / Tasks Card */
  .bulletin-board {{{{
    background: var(--checklist-bg);
    border: 1px solid var(--checklist-border);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 24px;
    text-align: left;
    transition: background 0.3s, border-color 0.3s;
  }}}}

  .bulletin-board.hidden {{{{
    display: none;
  }}}}

  .bulletin-date {{{{
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 12px;
    font-weight: 500;
  }}}}

  .task-list {{{{
    list-style: none;
  }}}}

  .task-item {{{{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 13px;
    color: var(--text-secondary);
    transition: color 0.3s;
    cursor: pointer;
  }}}}

  .task-item:hover {{{{
    color: var(--text-primary);
  }}}}

  .task-item.completed {{{{
    color: var(--check-done);
  }}}}

  .task-item .task-check {{{{
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--check-pending);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.3s;
  }}}}

  .task-item.completed .task-check {{{{
    background: var(--check-done);
    border-color: var(--check-done);
  }}}}

  .task-item.completed .task-check::after {{{{
    content: '\2713';
    color: #fff;
    font-size: 12px;
    font-weight: 700;
  }}}}

  .task-item.completed .task-label {{{{
    text-decoration: line-through;
    opacity: 0.7;
  }}}}

  .bulletin-notes {{{{
    font-size: 12px;
    color: var(--text-muted);
    font-style: italic;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--checklist-border);
  }}}}

  /* Upload History / Collapsible Section */
  .upload-history {{{{
    margin-bottom: 24px;
  }}}}

  .upload-history-header {{{{
    background: var(--checklist-bg);
    border: 1px solid var(--checklist-border);
    border-radius: 14px;
    padding: 16px 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: background 0.3s, border-color 0.3s;
    user-select: none;
  }}}}

  .upload-history-header:hover {{{{
    background: var(--card-bg);
  }}}}

  .upload-history-arrow {{{{
    font-size: 14px;
    transition: transform 0.3s ease;
    flex-shrink: 0;
  }}}}

  .upload-history-arrow.expanded {{{{
    transform: rotate(90deg);
  }}}}

  .upload-history-title {{{{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--accent);
    flex: 1;
    text-align: left;
  }}}}

  .upload-history-content {{{{
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease, padding 0.3s ease;
  }}}}

  .upload-history-content.expanded {{{{
    max-height: 500px;
    padding-top: 16px;
  }}}}

  .upload-history-body {{{{
    background: var(--checklist-bg);
    border: 1px solid var(--checklist-border);
    border-top: none;
    border-radius: 0 0 14px 14px;
    padding: 16px 20px;
    text-align: left;
  }}}}

  .upload-placeholder {{{{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
  }}}}

  /* Divider & Help Text */
  .divider {{{{
    height: 1px;
    background: var(--divider);
    margin: 24px 0;
    transition: background 0.3s;
  }}}}

  .help-text {{{{
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.7;
    transition: color 0.3s;
  }}}}

  .help-text a {{{{
    color: var(--help-link);
    font-weight: 600;
    transition: color 0.3s;
  }}}}

  /* Footer */
  .footer {{{{
    margin-top: 32px;
    font-size: 12px;
    color: var(--footer-text);
    transition: color 0.3s;
  }}}}

  .footer a {{{{
    color: var(--accent);
    font-weight: 600;
  }}}}
</style>
</head>
<body>
<!-- Announcement Banner -->
<div class="announcement" id="announcement">
  <span id="announcement-text"></span>
  <button class="close-btn" id="closeAnn">&times;</button>
</div>

<!-- Dark Mode Toggle -->
<div class="dark-toggle" id="darkToggle" title="Toggle dark mode">🌙</div>

<!-- Main Portal Card -->
<div class="card">
  <!-- SID Mascot -->
  <div class="sid-face">
    <svg class="sid-svg" width="80" height="80" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <path d="M38 12Q36 2 32 5Q34 10 38 14Z" fill="#7a5c3a"/>
      <path d="M50 8Q50-2 46 2Q48 7 50 12Z" fill="#7a5c3a"/>
      <path d="M62 12Q64 2 68 5Q66 10 62 14Z" fill="#7a5c3a"/>
      <ellipse cx="50" cy="52" rx="38" ry="40" fill="#d4a96a"/>
      <ellipse cx="50" cy="58" rx="28" ry="28" fill="#e8c88a"/>
      <ellipse cx="18" cy="38" rx="8" ry="10" fill="#d4a96a"/>
      <ellipse cx="82" cy="38" rx="8" ry="10" fill="#d4a96a"/>
      <g class="blink-group" style="transform-origin: 38px 46px">
        <ellipse cx="38" cy="46" rx="10" ry="11" fill="white"/>
        <circle class="pupil-l" cx="39" cy="46" r="6" fill="#3b8ed0"/>
        <circle class="iris-l" cx="40" cy="45" r="3" fill="#1a1a2e"/>
        <circle cx="41" cy="43" r="1.5" fill="white"/>
      </g>
      <g class="blink-group" style="transform-origin: 62px 46px">
        <ellipse cx="62" cy="46" rx="10" ry="11" fill="white"/>
        <circle class="pupil-r" cx="63" cy="46" r="6" fill="#3b8ed0"/>
        <circle class="iris-r" cx="64" cy="45" r="3" fill="#1a1a2e"/>
        <circle cx="65" cy="43" r="1.5" fill="white"/>
      </g>
      <ellipse cx="50" cy="60" rx="8" ry="6" fill="#8b6baa"/>
      <path d="M43 68Q50 76 57 68" stroke="#7a5c3a" stroke-width="2" fill="none" stroke-linecap="round"/>
    </svg>
  </div>

  <!-- Welcome Header -->
  <div class="welcome">Welcome</div>
  <h1>{display_name}</h1>
  <p class="subtitle">Your SID vendor portal. Install the extension, read the guide, and upload your files.</p>

  <!-- Onboarding Checklist -->
  <div class="checklist" id="checklist">
    <div class="checklist-title">Getting Started</div>
    <div class="checklist-item" id="check-install"><div class="check"></div><span class="label">Install the SID extension</span></div>
    <div class="checklist-item" id="check-guide"><div class="check"></div><span class="label">Read the vendor guide</span></div>
    <div class="checklist-item" id="check-upload"><div class="check"></div><span class="label">Upload your first ZIP file</span></div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width: 0%"></div></div>
  </div>

  <!-- Action Buttons -->
  <a href="#" id="installBtn" class="action install" onclick="handleInstallClick(event); return false;">
    Install SID Extension
  </a>
  <a href="https://sid.rocks/{folder_name}/guide.html" target="_blank" class="action guide" id="guideBtn">
    Open SID Guide
  </a>
  <a href="{upload_url}" target="_blank" class="action upload" id="uploadBtn">
    Upload ZIP Files
  </a>

  <!-- Bulletin Board / Today's Tasks -->
  <div class="bulletin-board hidden" id="bulletinBoard">
    <div class="checklist-title">Today's Tasks</div>
    <div class="bulletin-date" id="bulletinDate"></div>
    <ul class="task-list" id="taskList"></ul>
    <div class="bulletin-notes hidden" id="bulletinNotes"></div>
  </div>

  <!-- Upload History (Collapsible) -->
  <div class="upload-history">
    <div class="upload-history-header" id="uploadHistoryHeader">
      <span class="upload-history-arrow" id="uploadHistoryArrow">▶</span>
      <div class="upload-history-title">Recent Uploads</div>
    </div>
    <div class="upload-history-content" id="uploadHistoryContent">
      <div class="upload-history-body">
        <p class="upload-placeholder">Upload tracking coming soon — check your OneDrive folder directly.</p>
      </div>
    </div>
  </div>

  <!-- Divider -->
  <div class="divider"></div>

  <!-- Help Text -->
  <p class="help-text">
    No sign-in needed to upload. Just click, select your ZIP file, and you're done.<br>
    Questions? Email <a href="mailto:mallen@wallstjobs.com?subject=SID%20Portal%20-%20Question">Melissa</a>.
  </p>
</div>

<!-- Footer -->
<div class="footer">Powered by <a href="https://sid.rocks">sid.rocks</a></div>

<script>
/* ============================================================================
   DARK MODE
   ========================================================================== */
const darkToggle = document.getElementById('darkToggle');
let darkMode = false;

try {{{{
  darkMode = localStorage.getItem('sid_dark') === '1';
}}}} catch (e) {{{{
  // localStorage may not be available
}}}}

if (darkMode) {{{{
  document.documentElement.classList.add('dark');
  darkToggle.textContent = '☀️';
}}}}

darkToggle.addEventListener('click', () => {{{{
  darkMode = !darkMode;
  document.documentElement.classList.toggle('dark', darkMode);
  darkToggle.textContent = darkMode ? '☀️' : '🌙';
  try {{{{
    localStorage.setItem('sid_dark', darkMode ? '1' : '0');
  }}}} catch (e) {{{{
    // localStorage may not be available
  }}}}
}}}});

/* ============================================================================
   EYE TRACKING
   ========================================================================== */
const svg = document.querySelector('.sid-svg');
const pupilL = svg.querySelector('.pupil-l');
const irisL = svg.querySelector('.iris-l');
const pupilR = svg.querySelector('.pupil-r');
const irisR = svg.querySelector('.iris-r');

document.addEventListener('mousemove', (e) => {{{{
  const rect = svg.getBoundingClientRect();
  const dx = e.clientX - (rect.left + rect.width / 2);
  const dy = e.clientY - (rect.top + rect.height / 2);
  const distance = Math.sqrt(dx * dx + dy * dy);
  const factor = Math.min(distance / 200, 1) * 2.5;
  const angle = Math.atan2(dy, dx);
  const moveX = Math.cos(angle) * factor;
  const moveY = Math.sin(angle) * factor;

  pupilL.setAttribute('cx', 39 + moveX);
  pupilL.setAttribute('cy', 46 + moveY);
  irisL.setAttribute('cx', 40 + moveX);
  irisL.setAttribute('cy', 45 + moveY);

  pupilR.setAttribute('cx', 63 + moveX);
  pupilR.setAttribute('cy', 46 + moveY);
  irisR.setAttribute('cx', 64 + moveX);
  irisR.setAttribute('cy', 45 + moveY);
}}}});

/* ============================================================================
   CHECKLIST
   ========================================================================== */
const CHECKLIST_STORAGE_KEY = 'sid_checklist_{folder_name}';
let savedState = {{}};

try {{{{
  savedState = JSON.parse(localStorage.getItem(CHECKLIST_STORAGE_KEY) || '{{}}');
}}}} catch (e) {{{{
  // localStorage may not be available
}}}}

let installDone = savedState.install || false;
let guideDone = savedState.guide || false;
let uploadDone = savedState.upload || false;
let checklistCompleted = savedState.completed || false;

function saveChecklistState() {{{{
  try {{{{
    localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify({{{{
      install: installDone,
      guide: guideDone,
      upload: uploadDone,
      completed: checklistCompleted
    }}}});
  }}}} catch (e) {{{{
    // localStorage may not be available
  }}}}
}}}}

function updateChecklist() {{{{
  const checklistEl = document.getElementById('checklist');
  const items = [installDone, guideDone, uploadDone];
  const completedCount = items.filter(Boolean).length;
  const percentComplete = Math.round(completedCount / 3 * 100);

  if (checklistCompleted) {{{{
    checklistEl.classList.add('hidden');
    updateInstallButton();
    return;
  }}}}

  document.getElementById('check-install').classList.toggle('done', installDone);
  document.getElementById('check-guide').classList.toggle('done', guideDone);
  document.getElementById('check-upload').classList.toggle('done', uploadDone);
  document.getElementById('progressFill').style.width = percentComplete + '%';

  updateInstallButton();

  if (completedCount === 3) {{{{
    checklistCompleted = true;
    saveChecklistState();
    checklistEl.classList.add('completed');
    checklistEl.addEventListener('animationend', () => {{{{
      checklistEl.classList.add('hidden');
    }}}}, {{ once: true }});
  }}}}

  saveChecklistState();
}}}}

function updateInstallButton() {{{{
  const btn = document.getElementById('installBtn');
  if (installDone) {{{{
    btn.classList.add('installed');
    btn.classList.remove('install');
    btn.innerHTML = '✓ SID Extension Installed';
    btn.removeAttribute('href');
    btn.style.cursor = 'default';
  }}}} else {{{{
    btn.classList.remove('installed');
    btn.classList.add('install');
    btn.innerHTML = 'Install SID Extension';
    btn.setAttribute('href', '#');
    btn.style.cursor = 'pointer';
  }}}}
}}}}

function handleInstallClick(event) {{{{
  if (installDone) {{{{
    event.preventDefault();
    return false;
  }}}}
  alert('Chrome Web Store link coming soon!');
  return false;
}}}}

function detectExtension() {{{{
  if (document.documentElement.dataset.sidInstalled === 'true' || window.__SID_INSTALLED__) {{{{
    installDone = true;
    updateChecklist();
  }}}}
}}}}

// Detect extension on load and after delay
detectExtension();
setTimeout(detectExtension, 1500);

// Guide button listener
document.getElementById('guideBtn').addEventListener('click', () => {{{{
  if (!guideDone) {{{{
    guideDone = true;
    updateChecklist();
  }}}}
}}}});

// Upload button listener
document.getElementById('uploadBtn').addEventListener('click', () => {{{{
  if (!uploadDone) {{{{
    uploadDone = true;
    updateChecklist();
  }}}}
}}}});

// Initialize checklist display
updateChecklist();

/* ============================================================================
   BULLETIN BOARD / TODAY'S TASKS
   ========================================================================== */
function formatDate(dateString) {{{{
  const options = {{ year: 'numeric', month: 'long', day: 'numeric' }};
  return new Date(dateString + 'T00:00:00').toLocaleDateString('en-US', options);
}}}}

function getTodayString() {{{{
  const now = new Date();
  return now.getFullYear() + '-' +
         String(now.getMonth() + 1).padStart(2, '0') + '-' +
         String(now.getDate()).padStart(2, '0');
}}}}

function getTaskStorageKey(dateString) {{{{
  return 'sid_tasks_{folder_name}_' + dateString;
}}}}

function loadBulletinBoard() {{{{
  const today = getTodayString();
  const cachebusters = Date.now();

  fetch('https://sid.rocks/bulletin_{folder_name}.json?' + cachebusters)
    .then(response => response.json())
    .then(data => {{{{
      if (data.date && data.tasks && Array.isArray(data.tasks) && data.tasks.length > 0) {{{{
        // Check if tasks are for today
        if (data.date === today) {{{{
          displayBulletinBoard(data, today);
        }}}} else {{{{
          // Different date - hide bulletin board
          document.getElementById('bulletinBoard').classList.add('hidden');
        }}}}
      }}}} else {{{{
        // No tasks - hide bulletin board
        document.getElementById('bulletinBoard').classList.add('hidden');
      }}}}
    }}}})
    .catch(() => {{{{
      // Fetch failed - hide bulletin board
      document.getElementById('bulletinBoard').classList.add('hidden');
    }}}});
}}}}

function displayBulletinBoard(data, today) {{{{
  const bulletinEl = document.getElementById('bulletinBoard');
  const dateEl = document.getElementById('bulletinDate');
  const taskListEl = document.getElementById('taskList');
  const notesEl = document.getElementById('bulletinNotes');

  // Set date
  dateEl.textContent = formatDate(data.date);

  // Clear and build task list
  taskListEl.innerHTML = '';
  const storageKey = getTaskStorageKey(today);
  let taskStates = {{}};

  try {{{{
    taskStates = JSON.parse(localStorage.getItem(storageKey) || '{{}}');
  }}}} catch (e) {{{{
    // localStorage may not be available
  }}}}

  data.tasks.forEach((task, index) => {{{{
    const isCompleted = taskStates[index] === true;
    const li = document.createElement('li');
    li.className = 'task-item' + (isCompleted ? ' completed' : '');

    const checkDiv = document.createElement('div');
    checkDiv.className = 'task-check';
    li.appendChild(checkDiv);

    const labelSpan = document.createElement('span');
    labelSpan.className = 'task-label';
    labelSpan.textContent = task;
    li.appendChild(labelSpan);

    li.addEventListener('click', () => {{{{
      const wasDone = taskStates[index] === true;
      taskStates[index] = !wasDone;
      try {{{{
        localStorage.setItem(storageKey, JSON.stringify(taskStates));
      }}}} catch (e) {{{{
        // localStorage may not be available
      }}}}
      li.classList.toggle('completed');
    }}}});

    taskListEl.appendChild(li);
  }}}});

  // Set notes if present
  if (data.notes && data.notes.trim()) {{{{
    notesEl.textContent = data.notes;
    notesEl.classList.remove('hidden');
  }}}} else {{{{
    notesEl.classList.add('hidden');
  }}}}

  // Show bulletin board
  bulletinEl.classList.remove('hidden');
}}}}

loadBulletinBoard();

/* ============================================================================
   UPLOAD HISTORY COLLAPSIBLE
   ========================================================================== */
const uploadHistoryHeader = document.getElementById('uploadHistoryHeader');
const uploadHistoryContent = document.getElementById('uploadHistoryContent');
const uploadHistoryArrow = document.getElementById('uploadHistoryArrow');

uploadHistoryHeader.addEventListener('click', () => {{{{
  uploadHistoryContent.classList.toggle('expanded');
  uploadHistoryArrow.classList.toggle('expanded');
}}}});

/* ============================================================================
   ANNOUNCEMENT
   ========================================================================== */
function showAnnouncement(message, announcementId) {{{{
  const storageKey = 'sid_dismissed_' + (announcementId || 'default');

  try {{{{
    if (localStorage.getItem(storageKey)) {{{{
      return; // Already dismissed
    }}}}
  }}}} catch (e) {{{{
    // localStorage may not be available
  }}}}

  const announcementEl = document.getElementById('announcement');
  document.getElementById('announcement-text').textContent = message;
  announcementEl.classList.add('visible');
  document.body.style.paddingTop = '52px';

  document.getElementById('closeAnn').onclick = () => {{{{
    announcementEl.classList.remove('visible');
    document.body.style.paddingTop = '';
    try {{{{
      localStorage.setItem(storageKey, '1');
    }}}} catch (e) {{{{
      // localStorage may not be available
    }}}}
  }}}};
}}}}

// Fetch announcements
fetch('https://sid.rocks/announcements.json?' + Date.now())
  .then(response => response.json())
  .then(data => {{{{
    if (data.message) {{{{
      showAnnouncement(data.message, data.id);
    }}}}
  }}}})
  .catch(() => {{{{
    // Fetch failed - silently continue
  }}}});
</script>
</body>
</html>'''


def generate_guide(display_name, folder_name):
    portal_url = f"https://sid.rocks/{folder_name}"
    sop_path = os.path.join(SCRIPT_DIR, "SID_Vendor_SOP.html")
    with open(sop_path, "r") as f:
        g = f.read()
    replacements = [
        ('<title>SID - Smart Indeed Downloader | Vendor Guide</title>',
         f'<title>SID Vendor Guide - {display_name}</title>'),
        ('<p class="subtitle">Vendor Guide</p>',
         f'<p class="subtitle">Vendor Guide &mdash; {display_name}</p>'),
        ('upload the files using your personal upload link',
         f'upload the files on <a href="{portal_url}" style="color:#7860a8;">your portal page</a>'),
        ('Go to <strong><a href="https://sid.rocks" style="color:#7860a8;">sid.rocks</a></strong> and click the <strong>\u201cInstall SID\u201d</strong> button to open the Chrome Web Store page in <strong>Google Chrome</strong> (or Microsoft Edge).',
         f'Go to <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong> and click the <strong>\u201cInstall SID Extension\u201d</strong> button to open the Chrome Web Store page in <strong>Google Chrome</strong> (or Microsoft Edge).'),
        ('Go to <strong><a href="https://sid.rocks" style="color:#7860a8;">sid.rocks</a></strong> and click the <strong>"Install SID"</strong> button to open the Chrome Web Store page in <strong>Google Chrome</strong> (or Microsoft Edge).',
         f'Go to <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong> and click the <strong>"Install SID Extension"</strong> button to open the Chrome Web Store page in <strong>Google Chrome</strong> (or Microsoft Edge).'),
        ('upload the files using their personal upload link',
         'upload the files on their portal page'),
        ('<strong>Upload the ZIP(s)</strong> &mdash; Open your personal upload link and upload your ZIP file. See Section 5 below.',
         f'<strong>Upload the ZIP(s)</strong> &mdash; Go to <a href="{portal_url}" style="color:#7860a8;">your portal page</a> and click <strong>&quot;Upload ZIP Files&quot;</strong>. See Section 5 below.'),
        ('After you download the ZIP file from SID, upload it the same day using the <strong>personal upload link Melissa gave you</strong>. This is a unique link for your uploads &mdash; bookmark it so you have it handy.',
         f'After you download the ZIP file from SID, upload it the same day through <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong>. Bookmark your portal so you have it handy.'),
        ('Open the <strong>upload link</strong> Melissa provided you (check your email if you don\'t have it saved).',
         f'Go to <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong> and click <strong>&quot;Upload ZIP Files&quot;</strong>.'),
        ('Upload your ZIP file using your personal upload link by end of day.',
         f'Upload your ZIP file through <a href="{portal_url}" style="color:#7860a8;">your portal page</a> by end of day.'),
    ]
    for old, new in replacements:
        g = g.replace(old, new)
    return g


def add_lowercase_redirect(folder):
    """Add a lowercase redirect to the git index using hash-object (needed on case-insensitive macOS)."""
    lower = folder.lower()
    if lower == folder:
        return  # Already lowercase, no redirect needed
    try:
        os.chdir(SCRIPT_DIR)
        redirect_html = (
            f'<!DOCTYPE html>\n<html><head>\n'
            f'<meta http-equiv="refresh" content="0; url=https://sid.rocks/{folder}">\n'
            f'<link rel="canonical" href="https://sid.rocks/{folder}">\n'
            f'<title>Redirecting...</title>\n'
            f'</head><body>\n'
            f'<p>Redirecting to <a href="https://sid.rocks/{folder}">sid.rocks/{folder}</a>...</p>\n'
            f'</body></html>'
        )
        # Write blob directly to git object store
        blob = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                              input=redirect_html.encode(), capture_output=True, check=True)
        blob_sha = blob.stdout.decode().strip()
        # Add to git index at lowercase path (bypasses filesystem case-insensitivity)
        subprocess.run(["git", "update-index", "--add", "--cacheinfo",
                        f"100644,{blob_sha},{lower}/index.html"],
                       check=True, capture_output=True)
    except Exception:
        pass  # Non-fatal — the portal still works at the proper-case URL


def git_push(display_name, action="Add", folder=None):
    try:
        os.chdir(SCRIPT_DIR)
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        # If creating a new vendor, also add the lowercase redirect
        if action == "Add" and folder:
            add_lowercase_redirect(folder)
        subprocess.run(["git", "commit", "-m", f"{action} {display_name} vendor portal"],
                       check=True, capture_output=True)
        result = subprocess.run(["git", "push", "origin", "main"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return True, "Pushed to GitHub! Site will be live in ~1 minute."
        else:
            return False, f"Push failed: {result.stderr}"
    except subprocess.CalledProcessError as e:
        return False, f"Git error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return False, str(e)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SID Vendor Manager")
        self.configure(bg=BG)
        self.geometry("640x950")
        self.resizable(False, False)

        # ── Header ──
        header = tk.Frame(self, bg=PURPLE, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="SID Vendor Manager", font=("Helvetica Neue", 18, "bold"),
                 bg=PURPLE, fg="white").pack(side="left", padx=20)

        # ── Tabbed Interface ──
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Style the notebook
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', padding=[12, 8], font=("Helvetica Neue", 11))

        # Tab 1: Vendors
        self.vendors_tab = tk.Frame(notebook, bg=BG)
        notebook.add(self.vendors_tab, text="Vendors")
        self._build_vendors_tab()

        # Tab 2: Daily Tasks
        self.tasks_tab = tk.Frame(notebook, bg=BG)
        notebook.add(self.tasks_tab, text="Daily Tasks")
        self._build_tasks_tab()

        # Tab 3: Job Postings
        self.postings_tab = tk.Frame(notebook, bg=BG)
        notebook.add(self.postings_tab, text="Job Postings")
        self._build_postings_tab()

        # Tab 4: Settings
        self.settings_tab = tk.Frame(notebook, bg=BG)
        notebook.add(self.settings_tab, text="Settings")
        self._build_settings_tab()

        # ── Status bar ──
        self.status = tk.Label(self, text="Ready", font=("Helvetica Neue", 11),
                                bg="#e8e4ef", fg=GRAY, anchor="w", padx=16, pady=6)
        self.status.pack(fill="x", side="bottom")

    def _build_vendors_tab(self):
        """Build the Vendors tab with vendor list, add/remove vendors."""
        main = tk.Frame(self.vendors_tab, bg=BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        # --- Existing vendors ---
        tk.Label(main, text="CURRENT VENDORS", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        list_frame = tk.Frame(main, bg=CARD, highlightbackground=BORDER,
                              highlightthickness=1, bd=0)
        list_frame.pack(fill="x", pady=(0, 12))

        self.vendor_list = tk.Listbox(list_frame, height=5, font=("Helvetica Neue", 13),
                                       bg=CARD, fg=TEXT, selectbackground=PURPLE_LT,
                                       selectforeground="white", bd=0, highlightthickness=0,
                                       activestyle="none")
        self.vendor_list.pack(fill="x", padx=8, pady=8)
        self.refresh_list()

        del_btn = make_button(main, "Remove Selected Vendor", RED, "#c05050",
                              self.remove_vendor, font_size=12, pady=6)
        del_btn.pack(fill="x", pady=(0, 16))

        # --- Separator ---
        tk.Frame(main, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

        # --- Add new vendor ---
        tk.Label(main, text="ADD NEW VENDOR", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 10))

        fields = tk.Frame(main, bg=BG)
        fields.pack(fill="x")

        tk.Label(fields, text="Vendor Name", font=("Helvetica Neue", 11),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x")
        name_frame = tk.Frame(fields, bg=BORDER, bd=0)
        name_frame.pack(fill="x", pady=(2, 4))
        self.name_entry = tk.Entry(name_frame, font=("Helvetica Neue", 14), bd=0,
                                    bg="white", fg=TEXT, insertbackground=TEXT,
                                    highlightthickness=0, relief="flat")
        self.name_entry.pack(fill="x", ipady=6, padx=1, pady=1)
        tk.Label(fields, text="e.g. FBSPL, Acme Corp, MindSuperiorConsult",
                 font=("Helvetica Neue", 10), bg=BG, fg="#aaa", anchor="w").pack(fill="x", pady=(0, 10))

        url_label_row = tk.Frame(fields, bg=BG)
        url_label_row.pack(fill="x")
        tk.Label(url_label_row, text="OneDrive Upload URL", font=("Helvetica Neue", 11),
                 bg=BG, fg=GRAY, anchor="w").pack(side="left")
        help_label = tk.Label(url_label_row, text="How do I get this?", font=("Helvetica Neue", 10, "underline"),
                              bg=BG, fg=PURPLE, cursor="hand2")
        help_label.pack(side="right")
        help_label.bind("<Button-1>", lambda e: self.show_onedrive_help())
        help_label.bind("<Enter>", lambda e: help_label.config(fg=PURPLE_LT))
        help_label.bind("<Leave>", lambda e: help_label.config(fg=PURPLE))
        url_frame = tk.Frame(fields, bg=BORDER, bd=0)
        url_frame.pack(fill="x", pady=(2, 4))
        self.url_entry = tk.Entry(url_frame, font=("Helvetica Neue", 14), bd=0,
                                   bg="white", fg=TEXT, insertbackground=TEXT,
                                   highlightthickness=0, relief="flat")
        self.url_entry.pack(fill="x", ipady=6, padx=1, pady=1)
        tk.Label(fields, text="Paste the OneDrive share link for this vendor's upload folder",
                 font=("Helvetica Neue", 10), bg=BG, fg="#aaa", anchor="w").pack(fill="x", pady=(0, 14))

        add_btn = make_button(main, "Create Vendor Portal", GREEN, "#4ca87a",
                              self.add_vendor, font_size=14, pady=10)
        add_btn.pack(fill="x", pady=(0, 8))

    def _build_tasks_tab(self):
        """Build the Daily Tasks tab with vendor selector, task editor, and push controls."""
        main = tk.Frame(self.tasks_tab, bg=BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        # --- Select vendor ---
        tk.Label(main, text="SELECT VENDOR", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        vendor_frame = tk.Frame(main, bg=BORDER, bd=0)
        vendor_frame.pack(fill="x", pady=(0, 12))
        
        self.vendor_combo_var = tk.StringVar()
        self.vendor_combo = ttk.Combobox(vendor_frame, textvariable=self.vendor_combo_var,
                                         state="readonly", font=("Helvetica Neue", 13),
                                         height=6)
        self.vendor_combo.pack(fill="x", ipady=6, padx=1, pady=1)
        self.vendor_combo.bind("<<ComboboxSelected>>", self._on_vendor_selected)
        self._refresh_vendor_dropdown()

        # --- Tasks text area ---
        tk.Label(main, text="DAILY TASKS", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        tasks_frame = tk.Frame(main, bg=BORDER, bd=0)
        tasks_frame.pack(fill="both", expand=True, pady=(0, 12))

        self.tasks_text = tk.Text(tasks_frame, height=6, font=("Helvetica Neue", 12),
                                   bg="white", fg=TEXT, insertbackground=TEXT,
                                   bd=0, highlightthickness=0, wrap="word")
        self.tasks_text.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(main, text="One task per line (e.g., 'Post 5 SFG on Indeed')",
                 font=("Helvetica Neue", 10), bg=BG, fg="#aaa", anchor="w").pack(fill="x", pady=(0, 10))

        # --- Notes field ---
        tk.Label(main, text="NOTES", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        notes_frame = tk.Frame(main, bg=BORDER, bd=0)
        notes_frame.pack(fill="x", pady=(0, 12))
        self.notes_entry = tk.Entry(notes_frame, font=("Helvetica Neue", 12), bd=0,
                                     bg="white", fg=TEXT, insertbackground=TEXT,
                                     highlightthickness=0, relief="flat")
        self.notes_entry.pack(fill="x", ipady=5, padx=1, pady=1)

        tk.Label(main, text="Optional: context for this vendor (e.g., 'Priority on SFG today')",
                 font=("Helvetica Neue", 10), bg=BG, fg="#aaa", anchor="w").pack(fill="x", pady=(0, 12))

        # --- Action buttons ---
        button_frame = tk.Frame(main, bg=BG)
        button_frame.pack(fill="x", pady=(0, 12))

        push_btn = make_button(button_frame, "Push Tasks", GREEN, "#4ca87a",
                               self.push_tasks, font_size=12, pady=6)
        push_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        clear_btn = make_button(button_frame, "Clear Tasks", RED, "#c05050",
                                self.clear_tasks, font_size=12, pady=6)
        clear_btn.pack(side="right", expand=True, fill="x", padx=(4, 0))

    def _build_postings_tab(self):
        """Build the Job Postings tab with category and posting management."""
        main = tk.Frame(self.postings_tab, bg=BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        # --- Select vendor ---
        tk.Label(main, text="SELECT VENDOR", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        vendor_frame = tk.Frame(main, bg=BORDER, bd=0)
        vendor_frame.pack(fill="x", pady=(0, 12))
        
        self.postings_vendor_var = tk.StringVar()
        self.postings_vendor_combo = ttk.Combobox(vendor_frame, textvariable=self.postings_vendor_var,
                                                   state="readonly", font=("Helvetica Neue", 13),
                                                   height=6)
        self.postings_vendor_combo.pack(fill="x", ipady=6, padx=1, pady=1)
        self.postings_vendor_combo.bind("<<ComboboxSelected>>", self._on_postings_vendor_selected)
        self._refresh_postings_vendor_dropdown()

        # --- Categories section ---
        tk.Label(main, text="CATEGORIES", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        cat_add_frame = tk.Frame(main, bg=BG)
        cat_add_frame.pack(fill="x", pady=(0, 6))

        cat_entry_frame = tk.Frame(cat_add_frame, bg=BORDER, bd=0)
        cat_entry_frame.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.cat_entry = tk.Entry(cat_entry_frame, font=("Helvetica Neue", 12), bd=0,
                                    bg="white", fg=TEXT, insertbackground=TEXT,
                                    highlightthickness=0, relief="flat")
        self.cat_entry.pack(fill="x", ipady=4, padx=1, pady=1)

        add_cat_btn = make_button(cat_add_frame, "Add Category", BLUE, "#4a7aaf",
                                   self._add_category, font_size=11, pady=4)
        add_cat_btn.pack(side="right", fill="x", padx=(4, 0))

        # Categories display frame
        self.categories_frame = tk.Frame(main, bg=BG)
        self.categories_frame.pack(fill="x", pady=(0, 12))

        # --- Postings listbox ---
        tk.Label(main, text="JOB POSTINGS", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        postings_frame = tk.Frame(main, bg=BORDER, bd=0)
        postings_frame.pack(fill="both", expand=True, pady=(0, 12))

        self.postings_listbox = tk.Listbox(postings_frame, height=6, font=("Helvetica Neue", 12),
                                            bg=CARD, fg=TEXT, selectbackground=PURPLE_LT,
                                            selectforeground="white", bd=0, highlightthickness=0,
                                            activestyle="none")
        self.postings_listbox.pack(fill="both", expand=True, padx=1, pady=1)

        # --- Action buttons ---
        button_frame = tk.Frame(main, bg=BG)
        button_frame.pack(fill="x", pady=(0, 12))

        add_posting_btn = make_button(button_frame, "Add Posting", GREEN, "#4ca87a",
                                       self._add_posting, font_size=12, pady=6)
        add_posting_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        edit_posting_btn = make_button(button_frame, "Edit Posting", BLUE, "#4a7aaf",
                                        self._edit_posting, font_size=12, pady=6)
        edit_posting_btn.pack(side="left", expand=True, fill="x", padx=(2, 2))

        remove_posting_btn = make_button(button_frame, "Remove Posting", RED, "#c05050",
                                          self._remove_posting, font_size=12, pady=6)
        remove_posting_btn.pack(side="right", expand=True, fill="x", padx=(4, 0))

        # --- Push button ---
        push_postings_btn = make_button(main, "Push Postings", GREEN, "#4ca87a",
                                         self._push_postings, font_size=12, pady=6)
        push_postings_btn.pack(fill="x")

    def _refresh_postings_vendor_dropdown(self):
        """Refresh the vendor dropdown in the Job Postings tab."""
        vendors = get_vendors()
        vendor_names = [f"{display} ({folder})" for folder, display in vendors]
        self.postings_vendor_combo['values'] = vendor_names
        if vendor_names:
            self.postings_vendor_combo.current(0)
            self._on_postings_vendor_selected(None)

    def _on_postings_vendor_selected(self, event):
        """Load the selected vendor's postings and populate categories."""
        sel = self.postings_vendor_var.get()
        if not sel or "(" not in sel:
            return
        
        folder = sel.split("(")[-1].rstrip(")")
        self.current_postings_folder = folder
        self.postings_data = load_postings(folder)
        self._refresh_categories()
        self.postings_listbox.delete(0, tk.END)

    def _refresh_categories(self):
        """Refresh the category buttons display."""
        # Clear existing category buttons
        for widget in self.categories_frame.winfo_children():
            widget.destroy()
        
        categories = self.postings_data.get("categories", {})
        
        if not categories:
            tk.Label(self.categories_frame, text="No categories yet. Add one above.",
                     font=("Helvetica Neue", 10), bg=BG, fg=GRAY).pack(pady=4)
            return
        
        # Create category buttons
        for cat_key in sorted(categories.keys()):
            cat_data = categories[cat_key]
            cat_label = cat_data.get("label", cat_key)
            
            cat_btn_frame = tk.Frame(self.categories_frame, bg=BORDER, bd=0)
            cat_btn_frame.pack(side="left", fill="x", padx=(0, 4), pady=2)
            
            cat_btn = tk.Label(cat_btn_frame, text=cat_label,
                               font=("Helvetica Neue", 11, "bold"),
                               bg=PURPLE_LT, fg="white", padx=12, pady=4, cursor="hand2")
            cat_btn.pack(side="left", padx=1, pady=1)
            
            cat_btn.bind("<Button-1>", lambda e, k=cat_key: self._select_category(k))
            cat_btn.bind("<Enter>", lambda e: cat_btn.config(bg=PURPLE))
            cat_btn.bind("<Leave>", lambda e: cat_btn.config(bg=PURPLE_LT))
            
            # Delete button (X)
            del_btn = tk.Label(cat_btn_frame, text="✕", font=("Helvetica Neue", 10),
                               bg="#d06060", fg="white", padx=6, pady=3, cursor="hand2")
            del_btn.pack(side="left", padx=1, pady=1)
            
            del_btn.bind("<Button-1>", lambda e, k=cat_key: self._delete_category(k))
            del_btn.bind("<Enter>", lambda e: del_btn.config(bg="#c05050"))
            del_btn.bind("<Leave>", lambda e: del_btn.config(bg="#d06060"))

    def _select_category(self, cat_key):
        """Select a category and display its postings."""
        self.current_postings_category = cat_key
        self._refresh_postings_listbox()

    def _refresh_postings_listbox(self):
        """Refresh the postings listbox for the current category."""
        self.postings_listbox.delete(0, tk.END)
        
        if not hasattr(self, 'current_postings_category'):
            return
        
        categories = self.postings_data.get("categories", {})
        cat_data = categories.get(self.current_postings_category, {})
        posts = cat_data.get("posts", [])
        
        for post in posts:
            title = post.get("title", "Untitled")
            self.postings_listbox.insert(tk.END, title)

    def _add_category(self):
        """Add a new category."""
        if not hasattr(self, 'current_postings_folder'):
            messagebox.showwarning("No Vendor", "Please select a vendor first.")
            return
        
        cat_name = self.cat_entry.get().strip().upper()
        if not cat_name:
            messagebox.showwarning("Empty", "Please enter a category name.")
            return
        
        categories = self.postings_data.get("categories", {})
        if cat_name in categories:
            messagebox.showwarning("Exists", f"Category '{cat_name}' already exists.")
            return
        
        categories[cat_name] = {"label": cat_name, "posts": []}
        self.postings_data["categories"] = categories
        save_postings(self.current_postings_folder, self.postings_data)
        
        self.cat_entry.delete(0, tk.END)
        self._refresh_categories()

    def _delete_category(self, cat_key):
        """Delete a category (with confirmation)."""
        categories = self.postings_data.get("categories", {})
        cat_label = categories.get(cat_key, {}).get("label", cat_key)
        
        if not messagebox.askyesno("Delete Category",
                                    f"Delete category '{cat_label}'?\nAll postings in this category will be removed."):
            return
        
        del categories[cat_key]
        self.postings_data["categories"] = categories
        save_postings(self.current_postings_folder, self.postings_data)
        
        self.postings_listbox.delete(0, tk.END)
        self._refresh_categories()

    def _add_posting(self):
        """Open dialog to add a new posting."""
        if not hasattr(self, 'current_postings_category'):
            messagebox.showwarning("No Category", "Please select a category first.")
            return
        
        self._open_posting_dialog(None, self.current_postings_category)

    def _edit_posting(self):
        """Open dialog to edit selected posting."""
        sel = self.postings_listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Click on a posting to edit.")
            return
        
        idx = sel[0]
        categories = self.postings_data.get("categories", {})
        cat_data = categories.get(self.current_postings_category, {})
        posts = cat_data.get("posts", [])
        
        if idx < len(posts):
            self._open_posting_dialog(idx, self.current_postings_category)

    def _remove_posting(self):
        """Remove selected posting."""
        sel = self.postings_listbox.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Click on a posting to remove.")
            return
        
        idx = sel[0]
        categories = self.postings_data.get("categories", {})
        cat_data = categories.get(self.current_postings_category, {})
        posts = cat_data.get("posts", [])
        
        if idx < len(posts):
            post_title = posts[idx].get("title", "Untitled")
            if messagebox.askyesno("Remove Posting", f"Remove '{post_title}'?"):
                posts.pop(idx)
                save_postings(self.current_postings_folder, self.postings_data)
                self._refresh_postings_listbox()

    def _open_posting_dialog(self, post_idx, cat_key):
        """Open a dialog to add/edit a posting."""
        dialog = tk.Toplevel(self)
        dialog.title("Job Posting" if post_idx is None else "Edit Posting")
        dialog.configure(bg=CARD)
        dialog.geometry("600x700")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Main frame
        main = tk.Frame(dialog, bg=CARD, padx=20, pady=20)
        main.pack(fill="both", expand=True)

        # Load existing data if editing
        categories = self.postings_data.get("categories", {})
        cat_data = categories.get(cat_key, {})
        posts = cat_data.get("posts", [])
        existing_post = posts[post_idx] if post_idx is not None else None

        # Title
        tk.Label(main, text="Job Title", font=("Helvetica Neue", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 4))
        title_frame = tk.Frame(main, bg=BORDER, bd=0)
        title_frame.pack(fill="x", pady=(0, 12))
        title_entry = tk.Entry(title_frame, font=("Helvetica Neue", 12), bd=0,
                                bg="white", fg=TEXT, insertbackground=TEXT,
                                highlightthickness=0, relief="flat")
        title_entry.pack(fill="x", ipady=5, padx=1, pady=1)
        if existing_post:
            title_entry.insert(0, existing_post.get("title", ""))

        # Location
        tk.Label(main, text="Location", font=("Helvetica Neue", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 4))
        location_frame = tk.Frame(main, bg=BORDER, bd=0)
        location_frame.pack(fill="x", pady=(0, 12))
        location_entry = tk.Entry(location_frame, font=("Helvetica Neue", 12), bd=0,
                                   bg="white", fg=TEXT, insertbackground=TEXT,
                                   highlightthickness=0, relief="flat")
        location_entry.pack(fill="x", ipady=5, padx=1, pady=1)
        if existing_post:
            location_entry.insert(0, existing_post.get("location", ""))

        # Salary
        tk.Label(main, text="Salary", font=("Helvetica Neue", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 4))
        salary_frame = tk.Frame(main, bg=BORDER, bd=0)
        salary_frame.pack(fill="x", pady=(0, 12))
        salary_entry = tk.Entry(salary_frame, font=("Helvetica Neue", 12), bd=0,
                                 bg="white", fg=TEXT, insertbackground=TEXT,
                                 highlightthickness=0, relief="flat")
        salary_entry.pack(fill="x", ipady=5, padx=1, pady=1)
        if existing_post:
            salary_entry.insert(0, existing_post.get("salary", ""))

        # Benefits
        tk.Label(main, text="Benefits (comma-separated)", font=("Helvetica Neue", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 4))
        benefits_frame = tk.Frame(main, bg=BORDER, bd=0)
        benefits_frame.pack(fill="x", pady=(0, 12))
        benefits_entry = tk.Entry(benefits_frame, font=("Helvetica Neue", 12), bd=0,
                                   bg="white", fg=TEXT, insertbackground=TEXT,
                                   highlightthickness=0, relief="flat")
        benefits_entry.pack(fill="x", ipady=5, padx=1, pady=1)
        if existing_post:
            benefits = existing_post.get("benefits", [])
            if isinstance(benefits, list):
                benefits_entry.insert(0, ", ".join(benefits))
            else:
                benefits_entry.insert(0, benefits)

        # Description
        tk.Label(main, text="Description (supports HTML)", font=("Helvetica Neue", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 4))
        desc_frame = tk.Frame(main, bg=BORDER, bd=0)
        desc_frame.pack(fill="both", expand=True, pady=(0, 12))
        desc_text = tk.Text(desc_frame, height=8, font=("Helvetica Neue", 11), bd=0,
                             bg="white", fg=TEXT, insertbackground=TEXT,
                             highlightthickness=0, wrap="word")
        desc_text.pack(fill="both", expand=True, padx=1, pady=1)
        if existing_post:
            desc_text.insert("1.0", existing_post.get("description", ""))

        # Save/Cancel buttons
        button_frame = tk.Frame(main, bg=CARD)
        button_frame.pack(fill="x")

        def save_posting():
            title = title_entry.get().strip()
            location = location_entry.get().strip()
            salary = salary_entry.get().strip()
            benefits_str = benefits_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()

            if not title:
                messagebox.showwarning("Missing", "Please enter a job title.")
                return

            # Parse benefits
            benefits = [b.strip() for b in benefits_str.split(",") if b.strip()]

            post_data = {
                "title": title,
                "location": location,
                "salary": salary,
                "benefits": benefits,
                "description": description
            }

            if post_idx is None:
                # New posting
                posts.append(post_data)
            else:
                # Edit existing
                posts[post_idx] = post_data

            save_postings(self.current_postings_folder, self.postings_data)
            self._refresh_postings_listbox()
            dialog.destroy()

        save_btn = make_button(button_frame, "Save Posting", GREEN, "#4ca87a",
                                save_posting, font_size=12, pady=6)
        save_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        cancel_btn = make_button(button_frame, "Cancel", GRAY, "#8a92a2",
                                  dialog.destroy, font_size=12, pady=6)
        cancel_btn.pack(side="right", expand=True, fill="x", padx=(4, 0))

    def _push_postings(self):
        """Save and push postings for the selected vendor."""
        if not hasattr(self, 'current_postings_folder'):
            messagebox.showwarning("No Vendor", "Please select a vendor first.")
            return

        folder = self.current_postings_folder
        categories = self.postings_data.get("categories", {})
        total_posts = sum(len(cat.get("posts", [])) for cat in categories.values())

        if not messagebox.askyesno("Push Postings",
                                    f"Push {len(categories)} category/categories with {total_posts} posting(s)?"):
            return

        self.set_status(f"Saving postings for {folder}...")
        save_postings(folder, self.postings_data)

        ok, msg = git_push(f"postings for {folder}", "Update")
        if ok:
            self.set_status(f"Postings pushed for {folder}! Live in ~1 min.", GREEN)
            messagebox.showinfo("Done!", f"Postings are live on {folder}'s portal.")
        else:
            self.set_status(f"Saved locally for {folder}. Git push failed.", RED)
            messagebox.showwarning("Partial", f"Saved locally but push failed:\n{msg}")

    def _build_settings_tab(self):
        """Build the Settings tab with announcement banner controls."""
        main = tk.Frame(self.settings_tab, bg=BG, padx=24, pady=20)
        main.pack(fill="both", expand=True)

        # --- Announcement Banner ---
        tk.Label(main, text="ANNOUNCEMENT BANNER", font=("Helvetica Neue", 10, "bold"),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(0, 6))

        ann_frame = tk.Frame(main, bg=BG)
        ann_frame.pack(fill="x")

        ann_entry_frame = tk.Frame(ann_frame, bg=BORDER, bd=0)
        ann_entry_frame.pack(fill="x", pady=(0, 4))
        self.ann_entry = tk.Entry(ann_entry_frame, font=("Helvetica Neue", 13), bd=0,
                                   bg="white", fg=TEXT, insertbackground=TEXT,
                                   highlightthickness=0, relief="flat")
        self.ann_entry.pack(fill="x", ipady=5, padx=1, pady=1)

        ann_buttons = tk.Frame(main, bg=BG)
        ann_buttons.pack(fill="x", pady=(0, 4))

        post_btn = make_button(ann_buttons, "Post Announcement", PURPLE, PURPLE_LT,
                               self.post_announcement, font_size=12, pady=6)
        post_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        clear_btn = make_button(ann_buttons, "Clear Banner", GRAY, "#8a92a2",
                                self.clear_announcement, font_size=12, pady=6)
        clear_btn.pack(side="right", expand=True, fill="x", padx=(4, 0))

        self.ann_status = tk.Label(main, text="", font=("Helvetica Neue", 10),
                                    bg=BG, fg=GRAY, anchor="w")
        self.ann_status.pack(fill="x", pady=(0, 20))

        # Load current announcement into field
        self._load_current_announcement()

        # --- Other settings (placeholder) ---
        tk.Label(main, text="More settings coming soon...", font=("Helvetica Neue", 12),
                 bg=BG, fg=GRAY, anchor="w").pack(fill="x", pady=(20, 0))

    def refresh_list(self):
        self.vendor_list.delete(0, tk.END)
        for folder, display in get_vendors():
            status_indicator = "● " if has_todays_tasks(folder) else "○ "
            if display != folder:
                self.vendor_list.insert(tk.END, f"{status_indicator}{display}  ({folder})")
            else:
                self.vendor_list.insert(tk.END, f"{status_indicator}{folder}")

    def _refresh_vendor_dropdown(self):
        """Refresh the vendor dropdown in the Daily Tasks tab."""
        vendors = get_vendors()
        vendor_names = [f"{display} ({folder})" for folder, display in vendors]
        self.vendor_combo['values'] = vendor_names
        if vendor_names:
            self.vendor_combo.current(0)
            self._on_vendor_selected(None)

    def _on_vendor_selected(self, event):
        """Load the selected vendor's tasks into the editor."""
        sel = self.vendor_combo_var.get()
        if not sel or "(" not in sel:
            return
        
        folder = sel.split("(")[-1].rstrip(")")
        bulletin = load_bulletin(folder)
        
        self.tasks_text.delete("1.0", tk.END)
        for task in bulletin.get("tasks", []):
            self.tasks_text.insert(tk.END, task + "\n")
        
        self.notes_entry.delete(0, tk.END)
        self.notes_entry.insert(0, bulletin.get("notes", ""))

    def set_status(self, msg, color=GRAY):
        self.status.config(text=msg, fg=color)
        self.update_idletasks()

    def show_onedrive_help(self):
        win = tk.Toplevel(self)
        win.title("How to Get the OneDrive Upload Link")
        win.configure(bg=CARD)
        win.geometry("500x420")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        # Title
        tk.Label(win, text="Getting the OneDrive Upload Link",
                 font=("Helvetica Neue", 16, "bold"), bg=CARD, fg=PURPLE,
                 wraplength=460).pack(padx=20, pady=(20, 14))

        steps = (
            "1.  Go to onedrive.live.com (or your SharePoint) and open\n"
            "     the SID Vendor Uploads folder.\n\n"
            "2.  Click  + New  →  Folder  and name it the vendor's\n"
            "     name (e.g. \"FBSPL\").\n\n"
            "3.  Open the new folder you just created.\n\n"
            "4.  Click the  Share  button at the top (or right-click\n"
            "     the folder → Share).\n\n"
            "5.  In the share dialog:\n"
            "     •  Change \"People you specify\" to\n"
            "        \"Anyone with the link\"\n"
            "     •  Check \"Allow editing\" so vendors can upload\n"
            "     •  Click  Copy link\n\n"
            "6.  Paste that link into the OneDrive Upload URL field\n"
            "     in this app — done!"
        )

        text_frame = tk.Frame(win, bg="#f8f6fc", highlightbackground=BORDER,
                              highlightthickness=1, bd=0)
        text_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        tk.Label(text_frame, text=steps, font=("Helvetica Neue", 12),
                 bg="#f8f6fc", fg=TEXT, justify="left", anchor="nw",
                 wraplength=440).pack(padx=16, pady=16, fill="both", expand=True)

        got_it = make_button(win, "Got it!", PURPLE, PURPLE_LT, win.destroy, font_size=13, pady=8)
        got_it.pack(fill="x", padx=20, pady=(0, 20))

    def add_vendor(self):
        name = self.name_entry.get().strip()
        url = self.url_entry.get().strip()

        if not name:
            messagebox.showwarning("Missing Info", "Please enter a vendor name.")
            return
        if not url:
            messagebox.showwarning("Missing Info", "Please paste the OneDrive upload URL.")
            return

        # Auto-generate folder name: remove spaces and special chars
        folder = "".join(c for c in name if c.isalnum())

        if not folder:
            messagebox.showwarning("Invalid Name", "Vendor name must contain at least one letter or number.")
            return

        out_dir = os.path.join(SCRIPT_DIR, folder)
        if os.path.exists(out_dir):
            if not messagebox.askyesno("Already Exists",
                                        f"A portal for '{name}' already exists.\n\nDo you want to replace it?"):
                return

        self.set_status(f"Creating portal for {name}...")
        os.makedirs(out_dir, exist_ok=True)

        with open(os.path.join(out_dir, "index.html"), "w") as f:
            f.write(generate_portal(name, folder, url))
        with open(os.path.join(out_dir, "guide.html"), "w") as f:
            f.write(generate_guide(name, folder))

        self.set_status(f"Pushing to GitHub...")
        ok, msg = git_push(name, "Add", folder=folder)

        portal_link = f"sid.rocks/{folder}"
        if ok:
            self.set_status(f"Done! {portal_link} will be live in ~1 min.", GREEN)
            messagebox.showinfo("Vendor Created!",
                                f"Portal is live at:\n\n"
                                f"  Portal:  {portal_link}\n"
                                f"  Guide:   {portal_link}/guide.html\n\n"
                                f"Send your vendor this link:\n"
                                f"  https://{portal_link}\n\n"
                                f"{msg}")
        else:
            self.set_status(f"Files created locally. Git push failed.", RED)
            messagebox.showwarning("Partial Success",
                                    f"Files created for {name}, but couldn't push to GitHub:\n\n"
                                    f"{msg}\n\n"
                                    f"The portal will work once you push manually.")

        self.refresh_list()
        self._refresh_vendor_dropdown()
        self.name_entry.delete(0, tk.END)
        self.url_entry.delete(0, tk.END)

    def _load_current_announcement(self):
        """Load the current announcement from announcements.json into the entry field."""
        ann_path = os.path.join(SCRIPT_DIR, ANNOUNCEMENTS_FILE)
        try:
            if os.path.exists(ann_path):
                with open(ann_path, "r") as f:
                    data = json.load(f)
                msg = data.get("message", "")
                if msg:
                    self.ann_entry.insert(0, msg)
                    self.ann_status.config(text="Banner is currently live.", fg=GREEN)
                else:
                    self.ann_status.config(text="No banner active.", fg=GRAY)
            else:
                self.ann_status.config(text="No banner active.", fg=GRAY)
        except Exception:
            self.ann_status.config(text="No banner active.", fg=GRAY)

    def post_announcement(self):
        """Post an announcement banner to all vendor portals."""
        msg = self.ann_entry.get().strip()
        if not msg:
            messagebox.showwarning("Empty", "Type an announcement message first.")
            return

        if not messagebox.askyesno("Post Announcement",
                                    f"This will show a banner on ALL vendor portals:\n\n"
                                    f"\"{msg}\"\n\n"
                                    f"Post it now?"):
            return

        self.set_status("Posting announcement...")

        # Generate a unique ID based on the message (so dismissals reset for new messages)
        ann_id = "ann_" + str(abs(hash(msg)) % 100000)
        ann_data = {"message": msg, "id": ann_id}

        ann_path = os.path.join(SCRIPT_DIR, ANNOUNCEMENTS_FILE)
        with open(ann_path, "w") as f:
            json.dump(ann_data, f, indent=2)

        ok, push_msg = git_push("announcement", "Post")
        if ok:
            self.set_status("Announcement posted! Live in ~1 min.", GREEN)
            self.ann_status.config(text="Banner is currently live.", fg=GREEN)
            messagebox.showinfo("Posted!", f"Announcement is live on all portals:\n\n\"{msg}\"")
        else:
            self.set_status("Saved locally. Git push failed.", RED)
            self.ann_status.config(text="Saved locally, push failed.", fg=RED)
            messagebox.showwarning("Partial", f"Saved locally but push failed:\n{push_msg}")

    def clear_announcement(self):
        """Remove the announcement banner from all vendor portals."""
        if not messagebox.askyesno("Clear Banner",
                                    "Remove the announcement from all vendor portals?"):
            return

        self.set_status("Clearing announcement...")
        ann_path = os.path.join(SCRIPT_DIR, ANNOUNCEMENTS_FILE)
        with open(ann_path, "w") as f:
            json.dump({}, f)

        self.ann_entry.delete(0, tk.END)

        ok, push_msg = git_push("announcement", "Clear")
        if ok:
            self.set_status("Banner cleared! Will disappear in ~1 min.", GREEN)
            self.ann_status.config(text="No banner active.", fg=GRAY)
        else:
            self.set_status("Cleared locally. Git push failed.", RED)
            messagebox.showwarning("Partial", f"Cleared locally but push failed:\n{push_msg}")

    def remove_vendor(self):
        sel = self.vendor_list.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Click on a vendor in the list first.")
            return

        text = self.vendor_list.get(sel[0]).strip()
        # Extract folder name from display text (after the ● or ○)
        text = text.lstrip("● ○ ")
        if "(" in text and text.endswith(")"):
            folder = text.split("(")[-1].rstrip(")")
        else:
            folder = text

        if not messagebox.askyesno("Confirm Remove",
                                    f"Remove {folder}?\n\n"
                                    f"This will take down sid.rocks/{folder} "
                                    f"and delete the vendor's portal and guide."):
            return

        self.set_status(f"Removing {folder}...")
        out_dir = os.path.join(SCRIPT_DIR, folder)
        shutil.rmtree(out_dir, ignore_errors=True)

        ok, msg = git_push(folder, "Remove")
        if ok:
            self.set_status(f"Removed! sid.rocks/{folder} will go down in ~1 min.", GREEN)
            messagebox.showinfo("Removed", f"{folder} has been removed.\n\n{msg}")
        else:
            self.set_status(f"Removed locally. Git push failed.", RED)
            messagebox.showwarning("Partial", f"Removed locally but push failed:\n{msg}")

        self.refresh_list()
        self._refresh_vendor_dropdown()

    def push_tasks(self):
        """Save and push tasks for the selected vendor."""
        sel = self.vendor_combo_var.get()
        if not sel or "(" not in sel:
            messagebox.showwarning("No Vendor", "Please select a vendor first.")
            return
        
        folder = sel.split("(")[-1].rstrip(")")
        tasks_text = self.tasks_text.get("1.0", tk.END).strip()
        notes_text = self.notes_entry.get().strip()
        
        if not tasks_text:
            messagebox.showwarning("Empty", "Please add at least one task.")
            return
        
        tasks_list = [t.strip() for t in tasks_text.split("\n") if t.strip()]
        
        if not messagebox.askyesno("Push Tasks",
                                    f"Push {len(tasks_list)} task(s) to {folder}?"):
            return
        
        self.set_status(f"Saving tasks for {folder}...")
        save_bulletin(folder, tasks_list, notes_text)
        
        ok, msg = git_push(f"tasks for {folder}", "Update")
        if ok:
            self.set_status(f"Tasks pushed for {folder}! Live in ~1 min.", GREEN)
            messagebox.showinfo("Done!", f"Tasks are live on {folder}'s bulletin.")
            self.refresh_list()  # Update vendor list to show status indicator
        else:
            self.set_status(f"Saved locally for {folder}. Git push failed.", RED)
            messagebox.showwarning("Partial", f"Saved locally but push failed:\n{msg}")

    def clear_tasks(self):
        """Clear tasks for the selected vendor."""
        sel = self.vendor_combo_var.get()
        if not sel or "(" not in sel:
            messagebox.showwarning("No Vendor", "Please select a vendor first.")
            return
        
        folder = sel.split("(")[-1].rstrip(")")
        
        if not messagebox.askyesno("Clear Tasks",
                                    f"Clear all tasks for {folder}?"):
            return
        
        self.set_status(f"Clearing tasks for {folder}...")
        save_bulletin(folder, [], "")
        
        ok, msg = git_push(f"clear tasks for {folder}", "Update")
        if ok:
            self.set_status(f"Tasks cleared for {folder}!", GREEN)
            self.tasks_text.delete("1.0", tk.END)
            self.notes_entry.delete(0, tk.END)
            self.refresh_list()  # Update vendor list
        else:
            self.set_status(f"Cleared locally for {folder}. Git push failed.", RED)
            messagebox.showwarning("Partial", f"Cleared locally but push failed:\n{msg}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
