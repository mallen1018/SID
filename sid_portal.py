#!/usr/bin/env python3
"""
SID portal manager — create & manage vendor portals, then deploy to Cloudflare.

Commands:
  add "Display Name" folder "UPLOAD_URL" [--mode webstore|download|both]
        Create a new vendor portal (cloned from the fbspl template).
        Default mode is webstore.

  mode folder webstore|download|both
        Switch an existing portal's install mode (the "swap" — e.g. flip every
        portal to download while the Chrome Web Store is still catching up).

  mode-all webstore|download|both
        Switch ALL portals at once.

  update-zip
        Copy the latest SID extension zip into every download/both portal.

  deploy
        Rebuild public/ and deploy the Worker to sid.wsjshortlist.com.

  list
        Show every portal and its current mode.

Typical flow when the web store lags behind a fix:
  python3 sid_portal.py update-zip
  python3 sid_portal.py mode-all both
  python3 sid_portal.py deploy
"""
import os, re, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
TPL_DIR = os.path.join(ROOT, "_portal_templates")
BASE = os.path.join(ROOT, "fbspl", "index.html")          # canonical modern portal
CF_DIR = "/Users/melissaallen/Documents/sid-portals-cf"
LATEST_ZIP = "/Users/melissaallen/Documents/WSJCSVs/SID_Extension/SID_v5.8.13.zip"
WEBSTORE_URL = "https://chromewebstore.google.com/detail/oaejdaekhegedlgoanfkogmoiceelkbc"

FBSPL_UPLOAD = ("https://jobosaurus-my.sharepoint.com/:f:/g/personal/"
                "mallen_wallstjobs_com/IgAQAkLWz04gQIx-W-6lgkeSAXisYkAu9c0UU_1ieyVdsgI")

MODES = ("webstore", "download", "both")
BTN_RE = re.compile(r'<a [^>]*id="installBtn"[^>]*>.*?</a>', re.DOTALL)
MODAL_RE = re.compile(r'<!-- Install Instructions Modal -->.*?(?=<!-- Footer -->)', re.DOTALL)
MODE_TAG_RE = re.compile(r'<!-- SID_MODE: (\w+) -->')


def _frag(name):
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as f:
        return f.read()


def install_button(mode):
    if mode == "webstore":
        return (f'<a href="{WEBSTORE_URL}" target="_blank" id="installBtn" '
                f'class="action install" onclick="handleInstallClick(event);">\n'
                f'    Install SID Extension\n  </a>')
    # download + both both lead with the direct-download button
    return ('<a href="SID.zip" download id="installBtn" '
            'class="action install" onclick="handleInstallClick(event);">\n'
            '    Download SID Extension\n  </a>')


def install_modal(mode):
    if mode == "webstore":
        return _frag("modal_webstore.html").rstrip("\n") + "\n"
    modal = _frag("modal_download.html").rstrip("\n")
    if mode == "both":
        # add a web-store alternative line just under the modal subtitle
        note = (f'    <div class="modal-subtitle">Prefer the Chrome Web Store? '
                f'<a href="{WEBSTORE_URL}" target="_blank" style="color:#7860a8;font-weight:600">'
                f'Install it here</a> instead.</div>')
        modal = modal.replace("</div>\n", "</div>\n" + note + "\n", 1)
    return modal + "\n"


def set_mode(html, mode):
    """Swap the install button + modal + mode tag in a portal's HTML."""
    if not BTN_RE.search(html):
        raise ValueError("install button not found")
    if not MODAL_RE.search(html):
        raise ValueError("install modal not found")
    html = BTN_RE.sub(lambda m: install_button(mode), html, count=1)
    html = MODAL_RE.sub(lambda m: install_modal(mode), html, count=1)
    tag = f"<!-- SID_MODE: {mode} -->"
    if MODE_TAG_RE.search(html):
        html = MODE_TAG_RE.sub(tag, html, count=1)
    else:
        html = html.replace("</head>", f"{tag}\n</head>", 1)
    return html


def current_mode(html):
    m = MODE_TAG_RE.search(html)
    if m:
        return m.group(1)
    # infer from the button if untagged
    btn = BTN_RE.search(html)
    if btn and "chromewebstore" in btn.group(0):
        return "webstore"
    if btn and 'href="SID.zip"' in btn.group(0):
        return "download"
    return "unknown"


def portals():
    return sorted(d for d in os.listdir(ROOT)
                  if not d.startswith(".")
                  and os.path.isfile(os.path.join(ROOT, d, "index.html")))


