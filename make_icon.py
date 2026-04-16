#!/usr/bin/env python3
"""Generate polished SID icon for Chrome Web Store (128x128)."""
import cairosvg
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# SID face on a soft purple circular background with subtle shadow
icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#9b7ed8"/>
      <stop offset="100%" style="stop-color:#7860a8"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.15"/>
    </filter>
  </defs>
  <!-- Background rounded square -->
  <rect width="128" height="128" rx="28" ry="28" fill="url(#bg)"/>
  
  <!-- SID face, centered and scaled -->
  <g transform="translate(14,10) scale(1.0)">
    <!-- Hair tufts -->
    <path d="M38 12Q36 2 32 5Q34 10 38 14Z" fill="#7a5c3a"/>
    <path d="M50 8Q50-2 46 2Q48 7 50 12Z" fill="#7a5c3a"/>
    <path d="M62 12Q64 2 68 5Q66 10 62 14Z" fill="#7a5c3a"/>
    <!-- Head -->
    <ellipse cx="50" cy="52" rx="38" ry="40" fill="#d4a96a"/>
    <!-- Face inner -->
    <ellipse cx="50" cy="58" rx="28" ry="28" fill="#e8c88a"/>
    <!-- Eyes whites -->
    <ellipse cx="38" cy="46" rx="10" ry="11" fill="white"/>
    <ellipse cx="62" cy="46" rx="10" ry="11" fill="white"/>
    <!-- Irises -->
    <circle cx="39" cy="46" r="6" fill="#3b8ed0"/>
    <circle cx="63" cy="46" r="6" fill="#3b8ed0"/>
    <!-- Pupils -->
    <circle cx="40" cy="45" r="3" fill="#1a1a2e"/>
    <circle cx="64" cy="45" r="3" fill="#1a1a2e"/>
    <!-- Eye highlights -->
    <circle cx="41" cy="43" r="1.5" fill="white"/>
    <circle cx="65" cy="43" r="1.5" fill="white"/>
    <!-- Nose -->
    <ellipse cx="50" cy="60" rx="8" ry="6" fill="#8b6baa"/>
    <!-- Smile -->
    <path d="M43 68Q50 76 57 68" stroke="#7a5c3a" stroke-width="2" fill="none" stroke-linecap="round"/>
    <!-- Ears -->
    <ellipse cx="18" cy="38" rx="8" ry="10" fill="#d4a96a"/>
    <ellipse cx="82" cy="38" rx="8" ry="10" fill="#d4a96a"/>
  </g>
</svg>'''

# Generate 128x128 PNG
out_path = os.path.join(SCRIPT_DIR, "sid_icon_128.png")
cairosvg.svg2png(bytestring=icon_svg.encode(), write_to=out_path, output_width=128, output_height=128)
print(f"Created {out_path}")

# Also generate 48x48 and 16x16 for the extension itself
for size in [48, 16]:
    out = os.path.join(SCRIPT_DIR, f"sid_icon_{size}.png")
    cairosvg.svg2png(bytestring=icon_svg.encode(), write_to=out, output_width=size, output_height=size)
    print(f"Created {out}")
