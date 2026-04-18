#!/usr/bin/env python3
"""
SID Vendor Spawner
-------------------
GUI for creating a new vendor hub under sid.rocks/<VendorName> by cloning
the live FBSPL folder and running per-vendor string substitutions.

Two output modes:
  - Download SID (current):   install button downloads bundled SID.zip
                              + shows the unzip/load-unpacked modal.
  - Chrome Web Store (future): install button links to the SID extension
                              listing on the Chrome Web Store; unzip steps
                              in the guide are replaced with "Add to Chrome".

After creation, optionally runs `git add / commit / push` so sid.rocks
deploys the new portal automatically.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path
from datetime import datetime


# ─────────────────────────── constants ──────────────────────────── #

# Template vendor we clone from. FBSPL is kept as the canonical reference
# because its folder mirrors what the live portal should look like.
TEMPLATE_VENDOR = "FBSPL"

# Hard-coded values that live inside FBSPL and need to be replaced per vendor
FBSPL_ONEDRIVE_URL = (
    "https://jobosaurus-my.sharepoint.com/:f:/g/personal/"
    "mallen_wallstjobs_com/IgAQAkLWz04gQIx-W-6lgkeSAXisYkAu9c0UU_1ieyVdsgI"
)

# Chrome Web Store listing for the SID extension. When the pending update is
# published, this is the URL new vendors should be sent to. Re-publishing the
# extension does not change the listing ID, so this URL is stable.
CHROME_WEBSTORE_URL = (
    "https://chromewebstore.google.com/detail/oaejdaekhegedlgoanfkogmoiceelkbc"
)

# Files we expect in the template folder. If any are missing we bail early.
TEMPLATE_FILES = ["index.html", "guide.html", "guide_direct.html", "SID.zip"]

# If the user ever switches FBSPL's own install mode (e.g. from Download to
# Chrome Web Store), we snapshot the original FBSPL folder here so new vendors
# can still be spawned from the download-flavored template. The snapshot is
# preferred as the template source when it exists.
TEMPLATE_SNAPSHOT_DIR = ".fbspl_template"


# ─────────────────────────── helpers ────────────────────────────── #

def sid_root() -> Path:
    """Locate the repo root (/Users/.../Documents/SID).

    The app bundle lives at <root>/SID Vendor Spawner.app/Contents/Resources/app.py
    so the root is 4 parents up from this file.
    """
    here = Path(__file__).resolve()
    # app.py -> Resources -> Contents -> SID Vendor Spawner.app -> <root>
    return here.parents[3]


def sanitize_folder_name(raw: str) -> str:
    """Strip characters that are unsafe in folder names / URLs."""
    cleaned = re.sub(r"[^A-Za-z0-9_\-]", "", raw.strip())
    return cleaned


def get_template_path(root: Path) -> Path:
    """Return the folder we should clone new vendors from.

    Prefers the hidden `.fbspl_template/` snapshot if it exists — that snapshot
    holds the original, download-mode-wired FBSPL files and is created the
    first time FBSPL itself is switched to a non-default install mode. Falls
    back to the live FBSPL folder otherwise.
    """
    snapshot = root / TEMPLATE_SNAPSHOT_DIR
    if snapshot.is_dir():
        return snapshot
    return root / TEMPLATE_VENDOR


def ensure_template_snapshot(root: Path, log) -> Path:
    """Create `.fbspl_template/` from the live FBSPL folder if it doesn't exist.

    Called before any operation that would mutate FBSPL's install wiring, so
    future `spawn_vendor` calls still have a clean download-flavored template
    to clone from.
    """
    snapshot = root / TEMPLATE_SNAPSHOT_DIR
    if snapshot.is_dir():
        return snapshot
    tmpl = root / TEMPLATE_VENDOR
    if not tmpl.is_dir():
        raise FileNotFoundError(
            f"Cannot create template snapshot — {tmpl} does not exist."
        )
    log(f"  ✓ snapshotting {tmpl.name}/ → {TEMPLATE_SNAPSHOT_DIR}/ (preserves template)")
    shutil.copytree(tmpl, snapshot)
    return snapshot


def detect_vendor_upload_url(vendor_dir: Path) -> str:
    """Pull the OneDrive upload URL from an existing vendor's index.html.

    Used so switch-mode operations can preserve the vendor's existing upload
    link without making the user re-paste it. Returns "" if nothing was found.
    """
    idx = vendor_dir / "index.html"
    if not idx.exists():
        return ""
    try:
        html = idx.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(
        r'https://jobosaurus-my\.sharepoint\.com/[^\s"<>\')]+',
        html,
    )
    return match.group(0) if match else ""


# ─────────────────────── transformation logic ───────────────────── #

def transform_html(
    content: str,
    vendor_slug: str,
    display_name: str,
    upload_url: str,
    mode: str,  # "download" or "webstore"
) -> str:
    """Apply all per-vendor and per-mode replacements to an HTML file.

    ``vendor_slug`` is URL/filesystem-safe (e.g. "AlfaRecruit") and is used in
    URL paths, localStorage keys, and filename references. ``display_name``
    (e.g. "Alfa Recruit") is the pretty human-facing version used in <title>,
    <h1>, subtitle copy, etc. If display_name is empty, falls back to the slug.
    """
    if not display_name:
        display_name = vendor_slug

    # 1) slug contexts FIRST — URLs, storage keys, filename refs. These must
    # stay URL/identifier-safe, so they always use the slug (not display name).
    slug_replacements = [
        (f"sid.rocks/{TEMPLATE_VENDOR}", f"sid.rocks/{vendor_slug}"),
        (f"sid_checklist_{TEMPLATE_VENDOR}", f"sid_checklist_{vendor_slug}"),
        (f"sid_tasks_{TEMPLATE_VENDOR}", f"sid_tasks_{vendor_slug}"),
        (f"bulletin_{TEMPLATE_VENDOR}", f"bulletin_{vendor_slug}"),
        (f"postings_{TEMPLATE_VENDOR}", f"postings_{vendor_slug}"),
    ]
    out = content
    for old, new in slug_replacements:
        out = out.replace(old, new)

    # 2) Any remaining FBSPL tokens are user-facing (<title>, <h1>, subtitle
    # copy) — swap them for the display name (may contain spaces).
    out = out.replace(TEMPLATE_VENDOR, display_name)

    # 3) upload URL: FBSPL's OneDrive link → the new vendor's link.
    # Appears multiple times in guide_direct.html and once in index.html.
    if upload_url:
        out = out.replace(FBSPL_ONEDRIVE_URL, upload_url)

    # 4) mode-specific rewrites (only when the user wants the Chrome Web Store
    # flow — for Download mode we leave the FBSPL wiring intact).
    if mode == "webstore":
        out = _rewrite_for_webstore(out)

    return out


def _rewrite_for_webstore(html: str) -> str:
    """Convert Download-SID.zip install wiring into Chrome-Web-Store wiring."""

    # --- index.html install button ---
    # Original: <a href="SID.zip" download id="installBtn" class="action install" onclick="handleInstallClick(event);">
    #             Download SID Extension
    html = html.replace(
        '<a href="SID.zip" download id="installBtn"',
        f'<a href="{CHROME_WEBSTORE_URL}" target="_blank" id="installBtn"',
    )
    # The "Download Again" secondary button inside the modal (only in index.html)
    html = html.replace(
        '<a href="SID.zip" download class="modal-download-btn" id="modalDownloadBtn">',
        f'<a href="{CHROME_WEBSTORE_URL}" target="_blank" class="modal-download-btn" id="modalDownloadBtn">',
    )
    html = html.replace("Download Again", "Open Chrome Web Store")

    # Button/modal copy
    html = html.replace("Download SID Extension", "Install SID Extension")
    html = html.replace(
        "Your download has started. Follow the steps below to install the extension in your browser.",
        "The Chrome Web Store page is opening. Click \"Add to Chrome\" to install SID — that's it.",
    )

    # Rewrite the install-steps list inside the modal to a short Add-to-Chrome flow.
    # We find the Chrome section and the Edge section and collapse each to a single step.
    html = _replace_install_steps(
        html,
        anchor='<div class="browser-section active" id="section-chrome">',
        new_steps=[
            'On the Chrome Web Store page, click <strong>"Add to Chrome"</strong>, then confirm with <strong>"Add extension"</strong>.',
            'Click the <strong>puzzle piece</strong> icon in Chrome\'s toolbar and <strong>pin SID</strong> so it\'s always visible.',
        ],
    )
    html = _replace_install_steps(
        html,
        anchor='<div class="browser-section" id="section-edge">',
        new_steps=[
            'On the Chrome Web Store page, click <strong>"Add to Chrome"</strong> (Edge prompts "Add extension from another store" — click <strong>Allow</strong>, then <strong>Add extension</strong>).',
            'Click the <strong>puzzle piece</strong> icon in Edge\'s toolbar and <strong>pin SID</strong> so it\'s always visible.',
        ],
    )

    # --- guide.html / guide_direct.html install section ---
    # Collapse the 6-step "unpack the ZIP + load unpacked" flow into 2 steps.
    html = _rewrite_guide_install_section(html)

    # Remove the "IMPORTANT: do not delete the unzipped folder" callout — not
    # relevant when installed from the Web Store.
    html = re.sub(
        r'<div class="important-box"><strong>IMPORTANT:</strong>\s*Do\s*<strong>not</strong>\s*delete or move the unzipped extension folder.*?</div>',
        "",
        html,
        flags=re.DOTALL,
    )

    # Edge tip about edge://extensions no longer needed
    html = re.sub(
        r'<div class="tip-box"><strong>TIP:</strong> If you use Microsoft Edge, the same steps work.*?</div>',
        '<div class="tip-box"><strong>TIP:</strong> The same Chrome Web Store link works in <strong>Microsoft Edge</strong> — Edge will ask if you want to allow extensions from other stores, click <strong>Allow</strong>.</div>',
        html,
        flags=re.DOTALL,
    )

    # Troubleshooting section: strip the "Load unpacked" / "Developer mode" advice
    # that only applied to the unpacked-install flow. chrome://extensions is still
    # legitimate for toggling the extension, so leave that.
    html = html.replace(
        'make sure <strong>Developer mode</strong> is toggled on, and check that SID is listed and enabled. If SID is gone, click <strong>"Load unpacked"</strong> and re-select the extension folder.',
        'check that SID is listed and enabled. If SID is gone, re-install it from the <strong>"Install SID Extension"</strong> button on your portal page.',
    )
    html = html.replace(
        'Chrome sometimes disables manually loaded extensions after updates. Go to <strong>chrome://extensions</strong>, make sure <strong>Developer mode</strong> is on, and check if SID is listed. If it\'s gone, click <strong>"Load unpacked"</strong> again and re-select the extension folder.',
        'Chrome occasionally disables extensions after updates. Go to <strong>chrome://extensions</strong> and check if SID is listed. If it\'s gone, re-install it from the <strong>"Install SID Extension"</strong> button on your portal page.',
    )

    return html


def _replace_install_steps(html: str, anchor: str, new_steps: list[str]) -> str:
    """Inside a browser-section div in the install modal, replace the <ol>."""
    idx = html.find(anchor)
    if idx < 0:
        return html
    ol_open = html.find('<ol class="install-steps">', idx)
    ol_close = html.find("</ol>", ol_open)
    if ol_open < 0 or ol_close < 0:
        return html

    steps_html = "\n      " + "\n      ".join(
        f'<li class="install-step">\n          <div class="step-number">{i+1}</div>\n          '
        f'<div class="step-content">{txt}</div>\n        </li>'
        for i, txt in enumerate(new_steps)
    ) + "\n    "

    return (
        html[:ol_open]
        + '<ol class="install-steps">'
        + steps_html
        + html[ol_close:]
    )


def _rewrite_guide_install_section(html: str) -> str:
    """Replace the multi-step install section in the vendor guide (guide.html / guide_direct.html)."""
    # The section starts with <h2>2. Installing SID</h2> and ends before <!-- ========== SECTION 3
    pattern = re.compile(
        r'(<h2>2\.\s*Installing SID</h2>\s*<div class="section-line"></div>\s*)'
        r'<p>You only need to do this once\.</p>.*?(?=<!--\s*=+\s*SECTION 3)',
        flags=re.DOTALL,
    )
    replacement = (
        r'\1<p>You only need to do this once.</p>\n'
        '    <div class="steps">\n'
        '      <div class="step"><div class="step-num">1</div><div class="step-text">'
        '<strong>Open the Chrome Web Store listing</strong> &mdash; Click the button below '
        '(or the <strong>"Install SID Extension"</strong> button on your portal page). '
        'This opens the SID extension page in Google Chrome or Microsoft Edge.<br><br>'
        f'<a href="{CHROME_WEBSTORE_URL}" target="_blank" '
        'style="display:inline-block;padding:10px 24px;background:linear-gradient(135deg,#7860a8,#9b7ed8);'
        'color:#fff;border-radius:10px;font-weight:700;font-size:14px;text-decoration:none;'
        'letter-spacing:0.3px;">Install SID Extension</a>'
        '</div></div>\n'
        '      <div class="step"><div class="step-num">2</div><div class="step-text">'
        '<strong>Click "Add to Chrome"</strong> &mdash; On the Chrome Web Store page, click the '
        '<strong>"Add to Chrome"</strong> button, then confirm with <strong>"Add extension"</strong>. '
        '(In Microsoft Edge, click <strong>Allow</strong> to permit extensions from the Chrome Web Store '
        'and then <strong>Add extension</strong>.)'
        '</div></div>\n'
        '      <div class="step"><div class="step-num">3</div><div class="step-text">'
        '<strong>Pin the extension</strong> &mdash; Click the <strong>puzzle piece</strong> icon in the '
        'browser toolbar and pin <strong>SID</strong> so the icon is always visible.'
        '</div></div>\n'
        '      <div class="step"><div class="step-num">4</div><div class="step-text">'
        '<strong>Done!</strong> Go to <strong>employers.indeed.com</strong> and log in. Navigate to a '
        'job\'s Candidates page and click on a candidate\'s name &mdash; the SID widget will appear in '
        'the top-right corner.'
        '</div></div>\n'
        '    </div>\n'
        '    <div class="tip-box"><strong>TIP:</strong> The same Chrome Web Store link works in '
        '<strong>Microsoft Edge</strong>. Edge will ask if you want to allow extensions from other '
        'stores the first time &mdash; click <strong>Allow</strong>.</div>\n'
        '  </div>\n\n  '
    )
    return pattern.sub(replacement, html)


# ─────────────────────── file operations ────────────────────────── #

def spawn_vendor(
    root: Path,
    vendor_name: str,
    upload_url: str,
    mode: str,
    log,
    display_name: str = "",
) -> Path:
    """Create the vendor folder by cloning the template and personalizing it.

    ``vendor_name`` is the URL/folder slug (e.g. "AlfaRecruit"). ``display_name``
    is the pretty, human-facing name (e.g. "Alfa Recruit") shown in <h1>,
    <title>, and guide copy. If ``display_name`` is empty the slug is used.
    """

    tmpl = get_template_path(root)
    if not tmpl.is_dir():
        raise FileNotFoundError(
            f"Template folder {tmpl} does not exist. This app must live inside "
            f"the SID repo so it can clone the {TEMPLATE_VENDOR} folder."
        )
    for needed in TEMPLATE_FILES:
        if not (tmpl / needed).exists():
            raise FileNotFoundError(
                f"Template folder {tmpl} is missing {needed}. Cannot spawn a new vendor."
            )

    dest = root / vendor_name
    if dest.exists():
        raise FileExistsError(
            f"Vendor folder {dest} already exists. Delete it first or pick a different name."
        )

    log(f"Cloning {tmpl.name}/ → {dest.name}/ …")
    shutil.copytree(tmpl, dest)

    # Personalize the three HTML files
    for fname in ("index.html", "guide.html", "guide_direct.html"):
        fpath = dest / fname
        src = fpath.read_text(encoding="utf-8")
        out = transform_html(src, vendor_name, display_name, upload_url, mode)
        fpath.write_text(out, encoding="utf-8")
        log(f"  ✓ rewrote {fname} ({len(src):,} → {len(out):,} bytes)")

    # In Chrome Web Store mode the vendor folder doesn't need the SID.zip file
    if mode == "webstore":
        zip_path = dest / "SID.zip"
        if zip_path.exists():
            zip_path.unlink()
            log("  ✓ removed SID.zip (not needed for Chrome Web Store mode)")

    # Drop blank bulletin/postings files at the repo root so the portal's fetch
    # calls resolve with empty arrays instead of a 404 network error.
    bulletin_file = root / f"bulletin_{vendor_name}.json"
    postings_file = root / f"postings_{vendor_name}.json"
    if not bulletin_file.exists():
        bulletin_file.write_text("[]", encoding="utf-8")
        log(f"  ✓ created {bulletin_file.name}")
    if not postings_file.exists():
        postings_file.write_text(json.dumps({"categories": {}}), encoding="utf-8")
        log(f"  ✓ created {postings_file.name}")

    return dest


def switch_vendor_mode(
    root: Path,
    vendor_name: str,
    new_mode: str,
    upload_url: str,
    log,
    display_name: str = "",
) -> Path:
    """Flip an existing vendor folder between Download and Chrome Web Store mode.

    Used when sid.rocks/<vendor> already exists and the user wants to change
    its install flow in place (same URL, same folder name). We re-generate
    all three HTML files from the template, preserving the vendor's existing
    OneDrive upload URL unless the caller supplied a new one.

    Switching FBSPL is allowed: we snapshot the live FBSPL folder into
    .fbspl_template/ first so future `spawn_vendor` calls still have a clean
    download-wired source to clone from.
    """
    tmpl = get_template_path(root)
    if not tmpl.is_dir():
        raise FileNotFoundError(
            f"Template folder {tmpl} does not exist — cannot re-generate "
            f"vendor HTML."
        )

    dest = root / vendor_name
    if not dest.is_dir():
        raise FileNotFoundError(
            f"Vendor folder {dest} does not exist. Use the 'new vendor' "
            f"modes to create it first."
        )

    # Preserve the vendor's existing upload URL if the caller didn't pass one
    if not upload_url:
        upload_url = detect_vendor_upload_url(dest)
        if upload_url:
            log(f"  ✓ detected existing OneDrive URL in {vendor_name}/index.html")
        else:
            log(
                f"  ⚠ couldn't find an existing OneDrive URL in "
                f"{vendor_name}/index.html — switch will leave the template "
                f"placeholder in place (you can edit it manually)."
            )

    # If we're about to mutate FBSPL's wiring, preserve the template first so
    # future spawns still have a download-mode source to clone from.
    if vendor_name == TEMPLATE_VENDOR:
        ensure_template_snapshot(root, log)
        # After snapshotting, the spawn source is now .fbspl_template/, so this
        # switch can safely touch the FBSPL folder without corrupting the
        # template lineage.

    mode_label = "Chrome Web Store" if new_mode == "webstore" else "Download SID"
    log(f"Switching {vendor_name}/ → {mode_label} mode…")

    # Re-generate each HTML file from the template with the new mode applied
    for fname in ("index.html", "guide.html", "guide_direct.html"):
        src_path = tmpl / fname
        if not src_path.exists():
            log(f"  ⚠ template missing {fname}, skipping")
            continue
        src = src_path.read_text(encoding="utf-8")
        out = transform_html(src, vendor_name, display_name, upload_url, new_mode)
        (dest / fname).write_text(out, encoding="utf-8")
        log(f"  ✓ rewrote {fname} ({len(src):,} → {len(out):,} bytes)")

    # SID.zip handling
    zip_path = dest / "SID.zip"
    if new_mode == "webstore":
        if zip_path.exists():
            try:
                zip_path.unlink()
                log("  ✓ removed SID.zip (not needed for Chrome Web Store mode)")
            except OSError as e:
                log(f"  ⚠ could not remove {zip_path}: {e} (harmless — nothing references it in CWS mode)")
    else:  # download
        tmpl_zip = tmpl / "SID.zip"
        if tmpl_zip.exists() and not zip_path.exists():
            shutil.copy2(tmpl_zip, zip_path)
            log(f"  ✓ restored SID.zip ({zip_path.stat().st_size:,} bytes) for Download mode")

    return dest


def update_sid_zip(root: Path, new_zip_path: Path, log) -> int:
    """Replace SID.zip in the template and every Download-mode vendor folder.

    Called when the underlying SID extension is updated and every vendor that
    ships a bundled ZIP needs the new build. Vendors that have already been
    switched to Chrome Web Store mode don't carry a SID.zip and are skipped.

    Returns the number of folders that were updated (template + vendors).
    """
    if not new_zip_path.is_file():
        raise FileNotFoundError(f"SID.zip source {new_zip_path} does not exist.")
    if new_zip_path.suffix.lower() != ".zip":
        raise ValueError(f"{new_zip_path.name} is not a .zip file.")

    size = new_zip_path.stat().st_size
    log(f"Updating SID.zip from {new_zip_path.name} ({size:,} bytes)…")

    updated = 0
    targets: list[Path] = []

    # The snapshot template always gets the new zip if it exists — it's the
    # clean Download-wired source for future spawns, so it must always carry
    # the latest SID.zip. (If the snapshot doesn't exist yet, FBSPL itself is
    # the template and will be caught by the "existing SID.zip" scan below.)
    snapshot = root / TEMPLATE_SNAPSHOT_DIR
    if snapshot.is_dir() and (snapshot / "SID.zip").exists():
        targets.append(snapshot)

    # Every folder (FBSPL and real vendors) that already has a SID.zip is a
    # Download-mode portal and should receive the update. Folders that have
    # been switched to Chrome Web Store mode no longer carry a SID.zip and are
    # skipped automatically.
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") and child != snapshot:
            continue
        if child in targets:
            continue
        if (child / "SID.zip").exists():
            targets.append(child)

    if not targets:
        log("  ⚠ no folders with SID.zip found — nothing to update.")
        return 0

    for target in targets:
        dest_zip = target / "SID.zip"
        try:
            shutil.copy2(new_zip_path, dest_zip)
            log(f"  ✓ {target.name}/SID.zip updated")
            updated += 1
        except OSError as e:
            log(f"  ✗ could not update {target.name}/SID.zip: {e}")

    log(f"Done. {updated} folder(s) updated.")
    return updated


# ───────────────────────── git push ─────────────────────────────── #

def git_push(
    root: Path,
    vendor_name: str,
    mode: str,
    log,
    *,
    action: str = "add",
) -> bool:
    """Stage the vendor files and push them to the sid.rocks remote.

    ``action`` is a short verb ("add", "switch", "update") used in the commit
    message so git history clearly distinguishes a new vendor spawn from an
    in-place mode flip or a bundle update.
    """
    mode_label = "Chrome Web Store" if mode == "webstore" else "Download SID"
    log(f"Running git add/commit/push in {root} …")

    paths: list[str]
    if action == "update":
        # Updating SID.zip touches the template + every download-mode vendor folder;
        # stage the whole repo so we don't have to enumerate every folder here.
        paths = ["."]
    else:
        # bulletin_*.json / postings_*.json are intentionally gitignored — they
        # accumulate candidate/PII data locally and must never go to GitHub.
        # Only stage the vendor's portal folder.
        paths = [vendor_name]

    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=root, capture_output=True, text=True)

    # 1. git add
    add = run(["git", "add"] + paths)
    if add.returncode != 0:
        log(f"  ✗ git add failed: {add.stderr.strip()}")
        return False
    log("  ✓ git add")

    # 2. git commit
    if action == "switch":
        commit_msg = f"Switch {vendor_name} to {mode_label} install mode"
    elif action == "update":
        commit_msg = f"Update bundled SID.zip across Download-mode vendors"
    else:
        commit_msg = f"Add {vendor_name} vendor portal ({mode_label} mode)"
    commit = run(["git", "commit", "-m", commit_msg])
    if commit.returncode != 0:
        # Nothing to commit is fine, anything else is a real failure
        combined = (commit.stdout + commit.stderr).lower()
        if "nothing to commit" in combined:
            log("  (nothing new to commit)")
        else:
            log(f"  ✗ git commit failed: {commit.stderr.strip() or commit.stdout.strip()}")
            return False
    else:
        log(f"  ✓ git commit — \"{commit_msg}\"")

    # 3. git push
    push = run(["git", "push"])
    if push.returncode != 0:
        log(f"  ✗ git push failed: {push.stderr.strip() or push.stdout.strip()}")
        return False
    log("  ✓ git push")
    return True


# ──────────────────────────── GUI ───────────────────────────────── #

class SpawnerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SID Vendor Spawner")
        self.geometry("740x740")
        self.minsize(680, 640)

        # state vars
        self.vendor_var = tk.StringVar()
        self.display_var = tk.StringVar()
        # Track whether the user manually edited Display name — if not, we
        # keep auto-filling it from Vendor name as they type.
        self._display_edited_by_user = False
        self.upload_var = tk.StringVar()
        # mode values: "download" (new), "webstore_new" (preview), "webstore_switch" (in-place)
        self.mode_var = tk.StringVar(value="download")
        self.push_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._log_line(f"Ready. Repo root: {sid_root()}")
        self._log_line(f"Template vendor: {TEMPLATE_VENDOR}")
        self._log_line("")

    # --- layout ----------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 14, "pady": 6}

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", **pad)
        ttk.Label(
            header,
            text="SID Vendor Spawner",
            font=("Helvetica", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Clone the FBSPL vendor hub for a new vendor, then push to sid.rocks.",
            foreground="#555",
        ).pack(anchor="w")

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=14, pady=(4, 6))

        # Form
        form = ttk.Frame(self)
        form.pack(fill="x", **pad)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Vendor name").grid(row=0, column=0, sticky="w", pady=4)
        vendor_entry = ttk.Entry(form, textvariable=self.vendor_var)
        vendor_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=4)
        ttk.Label(
            form,
            text="Folder + URL slug. Letters/digits only — spaces get stripped. Example: AlfaRecruit → sid.rocks/AlfaRecruit",
            foreground="#777", font=("Helvetica", 11),
        ).grid(row=1, column=1, sticky="w", padx=(8, 0))

        # Display name — pretty, human-facing version. Auto-fills from Vendor
        # name (with spaces kept) until the user edits it manually.
        ttk.Label(form, text="Display name").grid(row=2, column=0, sticky="w", pady=(12, 4))
        display_entry = ttk.Entry(form, textvariable=self.display_var)
        display_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=(12, 4))
        ttk.Label(
            form,
            text="Shown on the portal <h1>, <title>, and in the vendor guide. Can have spaces. Example: 'Alfa Recruit'.",
            foreground="#777", font=("Helvetica", 11),
        ).grid(row=3, column=1, sticky="w", padx=(8, 0))

        # Auto-fill Display name from Vendor name as the user types, unless
        # they've manually edited Display name — then leave their edit alone.
        def _on_vendor_type(*_args: object) -> None:
            if not self._display_edited_by_user:
                self.display_var.set(self.vendor_var.get())
        self.vendor_var.trace_add("write", _on_vendor_type)

        def _on_display_edit(_event: object) -> None:
            # Any keystroke in the Display entry counts as manual editing.
            self._display_edited_by_user = True
        display_entry.bind("<Key>", _on_display_edit)

        # OneDrive URL label row — label on left, "How do I get this?" help link on right
        url_label_row = ttk.Frame(form)
        url_label_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 4))
        url_label_row.columnconfigure(1, weight=1)
        ttk.Label(url_label_row, text="OneDrive upload URL").grid(
            row=0, column=0, sticky="w"
        )
        help_link = tk.Label(
            url_label_row,
            text="How do I get this?",
            font=("Helvetica", 11, "underline"),
            fg="#6a4d9a", cursor="hand2",
            bg=self.cget("background"),
        )
        help_link.grid(row=0, column=1, sticky="e")
        help_link.bind("<Button-1>", lambda _e: self._show_onedrive_help())

        ttk.Entry(form, textvariable=self.upload_var).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(0, 4)
        )
        self.upload_hint = ttk.Label(
            form,
            text="Paste the SharePoint/OneDrive folder share link for this vendor's uploads.",
            foreground="#777", font=("Helvetica", 11),
        )
        self.upload_hint.grid(row=6, column=0, columnspan=2, sticky="w")

        # Mode
        mode_box = ttk.LabelFrame(self, text="What do you want to do?")
        mode_box.pack(fill="x", **pad)
        ttk.Radiobutton(
            mode_box,
            text="Create new vendor — Download SID   (installs from bundled SID.zip)",
            variable=self.mode_var, value="download",
            command=self._on_mode_change,
        ).pack(anchor="w", padx=10, pady=(6, 2))
        ttk.Radiobutton(
            mode_box,
            text="Create new vendor — Chrome Web Store preview   (new folder, different URL)",
            variable=self.mode_var, value="webstore_new",
            command=self._on_mode_change,
        ).pack(anchor="w", padx=10, pady=(2, 2))
        ttk.Radiobutton(
            mode_box,
            text="Switch existing vendor — Chrome Web Store   (same URL, flips install flow)",
            variable=self.mode_var, value="webstore_switch",
            command=self._on_mode_change,
        ).pack(anchor="w", padx=10, pady=(2, 2))
        ttk.Radiobutton(
            mode_box,
            text="Switch existing vendor — Download SID   (revert an existing vendor)",
            variable=self.mode_var, value="download_switch",
            command=self._on_mode_change,
        ).pack(anchor="w", padx=10, pady=(2, 8))

        # Options
        opts = ttk.Frame(self)
        opts.pack(fill="x", **pad)
        ttk.Checkbutton(
            opts,
            text="Auto-push to GitHub after the change",
            variable=self.push_var,
        ).pack(anchor="w")

        # Buttons
        btns = ttk.Frame(self)
        btns.pack(fill="x", **pad)
        self.go_btn = ttk.Button(
            btns, text="Spawn Vendor Page", command=self._on_spawn
        )
        self.go_btn.pack(side="left")
        ttk.Button(btns, text="Open SID folder", command=self._open_root).pack(
            side="left", padx=(10, 0)
        )
        ttk.Button(
            btns, text="Update SID.zip…", command=self._on_update_zip
        ).pack(side="left", padx=(10, 0))
        ttk.Button(btns, text="Clear log", command=self._clear_log).pack(
            side="right"
        )

        # Log pane
        log_frame = ttk.LabelFrame(self, text="Activity")
        log_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.log = scrolledtext.ScrolledText(
            log_frame, height=14, wrap="word",
            font=("Menlo", 11),
        )
        self.log.pack(fill="both", expand=True, padx=6, pady=6)
        self.log.configure(state="disabled")

    # --- log helpers -----------------------------------------------

    def _log_line(self, msg: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # --- actions ---------------------------------------------------

    def _open_root(self) -> None:
        subprocess.Popen(["open", str(sid_root())])

    def _show_onedrive_help(self) -> None:
        """Popup explaining how to create a per-vendor OneDrive File Request link.

        Vendor uploads use OneDrive's "Request files" feature, which gives the
        vendor an upload-only link — they can drop files in but can't see or
        modify anything already in the folder. This dialog walks through how
        to generate that link for a new vendor.
        """
        win = tk.Toplevel(self)
        win.title("How to Get the OneDrive Upload Link")
        win.configure(bg="#ffffff")
        win.geometry("540x520")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        tk.Label(
            win,
            text="Getting the OneDrive Upload Link",
            font=("Helvetica", 16, "bold"),
            bg="#ffffff", fg="#6a4d9a",
            wraplength=500,
        ).pack(padx=20, pady=(20, 6))

        tk.Label(
            win,
            text="Uses OneDrive's \"Request files\" feature — upload-only, "
                 "so vendors can't see what's already in the folder.",
            font=("Helvetica", 11),
            bg="#ffffff", fg="#666",
            wraplength=500, justify="center",
        ).pack(padx=20, pady=(0, 14))

        steps = (
            "1.  Go to onedrive.live.com (or your SharePoint) and open\n"
            "     the SID Vendor Uploads folder.\n\n"
            "2.  Click  + New  →  Folder  and name it the vendor's\n"
            "     name (e.g. \"FBSPL\").\n\n"
            "3.  Right-click the new folder → Request files\n"
            "     (or select it and click Request files in the toolbar).\n\n"
            "4.  Enter a short description (e.g. \"SID uploads for\n"
            "     [Vendor Name]\") and click Next.\n\n"
            "5.  Click Copy link.\n"
            "     (In Manage Access you'll see the link with\n"
            "     \"Anyone with the file request link can upload only\"\n"
            "     — that's the correct setting.)\n\n"
            "6.  Paste that link into the OneDrive Upload URL field\n"
            "     in this app — done!"
        )

        text_frame = tk.Frame(
            win, bg="#f8f6fc",
            highlightbackground="#d9d1ea", highlightthickness=1, bd=0,
        )
        text_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        tk.Label(
            text_frame, text=steps,
            font=("Helvetica", 12),
            bg="#f8f6fc", fg="#222",
            justify="left", anchor="nw", wraplength=460,
        ).pack(padx=16, pady=16, fill="both", expand=True)

        ttk.Button(win, text="Got it", command=win.destroy).pack(
            fill="x", padx=20, pady=(0, 20)
        )

    def _on_mode_change(self) -> None:
        """Refresh the primary button label + hints based on the selected mode."""
        mode = self.mode_var.get()
        if mode == "download":
            self.go_btn.configure(text="Spawn Vendor Page")
            self.upload_hint.configure(
                text="Paste the SharePoint/OneDrive folder share link for this "
                     "vendor's uploads.",
            )
        elif mode == "webstore_new":
            self.go_btn.configure(text="Spawn Preview Page")
            self.upload_hint.configure(
                text="Paste the OneDrive upload link. Use a distinct vendor "
                     "name (e.g. FBSPL-preview) so the real URL isn't touched.",
            )
        elif mode == "webstore_switch":
            self.go_btn.configure(text="Switch to Chrome Web Store")
            self.upload_hint.configure(
                text="Optional — leave blank to keep the vendor's existing "
                     "upload link. The URL sid.rocks/<vendor> is unchanged.",
            )
        elif mode == "download_switch":
            self.go_btn.configure(text="Switch back to Download SID")
            self.upload_hint.configure(
                text="Optional — leave blank to keep the vendor's existing "
                     "upload link. The URL sid.rocks/<vendor> is unchanged.",
            )

    def _on_spawn(self) -> None:
        vendor = sanitize_folder_name(self.vendor_var.get())
        display = self.display_var.get().strip() or vendor
        upload = self.upload_var.get().strip()
        mode = self.mode_var.get()
        push = self.push_var.get()

        if not vendor:
            messagebox.showerror("Missing vendor name", "Please enter a vendor name.")
            return

        is_switch = mode in ("webstore_switch", "download_switch")

        # Upload URL is required only when creating a new vendor; switching a
        # vendor in place preserves the existing URL unless the user supplies one.
        if not is_switch and not upload:
            messagebox.showerror(
                "Missing upload URL",
                "Please paste the OneDrive/SharePoint upload link.",
            )
            return
        if upload and not upload.lower().startswith("http"):
            messagebox.showerror(
                "Bad upload URL", "Upload URL should start with http(s)://"
            )
            return

        if vendor != self.vendor_var.get().strip():
            if not messagebox.askyesno(
                "Sanitize name?",
                f"Vendor name will be saved as '{vendor}'. Continue?",
            ):
                return

        # Extra guard for destructive in-place switches
        if is_switch:
            target_label = (
                "Chrome Web Store" if mode == "webstore_switch" else "Download SID"
            )
            if not messagebox.askyesno(
                "Confirm switch",
                f"Rewrite sid.rocks/{vendor} to {target_label} install mode?\n\n"
                f"This rewrites index.html, guide.html, and guide_direct.html "
                f"in the {vendor}/ folder. The URL doesn't change.",
            ):
                return

        self.go_btn.configure(state="disabled")
        t = threading.Thread(
            target=self._spawn_worker,
            args=(vendor, display, upload, mode, push),
            daemon=True,
        )
        t.start()

    def _spawn_worker(
        self,
        vendor: str,
        display: str,
        upload: str,
        mode: str,
        push: bool,
    ) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")

        # Map the UI mode onto the underlying install-mode string + action
        if mode == "download":
            install_mode, is_switch = "download", False
        elif mode == "webstore_new":
            install_mode, is_switch = "webstore", False
        elif mode == "webstore_switch":
            install_mode, is_switch = "webstore", True
        elif mode == "download_switch":
            install_mode, is_switch = "download", True
        else:
            self._log_line(f"✗ unknown mode: {mode}")
            self.go_btn.configure(state="normal")
            return

        verb = "Switching" if is_switch else "Spawning"
        self._log_line(
            f"[{stamp}] {verb} '{vendor}' ({install_mode} install mode)…"
        )
        try:
            root = sid_root()
            if is_switch:
                dest = switch_vendor_mode(
                    root, vendor, install_mode, upload, self._log_line,
                    display_name=display,
                )
                self._log_line(f"  ✓ {dest} re-wired")
            else:
                dest = spawn_vendor(
                    root, vendor, upload, install_mode, self._log_line,
                    display_name=display,
                )
                self._log_line(f"  ✓ vendor folder ready: {dest}")

            if push:
                action = "switch" if is_switch else "add"
                ok = git_push(
                    root, vendor, install_mode, self._log_line, action=action
                )
                if ok:
                    self._log_line("")
                    self._log_line(f"✅ Live soon at https://sid.rocks/{vendor}")
                else:
                    self._log_line("")
                    self._log_line(
                        "⚠ Files updated but git push failed. Fix the error above "
                        "and run `git push` from Terminal to finish."
                    )
            else:
                self._log_line("")
                if is_switch:
                    self._log_line(
                        f"Files updated. To publish, run:\n"
                        f"  cd \"{root}\" && git add {vendor}/ && "
                        f"git commit -m 'Switch {vendor} install mode' && git push"
                    )
                else:
                    self._log_line(
                        f"Files created. To publish, run:\n"
                        f"  cd \"{root}\" && git add {vendor}/ && "
                        f"git commit -m 'Add {vendor} vendor portal' && git push"
                    )
        except Exception as e:  # noqa: BLE001
            self._log_line(f"✗ {type(e).__name__}: {e}")
            messagebox.showerror("Operation failed", str(e))
        finally:
            self.go_btn.configure(state="normal")
            self._log_line("")

    def _on_update_zip(self) -> None:
        """Pick a new SID.zip and distribute it to every Download-mode vendor."""
        path_str = filedialog.askopenfilename(
            title="Choose the new SID.zip",
            filetypes=[("ZIP archives", "*.zip"), ("All files", "*.*")],
            initialdir=str(sid_root()),
        )
        if not path_str:
            return
        new_zip = Path(path_str)

        if not messagebox.askyesno(
            "Update SID.zip everywhere?",
            f"Replace SID.zip in the template and every Download-mode vendor "
            f"folder with:\n\n  {new_zip.name}\n  ({new_zip.stat().st_size:,} bytes)"
            f"\n\nVendors already switched to Chrome Web Store mode will be "
            f"skipped.",
        ):
            return

        push = self.push_var.get()
        self.go_btn.configure(state="disabled")

        def worker() -> None:
            stamp = datetime.now().strftime("%H:%M:%S")
            self._log_line(f"[{stamp}] Updating SID.zip from {new_zip} …")
            try:
                root = sid_root()
                count = update_sid_zip(root, new_zip, self._log_line)
                if push and count > 0:
                    ok = git_push(
                        root, "", "download", self._log_line, action="update"
                    )
                    if ok:
                        self._log_line("")
                        self._log_line("✅ SID.zip update pushed to sid.rocks.")
                    else:
                        self._log_line("")
                        self._log_line(
                            "⚠ SID.zip copied but git push failed. Fix the "
                            "error above and run `git push` from Terminal."
                        )
                elif not push and count > 0:
                    self._log_line("")
                    self._log_line(
                        f"SID.zip updated in {count} folder(s). To publish, run:\n"
                        f"  cd \"{root}\" && git add . && "
                        f"git commit -m 'Update bundled SID.zip' && git push"
                    )
            except Exception as e:  # noqa: BLE001
                self._log_line(f"✗ {type(e).__name__}: {e}")
                messagebox.showerror("Update failed", str(e))
            finally:
                self.go_btn.configure(state="normal")
                self._log_line("")

        threading.Thread(target=worker, daemon=True).start()


# ─────────────────────────── main ───────────────────────────────── #

def main() -> None:
    # Fail fast if we are not inside an SID repo
    root = sid_root()
    if not (root / TEMPLATE_VENDOR).is_dir():
        # Fall back to a tiny error window so the user can see what's wrong
        err = tk.Tk()
        err.title("SID Vendor Spawner")
        tk.Label(
            err,
            text=(
                f"Could not find {TEMPLATE_VENDOR}/ inside:\n{root}\n\n"
                "Move this app into the SID repo folder so it sits next to the\n"
                f"{TEMPLATE_VENDOR} folder, then launch it again."
            ),
            padx=20, pady=20, justify="left",
        ).pack()
        err.mainloop()
        sys.exit(1)

    app = SpawnerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
