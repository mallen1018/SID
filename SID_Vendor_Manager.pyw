#!/usr/bin/env python3
"""SID Vendor Manager — GUI for adding and removing vendor portals."""

import tkinter as tk
from tkinter import messagebox
import os
import subprocess
import shutil
import re

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


def generate_portal(display_name, folder_name, upload_url):
    portal_url = f"https://sid.rocks/{folder_name}"
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
  * {{{{ box-sizing: border-box; margin: 0; padding: 0; }}}}
  body {{{{
    font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
    color: #1a1a2e; line-height: 1.6; background: #fff;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(160deg, #faf8fd 0%, #f0ecf6 30%, #e8f0fa 70%, #f8fafc 100%);
    padding: 40px 20px;
  }}}}
  a {{{{ text-decoration: none; color: inherit; }}}}
  .card {{{{
    background: #fff; border-radius: 24px; padding: 48px 40px;
    max-width: 480px; width: 100%; text-align: center;
    box-shadow: 0 8px 40px rgba(120,96,168,0.10), 0 2px 12px rgba(0,0,0,0.04);
    border: 1px solid #ece8f4;
  }}}}
  .sid-face {{{{ margin-bottom: 20px; }}}}
  .welcome {{{{ font-size: 13px; color: #9b7ed8; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }}}}
  h1 {{{{ font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; letter-spacing: 0.04em; }}}}
  .subtitle {{{{ font-size: 15px; color: #64748b; margin-bottom: 36px; line-height: 1.7; }}}}
  .action {{{{
    display: block; width: 100%; padding: 16px 24px; border-radius: 14px;
    font-size: 14px; font-weight: 700; font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.5px; transition: all 0.2s; cursor: pointer;
    border: none; margin-bottom: 14px;
  }}}}
  .action.upload {{{{ background: linear-gradient(135deg, #78cca0, #64bc90); color: #fff; }}}}
  .action.upload:hover {{{{ box-shadow: 0 6px 24px rgba(120,204,160,0.35); transform: translateY(-2px); }}}}
  .action.guide {{{{ background: linear-gradient(135deg, #9b7ed8, #b89ae8); color: #fff; }}}}
  .action.guide:hover {{{{ box-shadow: 0 6px 24px rgba(155,126,216,0.35); transform: translateY(-2px); }}}}
  .action.install {{{{ background: linear-gradient(135deg, #6a9cd8, #5b8dcf); color: #fff; }}}}
  .action.install:hover {{{{ box-shadow: 0 6px 24px rgba(106,156,216,0.35); transform: translateY(-2px); }}}}
  .divider {{{{ height: 1px; background: #ece8f4; margin: 24px 0; }}}}
  .help-text {{{{ font-size: 13px; color: #94a3b8; line-height: 1.7; }}}}
  .help-text a {{{{ color: #7860a8; font-weight: 600; }}}}
  .footer {{{{ margin-top: 32px; font-size: 12px; color: #b0a8c0; }}}}
  .footer a {{{{ color: #9b7ed8; font-weight: 600; }}}}
</style>
</head>
<body>
  <div class="card">
    <div class="sid-face">
      <svg width="64" height="64" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <path d="M38 12Q36 2 32 5Q34 10 38 14Z" fill="#7a5c3a"/><path d="M50 8Q50-2 46 2Q48 7 50 12Z" fill="#7a5c3a"/><path d="M62 12Q64 2 68 5Q66 10 62 14Z" fill="#7a5c3a"/>
        <ellipse cx="50" cy="52" rx="38" ry="40" fill="#d4a96a"/><ellipse cx="50" cy="58" rx="28" ry="28" fill="#e8c88a"/>
        <ellipse cx="38" cy="46" rx="10" ry="11" fill="white"/><ellipse cx="62" cy="46" rx="10" ry="11" fill="white"/>
        <circle cx="39" cy="46" r="6" fill="#3b8ed0"/><circle cx="63" cy="46" r="6" fill="#3b8ed0"/>
        <circle cx="40" cy="45" r="3" fill="#1a1a2e"/><circle cx="64" cy="45" r="3" fill="#1a1a2e"/>
        <circle cx="41" cy="43" r="1.5" fill="white"/><circle cx="65" cy="43" r="1.5" fill="white"/>
        <ellipse cx="50" cy="60" rx="8" ry="6" fill="#8b6baa"/>
        <path d="M43 68Q50 76 57 68" stroke="#7a5c3a" stroke-width="2" fill="none" stroke-linecap="round"/>
        <ellipse cx="18" cy="38" rx="8" ry="10" fill="#d4a96a"/><ellipse cx="82" cy="38" rx="8" ry="10" fill="#d4a96a"/>
      </svg>
    </div>
    <div class="welcome">Welcome</div>
    <h1>{display_name}</h1>
    <p class="subtitle">Your SID vendor portal. Install the extension, read the guide, and upload your files.</p>
    <a href="#" class="action install" onclick="alert('Chrome Web Store link coming soon!');return false;">
      Install SID Extension
    </a>
    <a href="{portal_url}/guide.html" target="_blank" class="action guide">
      Open SID Guide
    </a>
    <a href="{upload_url}" target="_blank" class="action upload">
      Upload ZIP Files
    </a>
    <div class="divider"></div>
    <p class="help-text">
      No sign-in needed to upload. Just click, select your ZIP file, and you're done.<br>
      Questions? Email <a href="mailto:mallen@wallstjobs.com">Melissa</a>.
    </p>
  </div>
  <div class="footer">Powered by <a href="https://sid.rocks">sid.rocks</a></div>
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


def git_push(display_name, action="Add"):
    try:
        os.chdir(SCRIPT_DIR)
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
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
        self.geometry("540x620")
        self.resizable(False, False)

        # ── Header ──
        header = tk.Frame(self, bg=PURPLE, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="SID Vendor Manager", font=("Helvetica Neue", 18, "bold"),
                 bg=PURPLE, fg="white").pack(side="left", padx=20)

        # ── Main content ──
        main = tk.Frame(self, bg=BG, padx=24, pady=20)
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
        del_btn.pack(fill="x", pady=(0, 20))

        # --- Separator ---
        tk.Frame(main, bg=BORDER, height=1).pack(fill="x", pady=(0, 16))

        # --- Add new vendor (simplified: just name + URL) ---
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

        # ── Status bar ──
        self.status = tk.Label(self, text="Ready", font=("Helvetica Neue", 11),
                                bg="#e8e4ef", fg=GRAY, anchor="w", padx=16, pady=6)
        self.status.pack(fill="x", side="bottom")

    def refresh_list(self):
        self.vendor_list.delete(0, tk.END)
        for folder, display in get_vendors():
            if display != folder:
                self.vendor_list.insert(tk.END, f"  {display}  ({folder})")
            else:
                self.vendor_list.insert(tk.END, f"  {folder}")

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
        ok, msg = git_push(name, "Add")

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
        self.name_entry.delete(0, tk.END)
        self.url_entry.delete(0, tk.END)

    def remove_vendor(self):
        sel = self.vendor_list.curselection()
        if not sel:
            messagebox.showinfo("No Selection", "Click on a vendor in the list first.")
            return

        text = self.vendor_list.get(sel[0]).strip()
        # Extract folder name from display text
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


if __name__ == "__main__":
    app = App()
    app.mainloop()
