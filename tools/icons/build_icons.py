#!/usr/bin/env python3
"""Build the bpro app icons and the Lucide icon kits from tools/icons/icons.json.

    python3 tools/icons/build_icons.py --lucide <dir-with-lucide-icons/*.mjs>

Outputs (all committed, so Odoo never needs this script at runtime):
  * addons/<module>/static/description/icon.svg  - source of the app icon
  * addons/<module>/static/description/icon.png  - 256x256 raster of it
  * docs/icons.md                                 - the mapping table
  * addons/<module>/<kit path>.scss              - per-module icon kit: accent
    tokens, duotone chip, subtle motion and one CSS mask class per Lucide
    glyph actually used by that module (`.bpro_ic.bpro_ic--<name>`).

Glyph geometry is copied verbatim from the Lucide source files (lucide-react
v1.21 ESM build, ISC licence, https://lucide.dev); nothing is drawn by hand.
PNGs are rasterised with PyMuPDF (`pip install pymupdf`), which renders SVG
natively - no cairo / rsvg needed.
"""
import argparse
import colorsys
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LICENCE = ("Icons: Lucide v1.21 (https://lucide.dev), ISC licence, "
           "Copyright (c) Lucide Contributors / Cole Bemis (Feather, MIT).")


def load_glyph(lucide_dir, name):
    src = open(os.path.join(lucide_dir, name + ".mjs"), encoding="utf-8").read()
    alias = re.search(r"export \{ default \} from '\./([\w-]+)\.mjs'", src)
    if alias:  # Lucide keeps old names as re-exports (file-signature -> file-pen-line)
        return load_glyph(lucide_dir, alias.group(1))
    body = re.search(r"const __iconNode = (\[.*?\]);\n", src, re.S).group(1)
    body = re.sub(r"(?m)^(\s*)([A-Za-z][\w-]*):", r'\1"\2":', body)      # keys on own line
    body = re.sub(r'([{,]\s*)([A-Za-z][\w-]*):', r'\1"\2":', body)      # inline keys
    nodes = json.loads(body)
    out = []
    for tag, attrs in nodes:
        attrs = {k: v for k, v in attrs.items() if k != "key"}
        out.append((tag, attrs))
    return out


