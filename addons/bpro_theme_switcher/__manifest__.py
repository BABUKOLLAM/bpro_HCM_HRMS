{
    "name": "bpro Theme & Language Switcher",
    "summary": "Always-visible Day/Night/Auto theme and language selector in the backend systray",
    "description": """
Adds a persistent systray icon (next to the user avatar, visible on
every backend screen) with two controls:

* Language - lists every active language on this database, switches
  the current user's language and reloads.
* Theme - Day / Night / Auto. Odoo 18 Community has no built-in dark
  mode covering the app shell (confirmed directly: even with its own
  color_scheme cookie and dark asset bundle active, computed styles
  showed the body background staying light - Community's dark SCSS
  only covers a few widgets). Night instead applies a curated dark
  stylesheet over the backend's main surfaces (forms, lists, kanban,
  control panel, dialogs, dropdowns, chatter) via a plain DOM
  attribute, not a cookie/bundle swap - so switching is instant, no
  reload. Auto follows the device's own light/dark preference live.
  The choice persists per browser (localStorage) and applies before
  first paint - no flash. Same approach as the sibling mepcrm.in
  product's bpro_ui_prefs module, ported here.
""",
    "version": "18.0.1.0.1",
    "category": "Hidden",
    "author": "Team bpro",
    "website": "https://bpropms.com",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "bpro_theme_switcher/static/src/theme_utils.js",
            "bpro_theme_switcher/static/src/theme_lang_systray.js",
            "bpro_theme_switcher/static/src/theme_lang_systray.xml",
            "bpro_theme_switcher/static/src/bpro_icons.scss",
            "bpro_theme_switcher/static/src/theme_lang_systray.scss",
            "bpro_theme_switcher/static/src/dark_theme.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
}
