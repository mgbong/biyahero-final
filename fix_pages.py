"""
fix_pages.py
─────────────
For every HTML page in the html/ folder:
  1. Replace all btn-logout href="login.html" → href="#"
  2. Add <script src="../js/user.js"> before </body> if not already present.
  3. Replace hardcoded user-avatar initials and user-name text with neutral placeholders.

Run once:  python fix_pages.py
"""
import os, re

HTML_DIR = os.path.join(os.path.dirname(__file__), "html")

SKIP = {
    "login.html", "signup.html", "commuter-signup.html",
    "driver-signup.html", "driver-signup-vehicle.html",
    "driver-signup-documents.html", "operator-signup.html",
    "pending-approval.html", "declined.html",
}

changed = []

for fname in os.listdir(HTML_DIR):
    if not fname.endswith(".html"):
        continue
    if fname in SKIP:
        continue

    path = os.path.join(HTML_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    original = html

    # 1. Fix logout href
    html = re.sub(
        r'class="btn-logout"\s+href="login\.html"',
        'class="btn-logout" href="#"',
        html
    )

    # 2. Add user.js if not already there
    if "user.js" not in html:
        html = html.replace("</body>", '  <script src="../js/user.js" defer></script>\n</body>', 1)

    # 3. Replace hardcoded user-avatar initials (MC, JS, AR, etc.)
    html = re.sub(
        r'(<div class="user-avatar">)[^<]+(</div>)',
        r'\1??\2',
        html
    )
    # 4. Replace hardcoded user-name text
    html = re.sub(
        r'(<span class="user-name">)[^<]+(</span>)',
        r'\1Loading…\2',
        html
    )

    if html != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        changed.append(fname)

print(f"\nFixed {len(changed)} files:")
for f in sorted(changed):
    print(f"  • {f}")
print()
