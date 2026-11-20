#!/usr/bin/env python3
"""Static checks for the bpro icon refresh (runs without Odoo).

    python3 tools/icons/check_icons.py

  1. every `bpro_ic--<name>` used in a module's XML/JS exists in that
     module's generated kit, and the kit is listed in the module's assets;
  2. every kit turns motion off under prefers-reduced-motion;
  3. the files listed in icons.json "no_legacy" carry no FontAwesome or
     emoji/glyph icons any more;
  4. every app in icons.json has static/description/icon.svg + a 256x256
     icon.png, and every web_icon="module,path" points at a real file;
  5. every asset path in every bpro_* manifest exists.
Exit status 1 on any failure.
"""
import ast
import glob
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADDONS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "addons")
cfg = json.load(open(os.path.join(HERE, "icons.json"), encoding="utf-8"))
errors = []
LEGACY = re.compile(r"\bfa-[a-z]|[\U0001F300-\U0001FAFF☀-➿⭐⬆▲▼☰]")


def manifest(module):
    return ast.literal_eval(open(os.path.join(ADDONS, module, "__manifest__.py"), encoding="utf-8").read())


def asset_paths(man):
    for bundle in man.get("assets", {}).values():
        for item in bundle:
            path = item[-1] if isinstance(item, (list, tuple)) else item
            yield path


# 1 + 2: kits
kit_icons = {}
for module, kit in cfg.get("kits", {}).items():
    path = os.path.join(ADDONS, module, kit["path"])
    if not os.path.exists(path):
        errors.append(f"{module}: kit {kit['path']} missing (run build_icons.py)")
        continue
    scss = open(path, encoding="utf-8").read()
    kit_icons[module] = set(re.findall(r"\.bpro_ic--([a-z0-9-]+)\s*\{", scss))
    if set(kit["icons"]) != kit_icons[module]:
        errors.append(f"{module}: kit is stale vs icons.json (re-run build_icons.py)")
    if f"{module}/{kit['path']}" not in set(asset_paths(manifest(module))):
        errors.append(f"{module}: kit {kit['path']} not in manifest assets")
    red = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", scss, re.S)
    if not red or not all(s in red.group(1) for s in ("animation: none", "transition: none", "transform: none")):
        errors.append(f"{module}: kit lacks a full prefers-reduced-motion reset")
    if "@keyframes" in scss and "infinite" in scss.replace("bpro-ic-spin 0.9s linear infinite", ""):
        errors.append(f"{module}: a continuously running animation other than the spinner")

for f in glob.glob(os.path.join(ADDONS, "bpro_*", "**", "*.*"), recursive=True):
    if not f.endswith((".xml", ".js")) or "/tests/" in f:
        continue
    module = os.path.relpath(f, ADDONS).split(os.sep)[0]
    used = set(re.findall(r"bpro_ic--([a-z0-9-]+)", open(f, encoding="utf-8").read()))
    # JS can build the class from a field: "bpro_ic--" + icon, with icon: "sun"
    if f.endswith(".js") and "bpro_ic--" in open(f, encoding="utf-8").read():
        used |= set(re.findall(r'\bicon:\s*"([a-z0-9-]+)"', open(f, encoding="utf-8").read()))
    missing = used - kit_icons.get(module, set())
    if missing:
        errors.append(f"{os.path.relpath(f, ADDONS)}: icons not in the {module} kit: {sorted(missing)}")

# 3: no legacy icons left where we replaced them
for rel in cfg.get("no_legacy", []):
    text = open(os.path.join(ADDONS, rel), encoding="utf-8").read()
    for n, line in enumerate(text.splitlines(), 1):
        if LEGACY.search(line):
            errors.append(f"{rel}:{n}: legacy icon left: {line.strip()[:80]}")

# 4: app icons + web_icon targets
for module in cfg["apps"]:
    d = os.path.join(ADDONS, module, "static", "description")
    if not os.path.exists(os.path.join(d, "icon.svg")):
        errors.append(f"{module}: icon.svg missing")
    png = os.path.join(d, "icon.png")
    if not os.path.exists(png):
        errors.append(f"{module}: icon.png missing")
        continue
    head = open(png, "rb").read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(">II", head[16:24]) != (256, 256):
        errors.append(f"{module}: icon.png is not a 256x256 PNG")
for f in glob.glob(os.path.join(ADDONS, "bpro_*", "**", "*.xml"), recursive=True):
    for mod, path in re.findall(r'web_icon="([\w]+),([^"]+)"', open(f, encoding="utf-8").read()):
        if not os.path.exists(os.path.join(ADDONS, mod, path)):
            errors.append(f"{os.path.relpath(f, ADDONS)}: web_icon {mod},{path} does not exist")

# 5: manifest asset paths
for mf in sorted(glob.glob(os.path.join(ADDONS, "bpro_*", "__manifest__.py"))):
    for path in asset_paths(manifest(os.path.basename(os.path.dirname(mf)))):
        if "*" not in path and not os.path.exists(os.path.join(ADDONS, path)):
            errors.append(f"asset path missing: {path}")

for e in errors:
    print("FAIL", e)
print(f"check_icons: {len(cfg['apps'])} app icons, {len(kit_icons)} kits, {len(errors)} problem(s)")
sys.exit(1 if errors else 0)