def cmd_add(args):
    if len(args) < 3:
        sys.exit('usage: add "Display Name" folder "UPLOAD_URL" [--mode webstore|download|both]')
    display, folder, upload = args[0], args[1], args[2]
    mode = "webstore"
    if "--mode" in args:
        mode = args[args.index("--mode") + 1]
    if mode not in MODES:
        sys.exit(f"mode must be one of {MODES}")
    out_dir = os.path.join(ROOT, folder)
    if os.path.exists(os.path.join(out_dir, "index.html")):
        sys.exit(f"{folder}/index.html already exists — use `mode` to change it")

    html = open(BASE, encoding="utf-8").read()
    html = html.replace("<title>FBSPL - SID Vendor Portal</title>",
                        f"<title>{display} - SID Vendor Portal</title>")
    html = html.replace("<h1>FBSPL</h1>", f"<h1>{display}</h1>")
    html = html.replace("sid_checklist_fbspl", f"sid_checklist_{folder}")
    html = html.replace("sid_tasks_fbspl_", f"sid_tasks_{folder}_")
    # point data fetches at the current host (works on any domain)
    html = html.replace("https://sid.rocks/bulletin_fbspl.json", f"/bulletin_{folder}.json")
    html = html.replace("https://sid.rocks/announcements.json", "/announcements.json")
    html = html.replace(FBSPL_UPLOAD, upload)
    html = set_mode(html, mode)
    assert "fbspl" not in html.lower(), "FBSPL residue — aborting"

    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(html)
    # guide + zip
    shutil.copyfile(os.path.join(ROOT, "fbspl", "guide_direct.html"),
                    os.path.join(out_dir, "guide_direct.html"))
    if mode in ("download", "both") and os.path.exists(LATEST_ZIP):
        shutil.copyfile(LATEST_ZIP, os.path.join(out_dir, "SID.zip"))
    open(os.path.join(ROOT, f"bulletin_{folder}.json"), "a").close()  # empty bulletin ok
    print(f"Created {folder}/ (mode={mode}, name='{display}')")
    print("Next: python3 sid_portal.py deploy")


def cmd_mode(args):
    if len(args) != 2 or args[1] not in MODES:
        sys.exit("usage: mode folder webstore|download|both")
    folder, mode = args
    path = os.path.join(ROOT, folder, "index.html")
    if not os.path.exists(path):
        sys.exit(f"no portal at {folder}/")
    html = set_mode(open(path, encoding="utf-8").read(), mode)
    if mode in ("download", "both") and os.path.exists(LATEST_ZIP):
        shutil.copyfile(LATEST_ZIP, os.path.join(ROOT, folder, "SID.zip"))
    open(path, "w", encoding="utf-8").write(html)
    print(f"{folder} -> {mode}")


def cmd_mode_all(args):
    if len(args) != 1 or args[0] not in MODES:
        sys.exit("usage: mode-all webstore|download|both")
    mode = args[0]
    done, skipped = [], []
    for folder in portals():
        try:
            cmd_mode([folder, mode]); done.append(folder)
        except Exception as e:
            skipped.append(f"{folder} ({e})")
    print(f"\nflipped {len(done)} to {mode}; skipped {len(skipped)}: {skipped or 'none'}")


def cmd_update_zip(args):
    if not os.path.exists(LATEST_ZIP):
        sys.exit(f"missing {LATEST_ZIP}")
    n = 0
    for folder in portals():
        html = open(os.path.join(ROOT, folder, "index.html"), encoding="utf-8").read()
        if current_mode(html) in ("download", "both"):
            shutil.copyfile(LATEST_ZIP, os.path.join(ROOT, folder, "SID.zip"))
            n += 1
    print(f"Refreshed SID.zip in {n} download/both portals from {os.path.basename(LATEST_ZIP)}")


def cmd_list(args):
    for folder in portals():
        html = open(os.path.join(ROOT, folder, "index.html"), encoding="utf-8").read()
        name = (re.search(r"<h1>([^<]*)</h1>", html) or [None, "?"])[1]
        print(f"  {folder:22} {current_mode(html):9} {name}")


def cmd_deploy(args):
    subprocess.run(["bash", os.path.join(CF_DIR, "build.sh")], check=True)
    subprocess.run(["npx", "wrangler", "deploy"], cwd=CF_DIR, check=True)
    print("Deployed to https://sid.wsjshortlist.com")


CMDS = {"add": cmd_add, "mode": cmd_mode, "mode-all": cmd_mode_all,
        "update-zip": cmd_update_zip, "list": cmd_list, "deploy": cmd_deploy}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        sys.exit(1)
    CMDS[sys.argv[1]](sys.argv[2:])
