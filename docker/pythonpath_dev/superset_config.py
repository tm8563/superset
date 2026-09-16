# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os
import sys

from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache

logger = logging.getLogger()

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

# Use environment variable if set, otherwise construct from components
# This MUST take precedence over any other configuration
SQLALCHEMY_EXAMPLES_URI = os.getenv(
    "SUPERSET__SQLALCHEMY_EXAMPLES_URI",
    (
        f"{DATABASE_DIALECT}://"
        f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
        f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
    ),
)


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
THUMBNAIL_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.deletion_retention",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
        "superset.tasks.export_dashboard_excel",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
        # Gated on the SOFT_DELETE feature flag, which is off by default: the
        # task is scheduled either way, but purges nothing while the flag is
        # unset. Enable it in FEATURE_FLAGS below to exercise retention locally.
        "deletion_retention.purge_soft_deleted": {
            "task": "deletion_retention.purge_soft_deleted",
            "schedule": crontab(minute=0, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "DATASET_FOLDERS": True,
    "ENABLE_EXTENSIONS": True,
    "MOBILE_CONSUMPTION_MODE": True,
    "SEMANTIC_LAYERS": True,
    "AG_GRID_TABLE_ENABLED": True,
    "TABLE_V2_TIME_COMPARISON_ENABLED": True,
}
EXTENSIONS_PATH = "/app/docker/extensions"
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
# The Docker Compose app service is named "superset" and listens on 8088. Report
# paths are root-relative, so urljoin drops the base path; only the scheme, host,
# and port must be correct here. SUPERSET_APP_ROOT is kept for consumers that
# concatenate paths directly (e.g. cache warm-up). For screenshots in the dev
# stack (unbuilt static assets) point this at the nginx service instead:
# http://nginx{SUPERSET_APP_ROOT}/
WEBDRIVER_BASEURL = f"http://superset:8088{os.environ.get('SUPERSET_APP_ROOT', '/')}/"
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = (
    f"http://localhost:8888/{os.environ.get('SUPERSET_APP_ROOT', '/')}/"
)
SQLLAB_CTAS_NO_LIMIT = True

# Raise the dashboard layout (position_json) serialized-size limit.
# Default is 65535; set via env var SUPERSET_DASHBOARD_POSITION_DATA_LIMIT
# (e.g. in docker/.env). Falls back to 1 MB if unset.
# The underlying position_json column is MEDIUMTEXT (16 MB), so this is safe.
SUPERSET_DASHBOARD_POSITION_DATA_LIMIT = int(
    os.getenv("SUPERSET_DASHBOARD_POSITION_DATA_LIMIT", "1048576")
)

log_level_text = os.getenv("SUPERSET_LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level_text.upper(), logging.INFO)

if os.getenv("CYPRESS_CONFIG") == "true":
    # When running the service as a cypress backend, we need to import the config
    # located @ tests/integration_tests/superset_test_config.py
    base_dir = os.path.dirname(__file__)
    module_folder = os.path.abspath(
        os.path.join(base_dir, "../../tests/integration_tests/")
    )
    sys.path.insert(0, module_folder)
    from superset_test_config import *  # noqa

    sys.path.pop(0)

# MCP Service Configuration (Phase 11)
MCP_AUTH_ENABLED = True
MCP_JWT_ALGORITHM = "HS256"
MCP_JWT_SECRET = os.getenv("MCP_JWT_SECRET")
MCP_JWT_AUDIENCE = os.getenv("MCP_JWT_AUDIENCE", "superset-mcp")
MCP_RBAC_ENABLED = True
MCP_JWT_DEBUG_ERRORS = True


EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "tableau10",
        "description": "",
        "label": "Tableau 10",
        "isDefault": True,
        "colors": [
            "#4E79A7",  # blue
            "#F28E2B",  # orange
            "#E15759",  # red
            "#76B7B2",  # teal
            "#59A14F",  # green
            "#EDC948",  # yellow
            "#B07AA1",  # purple
            "#FF9DA7",  # pink
            "#9C755F",  # brown
            "#BAB0AC",  # gray
        ],
    }
]

# ---------------------------------------------------------------------------
# 1b. Surface the fork's Viewers field in the dashboard Edit Properties ->
#     Access UI (docs/00-runbook.md §5v/§6). Without this, the modal only
#     shows Editors, which grants full edit rights and bypasses every
#     viewer-based restriction -- there was no UI affordance for "let this
#     one person look at it without giving them edit access", so adding a
#     member "who can see" a restricted dashboard through the UI silently
#     added them as an Editor instead, undoing the restriction. Backend
#     enforcement of the viewers table (superset/dashboards/filters.py,
#     DashboardAccessFilter) was already unconditional regardless of this
#     flag; this only unhides the corresponding field client-side.
# ---------------------------------------------------------------------------
FEATURE_FLAGS = {
    "ENABLE_VIEWERS": True,
}

# ---------------------------------------------------------------------------
# 1d. Real language switching -- Superset's own mechanism, not a bespoke one.
#     Upstream ships a fully-working i18n system (Flask-Babel + Flask-
#     AppBuilder's `/lang/<locale>` route + real, Apache-maintained
#     translation catalogs, including Japanese) -- it's just switched off by
#     default (`LANGUAGES = {}` in superset/config.py, "translation in most
#     languages are incomplete"). Turning it back on here, scoped to only the
#     two languages this deployment actually supports, makes the globe-icon
#     switcher appear everywhere in Superset's own native UI (dashboard list,
#     chart builder, etc.) -- not just the custom homepage -- and puts every
#     employee's chosen language in one place: Flask's own session, the exact
#     state Superset's own gettext() calls already read everywhere.
# ---------------------------------------------------------------------------
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "es": {"flag": "es", "name": "Spanish"},
    "it": {"flag": "it", "name": "Italian"},
    "fr": {"flag": "fr", "name": "French"},
    "zh": {"flag": "cn", "name": "Chinese"},
    "zh_TW": {"flag": "tw", "name": "Traditional Chinese"},
    "ja": {"flag": "jp", "name": "Japanese"},
    "de": {"flag": "de", "name": "German"},
    "pl": {"flag": "pl", "name": "Polish"},
    "pt": {"flag": "pt", "name": "Portuguese"},
    "pt_BR": {"flag": "br", "name": "Brazilian Portuguese"},
    "ru": {"flag": "ru", "name": "Russian"},
    "ko": {"flag": "kr", "name": "Korean"},
    "cs": {"flag": "cz", "name": "Czech"},
    "sk": {"flag": "sk", "name": "Slovak"},
    "sl": {"flag": "si", "name": "Slovenian"},
    "sr": {"flag": "rs", "name": "Serbian (Cyrillic)"},
    "sr_Latn": {"flag": "rs", "name": "Serbian (Latin)"},
    "lv": {"flag": "lv", "name": "Latvian"},
    "nl": {"flag": "nl", "name": "Dutch"},
    "uk": {"flag": "ua", "name": "Ukrainian"},
    "mi": {"flag": "nz", "name": "Māori"},
    "ro": {"flag": "ro", "name": "Romanian"},
    "ar": {"flag": "sa", "name": "Arabic"},
    "ca": {"flag": "es", "name": "Catalan"},
    "fa": {"flag": "ir", "name": "Persian"},
    "fi": {"flag": "fi", "name": "Finnish"},
    "th": {"flag": "th", "name": "Thai"},
    "tr": {"flag": "tr", "name": "Turkish"},
    "ta": {"flag": "in", "name": "Tamil"},
}
# The full list above is copied verbatim from upstream's own commented-out
# default (superset/config.py) -- every one of these already has a complete,
# Apache-maintained translation catalog shipped in the vendored fork and
# compiled during the image build (§5aj, BUILD_TRANSLATIONS=true covers all
# of them, not just ja -- confirmed all 30 locale dirs got a messages.json).
# This project's OWN custom-page strings (_HSC_MSGIDS) only have a Japanese
# catalog (infra/superset/translations/ja/) -- gettext falls back to the
# English source text for any other locale on those specific pages, which
# is a safe, unsurprising default, not an error.
# Upstream defaults to "en"; this project's own default was always Japanese
# (the source Tableau tool and most of its employees are Japanese-first) --
# preserve that instead of silently flipping every brand-new session to
# English the moment this switched from a per-account DB preference to
# Superset's own session-based one.
BABEL_DEFAULT_LOCALE = "ja"

# This project's own custom pages (the homepage, settings page -- see §6)
# are plain Flask routes, not part of the React app, so they can't pull from
# Superset's frontend translation bundles -- but they CAN use the same
# Flask-Babel `gettext()` backend Superset's own Python code already uses,
# once a matching catalog is on the search path. FAB's BabelManager combines
# this with its own + Superset's own translations dirs automatically (see
# flask_appbuilder/babel/manager.py) -- this just adds one more, mounted
# read-only from infra/superset/translations/ (docker-compose.yml).
BABEL_TRANSLATION_DIRECTORIES = "/app/pythonpath/translations"

# ---------------------------------------------------------------------------
# 1c. Client's company logo alongside Superset's own wordmark, everywhere
#     Superset renders its nav logo -- including the login page, which this
#     project doesn't render itself (see §6 for the pages this project does
#     render). Superset's nav only has one logo slot, not a second one next
#     to it, so the two logos are composited into a single image and served
#     by a route registered in _hsc_flask_app_mutator() further down this
#     file (kept public/unauthenticated on purpose: the login page needs it
#     before anyone is signed in).
# ---------------------------------------------------------------------------
APP_ICON = "/hsc/assets/logo-combined.svg"
# APP_ICON alone only feeds THEME_DEFAULT/THEME_DARK's brandLogoUrl token at
# the point config.py itself builds those dicts -- before this file is ever
# imported -- so it has no effect on its own (config.py's own comment above
# APP_ICON says as much). The themes must be mutated directly too; importing
# them here gets the SAME dict objects config.py already built (mutating in
# place, not rebinding the name), so this is visible wherever else in the
# app already holds a reference to THEME_DEFAULT/THEME_DARK.
from superset.config import THEME_DEFAULT as _hsc_theme_default, THEME_DARK as _hsc_theme_dark

_hsc_theme_default["token"]["brandLogoUrl"] = APP_ICON
_hsc_theme_dark["token"]["brandLogoUrl"] = APP_ICON

# ---------------------------------------------------------------------------
# 2. Allow styled Markdown tiles for the HSC Menu Hub homepage (work plan
#    §7.6). Superset strips `style`/`class` attributes and `<style>` tags
#    from Markdown dashboard components by default (rehype-sanitize, since
#    PR #21895) to prevent stored-XSS -- this is exactly the class of issue
#    behind CVE-2022-43717. We deliberately widen the allowed set to ONLY
#    `style` and `class`, not "allow everything", and this file's docstring
#    plus docs/00-runbook.md both call out that dashboard **Edit** access
#    must stay restricted to trusted users as a result.
# ---------------------------------------------------------------------------
HTML_SANITIZATION_SCHEMA_EXTENSIONS = {
    "attributes": {
        "*": ["style", "class"],
        "svg": ["viewBox", "xmlns", "width", "height", "fill"],
        "path": ["d", "fill"],
        "circle": ["cx", "cy", "r", "fill"],
    },
    "tagNames": ["style", "svg", "path", "circle"],
}

# ---------------------------------------------------------------------------
# 3. HSC Menu homepage, rendered server-side, personalized per logged-in user.
#
#    History: `/welcome/` originally *redirected* to a Superset dashboard
#    (id 11, `hsc-menu`) built from a Markdown component -- see git history /
#    docs/00-runbook.md §5a-5c for why a redirect (not server-rendered
#    content) was needed to get Superset's client-side router to show it at
#    all. That approach hit a hard ceiling once real per-employee
#    customization was requested: a Markdown component cannot run
#    JavaScript (confirmed by testing -- an injected <script> tag is
#    stripped before it ever reaches the DOM) and cannot accept a real HTML
#    <form> POST tied to server logic. There is no way to remember "this
#    employee hid this tile" or "this employee picked this accent color"
#    from inside that sandbox.
#
#    The fix: stop trying to make the Markdown component interactive, and
#    render the homepage directly as a normal Flask response instead, from
#    the same `before_request` hook that used to just redirect. This runs as
#    real server code with the actual logged-in `current_user`, so it can:
#      - look up that employee's saved tile visibility/order/accent color
#        (table `hsc_user_menu_prefs` in the hsc_bi warehouse -- see
#        infra/postgres-init/02-user-menu-prefs.sql)
#      - render a genuine <form> at /hsc/menu-settings that POSTs changes
#        back and saves them -- no JavaScript needed anywhere in this flow
#      - fall back to sensible defaults for anyone who hasn't customized
#        anything yet
#
#    Dashboard 11 (`hsc-menu`) is left in place but is no longer the
#    homepage; it was the earlier, non-personalizable version.
#
#    Tiles are no longer a hand-maintained list. Any Superset dashboard that
#    is (a) Published and (b) tagged `hsc:pl` / `hsc:mh` / `hsc:att` (tags
#    are a normal, built-in Superset feature -- Edit dashboard properties ->
#    Tags) automatically appears as a live tile in that column, using the
#    dashboard's own title -- no code change needed to add a new one.
#    Untagged dashboards (including Superset's own example dashboards)
#    don't appear at all, so this stays a curated menu, not "every
#    dashboard on the server." A short list of *planned-but-not-yet-built*
#    items from the original Tableau menu (§7.6 of docs/06-workplan.md)
#    still renders as honest grey "coming soon" placeholders alongside the
#    real ones, so the menu still matches the shape of the original tool.
#
#    UI chrome (headers, buttons, status labels) supports Japanese and
#    English, toggled per-user via /hsc/set-lang and remembered the same way
#    as the other preferences. Real dashboard titles display as authored
#    (whatever language whoever built them used) -- translating dashboard
#    content itself is out of scope here.
#
#    Security note: this uses a *separate* direct Postgres connection as
#    `hsc_owner` (read-write) rather than the `hsc_reader` role Superset's
#    own chart datasets use -- keeping the read-only boundary documented in
#    infra/postgres-init/01-roles.sql intact. `hsc_owner`'s password here
#    matches infra/docker-compose.yml; change both together if it's ever
#    rotated.
# ---------------------------------------------------------------------------

_HSC_PLACEHOLDER_TILES = [
    {"id": "pl_summary", "group": "pl", "label": "収支表サマリ", "status": "soon"},
    {"id": "pl_income_statement", "group": "pl", "label": "損益計算書", "status": "soon"},
    {"id": "pl_project", "group": "pl", "label": "プロジェクト収支", "status": "soon"},
    {"id": "pl_project_deficit", "group": "pl", "label": "プロジェクト収支（赤字抜粋）", "status": "soon"},
    {"id": "pl_monthly_trend", "group": "pl", "label": "月別推移一覧表", "status": "soon"},
    {"id": "mh_summary", "group": "mh", "label": "工数サマリ", "status": "soon"},
    {"id": "mh_ga_users", "group": "mh", "label": "利用者分析（一般管理費）", "status": "soon"},
    {"id": "att_main", "group": "att", "label": "勤怠分析", "status": "na"},
]
_HSC_GROUP_IDS = ["pl", "mh", "att"]  # built-in, from the original Tableau menu -- see _hsc_all_groups() for the full list including manually-added categories
# Brand pink (RYOBI LAO logo mark), matching the approved "Version 6 —
# Enterprise Ready" direction -- used selectively (primary actions, focus,
# selection, active nav) via the existing accent-token system, not painted
# across the whole UI. Anyone who picked a different color previously keeps
# it (this only changes the default for accounts with no saved `accent`).
_HSC_DEFAULT_ACCENT = "#EF476F"
_HSC_DB_DSN = os.environ["HSC_DB_DSN"]

# ---------------------------------------------------------------------------
# Real i18n (§1d): every translatable string used by the custom homepage/
# settings pages, keyed the same way the old hand-rolled `_HSC_STRINGS` dict
# was, but the VALUE here is the English source text -- the gettext msgid --
# not a lookup table of pre-translated strings. The Japanese text that used
# to live in this file now lives as real msgstr entries in
# infra/superset/translations/ja/LC_MESSAGES/messages.po (compiled to
# messages.mo), extracted from these exact msgids via `pybabel extract` so
# the two can never drift apart silently. `greeting_suffix` and `lang_toggle`
# aren't here: neither is a translation of an English *string* (one has no
# English text to translate -- see _hsc_tr's docstring; the other is a
# language's own name, never translated into a different language).
# ---------------------------------------------------------------------------
_HSC_MSGIDS = {
    "header_title": "HSC Menu",
    "settings": "⚙ Settings",
    "logout": "Log out",
    "group_pl": "P&L",
    "group_mh": "Man-Hours",
    "group_att": "Attendance",
    "soon": "Coming soon",
    "na": "Out of scope",
    "live_badge": "Available",
    "stat_live": "Available",
    "stat_soon": "Coming soon",
    "stat_na": "Out of scope",
    "select_menu": "Select a Menu",
    "create_hint": "Click to create this dashboard",
    "add_dashboard_button": "Dashboard",
    "category_empty": "Nothing in this category yet.",
    "theme_presets_hint": "Picking a color re-themes the whole page — background, header, and buttons. Use the picker on the right for any custom color.",
    "add_category_title": "Add a new category",
    "add_category_hint": "Need a category beyond P&L / Man-Hours / Attendance? Add it here.",
    "new_category_name_ja": "Category name (Japanese)",
    "new_category_name_en": "Category name (English, optional)",
    "create_category_button": "Add",
    "import_title": "Import a dashboard",
    "import_hint": "Load an export (.zip or .json) from another Superset instance. After importing, tag it (e.g. hsc:pl) and publish it from Superset's own dashboard list.",
    "import_button": "Import",
    "mascot": "Click the menu for what you'd like to check!",
    "settings_title": "Customize Menu",
    "settings_subtitle": "Menu configuration · appearance · dashboards",
    "back_home": "← Back to Home",
    "back_home_btn": "Back to Home",
    "accent_label": "Theme color",
    "order_label": "Order",
    "category_color_label": "Category color",
    "save": "Save",
    "save_appearance": "Save appearance",
    "save_layout": "Save layout",
    "save_categories": "Save categories",
    "saved": "Saved.",
    "category_exists": "Category \"%(name)s\" already exists. Pick a different name.",
    "category_create_failed": "Could not create the category. Please try again.",
    "language_label": "Language",
    "section_name_label": "Section name",
    "hidden_section_label": "Hidden section",
    "category_name_label": "Category name",
    "out_of_scope_hint": "This dashboard is not part of the current scope and cannot be opened.",
    "add_dashboard_title": "Add a new dashboard",
    "add_dashboard_hint": "Enter a name and category to create an empty dashboard and open its editor.",
    "new_dashboard_name": "Dashboard name",
    "new_dashboard_group": "Category",
    "create_and_open": "Create and open editor",
    "homepage_layout_title": "Homepage layout",
    "homepage_layout_hint": "Drag dashboards between sections to arrange your homepage. Drag one to Hidden to remove it.",
    "hidden_section_name": "Hidden",
    "section_empty_hint": "Drop dashboards here.",
    "categories_layout_title": "Categories",
    "settings_view_hint": "Switch between settings sections from the sidebar \u2014 each section saves independently.",
    "appearance_label": "Appearance",
    "mode_light": "Light",
    "mode_dark": "Dark",
    "mode_system": "System",
    "density_label": "Card density",
    "density_comfortable": "Comfortable",
    "density_compact": "Compact",
    "skip_to_content": "Skip to content",
    # Keyboard-accessible alternative to the two kanban boards' HTML5 drag
    # (§5av) -- a grab-handle button per card/column, so Tab/Enter/Space/
    # arrow-keys/Escape can do everything the mouse drag can. Shared between
    # both boards where the interaction is identical (picking up a card),
    # separate where it isn't (a category column's own reorder vs. a card's
    # reorder-or-recategorize).
    "hsc_kanban_instructions": "Press Enter or Space to pick up this dashboard. While picked up, use Up or Down arrow keys to reorder it within its section, or Left or Right arrow keys to move it to an adjacent section. Press Enter or Space again to drop it, or Escape to cancel. You can also use the \"Move to\" menu on each dashboard without picking it up.",
    "hsc_section_instructions": "Press Enter or Space to pick up this section. While picked up, use Up or Down arrow keys to move it. Press Enter or Space again to drop it, or Escape to cancel.",
    "hsc_reorder_card_label": "Reorder %(card)s",
    "hsc_reorder_category_label": "Reorder %(category)s section",
    "hsc_picked_up_card": "Picked up %(card)s. Use arrow keys to move it.",
    "hsc_picked_up_category": "Picked up %(category)s section. Use up and down arrow keys to move it.",
    "hsc_moved_card_to_section": "Moved %(card)s to %(section)s, position %(pos)s of %(total)s.",
    "hsc_moved_category": "Moved %(category)s to position %(pos)s of %(total)s.",
    "hsc_move_canceled": "Move canceled.",
    # Search (homepage launcher, §5au audit follow-up): the homepage's one job
    # is "find and open the right dashboard fast" -- with 20+ tiles across 5
    # sections, visual scan-only stops scaling. A label, a visible placeholder,
    # a clear button, a live-region result count, and the "/" shortcut hint
    # are all separate strings because they play different roles.
    "search_label": "Search dashboards",
    "search_placeholder": "Search dashboards…",
    "clear_search": "Clear search",
    "search_results_count": "%(count)s found",
    "search_no_results": "No dashboards match your search.",
    "search_shortcut_hint": "Press / to search",
    # Drag affordances: a hover/tooltip on every grab handle so the control
    # explains itself, plus an aria-live announcement for MOUSE drags too
    # (the keyboard engine already announced its own moves; sighted-
    # screen-reader users dragging with a mouse got nothing).
    "drag_handle_hint": "Drag to move, or press Enter to move with the keyboard",
    "dragging_card": "Dragging %(name)s",
    # True empty state (first-run / all-dashboards-unpublished): the homepage
    # previously rendered nothing but the mascot when no tiles existed.
    "empty_home_title": "No dashboards yet",
    "empty_home_hint": "Published dashboards tagged hsc:* appear here automatically. Create your first dashboard to get started.",
    "empty_home_cta": "+ Create dashboard",
    # Unsaved-changes awareness (settings IA): the beforeunload guard (§5aw
    # F03) only fires when LEAVING the page -- within the page, nothing told
    # anyone their kanban drags weren't saved yet. A quiet reminder chip
    # appears next to the section nav once anything is edited.
    "unsaved_reminder": "You have unsaved changes — use a Save button to keep them.",
    "settings_nav_label": "Settings sections",
    # Version 6 homepage redesign: hero, status filters, per-category "show
    # all", and the bottom "can't find it" CTA.
    "hero_subtitle": "Find the dashboard you need and open it in one click.",
    "hero_welcome": "Welcome, %(name)s",
    "filter_all": "All",
    "filter_all_label": "Show all dashboards",
    "filter_live_label": "Show only available dashboards",
    "filter_soon_label": "Show only coming-soon dashboards",
    "filter_na_label": "Show only out-of-scope dashboards",
    "show_all_n": "Show all %(count)s →",
    "show_less": "Show less",
    "cant_find_title": "Can't find your dashboard?",
    "cant_find_hint": "Dashboards can be hidden, renamed, or moved between categories from the customization screen.",
    "customize_menu_button": "Customize menu",
    "search_no_matches_title": "No dashboards match",
    "search_no_matches_hint": "Try a different search term, or clear the filters above.",
    "clear_filters": "Clear filters",
    "view_all": "View all",
    "appearance_title": "Appearance",
    "appearance_hint": "Personalize how the menu looks \u2014 theme color, light/dark mode, and card density. Changes apply instantly to your account.",
    "sidebar_desc_appearance": "Theme, mode and density",
    "sidebar_desc_homepage": "Arrange categories and dashboards",
    "sidebar_desc_categories": "Names, colors and order",
    "sidebar_desc_dashboards": "Create and organize",
    "sidebar_desc_importexport": "Backup and restore",
    "theme_color_label": "Theme color",
    "display_mode_label": "Display mode",
    "card_density_label": "Card density",
    "density_standard": "Standard",
    "categories_title": "Categories",
    "categories_hint": "Categories organize the homepage. Reorder, rename, recolor, or remove them \u2014 changes apply for every employee.",
    "dashboards_title": "Dashboards",
    "dashboards_hint": "Create dashboards, import existing ones, and move them between categories.",
    "import_export_title_v6": "Import / Export",
    "export_title": "Export configuration",
    "export_hint": "Download your menu configuration: your personal homepage layout plus the shared category list (names, order, colors).",
    "import_title_v6": "Import configuration",
    "import_hint_v6": "Upload a configuration file exported from this screen. This replaces your current homepage layout and the shared category list \u2014 export a backup first if unsure.",
    "choose_file": "Choose file",
    "drop_file_here": "Drag a configuration file here",
    "create_dashboard_button": "Create dashboard",
    "cancel_action": "Cancel",
    "open_action": "Open",
    "move_action": "Move category",
    "dashboard_actions_label": "Actions for %(dashboard)s",
    "open_full_preview": "Open full preview",
    "dashboard_word": "dashboard",
    "dashboards_word": "dashboards",
    "rename_pop_title": "Rename",
    "change_color_pop_title": "Change color",
    "builtin_category_note": "Built-in category \u2014 can be reordered and recolored, but not renamed or deleted.",
    "whats_backed_up_title": "What gets backed up?",
    "whats_backed_up_layout": "Your personal homepage layout",
    "whats_backed_up_order": "Category ordering",
    "whats_backed_up_colors": "Category names and colors",
    # Version 6 settings redesign: category table (replaces the category
    # kanban board), dashboard-management reassign control, homepage layout
    # structured editor, live preview, sticky save/reset bar, import/export.
    "delete": "Delete",
    "hsc_move_category_up": "Move %(category)s up",
    "hsc_move_category_down": "Move %(category)s down",
    "delete_category_label": "Delete %(category)s",
    "delete_category_has_dashboards": "%(count)s dashboard(s) use this category. Choose where to move them, then confirm.",
    "delete_category_empty": "This category has no dashboards. It will be removed for everyone.",
    "reassign_to_label": "Move dashboards to",
    "delete_category_confirm": "Delete category",
    "categories_table_hint": "Drag to reorder, rename or delete a category you added, or set its color. Built-in categories can be reordered and recolored but not renamed or deleted.",
    "dashboard_list_title": "Existing dashboards",
    "dashboard_list_hint": "Change a dashboard's category here — the change applies for everyone.",
    "dashboard_category_label": "Category for %(dashboard)s",
    "dashboard_management_title": "Dashboard management",
    "import_export_title": "Import / export",
    "import_export_hint": "Back up your menu configuration (categories, colors, and your personal homepage layout) or restore it from a file.",
    "export_settings_button": "Export configuration",
    "import_settings_title": "Import configuration",
    "import_settings_hint": "Upload a configuration file exported from this screen. This replaces your current homepage layout and the shared category list — export a backup first if unsure.",
    "import_settings_button": "Import configuration",
    "import_settings_confirm": "This will replace the current category list and colors, and your personal homepage layout, with the contents of the file. Continue?",
    "import_settings_invalid": "That file isn't a valid HSC configuration export.",
    "import_settings_success": "Configuration imported.",
    "dashboard_import_title": "Import a dashboard bundle",
    "hsc_move_to_label": "Move %(card)s to another section",
    "reset_layout": "Reset",
    "reset_confirm": "Discard your unsaved changes?",
    "unsaved_changes_chip": "Unsaved changes",
    "collapse_section": "Collapse %(section)s",
    "expand_section": "Expand %(section)s",
    "live_preview_title": "Preview",
    "live_preview_hint": "How your homepage will look after saving.",
    "live_preview_toggle": "Show preview",
    "hide_preview_toggle": "Hide preview",
}


def _hsc_tr(key):
    """Translate one of _HSC_MSGIDS's keys via Flask-Babel, using whatever
    locale Superset's own session-based mechanism (flask_appbuilder's
    `/lang/<locale>` route, or this project's own `/hsc/set-lang`, which
    sets the identical `session["locale"]` key -- see §1d/§6.5) currently
    has active for this browser. Falls back to returning the key itself if
    it's not a real msgid (matches the old dict-lookup's behavior when a
    key was missing, so a typo'd key fails loud instead of crashing)."""
    from flask_babel import gettext as _hsc_gettext

    return _hsc_gettext(_HSC_MSGIDS[key]) if key in _HSC_MSGIDS else key


def _hsc_get_dynamic_tiles():
    """Published, hsc:*-tagged dashboards the CURRENT logged-in user can
    actually see -> live tiles. No hardcoded list, and no longer "tagged +
    published = visible to everyone" either.

    Applies Superset's own real access check (`DashboardAccessFilter`, the
    same class the dashboard list page itself uses) scoped to whoever's
    making this request -- not just `Dashboard.published`. That means a
    dashboard someone has deliberately scoped to specific Editors/Viewers
    (Superset's own "Dashboard properties -> Access" dialog) correctly
    disappears from both the homepage and the settings page for anyone not
    on that list, instead of showing up for every employee regardless.
    Confirmed by testing: with no explicit viewers, a published dashboard
    with real charts falls back to "visible to anyone with datasource
    access" (which is everyone, since all 24 employees are Alpha) -- adding
    even one explicit viewer switches that fallback off, and non-listed
    employees lose access immediately, both through this filter directly
    and through the homepage tile it drives.
    """
    try:
        from superset.extensions import db
        from superset.models.dashboard import Dashboard
        from superset.dashboards.filters import DashboardAccessFilter
        from flask_appbuilder.models.sqla.interface import SQLAInterface

        tiles = []
        group_ids = _hsc_all_group_ids()
        query = db.session.query(Dashboard).filter(Dashboard.published.is_(True))
        visible_ids = {
            row[0]
            for row in DashboardAccessFilter("id", SQLAInterface(Dashboard))
            .apply(query.with_entities(Dashboard.id), None)
            .all()
        }
        dashboards = [d for d in query.all() if d.id in visible_ids]
        for dash in dashboards:
            tag_names = {t.name for t in dash.tags}
            group = next((g for g in group_ids if f"hsc:{g}" in tag_names), None)
            if not group:
                continue
            tiles.append(
                {
                    "id": f"dash:{dash.id}",
                    "group": group,
                    "label": dash.dashboard_title,
                    "status": "live",
                    "href": f"/superset/dashboard/{dash.slug or dash.id}/?standalone=2",
                }
            )
        return tiles
    except Exception:
        # A metadata-DB hiccup should degrade to "just the placeholders", not a 500.
        return []