def glyph_markup(nodes, quote='"'):
    parts = []
    for tag, attrs in nodes:
        a = " ".join(f"{k}={quote}{v}{quote}" for k, v in attrs.items())
        parts.append(f"<{tag} {a}/>")
    return "".join(parts)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lighten(h, amount):
    r, g, b = (c / 255 for c in hex_rgb(h))
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1.0, l + amount)
    r, g, b = colorsys.hls_to_rgb(hh, l, s)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def rel_lum(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((rel_lum(a), rel_lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def over_white(h, alpha):
    r, g, b = hex_rgb(h)
    return "#%02x%02x%02x" % tuple(round(255 + (c - 255) * alpha) for c in (r, g, b))


def app_svg(nodes, color, title):
    # Solid fill (MuPDF, used for the PNG, ignores SVG gradients) plus a soft
    # top highlight so the tile does not look flat.
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">\n'
        f'  <title>{html.escape(title)}</title>\n'
        f'  <!-- {LICENCE} -->\n'
        f'  <rect width="256" height="256" rx="56" fill="{color}"/>\n'
        '  <rect width="256" height="128" rx="56" fill="#ffffff" fill-opacity="0.06"/>\n'
        '  <rect x="1.5" y="1.5" width="253" height="253" rx="54.5" fill="none" '
        'stroke="#ffffff" stroke-opacity="0.16" stroke-width="3"/>\n'
        '  <g transform="translate(56 56) scale(6)" fill="none" stroke="#ffffff" '
        'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">\n'
        f'    {glyph_markup(nodes)}\n'
        '  </g>\n'
        '</svg>\n'
    )


def mask_uri(nodes):
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
           "stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
           + glyph_markup(nodes, quote="'") + "</svg>")
    return "data:image/svg+xml," + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


BASE_SCSS = """
.bpro_ic {
    display: inline-block;
    flex: none;
    width: 1.25em;
    height: 1.25em;
    vertical-align: -0.22em;
    background-color: currentColor;
    -webkit-mask: var(--bpro-ic) center / contain no-repeat;
    mask: var(--bpro-ic) center / contain no-repeat;
}
"""

CHIP_SCSS = """
// Duotone chip: accent at ~14% behind an accent-coloured stroke.
.bpro_ic_chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 0.7rem;
    background-color: var(--ic-tint, rgba(71, 85, 105, 0.14));
    color: var(--ic, #475569);
    transition: transform 0.18s ease-out, box-shadow 0.18s ease-out, background-color 0.18s ease-out, color 0.18s ease-out;

    .bpro_ic {
        width: 1.25rem;
        height: 1.25rem;
        transition: transform 0.18s ease-out;
    }
}
.bpro_ic_chip--solid {
    background-color: var(--ic, #475569);
    color: #ffffff;
}
.bpro_ic_host:hover .bpro_ic_chip,
.bpro_ic_host:focus-within .bpro_ic_chip,
.bpro_ic_host:active .bpro_ic_chip {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px -4px var(--ic-glow, rgba(71, 85, 105, 0.35));

    .bpro_ic {
        transform: scale(1.08);
    }
}

// First render: fade + 4px rise, staggered 40ms, capped at 280ms.
@keyframes bpro-ic-rise {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: none; }
}
.bpro_ic_rise {
    animation: bpro-ic-rise 0.32s ease-out backwards;
}
@for $i from 2 through 8 {
    .bpro_ic_rise:nth-child(#{$i}) { animation-delay: #{($i - 1) * 40}ms; }
}
.bpro_ic_rise:nth-child(n+9) { animation-delay: 280ms; }

// One gentle pulse when an item becomes active (not looping).
@keyframes bpro-ic-pulse {
    0% { box-shadow: 0 0 0 0 var(--ic-glow, rgba(71, 85, 105, 0.35)); }
    100% { box-shadow: 0 0 0 8px transparent; }
}
.bpro_ic_pulse {
    animation: bpro-ic-pulse 0.6s ease-out 1;
}
"""

SPIN_SCSS = """
@keyframes bpro-ic-spin { to { transform: rotate(360deg); } }
.bpro_ic_spin { animation: bpro-ic-spin 0.9s linear infinite; }
"""

REDUCED = """
// Bare .bpro_ic is deliberately NOT listed: hosts rotate it for state
// (e.g. an expanded chevron) and .bpro_ic_spin is a loading indicator,
// which the spec keeps spinning.
@media (prefers-reduced-motion: reduce) {
    .bpro_ic_chip,
    .bpro_ic_rise,
    .bpro_ic_pulse,
    .bpro_ic_host:hover .bpro_ic_chip,
    .bpro_ic_host:focus-within .bpro_ic_chip,
    .bpro_ic_host:active .bpro_ic_chip,
    .bpro_ic_host:hover .bpro_ic_chip .bpro_ic,
    .bpro_ic_host:focus-within .bpro_ic_chip .bpro_ic,
    .bpro_ic_host:active .bpro_ic_chip .bpro_ic {
        transition: none !important;
        animation: none !important;
        transform: none !important;
    }
}
"""


def kit_scss(module, kit, cfg, lucide_dir):
    groups = cfg["groups"]
    lines = [
        f"// GENERATED by tools/icons/build_icons.py from tools/icons/icons.json - do not edit by hand.",
        f"// {LICENCE}",
        f"// Icon kit for {module}: {', '.join(kit['icons'])}.",
    ]
    if kit.get("chips"):
        lines.append(":root {")
        for g, spec in groups.items():
            c = spec["color"]
            r, gg, b = hex_rgb(c)
            lines.append(f"    --ic-{g}: {c};")
            lines.append(f"    --ic-{g}-tint: rgba({r}, {gg}, {b}, 0.14);")
            lines.append(f"    --ic-{g}-glow: rgba({r}, {gg}, {b}, 0.38);")
        lines.append("}")
        dark = cfg.get("dark_selector")
        if dark:
            lines.append(f"{dark} {{")
            for g, spec in groups.items():
                c = spec.get("dark") or lighten(spec["color"], 0.22)
                r, gg, b = hex_rgb(c)
                lines.append(f"    --ic-{g}: {c};")
                lines.append(f"    --ic-{g}-tint: rgba({r}, {gg}, {b}, 0.2);")
                lines.append(f"    --ic-{g}-glow: rgba({r}, {gg}, {b}, 0.4);")
            lines.append("}")
        for g in groups:
            lines.append(f".bpro_acc--{g} {{ --ic: var(--ic-{g}); --ic-tint: var(--ic-{g}-tint); "
                         f"--ic-glow: var(--ic-{g}-glow); }}")
    lines.append(BASE_SCSS)
    for name in kit["icons"]:
        lines.append(f'.bpro_ic--{name} {{ --bpro-ic: url("{mask_uri(load_glyph(lucide_dir, name))}"); }}')
    if kit.get("chips"):
        lines.append(CHIP_SCSS)
    if kit.get("spin"):
        lines.append(SPIN_SCSS)
    lines.append(REDUCED)
    return "\n".join(lines).rstrip() + "\n"


def write_doc(cfg):
    groups = cfg["groups"]
    out = ["# Icons", "",
           "GENERATED by `tools/icons/build_icons.py` from `tools/icons/icons.json` - edit the JSON, then run",
           "`python3 tools/icons/build_icons.py --lucide <lucide icons dir>` and `python3 tools/icons/check_icons.py`.",
           "", LICENCE, "",
           "App icons: the module's Lucide glyph in white on a rounded square of its group accent",
           "(`static/description/icon.svg` is the source, `icon.png` the 256x256 raster).",
           "In-app icons: `<span class=\"bpro_ic bpro_ic--<glyph>\" aria-hidden=\"true\"/>` (CSS mask of the",
           "Lucide SVG), optionally inside a `bpro_ic_chip` duotone tile; `bpro_acc--<group>` picks the accent.",
           "", "| Group | Accent | Modules (glyph) |", "|---|---|---|"]
    for g, spec in groups.items():
        mods = ", ".join(f"{m} (`{i}`)" for m, (i, gg) in cfg["apps"].items() if gg == g)
        out.append(f"| {spec['label']} (`{g}`) | `{spec['color']}` | {mods or '-'} |")
    out += ["", "| Module kit | Glyphs |", "|---|---|"]
    for m, kit in cfg.get("kits", {}).items():
        out.append(f"| {m} | {', '.join('`%s`' % i for i in kit['icons'])} |")
    for line in cfg.get("doc_notes", []):
        out += ["", line]
    open(os.path.join(REPO, "docs", "icons.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lucide", required=True, help="directory holding Lucide <name>.mjs files")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args()
    cfg = json.load(open(os.path.join(HERE, "icons.json"), encoding="utf-8"))
    addons = os.path.join(REPO, "addons")
    groups = cfg["groups"]

    for g, spec in groups.items():
        c = spec["color"]
        cw, ct = contrast("#ffffff", c), contrast(c, over_white(c, 0.14))
        if cw < 4.5 or ct < 3:
            sys.exit(f"group {g}: {c} fails contrast (white on it {cw:.2f}, on chip {ct:.2f})")

    if not args.no_png:
        import pymupdf
    for module, (icon, group) in cfg["apps"].items():
        d = os.path.join(addons, module, "static", "description")
        os.makedirs(d, exist_ok=True)
        svg = app_svg(load_glyph(args.lucide, icon), groups[group]["color"],
                      f"{module}: {icon} ({groups[group]['label']})")
        open(os.path.join(d, "icon.svg"), "w", encoding="utf-8").write(svg)
        if not args.no_png:
            doc = pymupdf.open("svg", svg.encode())
            pix = doc[0].get_pixmap(alpha=True)
            assert pix.width == 256, pix.width
            pix.save(os.path.join(d, "icon.png"))
        print(f"app  {module:28s} {icon:18s} {group}")

    for module, kit in cfg.get("kits", {}).items():
        path = os.path.join(addons, module, kit["path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(kit_scss(module, kit, cfg, args.lucide))
        print(f"kit  {module:28s} {len(kit['icons'])} icons -> {kit['path']}")
    write_doc(cfg)
    print("doc  docs/icons.md")


if __name__ == "__main__":
    main()
