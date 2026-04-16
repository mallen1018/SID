#!/usr/bin/env python3
"""
SID Manager Server - Vendor Management Backend
Serves static files and provides JSON-based API endpoints for managing vendors, postings, and bulletins.
Uses only Python standard library (http.server, no Flask).
"""

import http.server
import json
import os
import sys
import re
import subprocess
import urllib.request
import ssl
from datetime import date
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import io
from io import BytesIO
import base64
import traceback

# CSV Pipeline module
try:
    import csv_pipeline
except ImportError:
    csv_pipeline = None


class SIDManagerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for SID Manager API and static file serving."""

    # Set SCRIPT_DIR (directory where this script runs from)
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

    def log_message(self, format, *args):
        """Log to stderr so nohup captures it."""
        sys.stderr.write(f"[LOG] {self.client_address[0]} - {format % args}\n")
        sys.stderr.flush()

    def do_GET(self):
        """Handle GET requests for static files and API endpoints."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        print(f"[GET] {path}", flush=True)

        # API endpoints
        if path == "/api/vendors":
            self.handle_get_vendors()
        elif path == "/api/vendor-accounts":
            self.handle_get_vendor_accounts()
        elif path.startswith("/api/postings/"):
            vendor = path.replace("/api/postings/", "")
            self.handle_get_postings(vendor)
        elif path.startswith("/api/alerts/"):
            vendor = path.replace("/api/alerts/", "").split("?")[0].rstrip("/")
            self.handle_get_alerts(vendor)
        elif path.startswith("/api/bulletin/"):
            vendor = path.replace("/api/bulletin/", "")
            self.handle_get_bulletin(vendor)
        elif path == "/api/announcements":
            self.handle_get_announcements()
        elif path.startswith("/api/assignments/"):
            vendor = path.replace("/api/assignments/", "")
            self.handle_get_assignments(vendor)
        elif path == "/api/assignments":
            self.handle_get_all_assignments()
        elif path.startswith("/api/performance/"):
            vendor = path.replace("/api/performance/", "")
            self.handle_get_performance(vendor)
        elif path.startswith("/api/activity/"):
            vendor = path.replace("/api/activity/", "")
            self.handle_get_activity(vendor)
        elif path == "/api/activity":
            self.handle_get_all_activity()
        elif path == "/api/ai-config":
            self.handle_get_ai_config()
        elif path.startswith("/api/runs/"):
            vendor = path.replace("/api/runs/", "").split("?")[0].rstrip("/")
            self.handle_get_runs(vendor)
        elif path == "/api/candidates" or path.startswith("/api/candidates?"):
            self.handle_get_candidates()
        elif path.startswith("/api/candidates/"):
            vendor = path.replace("/api/candidates/", "").split("?")[0]
            self.handle_get_candidates(vendor)
        elif path.startswith("/api/processed/"):
            parts = path.replace("/api/processed/", "").split("/", 1)
            vendor = parts[0]
            if len(parts) > 1 and parts[1]:
                self.handle_get_processed_file(vendor, parts[1])
            else:
                self.handle_get_processed(vendor)
        elif path.startswith("/api/analytics/"):
            vendor = path.replace("/api/analytics/", "")
            self.handle_get_analytics(vendor)
        elif path == "/api/analytics":
            self.handle_get_analytics_all()
        elif path == "/api/pipeline-config":
            self.handle_get_pipeline_config()
        elif path == "/api/pipeline-log":
            self.handle_get_pipeline_log()
        elif path == "/api/pipeline-exports":
            self.handle_get_pipeline_exports()
        elif path.startswith("/api/pipeline-export/"):
            category = path.replace("/api/pipeline-export/", "").split("?")[0].rstrip("/")
            self.handle_get_combined_export(category)
        elif path == "/api/master-lists":
            self.handle_get_master_list_categories()
        elif path.startswith("/api/master-list/"):
            category = path.replace("/api/master-list/", "").split("?")[0].rstrip("/")
            self.handle_get_master_list(category)
        elif path.startswith("/api/uploads/"):
            vendor = path.replace("/api/uploads/", "")
            self.handle_get_uploads(vendor)
        elif path.startswith("/uploads/"):
            # Serve uploaded files statically
            self.serve_upload_file(path)
        elif path.startswith("/portal/"):
            # Serve dynamic vendor portal: /portal/VENDORNAME/
            self.serve_vendor_portal(path)
        elif path == "/":
            # Serve manager.html as root
            self.serve_static_file("manager.html")
        elif path.startswith("/"):
            # Serve static files
            self.serve_static_file(path.lstrip("/"))
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests for API endpoints."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        print(f"[POST] {path}", flush=True)

        # File upload endpoints (multipart) — handle before reading body as raw bytes
        if path.startswith("/api/upload/"):
            self.handle_file_upload(path)
            return

        # Read request body for JSON endpoints
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path.startswith("/api/postings/"):
            vendor = path.replace("/api/postings/", "")
            self.handle_post_postings(vendor, body)
        elif path.startswith("/api/alerts/"):
            vendor = path.replace("/api/alerts/", "").split("/")[0]
            self.handle_post_alert(vendor, body)
        elif path.startswith("/api/bulletin/"):
            vendor = path.replace("/api/bulletin/", "")
            self.handle_post_bulletin(vendor, body)
        elif path == "/api/announcements":
            self.handle_post_announcements(body)
        elif path == "/api/push":
            self.handle_post_push(body)
        elif path.startswith("/api/assignments/"):
            vendor = path.replace("/api/assignments/", "")
            self.handle_post_assignments(vendor, body)
        elif path.startswith("/api/activity/"):
            vendor = path.replace("/api/activity/", "")
            self.handle_post_activity(vendor, body)
        elif path == "/api/vendor-accounts":
            self.handle_post_vendor_accounts(body)
        elif path == "/api/vendors":
            self.handle_create_vendor(body)
        elif path.startswith("/api/peek-upload/"):
            vendor = path.replace("/api/peek-upload/", "")
            self.handle_peek_upload(vendor, body)
        elif path.startswith("/api/process-upload/"):
            vendor = path.replace("/api/process-upload/", "")
            self.handle_process_upload(vendor, body)
        elif path.startswith("/api/runs/") and "/confirm" in path:
            vendor = path.replace("/api/runs/", "").replace("/confirm", "").strip("/")
            self.handle_post_confirm_links(vendor, body)
        elif path.startswith("/api/runs/") and "/map" in path:
            vendor = path.replace("/api/runs/", "").replace("/map", "").strip("/")
            self.handle_post_title_map(vendor, body)
        elif path == "/api/generate-posting":
            self.handle_generate_posting(body)
        elif path == "/api/ai-config":
            self.handle_save_ai_config(body)
        elif path == "/api/pipeline-config":
            self.handle_save_pipeline_config(body)
        elif path == "/api/csv-clean":
            self.handle_csv_clean(body)
        elif path.startswith("/api/master-list/") and path.endswith("/add"):
            category = path.replace("/api/master-list/", "").replace("/add", "").strip("/")
            self.handle_add_to_master_list(category, body)
        elif path.startswith("/api/master-list/") and path.endswith("/dedup"):
            category = path.replace("/api/master-list/", "").replace("/dedup", "").strip("/")
            self.handle_dedup_master_list(category, body)
        elif path == "/api/row-divide":
            self.handle_row_divide(body)
        elif path == "/api/pipeline-run":
            self.handle_pipeline_run(body)
        else:
            self.send_error(404)

    def do_PATCH(self):
        """Handle PATCH requests for updating individual assignments."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        if path.startswith("/api/assignments/"):
            vendor = path.replace("/api/assignments/", "")
            self.handle_patch_assignment(vendor, body)
        else:
            self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests for cancelling assignments."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'

        if path.startswith("/api/assignments/"):
            vendor = path.replace("/api/assignments/", "")
            self.handle_delete_assignment(vendor, body)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def handle_get_vendors(self):
        """API: GET /api/vendors - List all vendors."""
        vendors = self.scan_vendors()
        self.send_json_response(vendors)

    def handle_get_vendor_accounts(self):
        """API: GET /api/vendor-accounts - Get account config per vendor."""
        config_file = os.path.join(self.SCRIPT_DIR, "vendor_accounts.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                self.send_json_response(data)
            except (json.JSONDecodeError, IOError):
                self.send_json_response({"default": [{"id": "indeed-usd", "label": "Indeed (USD)"}, {"id": "linkedin", "label": "LinkedIn"}]})
        else:
            self.send_json_response({"default": [{"id": "indeed-usd", "label": "Indeed (USD)"}, {"id": "linkedin", "label": "LinkedIn"}]})

    def handle_post_vendor_accounts(self, body):
        """API: POST /api/vendor-accounts - Save account config."""
        try:
            data = json.loads(body.decode("utf-8"))
            config_file = os.path.join(self.SCRIPT_DIR, "vendor_accounts.json")
            with open(config_file, "w") as f:
                json.dump(data, f, indent=2)
            self.send_json_response({"ok": True, "message": "Accounts saved"})
        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)

    def handle_create_vendor(self, body):
        """API: POST /api/vendors - Create a new vendor with full portal from template."""
        try:
            data = json.loads(body.decode("utf-8"))
            folder = data.get("folder", "").strip()
            display_name = data.get("display_name", folder).strip()

            if not folder:
                self.send_json_response({"ok": False, "message": "Folder name required"}, status=400)
                return

            # Sanitize folder name
            folder = re.sub(r'[^a-zA-Z0-9_-]', '', folder)
            vendor_path = os.path.join(self.SCRIPT_DIR, folder)

            if os.path.exists(vendor_path):
                self.send_json_response({"ok": False, "message": f"Vendor '{folder}' already exists"}, status=400)
                return

            os.makedirs(vendor_path, exist_ok=True)

            # Use the simple portal template (portal_demo.html) as the starting point
            # This gives vendors: Install extension, Guide link, Upload button, Onboarding checklist
            simple_template = os.path.join(self.SCRIPT_DIR, "portal_demo.html")
            guide_template_vendor = "FBSPL"
            guide_template = os.path.join(self.SCRIPT_DIR, guide_template_vendor, "guide.html")

            # Create index.html from simple portal template
            if os.path.exists(simple_template):
                with open(simple_template, "r", encoding="utf-8") as f:
                    content = f.read()
                # Replace demo vendor references with new vendor
                content = content.replace("Opus Galleria", display_name)
                content = content.replace("OpusGalleria", folder)
                # Remove the demo controls bar (everything between demo-bar div)
                import re as _re
                content = _re.sub(r'<div class="demo-bar">.*?</div>\s*', '', content, flags=_re.DOTALL)
                # Remove demo control JS functions
                content = _re.sub(r'// ── Demo Controls ──.*?updateChecklist\(\);\s*', '', content, flags=_re.DOTALL)
                # Set upload link as placeholder (to be configured in vendor settings)
                content = content.replace(
                    'href="https://jobosaurus-my.sharepoint.com/:f:/g/personal/mallen_wallstjobs_com/IgCHcPr36uaFQYkLdTZGMx4dAfpAbdsj9uukjvIara-mBC0"',
                    'href="#" onclick="alert(\'Upload link not configured yet. Contact your admin.\');return false;"'
                )
                with open(os.path.join(vendor_path, "index.html"), "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(os.path.join(vendor_path, "index.html"), "w", encoding="utf-8") as f:
                    f.write(f"<!DOCTYPE html><html><head><title>{display_name}</title></head><body><h1>{display_name}</h1><p>Portal coming soon.</p></body></html>")

            # Create guide.html from existing guide template
            if os.path.exists(guide_template):
                with open(guide_template, "r", encoding="utf-8") as f:
                    content = f.read()
                content = content.replace(guide_template_vendor, folder)
                content = content.replace(f"<title>SID Vendor Guide - {folder}", f"<title>SID Vendor Guide - {display_name}")
                content = content.replace(f"Guide &mdash; {folder}", f"Guide &mdash; {display_name}")
                with open(os.path.join(vendor_path, "guide.html"), "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                with open(os.path.join(vendor_path, "guide.html"), "w", encoding="utf-8") as f:
                    f.write(f"<!DOCTYPE html><html><head><title>{display_name} Guide</title></head><body><h1>{display_name} Guide</h1><p>Coming soon.</p></body></html>")

            # Create empty postings file
            postings_file = os.path.join(self.SCRIPT_DIR, f"postings_{folder}.json")
            with open(postings_file, "w") as f:
                json.dump({"categories": {}}, f, indent=2)

            # Create empty bulletin file
            bulletin_file = os.path.join(self.SCRIPT_DIR, f"bulletin_{folder}.json")
            with open(bulletin_file, "w") as f:
                json.dump([], f)

            # Add default accounts
            config_file = os.path.join(self.SCRIPT_DIR, "vendor_accounts.json")
            try:
                with open(config_file, "r") as f:
                    accounts = json.load(f)
            except:
                accounts = {}
            accounts[folder] = [
                {"id": "indeed-usd", "platform": "Indeed", "label": "Indeed (USD)", "currency": "USD", "description": "US dollar billing"},
                {"id": "linkedin", "platform": "LinkedIn", "label": "LinkedIn", "currency": "USD", "description": "LinkedIn job slots"}
            ]
            with open(config_file, "w") as f:
                json.dump(accounts, f, indent=2)

            self.send_json_response({
                "ok": True,
                "message": f"Vendor '{display_name}' created with full portal",
                "folder": folder,
                "portal_url": f"/{folder}",
            })
        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            self.send_json_response({"ok": False, "message": str(e)}, status=500)

    def handle_get_postings(self, vendor):
        """API: GET /api/postings/<vendor> - Get postings for a vendor."""
        postings_file = os.path.join(self.SCRIPT_DIR, f"postings_{vendor}.json")
        if os.path.exists(postings_file):
            try:
                with open(postings_file, "r") as f:
                    data = json.load(f)
                self.send_json_response(data)
            except (json.JSONDecodeError, IOError) as e:
                self.send_json_response({"categories": {}}, status=200)
        else:
            self.send_json_response({"categories": {}})

    def handle_post_postings(self, vendor, body):
        """API: POST /api/postings/<vendor> - Save postings for a vendor."""
        try:
            data = json.loads(body.decode("utf-8"))
            postings_file = os.path.join(self.SCRIPT_DIR, f"postings_{vendor}.json")
            with open(postings_file, "w") as f:
                json.dump(data, f, indent=2)
            self.send_json_response({"ok": True, "message": f"Postings saved for {vendor}"})
        except json.JSONDecodeError:
            self.send_json_response(
                {"ok": False, "message": "Invalid JSON in request body"}, status=400
            )
        except IOError as e:
            self.send_json_response(
                {"ok": False, "message": f"File write error: {str(e)}"}, status=500
            )

    def handle_get_bulletin(self, vendor):
        """API: GET /api/bulletin/<vendor> - Get bulletin for a vendor."""
        bulletin_file = os.path.join(self.SCRIPT_DIR, f"bulletin_{vendor}.json")
        if os.path.exists(bulletin_file):
            try:
                with open(bulletin_file, "r") as f:
                    data = json.load(f)
                # Auto-migrate old format { tasks, notes } to new format { history: [...] }
                if 'history' not in data and ('tasks' in data or 'notes' in data):
                    from datetime import date
                    today = date.today().isoformat()
                    tasks = data.get('tasks', '')
                    if isinstance(tasks, str):
                        tasks = [t.strip() for t in tasks.split('\n') if t.strip()]
                    data = {
                        'history': [{
                            'date': today,
                            'tasks': tasks,
                            'notes': data.get('notes', '')
                        }]
                    }
                    # Save migrated data back to file
                    with open(bulletin_file, 'w') as f:
                        json.dump(data, f, indent=2)
                self.send_json_response(data)
            except (json.JSONDecodeError, IOError):
                default_bulletin = {"history": []}
                self.send_json_response(default_bulletin, status=200)
        else:
            default_bulletin = {"history": []}
            self.send_json_response(default_bulletin)

    def handle_post_bulletin(self, vendor, body):
        """API: POST /api/bulletin/<vendor> - Save bulletin for a vendor (with history)."""
        try:
            data = json.loads(body.decode("utf-8"))
            # Validate history format
            if 'history' in data and isinstance(data['history'], list):
                bulletin_file = os.path.join(self.SCRIPT_DIR, f"bulletin_{vendor}.json")
                with open(bulletin_file, "w") as f:
                    json.dump(data, f, indent=2)
                self.send_json_response({"ok": True, "message": f"Bulletin saved for {vendor}"})
            else:
                self.send_json_response(
                    {"ok": False, "message": "Invalid bulletin format. Expected { history: [...] }"}, status=400
                )
        except json.JSONDecodeError:
            self.send_json_response(
                {"ok": False, "message": "Invalid JSON in request body"}, status=400
            )
        except IOError as e:
            self.send_json_response(
                {"ok": False, "message": f"File write error: {str(e)}"}, status=500
            )

    # ── Vendor Alerts System ─────────────────────────────────────────────
    # Persistent alerts pushed from manager to vendor portal.
    # Types: missing_csv, action_required, info, warning
    # Alerts are stored per-vendor in alerts/{vendor}.json

    ALERTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alerts")

    def _get_alerts_file(self, vendor):
        os.makedirs(self.ALERTS_DIR, exist_ok=True)
        return os.path.join(self.ALERTS_DIR, f"{vendor}.json")

    def _load_alerts(self, vendor):
        fpath = self._get_alerts_file(vendor)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"alerts": []}

    def _save_alerts(self, vendor, data):
        fpath = self._get_alerts_file(vendor)
        with open(fpath, 'w') as f:
            json.dump(data, f, indent=2)

    def handle_get_alerts(self, vendor):
        """API: GET /api/alerts/<vendor> — list active alerts for a vendor."""
        data = self._load_alerts(vendor)
        # Filter: only return non-dismissed alerts by default
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        show_all = params.get("all", ["0"])[0] == "1"
        if not show_all:
            data["alerts"] = [a for a in data["alerts"] if not a.get("dismissed")]
        self.send_json_response(data)

    def handle_post_alert(self, vendor, body, silent=False):
        """
        API: POST /api/alerts/<vendor>
        Actions:
          create: { action: "create", type, title, message, ... }
                  OR legacy: { action: "create", alert: { type, title, message, ... } }
          dismiss: { action: "dismiss", alert_id: "..." }
          dismiss_all: { action: "dismiss_all" }

        If silent=True, skips HTTP response (for internal calls from PATCH etc.)
        """
        try:
            payload = json.loads(body.decode("utf-8")) if isinstance(body, bytes) else json.loads(body)
            action = payload.get("action", "create")
            data = self._load_alerts(vendor)

            if action == "create":
                # Support both { alert: { ... } } and flat { type, title, message, ... }
                alert_info = payload.get("alert", None)
                if alert_info is None:
                    # Flat format — fields are directly in payload
                    alert_info = payload

                alert = {
                    "id": f"alert-{len(data['alerts'])+1}-{int(__import__('time').time()*1000)}",
                    "type": alert_info.get("type", "info"),
                    "title": alert_info.get("title", "Alert"),
                    "message": alert_info.get("message", ""),
                    "job_title": alert_info.get("job_title", ""),
                    "job_id": alert_info.get("job_id", ""),
                    "category": alert_info.get("category", ""),
                    "metadata": alert_info.get("metadata", {}),
                    "created_at": self._timestamp(),
                    "created_by": "manager",
                    "dismissed": False,
                    "dismissed_at": None,
                    "priority": alert_info.get("priority", "normal"),
                }
                data["alerts"].insert(0, alert)
                self._save_alerts(vendor, data)
                print(f"[ALERT] {vendor}: created '{alert['type']}' alert — {alert['title']}", flush=True)
                if not silent:
                    self.send_json_response({"ok": True, "alert": alert})

            elif action == "dismiss":
                alert_id = payload.get("alert_id", "")
                for a in data["alerts"]:
                    if a["id"] == alert_id:
                        a["dismissed"] = True
                        a["dismissed_at"] = self._timestamp()
                        break
                self._save_alerts(vendor, data)
                if not silent:
                    self.send_json_response({"ok": True, "message": f"Alert {alert_id} dismissed"})

            elif action == "dismiss_all":
                for a in data["alerts"]:
                    if not a.get("dismissed"):
                        a["dismissed"] = True
                        a["dismissed_at"] = self._timestamp()
                self._save_alerts(vendor, data)
                if not silent:
                    self.send_json_response({"ok": True, "message": "All alerts dismissed"})

            else:
                if not silent:
                    self.send_json_response({"ok": False, "message": f"Unknown action: {action}"}, status=400)

        except json.JSONDecodeError:
            if not silent:
                self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            if not silent:
                self.send_json_response({"ok": False, "message": str(e)}, status=500)

    def handle_get_announcements(self):
        """API: GET /api/announcements - Get announcements."""
        announcements_file = os.path.join(self.SCRIPT_DIR, "announcements.json")
        if os.path.exists(announcements_file):
            try:
                with open(announcements_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                    else:
                        data = {}
                self.send_json_response(data)
            except (json.JSONDecodeError, IOError):
                self.send_json_response({})
        else:
            self.send_json_response({})

    def handle_post_announcements(self, body):
        """API: POST /api/announcements - Save announcements."""
        try:
            data = json.loads(body.decode("utf-8"))
            announcements_file = os.path.join(self.SCRIPT_DIR, "announcements.json")
            with open(announcements_file, "w") as f:
                json.dump(data, f, indent=2)
            self.send_json_response({"ok": True, "message": "Announcements saved"})
        except json.JSONDecodeError:
            self.send_json_response(
                {"ok": False, "message": "Invalid JSON in request body"}, status=400
            )
        except IOError as e:
            self.send_json_response(
                {"ok": False, "message": f"File write error: {str(e)}"}, status=500
            )

    def handle_post_push(self, body):
        """API: POST /api/push - Run git add, commit, and push."""
        try:
            data = json.loads(body.decode("utf-8"))
            message = data.get("message", "Update via SID Manager")
        except json.JSONDecodeError:
            message = "Update via SID Manager"

        try:
            # Save current directory
            original_cwd = os.getcwd()
            # Change to SCRIPT_DIR
            os.chdir(self.SCRIPT_DIR)

            # Run git commands
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", message],
                check=True,
                capture_output=True,
            )
            subprocess.run(["git", "push"], check=True, capture_output=True)

            # Restore directory
            os.chdir(original_cwd)

            self.send_json_response(
                {"ok": True, "message": f"Pushed: {message}"}
            )
        except subprocess.CalledProcessError as e:
            os.chdir(original_cwd) if 'original_cwd' in locals() else None
            self.send_json_response(
                {"ok": False, "message": f"Git error: {str(e)}"}, status=500
            )
        except Exception as e:
            os.chdir(original_cwd) if 'original_cwd' in locals() else None
            self.send_json_response(
                {"ok": False, "message": f"Error: {str(e)}"}, status=500
            )

    # ── Assignment Persistence ─────────────────────────────────────────

    ASSIGNMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assignments")

    def _get_assignments_file(self, vendor, assign_date=None):
        """Get path to a vendor's assignments file for a given date."""
        if assign_date is None:
            assign_date = date.today().isoformat()
        vendor_dir = os.path.join(self.ASSIGNMENTS_DIR, vendor)
        os.makedirs(vendor_dir, exist_ok=True)
        return os.path.join(vendor_dir, f"{assign_date}.json")

    def _load_assignments(self, vendor, assign_date=None):
        """Load assignments for a vendor on a given date."""
        filepath = self._get_assignments_file(vendor, assign_date)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "date": assign_date or date.today().isoformat(),
            "vendor": vendor,
            "assignments": []
        }

    def _save_assignments(self, vendor, data, assign_date=None):
        """Save assignments for a vendor."""
        filepath = self._get_assignments_file(vendor, assign_date)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def handle_get_assignments(self, vendor):
        """
        API: GET /api/assignments/<vendor>
        Returns assignments for today by default, or ?date=YYYY-MM-DD for a specific date.
        Also supports ?range=7 for multiple days, and ?status=active to filter.
        """
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        status_filter = params.get("status", [None])[0]

        if "range" in params:
            from datetime import timedelta
            days = int(params["range"][0])
            results = {}
            for i in range(days):
                d = (date.today() - timedelta(days=i)).isoformat()
                data = self._load_assignments(vendor, d)
                assignments = data.get("assignments", [])
                if status_filter:
                    assignments = [a for a in assignments if a.get("status") == status_filter]
                if assignments:
                    results[d] = {"date": d, "vendor": vendor, "assignments": assignments}
            self.send_json_response(results)
        else:
            assign_date = params.get("date", [date.today().isoformat()])[0]
            data = self._load_assignments(vendor, assign_date)
            if status_filter:
                data["assignments"] = [a for a in data["assignments"] if a.get("status") == status_filter]
            self.send_json_response(data)

    def handle_get_all_assignments(self):
        """
        API: GET /api/assignments
        Returns today's assignments across all vendors. Used by team dashboard.
        Supports ?date=YYYY-MM-DD
        """
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        target_date = params.get("date", [date.today().isoformat()])[0]

        result = {}
        if os.path.exists(self.ASSIGNMENTS_DIR):
            for vendor_folder in os.listdir(self.ASSIGNMENTS_DIR):
                vendor_path = os.path.join(self.ASSIGNMENTS_DIR, vendor_folder)
                if os.path.isdir(vendor_path):
                    data = self._load_assignments(vendor_folder, target_date)
                    if data.get("assignments"):
                        result[vendor_folder] = data
        self.send_json_response(result)

    def handle_post_assignments(self, vendor, body):
        """
        API: POST /api/assignments/<vendor>
        Push new assignments from manager. Merges with existing assignments for the date.
        Accepts: { assignments: [...], date: "YYYY-MM-DD" }

        Each assignment object:
        {
            id: "SFG-0",                    // from posting grid
            title: "Senior Financial Analyst",
            category: "SFG",
            account: "indeed-usd",
            budget: "$5/day, $10 max",
            closeDate: "2026-03-28",
            location: { type: "Hybrid", ... },
            salary: "$95,000 - $120,000",
            benefits: [...],
            description: "...",
            status: "active"
        }
        """
        try:
            payload = json.loads(body.decode("utf-8"))
            new_assignments = payload.get("assignments", [])
            assign_date = payload.get("date", date.today().isoformat())

            if not new_assignments:
                self.send_json_response({"ok": False, "message": "No assignments provided"}, status=400)
                return

            # Load existing assignments for this date
            data = self._load_assignments(vendor, assign_date)
            existing = data.get("assignments", [])

            # Generate unique IDs and set defaults
            from datetime import datetime
            now = datetime.now().isoformat()

            for assignment in new_assignments:
                # Create a truly unique ID if not present or if it's a grid-based id
                if "uid" not in assignment:
                    base_id = assignment.get("id", "unknown")
                    assignment["uid"] = f"{vendor}-{base_id}-{int(datetime.now().timestamp() * 1000)}"

                assignment.setdefault("status", "active")
                assignment.setdefault("assignedAt", now)
                assignment.setdefault("assignedBy", "manager")

                # Avoid duplicates: remove existing with same uid
                existing = [a for a in existing if a.get("uid") != assignment["uid"]]
                existing.append(assignment)

            data["assignments"] = existing
            data["date"] = assign_date
            data["vendor"] = vendor
            self._save_assignments(vendor, data, assign_date)

            count = len(new_assignments)
            print(f"[ASSIGNMENTS] Pushed {count} assignment(s) to {vendor} for {assign_date}", flush=True)
            self.send_json_response({
                "ok": True,
                "message": f"Pushed {count} assignment(s) to {vendor}",
                "count": count
            })

        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"[ASSIGNMENT ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": f"Error: {str(e)}"}, status=500)

    def handle_patch_assignment(self, vendor, body):
        """
        API: PATCH /api/assignments/<vendor>
        Update fields on an existing assignment.
        Accepts: { uid: "...", date: "YYYY-MM-DD", updates: { field: value, ... } }

        Updatable fields: closeDate, budget, account, status, notes, category, description
        Status values: active, posted, closed, cancelled, paused
        """
        try:
            payload = json.loads(body.decode("utf-8"))
            uid = payload.get("uid")
            assign_date = payload.get("date", date.today().isoformat())
            updates = payload.get("updates", {})

            if not uid:
                self.send_json_response({"ok": False, "message": "Missing uid"}, status=400)
                return

            data = self._load_assignments(vendor, assign_date)
            found = False

            for assignment in data["assignments"]:
                if assignment.get("uid") == uid:
                    # Apply updates
                    allowed_fields = {
                        "closeDate", "budget", "account", "status", "notes",
                        "category", "description", "title", "salary", "location",
                        "benefits", "budgetInstructions"
                    }
                    for key, value in updates.items():
                        if key in allowed_fields:
                            assignment[key] = value

                    # Track modification
                    from datetime import datetime
                    assignment["lastModified"] = datetime.now().isoformat()
                    assignment["modifiedBy"] = "manager"

                    found = True
                    print(f"[ASSIGNMENTS] Updated {uid} for {vendor}: {list(updates.keys())}", flush=True)
                    break

            if not found:
                self.send_json_response({"ok": False, "message": f"Assignment {uid} not found"}, status=404)
                return

            self._save_assignments(vendor, data, assign_date)

            # ── Auto-push alert to vendor if requested ──
            alert_vendor = payload.get("alert", True)  # default: auto-alert
            if alert_vendor and found:
                title_str = assignment.get("title", uid)
                changes = []
                if "closeDate" in updates:
                    changes.append(f"close date → {updates['closeDate']}")
                if "budget" in updates or "budgetInstructions" in updates:
                    budget_val = updates.get("budgetInstructions") or updates.get("budget", "")
                    changes.append(f"budget → {budget_val}")
                if "notes" in updates:
                    changes.append(f"note: {updates['notes']}")
                if "status" in updates:
                    changes.append(f"status → {updates['status']}")

                if changes:
                    alert_body = {
                        "action": "create",
                        "type": "action_required",
                        "priority": "high",
                        "title": f"Update: {title_str}",
                        "message": f"Melissa adjusted this posting — {', '.join(changes)}. Please update on Indeed.",
                        "metadata": {"uid": uid, "updates": updates}
                    }
                    try:
                        self.handle_post_alert(vendor, json.dumps(alert_body).encode("utf-8"), silent=True)
                        print(f"[ALERT] Auto-pushed adjustment alert to {vendor} for {uid}", flush=True)
                    except Exception as ae:
                        print(f"[ALERT WARN] Could not auto-push alert: {ae}", flush=True)

            self.send_json_response({"ok": True, "message": f"Assignment {uid} updated"})

        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"[ASSIGNMENT ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": f"Error: {str(e)}"}, status=500)

    def handle_delete_assignment(self, vendor, body):
        """
        API: DELETE /api/assignments/<vendor>
        Cancel/remove an assignment.
        Accepts: { uid: "...", date: "YYYY-MM-DD", hard: false }

        soft delete (default): sets status to "cancelled"
        hard delete (hard: true): removes from list entirely
        """
        try:
            payload = json.loads(body.decode("utf-8"))
            uid = payload.get("uid")
            assign_date = payload.get("date", date.today().isoformat())
            hard_delete = payload.get("hard", False)

            if not uid:
                self.send_json_response({"ok": False, "message": "Missing uid"}, status=400)
                return

            data = self._load_assignments(vendor, assign_date)

            if hard_delete:
                original_count = len(data["assignments"])
                data["assignments"] = [a for a in data["assignments"] if a.get("uid") != uid]
                if len(data["assignments"]) == original_count:
                    self.send_json_response({"ok": False, "message": f"Assignment {uid} not found"}, status=404)
                    return
                print(f"[ASSIGNMENTS] Hard-deleted {uid} from {vendor}", flush=True)
            else:
                found = False
                for assignment in data["assignments"]:
                    if assignment.get("uid") == uid:
                        assignment["status"] = "cancelled"
                        from datetime import datetime
                        assignment["cancelledAt"] = datetime.now().isoformat()
                        found = True
                        print(f"[ASSIGNMENTS] Cancelled {uid} for {vendor}", flush=True)
                        break
                if not found:
                    self.send_json_response({"ok": False, "message": f"Assignment {uid} not found"}, status=404)
                    return

            self._save_assignments(vendor, data, assign_date)
            action = "deleted" if hard_delete else "cancelled"
            self.send_json_response({"ok": True, "message": f"Assignment {uid} {action}"})

        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"[ASSIGNMENT ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": f"Error: {str(e)}"}, status=500)

    # ── Vendor Activity Tracking ──────────────────────────────────────

    ACTIVITY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "activity")

    def _get_activity_file(self, vendor, activity_date=None):
        """Get path to a vendor's activity file for a given date."""
        if activity_date is None:
            activity_date = date.today().isoformat()
        vendor_dir = os.path.join(self.ACTIVITY_DIR, vendor)
        os.makedirs(vendor_dir, exist_ok=True)
        return os.path.join(vendor_dir, f"{activity_date}.json")

    def _load_activity(self, vendor, activity_date=None):
        """Load activity data for a vendor on a given date."""
        filepath = self._get_activity_file(vendor, activity_date)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"date": activity_date or date.today().isoformat(), "vendor": vendor, "closed": [], "posted": []}

    def _save_activity(self, vendor, data, activity_date=None):
        """Save activity data for a vendor."""
        filepath = self._get_activity_file(vendor, activity_date)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def handle_post_activity(self, vendor, body):
        """
        API: POST /api/activity/<vendor>
        Accepts: { action: "close"|"post"|"undo_close"|"undo_post", data: {...} }

        Close data: { id, title, category, postedDate, closedDate, applicants, budgetSpent, indeedLink }
        Post data:  { id, title, category, account, indeedLink|linkedinLink }
        """
        try:
            payload = json.loads(body.decode("utf-8"))
            action = payload.get("action")
            item = payload.get("data", {})
            activity_date = payload.get("date", date.today().isoformat())

            if action not in ("close", "post", "undo_close", "undo_post"):
                self.send_json_response(
                    {"ok": False, "message": "Invalid action. Use: close, post, undo_close, undo_post"},
                    status=400
                )
                return

            activity = self._load_activity(vendor, activity_date)

            if action == "close":
                # Add to closed list (avoid duplicates by id)
                activity["closed"] = [c for c in activity["closed"] if c.get("id") != item.get("id")]
                item["closedAt"] = self._timestamp()
                activity["closed"].append(item)
                print(f"[ACTIVITY] {vendor}: closed posting #{item.get('id')} — {item.get('title')}", flush=True)

            elif action == "undo_close":
                activity["closed"] = [c for c in activity["closed"] if c.get("id") != item.get("id")]
                print(f"[ACTIVITY] {vendor}: undo close for posting #{item.get('id')}", flush=True)

            elif action == "post":
                activity["posted"] = [p for p in activity["posted"] if p.get("id") != item.get("id")]
                item["postedAt"] = self._timestamp()
                activity["posted"].append(item)
                link = item.get("indeedLink") or item.get("linkedinLink") or ""
                print(f"[ACTIVITY] {vendor}: posted #{item.get('id')} — {item.get('title')} → {link[:60]}", flush=True)

            elif action == "undo_post":
                activity["posted"] = [p for p in activity["posted"] if p.get("id") != item.get("id")]
                print(f"[ACTIVITY] {vendor}: undo post for #{item.get('id')}", flush=True)

            self._save_activity(vendor, activity, activity_date)
            self.send_json_response({"ok": True, "message": f"Activity '{action}' recorded"})

        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"[ACTIVITY ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": f"Error: {str(e)}"}, status=500)

    def handle_get_performance(self, vendor):
        """
        API: GET /api/performance/<vendor>
        Scans all activity files for the vendor and aggregates closed posting data into
        performance stats: per posting and per category (applicants, budget, cost-per-applicant).
        """
        CURRENCY_SYMBOLS = {"$": "$", "₹": "₹", "€": "€", "£": "£", "C$": "C$", "A$": "A$", "₱": "₱", "MX$": "MX$"}
        # Approximate conversion rates to USD (updated periodically)
        TO_USD = {"$": 1.0, "₹": 0.012, "€": 1.08, "£": 1.26, "C$": 0.74, "A$": 0.65, "₱": 0.018, "MX$": 0.058}

        def parse_budget(raw):
            """Extract numeric value and currency symbol from budget string."""
            s = str(raw).strip()
            symbol = "$"
            for sym in sorted(CURRENCY_SYMBOLS.keys(), key=len, reverse=True):
                if s.startswith(sym):
                    symbol = sym
                    s = s[len(sym):]
                    break
            try:
                return float(s.replace(",", "").replace(" ", "")), symbol
            except (ValueError, TypeError):
                return 0.0, symbol

        def to_usd(amount, symbol):
            """Convert any currency amount to USD."""
            rate = TO_USD.get(symbol, 1.0)
            return amount * rate

        vendor_activity_dir = os.path.join(self.ACTIVITY_DIR, vendor)
        by_posting = {}   # key -> { title, category, applicants, budget_usd, runs, total_days, currency }
        by_category = {}  # cat -> { applicants, budget_usd, runs, total_days, currency }

        if os.path.exists(vendor_activity_dir):
            for filename in os.listdir(vendor_activity_dir):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(vendor_activity_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                    for closed in data.get("closed", []):
                        title = closed.get("title", "Unknown")
                        cat = closed.get("category", "Uncategorized")
                        applicants = 0
                        try:
                            applicants = int(closed.get("applicants", 0))
                        except (ValueError, TypeError):
                            pass
                        budget, sym = parse_budget(closed.get("budgetSpent", 0))
                        budget_usd = to_usd(budget, sym)

                        key = f"{cat}||{title}"
                        if key not in by_posting:
                            by_posting[key] = {"title": title, "category": cat, "applicants": 0, "budget_usd": 0.0, "runs": 0, "currency": sym}
                        by_posting[key]["applicants"] += applicants
                        by_posting[key]["budget_usd"] += budget_usd
                        by_posting[key]["runs"] += 1

                        if cat not in by_category:
                            by_category[cat] = {"applicants": 0, "budget_usd": 0.0, "runs": 0, "currency": sym}
                        by_category[cat]["applicants"] += applicants
                        by_category[cat]["budget_usd"] += budget_usd
                        by_category[cat]["runs"] += 1
                except (json.JSONDecodeError, IOError):
                    continue

        postings_list = []
        for p in by_posting.values():
            cpa_usd = round(p["budget_usd"] / p["applicants"], 2) if p["applicants"] > 0 else None
            avg_per_run = round(p["applicants"] / p["runs"]) if p["runs"] > 0 else None
            postings_list.append({
                "title": p["title"],
                "category": p["category"],
                "applicants": p["applicants"],
                "runs": p["runs"],
                "avgPerRun": avg_per_run,
                "costPerApplicant": cpa_usd,
                "costPerApplicantDisplay": f"${cpa_usd}" if cpa_usd is not None else None
            })
        postings_list.sort(key=lambda x: x["applicants"], reverse=True)

        categories_list = []
        for cat, c in by_category.items():
            cpa_usd = round(c["budget_usd"] / c["applicants"], 2) if c["applicants"] > 0 else None
            avg_per_run = round(c["applicants"] / c["runs"]) if c["runs"] > 0 else None
            categories_list.append({
                "category": cat,
                "applicants": c["applicants"],
                "runs": c["runs"],
                "avgPerRun": avg_per_run,
                "costPerApplicant": cpa_usd,
                "costPerApplicantDisplay": f"${cpa_usd}" if cpa_usd is not None else None
            })
        categories_list.sort(key=lambda x: x["applicants"], reverse=True)

        self.send_json_response({"postings": postings_list, "categories": categories_list})

    def handle_get_activity(self, vendor):
        """
        API: GET /api/activity/<vendor>
        Returns today's activity by default, or specify ?date=YYYY-MM-DD for a specific date,
        or ?range=7 for the last 7 days.
        """
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "range" in params:
            # Return multiple days
            days = int(params["range"][0])
            from datetime import timedelta
            results = {}
            for i in range(days):
                d = (date.today() - timedelta(days=i)).isoformat()
                activity = self._load_activity(vendor, d)
                if activity["closed"] or activity["posted"]:
                    results[d] = activity
            self.send_json_response(results)
        else:
            activity_date = params.get("date", [date.today().isoformat()])[0]
            activity = self._load_activity(vendor, activity_date)
            self.send_json_response(activity)

    def handle_get_all_activity(self):
        """
        API: GET /api/activity
        Returns today's activity across all vendors. Used by team dashboard.
        Supports ?date=YYYY-MM-DD and ?range=7
        """
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        today = params.get("date", [date.today().isoformat()])[0]

        result = {}
        if os.path.exists(self.ACTIVITY_DIR):
            for vendor_folder in os.listdir(self.ACTIVITY_DIR):
                vendor_path = os.path.join(self.ACTIVITY_DIR, vendor_folder)
                if os.path.isdir(vendor_path):
                    if "range" in params:
                        from datetime import timedelta
                        days = int(params["range"][0])
                        vendor_data = {}
                        for i in range(days):
                            d = (date.today() - timedelta(days=i)).isoformat()
                            activity = self._load_activity(vendor_folder, d)
                            if activity["closed"] or activity["posted"]:
                                vendor_data[d] = activity
                        if vendor_data:
                            result[vendor_folder] = vendor_data
                    else:
                        activity = self._load_activity(vendor_folder, today)
                        if activity["closed"] or activity["posted"]:
                            result[vendor_folder] = activity
        self.send_json_response(result)

    def _timestamp(self):
        """Return current ISO timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    # ── File Upload Handling ──────────────────────────────────────────

    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

    def handle_file_upload(self, path):
        """
        Handle file uploads via multipart form data.
        Routes:
            POST /api/upload/<vendor>/resumes   — daily resume ZIP
            POST /api/upload/<vendor>/eod       — EOD screenshot
        Files saved to: uploads/<vendor>/<YYYY-MM-DD>/<type>_<filename>
        """
        # Parse route: /api/upload/<vendor>/<type>
        parts = path.replace("/api/upload/", "").split("/")
        if len(parts) != 2 or parts[1] not in ("resumes", "eod", "opening"):
            self.send_json_response(
                {"ok": False, "message": "Invalid upload route. Use /api/upload/<vendor>/resumes or /api/upload/<vendor>/eod"},
                status=400
            )
            return

        vendor = parts[0]
        upload_type = parts[1]
        today = date.today().isoformat()

        # Parse multipart form data (no cgi module — manual parsing)
        try:
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" not in content_type:
                self.send_json_response(
                    {"ok": False, "message": "Expected multipart/form-data"},
                    status=400
                )
                return

            # Extract boundary from content type
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part.split("=", 1)[1].strip().strip('"')
                    break

            if not boundary:
                self.send_json_response(
                    {"ok": False, "message": "Missing boundary in content type"},
                    status=400
                )
                return

            # Read raw body
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)

            # Split on boundary
            boundary_bytes = f"--{boundary}".encode()
            parts_raw = raw_body.split(boundary_bytes)

            file_data = None
            original_name = None

            for part in parts_raw:
                if b"Content-Disposition:" not in part and b"content-disposition:" not in part:
                    continue

                # Split headers from body (double newline)
                header_end = part.find(b"\r\n\r\n")
                if header_end == -1:
                    continue

                header_section = part[:header_end].decode("utf-8", errors="replace")
                body_section = part[header_end + 4:]

                # Remove trailing \r\n-- if present
                if body_section.endswith(b"\r\n"):
                    body_section = body_section[:-2]

                # Check if this is the "file" field
                if 'name="file"' in header_section:
                    # Extract filename
                    fn_match = re.search(r'filename="([^"]*)"', header_section)
                    if fn_match:
                        original_name = fn_match.group(1)
                    file_data = body_section

            if file_data is None or not original_name:
                self.send_json_response(
                    {"ok": False, "message": "No file provided. Include a 'file' field."},
                    status=400
                )
                return

            # Sanitize filename
            original_name = os.path.basename(original_name)
            safe_name = re.sub(r'[^\w\-_. ]', '', original_name)
            if not safe_name:
                safe_name = f"{upload_type}_upload"

            # Create directory: uploads/<vendor>/<date>/
            save_dir = os.path.join(self.UPLOAD_DIR, vendor, today)
            os.makedirs(save_dir, exist_ok=True)

            # Prefix with type to avoid name collisions
            prefixes = {"resumes": "resumes_", "eod": "eod_", "opening": "opening_"}
            prefix = prefixes.get(upload_type, f"{upload_type}_")
            save_path = os.path.join(save_dir, f"{prefix}{safe_name}")

            # Write file
            with open(save_path, "wb") as f:
                f.write(file_data)

            file_size = len(file_data)
            size_label = f"{file_size / 1024:.1f} KB" if file_size < 1048576 else f"{file_size / 1048576:.1f} MB"

            print(f"[UPLOAD] {upload_type} from {vendor}: {safe_name} ({size_label}) → {save_path}", flush=True)

            response = {
                "ok": True,
                "message": f"Uploaded {safe_name} ({size_label})",
                "filename": safe_name,
                "size": file_size,
                "path": f"uploads/{vendor}/{today}/{prefix}{safe_name}"
            }

            # AUTO-PIPELINE: If this is a resumes ZIP, auto-process it
            if upload_type == "resumes" and safe_name.lower().endswith(".zip") and csv_pipeline:
                try:
                    print(f"[PIPELINE] Auto-processing {vendor} ZIP: {save_path}", flush=True)
                    pipeline_result = csv_pipeline.auto_process_vendor_upload(vendor, save_path)
                    response["pipeline"] = {
                        "ok": pipeline_result.get("ok", False),
                        "category": pipeline_result.get("category", ""),
                        "export_rows": pipeline_result.get("export_rows", 0),
                        "stages": pipeline_result.get("stages", []),
                        "categories_processed": pipeline_result.get("categories_processed", {}),
                        "unmatched_rows": pipeline_result.get("unmatched_rows", 0),
                        "error": pipeline_result.get("error"),
                    }
                    cats_processed = pipeline_result.get("categories_processed", {})
                    if pipeline_result.get("ok"):
                        cat_summary = ", ".join(f"{c}: {d.get('export_rows',0)} rows" for c, d in cats_processed.items())
                        print(f"[PIPELINE] Done — {pipeline_result.get('export_rows', 0)} total rows. Categories: {cat_summary}", flush=True)
                        if pipeline_result.get("unmatched_rows", 0) > 0:
                            print(f"[PIPELINE] Warning: {pipeline_result['unmatched_rows']} rows didn't match any category posting", flush=True)
                    else:
                        print(f"[PIPELINE] Failed: {pipeline_result.get('error')}", flush=True)
                except Exception as e:
                    print(f"[PIPELINE] Error: {traceback.format_exc()}", flush=True)
                    response["pipeline"] = {"ok": False, "error": str(e)}

            self.send_json_response(response)

        except Exception as e:
            print(f"[UPLOAD ERROR] {str(e)}", flush=True)
            self.send_json_response(
                {"ok": False, "message": f"Upload failed: {str(e)}"},
                status=500
            )

    def handle_get_uploads(self, vendor):
        """API: GET /api/uploads/<vendor> — list uploaded files for a vendor, grouped by date."""
        vendor_dir = os.path.join(self.UPLOAD_DIR, vendor)
        result = {}
        if os.path.exists(vendor_dir):
            for date_folder in sorted(os.listdir(vendor_dir), reverse=True):
                date_path = os.path.join(vendor_dir, date_folder)
                if os.path.isdir(date_path):
                    files = []
                    for fname in sorted(os.listdir(date_path)):
                        fpath = os.path.join(date_path, fname)
                        if os.path.isfile(fpath):
                            size = os.path.getsize(fpath)
                            files.append({
                                "name": fname,
                                "size": size,
                                "path": f"uploads/{vendor}/{date_folder}/{fname}"
                            })
                    if files:
                        result[date_folder] = files
        self.send_json_response(result)

    # ── CSV/ZIP Processing ─────────────────────────────────────────────

    def handle_peek_upload(self, vendor, body):
        """
        API: POST /api/peek-upload/<vendor>
        Reconciliation-based peek: scans the ZIP, pulls recently closed postings,
        and cross-checks both sides to flag matches, mismatches, and gaps.

        Returns:
          csv_jobs        — what's in the ZIP (titles, counts)
          closed_postings — what the vendor marked closed recently
          reconciliation  — matched pairs + discrepancies (missing from ZIP, unexpected in ZIP, count mismatches)
          assignments     — all recent assignments for manual fallback dropdown
        """
        import zipfile
        import csv

        try:
            payload = json.loads(body.decode("utf-8"))
            rel_path = payload.get("path", "")

            if not rel_path:
                self.send_json_response({"ok": False, "message": "No path provided"}, status=400)
                return

            full_path = os.path.abspath(os.path.join(self.SCRIPT_DIR, rel_path))
            if not full_path.startswith(os.path.abspath(self.SCRIPT_DIR)):
                self.send_json_response({"ok": False, "message": "Invalid path"}, status=403)
                return
            if not os.path.exists(full_path):
                self.send_json_response({"ok": False, "message": "File not found"}, status=404)
                return

            # ── Step 1: Scan the ZIP/CSV to see what's inside ──
            csv_jobs = []
            resume_count = 0

            if full_path.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(full_path, 'r') as zf:
                        all_names = zf.namelist()
                        resume_count = sum(1 for n in all_names
                                           if (n.lower().endswith('.pdf') or n.lower().endswith('.rtf') or n.lower().endswith('.docx'))
                                           and not n.startswith('__MACOSX'))

                        for name in all_names:
                            if not name.lower().endswith('.csv') or name.startswith('__MACOSX'):
                                continue
                            basename = os.path.basename(name).lower()
                            if 'master' in basename or 'candidate' in basename:
                                continue

                            try:
                                raw = zf.read(name).decode('utf-8', errors='replace')
                                if raw.startswith('\ufeff'):
                                    raw = raw[1:]
                                lines = raw.strip().split('\n')
                                reader = csv.DictReader(lines)
                                rows = list(reader)
                                if rows:
                                    clean_headers = {k.strip().lstrip('\ufeff').strip().lower() for k in (rows[0].keys() if rows else [])}
                                    has_assignment_id = 'assignment_id' in clean_headers or 'assignment id' in clean_headers
                                    job_title = rows[0].get('Job Title', '') or rows[0].get('job title', '') or ''
                                    job_title = job_title.strip()
                                    company = rows[0].get('Company', '') or rows[0].get('company', '') or ''
                                    assignment_id = ''
                                    if has_assignment_id:
                                        clean_r = {k.strip().lstrip('\ufeff').strip().lower(): v for k, v in rows[0].items()}
                                        assignment_id = (clean_r.get('assignment_id') or clean_r.get('assignment id') or '').strip()
                                    csv_jobs.append({
                                        "csv_file": os.path.basename(name),
                                        "job_title": job_title,
                                        "company": company.strip(),
                                        "applicant_count": len(rows),
                                        "has_assignment_id": bool(assignment_id),
                                        "assignment_id": assignment_id,
                                    })
                            except:
                                continue

                except zipfile.BadZipFile:
                    self.send_json_response({"ok": False, "message": "Invalid ZIP file"}, status=400)
                    return

            elif full_path.lower().endswith('.csv'):
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        raw = f.read()
                    if raw.startswith('\ufeff'):
                        raw = raw[1:]
                    reader = csv.DictReader(raw.strip().split('\n'))
                    rows = list(reader)
                    if rows:
                        job_title = rows[0].get('Job Title', '') or rows[0].get('job title', '') or ''
                        csv_jobs.append({
                            "csv_file": os.path.basename(full_path),
                            "job_title": job_title.strip(),
                            "company": (rows[0].get('Company', '') or '').strip(),
                            "applicant_count": len(rows),
                            "has_assignment_id": False,
                            "assignment_id": "",
                        })
                except:
                    pass

            # ── Step 2: Get recently closed postings for this vendor ──
            # Scan activity files for the last 14 days for closed entries.
            # Also find "last processed" timestamp to determine the reconciliation window.
            from datetime import timedelta
            closed_postings = []  # all closed entries in the window
            closed_by_id = {}    # id -> closed entry (for matching)

            activity_dir = os.path.join(self.ACTIVITY_DIR, vendor)
            if os.path.exists(activity_dir):
                for fname in sorted(os.listdir(activity_dir), reverse=True):
                    if not fname.endswith('.json'):
                        continue
                    try:
                        fdate = date.fromisoformat(fname.replace('.json', ''))
                        if (date.today() - fdate).days > 14:
                            continue
                    except:
                        continue
                    try:
                        with open(os.path.join(activity_dir, fname), 'r') as f:
                            adata = json.load(f)
                        for c in adata.get("closed", []):
                            cid = c.get("id", "")
                            if cid and cid not in closed_by_id:
                                entry = {
                                    "id": cid,
                                    "title": c.get("title", ""),
                                    "category": c.get("category", ""),
                                    "closed_date": fname.replace('.json', ''),
                                    "applicants_reported": c.get("applicants", 0),
                                    "budget_spent": c.get("budgetSpent", ""),
                                    "posted_date": c.get("postedDate", ""),
                                }
                                closed_postings.append(entry)
                                closed_by_id[cid] = entry
                    except:
                        continue

            # ── Step 3: Get all recent assignments (for UID lookup + dropdown fallback) ──
            assignments = []
            assignment_by_id = {}   # posting id (SFG-0) -> assignment
            assignment_by_uid = {}  # uid -> assignment
            assignments_dir = os.path.join(self.ASSIGNMENTS_DIR, vendor)
            seen_uids = set()
            if os.path.exists(assignments_dir):
                for fname in sorted(os.listdir(assignments_dir), reverse=True):
                    if not fname.endswith('.json'):
                        continue
                    try:
                        fdate = date.fromisoformat(fname.replace('.json', ''))
                        if (date.today() - fdate).days > 30:
                            continue
                    except:
                        continue
                    try:
                        with open(os.path.join(assignments_dir, fname), 'r') as f:
                            data = json.load(f)
                        for a in data.get("assignments", []):
                            uid = a.get("uid", "")
                            aid = a.get("id", "")
                            if uid and uid not in seen_uids:
                                seen_uids.add(uid)
                                entry = {
                                    "uid": uid,
                                    "id": aid,
                                    "title": a.get("title", ""),
                                    "category": a.get("category", ""),
                                    "account": a.get("account", ""),
                                    "budget": a.get("budget", ""),
                                    "close_date": a.get("closeDate", ""),
                                    "status": a.get("status", "active"),
                                    "assigned_date": fname.replace('.json', ''),
                                    "description_snippet": re.sub(r'<[^>]+>', '', a.get("description", ""))[:100],
                                }
                                assignments.append(entry)
                                if aid:
                                    assignment_by_id[aid] = entry
                                assignment_by_uid[uid] = entry
                    except:
                        continue

            # ── Step 4: Reconcile — match CSV jobs ↔ closed postings ──
            runs_data = self._load_runs(vendor)
            title_map = runs_data.get("title_map", {})
            reconciliation = []
            matched_closed_ids = set()
            has_any_assignment_ids = any(cj.get("has_assignment_id") for cj in csv_jobs)

            for cj in csv_jobs:
                csv_title = cj["job_title"]
                csv_count = cj["applicant_count"]
                rec = {
                    "csv_title": csv_title,
                    "csv_count": csv_count,
                    "csv_file": cj["csv_file"],
                    "assignment_uid": "",
                    "assignment_title": "",
                    "closed_id": "",
                    "closed_title": "",
                    "reported_count": None,
                    "count_match": None,       # True/False/None
                    "count_diff": None,         # +/- difference
                    "match_type": "unmatched",  # auto-id, closed-match, title-map, exact, fuzzy, unmatched
                    "match_score": 0,
                    "include": True,
                    "warnings": [],
                }

                # Try matching strategies in priority order:

                # A) Assignment_ID in CSV → find assignment → find its closed entry
                if cj.get("assignment_id"):
                    aid = cj["assignment_id"]
                    if aid in assignment_by_uid:
                        a = assignment_by_uid[aid]
                        rec["assignment_uid"] = aid
                        rec["assignment_title"] = a["title"]
                        rec["match_type"] = "auto-id"
                        rec["match_score"] = 1.0
                        # Find closed entry by the assignment's posting id
                        posting_id = a.get("id", "")
                        if posting_id in closed_by_id:
                            ce = closed_by_id[posting_id]
                            rec["closed_id"] = posting_id
                            rec["closed_title"] = ce["title"]
                            rec["reported_count"] = ce["applicants_reported"]
                            matched_closed_ids.add(posting_id)
                        else:
                            rec["warnings"].append("Assignment found but not marked closed yet")
                        reconciliation.append(rec)
                        continue

                # B) Match by closed posting title (fuzzy) → get assignment UID from id
                best_closed = None
                best_closed_score = 0
                for cid, ce in closed_by_id.items():
                    if cid in matched_closed_ids:
                        continue
                    # Exact title match
                    if ce["title"].lower().strip() == csv_title.lower().strip():
                        best_closed = ce
                        best_closed_score = 1.0
                        break
                    # Fuzzy
                    _, score = self._fuzzy_title_match(csv_title, [ce["title"]])
                    if score > best_closed_score:
                        best_closed_score = score
                        best_closed = ce

                if best_closed and best_closed_score >= 0.6:
                    cid = best_closed["id"]
                    rec["closed_id"] = cid
                    rec["closed_title"] = best_closed["title"]
                    rec["reported_count"] = best_closed["applicants_reported"]
                    rec["match_type"] = "closed-match" if best_closed_score >= 0.95 else "closed-fuzzy"
                    rec["match_score"] = round(best_closed_score, 3)
                    matched_closed_ids.add(cid)
                    # Look up assignment UID via the posting id
                    if cid in assignment_by_id:
                        rec["assignment_uid"] = assignment_by_id[cid]["uid"]
                        rec["assignment_title"] = assignment_by_id[cid]["title"]
                    reconciliation.append(rec)
                    continue

                # C) Title map (remembered from previous confirmations)
                if csv_title in title_map:
                    uid = title_map[csv_title]
                    if uid in assignment_by_uid:
                        a = assignment_by_uid[uid]
                        rec["assignment_uid"] = uid
                        rec["assignment_title"] = a["title"]
                        rec["match_type"] = "remembered"
                        rec["match_score"] = 1.0
                        pid = a.get("id", "")
                        if pid in closed_by_id:
                            ce = closed_by_id[pid]
                            rec["closed_id"] = pid
                            rec["closed_title"] = ce["title"]
                            rec["reported_count"] = ce["applicants_reported"]
                            matched_closed_ids.add(pid)
                        reconciliation.append(rec)
                        continue

                # D) Fuzzy match against assignment titles
                all_assignment_titles = {a["title"]: a for a in assignments}
                best_title, score = self._fuzzy_title_match(csv_title, list(all_assignment_titles.keys()))
                if best_title and score >= 0.6:
                    a = all_assignment_titles[best_title]
                    rec["assignment_uid"] = a["uid"]
                    rec["assignment_title"] = best_title
                    rec["match_type"] = "fuzzy"
                    rec["match_score"] = round(score, 3)
                    pid = a.get("id", "")
                    if pid in closed_by_id:
                        ce = closed_by_id[pid]
                        rec["closed_id"] = pid
                        rec["closed_title"] = ce["title"]
                        rec["reported_count"] = ce["applicants_reported"]
                        matched_closed_ids.add(pid)

                reconciliation.append(rec)

            # ── Step 5: Check for applicant count mismatches ──
            for rec in reconciliation:
                if rec["reported_count"] is not None and rec["csv_count"] > 0:
                    try:
                        reported = int(rec["reported_count"])
                        actual = rec["csv_count"]
                        rec["count_diff"] = actual - reported
                        # Allow small tolerance (±2) for timing/edge cases
                        if abs(actual - reported) <= 2:
                            rec["count_match"] = True
                        else:
                            rec["count_match"] = False
                            if actual > reported:
                                rec["warnings"].append(f"CSV has {actual} applicants but vendor reported {reported} (+{actual - reported})")
                            else:
                                rec["warnings"].append(f"CSV has {actual} applicants but vendor reported {reported} ({actual - reported})")
                    except:
                        pass

            # ── Step 6: Flag closed postings NOT found in the ZIP ──
            missing_from_zip = []
            for cid, ce in closed_by_id.items():
                if cid not in matched_closed_ids:
                    missing = {
                        "id": cid,
                        "title": ce["title"],
                        "category": ce.get("category", ""),
                        "closed_date": ce.get("closed_date", ""),
                        "applicants_reported": ce.get("applicants_reported", 0),
                    }
                    # Try to find the assignment UID
                    if cid in assignment_by_id:
                        missing["assignment_uid"] = assignment_by_id[cid]["uid"]
                    missing_from_zip.append(missing)

            self.send_json_response({
                "ok": True,
                "csv_jobs": csv_jobs,
                "resume_count": resume_count,
                "closed_postings": closed_postings,
                "reconciliation": reconciliation,
                "missing_from_zip": missing_from_zip,
                "assignments": assignments,
                "has_assignment_ids": has_any_assignment_ids,
                "file": os.path.basename(full_path),
                "summary": {
                    "csv_count": len(csv_jobs),
                    "closed_count": len(closed_postings),
                    "matched": sum(1 for r in reconciliation if r["match_type"] != "unmatched"),
                    "unmatched": sum(1 for r in reconciliation if r["match_type"] == "unmatched"),
                    "missing_from_zip": len(missing_from_zip),
                    "count_mismatches": sum(1 for r in reconciliation if r["count_match"] is False),
                },
            })

        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"[PEEK ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": str(e)}, status=500)

    def handle_process_upload(self, vendor, body):
        """
        API: POST /api/process-upload/<vendor>
        Scan a previously uploaded ZIP for CSVs, extract applicant data.
        Accepts: { path: "uploads/vendor/date/resumes_file.zip" }
        Returns: { ok, applicants: [...], summary: {...} }
        """
        import zipfile
        import csv
        from io import TextIOWrapper

        try:
            payload = json.loads(body.decode("utf-8"))
            rel_path = payload.get("path", "")

            if not rel_path:
                self.send_json_response({"ok": False, "message": "No path provided"}, status=400)
                return

            full_path = os.path.abspath(os.path.join(self.SCRIPT_DIR, rel_path))

            # Security check
            if not full_path.startswith(os.path.abspath(self.SCRIPT_DIR)):
                self.send_json_response({"ok": False, "message": "Invalid path"}, status=403)
                return

            if not os.path.exists(full_path):
                self.send_json_response({"ok": False, "message": "File not found"}, status=404)
                return

            applicants = []
            by_job = {}  # job_title -> [applicants]
            csv_files_found = 0
            resume_count = 0
            errors = []
            master_csv = None  # Track the master/candidate CSV separately

            if full_path.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(full_path, 'r') as zf:
                        all_names = zf.namelist()

                        # Count resumes
                        resume_count = sum(1 for n in all_names
                                           if (n.lower().endswith('.pdf') or n.lower().endswith('.rtf') or n.lower().endswith('.docx'))
                                           and not n.startswith('__MACOSX'))

                        # Process CSVs — skip master/candidate CSV on first pass (process per-job CSVs first)
                        csv_names = [n for n in all_names if n.lower().endswith('.csv') and not n.startswith('__MACOSX')]

                        for name in csv_names:
                            csv_files_found += 1
                            basename = os.path.basename(name).lower()
                            # Detect master/candidate CSV
                            if 'master' in basename or 'candidate' in basename or 'all_candidate' in basename:
                                master_csv = name
                                continue  # Process separately

                            try:
                                raw = zf.read(name).decode('utf-8', errors='replace')
                                # Remove BOM
                                if raw.startswith('\ufeff'):
                                    raw = raw[1:]
                                reader = csv.DictReader(raw.splitlines())
                                for row in reader:
                                    applicant = self._normalize_applicant_row(row, name)
                                    if applicant:
                                        applicants.append(applicant)
                                        jt = applicant.get("job_title", "Unknown")
                                        if jt not in by_job:
                                            by_job[jt] = []
                                        by_job[jt].append(applicant)
                            except Exception as e:
                                errors.append(f"Error reading {name}: {str(e)}")

                        # If no per-job CSVs found, fall back to master CSV
                        if not applicants and master_csv:
                            try:
                                raw = zf.read(master_csv).decode('utf-8', errors='replace')
                                if raw.startswith('\ufeff'):
                                    raw = raw[1:]
                                reader = csv.DictReader(raw.splitlines())
                                for row in reader:
                                    applicant = self._normalize_applicant_row(row, master_csv)
                                    if applicant:
                                        applicants.append(applicant)
                                        jt = applicant.get("job_title", "Unknown")
                                        if jt not in by_job:
                                            by_job[jt] = []
                                        by_job[jt].append(applicant)
                            except Exception as e:
                                errors.append(f"Error reading master CSV: {str(e)}")

                except zipfile.BadZipFile:
                    self.send_json_response({"ok": False, "message": "Invalid ZIP file"}, status=400)
                    return

            elif full_path.lower().endswith('.csv'):
                csv_files_found = 1
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            applicant = self._normalize_applicant_row(row)
                            if applicant:
                                applicants.append(applicant)
                except Exception as e:
                    errors.append(f"Error reading CSV: {str(e)}")
            else:
                self.send_json_response({"ok": False, "message": "Unsupported file type. Use .zip or .csv"}, status=400)
                return

            # ── Deduplication & International Flagging ──
            # CSVs contain duplicates when a candidate applied to multiple jobs.
            # We keep the full list (all_applications) for per-job counts,
            # but also build a deduped unique list keyed by email (or name if no email).
            # International = location not in a US state.

            US_STATES = {
                'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
                'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
                'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
                'VA','WA','WV','WI','WY','DC',
                'alabama','alaska','arizona','arkansas','california','colorado','connecticut',
                'delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa',
                'kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan',
                'minnesota','mississippi','missouri','montana','nebraska','nevada',
                'new hampshire','new jersey','new mexico','new york','north carolina',
                'north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island',
                'south carolina','south dakota','tennessee','texas','utah','vermont',
                'virginia','washington','west virginia','wisconsin','wyoming',
                'district of columbia',
            }

            def _is_us_location(loc):
                """Check if location string looks like a US location."""
                if not loc:
                    return False
                parts = [p.strip() for p in loc.replace(',', ' ').split()]
                for p in parts:
                    if p.upper() in US_STATES or p.lower() in US_STATES:
                        return True
                # Also check the last part after comma (e.g. "Harrison Township, MI")
                comma_parts = [p.strip() for p in loc.split(',')]
                if len(comma_parts) >= 2:
                    state_part = comma_parts[-1].strip().split()[0] if comma_parts[-1].strip() else ''
                    if state_part.upper() in US_STATES or state_part.lower() in US_STATES:
                        return True
                return False

            total_applications = len(applicants)

            # Flag international applicants
            for a in applicants:
                a['is_us'] = _is_us_location(a.get('location', ''))
                a['is_international'] = not a['is_us']

            # Dedupe: key by lowercase email (or name if no email)
            seen = {}
            unique_applicants = []
            for a in applicants:
                key = (a.get('email') or '').lower().strip()
                if not key:
                    key = (a.get('name') or '').lower().strip()
                if not key:
                    continue

                if key not in seen:
                    # First time seeing this person — create their entry
                    deduped = dict(a)
                    deduped['jobs_applied'] = [a.get('job_title', '')]
                    deduped['application_count'] = 1
                    seen[key] = deduped
                    unique_applicants.append(deduped)
                else:
                    # Seen before — just add this job to their list
                    existing = seen[key]
                    jt = a.get('job_title', '')
                    if jt and jt not in existing['jobs_applied']:
                        existing['jobs_applied'].append(jt)
                    existing['application_count'] = existing.get('application_count', 1) + 1

            us_unique = [a for a in unique_applicants if a.get('is_us')]
            intl_unique = [a for a in unique_applicants if a.get('is_international')]

            # Build job summary (from full non-deduped list for accurate per-job counts)
            job_summary = []
            for jt, apps in sorted(by_job.items(), key=lambda x: -len(x[1])):
                sponsored = sum(1 for a in apps if a.get("source", "").lower() == "sponsored")
                organic = len(apps) - sponsored
                us_count = sum(1 for a in apps if _is_us_location(a.get('location', '')))
                intl_count = len(apps) - us_count
                job_summary.append({
                    "job_title": jt,
                    "count": len(apps),
                    "sponsored": sponsored,
                    "organic": organic,
                    "us": us_count,
                    "international": intl_count,
                })

            # Save processed data
            processed_dir = os.path.join(self.SCRIPT_DIR, "processed", vendor)
            os.makedirs(processed_dir, exist_ok=True)
            timestamp = self._timestamp().replace(":", "-")
            processed_file = os.path.join(processed_dir, f"applicants_{timestamp}.json")
            save_data = {
                "source": rel_path,
                "processed_at": self._timestamp(),
                "applicants": unique_applicants,
                "by_job": job_summary,
                "resume_count": resume_count,
                "stats": {
                    "total_applications": total_applications,
                    "unique_applicants": len(unique_applicants),
                    "us_applicants": len(us_unique),
                    "international_applicants": len(intl_unique),
                },
            }
            with open(processed_file, "w") as f:
                json.dump(save_data, f, indent=2)

            print(f"[PROCESS] {vendor}: {total_applications} applications → {len(unique_applicants)} unique ({len(us_unique)} US, {len(intl_unique)} intl), {resume_count} resumes, {csv_files_found} CSV(s)", flush=True)

            # ── Auto-link to Posting Runs ──
            title_matches = {}
            try:
                title_matches = self._link_candidates_to_runs(vendor, applicants, by_job)
                match_summary = []
                for csv_t, m in title_matches.items():
                    match_summary.append({
                        "csv_title": csv_t,
                        "matched_to": m["posting_title"],
                        "match_type": m["match_type"],
                        "match_score": m["match_score"],
                        "run_id": m["run_id"],
                    })
                print(f"[RUNS] {vendor}: linked {len(title_matches)} CSV titles to posting runs", flush=True)
            except Exception as e:
                print(f"[RUNS WARNING] Could not link to runs: {str(e)}", flush=True)
                match_summary = []

            self.send_json_response({
                "ok": True,
                "applicants": unique_applicants,
                "by_job": job_summary,
                "title_matches": match_summary,
                "summary": {
                    "total_applications": total_applications,
                    "unique_applicants": len(unique_applicants),
                    "us_applicants": len(us_unique),
                    "international_applicants": len(intl_unique),
                    "csv_files": csv_files_found,
                    "resume_count": resume_count,
                    "source": os.path.basename(full_path),
                    "errors": errors,
                    "runs_linked": len(title_matches),
                }
            })

        except json.JSONDecodeError:
            self.send_json_response({"ok": False, "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"[PROCESS ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": f"Error: {str(e)}"}, status=500)

    def _normalize_applicant_row(self, row, csv_name=""):
        """
        Normalize a CSV row from SID/Indeed into a standard applicant dict.
        SID CSVs have: Name, Email, Phone, Location, Job Title, Company, Job Location, Date Applied, Source, Resume File, Notes
        Master CSV has: Name, Email, Phone, Location, Resume File, Applied To, Number of Applications
        Also handles other Indeed-style column names.
        """
        # Strip BOM and whitespace from keys
        clean_row = {}
        for k, v in row.items():
            key = k.strip().lstrip('\ufeff').strip()
            clean_row[key] = v.strip() if isinstance(v, str) else (v or '')
        lower_row = {k.lower(): v for k, v in clean_row.items()}

        # Name
        name = (lower_row.get('name') or lower_row.get('candidate name') or
                lower_row.get('applicant name') or lower_row.get('full name') or '').strip()
        if not name:
            fn = (lower_row.get('first name') or '').strip()
            ln = (lower_row.get('last name') or '').strip()
            name = f"{fn} {ln}".strip()
        if not name:
            return None

        # Email
        email = (lower_row.get('email') or lower_row.get('email address') or '').strip()

        # Phone
        phone = (lower_row.get('phone') or lower_row.get('phone number') or
                 lower_row.get('mobile') or '').strip()

        # Location
        location = (lower_row.get('location') or '').strip()
        if not location:
            city = (lower_row.get('city') or '').strip()
            state = (lower_row.get('state') or '').strip()
            location = f"{city}, {state}".strip(', ')

        # Apply date
        apply_date = (lower_row.get('date applied') or lower_row.get('apply date') or
                      lower_row.get('application date') or lower_row.get('date') or '').strip()

        # Job title
        job_title = (lower_row.get('job title') or lower_row.get('applied to') or
                     lower_row.get('position') or lower_row.get('job') or '').strip()

        # Source (Sponsored/Organic)
        source = (lower_row.get('source') or '').strip()

        # Company
        company = (lower_row.get('company') or '').strip()

        # Job Location (distinct from applicant location)
        job_location = (lower_row.get('job location') or '').strip()

        # Resume file reference
        resume_file = (lower_row.get('resume file') or '').strip()

        # Notes
        notes = (lower_row.get('notes') or '').strip()

        # Assignment ID (added by SID for automatic linking)
        assignment_id = (lower_row.get('assignment_id') or lower_row.get('assignment id') or
                         lower_row.get('run_id') or lower_row.get('run id') or '').strip()

        # Number of applications (from master CSV)
        num_applications = 0
        try:
            num_applications = int(lower_row.get('number of applications') or 0)
        except:
            pass

        result = {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
            "apply_date": apply_date,
            "job_title": job_title,
            "source": source,
            "company": company,
            "job_location": job_location,
            "resume_file": resume_file,
        }
        if notes:
            result["notes"] = notes
        if num_applications > 0:
            result["num_applications"] = num_applications
        if assignment_id:
            result["assignment_id"] = assignment_id

        return result

    def handle_get_processed(self, vendor):
        """API: GET /api/processed/<vendor> — list processed applicant files."""
        processed_dir = os.path.join(self.SCRIPT_DIR, "processed", vendor)
        result = []
        if os.path.exists(processed_dir):
            for fname in sorted(os.listdir(processed_dir), reverse=True):
                if fname.endswith('.json'):
                    fpath = os.path.join(processed_dir, fname)
                    try:
                        with open(fpath, 'r') as f:
                            data = json.load(f)
                        result.append({
                            "file": fname,
                            "source": data.get("source", ""),
                            "processed_at": data.get("processed_at", ""),
                            "count": len(data.get("applicants", [])),
                        })
                    except:
                        pass
        self.send_json_response(result)

    def handle_get_processed_file(self, vendor, filename):
        """API: GET /api/processed/<vendor>/<filename> — get processed applicant data."""
        processed_dir = os.path.join(self.SCRIPT_DIR, "processed", vendor)
        fpath = os.path.join(processed_dir, filename)
        fpath = os.path.abspath(fpath)

        if not fpath.startswith(os.path.abspath(processed_dir)):
            self.send_json_response({"ok": False, "message": "Invalid path"}, status=403)
            return

        if os.path.exists(fpath):
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                self.send_json_response(data)
            except:
                self.send_json_response({"ok": False, "message": "Error reading file"}, status=500)
        else:
            self.send_json_response({"ok": False, "message": "File not found"}, status=404)

    # ── Posting Runs (Links Assignments ↔ CSVs ↔ Activity) ─────────────

    RUNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posting_runs")

    def _get_runs_file(self, vendor):
        """Get path to a vendor's posting runs file."""
        os.makedirs(self.RUNS_DIR, exist_ok=True)
        return os.path.join(self.RUNS_DIR, f"{vendor}.json")

    def _load_runs(self, vendor):
        """Load all posting runs for a vendor."""
        fpath = self._get_runs_file(vendor)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"vendor": vendor, "runs": [], "title_map": {}}

    def _save_runs(self, vendor, data):
        """Save posting runs for a vendor."""
        fpath = self._get_runs_file(vendor)
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)

    def _fuzzy_title_match(self, csv_title, candidates, threshold=0.6):
        """
        Match a CSV job title to the best assignment title.
        Uses token-based similarity (Jaccard on lowercased words).
        Returns (best_match_title, score) or (None, 0).
        """
        if not csv_title or not candidates:
            return None, 0

        def tokenize(s):
            return set(re.sub(r'[^a-z0-9\s]', '', s.lower()).split())

        csv_tokens = tokenize(csv_title)
        if not csv_tokens:
            return None, 0

        best_match = None
        best_score = 0

        for candidate in candidates:
            cand_tokens = tokenize(candidate)
            if not cand_tokens:
                continue
            intersection = csv_tokens & cand_tokens
            union = csv_tokens | cand_tokens
            score = len(intersection) / len(union) if union else 0

            # Bonus: if one is a substring of the other
            if csv_title.lower() in candidate.lower() or candidate.lower() in csv_title.lower():
                score = max(score, 0.85)

            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= threshold:
            return best_match, best_score
        return None, 0

    def _create_or_update_run(self, vendor, assignment_uid, assignment_data, csv_job_title=None):
        """
        Create or update a posting run. A run represents one lifecycle of a posting:
        assigned → posted → collecting applicants → closed.

        Run structure:
        {
            "run_id": "FBSPL-SFG-0-1774713897788-run-1",
            "assignment_uid": "FBSPL-SFG-0-1774713897788",
            "posting_title": "Insurance Agent",
            "csv_job_titles": ["Insurance Agent - Remote", ...],  # matched CSV titles
            "category": "SFG",
            "account": "indeed-inr",
            "budget": "₹460/day, ₹920 max",
            "assigned_date": "2026-03-28",
            "close_date": "2026-03-30",
            "status": "active",  # active, posted, closed
            "description_hash": "abc123",  # to detect JD changes
            "description_snippet": "This role focuses on...",
            "candidates_linked": 87,
            "candidates_us": 72,
            "candidates_intl": 15,
            "budget_spent_usd": 4.56,
            "applicants_from_activity": 87,
            "cpa_usd": 0.052,
            "sources": {"Sponsored": 45, "Organic": 42},
            "days_active": 5,
            "closed_at": null,
            "candidate_ids": ["email1@...", "email2@..."]
        }
        """
        import hashlib
        runs_data = self._load_runs(vendor)
        runs = runs_data.get("runs", [])

        # Check if a run already exists for this assignment
        existing = None
        for r in runs:
            if r.get("assignment_uid") == assignment_uid:
                existing = r
                break

        desc = assignment_data.get("description", "")
        desc_hash = hashlib.md5(desc.encode()).hexdigest()[:12] if desc else ""
        desc_snippet = re.sub(r'<[^>]+>', '', desc)[:120] if desc else ""

        if existing:
            # Update existing run
            existing["posting_title"] = assignment_data.get("title", existing.get("posting_title", ""))
            existing["category"] = assignment_data.get("category", existing.get("category", ""))
            existing["account"] = assignment_data.get("account", existing.get("account", ""))
            existing["budget"] = assignment_data.get("budget", existing.get("budget", ""))
            existing["close_date"] = assignment_data.get("closeDate", existing.get("close_date", ""))
            existing["description_hash"] = desc_hash
            existing["description_snippet"] = desc_snippet
            if csv_job_title and csv_job_title not in existing.get("csv_job_titles", []):
                existing.setdefault("csv_job_titles", []).append(csv_job_title)
            return existing
        else:
            # Create new run
            run_count = sum(1 for r in runs if r.get("assignment_uid", "").startswith(assignment_uid.rsplit("-run-", 1)[0]))
            new_run = {
                "run_id": f"{assignment_uid}-run-{run_count + 1}",
                "assignment_uid": assignment_uid,
                "posting_title": assignment_data.get("title", "Unknown"),
                "csv_job_titles": [csv_job_title] if csv_job_title else [],
                "category": assignment_data.get("category", ""),
                "account": assignment_data.get("account", ""),
                "budget": assignment_data.get("budget", ""),
                "assigned_date": assignment_data.get("assignedAt", "")[:10] if assignment_data.get("assignedAt") else "",
                "close_date": assignment_data.get("closeDate", ""),
                "status": assignment_data.get("status", "active"),
                "description_hash": desc_hash,
                "description_snippet": desc_snippet,
                "candidates_linked": 0,
                "candidates_us": 0,
                "candidates_intl": 0,
                "budget_spent_usd": 0.0,
                "applicants_from_activity": 0,
                "cpa_usd": None,
                "sources": {},
                "days_active": 0,
                "closed_at": None,
                "candidate_ids": [],
            }
            runs.append(new_run)
            runs_data["runs"] = runs
            self._save_runs(vendor, runs_data)
            return new_run

    def _link_candidates_to_runs(self, vendor, applicants, by_job):
        """
        After processing a CSV, link applicants to posting runs.
        Priority order:
          0. Assignment_ID column (from SID CSV) — instant, guaranteed link
          1. Manual title_map overrides
          2. Exact title match
          3. Fuzzy title match
          4. Unmatched (create standalone run)
        Returns: { csv_title: { run_id, posting_title, match_score, match_type } }
        """
        runs_data = self._load_runs(vendor)
        runs = runs_data.get("runs", [])
        title_map = runs_data.get("title_map", {})  # manual overrides: csv_title -> assignment_uid

        # Collect all known posting titles from runs
        run_by_title = {}
        run_by_uid = {}
        for r in runs:
            run_by_uid[r["assignment_uid"]] = r
            pt = r.get("posting_title", "")
            if pt not in run_by_title:
                run_by_title[pt] = r

        # Also scan recent assignments (last 30 days) for titles not yet in runs
        from datetime import timedelta
        assignment_titles = {}
        assignment_by_uid = {}
        assignments_dir = os.path.join(self.ASSIGNMENTS_DIR, vendor)
        if os.path.exists(assignments_dir):
            for fname in sorted(os.listdir(assignments_dir), reverse=True)[:30]:
                if not fname.endswith('.json'):
                    continue
                try:
                    with open(os.path.join(assignments_dir, fname), 'r') as f:
                        adata = json.load(f)
                    for a in adata.get("assignments", []):
                        uid = a.get("uid", "")
                        title = a.get("title", "")
                        if uid and title:
                            assignment_titles[title] = a
                            assignment_by_uid[uid] = a
                            # Auto-create run if not exists
                            if uid not in run_by_uid:
                                new_run = self._create_or_update_run(vendor, uid, a)
                                run_by_uid[uid] = new_run
                                if title not in run_by_title:
                                    run_by_title[title] = new_run
                except:
                    continue

        all_posting_titles = list(run_by_title.keys()) + [t for t in assignment_titles.keys() if t not in run_by_title]
        matches = {}

        # ── Step 0: Check for Assignment_ID column (auto-link) ──
        # If applicants have assignment_id set, group by (csv_title, assignment_id) and link directly
        id_linked_titles = set()
        for a in applicants:
            aid = a.get("assignment_id", "").strip()
            csv_title = a.get("job_title", "").strip()
            if not aid or not csv_title or csv_title in id_linked_titles:
                continue

            # Find or create the run for this assignment UID
            if aid in run_by_uid:
                run = run_by_uid[aid]
            elif aid in assignment_by_uid:
                run = self._create_or_update_run(vendor, aid, assignment_by_uid[aid], csv_title)
                run_by_uid[aid] = run
            else:
                # Assignment UID not found in our records — still link it, create a run
                run = self._create_or_update_run(vendor, aid, {
                    "title": csv_title, "status": "active"
                }, csv_title)
                run_by_uid[aid] = run

            matches[csv_title] = {
                "run_id": run["run_id"],
                "posting_title": run.get("posting_title", csv_title),
                "assignment_uid": aid,
                "match_score": 1.0,
                "match_type": "auto-id",
            }
            # Also save to title_map for future reference
            runs_data.setdefault("title_map", {})[csv_title] = aid
            id_linked_titles.add(csv_title)
            print(f"[RUNS] Auto-linked '{csv_title}' via Assignment_ID → {aid}", flush=True)

        # For remaining CSV titles, fall through to title-based matching
        for csv_title in set(a.get("job_title", "") for a in applicants if a.get("job_title")):
            if not csv_title or csv_title in id_linked_titles:
                continue

            # 1. Check manual override map
            if csv_title in title_map:
                uid = title_map[csv_title]
                if uid in run_by_uid:
                    run = run_by_uid[uid]
                    matches[csv_title] = {
                        "run_id": run["run_id"],
                        "posting_title": run["posting_title"],
                        "assignment_uid": uid,
                        "match_score": 1.0,
                        "match_type": "manual",
                    }
                    self._create_or_update_run(vendor, uid, assignment_titles.get(run["posting_title"], {}), csv_title)
                    continue

            # 2. Exact match
            if csv_title in run_by_title:
                run = run_by_title[csv_title]
                matches[csv_title] = {
                    "run_id": run["run_id"],
                    "posting_title": run["posting_title"],
                    "assignment_uid": run["assignment_uid"],
                    "match_score": 1.0,
                    "match_type": "exact",
                }
                self._create_or_update_run(vendor, run["assignment_uid"], assignment_titles.get(csv_title, {}), csv_title)
                continue

            # 3. Fuzzy match
            best_title, score = self._fuzzy_title_match(csv_title, all_posting_titles)
            if best_title:
                run = run_by_title.get(best_title)
                if not run and best_title in assignment_titles:
                    a = assignment_titles[best_title]
                    run = self._create_or_update_run(vendor, a.get("uid", ""), a, csv_title)
                    run_by_uid[a.get("uid", "")] = run
                    run_by_title[best_title] = run

                if run:
                    matches[csv_title] = {
                        "run_id": run["run_id"],
                        "posting_title": run["posting_title"],
                        "assignment_uid": run["assignment_uid"],
                        "match_score": round(score, 3),
                        "match_type": "fuzzy",
                    }
                    self._create_or_update_run(vendor, run["assignment_uid"], assignment_titles.get(best_title, {}), csv_title)
                    continue

            # 4. Unmatched — create a standalone run
            standalone_uid = f"csv-{re.sub(r'[^a-zA-Z0-9]', '-', csv_title)[:40]}"
            standalone_run = self._create_or_update_run(vendor, standalone_uid, {
                "title": csv_title, "category": "Unmatched", "status": "csv-only"
            }, csv_title)
            run_by_uid[standalone_uid] = standalone_run
            matches[csv_title] = {
                "run_id": standalone_run["run_id"],
                "posting_title": csv_title,
                "assignment_uid": standalone_uid,
                "match_score": 0,
                "match_type": "unmatched",
            }

        # Now update run stats with linked candidates
        for csv_title, match in matches.items():
            run_id = match["run_id"]
            run = next((r for r in runs_data["runs"] if r["run_id"] == run_id), None)
            if not run:
                continue

            title_applicants = [a for a in applicants
                                if a.get("job_title") == csv_title or
                                (a.get("jobs_applied") and csv_title in a["jobs_applied"])]

            emails = set()
            us = 0
            intl = 0
            sources = {}
            for a in title_applicants:
                email = (a.get("email") or a.get("name", "")).lower()
                if email not in emails:
                    emails.add(email)
                    if a.get("is_us"):
                        us += 1
                    else:
                        intl += 1
                src = a.get("source", "Unknown")
                sources[src] = sources.get(src, 0) + 1

            run["candidates_linked"] = len(emails)
            run["candidates_us"] = us
            run["candidates_intl"] = intl
            run["sources"] = sources
            # Merge candidate IDs (don't replace, accumulate)
            existing_ids = set(run.get("candidate_ids", []))
            existing_ids.update(emails)
            run["candidate_ids"] = list(existing_ids)

        # Also pull in activity close data for spend/CPA
        vendor_activity_dir = os.path.join(self.ACTIVITY_DIR, vendor)
        if os.path.exists(vendor_activity_dir):
            for fname in os.listdir(vendor_activity_dir):
                if not fname.endswith('.json'):
                    continue
                try:
                    with open(os.path.join(vendor_activity_dir, fname), 'r') as f:
                        adata = json.load(f)
                    for closed in adata.get("closed", []):
                        closed_title = closed.get("title", "")
                        # Try to match to a run
                        for run in runs_data["runs"]:
                            if (closed_title == run["posting_title"] or
                                closed_title in run.get("csv_job_titles", [])):
                                spend, sym = self._parse_budget_to_usd(closed.get("budgetSpent", 0))
                                run["budget_spent_usd"] = round(run.get("budget_spent_usd", 0) + spend, 2)
                                try:
                                    apps = int(closed.get("applicants", 0))
                                    run["applicants_from_activity"] = run.get("applicants_from_activity", 0) + apps
                                except:
                                    pass
                                if run["applicants_from_activity"] > 0:
                                    run["cpa_usd"] = round(run["budget_spent_usd"] / run["applicants_from_activity"], 4)
                                if closed.get("closedDate"):
                                    run["closed_at"] = closed["closedDate"]
                                    run["status"] = "closed"
                                break
                except:
                    continue

        self._save_runs(vendor, runs_data)
        return matches

    def handle_get_runs(self, vendor):
        """API: GET /api/runs/<vendor> — get all posting runs for a vendor."""
        data = self._load_runs(vendor)
        # Sort runs: active first, then by assigned_date desc
        runs = data.get("runs", [])
        runs.sort(key=lambda r: (
            0 if r.get("status") == "active" else (1 if r.get("status") == "posted" else 2),
            r.get("assigned_date", "") or "0000",
        ), reverse=False)
        runs.sort(key=lambda r: r.get("assigned_date", ""), reverse=True)

        # Compute summary stats
        total_runs = len(runs)
        total_candidates = sum(r.get("candidates_linked", 0) for r in runs)
        total_spend = sum(r.get("budget_spent_usd", 0) for r in runs)
        total_applicants = sum(r.get("applicants_from_activity", 0) for r in runs)
        avg_cpa = round(total_spend / total_applicants, 4) if total_applicants > 0 else None

        self.send_json_response({
            "vendor": vendor,
            "runs": runs,
            "title_map": data.get("title_map", {}),
            "summary": {
                "total_runs": total_runs,
                "active_runs": sum(1 for r in runs if r.get("status") == "active"),
                "closed_runs": sum(1 for r in runs if r.get("status") == "closed"),
                "total_candidates": total_candidates,
                "total_spend_usd": round(total_spend, 2),
                "total_applicants": total_applicants,
                "avg_cpa": avg_cpa,
            }
        })

    def handle_post_confirm_links(self, vendor, body):
        """
        API: POST /api/runs/<vendor>/confirm
        User-confirmed links between CSV job titles and assignments.
        Called AFTER peek, BEFORE full processing.
        Accepts: {
            path: "uploads/vendor/date/file.zip",
            links: [ { csv_title, assignment_uid, include } ]
        }
        Saves the confirmed title mappings, then triggers full processing with linking.
        """
        try:
            payload = json.loads(body.decode("utf-8"))
            links = payload.get("links", [])
            file_path = payload.get("path", "")

            if not file_path:
                self.send_json_response({"ok": False, "message": "No file path"}, status=400)
                return

            # Save confirmed mappings to title_map for this and future use
            runs_data = self._load_runs(vendor)
            confirmed_titles = {}  # csv_title -> assignment_uid
            excluded_titles = set()

            for link in links:
                csv_title = link.get("csv_title", "").strip()
                assignment_uid = link.get("assignment_uid", "").strip()
                include = link.get("include", True)

                if not csv_title:
                    continue

                if not include:
                    excluded_titles.add(csv_title)
                    continue

                if assignment_uid:
                    runs_data.setdefault("title_map", {})[csv_title] = assignment_uid
                    confirmed_titles[csv_title] = assignment_uid

            self._save_runs(vendor, runs_data)

            # Now trigger the full processing — pass confirmed links + exclusions
            # We call handle_process_upload internally with extra context
            process_body = json.dumps({
                "path": file_path,
                "_confirmed_links": confirmed_titles,
                "_excluded_titles": list(excluded_titles),
            }).encode("utf-8")
            self.handle_process_upload(vendor, process_body)

        except Exception as e:
            print(f"[CONFIRM ERROR] {str(e)}", flush=True)
            self.send_json_response({"ok": False, "message": str(e)}, status=500)

    def handle_post_title_map(self, vendor, body):
        """
        API: POST /api/runs/<vendor>/map
        Manually map a CSV job title to an assignment UID.
        Accepts: { csv_title: "...", assignment_uid: "..." }
        """
        try:
            payload = json.loads(body.decode("utf-8"))
            csv_title = payload.get("csv_title", "").strip()
            assignment_uid = payload.get("assignment_uid", "").strip()

            if not csv_title or not assignment_uid:
                self.send_json_response({"ok": False, "message": "Both csv_title and assignment_uid required"}, status=400)
                return

            data = self._load_runs(vendor)
            data.setdefault("title_map", {})[csv_title] = assignment_uid
            self._save_runs(vendor, data)

            print(f"[RUNS] {vendor}: mapped '{csv_title}' → {assignment_uid}", flush=True)
            self.send_json_response({"ok": True, "message": f"Mapped '{csv_title}' to {assignment_uid}"})
        except Exception as e:
            self.send_json_response({"ok": False, "message": str(e)}, status=500)

    # ── Candidate Tracker ──────────────────────────────────────────────

    def handle_get_candidates(self, vendor=None):
        """
        API: GET /api/candidates?vendor=X&period=day|week|month&date=YYYY-MM-DD
        Scans all processed applicant files, builds a master candidate database.
        If vendor is specified, only that vendor. Otherwise all vendors.
        Returns candidates with their full history across vendors/dates/jobs.
        """
        from datetime import timedelta

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        target_vendor = vendor or params.get("vendor", [None])[0]
        period = params.get("period", ["all"])[0]  # day, week, month, all
        target_date = params.get("date", [date.today().isoformat()])[0]

        # Determine date range
        try:
            ref_date = date.fromisoformat(target_date)
        except:
            ref_date = date.today()

        if period == "day":
            start_date = ref_date
            end_date = ref_date
        elif period == "week":
            start_date = ref_date - timedelta(days=ref_date.weekday())  # Monday
            end_date = start_date + timedelta(days=6)
        elif period == "month":
            start_date = ref_date.replace(day=1)
            next_month = (start_date.replace(day=28) + timedelta(days=4))
            end_date = next_month.replace(day=1) - timedelta(days=1)
        else:  # all
            start_date = None
            end_date = None

        processed_base = os.path.join(self.SCRIPT_DIR, "processed")
        candidates = {}  # email -> candidate record

        # Scan processed files
        vendors_to_scan = [target_vendor] if target_vendor else []
        if not vendors_to_scan and os.path.exists(processed_base):
            vendors_to_scan = [d for d in os.listdir(processed_base)
                               if os.path.isdir(os.path.join(processed_base, d))]

        for v in vendors_to_scan:
            vendor_dir = os.path.join(processed_base, v)
            if not os.path.exists(vendor_dir):
                continue

            for fname in os.listdir(vendor_dir):
                if not fname.endswith('.json'):
                    continue
                fpath = os.path.join(vendor_dir, fname)
                try:
                    with open(fpath, 'r') as f:
                        data = json.load(f)
                except:
                    continue

                processed_at = data.get("processed_at", "")
                source_file = data.get("source", "")

                for app in data.get("applicants", []):
                    email = (app.get("email") or "").lower().strip()
                    name = (app.get("name") or "").strip()
                    if not email and not name:
                        continue
                    key = email if email else name.lower()

                    apply_date_str = app.get("apply_date", "")
                    # Filter by date range
                    if start_date and apply_date_str:
                        try:
                            ad = date.fromisoformat(apply_date_str)
                            if ad < start_date or ad > end_date:
                                continue
                        except:
                            pass

                    if key not in candidates:
                        candidates[key] = {
                            "name": name,
                            "email": email,
                            "phone": app.get("phone", ""),
                            "location": app.get("location", ""),
                            "is_us": app.get("is_us", True),
                            "is_international": app.get("is_international", False),
                            "vendors": [],
                            "jobs": [],
                            "dates": [],
                            "sources": [],
                            "total_applications": 0,
                            "history": [],
                        }

                    c = candidates[key]
                    # Update with latest info if better
                    if not c["phone"] and app.get("phone"):
                        c["phone"] = app["phone"]
                    if not c["location"] and app.get("location"):
                        c["location"] = app["location"]

                    # Track history entry
                    jobs_list = app.get("jobs_applied") or [app.get("job_title", "")]
                    for jt in jobs_list:
                        if jt and jt not in c["jobs"]:
                            c["jobs"].append(jt)

                    if v not in c["vendors"]:
                        c["vendors"].append(v)

                    if apply_date_str and apply_date_str not in c["dates"]:
                        c["dates"].append(apply_date_str)

                    src = app.get("source", "")
                    if src and src not in c["sources"]:
                        c["sources"].append(src)

                    c["total_applications"] += app.get("application_count", 1)

                    c["history"].append({
                        "vendor": v,
                        "date": apply_date_str,
                        "jobs": jobs_list,
                        "source": src,
                        "file": source_file,
                    })

        # Convert to list and sort by total applications (most active first)
        candidate_list = sorted(candidates.values(), key=lambda x: -x["total_applications"])

        # Stats
        total = len(candidate_list)
        multi_vendor = sum(1 for c in candidate_list if len(c["vendors"]) > 1)
        multi_job = sum(1 for c in candidate_list if len(c["jobs"]) > 1)
        us_count = sum(1 for c in candidate_list if c["is_us"])
        intl_count = total - us_count

        self.send_json_response({
            "candidates": candidate_list,
            "stats": {
                "total": total,
                "multi_vendor": multi_vendor,
                "multi_job": multi_job,
                "us": us_count,
                "international": intl_count,
            },
            "period": period,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            }
        })

    # ── Analytics ─────────────────────────────────────────────────────

    CURRENCY_TO_USD = {"$": 1.0, "₹": 0.012, "€": 1.08, "£": 1.26, "C$": 0.74, "A$": 0.65, "₱": 0.018, "MX$": 0.058}

    def _parse_budget_to_usd(self, raw):
        """Parse a budget string like '$8' or '₹420' and return USD float."""
        s = str(raw).strip()
        symbol = "$"
        for sym in sorted(self.CURRENCY_TO_USD.keys(), key=len, reverse=True):
            if s.startswith(sym):
                symbol = sym
                s = s[len(sym):]
                break
        try:
            amount = float(s.replace(",", "").replace(" ", ""))
        except (ValueError, TypeError):
            amount = 0.0
        return amount * self.CURRENCY_TO_USD.get(symbol, 1.0), symbol

    def _collect_vendor_analytics(self, vendor):
        """
        Aggregate all activity data for a vendor into analytics-friendly structure.
        Returns: {
            daily: [ { date, posted, closed, applicants, spend_usd, postings_details: [...] } ],
            totals: { applicants, spend_usd, posted, closed, avg_cpa },
            by_posting: [ { title, category, applicants, spend_usd, runs, avg_cpa } ],
            by_category: [ { category, applicants, spend_usd, runs, avg_cpa } ],
            by_account: [ { account, applicants, spend_usd, runs } ],
            spend_by_currency: { USD: x, INR: y }
        }
        """
        vendor_activity_dir = os.path.join(self.ACTIVITY_DIR, vendor)
        daily = {}
        by_posting = {}
        by_category = {}
        by_account = {}
        spend_by_currency = {}
        total_applicants = 0
        total_spend_usd = 0.0
        total_posted = 0
        total_closed = 0

        if not os.path.exists(vendor_activity_dir):
            return {"daily": [], "totals": {}, "by_posting": [], "by_category": [], "by_account": [], "spend_by_currency": {}}

        for filename in sorted(os.listdir(vendor_activity_dir)):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(vendor_activity_dir, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            d = data.get("date", filename.replace(".json", ""))
            day_applicants = 0
            day_spend_usd = 0.0
            day_posted = len(data.get("posted", []))
            day_closed = len(data.get("closed", []))
            day_details = []

            total_posted += day_posted

            for closed in data.get("closed", []):
                title = closed.get("title", "Unknown")
                cat = closed.get("category", "Uncategorized")
                account = closed.get("account", "unknown")
                applicants = 0
                try:
                    applicants = int(closed.get("applicants", 0))
                except (ValueError, TypeError):
                    pass

                spend_usd, sym = self._parse_budget_to_usd(closed.get("budgetSpent", 0))

                # Track by currency
                spend_by_currency[sym] = spend_by_currency.get(sym, 0.0)
                raw_amount = 0.0
                try:
                    raw_s = str(closed.get("budgetSpent", "0")).strip()
                    for s2 in sorted(self.CURRENCY_TO_USD.keys(), key=len, reverse=True):
                        if raw_s.startswith(s2):
                            raw_s = raw_s[len(s2):]
                            break
                    raw_amount = float(raw_s.replace(",", "").replace(" ", ""))
                except:
                    pass
                spend_by_currency[sym] += raw_amount

                day_applicants += applicants
                day_spend_usd += spend_usd
                total_applicants += applicants
                total_spend_usd += spend_usd
                total_closed += 1

                cpa = round(spend_usd / applicants, 4) if applicants > 0 else None
                day_details.append({
                    "title": title, "category": cat, "account": account,
                    "applicants": applicants, "spend_usd": round(spend_usd, 2), "cpa": cpa
                })

                # By posting
                key = f"{cat}||{title}"
                if key not in by_posting:
                    by_posting[key] = {"title": title, "category": cat, "applicants": 0, "spend_usd": 0.0, "runs": 0}
                by_posting[key]["applicants"] += applicants
                by_posting[key]["spend_usd"] += spend_usd
                by_posting[key]["runs"] += 1

                # By category
                if cat not in by_category:
                    by_category[cat] = {"applicants": 0, "spend_usd": 0.0, "runs": 0}
                by_category[cat]["applicants"] += applicants
                by_category[cat]["spend_usd"] += spend_usd
                by_category[cat]["runs"] += 1

                # By account
                if account not in by_account:
                    by_account[account] = {"applicants": 0, "spend_usd": 0.0, "runs": 0}
                by_account[account]["applicants"] += applicants
                by_account[account]["spend_usd"] += spend_usd
                by_account[account]["runs"] += 1

            daily[d] = {
                "date": d, "posted": day_posted, "closed": day_closed,
                "applicants": day_applicants, "spend_usd": round(day_spend_usd, 2),
                "details": day_details
            }

        # Build sorted lists
        daily_list = sorted(daily.values(), key=lambda x: x["date"])

        posting_list = []
        for p in by_posting.values():
            cpa = round(p["spend_usd"] / p["applicants"], 4) if p["applicants"] > 0 else None
            posting_list.append({**p, "spend_usd": round(p["spend_usd"], 2), "avg_cpa": cpa})
        posting_list.sort(key=lambda x: x["applicants"], reverse=True)

        cat_list = []
        for cat, c in by_category.items():
            cpa = round(c["spend_usd"] / c["applicants"], 4) if c["applicants"] > 0 else None
            cat_list.append({"category": cat, **c, "spend_usd": round(c["spend_usd"], 2), "avg_cpa": cpa})
        cat_list.sort(key=lambda x: x["applicants"], reverse=True)

        acct_list = []
        for acct, a in by_account.items():
            acct_list.append({"account": acct, **a, "spend_usd": round(a["spend_usd"], 2)})
        acct_list.sort(key=lambda x: x["spend_usd"], reverse=True)

        avg_cpa = round(total_spend_usd / total_applicants, 4) if total_applicants > 0 else None

        return {
            "daily": daily_list,
            "totals": {
                "applicants": total_applicants,
                "spend_usd": round(total_spend_usd, 2),
                "posted": total_posted,
                "closed": total_closed,
                "avg_cpa": avg_cpa,
            },
            "by_posting": posting_list,
            "by_category": cat_list,
            "by_account": acct_list,
            "spend_by_currency": {k: round(v, 2) for k, v in spend_by_currency.items()},
        }

    def handle_get_analytics(self, vendor):
        """API: GET /api/analytics/<vendor> — full analytics data for a vendor."""
        analytics = self._collect_vendor_analytics(vendor)
        self.send_json_response(analytics)

    def handle_get_analytics_all(self):
        """API: GET /api/analytics — analytics summary across all vendors."""
        result = {}
        if os.path.exists(self.ACTIVITY_DIR):
            for vendor_folder in os.listdir(self.ACTIVITY_DIR):
                vendor_path = os.path.join(self.ACTIVITY_DIR, vendor_folder)
                if os.path.isdir(vendor_path):
                    analytics = self._collect_vendor_analytics(vendor_folder)
                    if analytics["totals"]:
                        result[vendor_folder] = analytics
        self.send_json_response(result)

    # ── Vendor Scanning ─────────────────────────────────────────────

    def scan_vendors(self):
        """
        Scan SCRIPT_DIR for vendor subdirectories.
        A valid vendor directory contains both index.html and guide.html.
        Extract display name from <title> tag in index.html.
        """
        vendors = []

        try:
            entries = os.listdir(self.SCRIPT_DIR)
        except OSError:
            return vendors

        for entry in entries:
            entry_path = os.path.join(self.SCRIPT_DIR, entry)

            # Check if it's a directory
            if not os.path.isdir(entry_path):
                continue

            # Check for required files
            index_path = os.path.join(entry_path, "index.html")
            guide_path = os.path.join(entry_path, "guide.html")

            if not (os.path.exists(index_path) and os.path.exists(guide_path)):
                continue

            # Extract display name from index.html title
            display_name = self.extract_vendor_name(index_path)
            if not display_name:
                display_name = entry

            # Check if vendor has tasks (check for postings file)
            postings_file = os.path.join(self.SCRIPT_DIR, f"postings_{entry}.json")
            has_tasks = os.path.exists(postings_file)

            # Count postings
            posting_count = 0
            if has_tasks:
                try:
                    with open(postings_file, "r") as f:
                        postings_data = json.load(f)
                        categories = postings_data.get("categories", {})
                        for category in categories.values():
                            if isinstance(category, list):
                                posting_count += len(category)
                            elif isinstance(category, dict):
                                posts = category.get("posts", [])
                                posting_count += len(posts)
                except (json.JSONDecodeError, IOError):
                    pass

            vendors.append(
                {
                    "folder": entry,
                    "display_name": display_name,
                    "has_tasks": has_tasks,
                    "posting_count": posting_count,
                }
            )

        return sorted(vendors, key=lambda v: v["display_name"])

    def extract_vendor_name(self, html_path):
        """
        Extract vendor name from <title> tag in HTML file.
        Expected format: <title>VENDOR_NAME - SID Vendor Portal</title>
        """
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Use regex to find title tag
                match = re.search(r"<title>\s*(.+?)\s*-\s*SID Vendor Portal\s*</title>", content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        except (IOError, UnicodeDecodeError):
            pass

        return None

    def resolve_case_insensitive(self, file_path):
        """Resolve a file path case-insensitively by checking existing directories."""
        full_path = os.path.join(self.SCRIPT_DIR, file_path)
        if os.path.exists(full_path):
            return full_path

        # Try case-insensitive match on the first path segment (vendor folder)
        parts = file_path.split("/", 1)
        if parts:
            base_dir = self.SCRIPT_DIR
            for entry in os.listdir(base_dir):
                if entry.lower() == parts[0].lower() and os.path.isdir(os.path.join(base_dir, entry)):
                    resolved = os.path.join(base_dir, entry)
                    if len(parts) > 1:
                        resolved = os.path.join(resolved, parts[1])
                    if os.path.exists(resolved):
                        return resolved
                    break
        return full_path  # Return original (will 404 naturally)

    def serve_vendor_portal(self, path):
        """Serve the dynamic vendor portal for /portal/VENDORNAME/."""
        parts = path.strip("/").split("/")
        # parts = ['portal', 'VENDORNAME'] or ['portal', 'VENDORNAME', '']
        if len(parts) < 2 or not parts[1]:
            self.send_error(404)
            return

        vendor_folder = parts[1]

        # Validate vendor exists
        vendor_path = os.path.join(self.SCRIPT_DIR, vendor_folder)
        if not os.path.isdir(vendor_path):
            # Try case-insensitive match
            try:
                for entry in os.listdir(self.SCRIPT_DIR):
                    if entry.lower() == vendor_folder.lower() and os.path.isdir(os.path.join(self.SCRIPT_DIR, entry)):
                        vendor_folder = entry
                        vendor_path = os.path.join(self.SCRIPT_DIR, vendor_folder)
                        break
                else:
                    self.send_error(404)
                    return
            except OSError:
                self.send_error(404)
                return

        # Serve portal_v3_demo.html — the vendor is detected from the URL by the JS
        portal_file = os.path.join(self.SCRIPT_DIR, "portal_v3_demo.html")
        if not os.path.exists(portal_file):
            self.send_error(404)
            return

        try:
            with open(portal_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except IOError:
            self.send_error(500)

    def serve_static_file(self, file_path):
        """Serve a static file from SCRIPT_DIR with case-insensitive vendor folder matching."""
        full_path = self.resolve_case_insensitive(file_path)

        # Security: prevent directory traversal
        try:
            full_path = os.path.abspath(full_path)
            if not full_path.startswith(os.path.abspath(self.SCRIPT_DIR)):
                self.send_error(403)
                return
        except Exception:
            self.send_error(403)
            return

        if not os.path.exists(full_path):
            self.send_error(404)
            return

        # If it's a directory, serve index.html inside it
        if os.path.isdir(full_path):
            index_path = os.path.join(full_path, "index.html")
            if os.path.exists(index_path):
                full_path = index_path
            else:
                self.send_error(404)
                return

        try:
            # Determine content type
            content_type = self.get_content_type(full_path)

            with open(full_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except IOError:
            self.send_error(500)

    def serve_upload_file(self, path):
        """Serve a file from the uploads directory."""
        # Strip leading /uploads/ and resolve
        relative = path.replace("/uploads/", "", 1)
        full_path = os.path.abspath(os.path.join(self.UPLOAD_DIR, relative))

        # Security: prevent traversal outside uploads dir
        if not full_path.startswith(os.path.abspath(self.UPLOAD_DIR)):
            self.send_error(403)
            return

        if not os.path.exists(full_path) or os.path.isdir(full_path):
            self.send_error(404)
            return

        try:
            content_type = self.get_content_type(full_path)
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except IOError:
            self.send_error(500)

    def get_content_type(self, file_path):
        """Determine content type based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".txt": "text/plain",
            ".zip": "application/zip",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
        }
        return content_types.get(ext, "application/octet-stream")

    # ===== AI CONFIG & GENERATION =====

    def _get_config_path(self):
        return os.path.join(self.SCRIPT_DIR, "server_config.json")

    def _load_config(self):
        path = self._get_config_path()
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {"ai_provider": "anthropic", "anthropic_api_key": "", "openai_api_key": ""}

    def _save_config(self, config):
        with open(self._get_config_path(), "w") as f:
            json.dump(config, f, indent=2)

    def handle_get_ai_config(self):
        config = self._load_config()
        # Mask API keys for frontend display (show last 8 chars)
        safe = {
            "ai_provider": config.get("ai_provider", "anthropic"),
            "anthropic_key_set": bool(config.get("anthropic_api_key", "")),
            "openai_key_set": bool(config.get("openai_api_key", "")),
            "anthropic_key_hint": config.get("anthropic_api_key", "")[-8:] if config.get("anthropic_api_key") else "",
            "openai_key_hint": config.get("openai_api_key", "")[-8:] if config.get("openai_api_key") else "",
            "default_prompt": config.get("default_prompt", ""),
        }
        self.send_json_response(safe)

    def handle_save_ai_config(self, body):
        try:
            data = json.loads(body)
            config = self._load_config()
            if "ai_provider" in data:
                config["ai_provider"] = data["ai_provider"]
            if "anthropic_api_key" in data and data["anthropic_api_key"]:
                config["anthropic_api_key"] = data["anthropic_api_key"]
            if "openai_api_key" in data and data["openai_api_key"]:
                config["openai_api_key"] = data["openai_api_key"]
            if "default_prompt" in data:
                config["default_prompt"] = data["default_prompt"]
            self._save_config(config)
            self.send_json_response({"ok": True})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def _load_existing_postings(self, vendor):
        """Load existing posting titles and summaries for a vendor to avoid duplicates."""
        postings_file = os.path.join(self.SCRIPT_DIR, f"postings_{vendor}.json")
        if not os.path.exists(postings_file):
            return []
        try:
            with open(postings_file, "r") as f:
                data = json.load(f)
            categories = data.get("categories", data)
            existing = []
            for cat, posts in categories.items():
                for p in posts:
                    if p.get("archived"):
                        continue
                    # Summarize each existing posting briefly
                    loc = p.get("location", {})
                    loc_str = loc.get("type", "Remote") if isinstance(loc, dict) else str(loc)
                    existing.append(f"- [{cat}] {p.get('title', '?')} | {p.get('salary', '?')} | {loc_str}")
            return existing
        except Exception:
            return []

    def handle_generate_posting(self, body):
        """Call AI API to generate a full job posting from a title + optional context."""
        try:
            data = json.loads(body)
            title = data.get("title", "").strip()
            context = data.get("context", "").strip()
            vendor = data.get("vendor", "").strip()

            if not title:
                self.send_json_response({"error": "Title is required"}, 400)
                return

            config = self._load_config()
            provider = config.get("ai_provider", "anthropic")
            default_prompt = config.get("default_prompt", "").strip()

            # Load existing postings for differentiation
            existing = self._load_existing_postings(vendor) if vendor else []
            existing_block = ""
            if existing:
                existing_list = "\n".join(existing[:30])  # Cap at 30 to keep prompt manageable
                existing_block = f"""
IMPORTANT — This vendor already has these postings. Generate something DIFFERENT — vary the wording, angle, focus, and tone so this new posting is clearly distinct:
{existing_list}
"""

            prompt_text = f"""Generate a complete job posting for a BPO/outsourcing staffing company. Return ONLY valid JSON with no markdown formatting, no code blocks, no explanation.

Job Title: {title}
{"Additional context: " + context if context else ""}
{"Company/Vendor: " + vendor if vendor else ""}
{("STYLE INSTRUCTIONS (always follow these): " + default_prompt) if default_prompt else ""}
{existing_block}
Return this exact JSON structure:
{{"title": "the full job title", "salary": "competitive salary range like $XX-$XX/hr or $XXK-$XXK/year", "workType": "Remote", "remoteLocation": "US", "benefits": "comma separated benefits like Health Insurance, 401k, PTO, Dental", "description": "HTML formatted job description with sections for About the Role, Responsibilities (as ul/li), Requirements (as ul/li), and Nice to Have (as ul/li). Use <h3> for section headers, <ul><li> for lists, <p> for paragraphs. Make it professional and detailed, 200-400 words."}}"""

            if provider == "anthropic":
                api_key = config.get("anthropic_api_key", "")
                if not api_key:
                    self.send_json_response({"error": "Anthropic API key not configured. Go to AI Settings to add it."}, 400)
                    return
                result = self._call_anthropic(api_key, prompt_text)
            elif provider == "openai":
                api_key = config.get("openai_api_key", "")
                if not api_key:
                    self.send_json_response({"error": "OpenAI API key not configured. Go to AI Settings to add it."}, 400)
                    return
                result = self._call_openai(api_key, prompt_text)
            else:
                self.send_json_response({"error": f"Unknown provider: {provider}"}, 400)
                return

            # Parse the AI response as JSON
            # Strip any markdown code blocks if present
            result = result.strip()
            if result.startswith("```"):
                result = re.sub(r'^```(?:json)?\s*', '', result)
                result = re.sub(r'\s*```$', '', result)
            posting = json.loads(result)
            self.send_json_response(posting)

        except json.JSONDecodeError as e:
            self.send_json_response({"error": f"AI returned invalid JSON: {str(e)}", "raw": result[:500] if 'result' in dir() else ""}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    @staticmethod
    def _get_ssl_context():
        """Get SSL context, trying certifi certs first, then unverified fallback."""
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass
        # macOS Python often lacks proper certs — use unverified as fallback
        ctx = ssl._create_unverified_context()
        return ctx

    def _call_anthropic(self, api_key, prompt):
        """Call Anthropic Claude API."""
        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        ctx = self._get_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]

    def _call_openai(self, api_key, prompt):
        """Call OpenAI ChatGPT API."""
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        ctx = self._get_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]

    # =========================================================================
    # CSV PIPELINE HANDLERS
    # =========================================================================

    def handle_get_pipeline_log(self):
        """GET /api/pipeline-log — return today's pipeline runs."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline not available"}, 500)
        today = date.today().isoformat()
        log = csv_pipeline.get_pipeline_log(date_filter=today)
        self.send_json_response(log)

    def handle_get_pipeline_exports(self):
        """GET /api/pipeline-exports — return today's exportable files."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline not available"}, 500)
        exports = csv_pipeline.get_today_exports()
        self.send_json_response({"exports": exports})

    def handle_get_combined_export(self, category):
        """GET /api/pipeline-export/{category} — return combined today's export for a category."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline not available"}, 500)
        try:
            combined_df, stats = csv_pipeline.get_today_combined_export(category)
            if combined_df.empty:
                return self.send_json_response({"error": stats.get("error", "No data"), "stats": stats}, 404)

            result = {
                "ok": True,
                "stats": stats,
                "rows": len(combined_df),
                "preview": combined_df.head(50).to_dict(orient="records"),
                "csv_base64": base64.b64encode(combined_df.to_csv(index=False).encode("utf-8")).decode("ascii"),
            }
            self.send_json_response(result)
        except Exception as e:
            print(f"[ERROR] handle_get_combined_export: {traceback.format_exc()}", flush=True)
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_pipeline_config(self):
        """GET /api/pipeline-config — return pipeline configuration."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        config = csv_pipeline.get_pipeline_config()
        self.send_json_response(config)

    def handle_save_pipeline_config(self, body):
        """POST /api/pipeline-config — save pipeline configuration."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        try:
            config = json.loads(body)
            result = csv_pipeline.save_pipeline_config(config)
            self.send_json_response(result)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_get_master_list_categories(self):
        """GET /api/master-lists — return list of category names."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        cats = csv_pipeline.get_master_list_categories()
        self.send_json_response({"categories": cats})

    def handle_get_master_list(self, category):
        """GET /api/master-list/{category} — return master list data + sheet info.
        Supports ?sheet=SheetName query param to read a specific tab.
        """
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)

        # Parse optional sheet query param
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        sheet = query.get("sheet", [None])[0]

        # Get sheet listing
        sheet_info = csv_pipeline.get_master_list_sheets(category)

        df = csv_pipeline.get_master_list(category, sheet=sheet)

        # Convert datetime columns to strings for JSON
        if not df.empty and "Date" in df.columns:
            df["Date"] = df["Date"].apply(lambda x: str(x) if x is not None else "")

        result = {
            "category": category,
            "rows": len(df),
            "columns": list(df.columns) if not df.empty else csv_pipeline.MASTER_LIST_COLS,
            "data": df.tail(200).to_dict(orient="records") if not df.empty else [],
            "total_rows": len(df),
            "sheets": sheet_info.get("sheets", []),
            "rolling_tab": sheet_info.get("rolling_tab", ""),
            "dedup_days": sheet_info.get("dedup_days", 30),
            "active_sheet": sheet or sheet_info.get("rolling_tab", ""),
        }
        self.send_json_response(result)

    def handle_csv_clean(self, body):
        """POST /api/csv-clean — clean CSV data.
        Body: { type: "indeed"|"linkedin", files: [{name, data_base64}], company, list, date, stage }
        """
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        try:
            params = json.loads(body)
            cleaner_type = params.get("type", "indeed")
            files_data = params.get("files", [])
            company = params.get("company", "")
            list_val = params.get("list", "")
            date_val = params.get("date", "")
            stage = params.get("stage", "Initial")

            # Decode base64 file data
            csv_list = []
            for f in files_data:
                name = f.get("name", "unknown.csv")
                data_b64 = f.get("data_base64", "")
                if data_b64:
                    csv_list.append((name, base64.b64decode(data_b64)))

            if not csv_list:
                return self.send_json_response({"error": "No files provided"}, 400)

            if cleaner_type == "linkedin":
                cleaned_df, stats = csv_pipeline.clean_linkedin(
                    csv_list, company=company, list_val=list_val,
                    date_val=date_val, stage=stage
                )
            else:
                cleaned_df, stats = csv_pipeline.clean_indeed(
                    csv_list, company=company, list_val=list_val,
                    date_val=date_val, stage=stage
                )

            if cleaned_df is None:
                return self.send_json_response({"error": "Cleaning failed", "stats": stats}, 400)

            result = {
                "ok": True,
                "stats": stats,
                "rows": len(cleaned_df),
                "columns": list(cleaned_df.columns),
                "preview": cleaned_df.head(50).to_dict(orient="records"),
                "csv_base64": base64.b64encode(cleaned_df.to_csv(index=False).encode("utf-8")).decode("ascii"),
            }
            self.send_json_response(result)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_add_to_master_list(self, category, body):
        """POST /api/master-list/{category}/add — add cleaned CSV data to master list Excel workbook."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        try:
            params = json.loads(body)
            csv_b64 = params.get("csv_base64", "")
            if not csv_b64:
                return self.send_json_response({"error": "No csv_base64 provided"}, 400)

            csv_bytes = base64.b64decode(csv_b64)
            import pandas as _pd
            df = _pd.read_csv(io.StringIO(csv_bytes.decode("utf-8")), dtype=str, keep_default_na=False)

            stats = csv_pipeline.add_to_master_list(category, df)
            self.send_json_response({"ok": True, **stats})

        except Exception as e:
            print(f"[ERROR] handle_add_to_master_list: {traceback.format_exc()}", flush=True)
            self.send_json_response({"error": str(e)}, 500)

    def handle_dedup_master_list(self, category, body):
        """POST /api/master-list/{category}/dedup — deduplicate master list Excel workbook."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        try:
            params = json.loads(body) if body else {}
            days = params.get("days", None)  # None = use category default

            today_kept_df, removed_df, stats = csv_pipeline.dedup_master_list(category, days=days)

            result = {
                "ok": True,
                "stats": stats,
                "today_kept_rows": len(today_kept_df),
                "removed_rows": len(removed_df),
            }

            # Today's kept data = what gets exported for HeyMarket/GoHighLevel
            if not today_kept_df.empty:
                # Convert dates to strings for JSON
                export_df = today_kept_df.copy()
                if "Date" in export_df.columns:
                    export_df["Date"] = export_df["Date"].apply(lambda x: str(x) if x is not None else "")
                result["today_kept_preview"] = export_df.head(50).to_dict(orient="records")
                result["today_kept_csv_base64"] = base64.b64encode(
                    export_df.to_csv(index=False).encode("utf-8")
                ).decode("ascii")

            if not removed_df.empty:
                result["removed_preview"] = removed_df.head(50).to_dict(orient="records")

            self.send_json_response(result)

        except Exception as e:
            print(f"[ERROR] handle_dedup_master_list: {traceback.format_exc()}", flush=True)
            self.send_json_response({"error": str(e)}, 500)

    def handle_row_divide(self, body):
        """POST /api/row-divide — divide rows among accounts."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        try:
            params = json.loads(body)
            csv_b64 = params.get("csv_base64", "")
            accounts = params.get("accounts", [])
            date_val = params.get("date", "")
            list_template = params.get("list_template", "")
            mode = params.get("mode", "auto_scale")
            style = params.get("style", "smart_random")

            if not csv_b64:
                return self.send_json_response({"error": "No csv_base64 provided"}, 400)

            csv_bytes = base64.b64decode(csv_b64)
            zip_bytes, stats = csv_pipeline.divide_rows(
                csv_bytes, accounts, date_val=date_val,
                list_template=list_template, mode=mode, style=style
            )

            if zip_bytes is None:
                return self.send_json_response({"error": stats.get("error", "Division failed")}, 400)

            result = {
                "ok": True,
                "stats": stats,
                "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
            }
            self.send_json_response(result)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_pipeline_run(self, body):
        """POST /api/pipeline-run — run the full pipeline."""
        if not csv_pipeline:
            return self.send_json_response({"error": "csv_pipeline module not available"}, 500)
        try:
            params = json.loads(body)
            category = params.get("category", "")
            cleaner_type = params.get("type", "indeed")
            company = params.get("company", "")
            list_val = params.get("list", "")
            date_val = params.get("date", "")
            stage = params.get("stage", "Initial")
            do_dedup = params.get("dedup", True)
            dedup_days = params.get("dedup_days", 30)
            do_divide = params.get("divide", False)
            accounts = params.get("accounts", [])
            list_template = params.get("list_template", "")
            divide_mode = params.get("divide_mode", "auto_scale")
            divide_style = params.get("divide_style", "smart_random")

            # Handle file data
            files_data = params.get("files", [])
            csv_list = []
            for f in files_data:
                name = f.get("name", "unknown.csv")
                data_b64 = f.get("data_base64", "")
                if data_b64:
                    csv_list.append((name, base64.b64decode(data_b64)))

            if not csv_list:
                # Try vendor ZIP extraction
                vendor = params.get("vendor", "")
                zip_path = params.get("zip_path", "")
                if vendor and zip_path:
                    full_path = os.path.join(self.SCRIPT_DIR, zip_path)
                    if os.path.exists(full_path):
                        with open(full_path, "rb") as f:
                            zip_bytes = f.read()
                        csv_list = csv_pipeline.extract_csvs_from_zip(zip_bytes)

            if not csv_list:
                return self.send_json_response({"error": "No files provided"}, 400)

            results = csv_pipeline.run_full_pipeline(
                csv_list, category, cleaner_type=cleaner_type,
                company=company, list_val=list_val, date_val=date_val, stage=stage,
                do_dedup=do_dedup, dedup_days=dedup_days,
                do_divide=do_divide, accounts=accounts, list_template=list_template,
                divide_mode=divide_mode, divide_style=divide_style,
            )

            self.send_json_response(results)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def send_json_response(self, data, status=200):
        """Send a JSON response with CORS headers."""
        json_data = json.dumps(data)
        json_bytes = json_data.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(json_bytes))
        self.end_headers()
        self.wfile.write(json_bytes)

    def log_message(self, format, *args):
        """Suppress default logging - cleaner output."""
        # Optionally log to stderr, but keep it minimal
        # sys.stderr.write(f"{self.client_address[0]} - {format%args}\n")
        pass


def run_server(port=8888):
    """Start the SID Manager server."""
    handler = SIDManagerHandler
    class ThreadedServer(http.server.ThreadingHTTPServer):
        allow_reuse_address = True
    server = ThreadedServer(("0.0.0.0", port), handler)

    print(f"\n{'='*60}")
    print(f"SID Manager running at http://localhost:{port}/manager.html")
    print(f"{'='*60}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    port = 8888
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)

    run_server(port)