def _hsc_get_linked_placeholder_ids():
    """tile_id -> real dashboard already exists (hsc_placeholder_dashboard_links).

    Once a placeholder has a real dashboard, that dashboard shows up on its
    own through the normal tag mechanism above -- so the placeholder entry
    must stop rendering, or the same thing would appear twice.
    """
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT tile_id FROM hsc_placeholder_dashboard_links")
                return {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    except Exception:
        return set()


def _hsc_all_tiles():
    linked = _hsc_get_linked_placeholder_ids()
    placeholders = [t for t in _HSC_PLACEHOLDER_TILES if t["id"] not in linked]
    return placeholders + _hsc_get_dynamic_tiles()


def _hsc_get_dashboard_to_placeholder_id():
    """Reverse of _hsc_get_linked_placeholder_ids(): dashboard_id -> the
    placeholder tile_id it was linked from.

    A per-user hide/order preference (hsc_user_menu_prefs) saved while a menu
    slot was still a "coming soon" placeholder is keyed by that placeholder's
    tile_id (e.g. "pl_income_statement"). Once someone links a real dashboard
    to it, _hsc_all_tiles() starts rendering it as a dynamic tile keyed
    "dash:<id>" instead -- a bare id match would silently forget every
    existing hide/order choice at that moment. _hsc_tile_alias_ids() below
    uses this map so both the old and new id are honored for a linked tile.
    """
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT tile_id, dashboard_id FROM hsc_placeholder_dashboard_links")
                return {row[1]: row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    except Exception:
        return {}


def _hsc_tile_alias_ids(tile, dash_to_placeholder_id):
    ids = {tile["id"]}
    if tile["id"].startswith("dash:"):
        legacy = dash_to_placeholder_id.get(int(tile["id"].split(":", 1)[1]))
        if legacy:
            ids.add(legacy)
    return ids


def _hsc_tile_order_value(tile, order, dash_to_placeholder_id, default):
    for key in _hsc_tile_alias_ids(tile, dash_to_placeholder_id):
        if key in order:
            return order[key]
    return default


def _hsc_get_custom_categories():
    """Manually-added categories beyond the 3 built-in ones (hsc_categories
    table, §8 of the work plan) -- so the menu isn't stuck at exactly
    収支表/工数分析/勤怠分析 forever. `label` is the required
    Japanese/primary name; `label_en` is an optional English name (§5am),
    None when nobody gave one."""
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT key, label, label_en FROM hsc_categories ORDER BY created_at")
                return [{"id": r[0], "label": r[1], "label_en": r[2]} for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        return []


def _hsc_category_display_label(category):
    """Pick a custom category's display label for the current locale: the
    optional English name when the viewer's language is English AND one was
    actually given, otherwise the required Japanese/primary name -- never
    blank, since `label` is NOT NULL."""
    from flask_babel import get_locale

    if str(get_locale()) == "en" and category.get("label_en"):
        return category["label_en"]
    return category["label"]


def _hsc_all_groups():
    """(group_id, display_label) for every category, built-in + custom, in
    display order. Built-ins are translated via gettext; custom ones pick
    between their saved Japanese/English names by current locale (§5am).
    Order is a saved override (hsc_category_order, §5aq's category kanban
    board -- dragging a column reorders categories for everyone, same as
    colors) when one exists for a given category, else its natural position:
    built-ins first in their fixed order, then custom ones by created_at."""
    groups = [(gid, _hsc_tr(f"group_{gid}")) for gid in _HSC_GROUP_IDS]
    groups += [(c["id"], _hsc_category_display_label(c)) for c in _hsc_get_custom_categories()]
    overrides = _hsc_get_category_order()
    indexed = list(enumerate(groups))
    indexed.sort(key=lambda pair: overrides.get(pair[1][0], 10_000 + pair[0]))
    return [g for _, g in indexed]


def _hsc_all_category_labels():
    """Every category label a duplicate check must respect (audit F01):
    the built-ins' DISPLAY labels (収支表 etc., since those are what a user
    sees and would type again), every custom category's Japanese name, and
    every custom category's optional English name. Comparison happens
    casefold()-ed by the caller so "Audit"/"audit" collide too."""
    labels = [_hsc_tr(f"group_{gid}") for gid in _HSC_GROUP_IDS]
    for c in _hsc_get_custom_categories():
        labels.append(c["label"])
        if c.get("label_en"):
            labels.append(c["label_en"])
    return labels


def _hsc_all_group_ids():
    return [gid for gid, _ in _hsc_all_groups()]


def _hsc_get_category_order():
    """key -> saved sort position, for any category that's been dragged to a
    non-default spot on the category kanban board. See _hsc_all_groups()."""
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT key, sort_order FROM hsc_category_order")
                return dict(cur.fetchall())
        finally:
            conn.close()
    except Exception:
        return {}


def _hsc_save_category_order(ordered_group_ids):
    """Persist a full left-to-right (then top-to-bottom, once wrapped) column
    order from the category kanban board -- every category gets an explicit
    position, not just the ones that moved, so a later category added
    elsewhere doesn't unexpectedly jump ahead of ones a person deliberately
    arranged."""
    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            for i, gid in enumerate(ordered_group_ids):
                cur.execute(
                    """
                    INSERT INTO hsc_category_order (key, sort_order) VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET sort_order = EXCLUDED.sort_order
                    """,
                    (gid, i),
                )
        conn.commit()
    finally:
        conn.close()


_HSC_SECTION_COUNT = 5


def _hsc_effective_sections(settings, all_tiles, dash_to_placeholder_id):
    """The homepage's 5 kanban sections, reconciled against what's actually
    in `all_tiles` right now -- a tile can vanish (its dashboard got
    unpublished/deleted) or newly appear (a fresh hsc:*-tagged dashboard
    nobody has dragged anywhere yet) between one save and the next, and
    neither case should silently break someone's saved layout. A tile not
    found in any saved section (including every tile at all, the first time
    a person has no `sections` saved yet) lands at the end of Section 1 --
    never dropped, never duplicated.

    Hidden tiles (settings["hidden"], written by the same kanban board's
    "Hidden" bucket) are excluded before reconciliation, same list/format
    the rest of this file already reads.
    """
    hidden = set(settings.get("hidden") or [])

    def alias_ids(tile):
        return _hsc_tile_alias_ids(tile, dash_to_placeholder_id)

    visible = [t for t in all_tiles if not (alias_ids(t) & hidden)]
    by_id = {}
    for t in visible:
        for alias in alias_ids(t):
            by_id[alias] = t

    raw_sections = settings.get("sections")
    if isinstance(raw_sections, list) and raw_sections:
        sections = []
        for i in range(_HSC_SECTION_COUNT):
            src = raw_sections[i] if i < len(raw_sections) and isinstance(raw_sections[i], dict) else {}
            name = str(src.get("name") or "").strip() or f"Section {i + 1}"
            tiles, seen = [], set()
            for tid in src.get("tiles") or []:
                tile = by_id.get(tid)
                if tile and tile["id"] not in seen:
                    tiles.append(tile)
                    seen.add(tile["id"])
            sections.append({"name": name, "tiles": tiles})
    else:
        # No saved layout yet (brand new account, or a settings blob from
        # before this feature existed): reproduce the old category-grouped
        # order as a starting point rather than dumping everything into
        # Section 1 -- built-in/custom categories map 1:1 onto sections 1-5
        # in category order, using whatever legacy `order` values already
        # exist so nothing visibly reshuffles on first load.
        group_ids = _hsc_all_group_ids()
        order = settings.get("order") or {}
        sections = [{"name": glabel, "tiles": []} for _, glabel in _hsc_all_groups()[:_HSC_SECTION_COUNT]]
        while len(sections) < _HSC_SECTION_COUNT:
            sections.append({"name": f"Section {len(sections) + 1}", "tiles": []})
        for t in sorted(
            visible,
            key=lambda t: _hsc_tile_order_value(t, order, dash_to_placeholder_id, all_tiles.index(t)),
        ):
            gi = group_ids.index(t["group"]) if t["group"] in group_ids else 0
            sections[min(gi, _HSC_SECTION_COUNT - 1)]["tiles"].append(t)

    placed_ids = {t["id"] for s in sections for t in s["tiles"]}
    for t in visible:
        if t["id"] not in placed_ids:
            sections[0]["tiles"].append(t)
            placed_ids.add(t["id"])

    return sections


def _hsc_save_category(label_ja, label_en=None):
    """Insert a custom category. Returns the new key, or the string
    "__duplicate__" when the insert lost a uniqueness race instead of
    raising: the unique index on btrim(lower(label)) is the real duplicate
    guard (red-team 2026-09-10: three truly-concurrent POSTs of the same
    new name all passed the app-level check-then-INSERT and created three
    rows -- only a storage-layer constraint is race-safe), so losing that
    race is an expected, ordinary outcome to report as "already exists",
    not an infrastructure failure."""
    import uuid

    key = "cat_" + uuid.uuid4().hex[:8]
    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hsc_categories (key, label, label_en) VALUES (%s, %s, %s)",
                (key, label_ja, label_en),
            )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return "__duplicate__"
    finally:
        conn.close()
    return key


def _hsc_rename_category(key, field, new_label):
    """Rename a CUSTOM category's `label` or `label_en` column (never a
    built-in's -- those are gettext msgids, not DB rows, and the caller is
    responsible for only ever passing a `cat_*` key). Same duplicate-race
    handling as _hsc_save_category: the unique index is the real guard."""
    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE hsc_categories SET {field} = %s WHERE key = %s", (new_label, key))  # noqa: S608 -- field is one of two hardcoded literals below, never request-controlled
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return "__duplicate__"
    finally:
        conn.close()
    return key


def _hsc_delete_category(key):
    """Remove a custom category and every row that references it by key
    (order override, color override). Callers must reassign or verify zero
    dashboards remain tagged with it BEFORE calling this -- deleting the
    category row doesn't touch any `hsc:<key>` dashboard tag, so a
    dashboard left behind would simply stop appearing in _hsc_all_groups()
    and its tag would become orphaned. See _hsc_delete_category_view."""
    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hsc_categories WHERE key = %s", (key,))
            cur.execute("DELETE FROM hsc_category_order WHERE key = %s", (key,))
            cur.execute("DELETE FROM hsc_category_colors WHERE key = %s", (key,))
        conn.commit()
    finally:
        conn.close()


def _hsc_get_category_colors():
    """key -> overridden color, for any category (built-in or custom) that
    has one set. A category with no row here falls back to its position in
    _HSC_TILE_PALETTE -- see _hsc_group_colors()."""
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT key, color FROM hsc_category_colors")
                return dict(cur.fetchall())
        finally:
            conn.close()
    except Exception:
        return {}


def _hsc_save_category_color(key, color):
    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hsc_category_colors (key, color) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET color = EXCLUDED.color
                """,
                (key, color),
            )
        conn.commit()
    finally:
        conn.close()


def _hsc_group_colors(groups):
    """(group_id -> color) for every category in `groups` -- a saved
    override if one exists, else the next color in the default rotating
    palette. Every tile in a category shares this one color."""
    overrides = _hsc_get_category_colors()
    colors = {}
    for gi, (gid, _label) in enumerate(groups):
        default = _HSC_TILE_PALETTE[gi % len(_HSC_TILE_PALETTE)]
        colors[gid] = _hsc_valid_hex_color(overrides.get(gid), default)
    return colors


_HSC_ADMIN_USERNAME = os.environ["HSC_ADMIN_USERNAME"]
_HSC_ADMIN_PASSWORD = os.environ["HSC_ADMIN_PASSWORD"]
_HSC_BASE_URL = "http://localhost:8088"


# ---------------------------------------------------------------------------
# Ryobi Systems company logo (client-supplied SVG, RL-company_logo-en.svg).
# CSS classes/gradient id renamed from the original file's generic a/b/c so
# this can be embedded inline in the homepage alongside other markup without
# its <style> block (a real, page-global stylesheet once inlined, not
# scoped to just this SVG) colliding with an unrelated ".a"/".b"/".c" class
# anywhere else on the page.
# ---------------------------------------------------------------------------
_HSC_RL_LOGO_INNER = """<defs><style>.hsc-rl-a{fill:#1255a3;}.hsc-rl-b{fill:url(#hsc-rl-grad);}.hsc-rl-c{fill:#fff;}</style><linearGradient id="hsc-rl-grad" x1="328.89" y1="328.9" x2="7.21" y2="7.22" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#1255a3"/><stop offset="0.2" stop-color="#1255a3"/><stop offset="0.85" stop-color="#5fd2ff"/><stop offset="1" stop-color="#5fd2ff"/></linearGradient></defs><title>RL-company_logo-en</title><path class="hsc-rl-a" d="M1568.52,226.09h-79.66V66.68h-57.15V275h136.81Z"/><path class="hsc-rl-a" d="M1744.15,275h51.52L1704.75,66.68H1667L1576,275h51.52l18.29-41.74h80Zm-79.62-84.36L1685.85,142l21.32,48.63Z"/><path class="hsc-rl-a" d="M645.14,170.85q12-15.1,12-39.37A68.7,68.7,0,0,0,651,102.35a55.7,55.7,0,0,0-17.38-21.72,61.59,61.59,0,0,0-23.74-10.74q-13.81-3.24-48.86-3.2H501.44V275H555V193.38l48,81.61h64.51L610.3,191Q633.21,186,645.14,170.85Zm-52.58-12c-5.7,4.15-14.71,6.29-27,6.29H555V110.35h11.43q18.74,0,26.69,6.63c5.32,4.38,8,11.82,8,22.22C601.06,148.15,598.22,154.68,592.56,158.84Z"/><path class="hsc-rl-a" d="M781.27,66.67,750.4,120.33c-.22.36-.61,1.1-1.21,2.17-3.1,5.67-5.2,10.8-6.08,15.48a67.23,67.23,0,0,0-6.19-16.08,7.09,7.09,0,0,0-.87-1.57l-31-53.66H642.61l73,113.3v95h55V180l73-113.3Z"/><path class="hsc-rl-a" d="M1005.83,93.57a111.2,111.2,0,0,0-36.4-23.71,114.92,114.92,0,0,0-86,0,110.51,110.51,0,0,0-36.14,23.71,104.55,104.55,0,0,0-24.49,35.2,109.47,109.47,0,0,0,0,84,105,105,0,0,0,24.49,35.35,109.24,109.24,0,0,0,36.14,23.65,114.88,114.88,0,0,0,122.41-23.65,107.67,107.67,0,0,0,0-154.56ZM965.64,214.68Q950.12,232,926.39,232c-16.16,0-29.3-5.74-39.53-17.16s-15.29-26.21-15.29-44c0-17.57,5.21-32.17,15.53-43.77s23.41-17.45,39.29-17.45c15.48,0,28.51,5.88,39,17.49s15.72,26.31,15.72,43.73C981.13,188.47,976,203.06,965.64,214.68Z"/><path class="hsc-rl-a" d="M1169.79,163c13.2-3.57,22.86-8.91,28.87-15.89s9.12-16.42,9.12-28.3a49.77,49.77,0,0,0-6.13-24.91A44.8,44.8,0,0,0,1184,76.75c-6.75-3.69-14.8-6.27-24.18-7.84s-25.84-2.22-49.51-2.22h-57.13V275h58.87c23.87,0,41-.75,51.47-2.34s19.36-4.44,26.48-8.17a48.44,48.44,0,0,0,20.21-19.63c4.72-8.45,7.09-18.15,7.09-29.28,0-15.44-4.17-27.76-12.61-36.94S1184.71,164.17,1169.79,163ZM1106,107.8h12.27q21.32,0,28.63,4.77c4.93,3.2,7.4,8.82,7.4,16.68,0,7.69-2.63,13-7.88,16.11s-14.88,4.75-29,4.75H1106Zm48.73,119.51c-5.62,3.38-15.22,5.05-28.74,5.05h-20V187.15h20.86c13.9,0,23.42,1.7,28.57,5.2s7.73,9.48,7.73,18.17Q1163.11,222.34,1154.68,227.31Z"/><rect class="hsc-rl-a" x="1233.08" y="66.69" width="57.52" height="208.3"/><path class="hsc-rl-a" d="M1965,93.57a111.2,111.2,0,0,0-36.4-23.71,114.92,114.92,0,0,0-86,0,110.51,110.51,0,0,0-36.14,23.71,104.7,104.7,0,0,0-24.49,35.2,109.47,109.47,0,0,0,0,84,105.17,105.17,0,0,0,24.49,35.35,109.24,109.24,0,0,0,36.14,23.65A114.88,114.88,0,0,0,1965,248.13a107.64,107.64,0,0,0,0-154.56Zm-40.19,121.11Q1909.31,232,1885.58,232c-16.16,0-29.3-5.74-39.53-17.16s-15.28-26.21-15.28-44c0-17.57,5.21-32.17,15.52-43.77s23.42-17.45,39.29-17.45c15.48,0,28.51,5.88,39,17.49s15.72,26.31,15.72,43.73C1940.32,188.47,1935.16,203.06,1924.83,214.68Z"/><path class="hsc-rl-b" d="M109.22,340H26.77A26.77,26.77,0,0,1,0,313.22V192.46C23.87,209.55,88.23,261.69,109.22,340Zm2.31-12.12C118.27,270.48,152.22,119,334,9.89A26.71,26.71,0,0,0,313.22,0H26.77A26.77,26.77,0,0,0,0,26.78V98.2C95,175.39,109.73,288.09,111.53,327.88ZM114.07,340H313.22A26.77,26.77,0,0,0,340,313.22v-164C308.23,157.55,171.64,200.63,114.07,340Z"/><path class="hsc-rl-c" d="M334,9.89C152.22,119,118.27,270.48,111.53,327.88,109.73,288.09,95,175.39,0,98.2v94.26C23.87,209.55,88.23,261.69,109.22,340h4.85C171.64,200.63,308.23,157.55,340,149.26V26.78A26.61,26.61,0,0,0,334,9.89Z"/>"""

_HSC_RL_LOGO_VIEWBOX = "0 0 1997.48 340"


def _hsc_rl_logo_svg(height_css):
    """Standalone, self-contained <svg> for the client's company logo, sized
    via CSS height with the width following automatically (no distortion)."""
    return (
        f'<svg role="img" aria-label="RYOBI LAO" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="{_HSC_RL_LOGO_VIEWBOX}" style="height:{height_css};width:auto;display:block;">'
        f"{_HSC_RL_LOGO_INNER}</svg>"
    )


# Superset's own horizontal wordmark (superset-frontend/src/assets/branding/
# superset-logo-horiz.svg), reused as-is so the combined login-page logo
# below keeps Superset's own mark rather than replacing it outright.
_HSC_SUPERSET_LOGO_INNER = """<path d="M73.79,15.23C67.32,15.23 61.36,18.87 55.6,25.23C49.94,18.77 43.88,15.23 37.11,15.23C25.9,15.23 17.72,23.23 17.72,34C17.72,44.77 25.9,52.67 37.11,52.67C44,52.67 49.34,49.44 55.3,43C61.06,49.46 66.92,52.69 73.79,52.69C85,52.67 93.18,44.8 93.18,34C93.18,23.2 85,15.23 73.79,15.23ZM37.19,41.37C32.44,41.37 29.61,38.24 29.61,34.1C29.61,29.96 32.44,26.74 37.19,26.74C41.19,26.74 44.46,29.96 48,34.3C44.66,38.34 41.13,41.37 37.19,41.37ZM73.45,41.37C69.51,41.37 66.18,38.24 62.64,34.1C66.28,29.76 69.41,26.74 73.45,26.74C78.2,26.74 81,30 81,34.1C81,38.2 78.2,41.37 73.45,41.37Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M63.74,50L71.28,41C68.28,40.1 65.51,37.4 62.64,34.05L55.3,43C57.703,45.788 60.556,48.154 63.74,50Z" style="fill:rgb(32,167,201);fill-rule:nonzero;"/><path d="M116.72,40.39C116.751,39.474 116.36,38.592 115.66,38C114.539,37.193 113.272,36.609 111.93,36.28C109.421,35.66 107.048,34.582 104.93,33.1C103.37,31.922 102.481,30.053 102.55,28.1C102.528,26.015 103.555,24.052 105.28,22.88C107.327,21.458 109.79,20.754 112.28,20.88C114.812,20.767 117.301,21.577 119.28,23.16C120.994,24.509 121.961,26.601 121.88,28.78L121.88,28.88L116.82,28.88C116.861,27.778 116.419,26.71 115.61,25.96C114.667,25.171 113.457,24.773 112.23,24.85C111.077,24.779 109.934,25.104 108.99,25.77C108.263,26.344 107.842,27.224 107.85,28.15C107.867,28.99 108.298,29.769 109,30.23C110.313,31.008 111.726,31.603 113.2,32C115.582,32.553 117.81,33.633 119.72,35.16C121.197,36.462 122.013,38.362 121.94,40.33C122.008,42.418 121.013,44.404 119.3,45.6C117.238,46.985 114.78,47.662 112.3,47.53C109.663,47.589 107.072,46.823 104.89,45.34C102.838,43.996 101.66,41.648 101.81,39.2L101.81,39.09L107,39.09C106.889,40.389 107.42,41.664 108.42,42.5C109.597,43.291 111.004,43.671 112.42,43.58C113.571,43.658 114.716,43.348 115.67,42.7C116.371,42.144 116.762,41.283 116.72,40.39Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M137,44.4C136.453,45.359 135.672,46.164 134.73,46.74C132.116,48.188 128.835,47.72 126.73,45.6C125.583,44.267 125.01,42.24 125.01,39.52L125.01,27.85L130.21,27.85L130.21,39.58C130.131,40.629 130.379,41.678 130.92,42.58C131.434,43.208 132.22,43.551 133.03,43.5C133.767,43.516 134.498,43.38 135.18,43.1C135.764,42.836 136.268,42.422 136.64,41.9L136.64,27.85L141.86,27.85L141.86,47.18L137.41,47.18L137,44.4Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M162.87,38.05C162.99,40.508 162.286,42.937 160.87,44.95C159.569,46.68 157.492,47.658 155.33,47.56C154.4,47.575 153.478,47.384 152.63,47C151.843,46.61 151.158,46.042 150.63,45.34L150.63,54.62L145.43,54.62L145.43,27.85L150.13,27.85L150.44,30.13C150.968,29.331 151.673,28.664 152.5,28.18C153.363,27.707 154.336,27.469 155.32,27.49C157.535,27.403 159.644,28.467 160.89,30.3C162.313,32.49 163.013,35.072 162.89,37.68L162.87,38.05ZM157.65,37.65C157.71,36.118 157.397,34.595 156.74,33.21C156.228,32.144 155.132,31.476 153.95,31.51C153.253,31.49 152.562,31.656 151.95,31.99C151.393,32.322 150.937,32.799 150.63,33.37L150.63,41.86C150.942,42.394 151.4,42.828 151.95,43.11C152.573,43.411 153.259,43.558 153.95,43.54C155.082,43.61 156.161,43.032 156.73,42.05C157.376,40.819 157.684,39.439 157.62,38.05L157.65,37.65Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M174.21,47.56C171.699,47.674 169.258,46.696 167.52,44.88C165.828,43.026 164.93,40.579 165.02,38.07L165.02,37.36C164.918,34.784 165.761,32.258 167.39,30.26C170.696,26.757 176.29,26.572 179.82,29.85C181.338,31.617 182.119,33.903 182,36.23L182,39.07L170.43,39.07L170.43,39.18C170.48,40.34 170.933,41.447 171.71,42.31C172.51,43.146 173.634,43.595 174.79,43.54C175.762,43.562 176.732,43.444 177.67,43.19C178.539,42.91 179.377,42.542 180.17,42.09L181.58,45.32C180.656,46.037 179.609,46.579 178.49,46.92C177.108,47.366 175.662,47.582 174.21,47.56ZM173.74,31.56C172.841,31.53 171.983,31.946 171.45,32.67C170.859,33.531 170.513,34.537 170.45,35.58L170.5,35.67L176.9,35.67L176.9,35.21C176.949,34.261 176.674,33.322 176.12,32.55C175.546,31.835 174.655,31.446 173.74,31.51L173.74,31.56Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M195.3,32.33L193.38,32.33C192.711,32.303 192.047,32.47 191.47,32.81C190.964,33.141 190.567,33.614 190.33,34.17L190.33,47.18L185.13,47.18L185.13,27.85L190,27.85L190.23,30.71C190.616,29.787 191.224,28.972 192,28.34C192.71,27.776 193.594,27.476 194.5,27.49C194.741,27.488 194.982,27.508 195.22,27.55L195.89,27.7L195.3,32.33Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M208.32,41.86C208.308,41.257 207.996,40.698 207.49,40.37C206.544,39.809 205.498,39.435 204.41,39.27C202.553,38.979 200.785,38.271 199.24,37.2C198.087,36.32 197.433,34.93 197.49,33.48C197.487,31.814 198.265,30.24 199.59,29.23C201.198,28.003 203.19,27.386 205.21,27.49C207.312,27.38 209.391,27.991 211.1,29.22C212.489,30.234 213.279,31.882 213.2,33.6L213.2,33.71L208.2,33.71C208.226,33.002 207.958,32.314 207.46,31.81C206.859,31.287 206.074,31.024 205.28,31.08C204.561,31.04 203.85,31.26 203.28,31.7C202.816,32.075 202.55,32.644 202.56,33.24C202.551,33.826 202.837,34.379 203.32,34.71C204.271,35.243 205.318,35.582 206.4,35.71C208.308,35.991 210.126,36.71 211.71,37.81C212.862,38.729 213.506,40.148 213.44,41.62C213.458,43.325 212.62,44.93 211.21,45.89C209.473,47.062 207.403,47.641 205.31,47.54C203.1,47.652 200.925,46.939 199.21,45.54C197.817,44.508 196.996,42.873 197,41.14L197,41.04L201.77,41.04C201.72,41.907 202.093,42.746 202.77,43.29C203.515,43.784 204.397,44.029 205.29,43.99C206.067,44.039 206.838,43.835 207.49,43.41C208.012,43.069 208.326,42.484 208.32,41.86Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M224.86,47.56C222.352,47.674 219.914,46.696 218.18,44.88C216.488,43.026 215.59,40.579 215.68,38.07L215.68,37.36C215.579,34.786 216.419,32.261 218.04,30.26C221.346,26.757 226.94,26.572 230.47,29.85C231.992,31.615 232.77,33.903 232.64,36.23L232.64,39.07L221.09,39.07L221.09,39.18C221.137,40.339 221.587,41.446 222.36,42.31C223.162,43.149 224.291,43.598 225.45,43.54C226.419,43.562 227.385,43.444 228.32,43.19C229.193,42.912 230.034,42.544 230.83,42.09L232.24,45.32C231.315,46.035 230.268,46.577 229.15,46.92C227.765,47.366 226.315,47.582 224.86,47.56ZM224.4,31.56C223.5,31.526 222.641,31.943 222.11,32.67C221.519,33.532 221.174,34.537 221.11,35.58L221.17,35.67L227.57,35.67L227.57,35.21C227.619,34.261 227.344,33.322 226.79,32.55C226.214,31.832 225.318,31.442 224.4,31.51L224.4,31.56Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M242.35,23.11L242.35,27.85L245.61,27.85L245.61,31.51L242.35,31.51L242.35,41.36C242.296,41.937 242.465,42.513 242.82,42.97C243.15,43.299 243.604,43.474 244.07,43.45C244.304,43.451 244.538,43.435 244.77,43.4C245.003,43.363 245.233,43.313 245.46,43.25L245.91,47.02C245.408,47.195 244.893,47.332 244.37,47.43C243.834,47.516 243.293,47.56 242.75,47.56C241.219,47.662 239.712,47.126 238.59,46.08C237.508,44.765 236.984,43.077 237.13,41.38L237.13,31.51L234.31,31.51L234.31,27.85L237.13,27.85L237.13,23.11L242.35,23.11Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/><path d="M55.6,25.22C53.213,22.392 50.378,19.973 47.21,18.06L39.66,27.16C42.53,28.16 45.07,30.74 47.77,34.03L48.07,34.24L55.6,25.22Z" style="fill:rgb(32,167,201);fill-rule:nonzero;"/><path d="M248.77,23.62L247.92,23.62L247.92,26.28L247.37,26.28L247.37,23.62L246.52,23.62L246.52,23.14L248.77,23.14L248.77,23.62ZM251.93,24.27L251.05,26.27L250.75,26.27L249.84,24.17L249.84,26.26L249.3,26.26L249.3,23.14L249.98,23.14L250.92,25.42L251.92,23.14L252.57,23.14L252.57,26.28L252.02,26.28L251.93,24.27Z" style="fill:rgb(72,72,72);fill-rule:nonzero;"/>"""


def _hsc_combined_brand_logo_svg():
    """Superset's own wordmark plus the client's company logo, side by side
    in one image -- used as APP_ICON (§4.1) so it shows in the same slot
    Superset's nav/login page already renders its own logo in, without a
    frontend rebuild (Superset's nav only supports one logo image, not a
    second slot next to it)."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 433 56">
  <svg x="8" y="8" width="154.2" height="40" viewBox="0 0 266 69">{_HSC_SUPERSET_LOGO_INNER}</svg>
  <line x1="176" y1="10" x2="176" y2="46" stroke="#D8DCE1" stroke-width="1"/>
  <svg x="188" y="8" width="235" height="40" viewBox="{_HSC_RL_LOGO_VIEWBOX}">{_HSC_RL_LOGO_INNER}</svg>
</svg>"""


def _hsc_admin_api_session():
    """A logged-in requests.Session talking to Superset's own REST API.

    Used only to create/tag a dashboard on a real employee's behalf when
    they click a "coming soon" tile -- the employee's own Alpha role (see
    docs/00-runbook.md §5k) already lets them do this through Superset's UI
    directly too; this just automates the first step (create + tag + land
    them in the editor) instead of making them do it by hand.
    """
    import requests

    s = requests.Session()
    login = s.post(
        f"{_HSC_BASE_URL}/api/v1/security/login",
        json={
            "username": _HSC_ADMIN_USERNAME,
            "password": _HSC_ADMIN_PASSWORD,
            "provider": "db",
            "refresh": True,
        },
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    csrf = s.get(f"{_HSC_BASE_URL}/api/v1/security/csrf_token/", headers=headers).json()["result"]
    headers["X-CSRFToken"] = csrf
    headers["Referer"] = _HSC_BASE_URL
    headers["Content-Type"] = "application/json"
    return s, headers


def _hsc_can_create_dashboard(user):
    """Alpha/Admin can create dashboards (has all_datasource_access, needed
    to actually build charts inside one -- see docs/00-runbook.md §5l);
    Gamma cannot. Used to hide the homepage's own "+ Dashboard" button from
    anyone whose role wouldn't be able to use it anyway."""
    role_names = {r.name for r in getattr(user, "roles", [])}
    return bool(role_names & {"Alpha", "Admin"})


def _hsc_all_employee_user_ids():
    """Every non-admin Superset user id -- used to grant `editors` access
    on a freshly created dashboard. See _hsc_create_dashboard_for_tile for
    why this is necessary, not just generous."""
    try:
        from superset.extensions import db
        from flask_appbuilder.security.sqla.models import User

        rows = db.session.query(User.id).filter(User.username != _HSC_ADMIN_USERNAME).all()
        return [r[0] for r in rows]
    except Exception:
        return []


def _hsc_create_tagged_dashboard(title, group):
    """Create + tag + publish a real dashboard, ready to show up on the
    homepage via the normal hsc:* tag mechanism (§6.3 of the work plan).

    Uses the dashboard REST API itself (not a guessed "max id + 1") so the
    real id is whatever Superset actually assigns -- reading it back from
    the create response is the only reliable way to know it.

    Real bug hit and fixed here, worth remembering: this fork does NOT use
    classic Superset "owners" for dashboard visibility (`owners` is rejected
    outright by the create schema -- "Unknown field.") -- it uses an
    editors/viewers access model instead (superset/dashboards/filters.py,
    DashboardAccessFilter). A brand-new dashboard with none of: explicit
    editors, explicit viewers, or at least one chart, is **invisible to
    everyone, including Admin** -- confirmed by testing: a dashboard created
    with no `editors` 404'd as "Dashboard not found" even loaded as the
    admin account. The "no viewer -> fall back to dataset access" rule
    (case C in DashboardAccessFilter) requires an inner join through at
    least one real chart+dataset+database, so it never fires for an empty
    dashboard no matter who's asking. Fixed by setting `editors` to every
    employee's user id at creation time, so whoever opens the tile next
    can also see and keep building it -- not just the original creator.
    """
    s, headers = _hsc_admin_api_session()
    payload = {
        "dashboard_title": title,
        "published": True,
        "editors": _hsc_all_employee_user_ids(),
    }
    r = s.post(f"{_HSC_BASE_URL}/api/v1/dashboard/", headers=headers, json=payload)
    r.raise_for_status()
    new_id = r.json()["id"]
    tag_name = f"hsc:{group}"
    s.post(f"{_HSC_BASE_URL}/api/v1/tag/3/{new_id}/", headers=headers, json={"properties": {"tags": [tag_name]}})
    return new_id


def _hsc_recategorize_dashboard(dash_id, old_group, new_group):
    """Move a real, already-tagged dashboard from one category to another --
    dragging its card to a different column on the settings page's category
    kanban board (§5aq). Unlike a personal section (§5ap), this is a shared,
    org-wide change: every employee sees the dashboard under its new
    category immediately, the same as a category-color change already is
    (§6.9 of the work plan).

    Object type `3` is Superset's own dashboard ObjectType (superset/tags/
    models.py) -- same value already used by _hsc_create_tagged_dashboard
    above. Adds the new tag before removing the old one (not the reverse),
    so the dashboard is never briefly untagged -- and therefore briefly
    invisible on every employee's homepage, §6.3's tag mechanism -- if the
    second call were to fail.
    """
    from urllib.parse import quote

    s, headers = _hsc_admin_api_session()
    new_tag = f"hsc:{new_group}"
    old_tag = f"hsc:{old_group}"
    r = s.post(f"{_HSC_BASE_URL}/api/v1/tag/3/{dash_id}/", headers=headers, json={"properties": {"tags": [new_tag]}})
    r.raise_for_status()
    r = s.delete(f"{_HSC_BASE_URL}/api/v1/tag/3/{dash_id}/{quote(old_tag, safe='')}/", headers=headers)
    r.raise_for_status()


def _hsc_import_dashboard_bundle(file_storage):
    """Forward an uploaded Superset export (.zip or .json) to Superset's own
    /api/v1/dashboard/import/ endpoint. Returns Superset's own response body.

    Deliberately does NOT try to auto-tag/publish/set-editors on whatever
    gets imported -- an export can bundle multiple dashboards, charts, and
    datasets, and this endpoint's response only ever contains a plain
    {"message": ...}, never the id(s) of what was created (checked the
    actual handler source, superset.dashboards.api.DashboardRestApi.import_,
    before assuming). Point the person at Superset's own dashboard list
    afterward so they can tag + publish whatever came in through the normal
    UI -- same as they would if they'd used Superset's native import button.
    """
    s, headers = _hsc_admin_api_session()
    headers = dict(headers)
    headers.pop("Content-Type", None)  # let `requests` set the multipart boundary itself
    files = {
        "formData": (
            file_storage.filename,
            file_storage.read(),
            file_storage.content_type or "application/octet-stream",
        )
    }
    r = s.post(
        f"{_HSC_BASE_URL}/api/v1/dashboard/import/",
        headers=headers,
        files=files,
        data={"overwrite": "true"},
    )
    r.raise_for_status()
    return r.json()


def _hsc_create_dashboard_for_tile(tile, owner_user_id):
    return _hsc_create_tagged_dashboard(tile["label"], tile["group"])


def _hsc_get_placeholder_link(tile_id):
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT dashboard_id FROM hsc_placeholder_dashboard_links WHERE tile_id = %s",
                    (tile_id,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            conn.close()
    except Exception:
        return None


def _hsc_save_placeholder_link(tile_id, dashboard_id, created_by):
    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hsc_placeholder_dashboard_links (tile_id, dashboard_id, created_by)
                VALUES (%s, %s, %s)
                ON CONFLICT (tile_id) DO NOTHING
                """,
                (tile_id, dashboard_id, created_by),
            )
        conn.commit()
    finally:
        conn.close()


def _hsc_db_conn():
    import psycopg2

    return psycopg2.connect(_HSC_DB_DSN)


def _hsc_get_settings(email):
    try:
        conn = _hsc_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT settings FROM hsc_user_menu_prefs WHERE user_email = %s",
                    (email,),
                )
                row = cur.fetchone()
                return row[0] if row else {}
        finally:
            conn.close()
    except Exception:
        # A DB hiccup should degrade to "everyone's defaults", not a 500.
        return {}


def _hsc_save_settings(email, settings):
    import json

    conn = _hsc_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO hsc_user_menu_prefs (user_email, settings, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (user_email)
                DO UPDATE SET settings = EXCLUDED.settings, updated_at = now()
                """,
                (email, json.dumps(settings)),
            )
        conn.commit()
    finally:
        conn.close()


def _hsc_valid_hex_color(value, fallback):
    import re

    return value if value and re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else fallback


def _hsc_hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _hsc_tint(hex_color, amount):
    """Mix a color toward white -- amount 0 (no change) to 1 (white)."""
    r, g, b = _hsc_hex_to_rgb(hex_color)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return "#%02X%02X%02X" % (r, g, b)


def _hsc_shade(hex_color, amount, base="#0D1117"):
    """Mix a color toward a dark base -- _hsc_tint()'s dark-mode counterpart
    (that one only ever mixes toward white). `base` defaults to a near-black
    navy rather than pure #000 so a shaded accent still reads as "this
    product's dark chrome", not a generic invert."""
    r, g, b = _hsc_hex_to_rgb(hex_color)
    br, bg, bb = _hsc_hex_to_rgb(base)
    r = int(r + (br - r) * amount)
    g = int(g + (bg - g) * amount)
    b = int(b + (bb - b) * amount)
    return "#%02X%02X%02X" % (r, g, b)


def _hsc_theme_style_block(accent):
    """The CSS custom-property tokens both custom pages (`_hsc_render_menu_page`,
    `_hsc_render_settings_page`) theme themselves from -- one definition,
    included in both `<style>` blocks, so light/dark/density never drift
    between the two pages.

    V6 "Enterprise Ready" correction pass (2026-09-10): LIGHT mode is the
    flagship experience -- soft neutral page background, white cards, dark
    navy ink, subtle cool borders. Dark mode remains a proper transformation
    of the same design (same component classes, same `--hsc-*` token names),
    still reachable via the saved `theme_mode` / the OS setting, but it is
    no longer the visual default: both pages now stamp `data-theme="light"`
    when the person has never chosen a mode, and "System" keeps working by
    leaving the attribute off (the `prefers-color-scheme` tier below).

    Three-tier cascade for `--hsc-*`: light values live on bare `:root`; a
    `prefers-color-scheme: dark` block supplies dark values for "System"
    mode (guarded by `:not([data-theme="light"])` so an explicit Light
    choice always wins over the OS setting); `:root[data-theme="dark"]`
    supplies the same dark values again for an explicit Dark choice.

    `--hsc-bg` stays accent-derived (the long-standing "picking a color
    re-themes the whole page" promise) but only faintly in light mode
    (mixed 96.5% toward white, so the page reads as premium neutral with a
    whisper of the chosen brand color, not a wall of tint) and via a deep
    navy-shaded mix in dark mode.
    """
    light_bg = _hsc_tint(accent, 0.965)
    dark_bg = _hsc_shade(accent, 0.88, base="#10151C")
    dark_tokens = f"""
    --hsc-ink:#E8ECF1; --hsc-ink-muted:#9AA4B2; --hsc-ink-faint:#6B7686;
    --hsc-surface:#161B22; --hsc-surface-2:#1D232C; --hsc-surface-3:#252C37;
    --hsc-border:#2C3440; --hsc-border-strong:#3D4754;
    --hsc-bg:{dark_bg};
    --hsc-badge-live-fg:#4ADE80; --hsc-badge-live-bg:rgba(74,222,128,0.14);
    --hsc-badge-soon-fg:#FBBF24; --hsc-badge-soon-bg:rgba(251,191,36,0.14);
    --hsc-badge-na-fg:#9AA4B2; --hsc-badge-na-bg:rgba(154,164,178,0.14);
    --hsc-card-shadow:0 1px 2px rgba(0,0,0,0.35);
    --hsc-card-hover-shadow:0 12px 28px rgba(0,0,0,0.50);
    --hsc-icon-tile:#222A35;"""
    # Adaptive ink for accent-filled chrome (buttons, selected nav pills).
    # Computed HERE, not passed in, so every call site gets the same
    # contrast-correct pairing for free (the first render after adding the
    # shared component CSS referenced header_ink without defining it -- a
    # 500 caught immediately by the running container).
    header_ink = _hsc_ink_on(accent)
    return f"""
:root {{
  color-scheme: light;
  --hsc-ink:#141B2A; --hsc-ink-muted:#5B6675; --hsc-ink-faint:#8B94A3;
  --hsc-surface:#FFFFFF; --hsc-surface-2:#F6F8FA; --hsc-surface-3:#EEF1F5;
  --hsc-border:#E2E6ED; --hsc-border-strong:#C9D0DA;
  --hsc-bg:{light_bg};
  --hsc-badge-live-fg:#177E3D; --hsc-badge-live-bg:#E4F6EA;
  --hsc-badge-soon-fg:#9A6700; --hsc-badge-soon-bg:#FCF1CE;
  --hsc-badge-na-fg:#667085; --hsc-badge-na-bg:#EDF0F4;
  --hsc-card-shadow:0 1px 2px rgba(16,24,40,0.05);
  --hsc-card-hover-shadow:0 12px 24px rgba(16,24,40,0.10);
  --hsc-icon-tile:#F1F4F8;
  --hsc-radius:14px; --hsc-radius-sm:10px;
  --hsc-card-pad:16px 18px; --hsc-card-gap:10px; --hsc-col-gap:14px; --hsc-col-body-pad:16px;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{{dark_tokens}
  }}
}}
:root[data-theme="light"] {{ color-scheme: light; }}
:root[data-theme="dark"] {{{dark_tokens}
  color-scheme: dark;
}}
:root[data-density="compact"] {{
  --hsc-card-pad:10px 12px; --hsc-card-gap:6px; --hsc-col-gap:8px; --hsc-col-body-pad:10px;
}}
/* Canonical visually-hidden recipe (modern-web-guidance's accessibility
   guide) -- for real `<label>`s and skip links that shouldn't be seen but
   must stay in the accessibility tree and tab order. NOT `display:none`,
   which would remove them from both. */
.hsc-vh:where(:not(:focus-within, :active)) {{
  position: absolute !important;
  clip-path: inset(50%) !important;
  overflow: hidden !important;
  width: 1px !important;
  height: 1px !important;
  margin: -1px !important;
  padding: 0 !important;
  border: 0 !important;
  white-space: nowrap !important;
}}
.hsc-skip-link {{
  position: absolute; top: -1000px; left: 8px; z-index: 1000;
  background: var(--hsc-surface); color: var(--hsc-ink); padding: 10px 16px;
  border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); text-decoration: none; font-weight: 700;
}}
.hsc-skip-link:focus {{ top: 8px; }}
/* ----------------------------------------------------------------------
   Shared components (both custom pages) -- one definition here so the
   homepage and settings page can't drift apart. Component classes, not
   one-off inline styles: hover/focus/disabled states are impossible to
   express inline.
   ---------------------------------------------------------------------- */
[id] {{ scroll-margin-top: 16px; }}
[hidden] {{ display: none !important; }}
/* The custom pages own their full 1440–1480px application shell; make
   sure nothing in the surrounding Superset chrome re-constrains them
   (a fork regression earlier in this pass proved a wrapper cap is
   stronger than any max-width set on content inside it). */
body superset-root {{ font-family:Arial,"Noto Sans",sans-serif; width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0 !important; }}
/* One keyboard-focus recipe for every native control on both pages, so
   tabbing through a form never loses the ring on bare inputs/selects. */
input:focus-visible, select:focus-visible, textarea:focus-visible, button:focus-visible,
a:focus-visible {{ outline: 2px solid {accent}; outline-offset: 2px; }}
/* Buttons -- 44px control height, real horizontal padding, 14px label:
   commercial-enterprise scale, not a dense console. */
.hsc-btn {{
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  border-radius: var(--hsc-radius-sm); font-weight: 700; font-size: 14px;
  padding: 11px 22px; text-decoration: none; cursor: pointer;
  border: 1px solid transparent; font-family: inherit; line-height: 1.2;
}}
.hsc-btn-primary {{ background: {accent}; color: {header_ink}; box-shadow: 0 1px 2px rgba(16,24,40,0.10); }}
.hsc-btn-primary:hover {{ filter: brightness(1.06); }}
.hsc-btn-ghost {{ background: var(--hsc-surface); color: var(--hsc-ink); border-color: var(--hsc-border-strong); }}
.hsc-btn-ghost:hover {{ background: var(--hsc-surface-2); }}
.hsc-btn-primary:focus-visible, .hsc-btn-ghost:focus-visible,
.hsc-search-clear:focus-visible, .hsc-nav-link:focus-visible {{
  outline: 2px solid {accent}; outline-offset: 2px;
}}
/* Search bar (homepage) -- a major discovery tool, not a utility: large
   (fluid min()), 46px tall, prominent shadow, focus ring on the WRAPPER,
   clear button, "/" shortcut hint. */
.hsc-toolbar {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }}
.hsc-searchbar {{
  display: flex; align-items: center; gap: 12px;
  background: var(--hsc-surface); border: 1px solid var(--hsc-border);
  border-radius: 12px; padding: 12px 18px; width: min(680px, 100%);
  box-shadow: 0 1px 3px rgba(16,24,40,0.07), 0 1px 2px rgba(16,24,40,0.04);
}}
.hsc-searchbar:focus-within {{ border-color: {accent}; box-shadow: 0 0 0 3px {accent}33; }}
.hsc-searchbar input {{
  flex: 1; min-width: 0; border: none; background: transparent;
  color: var(--hsc-ink); font-size: 14.5px; outline: none; font-family: inherit;
}}
.hsc-searchbar input::placeholder {{ color: var(--hsc-ink-faint); }}
.hsc-search-clear {{
  border: none; background: var(--hsc-surface-2); color: var(--hsc-ink-muted);
  width: 24px; height: 24px; border-radius: 6px; cursor: pointer;
  font-size: 12px; line-height: 1; flex: 0 0 auto; padding: 0;
}}
.hsc-search-kbd {{
  font-size: 11px; font-weight: 700; color: var(--hsc-ink-muted); border: 1px solid var(--hsc-border);
  border-bottom-width: 2px; border-radius: 6px; padding: 3px 8px; background: var(--hsc-surface-2); flex: 0 0 auto;
}}
/* Empty states (no dashboards at all / no search hits) -- honest, calm,
   with a single next action rather than a dead grey box. */
.hsc-empty {{
  background: var(--hsc-surface); border: 1.5px dashed var(--hsc-border);
  border-radius: var(--hsc-radius); padding: 48px 24px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}}
.hsc-empty-title {{ font-size: 17px; font-weight: 700; color: var(--hsc-ink); margin: 0; }}
.hsc-empty-hint {{ font-size: 14px; color: var(--hsc-ink-muted); margin: 0; max-width: 480px; line-height: 1.6; }}
/* Disabled dashboard cards (out-of-scope tiles): greyed icon + muted title
   make the whole card read as inert at a glance, not just the badge. */
.hsc-card-na {{ cursor: default; }}
.hsc-card-na:hover {{ transform: none; box-shadow: var(--hsc-card-shadow); border-color: var(--hsc-border); }}
.hsc-card-na .hsc-card-icon {{ opacity: 0.45; filter: grayscale(1); }}
.hsc-card-na .hsc-card-title {{ color: var(--hsc-ink-muted); }}
/* Settings shell -- TRUE section switching, not one long scroll page:
   a premium 232px sidebar with one-line descriptions controls which
   settings view fills the workspace (server-side via ?view=, one major
   area at a time). Active item: soft pink surface + accent edge bar. */
.hsc-settings-shell {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 24px; }}
.hsc-settings-nav {{
  display: flex; gap: 6px; overflow-x: auto;
  background: var(--hsc-surface); border: 1px solid var(--hsc-border);
  border-radius: var(--hsc-radius); padding: 10px; box-shadow: var(--hsc-card-shadow);
}}
.hsc-nav-link {{
  flex: 0 0 auto; font-size: 14px; font-weight: 600; color: var(--hsc-ink-muted);
  text-decoration: none; padding: 10px 16px; border-radius: var(--hsc-radius-sm);
  white-space: nowrap; border: 1px solid transparent;
  display: inline-flex; align-items: center; gap: 10px;
}}
.hsc-nav-link:hover {{ color: var(--hsc-ink); background: var(--hsc-surface-2); }}
.hsc-nav-icon {{ display: inline-flex; width: 18px; height: 18px; flex: 0 0 auto; }}
.hsc-nav-icon svg {{ width: 18px; height: 18px; }}
.hsc-nav-text {{ display: flex; flex-direction: column; gap: 1px; min-width: 0; }}
.hsc-nav-desc {{ display: none; font-size: 11.5px; font-weight: 500; color: var(--hsc-ink-faint); line-height: 1.45; white-space: normal; }}
.hsc-nav-link[aria-current="location"] {{
  background: {accent}14; color: {accent}; font-weight: 700; border-color: {accent}3D;
  box-shadow: inset 3px 0 0 {accent};
}}
.hsc-dirty-hint {{
  margin: 10px 4px 0; font-size: 12px; font-weight: 600;
  color: var(--hsc-badge-soon-fg); background: var(--hsc-badge-soon-bg);
  padding: 8px 12px; border-radius: var(--hsc-radius-sm); white-space: nowrap;
}}
@media (min-width: 1024px) {{
  .hsc-settings-shell {{ grid-template-columns: 232px minmax(0, 1fr); align-items: start; gap: 28px; }}
  .hsc-settings-nav {{ flex-direction: column; overflow: visible; position: sticky; top: 24px; padding: 12px; gap: 4px; }}
  .hsc-nav-link {{ padding: 10px 12px; align-items: flex-start; }}
  .hsc-nav-link .hsc-nav-icon {{ margin-top: 2px; }}
  .hsc-nav-desc {{ display: block; }}
  .hsc-dirty-hint {{ white-space: normal; }}
}}
/* The create/import form cards flow as a responsive grid instead of
   one narrow centered column. */
.hsc-form-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-top: 16px; }}
/* Appearance: a composed two-column view (settings left, live miniature
   of the themed homepage right) so every choice is understood, not
   guessed -- the direct fix for "the page has huge empty space and no
   context". The miniature re-uses the page's real --hsc-* tokens, so
   picking a color re-themes the preview in the same second. */
.hsc-appearance-grid {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 24px; align-items: start; }}
@media (min-width: 1100px) {{ .hsc-appearance-grid {{ grid-template-columns: minmax(0, 1fr) 330px; }} }}
.hsc-look-preview {{ background: var(--hsc-surface); border: 1px solid var(--hsc-border); border-radius: var(--hsc-radius);
  padding: 18px; box-shadow: var(--hsc-card-shadow); }}
.hsc-look-frame {{ background: var(--hsc-bg); border: 1px solid var(--hsc-border); border-radius: 12px; padding: 12px;
  display: flex; flex-direction: column; gap: 10px; }}
.hsc-look-header {{ background: linear-gradient(115deg,#081C26 0%,#0C3038 55%,#0E3A42 100%); border-radius: 9px; padding: 9px 12px;
  display: flex; align-items: center; gap: 8px; }}
.hsc-look-logo {{ width: 18px; height: 18px; border-radius: 5px; background: rgba(255,255,255,0.92); flex: 0 0 auto; }}
.hsc-look-brand {{ color: rgba(255,255,255,0.92); font-size: 11px; font-weight: 700; white-space: nowrap; }}
.hsc-look-spacer {{ flex: 1; }}
.hsc-look-pill {{ background: {accent}; color: {header_ink}; font-size: 9.5px; font-weight: 700; border-radius: 5px; padding: 3px 8px; white-space: nowrap; }}
.hsc-look-search {{ background: var(--hsc-surface); border: 1px solid var(--hsc-border); border-radius: 9px; padding: 8px 11px;
  display: flex; align-items: center; gap: 8px; color: var(--hsc-ink-faint); font-size: 11px; box-shadow: var(--hsc-card-shadow); }}
.hsc-look-cards {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
.hsc-look-card {{ background: var(--hsc-surface); border: 1px solid var(--hsc-border); border-radius: 10px; padding: 10px;
  display: flex; flex-direction: column; gap: 7px; box-shadow: var(--hsc-card-shadow); }}
.hsc-look-tile {{ width: 26px; height: 26px; border-radius: 7px; flex: 0 0 auto; }}
.hsc-look-line {{ height: 6px; border-radius: 3px; background: var(--hsc-surface-3); width: 80%; }}
.hsc-look-line-short {{ width: 55%; }}
.hsc-look-badge {{ align-self: flex-start; font-size: 8.5px; font-weight: 700; border-radius: 8px; padding: 2px 7px;
  background: var(--hsc-badge-live-bg); color: var(--hsc-badge-live-fg); }}
.hsc-look-badge-soon {{ background: var(--hsc-badge-soon-bg); color: var(--hsc-badge-soon-fg); }}
/* Drag-and-drop feedback: the dragging row dims, drop targets get a dashed
   accent outline so the insertion point is visible BEFORE release. */
.hsc-dragging {{ opacity: 0.45; }}
.hsc-drop-target {{ outline: 2px dashed {accent}; outline-offset: -2px; }}
/* Visual drag feedback for the mouse path: rows lift while dragging, and
   a 3px accent insertion line paints on the row BEFORE the drop. */
.hsc-row-dragging {{ opacity: 0.5; box-shadow: 0 10px 24px rgba(16,24,40,0.18); }}
.hsc-row-over-top {{ box-shadow: inset 0 3px 0 {accent}; }}
.hsc-row-over-bottom {{ box-shadow: inset 0 -3px 0 {accent}; }}
.hsc-drag-ghost {{ position: fixed; top: -200px; left: -200px; z-index: -1; }}
/* Native-drag text-selection guard: while any drag is active, dragging the
   grab handles must not select neighbouring text. */
body.hsc-drag-active {{ user-select:none; -webkit-user-select:none; }}
"""


def _hsc_is_light(hex_color):
    """True when hex_color is pale enough that white text/icons on it (or on
    a translucent-white pill sitting in front of it) go unreadable -- e.g. a
    user picking white/near-white as their theme color in menu-settings.
    Standard perceived-luminance formula."""
    r, g, b = _hsc_hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 170


def _hsc_ink_on(hex_color, dark="#1B2126", light="#FFFFFF"):
    """Pick a readable ink color for content sitting on top of hex_color."""
    return dark if _hsc_is_light(hex_color) else light


# Rotating palette for service-card colors -- filled (accent) for live tiles,
# outlined-on-tint for not-yet-built ones. Distinct from the personalized
# `accent` color, which is instead used for chrome (header, badges, the
# live-tile ring) so a person's color choice is visible without making every
# card the same color -- deliberately closer to a colorful service-card grid
# than the flat single-hue directory board this replaced.
_HSC_TILE_PALETTE = ["#EF476F", "#4C6EF5", "#12B886", "#F59F00", "#7048E8", "#0CA5B0", "#E8590C", "#D6336C"]

# Locales that read right-to-left (audit F05). Superset's own LANGUAGES dict
# carries no direction metadata, and `<html lang="ar">` alone still lays the
# document out LTR (verified in the audit) -- the `dir` attribute is what
# actually flips it. Kept as a data-driven set so a future RTL locale
# addition is a one-line change, not a template hunt.
_HSC_RTL_LOCALES = {"ar", "fa", "he", "ur"}


def _hsc_dir_attr(lang):
    """` dir="rtl"` for RTL locales, `""` for everything else -- spliced
    straight into both custom pages' <html> tag."""
    return ' dir="rtl"' if str(lang) in _HSC_RTL_LOCALES else ""


def _hsc_lang_key(locale):
    """Map a runtime babel locale back to its LANGUAGES key.

    flask_babel normalizes some session locales, notably `zh_TW` ->
    `zh_Hant_TW` (Babel resolves the script of the Chinese variants), so
    the string that comes back from `str(get_locale())` no longer equals
    the LANGUAGES dict key the user picked. Compare on the normalized
    form of BOTH sides -- `Locale.parse(key)` is stable for every key
    that already is a canonical babel id, and lands `zh_TW` on
    `zh_Hant_TW` too, so the two finally compare equal.
    """
    from babel import Locale as _BabelLocale

    try:
        return str(_BabelLocale.parse(locale))
    except Exception:
        return str(locale)


# Filled-path-only icons (the Markdown/HTML sanitizer here whitelists `fill`
# but not `stroke` on svg/path/circle -- see HTML_SANITIZATION_SCHEMA_EXTENSIONS
# above -- so every icon is built from solid shapes, no outlines).
_HSC_GROUP_ICON_PATHS = {
    "pl": [
        "M4 2h9l4 4v14H4z",
        "M13 2v4h4z",
        "M7 11h9v1.6H7z",
        "M7 14.4h9v1.6H7z",
        "M7 17.8h6v1.6H7z",
    ],
    "mh": ["M4 14h4v6H4z", "M10 9h4v11h-4z", "M16 4h4v16h-4z"],
    "att": ["M11.2 6.5h1.6v6.3h-1.6z", "M12 12h4.6v1.6H12z"],
    # Generic folder shape for manually-added categories, which have no
    # dedicated icon of their own -- also used by the homepage's category
    # section headers (V6: every section gets a colored icon chip).
    "_default": ["M3 6h6l2 2h10v11H3z"],
}


def _hsc_group_icon(gid, color):
    icon_paths = _HSC_GROUP_ICON_PATHS.get(gid) or _HSC_GROUP_ICON_PATHS["_default"]
    paths = "".join(f'<path d="{d}" fill="{color}"/>' for d in icon_paths)
    center_dot = f'<circle cx="12" cy="12" r="1.3" fill="{color}"/>' if gid == "att" else ""
    return f'<svg aria-hidden="true" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="width:22px;height:22px;">{paths}{center_dot}</svg>'


def _hsc_render_menu_page(display_name, settings, can_create_dashboard=False):
    import json

    from markupsafe import escape
    from flask import current_app
    from flask_babel import get_locale, gettext as _hsc_gettext

    lang = str(get_locale())
    tr = _hsc_tr
    # Appearance (§5at): Light is the V6 flagship default -- an unset choice
    # renders with `data-theme="light"`; an explicit "system" stays
    # attribute-less so the `prefers-color-scheme` tier applies; "dark"
    # keeps Dark. Same convention on the settings page.
    theme_mode = settings.get("theme_mode")
    if theme_mode not in ("light", "dark"):
        theme_mode = "light" if settings.get("theme_mode") != "system" else None
    data_theme_attr = f' data-theme="{theme_mode}"' if theme_mode else ""
    # MANDATORY per modern-web-guidance's dark-mode guide: a <meta
    # name="color-scheme"> reflecting the same choice, so the browser knows
    # which native UI theme to paint before first render.
    meta_color_scheme = {"light": "light", "dark": "dark"}.get(theme_mode, "light dark")
    density = "compact" if settings.get("density") == "compact" else "comfortable"
    data_density_attr = ' data-density="compact"' if density == "compact" else ""
    # A personal-name suffix ("さん") isn't a translation OF anything --
    # English has no equivalent word to translate -- so this is a real
    # msgid of its own (a name placeholder, %(name)s) rather than one of
    # _HSC_MSGIDS's English-source-string entries. `display_name` is
    # escaped BEFORE substitution.
    greeting_html = _hsc_gettext("%(name)s") % {"name": escape(display_name)}
    # A dropdown, not a pill row, so this scales to every language Superset
    # itself supports (§5ak's LANGUAGES config, all 30) -- picking one this
    # page has no real translation for just falls back to the English
    # source text.
    #
    # This needed a REAL <script>, not an inline onchange="" attribute:
    # Superset's own Talisman-issued CSP ships a per-request nonce in
    # script-src, and per the CSP spec, a nonce-source in a directive makes
    # browsers ignore that directive's 'unsafe-inline' entirely -- so an
    # inline event-handler attribute is silently a no-op. Every other
    # control on this page stays a plain link/form submit; this is the one
    # spot that genuinely needs a JS event, so it gets the same nonce
    # Talisman itself put in the CSP header.
    csp_nonce = current_app.jinja_env.globals.get("csp_nonce", lambda: "")()
    # Explicit color+background on every <option>, not just the <select>:
    # the browser's native open-dropdown popup is drawn by the OS, and on
    # most browsers/platforms it inherits the <select>'s own text color into
    # that popup's option list -- so a <select> styled to match the (dark)
    # header, sitting on the popup's plain white system background, renders
    # every unhovered option as invisible white-on-white. Fixing it means
    # never letting the <select>'s own ink go light -- see below.
    # NOTE: compare via _hsc_lang_key -- `str(get_locale())` yields the
    # normalized locale (zh_TW -> zh_Hant_TW), which otherwise never matches
    # the `zh_TW` LANGUAGES key, leaving no option `selected` and the
    # switcher showing English while the page itself is translated.
    lang_norm = _hsc_lang_key(lang)
    lang_options_html = "".join(
        f'<option value="{code}"{" selected" if _hsc_lang_key(code) == lang_norm else ""} style="color:#1B2126;background:#FFFFFF;">{escape(info["name"])}</option>'
        for code, info in current_app.config.get("LANGUAGES", {}).items()
    )
    accent = _hsc_valid_hex_color(settings.get("accent"), _HSC_DEFAULT_ACCENT)
    # V6 header: deep RYOBI teal/navy chrome -- the accent lives in buttons,
    # chips and focus rings, not painted across the header gradient, so
    # header controls can use one fixed readable ink on either theme.
    header_ink = "#FFFFFF"
    lang_switcher_html = f"""<select id="hsc-lang-select" aria-label="{escape(tr("language_label"))}" style="font-size:13px;color:#141B2A;background:#FFFFFF;border:none;padding:9px 12px;border-radius:10px;font-weight:600;cursor:pointer;height:38px;">{lang_options_html}</select>
<script nonce="{csp_nonce}">document.getElementById('hsc-lang-select').addEventListener('change', function(){{window.location.href='/hsc/set-lang?lang='+this.value;}});</script>"""
    groups = _hsc_all_groups()
    all_tiles = _hsc_all_tiles()
    dash_to_placeholder_id = _hsc_get_dashboard_to_placeholder_id()
    sections = _hsc_effective_sections(settings, all_tiles, dash_to_placeholder_id)
    visible_tiles = [t for s in sections for t in s["tiles"]]

    counts = {"live": 0, "soon": 0, "na": 0}
    for t in visible_tiles:
        counts[t["status"]] = counts.get(t["status"], 0) + 1

    group_labels = dict(groups)

    # V6 card recipe: white surface, a large category-tinted icon tile, a
    # muted status pill, title + category line -- a sellable SaaS card, not
    # a developer chip. Uses real CSS classes (`.hsc-card` etc., defined
    # once in the <style> block below) so hover/focus states work.
    def render_tile(tile, palette_color):
        label = escape(tile["label"])
        glabel = escape(group_labels.get(tile["group"], tile["group"]))
        # Two icon-chip backgrounds, not one: a category color tinted toward
        # white reads fine on a white card but goes a washed-out, low-
        # contrast near-white blob on a dark one. Both are set as custom
        # properties scoped to this card; `.hsc-card-icon` picks between
        # them the same way it picks any other `--hsc-*` token.
        icon_bg_light = _hsc_tint(palette_color, 0.86)
        icon_bg_dark = _hsc_shade(palette_color, 0.78, base="#161B22")
        icon = _hsc_group_icon(tile["group"], palette_color)
        card_style = f"--tile-icon-bg-l:{icon_bg_light};--tile-icon-bg-d:{icon_bg_dark};"
        # data-status: purely a client-side filter hook for the homepage's
        # status chips (hsc-filterbar) below -- never read server-side.
        if tile["status"] == "live":
            badge = f'<span class="hsc-badge hsc-badge-live">{escape(tr("live_badge"))}</span>'
            open_tag, close_tag = f'<a class="hsc-card hsc-card-live" href="{escape(tile["href"])}" style="{card_style}" data-status="live">', "</a>"
            footer = ""
        elif tile["status"] == "soon":
            badge = f'<span class="hsc-badge hsc-badge-soon">{escape(tr("soon"))}</span>'
            open_tag = f'<a class="hsc-card hsc-card-live" href="/hsc/create-dashboard?tile={escape(tile["id"])}" style="{card_style}" data-status="soon">'
            close_tag = "</a>"
            footer = f'<div class="hsc-card-cta" style="color:{palette_color};">+ {escape(tr("create_hint"))}</div>'
        else:
            badge = f'<span class="hsc-badge hsc-badge-na">{escape(tr("na"))}</span>'
            open_tag, close_tag = f'<div class="hsc-card hsc-card-na" style="{card_style}" data-status="na">', "</div>"
            # Audit F10: the tile only said "Out of scope" with no why, so a
            # user had no way to know whether it was broken, unimplemented,
            # or not for them. One short localized line under the title
            # answers that; the card stays a non-clickable div.
            footer = f'<div class="hsc-card-meta" style="font-weight:400;">{escape(tr("out_of_scope_hint"))}</div>'
        return f"""{open_tag}
  <div class="hsc-card-top">
    <span class="hsc-card-icon">{icon}</span>
    {badge}
  </div>
  <div class="hsc-card-title">{label}</div>
  <div class="hsc-card-meta"><span class="hsc-card-dot" style="background:{palette_color};"></span>{glabel}</div>
  {footer}
  <span class="hsc-card-open-arrow" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M9 7h8v8"/></svg></span>
{close_tag}"""

    group_colors = _hsc_group_colors(groups)
    # V6 composition: each category is a full-width section -- an icon+
    # title+count header with a right-aligned "Show all" link, then a
    # responsive card GRID. A section with more than
    # `_HSC_SECTION_CARD_CAP` tiles starts collapsed to that many.
    _HSC_SECTION_CARD_CAP = 8
    section_blocks = []
    for sec in sections:
        if not sec["tiles"]:
            continue
        cards_html = "".join(render_tile(t, group_colors.get(t["group"], _HSC_DEFAULT_ACCENT)) for t in sec["tiles"])
        count = len(sec["tiles"])
        sec_color = group_colors.get(sec["tiles"][0]["group"], _HSC_DEFAULT_ACCENT)
        show_all_html = ""
        if count > _HSC_SECTION_CARD_CAP:
            show_label = escape(tr("show_all_n") % {"count": count})
            less_label = escape(tr("show_less"))
            show_all_html = (
                f'<button type="button" class="hsc-show-all" aria-expanded="false" '
                f'data-show-label="{show_label}" data-less-label="{less_label}">{show_label}</button>'
            )
        section_blocks.append(f"""<section class="hsc-cat-section" data-section-name="{escape(sec["name"])}">
  <div class="hsc-cat-head">
    <span class="hsc-cat-icon" style="background:{_hsc_tint(sec_color, 0.88)};">{_hsc_group_icon("folder", sec_color)}</span>
    <h3 class="hsc-cat-title">{escape(sec["name"])}</h3>
    <span class="hsc-cat-count">{count}</span>
    <span class="hsc-cat-spacer"></span>
    <a class="hsc-cat-viewall" href="#" aria-hidden="true" tabindex="-1">{escape(tr("view_all"))} &#8594;</a>
    {show_all_html if show_all_html else ""}
  </div>
  <div class="hsc-cat-grid" data-cap="{_HSC_SECTION_CARD_CAP}" data-expanded="false">
    {cards_html}
  </div>
</section>""")
    sections_html = "".join(section_blocks)

    # True empty state: a brand-new instance (or one where every dashboard
    # got unpublished) renders a calm, honest blank with a create shortcut
    # when the viewer is allowed to create.
    if not visible_tiles:
        empty_cta = (
            f'<a class="hsc-btn hsc-btn-primary" href="/hsc/menu-settings?view=dashboards">{escape(tr("empty_home_cta"))}</a>'
            if can_create_dashboard
            else ""
        )
        sections_html = f"""<div class="hsc-empty" style="width:100%;">
  <h2 class="hsc-empty-title">{escape(tr("empty_home_title"))}</h2>
  <p class="hsc-empty-hint">{escape(tr("empty_home_hint"))}</p>
  {empty_cta}
</div>"""

    # Search + status filters + show-all (the launcher's core job): one
    # nonce'd script drives all three, since they act on the exact same set
    # of cards. A card must pass BOTH the text query and the active status
    # chip to stay visible; a section with zero visible cards hides
    # entirely; a live-region count announces the total for screen readers;
    # "Show all" grids are force-expanded while any filter is active.
    # Data lives in data-section-name/data-status on the DOM already
    # rendered above, so no JSON blob and no server round-trip.
    csp_nonce_menu = csp_nonce
    search_script = f"""
<script nonce="{csp_nonce_menu}">
(function() {{
  var input = document.getElementById('hsc-search-input');
  var clear = document.getElementById('hsc-search-clear');
  var count = document.getElementById('hsc-search-count');
  var board = document.getElementById('hsc-board');
  var noMatches = document.getElementById('hsc-no-matches');
  var filterBar = document.getElementById('hsc-filterbar');
  var clearFiltersBtn = document.getElementById('hsc-clear-filters');
  if (!input || !board) return;
  var fmtTpl = {json.dumps(tr("search_results_count"))};
  function fmt(n) {{ return fmtTpl.replace('%(count)s', n); }}
  var activeStatus = 'all';

  function refilter() {{
    var q = input.value.trim().toLowerCase();
    var filtering = !!q || activeStatus !== 'all';
    var total = 0;
    var sections = board.querySelectorAll('.hsc-cat-section');
    Array.prototype.forEach.call(sections, function(sec) {{
      var grid = sec.querySelector('.hsc-cat-grid');
      if (filtering && grid) grid.setAttribute('data-expanded', 'true');
      var shown = 0;
      var cards = sec.querySelectorAll('.hsc-card');
      Array.prototype.forEach.call(cards, function(card) {{
        var textHit = !q || card.textContent.toLowerCase().indexOf(q) !== -1;
        var statusHit = activeStatus === 'all' || card.getAttribute('data-status') === activeStatus;
        var hit = textHit && statusHit;
        card.hidden = !hit;
        if (hit) shown++;
      }});
      sec.hidden = shown === 0;
      total += shown;
    }});
    if (count) count.textContent = filtering ? fmt(total) : '';
    if (clear) clear.hidden = !q;
    if (noMatches) noMatches.hidden = total !== 0;
  }}

  input.addEventListener('input', refilter);
  if (clear) clear.addEventListener('click', function() {{ input.value = ''; refilter(); input.focus(); }});
  document.addEventListener('keydown', function(e) {{
    if ((e.key === '/' || ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')))
        && !(e.key === '/' && (e.ctrlKey || e.metaKey || e.altKey))) {{
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      e.preventDefault();
      input.focus();
    }}
  }});
  input.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') {{ if (input.value) {{ input.value = ''; refilter(); }} input.blur(); }}
  }});

  if (filterBar) {{
    filterBar.addEventListener('click', function(e) {{
      var chip = e.target.closest('.hsc-filter-chip');
      if (!chip) return;
      activeStatus = chip.getAttribute('data-filter');
      Array.prototype.forEach.call(filterBar.querySelectorAll('.hsc-filter-chip'), function(c) {{
        c.setAttribute('aria-pressed', c === chip ? 'true' : 'false');
      }});
      refilter();
    }});
  }}
  if (clearFiltersBtn) {{
    clearFiltersBtn.addEventListener('click', function() {{
      input.value = '';
      activeStatus = 'all';
      if (filterBar) {{
        Array.prototype.forEach.call(filterBar.querySelectorAll('.hsc-filter-chip'), function(c) {{
          c.setAttribute('aria-pressed', c.getAttribute('data-filter') === 'all' ? 'true' : 'false');
        }});
      }}
      refilter();
      input.focus();
    }});
  }}
  board.addEventListener('click', function(e) {{
    var btn = e.target.closest('.hsc-show-all');
    if (!btn) return;
    var grid = btn.closest('.hsc-cat-head').nextElementSibling;
    if (!grid || !grid.classList.contains('hsc-cat-grid')) return;
    var expanded = grid.getAttribute('data-expanded') === 'true';
    grid.setAttribute('data-expanded', expanded ? 'false' : 'true');
    btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
    btn.textContent = expanded ? btn.dataset.showLabel : btn.dataset.lessLabel;
  }});

  // V6 grid/list toggle -- a presentation-only switch on the same cards
  // (no refetch): the board flips `data-view`, CSS does the rest.
  var viewToggle = document.getElementById('hsc-view-toggle');
  if (viewToggle) {{
    viewToggle.addEventListener('click', function(e) {{
      var btn = e.target.closest('.hsc-view-btn');
      if (!btn) return;
      board.setAttribute('data-view', btn.getAttribute('data-view-mode'));
      Array.prototype.forEach.call(viewToggle.querySelectorAll('.hsc-view-btn'), function(b) {{
        b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
      }});
    }});
  }}
}})();
</script>"""

    initials = escape((display_name or "?")[:1].upper())

    def stat_pill(color, count, key):
        return f"""<div class="hsc-stat-pill">
      <span class="hsc-stat-dot" style="background:{color};"></span>
      <span class="hsc-stat-label">{escape(tr(key))} <b>{count}</b></span>
    </div>"""

    settings_icon = """<svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="#FFFFFF"><path d="M19.4 13a7.6 7.6 0 0 0 .1-1 7.6 7.6 0 0 0-.1-1l2.1-1.6a.5.5 0 0 0 .1-.7l-2-3.4a.5.5 0 0 0-.6-.2l-2.5 1a7.7 7.7 0 0 0-1.7-1l-.4-2.6a.5.5 0 0 0-.5-.5h-4a.5.5 0 0 0-.5.4l-.4 2.7a7.7 7.7 0 0 0-1.7 1l-2.5-1a.5.5 0 0 0-.6.2l-2 3.4a.5.5 0 0 0 .1.7L4.5 11a7.6 7.6 0 0 0 0 2l-2.1 1.6a.5.5 0 0 0-.1.7l2 3.4c.1.2.4.3.6.2l2.5-1a7.7 7.7 0 0 0 1.7 1l.4 2.6c0 .3.2.5.5.5h4c.2 0 .5-.2.5-.4l.4-2.7a7.7 7.7 0 0 0 1.7-1l2.5 1c.2.1.5 0 .6-.2l2-3.4a.5.5 0 0 0-.1-.7L19.4 13Zm-7.4 2.5A3.5 3.5 0 1 1 15.5 12 3.5 3.5 0 0 1 12 15.5Z"/></svg>"""
    grid_icon = """<svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z"/></svg>"""
    list_icon = """<svg aria-hidden="true" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M3 5h18v3H3zM3 10.5h18v3H3zM3 16h18v3H3z"/></svg>"""

    return f"""<!DOCTYPE html>
<html lang="{lang}"{_hsc_dir_attr(lang)}{data_theme_attr}{data_density_attr}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="{meta_color_scheme}">
<title>{escape(tr("header_title"))}</title>
<style>
{_hsc_theme_style_block(accent)}
/* V6 homepage chrome -- component classes so hover/focus/reduced-motion
   states work; reads the shared --hsc-* tokens so light/dark/density all
   apply. `style-src` allows 'unsafe-inline' with no nonce (confirmed via
   the response's own CSP header), so this needs no nonce -- only
   script-src does. */
.hsc-app-header {{ background:linear-gradient(115deg,#081C26 0%,#0C3038 55%,#0E3A42 100%);
  padding:14px clamp(18px,3.5vw,44px); position:sticky; top:0; z-index:20;
  box-shadow:0 1px 0 rgba(255,255,255,0.06), 0 4px 16px rgba(8,28,38,0.35); }}
.hsc-app-header-inner {{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; max-width:1440px; margin:0 auto; }}
.hsc-brand {{ display:flex; align-items:center; gap:12px; min-width:0; }}
.hsc-brand-logo {{ background:#FFFFFF; border-radius:10px; padding:7px 12px; display:flex; align-items:center; flex:0 0 auto; }}
.hsc-avatar {{ width:38px; height:38px; border-radius:50%; background:{accent}; display:flex; align-items:center; justify-content:center;
  font-size:16px; font-weight:700; color:{_hsc_ink_on(accent)}; flex:0 0 auto; border:2px solid rgba(255,255,255,0.55); }}
.hsc-brand-name {{ font-size:15px; font-weight:700; color:#FFFFFF; line-height:1.25; white-space:nowrap; }}
.hsc-brand-sub {{ font-size:12px; color:rgba(255,255,255,0.72); line-height:1.2; white-space:nowrap; }}
.hsc-header-controls {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
.hsc-stat-pill {{ display:flex; align-items:center; gap:8px; background:rgba(255,255,255,0.10);
  padding:9px 14px; border-radius:10px; height:38px; box-sizing:border-box; }}
.hsc-stat-dot {{ width:8px; height:8px; border-radius:50%; flex:0 0 auto; }}
.hsc-stat-label {{ color:#FFFFFF; font-size:13px; white-space:nowrap; }}
.hsc-stat-label b {{ font-weight:700; }}
.hsc-icon-btn {{ width:38px; height:38px; border-radius:10px; background:rgba(255,255,255,0.10); border:none;
  display:flex; align-items:center; justify-content:center; cursor:pointer; flex:0 0 auto; text-decoration:none; }}
.hsc-icon-btn:hover {{ background:rgba(255,255,255,0.2); }}
.hsc-icon-btn:focus-visible {{ outline:2px solid #FFFFFF; outline-offset:2px; }}
.hsc-logout-btn {{ font-size:13px; color:{_hsc_ink_on(accent)}; background:{accent}; padding:9px 18px;
  border-radius:10px; font-weight:700; text-decoration:none; height:38px; display:inline-flex; align-items:center; white-space:nowrap; }}
.hsc-logout-btn:hover {{ filter:brightness(1.07); }}
.hsc-logout-btn:focus-visible {{ outline:2px solid #FFFFFF; outline-offset:2px; }}
.hsc-page {{ max-width:1480px; margin:0 auto; padding:36px clamp(18px,3.5vw,44px) 64px; }}
.hsc-hero {{ display:flex; align-items:center; justify-content:space-between; gap:28px; min-height:112px; margin-bottom:24px; }}
.hsc-hero-title {{ font-size:28px; font-weight:700; color:var(--hsc-ink); margin:0 0 8px; line-height:1.3; letter-spacing:-0.01em; }}
.hsc-hero-subtitle {{ font-size:15px; color:var(--hsc-ink-muted); margin:0; max-width:560px; line-height:1.6; }}
/* Restrained branded visual (not a marketing hero): a small abstract
   data-motif -- rising bars -- tinted with the accent. Decorative only:
   aria-hidden, fixed size, quiet colors. */
.hsc-hero-visual {{ flex:0 0 auto; width:190px; height:88px; border-radius:var(--hsc-radius); display:flex; align-items:flex-end; gap:7px;
  padding:14px 16px; box-sizing:border-box; background:{accent}0D; border:1px solid {accent}1F; }}
.hsc-hero-bar {{ width:16px; border-radius:5px 5px 0 0; background:{accent}59; }}
.hsc-hero-bar-strong {{ background:{accent}; }}
@media (max-width: 900px) {{ .hsc-hero-visual {{ display:none; }} }}
.hsc-filterbar {{ display:flex; gap:10px; flex-wrap:wrap; margin:0 0 30px; }}
.hsc-filter-chip {{ display:inline-flex; align-items:center; gap:8px; border:1px solid var(--hsc-border); background:var(--hsc-surface);
  color:var(--hsc-ink-muted); font-size:13px; font-weight:700; font-family:inherit; padding:9px 16px; border-radius:22px; cursor:pointer; height:38px; box-sizing:border-box; }}
.hsc-filter-chip:hover {{ color:var(--hsc-ink); border-color:var(--hsc-border-strong); }}
.hsc-filter-chip[aria-pressed="true"] {{ background:{accent}14; border-color:{accent}; color:{accent}; }}
.hsc-filter-chip:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-filter-count {{ background:var(--hsc-surface-3); border-radius:10px; padding:1px 8px; font-size:12px; }}
.hsc-filter-chip[aria-pressed="true"] .hsc-filter-count {{ background:{accent}26; }}
/* Category sections: icon + title + count header, generous spacing, then
   the card grid. "View all" reads quieter than the title on purpose. */
#hsc-board {{ display:flex; flex-direction:column; gap:42px; }}
.hsc-cat-section {{ min-width:0; }}
.hsc-cat-head {{ display:flex; align-items:center; gap:12px; margin-bottom:16px; min-width:0; }}
.hsc-cat-icon {{ width:34px; height:34px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex:0 0 auto; }}
.hsc-cat-title {{ font-size:18px; font-weight:700; color:var(--hsc-ink); margin:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.hsc-cat-count {{ font-size:12px; font-weight:700; color:{accent}; background:{accent}14; border-radius:10px; padding:2px 10px; flex:0 0 auto; }}
.hsc-cat-spacer {{ flex:1; }}
.hsc-cat-viewall {{ font-size:12.5px; font-weight:600; color:var(--hsc-ink-faint); text-decoration:none; flex:0 0 auto; white-space:nowrap; }}
.hsc-show-all {{ border:none; background:none; font-family:inherit; font-size:13px; font-weight:700; color:{accent}; cursor:pointer; padding:6px 4px; border-radius:6px; flex:0 0 auto; white-space:nowrap; }}
.hsc-show-all:hover {{ text-decoration:underline; }}
.hsc-show-all:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-cat-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:var(--hsc-col-gap,14px); }}
.hsc-cat-grid[data-expanded="false"] .hsc-card:nth-child(n+9) {{ display:none; }}
/* Cards: polished click targets -- 42px icon tile with an inset ring,
   15px title, quiet category line, and an open-arrow affordance that
   slides in on hover. Hover: 2px lift + accent-tinted border. */
.hsc-card {{ display:flex; flex-direction:column; gap:9px; background:var(--hsc-surface); border:1px solid var(--hsc-border);
  border-radius:var(--hsc-radius); padding:16px 18px; min-height:118px; text-decoration:none; box-shadow:var(--hsc-card-shadow);
  transition:box-shadow .15s ease, transform .15s ease, border-color .15s ease; position:relative; }}
.hsc-card-live {{ cursor:pointer; }}
.hsc-card-live:hover {{ box-shadow:var(--hsc-card-hover-shadow); transform:translateY(-2px); border-color:{accent}66; }}
.hsc-card-live:active {{ transform:translateY(0); box-shadow:var(--hsc-card-shadow); }}
.hsc-card-live:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-card-top {{ display:flex; align-items:center; justify-content:space-between; gap:8px; }}
.hsc-card-icon {{ width:42px; height:42px; border-radius:12px; display:flex; align-items:center; justify-content:center; flex:0 0 auto;
  background:var(--tile-icon-bg-l); box-shadow:inset 0 0 0 1px rgba(16,24,40,0.05); }}
.hsc-card-icon svg {{ width:22px; height:22px; }}
.hsc-card-title {{ font-size:15px; font-weight:700; color:var(--hsc-ink); line-height:1.35; padding-right:18px; }}
.hsc-card-meta {{ display:flex; align-items:center; gap:7px; font-size:12.5px; color:var(--hsc-ink-muted); font-weight:500; margin-top:auto; }}
.hsc-card-dot {{ width:7px; height:7px; border-radius:50%; flex:0 0 auto; }}
.hsc-card-cta {{ font-size:12.5px; font-weight:700; }}
.hsc-card-open-arrow {{ position:absolute; right:14px; bottom:14px; color:{accent}; opacity:0; transform:translate(-4px,4px);
  transition:opacity .15s ease, transform .15s ease; pointer-events:none; }}
.hsc-card-live:hover .hsc-card-open-arrow, .hsc-card-live:focus-visible .hsc-card-open-arrow {{ opacity:1; transform:none; }}
.hsc-badge {{ font-size:11.5px; font-weight:700; padding:3px 10px; border-radius:20px; white-space:nowrap; }}
.hsc-badge-live {{ color:var(--hsc-badge-live-fg); background:var(--hsc-badge-live-bg); }}
.hsc-badge-soon {{ color:var(--hsc-badge-soon-fg); background:var(--hsc-badge-soon-bg); }}
.hsc-badge-na {{ color:var(--hsc-badge-na-fg); background:var(--hsc-badge-na-bg); }}
/* List view (V6 toggle): one row per dashboard, horizontal layout. */
#hsc-board[data-view="list"] .hsc-cat-grid {{ grid-template-columns:1fr; }}
#hsc-board[data-view="list"] .hsc-card {{ flex-direction:row; align-items:center; min-height:0; padding:12px 18px; gap:14px; }}
#hsc-board[data-view="list"] .hsc-card-top {{ flex:0 0 auto; }}
#hsc-board[data-view="list"] .hsc-card-title {{ flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
#hsc-board[data-view="list"] .hsc-card-meta, #hsc-board[data-view="list"] .hsc-card-cta {{ margin-top:0; flex:0 0 auto; }}
.hsc-view-toggle {{ display:flex; gap:4px; background:var(--hsc-surface); border:1px solid var(--hsc-border);
  border-radius:10px; padding:4px; box-shadow:var(--hsc-card-shadow); flex:0 0 auto; }}
.hsc-view-btn {{ border:none; background:transparent; color:var(--hsc-ink-muted); width:34px; height:30px;
  border-radius:7px; display:flex; align-items:center; justify-content:center; cursor:pointer; padding:0; }}
.hsc-view-btn:hover {{ color:var(--hsc-ink); }}
.hsc-view-btn[aria-pressed="true"] {{ background:{accent}14; color:{accent}; }}
.hsc-view-btn:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-bottom-cta {{ display:flex; align-items:center; justify-content:space-between; gap:18px; flex-wrap:wrap;
  background:{accent}0A; border:1px solid {accent}33; border-radius:var(--hsc-radius); padding:22px 26px; margin-top:44px; }}
.hsc-bottom-cta-title {{ font-size:16px; font-weight:700; color:var(--hsc-ink); margin:0 0 4px; }}
.hsc-bottom-cta-hint {{ font-size:13px; color:var(--hsc-ink-muted); margin:0; max-width:520px; line-height:1.6; }}
.hsc-app-footer {{ max-width:1480px; margin:0 auto; padding:18px clamp(18px,3.5vw,44px) 28px; display:flex; align-items:center;
  justify-content:space-between; gap:12px; flex-wrap:wrap; font-size:12.5px; color:var(--hsc-ink-faint);
  border-top:1px solid var(--hsc-border); }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) .hsc-card-icon {{ background:var(--tile-icon-bg-d); }}
}}
:root[data-theme="dark"] .hsc-card-icon {{ background:var(--tile-icon-bg-d); }}
@media (max-width: 767px) {{
  .hsc-hero-title {{ font-size:22px; }}
  #hsc-board {{ gap:26px; }}
}}
@media (prefers-reduced-motion: reduce) {{
  .hsc-card {{ transition:none; }}
  .hsc-card-live:hover {{ transform:none; }}
}}

/* Reference reconstruction: measured desktop composition, September 2026. */
.hsc-app-header {{ background:#073442; box-shadow:0 2px 8px #082e4020; padding:16px 32px; }}
.hsc-app-header-inner {{ max-width:1480px; flex-wrap:nowrap; }}
.hsc-page {{ box-sizing:border-box; width:100%; max-width:1544px; padding:20px 32px 20px; }}
.hsc-app-footer {{ box-sizing:border-box; max-width:1544px; padding:16px 32px 24px; border:0; }}
.hsc-stat-pill,.hsc-icon-btn,.hsc-logout-btn {{ box-sizing:border-box; height:42px; border-radius:7px; }}
.hsc-icon-btn {{ width:42px; background:#fff; }}
.hsc-icon-btn svg {{ stroke:#425978; }}
.hsc-header-controls > a[style],#hsc-lang-select {{ height:42px !important; border-radius:7px !important; box-sizing:border-box; }}
.hsc-header-controls > div[style] {{ padding:0 !important; background:none !important; }}
.hsc-brand-logo {{ border-radius:6px; }}
.hsc-hero {{ min-height:120px; margin:0 0 12px; position:relative; }}
.hsc-hero-title {{ color:var(--hsc-ink); font-size:30px; }}
.hsc-hero-subtitle {{ max-width:800px; }}
.hsc-hero-visual {{ width:300px; height:112px; border:0; background:transparent; gap:12px; align-items:flex-end; padding:14px 28px; border-radius:0; }}
.hsc-hero-visual::before {{ content:""; position:absolute; right:0; width:300px; height:110px; background:radial-gradient(ellipse at center,{accent}18,transparent 70%); pointer-events:none; }}
.hsc-hero-bar {{ width:25px; background:{accent}28; border-radius:3px 3px 0 0; box-shadow:inset 0 0 0 1px {accent}18; }}
.hsc-hero-bar-strong {{ background:{accent}60; }}
.hsc-toolbar {{ margin-bottom:16px; }}
.hsc-searchbar {{ width:680px; max-width:100%; height:48px; box-sizing:border-box; border-radius:8px; }}
.hsc-searchbar > svg {{ width:22px; height:22px; stroke:{accent}; }}
.hsc-filterbar {{ align-items:center; gap:10px; margin-bottom:26px; }}
.hsc-filter-chip {{ height:42px; border-radius:8px; padding:8px 14px; }}
.hsc-filter-chip[aria-pressed="true"],.hsc-view-btn[aria-pressed="true"] {{ color:{_hsc_ink_on(accent)}; background:{accent}; border-color:{accent}; }}
.hsc-filter-chip[data-filter="live"]:not([aria-pressed="true"]) {{ color:var(--hsc-badge-live-fg); }}
.hsc-filter-chip[data-filter="soon"]:not([aria-pressed="true"]) {{ color:var(--hsc-badge-soon-fg); }}
.hsc-filter-chip[aria-pressed="true"] .hsc-filter-count {{ background:#ffffff35; }}
.hsc-view-toggle {{ margin-left:auto; padding:0; gap:0; border-radius:7px; overflow:hidden; }}
.hsc-view-btn {{ width:42px; height:40px; border-radius:0; }}
#hsc-board {{ gap:26px; }}
.hsc-cat-head {{ margin-bottom:12px; gap:12px; }}
.hsc-cat-count {{ color:#275296; background:#e5efff; }}
/* ==== Homepage card recipe — measured against the approved Version 6
   reference (256×152 grid, 14px gap): icon chip top-LEFT spanning two text
   rows, title + category line beside it, status pill pinned bottom-RIGHT,
   open-arrow bottom-LEFT. Category accent lives in the icon chip tint, not
   painted across the card. ==== */
.hsc-cat-grid {{ grid-template-columns:repeat(5,minmax(0,1fr)); gap:14px; }}
#hsc-board[data-view="grid"] .hsc-card {{ display:grid; grid-template-columns:44px minmax(0,1fr); grid-template-rows:minmax(38px,auto) minmax(0,1fr) auto;
  box-sizing:border-box; min-height:152px; padding:16px 16px 13px; border-radius:9px; box-shadow:0 3px 9px #172e5010;
  column-gap:12px; row-gap:6px; align-content:start; }}
#hsc-board[data-view="grid"] .hsc-card-top {{ display:contents; }}
#hsc-board[data-view="grid"] .hsc-card-icon {{ grid-column:1; grid-row:1; width:44px; height:46px; border-radius:8px; box-shadow:none; }}
#hsc-board[data-view="grid"] .hsc-card-title {{ grid-column:2; grid-row:1; padding:0; font-size:14px; align-self:start; }}
#hsc-board[data-view="grid"] .hsc-card-meta {{ grid-column:2; grid-row:2; margin:0; align-self:start; font-size:12px; }}
#hsc-board[data-view="grid"] .hsc-card-dot {{ display:none; }}
#hsc-board[data-view="grid"] .hsc-badge {{ grid-column:2; grid-row:3; justify-self:end; align-self:end; font-size:11px; }}
#hsc-board[data-view="grid"] .hsc-card-cta {{ grid-column:1 / -1; font-size:11px; }}
.hsc-card-na .hsc-card-open-arrow {{ display:none; }}
.hsc-card-open-arrow {{ bottom:15px; left:17px; right:auto; opacity:.45; transform:none; }}
.hsc-bottom-cta {{ margin-top:24px; padding:18px 22px; border-radius:9px; }}
:root[data-density="compact"] #hsc-board[data-view="grid"] .hsc-card {{ min-height:128px; padding:12px; }}
@media(min-width:1600px) {{ .hsc-app-header {{ padding-left:max(32px,calc((100vw - 1480px)/2)); padding-right:max(32px,calc((100vw - 1480px)/2)); }} }}
@media(max-width:1279px) {{ .hsc-app-header-inner {{ flex-wrap:wrap; }} .hsc-cat-grid {{ grid-template-columns:repeat(4,minmax(0,1fr)); }} }}
@media(max-width:1023px) {{ .hsc-cat-grid {{ grid-template-columns:repeat(3,minmax(0,1fr)); }} }}
@media(max-width:767px) {{ .hsc-page {{ padding:16px; }} .hsc-app-header {{ padding:12px 16px; }} .hsc-header-controls {{ gap:7px; }} .hsc-stat-pill {{ padding:7px; }} .hsc-stat-label {{ font-size:11px; }} .hsc-hero-title {{ font-size:23px; }} .hsc-cat-grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }} #hsc-board[data-view="grid"] .hsc-card {{ grid-template-columns:32px minmax(0,1fr); gap:6px; padding:12px; }} #hsc-board[data-view="grid"] .hsc-card-icon {{ width:32px; height:36px; }} .hsc-filter-chip {{ font-size:12px; padding:8px 10px; }} .hsc-view-toggle {{ margin-left:0; }} }}
@media(max-width:450px) {{ .hsc-cat-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body style="margin:0;min-height:100vh;background:var(--hsc-bg);color:var(--hsc-ink);
font-family:'Noto Sans JP','Hiragino Kaku Gothic ProN','Yu Gothic','IBM Plex Sans',system-ui,sans-serif;">
<a href="#content" class="hsc-skip-link">{escape(tr("skip_to_content"))}</a>

<header class="hsc-app-header">
  <div class="hsc-app-header-inner">
    <div class="hsc-brand">
      <div class="hsc-brand-logo">{_hsc_rl_logo_svg("24px")}</div>
      <div class="hsc-avatar">{initials}</div>
      <div style="min-width:0;">
        <div class="hsc-brand-name">{greeting_html}</div>
        <div class="hsc-brand-sub">{escape(tr("header_title"))}</div>
      </div>
    </div>
    <div class="hsc-header-controls">
      {stat_pill("#12B886", counts.get("live",0), "stat_live")}
      {stat_pill("#F59F00", counts.get("soon",0), "stat_soon")}
      {stat_pill("#8D99A6", counts.get("na",0), "stat_na")}
      {f'<a href="/hsc/menu-settings?view=dashboards" style="font-size:13px;color:{_hsc_ink_on(accent)};background:{accent};padding:9px 16px;border-radius:10px;font-weight:700;text-decoration:none;height:38px;display:inline-flex;align-items:center;white-space:nowrap;">+ {escape(tr("add_dashboard_button"))}</a>' if can_create_dashboard else ''}
      <div style="display:flex;gap:4px;background:rgba(255,255,255,0.08);padding:4px;border-radius:12px;">{lang_switcher_html}</div>
      <a class="hsc-icon-btn" href="/hsc/menu-settings" aria-label="{escape(tr("settings"))}" title="{escape(tr("settings"))}">{settings_icon}</a>
      <a class="hsc-logout-btn" href="/logout/">{escape(tr("logout"))}</a>
    </div>
  </div>
</header>

<main id="content" tabindex="-1" class="hsc-page">
  <section class="hsc-hero">
    <div>
      <h1 class="hsc-hero-title">{tr("hero_welcome") % {"name": escape(display_name or "?")}}</h1>
      <p class="hsc-hero-subtitle">{escape(tr("hero_subtitle"))}</p>
    </div>
    <div class="hsc-hero-visual" aria-hidden="true">
      <svg width="280" height="112" viewBox="0 0 280 112" fill="none">
        <ellipse cx="160" cy="101" rx="116" ry="8" fill="{accent}" opacity=".08"/>
        <g fill="{accent}" opacity=".14">
          <path d="M22 97V73h15v24M44 97V52h18v45M68 97V65h22v32M97 97V35h22v62M127 97V16h19v81M154 97V44h24v53M186 97V60h20v37M214 97V71h18v26M240 97V82h18v15"/>
        </g>
        <g fill="#879cc2" opacity=".28">
          <path d="M51 97V38h10v59M103 97V26h11v71M132 97V8h8v89M160 97V34h12v63M192 97V49h8v48"/>
        </g>
        <path d="M136 8V1M107 26V19M54 38V29" stroke="#9eacc7"/>
        <path d="M20 86l33-10 24 5 31-19 28 6 30-29 31 8 35-22 28 7" stroke="{accent}" stroke-width="2" opacity=".35"/>
        <g fill="{accent}" opacity=".5"><circle cx="108" cy="62" r="3"/><circle cx="166" cy="39" r="3"/><circle cx="232" cy="25" r="3"/></g>
      </svg>
    </div>
  </section>

  <div class="hsc-toolbar">
    <form class="hsc-searchbar" role="search" id="hsc-search" onsubmit="return false;">
      <label class="hsc-vh" for="hsc-search-input">{escape(tr("search_label"))}</label>
      <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--hsc-ink-faint)" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input id="hsc-search-input" type="search" placeholder="{escape(tr("search_placeholder"))}" autocomplete="off">
      <button type="button" class="hsc-search-clear" id="hsc-search-clear" aria-label="{escape(tr("clear_search"))}" hidden>✕</button>
      <span class="hsc-search-kbd" aria-hidden="true">Ctrl K</span>
    </form>

  </div>

  <div class="hsc-filterbar" id="hsc-filterbar" role="group" aria-label="{escape(tr("select_menu"))}">
    <button type="button" class="hsc-filter-chip" data-filter="all" aria-pressed="true" aria-label="{escape(tr("filter_all_label"))}">{escape(tr("filter_all"))} <span class="hsc-filter-count">{len(visible_tiles)}</span></button>
    <button type="button" class="hsc-filter-chip" data-filter="live" aria-pressed="false" aria-label="{escape(tr("filter_live_label"))}">{escape(tr("stat_live"))} <span class="hsc-filter-count">{counts.get("live", 0)}</span></button>
    <button type="button" class="hsc-filter-chip" data-filter="soon" aria-pressed="false" aria-label="{escape(tr("filter_soon_label"))}">{escape(tr("stat_soon"))} <span class="hsc-filter-count">{counts.get("soon", 0)}</span></button>
    <button type="button" class="hsc-filter-chip" data-filter="na" aria-pressed="false" aria-label="{escape(tr("filter_na_label"))}">{escape(tr("stat_na"))} <span class="hsc-filter-count">{counts.get("na", 0)}</span></button>
    <div class="hsc-view-toggle" id="hsc-view-toggle" role="group" aria-label="{escape(tr("select_menu"))}">
      <button type="button" class="hsc-view-btn" data-view-mode="grid" aria-pressed="true" aria-label="Grid view">{grid_icon}</button>
      <button type="button" class="hsc-view-btn" data-view-mode="list" aria-pressed="false" aria-label="List view">{list_icon}</button>
    </div>
  </div>

  <p id="hsc-search-count" class="hsc-vh" aria-live="polite"></p>
  <div id="hsc-board" data-view="grid">
    {sections_html}
  </div>
  <div id="hsc-no-matches" class="hsc-empty" hidden>
    <h2 class="hsc-empty-title">{escape(tr("search_no_matches_title"))}</h2>
    <p class="hsc-empty-hint">{escape(tr("search_no_matches_hint"))}</p>
    <button type="button" class="hsc-btn hsc-btn-ghost" id="hsc-clear-filters">{escape(tr("clear_filters"))}</button>
  </div>

  <div class="hsc-bottom-cta">
    <div>
      <h2 class="hsc-bottom-cta-title">{escape(tr("cant_find_title"))}</h2>
      <p class="hsc-bottom-cta-hint">{escape(tr("cant_find_hint"))}</p>
    </div>
    <a class="hsc-btn hsc-btn-primary" href="/hsc/menu-settings?view=homepage-layout">{escape(tr("customize_menu_button"))}</a>
  </div>
</main>

<footer class="hsc-app-footer">
  <span>RYOBI LAO &nbsp;|&nbsp; {escape(tr("header_title"))} &nbsp;|&nbsp; v1.0</span>
  <span>Better Data. A Stronger Tomorrow.</span>
</footer>
{search_script}

</body></html>"""


# ---------------------------------------------------------------------------
# 3av. Keyboard-accessible alternative to the two kanban boards' HTML5 drag# ---------------------------------------------------------------------------
# 3av. Keyboard-accessible alternative to the two kanban boards' HTML5 drag
#    (docs/00-runbook.md §5av) -- flagged as the single most significant
#    accessibility gap left by §5au's audit: only a mouse/touch user could
#    reorder a homepage section, reorder a category, or recategorize a
#    dashboard. Built from the modern-web-guidance skill's accessibility
#    guide, §5 "Keyboard and Focus Management" (a real <button> grab handle,
#    so Enter/Space activation is native and needs no custom keydown/keyup
#    handling; `aria-pressed` for the grabbed/not-grabbed toggle state) and
#    §8 "Live Regions" (one centralized `aria-live="polite"` region for the
#    whole page, not one per board).
#
#    Deliberately a plain string, not an f-string: this JS is identical on
#    every render and has far more literal `{`/`}` (object literals,
#    function bodies) than the one thing that actually varies per request
#    (the current locale's announcement templates) -- doubling every brace
#    to make it an f-string would only make it harder to read. The
#    per-request data is injected as a single JSON blob (`HSC_I18N`) via
#    plain string concatenation in `_hsc_render_settings_page`, the same
#    technique already used nowhere else in this file only because nothing
#    else here has needed a static, reused JS body before.
#
#    Deliberately operates on the SAME DOM nodes/classes the existing mouse
#    drag already uses (`.hsc-layout-row`, `.hsc-layout-section`) --
#    `#hsc-sections-form`'s own `submit` listener (defined earlier on this
#    page) serializes from final DOM position at submit time, so a
#    keyboard-only move needs no new endpoint, no new serialization, and no
#    Python-side changes to what gets saved -- only to how a row/section can
#    get to its final position without a mouse. (Category management no
#    longer has a drag surface at all -- it's a plain table of buttons/
#    inputs, each already keyboard-operable natively -- so this engine only
#    runs against `#hsc-kanban` now.)
# ---------------------------------------------------------------------------
_HSC_KANBAN_A11Y_JS = """
(function () {
  "use strict";

  function announce(msg) {
    // Deliberately a direct, synchronous set -- an earlier draft cleared
    // the region and re-set it on the next requestAnimationFrame (a common
    // trick to force a re-announcement of identical consecutive text), but
    // rAF never fires while the tab is backgrounded/hidden, which silently
    // dropped every announcement in that state (caught via real testing,
    // not assumed). Every message here already varies by position/name on
    // each real move, so the trick wasn't buying anything worth that risk.
    var el = document.getElementById("hsc-announcer");
    if (el) el.textContent = msg;
  }

  function fmt(tmpl, vars) {
    return tmpl.replace(/%\\(([a-zA-Z_]+)\\)s/g, function (_, key) {
      return Object.prototype.hasOwnProperty.call(vars, key) ? String(vars[key]) : "";
    });
  }

  // ================= Homepage-layout board (V6: stacked, collapsible
  // sections instead of side-by-side kanban columns) -- card (row) move
  // AND section move now both live here, since the old separate "category
  // board" keyboard engine below no longer has any drag surface to run on
  // (category management is a plain table of buttons/inputs, each already
  // natively keyboard-operable with no custom engine needed). =================
  var kanbanRoot = document.getElementById("hsc-kanban");
  if (kanbanRoot) {
    var grabbedRow = null; // {row, originRows, originNext}
    var grabbedSection = null; // {section, originNext}

    function kanbanSections() { return Array.prototype.slice.call(kanbanRoot.querySelectorAll(".hsc-layout-section")); }
    function kanbanRows(sec) { return sec.querySelector(".hsc-layout-rows"); }
    function kanbanRowEls(sec) { return Array.prototype.slice.call(kanbanRows(sec).querySelectorAll(".hsc-layout-row")); }
    function kanbanSectionOf(row) { return row.closest(".hsc-layout-section"); }
    function kanbanSectionName(sec) {
      var input = sec.querySelector(".hsc-section-name");
      if (input) return input.value;
      var fixed = sec.querySelector(".hsc-section-name-fixed");
      return fixed ? fixed.textContent.trim() : "";
    }
    function kanbanRemoveEmptyHint(rows) {
      var hint = rows.querySelector(".hsc-kanban-empty");
      if (hint) hint.remove();
    }
    function kanbanSyncMoveSelect(row) {
      // Keep the row's own "Move to" <select> (the no-drag fallback) in
      // sync after a keyboard or mouse-drag move lands it in a different
      // section, so re-opening that dropdown shows where the row actually
      // is rather than where it started.
      var sel = row.querySelector(".hsc-row-move-select");
      var sectionId = kanbanSectionOf(row).getAttribute("data-section-id");
      if (sel) sel.value = sectionId;
    }
    function kanbanSetGrabbed(handle, row, on) {
      handle.setAttribute("aria-pressed", on ? "true" : "false");
      row.classList.toggle("hsc-grabbed", on);
    }
    function kanbanAnnounceRowMove(row, sec) {
      var idx = kanbanRowEls(sec).indexOf(row);
      announce(fmt(HSC_I18N.hsc_moved_card_to_section, {
        card: row.getAttribute("data-label"),
        section: kanbanSectionName(sec),
        pos: idx + 1,
        total: kanbanRowEls(sec).length,
      }));
    }
    function kanbanReorderableSections() {
      // "Hidden" is never part of the reorder -- excluded here so its
      // announced position/total always reflects only the sections a
      // person can actually reorder, not a phantom 6th slot.
      return kanbanSections().filter(function (s) { return s.getAttribute("data-section-id") !== "hidden"; });
    }
    function kanbanAnnounceSectionMove(sec) {
      var list = kanbanReorderableSections();
      var idx = list.indexOf(sec);
      announce(fmt(HSC_I18N.hsc_moved_category, { category: kanbanSectionName(sec), pos: idx + 1, total: list.length }));
    }

    function kanbanToggleGrab(handle) {
      var row = handle.closest(".hsc-layout-row");
      var head = handle.closest(".hsc-layout-section-head");
      if (row) {
        if (grabbedSection) return; // one active grab at a time on this board
        if (grabbedRow && grabbedRow.row === row) {
          kanbanSetGrabbed(handle, row, false);
          kanbanAnnounceRowMove(row, kanbanSectionOf(row));
          grabbedRow = null;
          handle.focus();
        } else if (!grabbedRow) {
          grabbedRow = { row: row, originRows: kanbanRows(kanbanSectionOf(row)), originNext: row.nextElementSibling };
          kanbanSetGrabbed(handle, row, true);
          announce(fmt(HSC_I18N.hsc_picked_up_card, { card: row.getAttribute("data-label") }));
        }
      } else if (head) {
        if (grabbedRow) return;
        var sec = head.closest(".hsc-layout-section");
        if (grabbedSection && grabbedSection.section === sec) {
          handle.setAttribute("aria-pressed", "false");
          head.classList.remove("hsc-grabbed");
          kanbanAnnounceSectionMove(sec);
          grabbedSection = null;
          handle.focus();
        } else if (!grabbedSection) {
          grabbedSection = { section: sec, originNext: sec.nextElementSibling };
          handle.setAttribute("aria-pressed", "true");
          head.classList.add("hsc-grabbed");
          announce(fmt(HSC_I18N.hsc_picked_up_category, { category: kanbanSectionName(sec) }));
        }
      }
    }

    // Real pointer activation (mouse/touch) of a grab handle.
    kanbanRoot.addEventListener("click", function (e) {
      var handle = e.target.closest(".hsc-grab-handle");
      if (handle) kanbanToggleGrab(handle);
    });

    kanbanRoot.addEventListener("keydown", function (e) {
      var toggleHandle = e.target.closest(".hsc-grab-handle");
      if (toggleHandle && e.key === "Enter") {
        // Explicit Enter handling, not a reliance on the browser's own
        // "Enter activates a focused <button>" default: per
        // modern-web-guidance's "Custom Trigger Keyboards" recipe, Enter is
        // a keydown handler -- and empirically, some environments (this
        // page's own automated keyboard testing included) don't reliably
        // synthesize the follow-on `click` a real physical Enter key press
        // would trigger, so this can't be the only path. preventDefault
        // stops the browser from *also* firing its own click for a real
        // keypress, which would otherwise immediately re-toggle the state
        // this handler just set (grab, then instant un-grab).
        e.preventDefault();
        kanbanToggleGrab(toggleHandle);
        return;
      }
      if (toggleHandle && e.key === " ") {
        e.preventDefault(); // prevent page scroll; Space toggles on keyup below, matching native <button>
        return;
      }

      if (grabbedRow) {
        var handle = e.target.closest(".hsc-grab-handle");
        if (!handle || handle.closest(".hsc-layout-row") !== grabbedRow.row) return;
        var row = grabbedRow.row;
        if (e.key === "Escape") {
          e.preventDefault();
          grabbedRow.originRows.insertBefore(row, grabbedRow.originNext);
          kanbanSyncMoveSelect(row);
          kanbanSetGrabbed(handle, row, false);
          announce(HSC_I18N.hsc_move_canceled);
          grabbedRow = null;
          handle.focus();
        } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
          e.preventDefault();
          var sec = kanbanSectionOf(row);
          var list = kanbanRowEls(sec);
          var idx = list.indexOf(row);
          var newIdx = idx + (e.key === "ArrowUp" ? -1 : 1);
          if (newIdx < 0 || newIdx >= list.length) return;
          var ref = e.key === "ArrowDown" ? list[newIdx].nextElementSibling : list[newIdx];
          kanbanRows(sec).insertBefore(row, ref);
          handle.focus(); // moving the node can drop focus to <body> in some browsers -- reclaim it
          kanbanAnnounceRowMove(row, sec);
        } else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
          e.preventDefault();
          var secs = kanbanSections();
          var fromSec = kanbanSectionOf(row);
          var secIdx = secs.indexOf(fromSec);
          var newSecIdx = secIdx + (e.key === "ArrowLeft" ? -1 : 1);
          if (newSecIdx < 0 || newSecIdx >= secs.length) return;
          var targetSec = secs[newSecIdx];
          kanbanRemoveEmptyHint(kanbanRows(targetSec));
          kanbanRows(targetSec).appendChild(row);
          kanbanSyncMoveSelect(row);
          handle.focus();
          kanbanAnnounceRowMove(row, targetSec);
        }
      } else if (grabbedSection) {
        var handle2 = e.target.closest(".hsc-grab-handle");
        if (!handle2 || handle2.closest(".hsc-layout-section") !== grabbedSection.section) return;
        var sec2 = grabbedSection.section;
        if (e.key === "Escape") {
          e.preventDefault();
          kanbanRoot.insertBefore(sec2, grabbedSection.originNext);
          handle2.setAttribute("aria-pressed", "false");
          sec2.querySelector(".hsc-layout-section-head").classList.remove("hsc-grabbed");
          announce(HSC_I18N.hsc_move_canceled);
          grabbedSection = null;
          handle2.focus();
        } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
          e.preventDefault();
          // "Hidden" never participates in section reorder (no grab handle
          // is ever rendered for it, so grabbedSection can't be it), but it
          // must still be excluded here so it's never treated as a valid
          // landing slot.
          var secs2 = kanbanReorderableSections();
          var idx2 = secs2.indexOf(sec2);
          var newIdx2 = idx2 + (e.key === "ArrowUp" ? -1 : 1);
          if (newIdx2 < 0 || newIdx2 >= secs2.length) return;
          var ref2 = e.key === "ArrowDown" ? secs2[newIdx2].nextElementSibling : secs2[newIdx2];
          kanbanRoot.insertBefore(sec2, ref2);
          handle2.focus();
          kanbanAnnounceSectionMove(sec2);
        }
      }
    });

    kanbanRoot.addEventListener("keyup", function (e) {
      var handle = e.target.closest(".hsc-grab-handle");
      if (handle && e.key === " ") {
        e.preventDefault();
        kanbanToggleGrab(handle);
      }
    });
  }
})();
"""


# §5aw-extras: audit F03 (unsaved-changes guard) + F06 (category-color live
# preview). See the injection site in _hsc_render_settings_page for why this
# is a plain string with a __ACCENT__ placeholder.
_HSC_SETTINGS_EXTRAS_JS = """
(function () {
  "use strict";

  // ---- color-input hit-area forwarding ----------------------------------
  // §5aw F08: clicks landing on the wrapper's enlarged hit area (::after
  // covers it) forward to the input so the picker opens from the whole
  // target, not just the small swatch -- still needed now that category
  // colors live in a table row instead of a kanban column head.
  document.querySelectorAll('.hsc-color-wrap').forEach(function (wrap) {
    var input = wrap.querySelector('input[type="color"]');
    if (!input) return;
    wrap.addEventListener("click", function (e) {
      if (e.target !== input) {
        e.preventDefault();
        input.click();
      }
    });
  });

  // ---- unsaved-changes guard, split per form ----------------------------
  // The settings page has several independent POST forms; editing a field
  // or dragging a row/section and then navigating away should warn before
  // silently discarding it. "Dirty" is computed AT unload/check time by
  // diffing the live DOM against a load-time snapshot -- a flag-only
  // approach false-positives on an Escape-canceled drag (the restore is
  // itself a DOM mutation) -- so diffing is what actually catches both
  // directions correctly. Two independent snapshots (sections / categories)
  // so each form's own sticky save-bar chip reflects only ITS OWN unsaved
  // edits, not the other form's.
  function fieldsIn(formId) {
    return Array.prototype.slice.call(
      document.querySelectorAll("#" + formId + " input, #" + formId + " select")
    ).filter(function (el) { return el.type !== "hidden"; });
  }
  function fieldValues(formId) {
    return fieldsIn(formId).map(function (el) { return el.value; }).join("\\u0000");
  }
  function rowState(root, selector) {
    if (!root) return null;
    return Array.prototype.map.call(root.querySelectorAll(selector), function (c) {
      return c.dataset.tileId || c.dataset.groupId || "";
    }).join(",");
  }
  var kanbanRoot = document.getElementById("hsc-kanban");
  var catTable = document.getElementById("hsc-category-table");

  var sectionsSnapshot = { fields: fieldValues("hsc-sections-form"), rows: rowState(kanbanRoot, ".hsc-layout-row") };
  var categoriesSnapshot = { fields: fieldValues("hsc-categories-form"), rows: rowState(catTable, ".hsc-cat-row") };

  function isSectionsDirty() {
    return fieldValues("hsc-sections-form") !== sectionsSnapshot.fields || rowState(kanbanRoot, ".hsc-layout-row") !== sectionsSnapshot.rows;
  }
  function isCategoriesDirty() {
    return fieldValues("hsc-categories-form") !== categoriesSnapshot.fields || rowState(catTable, ".hsc-cat-row") !== categoriesSnapshot.rows;
  }
  // Exposed globally: the scrollspy/dirty-chip script and each save-bar's
  // Reset-button script run as SEPARATE <script> tags from this IIFE, so a
  // closure-local binding would be invisible to them.
  window.HSC_IS_DIRTY_SECTIONS = isSectionsDirty;
  window.HSC_IS_DIRTY_CATEGORIES = isCategoriesDirty;
  window.HSC_IS_DIRTY = function () { return isSectionsDirty() || isCategoriesDirty(); };

  function refreshDirtyChip(id, dirty) {
    var chip = document.getElementById(id);
    if (chip) chip.hidden = !dirty;
  }
  var dirtyTick = false;
  function recheckDirty() {
    dirtyTick = false;
    refreshDirtyChip("hsc-sections-dirty", isSectionsDirty());
    refreshDirtyChip("hsc-categories-dirty", isCategoriesDirty());
  }
  // setTimeout, not requestAnimationFrame: rAF never fires while the tab
  // is backgrounded/hidden (same pitfall this page's own announce() helper
  // already documents and avoids for the same reason) -- which would leave
  // both save-bar chips stuck stale for anyone who tabs away mid-edit.
  function scheduleDirtyCheck() {
    if (dirtyTick) return;
    dirtyTick = true;
    setTimeout(recheckDirty, 0);
  }
  document.addEventListener("input", scheduleDirtyCheck);
  document.addEventListener("change", scheduleDirtyCheck);
  document.addEventListener("dragend", function () { setTimeout(recheckDirty, 0); });
  document.addEventListener("hsc:rowmoved", scheduleDirtyCheck);
  recheckDirty();

  // On ANY form submit, adopt the current DOM as the new baseline BEFORE
  // the navigation starts (submit fires before beforeunload) -- otherwise
  // the unload check still sees a DOM that differs from the ORIGINAL
  // snapshot and warns even though the click was a Save. The POST return
  // renders a fresh page with a fresh snapshot anyway; this only closes
  // the gap during the submit→unload window.
  var sectionsForm = document.getElementById("hsc-sections-form");
  if (sectionsForm) {
    sectionsForm.addEventListener("submit", function () {
      sectionsSnapshot = { fields: fieldValues("hsc-sections-form"), rows: rowState(kanbanRoot, ".hsc-layout-row") };
    });
  }
  var categoriesForm = document.getElementById("hsc-categories-form");
  if (categoriesForm) {
    categoriesForm.addEventListener("submit", function () {
      categoriesSnapshot = { fields: fieldValues("hsc-categories-form"), rows: rowState(catTable, ".hsc-cat-row") };
    });
  }
  window.addEventListener("beforeunload", function (e) {
    if (!isSectionsDirty() && !isCategoriesDirty()) return;
    e.preventDefault();
    e.returnValue = "";
  });

  // ---- live preview (Homepage Layout) -----------------------------------
  // A small read-only mirror of what the homepage will look like after
  // Save: rebuilt straight from the editor's own current DOM (section
  // names/order, row order, the Hidden bucket excluded) every time
  // something changes, so it never drifts from what Save would actually
  // persist -- no second source of truth. Kept intentionally simple (a
  // list, not full card chrome): it's a preview of STRUCTURE, not a pixel
  // clone of the homepage.
  var previewBody = document.getElementById("hsc-live-preview-body");
  var previewPanel = document.getElementById("hsc-live-preview");
  var previewToggle = document.getElementById("hsc-live-preview-toggle");
  if (previewBody && kanbanRoot) {
    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, function (c) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
      });
    }
    function renderPreview() {
      // A miniature of the real homepage -- mini teal header, mini search,
      // then one mini row per dashboard grouped by section -- rebuilt from
      // the editor's own DOM on every change, so it never drifts from what
      // Save would actually persist. Strings injected server-side (tr())
      // so the preview is translated exactly like the real page.
      var html = "";
      html += '<div class="hsc-look-header" style="margin-bottom:10px;"><span class="hsc-look-logo"></span><span class="hsc-look-brand">RYOBI LAO</span></div>';
      html += '<div class="hsc-look-search" style="margin-bottom:8px;">' + __PV_SEARCH__ + '</div>';
      html += '<div style="display:flex;gap:5px;margin-bottom:12px;flex-wrap:wrap;">';
      [__PV_CHIP_ALL__, __PV_CHIP_LIVE__, __PV_CHIP_SOON__].forEach(function (chip) {
        html += '<span style="font-size:9px;font-weight:700;color:var(--hsc-ink-faint);border:1px solid var(--hsc-border);border-radius:8px;padding:2px 8px;background:var(--hsc-surface);">' + chip + '</span>';
      });
      html += '</div>';
      kanbanRoot.querySelectorAll(".hsc-layout-section").forEach(function (sec) {
        if (sec.getAttribute("data-section-id") === "hidden") return;
        var nameInput = sec.querySelector(".hsc-section-name");
        var name = nameInput ? nameInput.value : "";
        var rows = Array.prototype.slice.call(sec.querySelectorAll(".hsc-layout-row"));
        if (!rows.length) return;
        html += '<div class="hsc-live-preview-section">';
        html += '<p class="hsc-live-preview-section-title">' + escapeHtml(name) + '</p>';
        rows.forEach(function (row) {
          var color = row.getAttribute("data-color") || "";
          html += '<div class="hsc-pv-card" style="--pv-color:' + (color ? _pvTint(color) : 'var(--hsc-surface-3)') + ';">';
          html += '<span class="hsc-pv-tile"></span>';
          html += '<span class="hsc-pv-label">' + escapeHtml(row.getAttribute("data-label") || "") + '</span>';
          html += '<span class="hsc-pv-dot" style="background:' + (color || 'var(--hsc-ink-faint)') + ';"></span>';
          html += '</div>';
        });
        html += '</div>';
      });
      previewBody.innerHTML = html;
    }
    // Light server-side tint of an accent hex for the mini icon tiles.
    function _pvTint(hex) {
      var m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
      if (!m) return "";
      var n = parseInt(m[1], 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
      return "rgb(" + Math.round(r + (255 - r) * 0.82) + "," + Math.round(g + (255 - g) * 0.82) + "," + Math.round(b + (255 - b) * 0.82) + ")";
    }
    renderPreview();
    document.addEventListener("input", function (e) {
      if (e.target.closest && (e.target.closest("#hsc-kanban") || e.target.closest('#hsc-category-table input[type="color"]'))) renderPreview();
    });
    document.addEventListener("change", function (e) {
      if (e.target.closest && e.target.closest("#hsc-kanban")) renderPreview();
    });
    document.addEventListener("dragend", function () { setTimeout(renderPreview, 0); });
    document.addEventListener("hsc:rowmoved", renderPreview);

    if (previewToggle) {
      previewToggle.addEventListener("click", function () {
        var collapsed = previewPanel.getAttribute("data-collapsed") === "true";
        previewPanel.setAttribute("data-collapsed", collapsed ? "false" : "true");
        previewToggle.setAttribute("aria-expanded", collapsed ? "true" : "false");
        previewToggle.textContent = previewToggle.getAttribute(collapsed ? "data-hide-label" : "data-show-label") || previewToggle.textContent;
      });
    }
  }
})();
"""


def _hsc_render_settings_page(settings, csrf_token, saved=False, category_error=None, import_settings_result=None, view="appearance"):
    import json

    from markupsafe import escape
    from flask import current_app
    from flask_babel import get_locale

    lang = str(get_locale())
    tr = _hsc_tr
    csp_nonce = current_app.jinja_env.globals.get("csp_nonce", lambda: "")()
    accent = _hsc_valid_hex_color(settings.get("accent"), _HSC_DEFAULT_ACCENT)
    # Same header-contrast fix as the homepage: accent-filled controls need
    # adaptive ink; the V6 header itself is fixed dark teal with white ink.
    header_ink = _hsc_ink_on(accent)
    # Same Appearance semantics as the homepage (V6 light-first default).
    theme_mode = settings.get("theme_mode")
    if theme_mode not in ("light", "dark"):
        theme_mode = "light" if settings.get("theme_mode") != "system" else None
    data_theme_attr = f' data-theme="{theme_mode}"' if theme_mode else ""
    meta_color_scheme = {"light": "light", "dark": "dark"}.get(theme_mode, "light dark")
    density = "compact" if settings.get("density") == "compact" else "comfortable"
    data_density_attr = ' data-density="compact"' if density == "compact" else ""
    all_tiles = _hsc_all_tiles()
    dash_to_placeholder_id = _hsc_get_dashboard_to_placeholder_id()
    groups = _hsc_all_groups()
    group_labels = dict(groups)
    group_colors = _hsc_group_colors(groups)

    # V6 architecture: TRUE section switching. The sidebar sets ?view= and
    # only the selected major settings area is rendered into the workspace.
    valid_views = ("appearance", "homepage-layout", "categories", "dashboards", "import-export")
    if view not in valid_views:
        view = "appearance"

    tiles_by_group = {}
    for t in all_tiles:
        tiles_by_group.setdefault(t["group"], []).append(t)

    custom_category_ids = {c["id"] for c in _hsc_get_custom_categories()}

    def render_category_row(gid, glabel, gcolor, index, total):
        count = len(tiles_by_group.get(gid, []))
        is_custom = gid in custom_category_ids
        move_up_label = escape(tr("hsc_move_category_up") % {"category": glabel})
        move_down_label = escape(tr("hsc_move_category_down") % {"category": glabel})
        up_disabled = " disabled" if index == 0 else ""
        down_disabled = " disabled" if index == total - 1 else ""
        icon_chip = f'<span class="hsc-catrow-icon" style="background:{_hsc_tint(gcolor, 0.86)};">{_hsc_group_icon("folder", gcolor)}</span>'
        # Custom categories expose Rename inline via the ⋯ menu; built-ins
        # get a clear "cannot rename/delete" note instead.
        custom_items = f"""
        <form method="POST" action="/hsc/rename-category" class="hsc-cat-pop-form">
          <input type="hidden" name="csrf_token" value="{csrf_token}">
          <input type="hidden" name="key" value="{escape(gid)}">
          <label class="hsc-vh" for="hsc-cat-rename-{escape(gid)}">{escape(tr('category_name_label'))}: {escape(glabel)}</label>
          <input type="text" id="hsc-cat-rename-{escape(gid)}" name="label" value="{escape(glabel)}" maxlength="60" class="hsc-text-input">
          <button type="submit" class="hsc-btn hsc-btn-primary hsc-cat-menu-btn">{escape(tr('save'))}</button>
        </form>""" if is_custom else f'<p class="hsc-cat-pop-note">{escape(tr("builtin_category_note"))}</p>'
        delete_items = ""
        if is_custom:
            delete_items = f"""
        <form method="POST" action="/hsc/delete-category" class="hsc-cat-pop-form hsc-cat-pop-danger">
          <input type="hidden" name="csrf_token" value="{csrf_token}">
          <input type="hidden" name="key" value="{escape(gid)}">
          {(
            f'<p class="hsc-cat-delete-warning">{escape(tr("delete_category_has_dashboards") % {"count": count})}</p>'
            f'<label class="hsc-vh" for="hsc-reassign-{escape(gid)}">{escape(tr("reassign_to_label"))}</label>'
            f'<select id="hsc-reassign-{escape(gid)}" name="reassign_to" class="hsc-cat-reassign-select">'
            + "".join(f'<option value="{escape(og)}">{escape(ol)}</option>' for og, ol in groups if og != gid)
            + '</select>'
          ) if count else f'<p class="hsc-cat-delete-warning">{escape(tr("delete_category_empty"))}</p>'}
          <button type="submit" class="hsc-btn hsc-btn-primary hsc-cat-menu-btn hsc-btn-danger">{escape(tr('delete_category_confirm'))}</button>
        </form>"""
        # Secondary name: custom categories show the other-language label
        # under the primary one (built-ins have none -- they're translated).
        secondary = ""
        if is_custom:
            custom_meta = {c["id"]: c for c in _hsc_get_custom_categories()}.get(gid, {})
            other = custom_meta.get("label_en") or custom_meta.get("label")
            if other and other != glabel:
                secondary = f'<span class="hsc-cat-row-sub">{escape(other)}</span>'
        color_input = (
            f'<span class="hsc-color-wrap" style="flex:0 0 auto;display:inline-flex;position:relative;">'
            f'<input type="color" form="hsc-categories-form" name="category_color_{escape(gid)}" value="{gcolor}" '
            f'aria-label="{escape(tr("category_color_label"))}: {escape(glabel)}" class="hsc-color-input" '
            f'style="width:30px;height:26px;border:none;border-radius:7px;cursor:pointer;"></span>'
        )
        return f"""<div class="hsc-cat-row" data-group-id="{escape(gid)}" draggable="true">
  <button type="button" class="hsc-grab-handle hsc-cat-grab" draggable="true"
    aria-label="{escape(tr('hsc_reorder_category_label') % {'category': glabel})}" title="{escape(tr('drag_handle_hint'))}"
    aria-describedby="hsc-kanban-instructions">&#8942;&#8942;</button>
  {icon_chip}
  <div class="hsc-cat-row-main">
    <span class="hsc-cat-row-name">{escape(glabel)}</span>
    {secondary}
  </div>
  {color_input}
  <span class="hsc-cat-row-count">{count} {escape(tr("dashboard_word" if count == 1 else "dashboards_word"))}</span>
  <details class="hsc-cat-row-menu">
    <summary aria-label="{escape(tr('hsc_move_to_label') % {'card': glabel})}">&#8943;</summary>
    <div class="hsc-row-menu-panel hsc-cat-menu-panel">
      <div class="hsc-cat-pop-section">
        <p class="hsc-cat-pop-title">{escape(tr('rename_pop_title'))}</p>
        {custom_items}
      </div>
      <div class="hsc-cat-pop-section">
        <p class="hsc-cat-pop-title">{escape(tr('change_color_pop_title'))}</p>
        {color_input}
      </div>
      {f'<div class="hsc-cat-pop-section hsc-cat-pop-danger-zone"><p class="hsc-cat-pop-title">{escape(tr("delete_category_confirm"))}</p>{delete_items}</div>' if is_custom else ''}
    </div>
  </details>
</div>"""

    category_rows = list(groups)
    category_table_html = "".join(
        render_category_row(gid, glabel, group_colors[gid], i, len(category_rows))
        for i, (gid, glabel) in enumerate(category_rows)
    )
    categories_json_value = json.dumps({"order": [gid for gid, _ in category_rows]})

    sections = _hsc_effective_sections(settings, all_tiles, dash_to_placeholder_id)
    hidden_ids = set(settings.get("hidden") or [])
    hidden_tiles = [t for t in all_tiles if _hsc_tile_alias_ids(t, dash_to_placeholder_id) & hidden_ids]

    # V6 Homepage Layout editor: stacked collapsible sections; every
    # section a `.hsc-layout-section`; every dashboard a `.hsc-layout-row`
    # with drag handle, icon chip, name, status pill, and an overflow menu
    # ("Move to category…") as the non-drag fallback.
    all_section_ids = [f"s{i}" for i in range(len(sections))] + ["hidden"]
    all_section_names = [sec["name"] for sec in sections] + [tr("hidden_section_name")]

    def render_move_to_select(tile, current_section_id):
        move_label = escape(tr("hsc_move_to_label") % {"card": tile["label"]})
        options = "".join(
            f'<option value="{sid}"{" selected" if sid == current_section_id else ""}>{escape(nm)}</option>'
            for sid, nm in zip(all_section_ids, all_section_names)
        )
        return (
            f'<label class="hsc-vh" for="hsc-move-{escape(tile["id"])}">{move_label}</label>'
            f'<select id="hsc-move-{escape(tile["id"])}" class="hsc-row-move-select" data-tile-id="{escape(tile["id"])}">{options}</select>'
        )

    status_badge = {
        "live": ('<span class="hsc-badge hsc-badge-live">{}</span>').format(escape(tr("live_badge"))),
        "soon": ('<span class="hsc-badge hsc-badge-soon">{}</span>').format(escape(tr("soon"))),
        "na": ('<span class="hsc-badge hsc-badge-na">{}</span>').format(escape(tr("na"))),
    }

    def render_layout_row(tile, section_id):
        gcolor = group_colors.get(tile["group"], _HSC_DEFAULT_ACCENT)
        grab_label = escape(tr("hsc_reorder_card_label") % {"card": tile["label"]})
        drag_hint = escape(tr("drag_handle_hint"))
        badge = status_badge.get(tile["status"], status_badge["na"])
        return f"""<div class="hsc-layout-row" draggable="true" data-tile-id="{escape(tile['id'])}"
    data-label="{escape(tile['label'])}" data-color="{gcolor}" role="listitem">
  <button type="button" class="hsc-grab-handle hsc-row-grab" aria-pressed="false" aria-label="{grab_label}" title="{drag_hint}" aria-describedby="hsc-kanban-instructions">&#8942;&#8942;</button>
  <span class="hsc-layout-row-icon" style="background:{_hsc_tint(gcolor, 0.86)};">{_hsc_group_icon("folder", gcolor)}</span>
  <span class="hsc-layout-row-label">{escape(tile['label'])}</span>
  {badge}
  <details class="hsc-row-menu">
    <summary aria-label="{escape(tr('hsc_move_to_label') % {'card': tile['label']})}">&#8943;</summary>
    <div class="hsc-row-menu-panel">{render_move_to_select(tile, section_id)}</div>
  </details>
</div>"""

    def render_layout_section(section_id, name, tiles, editable_name, is_hidden_col):
        rows_html = "".join(render_layout_row(t, section_id) for t in tiles) or (
            f'<div class="hsc-kanban-empty">{escape(tr("section_empty_hint"))}</div>'
        )
        name_label = escape(tr("hidden_section_label")) if is_hidden_col else escape(tr("section_name_label"))
        name_html = (
            f'<input type="text" class="hsc-section-name" value="{escape(name)}" maxlength="60" '
            f'aria-label="{name_label}: {escape(name)}">'
            if editable_name
            else f'<span class="hsc-section-name-fixed">{escape(name)}</span>'
        )
        collapse_label = escape(tr("collapse_section") % {"section": name})
        handle_html = ""
        if not is_hidden_col:
            section_grab_label = escape(tr("hsc_reorder_category_label") % {"category": name})
            handle_html = (
                f'<button type="button" class="hsc-grab-handle hsc-sec-grab" aria-pressed="false" '
                f'aria-label="{section_grab_label}" aria-describedby="hsc-section-instructions">&#8942;&#8942;</button>'
            )
        draggable_attr = "" if is_hidden_col else ' draggable="true"'
        sec_icon_color = group_colors.get(all_section_ids[0] and section_id, _HSC_DEFAULT_ACCENT)
        add_html = "" if is_hidden_col else (
            f'<a class="hsc-layout-add-link" href="/hsc/menu-settings?view=dashboards">+ {escape(tr("add_dashboard_button"))}</a>'
        )
        return f"""<div class="hsc-layout-section" data-section-id="{section_id}"{draggable_attr}>
  <div class="hsc-layout-section-head">
    {handle_html}
    <button type="button" class="hsc-section-collapse" aria-expanded="true" aria-label="{collapse_label}" data-collapse-label="{collapse_label}" data-expand-label="{escape(tr('expand_section') % {'section': name})}">&#9662;</button>
    <span class="hsc-sec-icon" style="background:{_hsc_tint(group_colors.get(name, _HSC_DEFAULT_ACCENT), 0.86)};">{_hsc_group_icon("folder", group_colors.get(name, _HSC_DEFAULT_ACCENT))}</span>
    {name_html}
    <span class="hsc-layout-count">{len(tiles)}</span>
    {add_html}
  </div>
  <div class="hsc-layout-rows" role="list" aria-label="{escape(name)}">{rows_html}</div>
</div>"""

    kanban_html = "".join(
        render_layout_section(f"s{i}", sec["name"], sec["tiles"], True, False) for i, sec in enumerate(sections)
    ) + render_layout_section("hidden", tr("hidden_section_name"), hidden_tiles, False, True)

    # Per-form save status (§5aw), rendered inside its own form card.
    def hsc_status(role, text, cls, status_id=None):
        id_attr = f' id="{status_id}" tabindex="-1"' if status_id else ""
        return (
            f'<p role="{role}"{id_attr} class="hsc-form-status" style="{cls}margin:10px 0 0;'
            f'padding:8px 12px;border-radius:8px;font-size:12px;font-weight:600;outline:none;">{escape(text)}</p>'
        )

    saved_flags = saved.split(",") if isinstance(saved, str) else ([] if not saved else ["appearance"])
    status_saved_style = "background:var(--hsc-badge-live-bg);color:var(--hsc-badge-live-fg);"
    appearance_status = hsc_status("status", f"✓ {tr('saved')}", status_saved_style, "hsc-status-appearance") if "appearance" in saved_flags else ""
    sections_status = hsc_status("status", f"✓ {tr('saved')}", status_saved_style, "hsc-status-sections") if "sections" in saved_flags else ""
    categories_status = hsc_status("status", f"✓ {tr('saved')}", status_saved_style, "hsc-status-categories") if "categories" in saved_flags else ""
    if "category" in saved_flags:
        category_status = hsc_status("status", f"✓ {tr('saved')}", status_saved_style, "hsc-status-category")
    elif category_error:
        if category_error == "!db":
            error_text = tr("category_create_failed")
        else:
            error_text = tr("category_exists") % {"name": category_error}
        category_status = hsc_status("alert", error_text, "background:var(--hsc-badge-na-bg);color:var(--hsc-badge-na-fg);", "hsc-status-category")
    else:
        category_status = ""

    swatches_html = "".join(
        f'<button type="submit" name="preset_accent" value="{c}" aria-label="{escape(tr("accent_label"))}: {c}" class="hsc-swatch{" hsc-swatch-current" if c == accent else ""}"'
        f'style="background:{c};"></button>'
        for c in _HSC_TILE_PALETTE
    )

    category_options = "".join(f'<option value="{gid}">{escape(glabel)}</option>' for gid, glabel in groups)

    # Dashboard Management list: title, category select (auto-submit), status.
    live_dashboard_tiles = [t for t in all_tiles if t["status"] == "live" and t["id"].startswith("dash:")]

    def render_dashboard_row(tile):
        dash_id = tile["id"].split(":", 1)[1]
        options = "".join(
            f'<option value="{gid}"{" selected" if gid == tile["group"] else ""}>{escape(glabel)}</option>'
            for gid, glabel in groups
        )
        select_id = f"hsc-dash-group-{escape(dash_id)}"
        gcolor = group_colors.get(tile["group"], _HSC_DEFAULT_ACCENT)
        badge = status_badge.get(tile["status"], status_badge["na"])
        # Actions: Open (real link) + Move category (the supported POST) in
        # one compact ⋯ menu -- no exposed dropdown on every row.
        return f"""<div class="hsc-dashboard-list-row" data-dash-label="{escape(tile['label'])}">
  <span class="hsc-layout-row-icon" style="background:{_hsc_tint(gcolor, 0.86)};">{_hsc_group_icon("folder", gcolor)}</span>
  <span class="hsc-dashboard-list-title">{escape(tile['label'])}</span>
  <span class="hsc-dashboard-list-cat">{escape(group_labels.get(tile['group'], tile['group']))}</span>
  {badge}
  <details class="hsc-row-menu">
    <summary aria-label="{escape(tr('dashboard_actions_label') % {'dashboard': tile['label']})}">&#8943;</summary>
    <div class="hsc-row-menu-panel hsc-dash-menu-panel">
      <a class="hsc-btn hsc-btn-ghost hsc-cat-menu-btn" href="{escape(tile['href'])}" target="_blank" rel="noopener">{escape(tr('open_action'))}</a>
      <form method="POST" action="/hsc/recategorize-dashboard" class="hsc-cat-pop-form">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <input type="hidden" name="dash_id" value="{escape(dash_id)}">
        <input type="hidden" name="old_group" value="{escape(tile['group'])}">
        <label class="hsc-vh" for="{select_id}">{escape(tr('dashboard_category_label') % {'dashboard': tile['label']})}</label>
        <select id="{select_id}" name="new_group" class="hsc-dashboard-list-select">{options}</select>
        <button type="submit" class="hsc-btn hsc-btn-primary hsc-cat-menu-btn">{escape(tr('move_action'))}</button>
      </form>
    </div>
  </details>
</div>"""

    dashboard_list_html = "".join(render_dashboard_row(t) for t in live_dashboard_tiles) or (
        f'<p class="hsc-dash-empty">{escape(tr("empty_home_title"))}</p>'
    )

    if import_settings_result == "ok":
        import_settings_status = hsc_status("status", f"✓ {tr('import_settings_success')}", status_saved_style)
    elif import_settings_result == "invalid":
        import_settings_status = hsc_status(
            "alert", tr("import_settings_invalid"), "background:var(--hsc-badge-na-bg);color:var(--hsc-badge-na-fg);"
        )
    else:
        import_settings_status = ""

    def render_segmented(name, options, current):
        buttons = "".join(
            f'<button type="submit" name="{name}" value="{value}" class="hsc-seg{" hsc-seg-current" if value == current else ""}">{escape(label)}</button>'
            for value, label in options
        )
        return f'<div class="hsc-seg-group">{buttons}</div>'

    appearance_mode_html = render_segmented(
        "theme_mode",
        [("light", tr("mode_light")), ("dark", tr("mode_dark")), ("system", tr("mode_system"))],
        theme_mode or "system",
    )
    density_html = render_segmented(
        "density",
        [("comfortable", tr("density_comfortable")), ("compact", tr("density_compact"))],
        density,
    )

    # Live-announcement templates for the keyboard-move engine (§5av).
    kanban_a11y_i18n = {
        key: tr(key)
        for key in (
            "hsc_picked_up_card",
            "hsc_picked_up_category",
            "hsc_moved_card_to_section",
            "hsc_moved_category",
            "hsc_move_canceled",
        )
    }
    kanban_a11y_script = "var HSC_I18N = " + json.dumps(kanban_a11y_i18n) + ";\n" + _HSC_KANBAN_A11Y_JS

    hsc_settings_extras_script = _HSC_SETTINGS_EXTRAS_JS.replace("__ACCENT__", accent).replace(
        "__PV_SEARCH__", json.dumps(tr("search_placeholder"))
    ).replace(
        "__PV_CHIP_ALL__", json.dumps(tr("filter_all"))
    ).replace(
        "__PV_CHIP_LIVE__", json.dumps(tr("live_badge"))
    ).replace(
        "__PV_CHIP_SOON__", json.dumps(tr("soon"))
    )

    drag_hint_i18n = "var HSC_DRAG_HINT = " + json.dumps(tr("drag_handle_hint")) + ";\n" + (
        "document.addEventListener('mouseover', function(e) {\n"
        "  var h = e.target.closest && e.target.closest('.hsc-grab-handle');\n"
        "  if (h && h.title !== HSC_DRAG_HINT) h.title = HSC_DRAG_HINT;\n"
        "});"
    )

    dnd_feedback_script = """
(function() {
  var live = document.getElementById('hsc-announcer');
  var draggedName = '';
  function nameOf(el) {
    if (!el) return '';
    if (el.classList.contains('hsc-layout-row')) return el.getAttribute('data-label') || '';
    if (el.classList.contains('hsc-layout-section')) {
      var i = el.querySelector('.hsc-section-name');
      if (i) return i.value;
      var f = el.querySelector('.hsc-section-name-fixed');
      return f ? f.textContent.trim() : (el.getAttribute('data-section-id') || '');
    }
    return '';
  }
  function clearTargets() {
    document.querySelectorAll('.hsc-drop-target').forEach(function(el) { el.classList.remove('hsc-drop-target'); });
  }
  var root = document.getElementById('hsc-kanban');
  if (!root) return;
  root.addEventListener('dragstart', function(e) {
    var row = e.target.closest && e.target.closest('.hsc-layout-row');
    var sec = e.target.closest && e.target.closest('.hsc-layout-section');
    var el = row || sec;
    draggedName = nameOf(el);
    if (el) el.classList.add('hsc-dragging');
    if (live && draggedName) live.textContent = draggedName;
  });
  root.addEventListener('dragover', function(e) {
    var sec = e.target.closest && e.target.closest('.hsc-layout-section');
    clearTargets();
    if (sec && !sec.classList.contains('hsc-dragging')) {
      sec.classList.add('hsc-drop-target');
      var toggle = sec.querySelector('.hsc-section-collapse');
      var rows = sec.querySelector('.hsc-layout-rows');
      if (toggle && rows && rows.hidden) {
        rows.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
      }
    }
  });
  root.addEventListener('dragleave', function(e) {
    if (e.target === root) clearTargets();
  });
  root.addEventListener('drop', clearTargets);
  root.addEventListener('dragend', function(e) {
    var el = e.target.closest && e.target.closest('.hsc-layout-row, .hsc-layout-section');
    if (el) el.classList.remove('hsc-dragging');
    clearTargets();
    draggedName = '';
  });
})();
"""

    # f-strings can't carry escaped quotes inside expressions (Python <3.12
    # hard rule), so conditional attributes come from plain code, not
    # inline conditionals inside f-strings.

    # Sidebar nav -- each item a real link to ?view=, so only the selected
    # major settings area renders (true section switching, not scrollspy).
    # Icons are solid-path (sanitizer-safe) and descriptions are one-liners
    # shown at desktop width, per the V6 "enterprise settings navigation"
    # direction.
    nav_icons = {
        "appearance": "<circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M12 3a9 9 0 0 0 0 18 9 9 0 0 1 0-18z\"/>",
        "homepage-layout": "<path d=\"M3 3h8v8H3zM13 3h8v8h-8zM3 13h8v8H3zM13 13h8v8h-8z\"/>",
        "categories": "<path d=\"M3 6h6l2 2h10v11H3z\"/>",
        "dashboards": "<path d=\"M4 4h16v4H4zM4 10h9v10H4zM15 10h5v10h-5z\"/>",
        "import-export": "<path d=\"M8 3v10H4l5 6 5-6h-4V3h-2zM17 21V11h4l-5-6-5 6h4v10h2z\"/>",
    }
    nav_defs = [
        ("appearance", tr("appearance_label"), tr("sidebar_desc_appearance")),
        ("homepage-layout", tr("homepage_layout_title"), tr("sidebar_desc_homepage")),
        ("categories", tr("categories_layout_title"), tr("sidebar_desc_categories")),
        ("dashboards", tr("dashboard_management_title"), tr("sidebar_desc_dashboards")),
        ("import-export", tr("import_export_title"), tr("sidebar_desc_importexport")),
    ]

    def nav_icon_html(vid, color):
        # Backslash-free: escaped quotes inside an f-string expression crash
        # Python 3.11, so the path markup is built by plain concatenation.
        paths = "".join('<path d="' + d + '" fill="' + color + '"/>' for d in _HSC_GROUP_ICON_PATHS.get("folder", []))
        return (
            '<span class="hsc-nav-icon"><svg aria-hidden="true" viewBox="0 0 24 24" '
            'xmlns="http://www.w3.org/2000/svg">' + paths + "</svg></span>"
        )

    nav_html = ""
    for vid, label, desc in nav_defs:
        is_current = vid == view
        icon_color = accent if is_current else "currentColor"
        icon = (
            f'<span class="hsc-nav-icon"><svg aria-hidden="true" viewBox="0 0 24 24" '
            f'xmlns="http://www.w3.org/2000/svg">'
            + "".join(f'<path d="{d}" fill="{icon_color}"/>' for d in (
                _HSC_GROUP_ICON_PATHS.get(
                    {"homepage-layout": "pl", "categories": "folder", "dashboards": "mh", "import-export": "folder", "appearance": "folder"}.get(vid, "folder")
                )
                or _HSC_GROUP_ICON_PATHS["_default"]
            ))
            + '</svg></span>'
        )
        current_attr = ' aria-current="location"' if is_current else ""
        nav_html += (
            f'<a class="hsc-nav-link" href="/hsc/menu-settings?view={vid}"{current_attr}>'
            f'{icon}<span class="hsc-nav-text"><span>{escape(label)}</span>'
            f'<span class="hsc-nav-desc">{escape(desc)}</span></span></a>'
        )

    # ---------------- View bodies (only the selected one is rendered) ------
    def look_preview_html():
        """A live miniature of the themed homepage, rendered from the same
        --hsc-* tokens the real page uses -- the right-rail preview that
        makes every Appearance choice immediately understandable."""
        return f"""<aside class="hsc-look-preview" aria-label="{escape(tr('live_preview_title'))}">
  <h3 class="hsc-live-preview-title">{escape(tr("live_preview_title"))}</h3>
  <p class="hsc-live-preview-hint" style="margin-bottom:12px;">{escape(tr("live_preview_hint"))}</p>
  <div class="hsc-look-frame">
    <div class="hsc-look-header">
      <span class="hsc-look-logo"></span>
      <span class="hsc-look-brand">RYOBI LAO</span>
      <span class="hsc-look-spacer"></span>
      <span class="hsc-look-pill">{escape(tr("logout"))}</span>
    </div>
    <div class="hsc-look-search">
      <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--hsc-ink-faint)" stroke-width="2.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      {escape(tr("search_placeholder"))}
    </div>
    <div class="hsc-look-cards">
      <div class="hsc-look-card">
        <span class="hsc-look-tile" style="background:{_hsc_tint(accent, 0.86)};"></span>
        <span class="hsc-look-line"></span>
        <span class="hsc-look-line hsc-look-line-short"></span>
        <span class="hsc-look-badge">{escape(tr("live_badge"))}</span>
      </div>
      <div class="hsc-look-card">
        <span class="hsc-look-tile" style="background:var(--hsc-surface-3);"></span>
        <span class="hsc-look-line"></span>
        <span class="hsc-look-line hsc-look-line-short"></span>
        <span class="hsc-look-badge hsc-look-badge-soon">{escape(tr("soon"))}</span>
      </div>
    </div>
  </div>
</aside>"""

    view_body = ""
    if view == "appearance":
        view_body = f"""
  <div class="hsc-view-head">
    <h2 class="hsc-view-title">{escape(tr("appearance_title"))}</h2>
    <div class="hsc-view-hint">{escape(tr("appearance_hint"))}</div>
  </div>
  <div class="hsc-appearance-grid">
  <form method="POST" action="/hsc/menu-settings" class="hsc-view-form">
    <input type="hidden" name="csrf_token" value="{csrf_token}">
    <div class="hsc-setting-card">
      <div class="hsc-setting-card-head">
        <h2 class="hsc-setting-card-title">{escape(tr("theme_color_label"))}</h2>
        <input type="color" name="accent" value="{accent}" aria-label="{escape(tr("theme_color_label"))}" class="hsc-color-lg">
      </div>
      <div class="hsc-setting-hint">{escape(tr("theme_presets_hint"))}</div>
      <div class="hsc-swatch-row">{swatches_html}</div>
    </div>
    <div class="hsc-setting-card">
      <h2 class="hsc-setting-card-title">{escape(tr("display_mode_label"))}</h2>
      {appearance_mode_html}
    </div>
    <div class="hsc-setting-card">
      <h2 class="hsc-setting-card-title">{escape(tr("card_density_label"))}</h2>
      {density_html}
    </div>
    <div class="hsc-appearance-actions">
      <a class="hsc-btn hsc-btn-ghost" href="/welcome/">{escape(tr("back_home_btn"))}</a>
      <button type="submit" class="hsc-btn hsc-btn-primary">{escape(tr("save_appearance"))}</button>
    </div>
    {appearance_status}
  </form>
  {look_preview_html()}
  </div>"""
    elif view == "homepage-layout":
        view_body = f"""
  <div class="hsc-view-head">
    <h2 class="hsc-view-title">{escape(tr("homepage_layout_title"))}</h2>
    <div class="hsc-view-hint">{escape(tr("homepage_layout_hint"))}</div>
  </div>
  <p id="hsc-kanban-instructions" class="hsc-vh">{escape(tr("hsc_kanban_instructions"))}</p>
  <p id="hsc-section-instructions" class="hsc-vh">{escape(tr("hsc_section_instructions"))}</p>
  <div class="hsc-layout-with-preview">
    <form id="hsc-sections-form" method="POST" action="/hsc/save-sections">
      <input type="hidden" name="csrf_token" value="{csrf_token}">
      <input type="hidden" name="sections_json" id="hsc-sections-json" value="">
      <div class="hsc-save-bar hsc-save-bar-top">
        <span class="hsc-save-bar-status" id="hsc-sections-dirty" hidden>{escape(tr("unsaved_changes_chip"))}</span>
        <span class="hsc-save-bar-saved" id="hsc-sections-saved" hidden>{escape(tr('saved'))}</span>
        <div class="hsc-save-bar-actions">
          <button type="button" class="hsc-btn hsc-btn-reset" id="hsc-sections-reset">{escape(tr("reset_layout"))}</button>
          <button type="submit" class="hsc-btn hsc-btn-primary">{escape(tr("save_layout"))}</button>
        </div>
      </div>
      <div id="hsc-kanban">{kanban_html}</div>
      {sections_status}
    </form>
    <aside class="hsc-live-preview" id="hsc-live-preview" data-collapsed="true">
      <div class="hsc-live-preview-head">
        <div>
          <h3 class="hsc-live-preview-title">{escape(tr("live_preview_title"))}</h3>
          <p class="hsc-live-preview-hint">{escape(tr("live_preview_hint"))}</p>
        </div>
        <button type="button" class="hsc-btn hsc-btn-ghost hsc-live-preview-toggle" id="hsc-live-preview-toggle" aria-expanded="false"
        data-show-label="{escape(tr('live_preview_toggle'))}" data-hide-label="{escape(tr('hide_preview_toggle'))}">{escape(tr("live_preview_toggle"))}</button>
      </div>
      <div class="hsc-live-preview-body" id="hsc-live-preview-body"></div>
      <a class="hsc-live-preview-full" href="/welcome/" target="_blank" rel="noopener">{escape(tr("open_full_preview"))} &#8599;</a>
    </aside>
  </div>"""
    elif view == "categories":
        view_body = f"""
  <div class="hsc-view-head" style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
    <div>
      <h2 class="hsc-view-title">{escape(tr("categories_layout_title"))}</h2>
      <div class="hsc-view-hint">{escape(tr("categories_table_hint"))}</div>
    </div>
    <button type="button" id="hsc-add-category-btn" class="hsc-btn hsc-btn-primary" style="flex:0 0 auto;">+ {escape(tr("add_category_title"))}</button>
  </div>
  <details id="add-category-panel" class="hsc-setting-card hsc-create-card" style="margin-bottom:16px;">
    <summary class="hsc-create-summary" hidden aria-hidden="true">{escape(tr("add_category_title"))}</summary>
    <div class="hsc-create-body">
    <div class="hsc-setting-hint" style="margin-bottom:12px;">{escape(tr("add_category_hint"))}</div>
    {category_status}
    <form method="POST" action="/hsc/create-category" style="display:flex;gap:10px;flex-wrap:wrap;">
      <input type="hidden" name="csrf_token" value="{csrf_token}">
      <label for="hsc-new-category-ja" class="hsc-vh">{escape(tr('new_category_name_ja'))}</label>
      <input type="text" id="hsc-new-category-ja" name="category_label_ja" required maxlength="60" placeholder="{escape(tr('new_category_name_ja'))}" class="hsc-text-input" style="flex:1;min-width:180px;">
      <label for="hsc-new-category-en" class="hsc-vh">{escape(tr('new_category_name_en'))}</label>
      <input type="text" id="hsc-new-category-en" name="category_label_en" maxlength="60" placeholder="{escape(tr('new_category_name_en'))}" class="hsc-text-input" style="flex:1;min-width:180px;">
      <button type="submit" class="hsc-btn hsc-btn-primary">+ {escape(tr("create_category_button"))}</button>
    </form>
    </div>
  </details>
  <form id="hsc-categories-form" method="POST" action="/hsc/save-categories" class="hsc-setting-card" style="padding:6px 8px;">
    <input type="hidden" name="csrf_token" value="{csrf_token}">
    <input type="hidden" name="categories_json" value='{categories_json_value}'>
    <div id="hsc-category-table">{category_table_html}</div>
    <div class="hsc-save-bar" style="border:none;box-shadow:none;padding:12px 12px 14px;margin-top:4px;background:transparent;position:static;">
      <span class="hsc-save-bar-status" id="hsc-categories-dirty" hidden>{escape(tr("unsaved_changes_chip"))}</span>
      <div class="hsc-save-bar-actions">
        <button type="button" class="hsc-btn hsc-btn-reset" id="hsc-categories-reset">{escape(tr("reset_layout"))}</button>
        <button type="submit" class="hsc-btn hsc-btn-primary">{escape(tr("save_categories"))}</button>
      </div>
    </div>
    {categories_status}
  </form>"""
    elif view == "dashboards":
        view_body = f"""
  <div class="hsc-view-head" style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap;">
    <div>
      <h2 class="hsc-view-title">{escape(tr("dashboard_management_title"))}</h2>
      <div class="hsc-view-hint">{escape(tr("dashboard_list_hint"))}</div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;flex:0 0 auto;">
      <button type="button" id="hsc-import-dash-btn" class="hsc-btn hsc-btn-ghost">{escape(tr("import_button"))}</button>
      <button type="button" id="hsc-create-dash-btn" class="hsc-btn hsc-btn-primary">+ {escape(tr("create_dashboard_button"))}</button>
    </div>
  </div>
  <details id="add-dashboard" class="hsc-setting-card hsc-create-card">
    <summary class="hsc-create-summary">{escape(tr("add_dashboard_title"))}</summary>
    <div class="hsc-create-body">
      <div class="hsc-setting-hint" style="margin-bottom:12px;">{escape(tr("add_dashboard_hint"))}</div>
      <form method="POST" action="/hsc/create-dashboard-custom" class="hsc-inline-form">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <label for="hsc-new-dashboard-title" class="hsc-field-label">{escape(tr("new_dashboard_name"))}
          <input type="text" id="hsc-new-dashboard-title" name="new_title" required class="hsc-text-input">
        </label>
        <label for="hsc-new-dashboard-group" class="hsc-field-label">{escape(tr("new_dashboard_group"))}
          <select id="hsc-new-dashboard-group" name="new_group" class="hsc-text-input">{category_options}</select>
        </label>
        <div style="display:flex;gap:10px;">
          <button type="button" id="hsc-cancel-create-dash" class="hsc-btn hsc-btn-ghost">{escape(tr("cancel_action"))}</button>
          <button type="submit" class="hsc-btn hsc-btn-primary hsc-field-submit">+ {escape(tr("create_and_open"))}</button>
        </div>
      </form>
    </div>
  </details>
  <details id="dashboard-import" class="hsc-setting-card hsc-create-card" style="margin-top:14px;">
    <summary class="hsc-create-summary">{escape(tr("dashboard_import_title"))}</summary>
    <div class="hsc-create-body">
      <div class="hsc-setting-hint" style="margin-bottom:12px;">{escape(tr("import_hint"))}</div>
      <form method="POST" action="/hsc/import-dashboard" enctype="multipart/form-data">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <label for="hsc-import-file" id="hsc-import-dropzone">
          <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="{accent}" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M12 4l-4 4M12 4l4 4"/>
          <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>
          <span id="hsc-import-filename">{escape(tr("drop_file_here"))}</span>
          <input type="file" id="hsc-import-file" name="import_file" accept=".zip,.json" required
          style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;">
        </label>
        <button type="submit" class="hsc-btn hsc-btn-primary" style="width:100%;margin-top:12px;">{escape(tr("import_button"))}</button>
      </form>
    </div>
  </details>
  <div class="hsc-setting-card" style="margin-top:14px;padding:0;overflow:hidden;">
    <div class="hsc-dash-table-head">
      <input type="search" id="hsc-dash-search" placeholder="{escape(tr("search_placeholder"))}" autocomplete="off" class="hsc-dash-search">
    </div>
    <div class="hsc-dashboard-list">{dashboard_list_html}</div>
  </div>"""
    else:  # import-export
        view_body = f"""
  <div class="hsc-view-head">
    <h2 class="hsc-view-title">{escape(tr("import_export_title"))}</h2>
    <div class="hsc-view-hint">{escape(tr("import_export_hint"))}</div>
  </div>
  <div class="hsc-form-grid">
    <div class="hsc-setting-card">
      <h3 class="hsc-setting-card-title">{escape(tr("export_title"))}</h3>
      <div class="hsc-setting-hint" style="margin-bottom:14px;">{escape(tr("export_hint"))}</div>
      <p style="font-size:13px;font-weight:700;color:var(--hsc-ink);margin:0 0 2px;">{escape(tr("whats_backed_up_title"))}</p>
      <ul class="hsc-backup-list">
        <li>&#10003; {escape(tr("whats_backed_up_layout"))}</li>
        <li>&#10003; {escape(tr("whats_backed_up_order"))}</li>
        <li>&#10003; {escape(tr("whats_backed_up_colors"))}</li>
      </ul>
      <a class="hsc-btn hsc-btn-primary" style="margin-top:14px;display:inline-flex;" href="/hsc/export-settings">&#8659; {escape(tr("export_settings_button"))}</a>
    </div>
    <div class="hsc-setting-card">
      <h3 class="hsc-setting-card-title">{escape(tr("import_title_v6"))}</h3>
      <div class="hsc-setting-hint" style="margin-bottom:14px;">{escape(tr("import_hint_v6"))}</div>
      <form method="POST" action="/hsc/import-settings" enctype="multipart/form-data" id="hsc-import-settings-form" class="hsc-import-settings-form">
        <input type="hidden" name="csrf_token" value="{csrf_token}">
        <label for="hsc-import-settings-file" id="hsc-import-settings-dropzone">
          <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="{accent}" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M12 4l-4 4M12 4l4 4"/>
          <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>
          <span id="hsc-import-settings-filename">{escape(tr("drop_file_here"))}</span>
          <input type="file" id="hsc-import-settings-file" name="config_file" accept=".json" required
          style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;">
        </label>
        <button type="submit" class="hsc-btn hsc-btn-ghost" style="width:100%;margin-top:12px;">{escape(tr("import_settings_button"))}</button>
      </form>
      {import_settings_status}
    </div>
  </div>
  <div class="hsc-setting-card" style="margin-top:20px;">
    <h3 class="hsc-setting-card-title">{escape(tr("whats_backed_up_title"))}</h3>
    <ul class="hsc-backup-list">
      <li>{escape(tr("whats_backed_up_layout"))}</li>
      <li>{escape(tr("whats_backed_up_order"))}</li>
      <li>{escape(tr("whats_backed_up_colors"))}</li>
    </ul>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="{lang}"{_hsc_dir_attr(lang)}{data_theme_attr}{data_density_attr}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="{meta_color_scheme}">
<title>{escape(tr("settings_title"))}</title>
<style>
{_hsc_theme_style_block(accent)}
/* Keyboard-accessible alternative to HTML5 drag (§5av) -- a real <button>
   grab handle per card/section; aria-pressed carries grab state. */
.hsc-grab-handle {{ border:1px solid var(--hsc-border); background:var(--hsc-surface-2); color:var(--hsc-ink-muted);
  border-radius:6px; width:26px; height:26px; font-size:13px; line-height:1; cursor:grab; flex:0 0 auto; position:relative; }}
.hsc-grab-handle::after {{ content:""; position:absolute; top:-8px; left:-8px; right:-8px; bottom:-8px; }}
.hsc-grab-handle[aria-pressed="true"] {{ background:{accent}; border-color:{accent}; color:{header_ink}; }}
.hsc-grab-handle:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-layout-row.hsc-grabbed {{ outline:2px solid {accent}; outline-offset:2px; box-shadow:0 4px 12px rgba(0,0,0,0.15); }}
.hsc-layout-section-head.hsc-grabbed {{ outline:2px solid {accent}; outline-offset:-2px; }}
.hsc-color-wrap::after {{ content:""; position:absolute; top:-3px; left:-8px; right:-8px; bottom:-3px; cursor:pointer; }}

/* ==== V6 settings chrome -- same product header system as the homepage:
   teal shell, logo + page title block on the left, real controls on the
   right, so both pages obviously belong to one product. ==== */
.hsc-app-header {{ background:#073442; box-shadow:0 2px 8px #082e4020; padding:14px 32px; position:sticky; top:0; z-index:20; }}
.hsc-app-header-inner {{ display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; max-width:1480px; margin:0 auto; }}
.hsc-brand {{ display:flex; align-items:center; gap:14px; min-width:0; }}
.hsc-brand-logo {{ background:#FFFFFF; border-radius:10px; padding:8px 13px; display:flex; align-items:center; flex:0 0 auto; }}
.hsc-brand-sub {{ font-size:12px; color:rgba(255,255,255,0.72); line-height:1.25; white-space:normal; overflow-wrap:anywhere; }}
.hsc-header-controls {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; }}
.hsc-back-pill {{ display:inline-flex; align-items:center; font-size:13px; color:#FFFFFF; background:rgba(255,255,255,0.14);
  padding:8px 16px; border-radius:20px; font-weight:600; text-decoration:none; white-space:nowrap; }}
.hsc-back-pill:hover {{ background:rgba(255,255,255,0.25); }}
.hsc-back-pill:focus-visible {{ outline:2px solid #FFFFFF; outline-offset:2px; }}
.hsc-header-h1 {{ color:#FFFFFF; font-size:19px; font-weight:700; margin:0; white-space:normal; overflow-wrap:anywhere; line-height:1.3; }}
.hsc-brand > div[style] {{ min-width:0; }}
.hsc-logout-ghost {{ display:inline-flex; align-items:center; font-size:13px; color:#FFFFFF; background:rgba(255,255,255,0.14);
  padding:9px 18px; border-radius:10px; font-weight:700; text-decoration:none; white-space:nowrap; }}
.hsc-logout-ghost:hover {{ background:rgba(255,255,255,0.25); }}
.hsc-logout-ghost:focus-visible {{ outline:2px solid #FFFFFF; outline-offset:2px; }}
.hsc-page {{ max-width:1544px; margin:0 auto; padding:28px 32px 56px; box-sizing:border-box; }}
.hsc-settings-shell {{ margin-top:0; }}
.hsc-view-form {{ display:flex; flex-direction:column; gap:20px; max-width:780px; }}
.hsc-setting-card {{ background:var(--hsc-surface); border:1px solid var(--hsc-border); border-radius:var(--hsc-radius);
  padding:24px 26px; box-shadow:var(--hsc-card-shadow); }}
.hsc-setting-card-title {{ font-size:17px; font-weight:700; color:var(--hsc-ink); margin:0 0 6px; }}
.hsc-setting-hint {{ font-size:13px; color:var(--hsc-ink-muted); line-height:1.6; }}
.hsc-setting-card-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; }}
.hsc-color-lg {{ width:52px; height:38px; border:1px solid var(--hsc-border); border-radius:10px; cursor:pointer; background:var(--hsc-surface); }}
.hsc-swatch-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:14px; }}
.hsc-swatch {{ width:38px; height:38px; border-radius:50%; border:2px solid var(--hsc-border); cursor:pointer; padding:0; box-shadow:0 1px 3px rgba(16,24,40,0.15); }}
.hsc-swatch:hover {{ transform:scale(1.08); }}
.hsc-swatch-current {{ border-color:var(--hsc-ink); outline:2px solid {accent}; outline-offset:2px; }}
.hsc-swatch:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-seg-group {{ display:flex; gap:4px; background:var(--hsc-surface-2); border-radius:12px; padding:4px; margin-top:10px; max-width:420px; }}
.hsc-seg {{ flex:1; padding:10px 12px; border-radius:9px; border:none; font-size:13.5px; font-weight:700; cursor:pointer;
  background:transparent; color:var(--hsc-ink-muted); font-family:inherit; }}
.hsc-seg:hover {{ color:var(--hsc-ink); }}
.hsc-seg-current {{ background:{accent}; color:{header_ink}; box-shadow:0 1px 3px rgba(16,24,40,0.2); }}
.hsc-seg:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-appearance-actions {{ display:flex; gap:12px; max-width:640px; }}
.hsc-appearance-actions .hsc-btn {{ flex:1; padding:13px 24px; }}
.hsc-view-head {{ margin-bottom:20px; }}
.hsc-view-title {{ font-size:28px; font-weight:700; color:var(--hsc-ink); margin:0 0 6px; letter-spacing:-0.01em; line-height:1.3; }}
.hsc-view-hint {{ font-size:14px; color:var(--hsc-ink-muted); line-height:1.6; max-width:680px; }}

/* ==== Homepage Layout editor (V6) -- contained editable components ==== */
.hsc-layout-section {{ background:var(--hsc-surface); border:1px solid var(--hsc-border); border-radius:var(--hsc-radius);
  margin-bottom:16px; overflow:hidden; box-shadow:var(--hsc-card-shadow); transition:border-color .15s ease, box-shadow .15s ease; }}
.hsc-layout-section:hover {{ border-color:var(--hsc-border-strong); }}
.hsc-layout-section.hsc-drop-target {{ outline:2px dashed {accent}; outline-offset:-2px; border-color:{accent}; }}
.hsc-layout-section-head {{ display:flex; align-items:center; flex-wrap:wrap; gap:10px; padding:14px 16px; min-height:56px; box-sizing:border-box;
  background:var(--hsc-surface-2); border-bottom:1px solid var(--hsc-border); min-width:0; }}
.hsc-sec-icon {{ width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex:0 0 auto; }}
.hsc-sec-icon svg {{ width:17px; height:17px; }}
.hsc-sec-grab {{ cursor:grab; font-size:11px; letter-spacing:-1px; }}
.hsc-section-collapse {{ border:none; background:none; color:var(--hsc-ink-muted); cursor:pointer; width:26px; height:26px;
  border-radius:6px; flex:0 0 auto; font-size:12px; display:flex; align-items:center; justify-content:center; transition:transform .15s ease; }}
.hsc-section-collapse:hover {{ background:var(--hsc-surface-3); color:var(--hsc-ink); }}
.hsc-section-collapse:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-section-collapse[aria-expanded="false"] {{ transform:rotate(-90deg); }}
.hsc-section-name {{ flex:1; min-width:140px; border:none; background:transparent; font-size:15px; font-weight:700;
  color:var(--hsc-ink); padding:5px 4px; outline:none; border-radius:6px; }}
.hsc-section-name:focus-visible {{ outline:2px solid {accent}; outline-offset:1px; }}
.hsc-section-name-fixed {{ flex:1; min-width:0; font-size:15px; font-weight:700; color:var(--hsc-ink-muted); padding:5px 4px; }}
.hsc-layout-count {{ font-size:12px; font-weight:700; color:{accent}; background:{accent}14;
  border-radius:10px; padding:2px 10px; flex:0 0 auto; }}
.hsc-layout-add-link {{ font-size:12.5px; font-weight:700; color:{accent}; text-decoration:none; flex:0 0 auto;
  white-space:nowrap; padding:6px 10px; border-radius:8px; border:1px solid {accent}3D; }}
.hsc-layout-add-link:hover {{ background:{accent}0D; text-decoration:none; }}
.hsc-layout-add-link:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-layout-rows {{ padding:12px; display:flex; flex-direction:column; gap:8px; }}
.hsc-kanban-empty {{ font-size:13px; color:var(--hsc-ink-faint); text-align:center; padding:20px 8px;
  border:1.5px dashed var(--hsc-border); border-radius:10px; }}
.hsc-layout-section.hsc-drop-target .hsc-kanban-empty {{ border-color:{accent}; color:{accent}; background:{accent}08; }}
.hsc-layout-row {{ display:flex; align-items:center; gap:11px; background:var(--hsc-surface); border:1px solid var(--hsc-border);
  border-radius:11px; padding:10px 14px; min-height:52px; box-sizing:border-box; cursor:grab; transition:border-color .12s ease, box-shadow .12s ease; }}
.hsc-layout-row:hover {{ border-color:var(--hsc-border-strong); box-shadow:0 2px 6px rgba(16,24,40,0.08); }}
.hsc-layout-row-icon {{ width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; flex:0 0 auto; }}
.hsc-layout-row-icon svg {{ width:18px; height:18px; }}
.hsc-layout-row-label {{ font-size:14px; font-weight:600; color:var(--hsc-ink); flex:1; min-width:0;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.hsc-row-grab {{ cursor:grab; font-size:11px; letter-spacing:-1px; }}
.hsc-row-menu {{ position:relative; flex:0 0 auto; }}
.hsc-row-menu summary {{ list-style:none; cursor:pointer; color:var(--hsc-ink-muted); font-size:16px; line-height:1;
  width:28px; height:28px; border-radius:7px; display:flex; align-items:center; justify-content:center; }}
.hsc-row-menu summary::-webkit-details-marker {{ display:none; }}
.hsc-row-menu summary:hover {{ background:var(--hsc-surface-2); color:var(--hsc-ink); }}
.hsc-row-menu summary:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-row-menu-panel {{ position:absolute; right:0; top:calc(100% + 6px); z-index:6; background:var(--hsc-surface);
  border:1px solid var(--hsc-border); border-radius:10px; padding:10px; box-shadow:0 8px 24px rgba(0,0,0,0.16); }}
.hsc-row-menu[open] .hsc-row-menu-panel {{ min-width:200px; }}
.hsc-row-move-select {{ font-size:12.5px; border:1px solid var(--hsc-border); border-radius:7px; padding:7px 9px;
  background:var(--hsc-surface); color:var(--hsc-ink); width:100%; box-sizing:border-box; font-family:inherit; }}
.hsc-row-move-select:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.badge {{ }}

/* ==== Category management (V6) -- management rows, not a database table.
   Edit/delete utilities live in the ⋯ menu; the row itself just reads. */
.hsc-cat-row {{ display:flex; align-items:center; gap:14px; padding:13px 16px; border-bottom:1px solid var(--hsc-border); transition:background-color .12s ease; }}
.hsc-cat-row:hover {{ background:var(--hsc-surface-2); }}
.hsc-cat-row:last-child {{ border-bottom:none; }}
.hsc-cat-row-main {{ display:flex; flex-direction:column; gap:1px; min-width:0; flex:1; }}
.hsc-cat-row-sub {{ font-size:12px; color:var(--hsc-ink-faint); line-height:1.4; }}
.hsc-cat-grab {{ cursor:grab; font-size:11px; letter-spacing:-1px; }}
.hsc-cat-row-menu {{ position:relative; flex:0 0 auto; }}
.hsc-cat-row-menu summary {{ list-style:none; cursor:pointer; color:var(--hsc-ink-muted); font-size:16px; line-height:1;
  width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; }}
.hsc-cat-row-menu summary::-webkit-details-marker {{ display:none; }}
.hsc-cat-row-menu summary:hover {{ background:var(--hsc-surface-3); color:var(--hsc-ink); }}
.hsc-cat-row-menu summary:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
.hsc-cat-menu-panel {{ display:flex; flex-direction:column; gap:12px; min-width:240px; }}
.hsc-cat-menu-btn {{ justify-content:center; font-size:12.5px; padding:8px 12px; white-space:nowrap; }}
.hsc-cat-pop-section {{ display:flex; flex-direction:column; gap:8px; }}
.hsc-cat-pop-section + .hsc-cat-pop-section {{ border-top:1px solid var(--hsc-border); padding-top:12px; }}
.hsc-cat-pop-title {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--hsc-ink-faint); margin:0; }}
.hsc-cat-pop-form {{ display:flex; flex-direction:column; gap:8px; }}
.hsc-cat-pop-note {{ font-size:12.5px; color:var(--hsc-ink-muted); margin:0; line-height:1.55; }}
.hsc-btn-danger {{ background:#D64545; color:#FFFFFF; }}
.hsc-btn-danger:hover {{ filter:brightness(1.07); }}
.hsc-catrow-icon {{ width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; flex:0 0 auto; }}
.hsc-catrow-icon svg {{ width:19px; height:19px; }}
.hsc-cat-row-name {{ font-size:14.5px; font-weight:600; color:var(--hsc-ink); }}
.hsc-cat-row-count {{ font-size:12px; font-weight:600; color:var(--hsc-ink-muted); background:var(--hsc-surface-3);
  border-radius:10px; padding:4px 12px; flex:0 0 auto; white-space:nowrap; }}
.hsc-cat-delete-warning {{ font-size:13px; color:var(--hsc-ink); margin:0; line-height:1.55; }}
.hsc-cat-reassign-select {{ width:100%; box-sizing:border-box; border:1px solid var(--hsc-border); border-radius:8px;
  padding:8px 10px; font-size:13px; background:var(--hsc-surface); color:var(--hsc-ink); font-family:inherit; }}

/* ==== Sticky save/reset bar -- top-of-editor toolbar variant ==== */
.hsc-save-bar {{ position:sticky; bottom:0; display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;
  background:var(--hsc-surface); border:1px solid var(--hsc-border); border-radius:12px; padding:12px 16px; margin-top:14px;
  box-shadow:0 -4px 16px rgba(0,0,0,0.06); }}
.hsc-save-bar-top {{ position:sticky; top:12px; z-index:8; margin:0 0 16px; box-shadow:var(--hsc-card-hover-shadow); }}
.hsc-save-bar-status {{ font-size:12.5px; font-weight:700; color:var(--hsc-badge-soon-fg); display:flex; align-items:center; gap:7px;
  background:var(--hsc-badge-soon-bg); border-radius:20px; padding:6px 14px; }}
.hsc-save-bar-status::before {{ content:""; width:8px; height:8px; border-radius:50%; background:var(--hsc-badge-soon-fg); flex:0 0 auto; }}
.hsc-save-bar-saved {{ font-size:12.5px; font-weight:700; color:var(--hsc-badge-live-fg); display:flex; align-items:center; gap:7px;
  background:var(--hsc-badge-live-bg); border-radius:20px; padding:6px 14px; }}
.hsc-save-bar-actions {{ display:flex; gap:10px; margin-left:auto; }}
.hsc-btn-reset {{ background:var(--hsc-surface); color:var(--hsc-ink-muted); border:1.5px solid var(--hsc-border-strong); }}
.hsc-btn-reset:hover {{ color:var(--hsc-ink); }}

/* ==== Dashboard Management (V6) ==== */
.hsc-inline-form {{ display:flex; flex-direction:column; gap:14px; }}
.hsc-field-label {{ display:block; font-size:13.5px; font-weight:600; color:var(--hsc-ink); }}
.hsc-field-label .hsc-text-input, .hsc-field-label select {{ margin-top:7px; }}
.hsc-field-submit {{ margin-top:4px; }}
.hsc-text-input {{ display:block; width:100%; box-sizing:border-box; border:1px solid var(--hsc-border); border-radius:10px;
  padding:11px 13px; font-size:14px; background:var(--hsc-surface); color:var(--hsc-ink); font-family:inherit; }}
.hsc-text-input:focus-visible {{ outline:2px solid {accent}; outline-offset:1px; }}
.hsc-dash-empty {{ font-size:13.5px; color:var(--hsc-ink-muted); }}
/* Management list as a commercial table: toolbar header with search, then
   column-styled rows; per-row actions in a ⋯ menu. */
.hsc-dash-table-head {{ padding:14px 16px; border-bottom:1px solid var(--hsc-border); background:var(--hsc-surface); }}
.hsc-dash-search {{ width:100%; max-width:440px; box-sizing:border-box; border:1px solid var(--hsc-border); border-radius:10px;
  padding:10px 14px; font-size:14px; background:var(--hsc-surface); color:var(--hsc-ink); font-family:inherit; }}
.hsc-dash-search:focus-visible {{ outline:2px solid {accent}; outline-offset:1px; }}
.hsc-dashboard-list-cat {{ font-size:12.5px; font-weight:600; color:var(--hsc-ink-muted); flex:0 0 170px; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }}
.hsc-dash-menu-panel {{ display:flex; flex-direction:column; gap:10px; min-width:220px; }}
.hsc-dash-menu-panel .hsc-dashboard-list-select {{ max-width:none; }}
/* Create-dashboard workflow: compact disclosure card, not a full-screen
   form -- the management table stays the page's main content. */
.hsc-create-card[open] {{ border-color:var(--hsc-border-strong); }}
/* The disclosure panels are toggled by their header buttons only; their
   summaries would duplicate the same action on screen, so a CLOSED panel
   collapses to zero height -- nothing in the page flow until opened. */
details.hsc-create-card:not([open]) {{ height:0; min-height:0; margin:0; padding:0;
  border:none; overflow:hidden; visibility:hidden; }}
#add-category-panel[open] {{ margin-bottom:16px !important; }}
.hsc-create-summary {{ cursor:pointer; font-size:15px; font-weight:700; color:var(--hsc-ink); list-style:none; }}
.hsc-create-summary::-webkit-details-marker {{ display:none; }}
.hsc-create-summary::before {{ content:"+ "; color:{accent}; }}
.hsc-create-card[open] .hsc-create-summary::before {{ content:"\u2212 "; }}
.hsc-create-body {{ padding-top:14px; margin-top:14px; border-top:1px solid var(--hsc-border); }}
.hsc-backup-list {{ margin:8px 0 0; padding-left:20px; font-size:13.5px; color:var(--hsc-ink-muted); line-height:1.7; }}
/* Dashboard list: normal document scrolling -- no nested scroll container
   (the page itself scrolls; search handles finding, pagination can come
   later if the list ever grows). */
.hsc-dashboard-list {{ display:flex; flex-direction:column; gap:8px; }}
.hsc-dashboard-list-row {{ display:flex; align-items:center; gap:12px; padding:10px 14px; border:1px solid var(--hsc-border);
  border-radius:11px; background:var(--hsc-surface); min-height:52px; box-sizing:border-box; }}
.hsc-dashboard-list-title {{ flex:1; min-width:0; font-size:14px; font-weight:600; color:var(--hsc-ink);
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.hsc-dashboard-list-select {{ font-size:13px; border:1px solid var(--hsc-border); border-radius:8px; padding:8px 10px;
  background:var(--hsc-surface); color:var(--hsc-ink); font-family:inherit; flex:0 0 auto; max-width:190px; }}
.hsc-dashboard-list-select:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
#hsc-import-dropzone, #hsc-import-settings-dropzone {{ display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:7px; border:2px dashed var(--hsc-border); border-radius:14px; padding:30px 20px; cursor:pointer; text-align:center;
  background:var(--hsc-surface-2); transition:border-color .15s, background-color .15s; position:relative; }}
#hsc-import-dropzone:hover, #hsc-import-settings-dropzone:hover {{ border-color:{accent}; }}
#hsc-import-dropzone:focus-within, #hsc-import-settings-dropzone:focus-within {{ outline:2px solid {accent}; outline-offset:2px; }}
#hsc-import-filename, #hsc-import-settings-filename {{ font-size:13.5px; font-weight:600; color:var(--hsc-ink); }}

/* ==== Live preview (V6: sticky 330px desktop rail, real miniature) ==== */
.hsc-layout-with-preview {{ display:grid; grid-template-columns:minmax(0, 1fr); gap:22px; align-items:start; }}
.hsc-live-preview {{ background:var(--hsc-surface); border:1px solid var(--hsc-border); border-radius:var(--hsc-radius); padding:16px; }}
.hsc-live-preview-head {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:12px; }}
.hsc-live-preview-title {{ font-size:14.5px; font-weight:700; color:var(--hsc-ink); margin:0; }}
.hsc-live-preview-hint {{ font-size:12px; color:var(--hsc-ink-muted); margin:3px 0 0; }}
.hsc-live-preview-body {{ transform:scale(1); border:1px solid var(--hsc-border); border-radius:12px; padding:14px;
  background:var(--hsc-bg); max-height:560px; overflow-y:auto; }}
.hsc-live-preview-section {{ margin-bottom:14px; }}
.hsc-live-preview-section:last-child {{ margin-bottom:0; }}
.hsc-live-preview-section-title {{ font-size:12px; font-weight:700; color:var(--hsc-ink); margin:0 0 7px; display:flex; align-items:center; gap:7px; }}
.hsc-live-preview-row {{ display:flex; align-items:center; gap:7px; font-size:12px; color:var(--hsc-ink-muted);
  background:var(--hsc-surface); border:1px solid var(--hsc-border); border-radius:8px; padding:7px 10px; margin-bottom:5px; }}
.hsc-live-preview-toggle {{ display:none; }}
.hsc-live-preview-full {{ display:inline-flex; align-items:center; gap:6px; margin-top:12px; font-size:12.5px; font-weight:700;
  color:{accent}; text-decoration:none; }}
.hsc-live-preview-full:hover {{ text-decoration:underline; }}
.hsc-live-preview-full:focus-visible {{ outline:2px solid {accent}; outline-offset:2px; }}
/* Preview mini-cards: same treatment as real homepage cards (icon tile +
   status pill), colored per category via --pv-color. */
.hsc-pv-card {{ display:flex; align-items:center; gap:8px; background:var(--hsc-surface); border:1px solid var(--hsc-border);
  border-radius:9px; padding:8px 10px; margin-bottom:5px; box-shadow:var(--hsc-card-shadow); }}
.hsc-pv-tile {{ width:22px; height:22px; border-radius:6px; flex:0 0 auto; background:var(--pv-color, var(--hsc-surface-3));
  box-shadow:inset 0 0 0 1px rgba(16,24,40,0.06); }}
.hsc-pv-label {{ font-size:11.5px; font-weight:600; color:var(--hsc-ink); flex:1; min-width:0; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }}
.hsc-pv-dot {{ width:7px; height:7px; border-radius:50%; flex:0 0 auto; }}
@media (min-width: 1200px) {{
  .hsc-layout-with-preview {{ grid-template-columns:minmax(0, 1fr) 330px; }}
  .hsc-live-preview {{ position:sticky; top:24px; }}
}}
@media (max-width: 1199px) {{
  .hsc-live-preview[data-collapsed="true"] .hsc-live-preview-body {{ display:none; }}
  .hsc-live-preview-toggle {{ display:inline-flex; }}
}}
@media (max-width: 1023px) {{
  .hsc-settings-nav {{ position:static; flex-direction:row; overflow-x:auto; }}
  .hsc-nav-link {{ flex:0 0 auto; }}
  .hsc-nav-desc {{ display:none; }}
}}
@media (max-width: 767px) {{
  .hsc-view-title {{ font-size:22px; }}
  .hsc-setting-card {{ padding:18px; }}
  .hsc-cat-row {{ flex-wrap:wrap; }}
}}
</style>
</head>
<body style="margin:0;min-height:100vh;background:var(--hsc-bg);color:var(--hsc-ink);
font-family:'Noto Sans JP','Hiragino Kaku Gothic ProN','Yu Gothic','IBM Plex Sans',system-ui,sans-serif;">
<a href="#content" class="hsc-skip-link">{escape(tr("skip_to_content"))}</a>

<header class="hsc-app-header">
  <div class="hsc-app-header-inner">
    <div class="hsc-brand">
      <div class="hsc-brand-logo">{_hsc_rl_logo_svg("24px")}</div>
      <div style="min-width:0;">
        <h1 class="hsc-header-h1">{escape(tr("settings_title"))}</h1>
        <div class="hsc-brand-sub">{escape(tr("settings_subtitle"))}</div>
      </div>
    </div>
    <div class="hsc-header-controls">
      <a class="hsc-back-pill" href="/welcome/">{escape(tr("back_home"))}</a>
      <a class="hsc-logout-ghost" href="/logout/">{escape(tr("logout"))}</a>
    </div>
  </div>
</header>

<main id="content" tabindex="-1" class="hsc-page">
  <div id="hsc-announcer" class="hsc-vh" aria-live="polite" aria-atomic="true"></div>
  <!-- V6 IA: a persistent settings sidebar; clicking an item swaps the MAIN
       CONTENT VIEW (?view=) instead of scrolling one enormous page. Only
       the selected major settings area is rendered into the workspace. -->
  <div class="hsc-settings-shell">
    <nav class="hsc-settings-nav" aria-label="{escape(tr("settings_nav_label"))}">
      {nav_html}
      <p class="hsc-dirty-hint" id="hsc-dirty-hint" hidden>{escape(tr("unsaved_reminder"))}</p>
    </nav>
    <div style="min-width:0;">
    {view_body}

    <script nonce="{csp_nonce}">(function(){{
    "use strict";
    var board = document.getElementById('hsc-kanban');
    if (!board) return;
    var rowDragEl = null;
    var sectionDragEl = null;

    function getDragAfterRow(container, y){{
      var els = Array.prototype.filter.call(container.querySelectorAll('.hsc-layout-row'), function(c){{ return c !== rowDragEl; }});
      var closest = {{offset: -Infinity, element: null}};
      els.forEach(function(child){{
        var box = child.getBoundingClientRect();
        var offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {{ closest = {{offset: offset, element: child}}; }}
      }});
      return closest.element;
    }}
    function refreshMoveSelect(row){{
      var sel = row.querySelector('.hsc-row-move-select');
      var sectionId = row.closest('.hsc-layout-section').dataset.sectionId;
      if (sel) sel.value = sectionId;
    }}
    function wireRow(row){{
      row.addEventListener('dragstart', function(e){{
        rowDragEl = row;
        row.classList.add('hsc-dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', row.dataset.tileId);
      }});
      row.addEventListener('dragend', function(){{
        row.classList.remove('hsc-dragging');
        rowDragEl = null;
      }});
    }}
    board.querySelectorAll('.hsc-layout-row').forEach(wireRow);
    board.querySelectorAll('.hsc-layout-rows').forEach(function(rows){{
      rows.addEventListener('dragover', function(e){{
        e.preventDefault();
        if (!rowDragEl) return;
        var hint = rows.querySelector('.hsc-kanban-empty');
        if (hint) hint.remove();
        var after = getDragAfterRow(rows, e.clientY);
        if (after == null) {{ rows.appendChild(rowDragEl); }}
        else {{ rows.insertBefore(rowDragEl, after); }}
        refreshMoveSelect(rowDragEl);
      }});
    }});

    function getDragAfterSection(container, y){{
      var secs = Array.prototype.filter.call(container.querySelectorAll('.hsc-layout-section'), function(c){{ return c !== sectionDragEl && c.dataset.sectionId !== 'hidden'; }});
      var closest = {{offset: -Infinity, element: null}};
      secs.forEach(function(child){{
        var box = child.getBoundingClientRect();
        var offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {{ closest = {{offset: offset, element: child}}; }}
      }});
      return closest.element;
    }}
    board.querySelectorAll('.hsc-layout-section-head .hsc-grab-handle').forEach(function(handle){{
      var head = handle.closest('.hsc-layout-section-head');
      head.setAttribute('draggable', 'true');
      head.addEventListener('dragstart', function(e){{
        sectionDragEl = head.closest('.hsc-layout-section');
        sectionDragEl.classList.add('hsc-dragging');
        e.dataTransfer.effectAllowed = 'move';
      }});
      head.addEventListener('dragend', function(){{
        if (sectionDragEl) sectionDragEl.classList.remove('hsc-dragging');
        sectionDragEl = null;
      }});
    }});
    board.addEventListener('dragover', function(e){{
      if (!sectionDragEl) return;
      e.preventDefault();
      var after = getDragAfterSection(board, e.clientY);
      if (after == null) {{
        var hiddenSec = board.querySelector('.hsc-layout-section[data-section-id="hidden"]');
        board.insertBefore(sectionDragEl, hiddenSec || null);
      }}
      else {{ board.insertBefore(sectionDragEl, after); }}
    }});

    board.addEventListener('click', function(e){{
      var toggle = e.target.closest('.hsc-section-collapse');
      if (!toggle) return;
      var rows = toggle.closest('.hsc-layout-section').querySelector('.hsc-layout-rows');
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      rows.hidden = expanded;
      toggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      toggle.setAttribute('aria-label', expanded ? toggle.dataset.expandLabel : toggle.dataset.collapseLabel);
    }});

    board.addEventListener('change', function(e){{
      var sel = e.target.closest('.hsc-row-move-select');
      if (!sel) return;
      var row = sel.closest('.hsc-layout-row');
      var targetSection = board.querySelector('.hsc-layout-section[data-section-id="' + sel.value + '"] .hsc-layout-rows');
      if (!targetSection) return;
      var hint = targetSection.querySelector('.hsc-kanban-empty');
      if (hint) hint.remove();
      targetSection.appendChild(row);
      row.querySelector('.hsc-grab-handle').focus();
      document.dispatchEvent(new Event('hsc:rowmoved'));
    }});

    document.getElementById('hsc-sections-form').addEventListener('submit', function(){{
      var sections = [];
      var hiddenIds = [];
      document.querySelectorAll('.hsc-layout-section').forEach(function(sec){{
        var rows = sec.querySelector('.hsc-layout-rows');
        var ids = Array.prototype.map.call(rows.querySelectorAll('.hsc-layout-row'), function(c){{ return c.dataset.tileId; }});
        if (sec.dataset.sectionId === 'hidden') {{ hiddenIds = ids; }}
        else {{
          var nameInput = sec.querySelector('.hsc-section-name');
          sections.push({{name: nameInput ? nameInput.value : sec.dataset.sectionId, tiles: ids}});
        }}
      }});
      document.getElementById('hsc-sections-json').value = JSON.stringify({{sections: sections, hidden: hiddenIds}});
    }});
    var resetBtn = document.getElementById('hsc-sections-reset');
    if (resetBtn) {{
      resetBtn.addEventListener('click', function(){{
        if (typeof window.HSC_IS_DIRTY_SECTIONS === 'function' && window.HSC_IS_DIRTY_SECTIONS()) {{
          if (!window.confirm({json.dumps(tr("reset_confirm"))})) return;
        }}
        window.location.reload();
      }});
    }}
  }})();</script>

  <script nonce="{csp_nonce}">(function(){{
    "use strict";
    // Layout save: after the POST round-trip (?saved=sections), show a
    // restrained green confirmation in the sticky toolbar for a few seconds.
    var savedChip = document.getElementById('hsc-sections-saved');
    if (savedChip) {{
      var statusEl = document.getElementById('hsc-status-sections');
      if (statusEl && statusEl.textContent.indexOf('\u2713') !== -1) {{
        savedChip.hidden = false;
        setTimeout(function() {{ savedChip.hidden = true; }}, 4000);
      }}
    }}
    // Dashboard-management list: live text filter over the rows.
    var dashSearch = document.getElementById('hsc-dash-search');
    if (dashSearch) {{
      dashSearch.addEventListener('input', function() {{
        var q = dashSearch.value.trim().toLowerCase();
        document.querySelectorAll('.hsc-dashboard-list-row').forEach(function(row) {{
          row.hidden = !!q && (row.getAttribute('data-dash-label') || '').toLowerCase().indexOf(q) === -1;
        }});
      }});
    }}
  }})();</script>

  <script nonce="{csp_nonce}">(function(){{
    "use strict";
    var catForm = document.getElementById('hsc-categories-form');
    if (!catForm) return;
    var catDragEl = null;
    function getAfterCat(container, y){{
      var els = Array.prototype.filter.call(container.querySelectorAll('.hsc-cat-row'), function(c){{ return c !== catDragEl; }});
      var closest = {{offset: -Infinity, element: null}};
      els.forEach(function(child){{
        var box = child.getBoundingClientRect();
        var offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {{ closest = {{offset: offset, element: child}}; }}
      }});
      return closest.element;
    }}
    catForm.addEventListener('dragstart', function(e){{
      var row = e.target.closest && e.target.closest('.hsc-cat-row');
      if (!row) return;
      catDragEl = row;
      row.classList.add('hsc-dragging');
      e.dataTransfer.effectAllowed = 'move';
    }});
    catForm.addEventListener('dragover', function(e){{
      if (!catDragEl) return;
      e.preventDefault();
      var after = getAfterCat(catForm, e.clientY);
      var rowsHost = document.getElementById('hsc-category-table') || catForm;
      if (after == null) {{
        var bar = rowsHost.querySelector('.hsc-save-bar');
        if (bar) {{ rowsHost.insertBefore(catDragEl, bar); }}
        else {{ rowsHost.appendChild(catDragEl); }}
      }}
      else {{ rowsHost.insertBefore(catDragEl, after); }}
    }});
    catForm.addEventListener('drop', function(e){{ e.preventDefault(); }});
    catForm.addEventListener('dragend', function(){{
      if (catDragEl) catDragEl.classList.remove('hsc-dragging');
      catDragEl = null;
    }});
  }})();</script>

  <script nonce="{csp_nonce}">(function(){{
    "use strict";
    var resetBtn = document.getElementById('hsc-categories-reset');
    if (resetBtn) {{
      resetBtn.addEventListener('click', function(){{
        if (typeof window.HSC_IS_DIRTY_CATEGORIES === 'function' && window.HSC_IS_DIRTY_CATEGORIES()) {{
          if (!window.confirm({json.dumps(tr("reset_confirm"))})) return;
        }}
        window.location.reload();
      }});
    }}
  }})();</script>
  <script nonce="{csp_nonce}">{kanban_a11y_script}</script>
    </div><!-- /settings content column -->
  </div>
</main>
<script nonce="{csp_nonce}">(function(){{
  document.querySelectorAll('.hsc-dashboard-list-select').forEach(function(sel){{
    sel.addEventListener('change', function(){{ sel.form.submit(); }});
  }});
  var importForm = document.getElementById('hsc-import-settings-form');
  if (importForm) {{
    importForm.addEventListener('submit', function(e){{
      if (!window.confirm({json.dumps(tr("import_settings_confirm"))})) e.preventDefault();
    }});
  }}
}})();</script>
<script nonce="{csp_nonce}">(function(){{
  function wireDropzone(fileInputId, zoneId, labelId) {{
    var input = document.getElementById(fileInputId);
    var zone = document.getElementById(zoneId);
    var label = document.getElementById(labelId);
    if (!input || !zone || !label) return;
    var placeholder = label.textContent;
    function showFile(){{
      if (input.files && input.files.length) {{ label.textContent = input.files[0].name; }}
      else {{ label.textContent = placeholder; }}
    }}
    input.addEventListener('change', showFile);
    zone.addEventListener('dragover', function(e){{ e.preventDefault(); zone.style.borderColor = '{accent}'; }});
    zone.addEventListener('dragleave', function(){{ zone.style.borderColor = ''; }});
    zone.addEventListener('drop', function(e){{
      e.preventDefault();
      zone.style.borderColor = '';
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {{
        input.files = e.dataTransfer.files;
        showFile();
      }}
    }});
  }}
  wireDropzone('hsc-import-file', 'hsc-import-dropzone', 'hsc-import-filename');
  wireDropzone('hsc-import-settings-file', 'hsc-import-settings-dropzone', 'hsc-import-settings-filename');
}})();</script>
<script nonce="{csp_nonce}">{hsc_settings_extras_script}</script>
<script nonce="{csp_nonce}">(function(){{
  // After a POST round-trip, move keyboard focus onto the visible status
  // chip (runs on `load` so the browser's own #anchor processing doesn't
  // reset focus first).
  function focusStatus() {{
    var statusEl = document.querySelector('.hsc-form-status');
    if (statusEl) statusEl.focus({{preventScroll: false}});
  }}
  if (document.readyState === 'complete') focusStatus();
  else window.addEventListener('load', focusStatus);
}})();</script>
<script nonce="{csp_nonce}">(function(){{
  // Disclosure buttons (CSP forbids inline event handlers whenever a
  // script-src nonce is present -- see the language-select script for the
  // same pattern): header buttons open the matching <details>, the
  // create-dashboard Cancel closes it. Each falls back to toggling.
  function wireDisclosure(btnId, panelId, focusSel, close) {{
    var btn = document.getElementById(btnId);
    var panel = document.getElementById(panelId);
    if (!btn || !panel) return;
    btn.addEventListener('click', function() {{
      panel.open = !!close ? false : true;
      var target = focusSel ? panel.querySelector(focusSel) : null;
      if (target && panel.open) target.focus();
    }});
  }}
  wireDisclosure('hsc-add-category-btn', 'add-category-panel', '#hsc-new-category-ja');
  wireDisclosure('hsc-create-dash-btn', 'add-dashboard', '#hsc-new-dashboard-title');
  wireDisclosure('hsc-import-dash-btn', 'dashboard-import', '#hsc-import-file');
  wireDisclosure('hsc-cancel-create-dash', 'add-dashboard', null, true);
  // While any native drag is active, suppress accidental text selection
  // (mousedown+move on the grab handles used to select neighbouring text).
  document.addEventListener('dragstart', function() {{ document.body.classList.add('hsc-drag-active'); }}, true);
  document.addEventListener('dragend', function() {{ document.body.classList.remove('hsc-drag-active'); }}, true);
}})();</script>
<script nonce="{csp_nonce}">(function(){{
  // Unsaved-changes chip in the sidebar (reuses the snapshot diff from
  // _HSC_SETTINGS_EXTRAS_JS; only shown on forms present on THIS view).
  var dirtyChip = document.getElementById('hsc-dirty-hint');
  if (dirtyChip && typeof window.HSC_IS_DIRTY === 'function') {{
    var dirtyTick = false;
    function checkDirty() {{
      dirtyTick = false;
      try {{ dirtyChip.hidden = !window.HSC_IS_DIRTY(); }} catch (e) {{}}
    }}
    function scheduleCheckDirty() {{
      if (dirtyTick) return;
      dirtyTick = true;
      setTimeout(checkDirty, 0);
    }}
    document.addEventListener('input', scheduleCheckDirty);
    document.addEventListener('change', scheduleCheckDirty);
    document.addEventListener('hsc:rowmoved', scheduleCheckDirty);
    document.addEventListener('dragend', function() {{ setTimeout(checkDirty, 0); }});
    checkDirty();
  }}
}})();</script>
</body></html>"""


def _hsc_flask_app_mutator(app):
    from flask import Response, redirect, request
    from flask_login import current_user

    @app.before_request
    def _hsc_render_home():
        if request.path != "/welcome/":
            return None
        if not getattr(current_user, "is_authenticated", False):
            return None
        settings = _hsc_get_settings(current_user.email)
        display_name = current_user.first_name or current_user.username
        can_create = _hsc_can_create_dashboard(current_user)
        return Response(_hsc_render_menu_page(display_name, settings, can_create), mimetype="text/html")

    def _hsc_menu_settings_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")

        if request.method == "POST":
            # Merge into the existing blob rather than replacing it wholesale
            # -- `sections`/`hidden` (the kanban board, /hsc/save-sections)
            # live in this same per-user JSON but are saved through a
            # separate form, so a plain accent/color save must not clobber
            # them.
            existing = _hsc_get_settings(current_user.email)
            existing["accent"] = _hsc_valid_hex_color(
                request.form.get("preset_accent") or request.form.get("accent"), _HSC_DEFAULT_ACCENT
            )
            # Appearance (§5at): each is its own instant-apply segmented
            # button (same pattern as the accent swatches above), so a
            # request touching one of these fields might not touch the
            # other -- fall back to whatever's already saved, not a fixed
            # default, so clicking "Dark" doesn't silently reset density
            # back to Comfortable.
            theme_mode = request.form.get("theme_mode")
            if theme_mode in ("light", "dark", "system"):
                existing["theme_mode"] = theme_mode
            density = request.form.get("density")
            if density in ("comfortable", "compact"):
                existing["density"] = density
            _hsc_save_settings(current_user.email, existing)
            settings_for_form = existing
            saved = True
            # A self-posted appearance save can't also carry a category
            # error (that only arrives via ?cat_error= on a GET) -- define
            # it here so the template call below always has both names
            # bound regardless of which branch ran.
            category_error = None
        else:
            settings_for_form = _hsc_get_settings(current_user.email)
            # Per-form status flags come back as query params from each of
            # the page's four POST targets (§5aw save feedback): the accent
            # form self-posts here, while save-sections/save-categories/
            # create-category redirect back with `saved=<form>` or
            # `error=<code>`. Rendering one status per form (instead of one
            # page-wide banner) is what keeps the confirmation next to the
            # button that was actually clicked -- the audit (§5av's
            # predecessor) measured the old single banner ~471px above the
            # viewport when saving a bottom form.
            #
            # Backward compat: pre-§5aw redirects carried `saved=1` (the old
            # page-wide banner flag). Old URLs may still be open in tabs or
            # history; map them to the appearance form, the only form that
            # ever self-posted to this endpoint.
            saved = request.args.get("saved") or ""
            if saved == "1":
                saved = "appearance"
            category_error = request.args.get("cat_error")

        import_settings_result = request.args.get("import_result")

        # V6 IA: the sidebar's ?view= parameter selects which major settings
        # area fills the workspace (true section switching, not scrolling).
        # POST round-trips redirect back with their own ?saved=...#anchor,
        # so map any #anchor-era URLs to their matching view; ?view= wins.
        view = request.args.get("view") or ""
        if view not in ("appearance", "homepage-layout", "categories", "dashboards", "import-export"):
            anchor = request.args.get("anchor") or ""
            view = {
                "homepage-layout": "homepage-layout",
                "category-layout": "categories",
                "dashboard-management": "dashboards",
                "import-export": "import-export",
            }.get(anchor, "appearance")

        from flask_wtf.csrf import generate_csrf

        html = _hsc_render_settings_page(
            settings_for_form,
            generate_csrf(),
            saved=saved,
            category_error=category_error,
            import_settings_result=import_settings_result,
            view=view,
        )
        return Response(html, mimetype="text/html")

    def _hsc_save_sections_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        import json

        all_tiles = _hsc_all_tiles()
        dash_to_placeholder_id = _hsc_get_dashboard_to_placeholder_id()
        valid_ids = set()
        for t in all_tiles:
            valid_ids |= _hsc_tile_alias_ids(t, dash_to_placeholder_id)

        try:
            payload = json.loads(request.form.get("sections_json") or "{}")
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}

        sections = []
        for src in (payload.get("sections") or [])[:_HSC_SECTION_COUNT]:
            if not isinstance(src, dict):
                continue
            name = str(src.get("name") or "").strip()[:60]
            tiles = [tid for tid in (src.get("tiles") or []) if isinstance(tid, str) and tid in valid_ids]
            sections.append({"name": name, "tiles": tiles})
        hidden = [tid for tid in (payload.get("hidden") or []) if isinstance(tid, str) and tid in valid_ids]

        # Same merge-not-replace rule as the accent/color form above: this
        # is a different <form> (and a different POST) touching a different
        # slice of the same per-user settings blob.
        existing = _hsc_get_settings(current_user.email)
        existing["sections"] = sections
        existing["hidden"] = hidden
        existing.pop("order", None)  # superseded by each section's own tile order
        _hsc_save_settings(current_user.email, existing)

        # §5aw: `saved=sections` (not the legacy `saved=1`) names WHICH form
        # succeeded, so its own inline status renders next to that form's
        # Save button instead of a page-top banner nobody sees from down
        # here.
        return redirect("/hsc/menu-settings?view=homepage-layout&saved=sections")

    def _hsc_save_categories_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        import json

        valid_group_ids = set(_hsc_all_group_ids())

        # Category colors -- moved here from the plain accent/color form
        # (§5aq): a shared, org-wide setting (like the category names
        # themselves), same as it always was, just saved through this
        # board's own POST now that the color picker lives on each column.
        for gid in valid_group_ids:
            raw_color = request.form.get(f"category_color_{gid}")
            valid_color = _hsc_valid_hex_color(raw_color, None)
            if valid_color:
                _hsc_save_category_color(gid, valid_color)

        try:
            payload = json.loads(request.form.get("categories_json") or "{}")
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}

        # Order: every category gets an explicit position, including ones
        # missing from the payload (a malformed/stale request), appended in
        # their current order rather than silently dropped from the list.
        # V6 redesign: the category table has no drag surface any more --
        # reordering is a plain `move_up`/`move_down` submit button (see
        # render_category_row), which swaps two adjacent positions in the
        # CURRENT saved order directly, rather than the client recomputing
        # and posting a whole new order via JS. `categories_json.order` is
        # still accepted as a base/fallback (e.g. a future bulk-reorder UI),
        # applied before any move_up/move_down swap.
        order = [gid for gid in (payload.get("order") or []) if isinstance(gid, str) and gid in valid_group_ids]
        for gid in _hsc_all_group_ids():
            if gid not in order:
                order.append(gid)

        move_up = request.form.get("move_up")
        move_down = request.form.get("move_down")
        target, direction = (move_up, -1) if move_up else (move_down, 1) if move_down else (None, 0)
        if target in valid_group_ids:
            idx = order.index(target)
            swap_idx = idx + direction
            if 0 <= swap_idx < len(order):
                order[idx], order[swap_idx] = order[swap_idx], order[idx]

        _hsc_save_category_order(order)

        # Moving a DASHBOARD to a different category is no longer done from
        # this board (it had no drag surface to do it with) -- that action
        # now lives in Dashboard Management's per-dashboard "Category"
        # <select> (see _hsc_recategorize_dashboard_view), which is the only
        # thing that calls _hsc_recategorize_dashboard now.

        return redirect("/hsc/menu-settings?view=categories&saved=categories")

    def _hsc_set_lang_view():
        # Own thin wrapper around flask_appbuilder's own /lang/<locale>
        # route (same session key, same flask_babel.refresh() call) rather
        # than linking straight to that route: its own redirect-back logic
        # depends on a page_history session stack that only FAB's own
        # BaseView-based pages ever push to, so it wouldn't reliably return
        # to a plain Flask route like /welcome/. See docs/00-runbook.md §6.5.
        from flask import current_app, session
        from flask_babel import refresh

        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/welcome/")
        lang = request.args.get("lang")
        if lang in current_app.config.get("LANGUAGES", {}):
            session["locale"] = lang
            refresh()
        return redirect("/welcome/")

    def _hsc_create_dashboard_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/welcome/")

        tile_id = request.args.get("tile")
        tile = next((t for t in _HSC_PLACEHOLDER_TILES if t["id"] == tile_id), None)
        if not tile or tile["status"] != "soon":
            return redirect("/welcome/")

        existing_id = _hsc_get_placeholder_link(tile_id)
        if existing_id:
            return redirect(f"/superset/dashboard/{existing_id}/?edit=true")

        try:
            new_id = _hsc_create_dashboard_for_tile(tile, current_user.id)
            _hsc_save_placeholder_link(tile_id, new_id, current_user.email)
        except Exception:
            # Creation failing (e.g. the admin API session couldn't reach
            # Superset) should land the person back on a working homepage,
            # not a 500 -- the tile just stays "coming soon" for next time.
            return redirect("/welcome/")

        return redirect(f"/superset/dashboard/{new_id}/?edit=true")

    def _hsc_create_custom_dashboard_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        title = (request.form.get("new_title") or "").strip()
        group = request.form.get("new_group")
        if not title or group not in _hsc_all_group_ids():
            return redirect("/hsc/menu-settings")

        try:
            new_id = _hsc_create_tagged_dashboard(title, group)
        except Exception:
            return redirect("/hsc/menu-settings")

        return redirect(f"/superset/dashboard/{new_id}/?edit=true")

    def _hsc_create_category_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        label_ja = (request.form.get("category_label_ja") or "").strip()
        label_en = (request.form.get("category_label_en") or "").strip() or None
        # §5aw-fix (red-team): the input had no length bound -- a 300-char
        # name was accepted and stored (rendering survives via ellipsis, but
        # it pollutes the category dropdown and can't be matched against the
        # 60-char section-name convention). Cap at the same 60 the section
        # kanban name inputs already enforce.
        if label_ja:
            label_ja = label_ja[:60]
            if label_en:
                label_en = label_en[:60]
            # §5av-fix (audit F01): this used to swallow every failure with
            # `except Exception: pass`, and never checked for an existing
            # category with the same name -- so submitting 監査 twice
            # silently created two org-wide categories (confirmed twice,
            # persisted across reload) that only direct DB access could
            # remove, since nothing on this page deletes a category. Now:
            # normalized (trim + casefold) comparison against every existing
            # label before INSERT, and a visible, localized error carried
            # back through the redirect. The original exception-swallowing
            # is gone: a genuine DB failure now surfaces as its own error
            # banner rather than a silent no-op.
            normalized = label_ja.casefold()
            existing_labels = {label.casefold() for label in _hsc_all_category_labels()}
            if normalized in existing_labels:
                from urllib.parse import quote

                return redirect(f"/hsc/menu-settings?view=categories&cat_error={quote(label_ja)}")
            try:
                result = _hsc_save_category(label_ja, label_en)
            except Exception:
                from urllib.parse import quote

                return redirect(f"/hsc/menu-settings?view=categories&cat_error={quote('!db')}")
            if result == "__duplicate__":
                # Lost the unique-index race (a concurrent request inserted
                # the same name between our check and our INSERT). Same
                # user-visible outcome as the pre-check above.
                from urllib.parse import quote

                return redirect(f"/hsc/menu-settings?view=categories&cat_error={quote(label_ja)}")
        return redirect("/hsc/menu-settings?view=categories&saved=category")

    def _hsc_import_dashboard_view():
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        upload = request.files.get("import_file")
        if not upload or not upload.filename:
            return redirect("/hsc/menu-settings?view=dashboards")

        try:
            _hsc_import_dashboard_bundle(upload)
        except Exception:
            # Import can fail for reasons only Superset's own UI explains well
            # (password-protected database configs in the bundle, a version
            # mismatch, a bad zip) -- send them to the native import dialog
            # rather than swallowing the real error message.
            return redirect("/dashboard/list/")

        return redirect("/dashboard/list/")

    def _hsc_rename_category_view():
        # V6 Category Management: rename, custom categories only -- a
        # built-in's label is a gettext msgid (_HSC_MSGIDS's group_pl etc.),
        # not a DB row, so there is nothing here to UPDATE for one; the
        # settings page never renders a rename form for a built-in in the
        # first place (see render_category_row), but this is re-checked
        # server-side since forms are never trusted on their own.
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        from flask_babel import get_locale

        key = request.form.get("key") or ""
        new_label = (request.form.get("label") or "").strip()[:60]
        if not key.startswith("cat_") or key not in set(_hsc_all_group_ids()) or not new_label:
            return redirect("/hsc/menu-settings?view=categories")

        # Same locale convention as _hsc_category_display_label: an English
        # viewer renaming the label they SEE (label_en, when the category
        # has one) edits that column; everyone else edits the primary/
        # Japanese `label` column. A category with no label_en yet always
        # edits `label`, even for an English viewer, since there is no
        # English text on screen to be renaming.
        custom = {c["id"]: c for c in _hsc_get_custom_categories()}
        cat = custom.get(key)
        if not cat:
            return redirect("/hsc/menu-settings?view=categories")
        field = "label_en" if (str(get_locale()) == "en" and cat.get("label_en")) else "label"

        normalized = new_label.casefold()
        other_labels = {lbl.casefold() for lbl in _hsc_all_category_labels() if lbl.casefold() != cat[("label_en" if field == "label_en" else "label")].casefold()}
        if normalized in other_labels:
            from urllib.parse import quote

            return redirect(f"/hsc/menu-settings?view=categories&cat_error={quote(new_label)}")

        try:
            result = _hsc_rename_category(key, field, new_label)
        except Exception:
            return redirect("/hsc/menu-settings?view=categories")
        if result == "__duplicate__":
            from urllib.parse import quote

            return redirect(f"/hsc/menu-settings?view=categories&cat_error={quote(new_label)}")

        return redirect("/hsc/menu-settings?view=categories&saved=categories")

    def _hsc_delete_category_view():
        # V6 Category Management: delete, custom categories only. Any
        # dashboard still tagged with this category must be moved to the
        # chosen `reassign_to` category FIRST (a real, visible re-tag, same
        # helper the old kanban board's drag-to-recategorize used) -- never
        # silently orphaning a dashboard's tag.
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        key = request.form.get("key") or ""
        valid_group_ids = set(_hsc_all_group_ids())
        if not key.startswith("cat_") or key not in valid_group_ids:
            return redirect("/hsc/menu-settings?view=categories")

        all_tiles = _hsc_all_tiles()
        tiles_in_category = [t for t in all_tiles if t["group"] == key and t["status"] == "live" and t["id"].startswith("dash:")]
        if tiles_in_category:
            reassign_to = request.form.get("reassign_to")
            if reassign_to not in valid_group_ids or reassign_to == key:
                return redirect("/hsc/menu-settings?view=categories")
            for tile in tiles_in_category:
                try:
                    _hsc_recategorize_dashboard(int(tile["id"].split(":", 1)[1]), key, reassign_to)
                except Exception:
                    pass

        _hsc_delete_category(key)
        return redirect("/hsc/menu-settings?view=categories&saved=categories")

    def _hsc_recategorize_dashboard_view():
        # Dashboard Management's per-dashboard "Category" <select> (replaces
        # the old category kanban board's drag-a-card-to-a-different-column
        # gesture with a plain, keyboard-native control -- same underlying
        # re-tag, same helper).
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        valid_group_ids = set(_hsc_all_group_ids())
        dash_id = request.form.get("dash_id") or ""
        old_group = request.form.get("old_group")
        new_group = request.form.get("new_group")
        if (
            dash_id.isdigit()
            and old_group in valid_group_ids
            and new_group in valid_group_ids
            and old_group != new_group
        ):
            try:
                _hsc_recategorize_dashboard(int(dash_id), old_group, new_group)
            except Exception:
                pass
        return redirect("/hsc/menu-settings?view=dashboards")

    def _hsc_export_settings_view():
        # Import/Export: a portable snapshot of everything this screen lets
        # someone configure -- their OWN personal settings (accent/theme/
        # density/homepage layout/hidden tiles) plus the SHARED, org-wide
        # category list (custom categories, display order, colors). Real
        # dashboards themselves are out of scope (that's Superset's own
        # export, reachable from Dashboard Management's existing "Import a
        # dashboard bundle" control) -- this is menu/layout configuration
        # only, matching what the settings screen actually edits.
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")

        import json as json_mod
        from datetime import datetime, timezone

        payload = {
            "hsc_config_version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "personal_settings": _hsc_get_settings(current_user.email),
            "categories": {
                "custom": _hsc_get_custom_categories(),
                "order": _hsc_get_category_order(),
                "colors": _hsc_get_category_colors(),
            },
        }
        body = json_mod.dumps(payload, indent=2, ensure_ascii=False)
        resp = Response(body, mimetype="application/json")
        resp.headers["Content-Disposition"] = 'attachment; filename="hsc-menu-config.json"'
        return resp

    def _hsc_import_settings_view():
        # Import/Export: the inverse of _hsc_export_settings_view. Every
        # field is validated/coerced rather than trusted, same discipline as
        # /hsc/save-sections and /hsc/save-categories already apply to their
        # own client-submitted JSON -- an uploaded file is just as untrusted
        # as a hand-crafted POST body. A malformed file redirects back with
        # `import_result=invalid` (§5aw-style per-section status) instead of
        # a 500 or a silently-partial import.
        if not getattr(current_user, "is_authenticated", False):
            return redirect("/login/?next=/hsc/menu-settings")
        if request.method != "POST":
            return redirect("/hsc/menu-settings")

        import json as json_mod

        upload = request.files.get("config_file")
        if not upload or not upload.filename:
            return redirect("/hsc/menu-settings?view=import-export&import_result=invalid")

        try:
            data = json_mod.loads(upload.read().decode("utf-8"))
        except Exception:
            return redirect("/hsc/menu-settings?view=import-export&import_result=invalid")
        if not isinstance(data, dict) or not isinstance(data.get("personal_settings"), dict):
            return redirect("/hsc/menu-settings?view=import-export&import_result=invalid")

        raw_settings = data["personal_settings"]
        clean_settings = {
            "accent": _hsc_valid_hex_color(raw_settings.get("accent"), _HSC_DEFAULT_ACCENT),
            "theme_mode": raw_settings.get("theme_mode") if raw_settings.get("theme_mode") in ("light", "dark", "system") else "system",
            "density": raw_settings.get("density") if raw_settings.get("density") in ("comfortable", "compact") else "comfortable",
        }
        raw_sections = raw_settings.get("sections")
        if isinstance(raw_sections, list):
            sections = []
            for src in raw_sections[:_HSC_SECTION_COUNT]:
                if not isinstance(src, dict):
                    continue
                name = str(src.get("name") or "").strip()[:60]
                tiles = [tid for tid in (src.get("tiles") or []) if isinstance(tid, str)][:200]
                sections.append({"name": name, "tiles": tiles})
            clean_settings["sections"] = sections
        clean_settings["hidden"] = [tid for tid in (raw_settings.get("hidden") or []) if isinstance(tid, str)][:500]
        _hsc_save_settings(current_user.email, clean_settings)

        categories_data = data.get("categories") if isinstance(data.get("categories"), dict) else {}
        existing_labels = {lbl.casefold() for lbl in _hsc_all_category_labels()}
        for entry in (categories_data.get("custom") or [])[:100]:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label") or "").strip()[:60]
            label_en = (str(entry.get("label_en")).strip()[:60] or None) if entry.get("label_en") else None
            if not label or label.casefold() in existing_labels:
                continue
            try:
                _hsc_save_category(label, label_en)
                existing_labels.add(label.casefold())
            except Exception:
                pass

        valid_group_ids = set(_hsc_all_group_ids())
        raw_order = categories_data.get("order") if isinstance(categories_data.get("order"), dict) else {}
        if raw_order:
            ordered = sorted(
                (gid for gid in valid_group_ids if gid in raw_order),
                key=lambda gid: raw_order[gid],
            )
            ordered += [gid for gid in _hsc_all_group_ids() if gid not in ordered]
            _hsc_save_category_order(ordered)

        raw_colors = categories_data.get("colors") if isinstance(categories_data.get("colors"), dict) else {}
        for gid, color in raw_colors.items():
            if gid in valid_group_ids:
                valid_color = _hsc_valid_hex_color(color, None)
                if valid_color:
                    _hsc_save_category_color(gid, valid_color)

        return redirect("/hsc/menu-settings?view=import-export&import_result=ok")

    app.add_url_rule(
        "/hsc/menu-settings",
        "hsc_menu_settings",
        _hsc_menu_settings_view,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/hsc/save-sections",
        "hsc_save_sections",
        _hsc_save_sections_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/save-categories",
        "hsc_save_categories",
        _hsc_save_categories_view,
        methods=["POST"],
    )
    app.add_url_rule("/hsc/set-lang", "hsc_set_lang", _hsc_set_lang_view, methods=["GET"])
    app.add_url_rule(
        "/hsc/create-dashboard",
        "hsc_create_dashboard",
        _hsc_create_dashboard_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/hsc/create-dashboard-custom",
        "hsc_create_dashboard_custom",
        _hsc_create_custom_dashboard_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/create-category",
        "hsc_create_category",
        _hsc_create_category_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/import-dashboard",
        "hsc_import_dashboard",
        _hsc_import_dashboard_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/rename-category",
        "hsc_rename_category",
        _hsc_rename_category_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/delete-category",
        "hsc_delete_category",
        _hsc_delete_category_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/recategorize-dashboard",
        "hsc_recategorize_dashboard",
        _hsc_recategorize_dashboard_view,
        methods=["POST"],
    )
    app.add_url_rule(
        "/hsc/export-settings",
        "hsc_export_settings",
        _hsc_export_settings_view,
        methods=["GET"],
    )
    app.add_url_rule(
        "/hsc/import-settings",
        "hsc_import_settings",
        _hsc_import_settings_view,
        methods=["POST"],
    )

    def _hsc_combined_logo_view():
        # Deliberately no auth check -- this is APP_ICON's target (§1c),
        # rendered on the login page before anyone is signed in.
        resp = Response(_hsc_combined_brand_logo_svg(), mimetype="image/svg+xml")
        resp.cache_control.public = True
        resp.cache_control.max_age = 3600
        return resp

    app.add_url_rule(
        "/hsc/assets/logo-combined.svg",
        "hsc_combined_logo",
        _hsc_combined_logo_view,
        methods=["GET"],
    )

    return None


FLASK_APP_MUTATOR = _hsc_flask_app_mutator


#
# Optionally import superset_config_docker.py (which will have been included on

# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa: F403

    logger.info(
        "Loaded your Docker configuration at [%s]", superset_config_docker.__file__
    )
except ImportError:
    logger.info("Using default Docker config...")
