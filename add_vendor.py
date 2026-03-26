#!/usr/bin/env python3
"""
Add a new SID vendor portal + personalized guide.

Usage:
    python3 add_vendor.py "Vendor Display Name" "FolderName" "OneDrive_Upload_URL"

Example:
    python3 add_vendor.py "Acme Corp" "AcmeCorp" "https://jobosaurus-my.sharepoint.com/:f:/g/personal/mallen_wallstjobs_com/xxxxx"

This creates:
    FolderName/index.html  — vendor portal page (install, guide, upload buttons)
    FolderName/guide.html  — personalized SOP guide

Then just push to GitHub:
    cd /path/to/SID
    git add FolderName/
    git commit -m "Add vendor portal for Vendor Display Name"
    git push
"""

import sys
import os

if len(sys.argv) != 4:
    print(__doc__)
    sys.exit(1)

display_name = sys.argv[1]
folder_name = sys.argv[2]
upload_url = sys.argv[3]
portal_url = f"https://sid.rocks/{folder_name}"
script_dir = os.path.dirname(os.path.abspath(__file__))

# ─── Portal page (index.html) ───
portal_html = f'''<!DOCTYPE html>
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
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
    color: #1a1a2e; line-height: 1.6; background: #fff;
    -webkit-font-smoothing: antialiased;
    min-height: 100vh;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: linear-gradient(160deg, #faf8fd 0%, #f0ecf6 30%, #e8f0fa 70%, #f8fafc 100%);
    padding: 40px 20px;
  }}
  a {{ text-decoration: none; color: inherit; }}

  .card {{
    background: #fff; border-radius: 24px; padding: 48px 40px;
    max-width: 480px; width: 100%; text-align: center;
    box-shadow: 0 8px 40px rgba(120,96,168,0.10), 0 2px 12px rgba(0,0,0,0.04);
    border: 1px solid #ece8f4;
  }}
  .sid-face {{ margin-bottom: 20px; }}
  .welcome {{ font-size: 13px; color: #9b7ed8; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }}
  h1 {{
    font-family: 'Outfit', sans-serif; font-size: 28px; font-weight: 700;
    color: #1a1a2e; margin-bottom: 8px; letter-spacing: 0.04em;
  }}
  .subtitle {{ font-size: 15px; color: #64748b; margin-bottom: 36px; line-height: 1.7; }}

  .action {{
    display: block; width: 100%; padding: 16px 24px; border-radius: 14px;
    font-size: 14px; font-weight: 700; font-family: 'DM Sans', sans-serif;
    letter-spacing: 0.5px; transition: all 0.2s; cursor: pointer;
    border: none; margin-bottom: 14px;
  }}
  .action.upload {{
    background: linear-gradient(135deg, #78cca0, #64bc90); color: #fff;
  }}
  .action.upload:hover {{ box-shadow: 0 6px 24px rgba(120,204,160,0.35); transform: translateY(-2px); }}
  .action.guide {{
    background: linear-gradient(135deg, #9b7ed8, #b89ae8); color: #fff;
  }}
  .action.guide:hover {{ box-shadow: 0 6px 24px rgba(155,126,216,0.35); transform: translateY(-2px); }}
  .action.install {{
    background: linear-gradient(135deg, #6a9cd8, #5b8dcf); color: #fff;
  }}
  .action.install:hover {{ box-shadow: 0 6px 24px rgba(106,156,216,0.35); transform: translateY(-2px); }}

  .divider {{ height: 1px; background: #ece8f4; margin: 24px 0; }}

  .help-text {{ font-size: 13px; color: #94a3b8; line-height: 1.7; }}
  .help-text a {{ color: #7860a8; font-weight: 600; }}

  .footer {{ margin-top: 32px; font-size: 12px; color: #b0a8c0; }}
  .footer a {{ color: #9b7ed8; font-weight: 600; }}
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

# ─── Personalized guide (guide.html) ───
# Read the general SOP as the template
sop_path = os.path.join(script_dir, 'SID_Vendor_SOP.html')
with open(sop_path, 'r') as f:
    guide = f.read()

# Apply all personalizations
guide = guide.replace(
    '<title>SID - Smart Indeed Downloader | Vendor Guide</title>',
    f'<title>SID Vendor Guide - {display_name}</title>'
)
guide = guide.replace(
    '<p class="subtitle">Vendor Guide</p>',
    f'<p class="subtitle">Vendor Guide &mdash; {display_name}</p>'
)
guide = guide.replace(
    'upload the files using your personal upload link',
    f'upload the files on <a href="{portal_url}" style="color:#7860a8;">your portal page</a>'
)
guide = guide.replace(
    'Go to <strong><a href="https://sid.rocks" style="color:#7860a8;">sid.rocks</a></strong> and click the <strong>"Install SID"</strong> button to open the Chrome Web Store page in <strong>Google Chrome</strong> (or Microsoft Edge).',
    f'Go to <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong> and click the <strong>"Install SID Extension"</strong> button to open the Chrome Web Store page in <strong>Google Chrome</strong> (or Microsoft Edge).'
)
guide = guide.replace(
    'upload the files using their personal upload link',
    'upload the files on their portal page'
)
guide = guide.replace(
    '<strong>Upload the ZIP(s)</strong> &mdash; Open your personal upload link and upload your ZIP file. See Section 5 below.',
    f'<strong>Upload the ZIP(s)</strong> &mdash; Go to <a href="{portal_url}" style="color:#7860a8;">your portal page</a> and click <strong>&quot;Upload ZIP Files&quot;</strong>. See Section 5 below.'
)
guide = guide.replace(
    'After you download the ZIP file from SID, upload it the same day using the <strong>personal upload link Melissa gave you</strong>. This is a unique link for your uploads &mdash; bookmark it so you have it handy.',
    f'After you download the ZIP file from SID, upload it the same day through <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong>. Bookmark your portal so you have it handy.'
)
guide = guide.replace(
    'Open the <strong>upload link</strong> Melissa provided you (check your email if you don\'t have it saved).',
    f'Go to <strong><a href="{portal_url}" style="color:#7860a8;">your portal page</a></strong> and click <strong>&quot;Upload ZIP Files&quot;</strong>.'
)
guide = guide.replace(
    'Upload your ZIP file using your personal upload link by end of day.',
    f'Upload your ZIP file through <a href="{portal_url}" style="color:#7860a8;">your portal page</a> by end of day.'
)

# ─── Write files ───
out_dir = os.path.join(script_dir, folder_name)
os.makedirs(out_dir, exist_ok=True)

with open(os.path.join(out_dir, 'index.html'), 'w') as f:
    f.write(portal_html)

with open(os.path.join(out_dir, 'guide.html'), 'w') as f:
    f.write(guide)

print(f'Created {folder_name}/index.html (portal page)')
print(f'Created {folder_name}/guide.html (personalized guide)')
print(f'')
print(f'Live at: {portal_url}')
print(f'Guide:   {portal_url}/guide.html')
print(f'')
print(f'Next: git add {folder_name}/ && git commit -m "Add {display_name} vendor portal" && git push')
