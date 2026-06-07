import base64
import copy
import html
import json
import mimetypes
import os
import re
import time
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    def st_autorefresh(*args, **kwargs):
        return None


st.set_page_config(
    page_title="World Cup FC",
    page_icon="titlethumb.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
html, body, [data-testid="stAppViewContainer"], .stApp { background:#000!important; color:#fff!important; }
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] { background:#000!important; }
.stMarkdown, .stCaption, label, p, h1, h2, h3, h4, h5, h6 { color:#fff; }
button { border-radius:8px!important; }
div[data-testid="stButton"] > button {
    background:#121212!important; color:#fff!important; border:1px solid #444!important;
    min-height:46px!important; font-weight:900!important; white-space:normal!important; line-height:1.2!important;
}
div[data-testid="stButton"] > button:hover { border-color:#00e5ff!important; background:#181818!important; color:#fff!important; }
div[data-testid="stButton"] > button:disabled {
    background:#202020!important; color:#7e7e7e!important; border-color:#333!important; opacity:1!important;
}
div[data-testid="stExpander"] { background:#050505!important; border:1px solid #2e2e2e!important; border-radius:8px!important; }
div[data-testid="stExpander"] details > summary,
div[data-testid="stExpander"] details[open] > summary,
div[data-testid="stExpander"] summary:hover,
div[data-testid="stExpander"] summary:focus,
div[data-testid="stExpander"] summary:active {
    background:#050505!important; color:#ffd54a!important; border-radius:8px!important;
}
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span { color:#ffd54a!important; font-weight:1000!important; }
div[data-testid="stExpander"] summary svg {
    color:#ffd54a!important; fill:#ffd54a!important; stroke:#ffd54a!important;
}
input, textarea, select { color:#fff!important; }
.top-thumbnail-wrap { width:100%; display:flex; justify-content:center; margin:.2rem 0 .75rem; }
.top-thumbnail { width:100%; max-width:1080px; max-height:320px; object-fit:contain; border-radius:8px; display:block; }
.hero-title { display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:12px; margin:.25rem 0 1rem; }
.hero-title h1 { margin:0; padding:0; font-size:clamp(1.75rem, 6.4vw, 3.35rem); line-height:.98; font-weight:1000; color:#ffd54a; }
.hero-kicker { color:#00e5ff; text-transform:uppercase; font-size:.82rem; letter-spacing:.12em; font-weight:1000; }
.deadline-pill { border:2px solid #ffd54a; color:#ffd54a; border-radius:8px; padding:8px 10px; font-weight:950; background:#090909; }
.section-title { color:#ffd54a; font-weight:1000; font-size:1.35rem; margin:1.2rem 0 .55rem; }
.subtle { color:#b9c2c9; font-size:.9rem; }
.rules-box { border-left:5px solid #00e5ff; border-radius:8px; background:#070707; padding:12px 14px; margin:.8rem 0 1rem; color:#dceff5; }
.standings-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px; }
.coach-card { border:3px solid var(--coach-color); border-radius:8px; padding:12px; background:#070707; box-shadow:0 0 18px var(--coach-color), inset 0 0 22px rgba(255,255,255,.055), inset 0 0 30px color-mix(in srgb, var(--coach-color) 18%, transparent); min-height:280px; }
.coach-head { display:flex; align-items:center; gap:12px; min-width:0; }
.coach-face { width:74px; height:74px; border-radius:50%; object-fit:cover; border:4px solid var(--coach-color); box-shadow:0 0 14px var(--coach-color); flex:0 0 auto; }
.coach-face-placeholder { width:74px; height:74px; border-radius:50%; border:4px solid var(--coach-color); color:var(--coach-color); display:flex; align-items:center; justify-content:center; text-align:center; font-weight:1000; font-size:.78rem; line-height:1; flex:0 0 auto; }
.coach-name { font-size:1.25rem; font-weight:1000; overflow-wrap:anywhere; }
.score-badge { margin-left:auto; width:68px; height:68px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:var(--coach-color); color:#000; font-size:1.45rem; font-weight:1000; box-shadow:0 0 14px var(--coach-color); flex:0 0 auto; }
.award-lines { margin-top:2px; }
.award-line { color:var(--coach-color); font-size:.84rem; line-height:1.18; font-weight:950; text-shadow:0 0 7px var(--coach-color); }
.metric-row { display:flex; justify-content:space-between; gap:10px; border-bottom:1px solid rgba(255,255,255,.11); padding:7px 0; font-size:.92rem; }
.metric-row b { color:#fff; }
.points-pair span { flex:1 1 0; display:flex; justify-content:space-between; gap:8px; }
.points-pair span + span { border-left:1px solid rgba(255,255,255,.28); padding-left:12px; }
.draft-help { border:1px solid rgba(255,213,74,.45); border-radius:8px; background:#090909; color:#fff7cf; padding:9px 10px; font-weight:850; margin:.25rem 0 .75rem; }
.draft-save-note { margin:.28rem 0 .2rem; color:#ffd54a; font-size:.82rem; font-weight:900; line-height:1.15; }
.asset-list { color:#e8f6f8; font-size:.88rem; line-height:1.45; margin-top:9px; }
.draft-board { overflow-x:auto; width:100%; margin:.45rem 0 1rem; }
.draft-board table { width:100%; border-collapse:collapse; min-width:820px; font-size:.82rem; table-layout:fixed; }
.draft-board th { background:#101010; color:#ffd54a; border:1px solid #333; padding:7px 5px; text-align:center; }
.draft-board td { border:1px solid #242424; padding:5px; vertical-align:top; background:#060606; }
.round-head { width:64px; color:#00e5ff!important; }
.pick-cell { border:2px solid var(--coach-color); border-left-width:5px; min-height:74px; border-radius:6px; padding:6px; background:linear-gradient(135deg, rgba(255,255,255,.035), rgba(0,0,0,.02)); box-shadow:inset 0 0 0 1px rgba(255,255,255,.04); }
.pick-cell:hover { background:color-mix(in srgb, var(--coach-color) 22%, #111); box-shadow:0 0 12px var(--coach-color), inset 0 0 0 1px rgba(255,255,255,.06); }
.pick-num { color:#00e5ff; font-size:.75rem; font-weight:1000; }
.pick-coach { font-weight:1000; color:var(--coach-color); font-size:.78rem; }
.pick-choice { color:#ffd54a; font-weight:900; margin-top:3px; overflow-wrap:anywhere; }
.current-pick-box { border:3px solid var(--coach-color); box-shadow:0 0 18px var(--coach-color); border-radius:8px; padding:12px; margin:.75rem 0 1rem; text-align:center; font-size:clamp(1.05rem, 4vw, 1.65rem); font-weight:1000; }
.current-pick-box span { color:var(--coach-color); }
.current-pick-accent { color:var(--coach-color); }
.draft-actions { display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:8px; margin:.3rem 0 .8rem; }
.draft-status-line { display:flex; flex-wrap:wrap; gap:8px; align-items:center; color:#b9c2c9; font-size:.9rem; margin:-.35rem 0 .6rem; }
.draft-control-row { margin:.2rem 0 .5rem; }
.draft-control-row div[data-testid="stButton"] > button { width:100%!important; min-height:50px!important; }
.draft-start-control div[data-testid="stButton"] > button { background:#24b84a!important; border-color:#6dff91!important; color:#001706!important; }
.draft-stop-control div[data-testid="stButton"] > button { background:#ff1f1f!important; border-color:#ff8c8c!important; color:#fff!important; }
.draft-undo-control div[data-testid="stButton"] > button { background:#ffd54a!important; border-color:#fff1a8!important; color:#151000!important; }
.st-key-admin-start-draft div[data-testid="stButton"] > button { background:#24b84a!important; border-color:#6dff91!important; color:#001706!important; }
.st-key-admin-stop-draft div[data-testid="stButton"] > button { background:#ff1f1f!important; border-color:#ff8c8c!important; color:#fff!important; }
.st-key-admin-undo-last-pick-top div[data-testid="stButton"] > button { background:#ffd54a!important; border-color:#fff1a8!important; color:#151000!important; }
.st-key-team-pick-buttons div[data-testid="stButton"] > button,
.st-key-player-pick-buttons div[data-testid="stButton"] > button {
    background:var(--draft-button-bg, #121212)!important;
    border-color:var(--draft-button-border, #444)!important;
    color:var(--draft-button-fg, #fff)!important;
    box-shadow:0 0 12px color-mix(in srgb, var(--draft-button-border, #444) 35%, transparent)!important;
}
.st-key-team-pick-buttons div[data-testid="stButton"] > button:hover,
.st-key-player-pick-buttons div[data-testid="stButton"] > button:hover {
    background:var(--draft-button-hover, #181818)!important;
    border-color:var(--draft-button-border, #00e5ff)!important;
    box-shadow:0 0 18px color-mix(in srgb, var(--draft-button-border, #00e5ff) 50%, transparent)!important;
}
.draft-choice-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:7px; margin:.45rem 0 1rem; }
.draft-choice-cell { display:flex; align-items:stretch; gap:6px; min-width:0; }
.draft-choice-link, .draft-choice-disabled, .draft-choice-button {
    flex:1 1 auto; min-width:0; min-height:42px; display:flex; align-items:center;
    border:1px solid #444; border-radius:8px; background:#121212; color:#fff!important;
    text-decoration:none!important; font-weight:900; font-size:.86rem; line-height:1.15;
    padding:6px 9px; overflow-wrap:anywhere;
}
.draft-choice-link:hover, .draft-choice-button:hover { border-color:#00e5ff; background:#181818; }
.draft-choice-disabled { color:#777!important; background:#202020; border-color:#333; }
.draft-choice-button { justify-content:space-between; width:100%; cursor:pointer; }
.draft-choice-button .info-link { margin-left:8px; flex:0 0 auto; }
.draft-info-wrap { flex:0 0 32px; min-height:42px; display:flex; align-items:center; justify-content:center; border:1px solid #303030; border-radius:8px; background:#070707; }
.info-link { color:#00e5ff!important; text-decoration:none!important; font-size:.82rem; margin-left:3px; display:inline-flex; align-items:center; justify-content:center; }
.flag-icon { display:inline-flex; width:1.05em; height:1.05em; align-items:center; justify-content:center; vertical-align:-.13em; margin-right:.22em; }
.flag-icon svg { width:100%; height:100%; display:block; }
.asset-list .info-link, .match-line .info-link, .data-table .info-link { font-size:.72rem; margin-left:2px; }
.available-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(112px, 1fr)); gap:6px; margin:.45rem 0 1rem; }
.choice-card { border:0; border-radius:0; background:transparent; padding:0; min-height:0; }
.choice-title { font-weight:1000; color:#fff; }
.choice-meta { color:#9eefff; font-size:.82rem; margin:.15rem 0 .45rem; }
.match-card { border:1px solid #292929; border-radius:8px; background:#070707; padding:10px 12px; margin-bottom:8px; }
.match-line { display:flex; flex-wrap:wrap; align-items:center; gap:8px; font-weight:1000; }
.match-score { color:#ffd54a; }
.matches-grid { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:8px; }
.match-section-spacer { height:14px; }
.match-stage-title { color:#ffd54a; font-weight:1000; font-size:1rem; }
div[data-testid="stExpander"] summary p { font-size:1.03rem; }
.drafted-chip { display:inline-flex; border-radius:6px; border:1px solid var(--coach-color); color:var(--coach-color); padding:2px 6px; margin:2px 3px 0 0; font-size:.78rem; font-weight:900; }
.payout-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; }
.payout-item { border:1px solid #2d2d2d; border-radius:8px; padding:10px; background:#070707; }
.payout-item b { color:#ffd54a; }
.payout-desc { border-left:4px solid #ffd54a; background:#070707; border-radius:8px; padding:11px 13px; margin:.7rem 0; color:#eaf7fa; line-height:1.45; }
.payout-desc b { color:#ffd54a; }
.data-table { width:100%; border-collapse:collapse; background:#070707; border-radius:8px; overflow:hidden; font-size:.88rem; }
.data-table th { text-align:left; color:#ffd54a; background:#101010; border-bottom:1px solid #333; padding:8px; }
.data-table td { border-bottom:1px solid rgba(255,255,255,.1); padding:8px; vertical-align:middle; }
.data-table tr:last-child td { border-bottom:none; }
.team-standings-table { table-layout:fixed; }
.team-standings-table th:nth-child(1), .team-standings-table td:nth-child(1) { width:28%; }
.team-standings-table th:nth-child(2), .team-standings-table td:nth-child(2) { width:24%; }
.team-standings-table th:nth-child(3), .team-standings-table td:nth-child(3) { width:10%; text-align:center; }
.team-standings-table th:nth-child(4), .team-standings-table td:nth-child(4) { width:14%; text-align:center; }
.team-standings-table th:nth-child(5), .team-standings-table td:nth-child(5) { width:12%; text-align:center; }
.team-standings-table th:nth-child(6), .team-standings-table td:nth-child(6) { width:12%; text-align:center; }
.team-main-row td { border-bottom:0; font-weight:900; }
.team-name-cell { overflow-wrap:anywhere; }
.team-detail-row td { background:#050505; color:#b9c2c9; padding-top:2px; border-bottom:1px solid rgba(255,255,255,.16); }
.team-detail-grid { display:grid; grid-template-columns:1.35fr 1fr; gap:8px; align-items:center; font-size:.8rem; line-height:1.25; }
.team-detail-grid b { color:#ffd54a; }
.coach-dot { display:inline-flex; width:.85rem; height:.85rem; border-radius:50%; background:var(--coach-color); box-shadow:0 0 8px var(--coach-color); margin-right:6px; vertical-align:-.12rem; }
.coach-mini-face { width:22px; height:22px; border-radius:50%; object-fit:cover; border:2px solid var(--coach-color); box-shadow:0 0 8px var(--coach-color); vertical-align:middle; margin:0 4px 0 0; }
.coach-mini-placeholder { display:inline-flex; width:22px; height:22px; border-radius:50%; border:2px solid var(--coach-color); color:var(--coach-color); align-items:center; justify-content:center; font-size:.58rem; font-weight:1000; vertical-align:middle; margin:0 4px 0 0; }
.admin-box { border:1px solid #333; background:#060606; border-radius:8px; padding:12px; margin:1rem 0; }
@media (max-width:700px) {
    div[data-testid="stButton"] > button { min-height:42px!important; font-size:.84rem!important; padding:6px 7px!important; }
    .top-thumbnail-wrap { width:100vw; margin-left:calc(50% - 50vw); margin-right:calc(50% - 50vw); }
    .top-thumbnail { width:100vw; max-width:none; max-height:34vh; object-fit:cover; border-radius:0; }
    .coach-card { min-height:auto; }
    .coach-face, .coach-face-placeholder { width:60px; height:60px; }
    .score-badge { width:58px; height:58px; font-size:1.2rem; }
    .matches-grid { grid-template-columns:1fr; }
    .available-grid { grid-template-columns:repeat(3, minmax(0, 1fr)); gap:5px; }
    .draft-board table { min-width:720px; font-size:.74rem; }
    .draft-board th { padding:5px 3px; }
    .draft-board td { padding:3px; }
    .pick-cell { min-height:62px; padding:4px; }
    .pick-choice { font-size:.72rem; }
    .draft-control-row { margin:.15rem 0 .35rem; }
    .draft-control-row div[data-testid="stButton"] > button { min-height:38px!important; font-size:.75rem!important; padding:4px 6px!important; }
    .draft-save-note { font-size:.74rem; margin:.2rem 0 .1rem; }
    .draft-choice-grid { grid-template-columns:repeat(2, minmax(0, 1fr)); gap:5px; }
    .draft-choice-link, .draft-choice-disabled { min-height:38px; font-size:.74rem; padding:5px 6px; }
    .draft-info-wrap { flex-basis:26px; min-height:38px; }
    .info-link { font-size:.74rem; margin-left:1px; }
    .data-table { font-size:.78rem; }
    .data-table th, .data-table td { padding:6px 5px; }
    .team-standings-table { font-size:.72rem; }
    .team-standings-table th, .team-standings-table td { padding:5px 4px; }
    .team-standings-table th:nth-child(1), .team-standings-table td:nth-child(1) { width:30%; }
    .team-standings-table th:nth-child(2), .team-standings-table td:nth-child(2) { width:24%; }
    .team-standings-table th:nth-child(3), .team-standings-table td:nth-child(3) { width:10%; }
    .team-standings-table th:nth-child(4), .team-standings-table td:nth-child(4) { width:14%; }
    .team-standings-table th:nth-child(5), .team-standings-table td:nth-child(5) { width:11%; }
    .team-standings-table th:nth-child(6), .team-standings-table td:nth-child(6) { width:11%; }
    .team-detail-grid { grid-template-columns:1fr; gap:3px; font-size:.7rem; }
    .team-standings-table .coach-mini-face,
    .team-standings-table .coach-mini-placeholder { width:18px; height:18px; margin-right:3px; }
}
</style>
""",
    unsafe_allow_html=True,
)


COACHES = ["Benji", "Jeff", "Peter", "Chad", "Lamp", "Herb", "Jayme", "Spencer"]
STATE_FILE_PATH = "draft_state.json"
BRANCH = "main"
REPO_OWNER = "theleitas"
REPO_NAME = "world-cup-fc"
TITLE_THUMBNAIL_PATH = "titlethumb.png"
AUTO_SCORE_REFRESH_SECONDS = 5 * 60
KICKOFF_DEADLINE = "Thursday, June 11 at 8:00 PM EST"

TEAM_ROUND_DIRECTIONS = ["forward", "reverse", "reverse", "forward", "reverse", "forward"]
PLAYER_ROUND_DIRECTIONS = ["reverse", "forward"]
DRAFT_BUTTON_COLUMNS = 2

TEAM_COLOR_OPTIONS = [
    ("Gold", "#FFD54A"),
    ("Electric Cyan", "#00E5FF"),
    ("Hot Pink", "#FF2DAA"),
    ("Volt Green", "#40FF6A"),
    ("Orange Flash", "#FF7A1A"),
    ("Royal Blue", "#3F7BFF"),
    ("Lavender", "#B56CFF"),
    ("Red Alert", "#FF3D3D"),
    ("Mint", "#48FFD2"),
    ("White Gold", "#FFF1A8"),
]
TEAM_COLOR_BY_HEX = {hex_value: label for label, hex_value in TEAM_COLOR_OPTIONS}

DEFAULT_PLAYERS = [
    "Lamine Yamal (Spain)",
    "Kylian Mbappe (France)",
    "Harry Kane (England)",
    "Ousmane Dembele (France)",
    "Michael Olise (France)",
    "Erling Haaland (Norway)",
    "Vinicius Junior (Brazil)",
    "Julian Alvarez (Argentina)",
    "Raphinha (Brazil)",
    "Lionel Messi (Argentina)",
    "Luis Diaz (Colombia)",
    "Antoine Semenyo (Ghana)",
    "Lautaro Martinez (Argentina)",
    "Bukayo Saka (England)",
    "Desire Doue (France)",
    "Jeremy Doku (Belgium)",
    "Cristiano Ronaldo (Portugal)",
    "Neymar Jr. (Brazil)",
    "Sadio Mane (Senegal)",
    "Nico Williams (Spain)",
    "Mohamed Salah (Egypt)",
    "Omar Marmoush (Egypt)",
    "Patrick Schick (Czechia)",
    "Victor Gyokeres (Sweden)",
    "Arda Guler (Türkiye)",
]

WORLD_CUP_TEAMS = [
    {"name": "Canada", "flag": "🇨🇦", "confed": "Concacaf"},
    {"name": "Mexico", "flag": "🇲🇽", "confed": "Concacaf"},
    {"name": "USA", "flag": "🇺🇸", "confed": "Concacaf"},
    {"name": "Australia", "flag": "🇦🇺", "confed": "AFC"},
    {"name": "Iraq", "flag": "🇮🇶", "confed": "AFC"},
    {"name": "IR Iran", "flag": "🇮🇷", "confed": "AFC"},
    {"name": "Japan", "flag": "🇯🇵", "confed": "AFC"},
    {"name": "Jordan", "flag": "🇯🇴", "confed": "AFC"},
    {"name": "Korea Republic", "flag": "🇰🇷", "confed": "AFC"},
    {"name": "Qatar", "flag": "🇶🇦", "confed": "AFC"},
    {"name": "Saudi Arabia", "flag": "🇸🇦", "confed": "AFC"},
    {"name": "Uzbekistan", "flag": "🇺🇿", "confed": "AFC"},
    {"name": "Algeria", "flag": "🇩🇿", "confed": "CAF"},
    {"name": "Cabo Verde", "flag": "🇨🇻", "confed": "CAF"},
    {"name": "Congo DR", "flag": "🇨🇩", "confed": "CAF"},
    {"name": "Côte d'Ivoire", "flag": "🇨🇮", "confed": "CAF"},
    {"name": "Egypt", "flag": "🇪🇬", "confed": "CAF"},
    {"name": "Ghana", "flag": "🇬🇭", "confed": "CAF"},
    {"name": "Morocco", "flag": "🇲🇦", "confed": "CAF"},
    {"name": "Senegal", "flag": "🇸🇳", "confed": "CAF"},
    {"name": "South Africa", "flag": "🇿🇦", "confed": "CAF"},
    {"name": "Tunisia", "flag": "🇹🇳", "confed": "CAF"},
    {"name": "Curaçao", "flag": "🇨🇼", "confed": "Concacaf"},
    {"name": "Haiti", "flag": "🇭🇹", "confed": "Concacaf"},
    {"name": "Panama", "flag": "🇵🇦", "confed": "Concacaf"},
    {"name": "Argentina", "flag": "🇦🇷", "confed": "CONMEBOL"},
    {"name": "Brazil", "flag": "🇧🇷", "confed": "CONMEBOL"},
    {"name": "Colombia", "flag": "🇨🇴", "confed": "CONMEBOL"},
    {"name": "Ecuador", "flag": "🇪🇨", "confed": "CONMEBOL"},
    {"name": "Paraguay", "flag": "🇵🇾", "confed": "CONMEBOL"},
    {"name": "Uruguay", "flag": "🇺🇾", "confed": "CONMEBOL"},
    {"name": "New Zealand", "flag": "🇳🇿", "confed": "OFC"},
    {"name": "Austria", "flag": "🇦🇹", "confed": "UEFA"},
    {"name": "Belgium", "flag": "🇧🇪", "confed": "UEFA"},
    {"name": "Bosnia and Herzegovina", "flag": "🇧🇦", "confed": "UEFA"},
    {"name": "Croatia", "flag": "🇭🇷", "confed": "UEFA"},
    {"name": "Czechia", "flag": "🇨🇿", "confed": "UEFA"},
    {"name": "England", "flag": "🇬🇧", "confed": "UEFA"},
    {"name": "France", "flag": "🇫🇷", "confed": "UEFA"},
    {"name": "Germany", "flag": "🇩🇪", "confed": "UEFA"},
    {"name": "Netherlands", "flag": "🇳🇱", "confed": "UEFA"},
    {"name": "Norway", "flag": "🇳🇴", "confed": "UEFA"},
    {"name": "Portugal", "flag": "🇵🇹", "confed": "UEFA"},
    {"name": "Scotland", "flag": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F", "confed": "UEFA"},
    {"name": "Spain", "flag": "🇪🇸", "confed": "UEFA"},
    {"name": "Sweden", "flag": "🇸🇪", "confed": "UEFA"},
    {"name": "Switzerland", "flag": "🇨🇭", "confed": "UEFA"},
    {"name": "Türkiye", "flag": "🇹🇷", "confed": "UEFA"},
]

DEFAULT_ODDS = {
    "Spain": "+400",
    "France": "+450",
    "England": "+600",
    "Brazil": "+800",
    "Argentina": "+800",
    "Portugal": "+800",
    "Germany": "+1400",
    "Netherlands": "+2000",
    "Norway": "+2500",
    "Belgium": "+3300",
    "Colombia": "+3300",
    "Morocco": "+5000",
    "Japan": "+5000",
    "USA": "+6600",
    "Mexico": "+6600",
    "Uruguay": "+6600",
    "Switzerland": "+8000",
    "Croatia": "+8000",
    "Türkiye": "+8000",
    "Ecuador": "+10000",
    "Sweden": "+10000",
    "Senegal": "+15000",
    "Canada": "+15000",
    "Austria": "+15000",
    "Paraguay": "+15000",
    "Scotland": "+25000",
    "Bosnia and Herzegovina": "+25000",
    "Côte d'Ivoire": "+30000",
    "Czechia": "+30000",
    "Egypt": "+30000",
    "Ghana": "+35000",
    "Algeria": "+40000",
    "Korea Republic": "+40000",
    "Australia": "+50000",
    "Tunisia": "+50000",
    "IR Iran": "+50000",
    "Congo DR": "+75000",
    "South Africa": "+90000",
    "Saudi Arabia": "+100000",
    "Qatar": "+100000",
    "Panama": "+100000",
    "Iraq": "+100000",
    "New Zealand": "+100000",
    "Cabo Verde": "+100000",
    "Uzbekistan": "+100000",
    "Jordan": "+100000",
    "Haiti": "+100000",
    "Curaçao": "+100000",
}

FIFA_RANKING_LOCK_DATE = "April 1, 2026"
FIFA_RANKING_SOURCE_URL = "https://inside.fifa.com/fifa-world-ranking/USA?gender=men"
FIFA_EXPECTED_LOW = 6.0
FIFA_EXPECTED_HIGH = 54.0
FIFA_RANKINGS = {
    "France": {"rank": 1, "points": 1877.32, "code": "FRA"},
    "Spain": {"rank": 2, "points": 1876.4, "code": "ESP"},
    "Argentina": {"rank": 3, "points": 1874.81, "code": "ARG"},
    "England": {"rank": 4, "points": 1825.97, "code": "ENG"},
    "Portugal": {"rank": 5, "points": 1763.83, "code": "POR"},
    "Brazil": {"rank": 6, "points": 1761.16, "code": "BRA"},
    "Netherlands": {"rank": 7, "points": 1757.87, "code": "NED"},
    "Morocco": {"rank": 8, "points": 1755.87, "code": "MAR"},
    "Belgium": {"rank": 9, "points": 1734.71, "code": "BEL"},
    "Germany": {"rank": 10, "points": 1730.37, "code": "GER"},
    "Croatia": {"rank": 11, "points": 1717.07, "code": "CRO"},
    "Colombia": {"rank": 13, "points": 1693.09, "code": "COL"},
    "Senegal": {"rank": 14, "points": 1688.99, "code": "SEN"},
    "Mexico": {"rank": 15, "points": 1681.03, "code": "MEX"},
    "USA": {"rank": 16, "points": 1673.13, "code": "USA"},
    "Uruguay": {"rank": 17, "points": 1673.07, "code": "URU"},
    "Japan": {"rank": 18, "points": 1660.43, "code": "JPN"},
    "Switzerland": {"rank": 19, "points": 1649.4, "code": "SUI"},
    "IR Iran": {"rank": 21, "points": 1615.3, "code": "IRN"},
    "Türkiye": {"rank": 22, "points": 1599.04, "code": "TUR"},
    "Ecuador": {"rank": 23, "points": 1594.78, "code": "ECU"},
    "Austria": {"rank": 24, "points": 1593.45, "code": "AUT"},
    "Korea Republic": {"rank": 25, "points": 1588.66, "code": "KOR"},
    "Australia": {"rank": 27, "points": 1580.67, "code": "AUS"},
    "Algeria": {"rank": 28, "points": 1564.26, "code": "ALG"},
    "Egypt": {"rank": 29, "points": 1563.24, "code": "EGY"},
    "Canada": {"rank": 30, "points": 1556.48, "code": "CAN"},
    "Norway": {"rank": 31, "points": 1550.94, "code": "NOR"},
    "Panama": {"rank": 33, "points": 1540.64, "code": "PAN"},
    "Côte d'Ivoire": {"rank": 34, "points": 1532.98, "code": "CIV"},
    "Sweden": {"rank": 38, "points": 1514.77, "code": "SWE"},
    "Paraguay": {"rank": 40, "points": 1503.5, "code": "PAR"},
    "Czechia": {"rank": 41, "points": 1501.38, "code": "CZE"},
    "Scotland": {"rank": 43, "points": 1498.35, "code": "SCO"},
    "Tunisia": {"rank": 44, "points": 1483.05, "code": "TUN"},
    "Congo DR": {"rank": 46, "points": 1478.35, "code": "COD"},
    "Uzbekistan": {"rank": 50, "points": 1465.34, "code": "UZB"},
    "Qatar": {"rank": 55, "points": 1454.96, "code": "QAT"},
    "Iraq": {"rank": 57, "points": 1447.14, "code": "IRQ"},
    "South Africa": {"rank": 60, "points": 1429.73, "code": "RSA"},
    "Saudi Arabia": {"rank": 61, "points": 1421.43, "code": "KSA"},
    "Jordan": {"rank": 63, "points": 1391.45, "code": "JOR"},
    "Bosnia and Herzegovina": {"rank": 65, "points": 1385.84, "code": "BIH"},
    "Cabo Verde": {"rank": 69, "points": 1366.13, "code": "CPV"},
    "Ghana": {"rank": 74, "points": 1346.31, "code": "GHA"},
    "Curaçao": {"rank": 82, "points": 1294.65, "code": "CUW"},
    "Haiti": {"rank": 83, "points": 1291.71, "code": "HAI"},
    "New Zealand": {"rank": 85, "points": 1281.57, "code": "NZL"},
}

TEAM_ALIASES = {
    "united states": "USA",
    "usa": "USA",
    "us": "USA",
    "turkey": "Türkiye",
    "turkiye": "Türkiye",
    "türkiye": "Türkiye",
    "ivory coast": "Côte d'Ivoire",
    "cote d'ivoire": "Côte d'Ivoire",
    "côte d'ivoire": "Côte d'Ivoire",
    "cape verde": "Cabo Verde",
    "cape verde islands": "Cabo Verde",
    "cabo verde": "Cabo Verde",
    "czech republic": "Czechia",
    "czechia": "Czechia",
    "south korea": "Korea Republic",
    "korea republic": "Korea Republic",
    "iran": "IR Iran",
    "ir iran": "IR Iran",
    "curacao": "Curaçao",
    "curaçao": "Curaçao",
    "dr congo": "Congo DR",
    "congo dr": "Congo DR",
}

FIFA_TEAM_SLUGS = {
    "Canada": "canada",
    "Mexico": "mexico",
    "USA": "usa",
    "Australia": "australia",
    "Iraq": "iraq",
    "IR Iran": "ir-iran",
    "Japan": "japan",
    "Jordan": "jordan",
    "Korea Republic": "korea-republic",
    "Qatar": "qatar",
    "Saudi Arabia": "saudi-arabia",
    "Uzbekistan": "uzbekistan",
    "Algeria": "algeria",
    "Cabo Verde": "cabo-verde",
    "Congo DR": "congo-dr",
    "Côte d'Ivoire": "cote-divoire",
    "Egypt": "egypt",
    "Ghana": "ghana",
    "Morocco": "morocco",
    "Senegal": "senegal",
    "South Africa": "south-africa",
    "Tunisia": "tunisia",
    "Curaçao": "curacao",
    "Haiti": "haiti",
    "Panama": "panama",
    "Argentina": "argentina",
    "Brazil": "brazil",
    "Colombia": "colombia",
    "Ecuador": "ecuador",
    "Paraguay": "paraguay",
    "Uruguay": "uruguay",
    "New Zealand": "new-zealand",
    "Austria": "austria",
    "Belgium": "belgium",
    "Bosnia and Herzegovina": "bosnia-and-herzegovina",
    "Croatia": "croatia",
    "Czechia": "czechia",
    "England": "england",
    "France": "france",
    "Germany": "germany",
    "Netherlands": "netherlands",
    "Norway": "norway",
    "Portugal": "portugal",
    "Scotland": "scotland",
    "Spain": "spain",
    "Sweden": "sweden",
    "Switzerland": "switzerland",
    "Türkiye": "turkiye",
}

ADVANCEMENT_BONUSES = {
    "Group Stage": 0,
    "Round of 32": 5,
    "Round of 16": 8,
    "Quarterfinals": 12,
    "Semifinals": 15,
    "Final": 20,
    "Champion": 25,
}
ADVANCEMENT_LEVELS = list(ADVANCEMENT_BONUSES.keys())

PAYOUTS = [
    ("Gold", "$300", "1st overall by total points"),
    ("Silver", "$150", "2nd overall by total points"),
    ("Bronze", "$100", "3rd overall by total points"),
    ("Group Stage Winner", "$90", "Most group-stage fantasy points"),
    ("Empire Builder", "$80", "Most teams reaching the Round of 16; tiebreaker goals"),
    ("Cinderella Award", "$80", "Single drafted team with the biggest actual-minus-FIFA-baseline score"),
]


def read_secret(*path):
    try:
        cur = st.secrets
        for key in path:
            if key not in cur:
                return None
            cur = cur[key]
        return cur
    except Exception:
        return None


GITHUB_TOKEN = read_secret("GITHUB", "TOKEN") or os.environ.get("GITHUB_TOKEN")
GITHUB_OWNER = read_secret("GITHUB", "OWNER") or os.environ.get("GITHUB_OWNER") or REPO_OWNER
GITHUB_REPO = read_secret("GITHUB", "REPO_NAME") or os.environ.get("GITHUB_REPO_NAME") or REPO_NAME
FOOTBALL_DATA_TOKEN = read_secret("FOOTBALL_DATA", "TOKEN") or os.environ.get("FOOTBALL_DATA_TOKEN")

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def clean_key(value):
    value = str(value or "").strip().lower()
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "á": "a", "à": "a", "ä": "a", "ã": "a",
        "í": "i", "ï": "i", "ó": "o", "ö": "o",
        "ú": "u", "ü": "u", "ç": "c", "ı": "i",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"\s+", " ", value).strip()


def canonical_team_name(value):
    text = str(value or "").strip()
    if not text:
        return ""
    team_names = {team["name"] for team in WORLD_CUP_TEAMS}
    if text in team_names:
        return text
    return TEAM_ALIASES.get(clean_key(text), text)


def team_lookup():
    return {team["name"]: team for team in WORLD_CUP_TEAMS}


def flag_for_team(team_name):
    return team_lookup().get(canonical_team_name(team_name), {}).get("flag", "🏳️")


def display_team(team_name, odds=None):
    name = canonical_team_name(team_name)
    suffix = f" ({odds})" if odds else ""
    return f"{flag_for_team(name)} {name}{suffix}"


def team_flag_html(team_name):
    name = canonical_team_name(team_name)
    if name == "Bosnia and Herzegovina":
        return """
<span class='flag-icon' title='Bosnia and Herzegovina'>
  <svg viewBox='0 0 64 64' aria-hidden='true' focusable='false'>
    <path d='M13 7h38v22c0 18-12 27-19 31-7-4-19-13-19-31z' fill='#0b8bd3'/>
    <path d='M8 7h16l33 45-7 6L13 11z' fill='#fff'/>
    <g fill='#ffd54a'>
      <path d='M33 13l2 5 5 1-4 3 1 5-4-3-4 3 1-5-4-3 5-1z'/>
      <path d='M45 18l2 5 5 1-4 3 1 5-4-3-4 3 1-5-4-3 5-1z'/>
      <path d='M36 31l2 5 5 1-4 3 1 5-4-3-4 3 1-5-4-3 5-1z'/>
      <path d='M27 44l2 5 5 1-4 3 1 5-4-3-4 3 1-5-4-3 5-1z'/>
    </g>
  </svg>
</span>
"""
    return f"<span class='flag-icon'>{html.escape(flag_for_team(name))}</span>"


def team_info_url(team_name):
    name = canonical_team_name(team_name)
    slug = FIFA_TEAM_SLUGS.get(name)
    if slug:
        return f"https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/teams/{slug}"
    return "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/teams/"


def player_info_url(player):
    query = f"{player_base_name(player)} footballer"
    return f"https://en.wikipedia.org/wiki/Special:Search?search={quote(query)}"


def info_link(url, label="info"):
    return f"<a class='info-link' href='{html.escape(url, quote=True)}' target='_blank' rel='noopener' title='{html.escape(label)}'>ⓘ</a>"


def display_team_html(team_name, odds=None, include_info=True):
    name = canonical_team_name(team_name)
    suffix = f" ({html.escape(str(odds))})" if odds else ""
    text = f"{team_flag_html(name)}{html.escape(name)}{suffix}"
    return text + (info_link(team_info_url(team_name), f"{canonical_team_name(team_name)} info") if include_info else "")


def display_player_html(player, include_info=True):
    text = html.escape(display_player(player))
    return text + (info_link(player_info_url(player), f"{player_base_name(player)} info") if include_info else "")


def player_country(player):
    match = re.search(r"\(([^)]+)\)\s*$", str(player or ""))
    return canonical_team_name(match.group(1)) if match else ""


def player_base_name(player):
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(player or "")).strip()


def normalize_player_name(value):
    text = clean_key(value)
    replacements = {
        "mbappe": "mbappe",
        "mbappé": "mbappe",
        "vinicius jr": "vinicius junior",
        "vinicius jr.": "vinicius junior",
        "neymar": "neymar jr",
        "cristiano ronaldo dos santos aveiro": "cristiano ronaldo",
        "lamine yamal nasraoui ebana": "lamine yamal",
        "arda güler": "arda guler",
        "victor gyökeres": "victor gyokeres",
        "ousmane dembélé": "ousmane dembele",
        "désiré doué": "desire doue",
        "lautaro martinez": "lautaro martinez",
        "julián alvarez": "julian alvarez",
        "luis díaz": "luis diaz",
    }
    text = replacements.get(text, text)
    text = re.sub(r"\b(jr|jr\.)\b", "junior", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def player_lookup(players):
    lookup = {}
    for player in players:
        base = player_base_name(player)
        lookup[normalize_player_name(base)] = player
        parts = normalize_player_name(base).split()
        if len(parts) >= 2:
            lookup.setdefault(" ".join(parts[-2:]), player)
            lookup.setdefault(parts[-1], player)
    return lookup


def match_player_to_pool(name, players):
    normalized = normalize_player_name(name)
    lookup = player_lookup(players)
    if normalized in lookup:
        return lookup[normalized]
    for key, player in lookup.items():
        if key and (key in normalized or normalized in key):
            return player
    return ""


def display_player(player):
    country = player_country(player)
    return f"{flag_for_team(country)} {player}" if country else str(player)


def coach_photo_filename(coach):
    return f"{coach}.png"


def default_team_color(index):
    return TEAM_COLOR_OPTIONS[index % len(TEAM_COLOR_OPTIONS)][1]


def build_draft_sequence(round_directions, start_pick=1):
    sequence = []
    pick_number = start_pick
    for round_index, direction in enumerate(round_directions, start=1):
        coaches = list(COACHES) if direction == "forward" else list(reversed(COACHES))
        for slot_index, coach in enumerate(coaches, start=1):
            sequence.append(
                {
                    "pick": pick_number,
                    "round": round_index,
                    "slot": slot_index,
                    "coach": coach,
                    "direction": direction,
                }
            )
            pick_number += 1
    return sequence


TEAM_DRAFT_SEQUENCE = build_draft_sequence(TEAM_ROUND_DIRECTIONS)
PLAYER_DRAFT_SEQUENCE = build_draft_sequence(PLAYER_ROUND_DIRECTIONS, start_pick=len(TEAM_DRAFT_SEQUENCE) + 1)


def odds_to_expected_points(odds):
    text = str(odds or "").strip()
    if not text:
        return 12.0
    number = re.sub(r"[^0-9-]", "", text)
    try:
        value = abs(int(number))
    except ValueError:
        return 12.0
    if value <= 500:
        return 54.0
    if value <= 1000:
        return 44.0
    if value <= 2500:
        return 35.0
    if value <= 6600:
        return 26.0
    if value <= 15000:
        return 18.0
    if value <= 40000:
        return 12.0
    return 7.0


def fifa_expected_points(team_name):
    name = canonical_team_name(team_name)
    ranking = FIFA_RANKINGS.get(name)
    if not ranking:
        return 0.0
    all_points = [item["points"] for item in FIFA_RANKINGS.values()]
    min_points = min(all_points)
    max_points = max(all_points)
    if max_points == min_points:
        return (FIFA_EXPECTED_LOW + FIFA_EXPECTED_HIGH) / 2
    strength = (float(ranking["points"]) - min_points) / (max_points - min_points)
    return FIFA_EXPECTED_LOW + strength * (FIFA_EXPECTED_HIGH - FIFA_EXPECTED_LOW)


def fifa_rank_text(team_name):
    ranking = FIFA_RANKINGS.get(canonical_team_name(team_name), {})
    if not ranking:
        return "FIFA rank n/a"
    return f"FIFA #{ranking['rank']} / {ranking['points']:.2f} pts"


def default_coaches():
    return {
        coach: {
            "team_name": coach,
            "color": default_team_color(index),
            "image": coach_photo_filename(coach),
            "national_teams": [],
            "star_players": [],
        }
        for index, coach in enumerate(COACHES)
    }


def seed_matches():
    return [
        {
            "id": "match-001",
            "date": "2026-06-11T20:00:00-04:00",
            "stage": "Group Stage",
            "home": "Mexico",
            "away": "South Africa",
            "home_score": None,
            "away_score": None,
            "status": "Scheduled",
            "group": "GROUP_A",
        }
    ]


def default_state():
    odds = copy.deepcopy(DEFAULT_ODDS)
    return {
        "app_title": "World Cup FC",
        "draft_enabled": True,
        "draft_active": True,
        "teams": default_coaches(),
        "team_picks": [],
        "player_picks": [],
        "players": list(DEFAULT_PLAYERS),
        "odds": odds,
        "expected_points": {name: odds_to_expected_points(odds.get(name)) for name in DEFAULT_ODDS},
        "matches": seed_matches(),
        "player_stats": {player: {"goals": 0, "assists": 0, "group_goals": 0, "group_assists": 0} for player in DEFAULT_PLAYERS},
        "advancement": {team["name"]: "Group Stage" for team in WORLD_CUP_TEAMS},
        "last_score_refresh_at": 0,
        "last_score_refresh_attempt_at": 0,
        "last_api_error": "",
        "last_friendly_api_error": "",
        "current_pick_started_at": int(time.time()),
    }


def normalize_state(state):
    base = default_state()
    if not isinstance(state, dict):
        return base

    state.setdefault("app_title", base["app_title"])
    state.setdefault("draft_enabled", base["draft_enabled"])
    state.setdefault("draft_active", True)
    state.setdefault("team_picks", [])
    state.setdefault("player_picks", [])
    state.setdefault("players", list(DEFAULT_PLAYERS))
    state.setdefault("odds", {})
    state.setdefault("expected_points", {})
    state.setdefault("matches", [])
    state.setdefault("player_stats", {})
    state.setdefault("advancement", {})
    state.setdefault("last_score_refresh_at", 0)
    state.setdefault("last_score_refresh_attempt_at", 0)
    state.setdefault("last_api_error", "")
    state.setdefault("last_friendly_api_error", "")
    state.setdefault("current_pick_started_at", int(time.time()))

    state["players"] = [str(player).strip() for player in state.get("players", []) if str(player).strip()]
    if not state["players"]:
        state["players"] = list(DEFAULT_PLAYERS)

    normalized_odds = copy.deepcopy(DEFAULT_ODDS)
    for raw_team, raw_odds in (state.get("odds") or {}).items():
        name = canonical_team_name(raw_team)
        if name:
            normalized_odds[name] = str(raw_odds or "").strip()
    state["odds"] = normalized_odds

    normalized_expected = {name: odds_to_expected_points(normalized_odds.get(name)) for name in normalized_odds}
    for raw_team, raw_expected in (state.get("expected_points") or {}).items():
        name = canonical_team_name(raw_team)
        try:
            normalized_expected[name] = float(raw_expected)
        except (TypeError, ValueError):
            pass
    state["expected_points"] = normalized_expected

    normalized_advancement = {team["name"]: "Group Stage" for team in WORLD_CUP_TEAMS}
    for raw_team, raw_level in (state.get("advancement") or {}).items():
        name = canonical_team_name(raw_team)
        level = str(raw_level or "Group Stage").strip()
        normalized_advancement[name] = level if level in ADVANCEMENT_BONUSES else "Group Stage"
    state["advancement"] = normalized_advancement

    existing_coaches = state.get("teams") if isinstance(state.get("teams"), dict) else {}
    normalized_coaches = {}
    used_colors = set()
    for index, coach in enumerate(COACHES):
        prior = existing_coaches.get(coach) if isinstance(existing_coaches.get(coach), dict) else {}
        color = str(prior.get("color") or default_team_color(index)).strip()
        if color not in TEAM_COLOR_BY_HEX or color in used_colors:
            color = next(hex_value for _, hex_value in TEAM_COLOR_OPTIONS if hex_value not in used_colors)
        used_colors.add(color)
        normalized_coaches[coach] = {
            "team_name": str(prior.get("team_name") or coach).strip() or coach,
            "color": color,
            "image": coach_photo_filename(coach),
            "national_teams": [canonical_team_name(item) for item in prior.get("national_teams", []) if canonical_team_name(item)],
            "star_players": [str(item).strip() for item in prior.get("star_players", []) if str(item).strip()],
        }
    state["teams"] = normalized_coaches

    state["team_picks"] = normalize_pick_list(state.get("team_picks"), TEAM_DRAFT_SEQUENCE, "team")
    state["player_picks"] = normalize_pick_list(state.get("player_picks"), PLAYER_DRAFT_SEQUENCE, "player")
    apply_picks_to_rosters(state)

    state["matches"] = [normalize_match(match, index) for index, match in enumerate(state.get("matches") or [])]
    state["player_stats"] = normalize_player_stats(state.get("player_stats"), state["players"])
    return state


def normalize_pick_list(raw_picks, sequence, field):
    picks = []
    seen_pick_numbers = set()
    sequence_by_pick = {item["pick"]: item for item in sequence}
    for raw in raw_picks or []:
        if not isinstance(raw, dict):
            continue
        try:
            pick_number = int(raw.get("pick"))
        except (TypeError, ValueError):
            continue
        if pick_number not in sequence_by_pick or pick_number in seen_pick_numbers:
            continue
        expected = sequence_by_pick[pick_number]
        choice = raw.get(field)
        choice = canonical_team_name(choice) if field == "team" else str(choice or "").strip()
        if not choice:
            continue
        picks.append(
            {
                "pick": pick_number,
                "round": expected["round"],
                "coach": expected["coach"],
                field: choice,
                "picked_at": raw.get("picked_at") or "",
            }
        )
        seen_pick_numbers.add(pick_number)
    return sorted(picks, key=lambda item: item["pick"])


def apply_picks_to_rosters(state):
    for coach in COACHES:
        state["teams"][coach]["national_teams"] = []
        state["teams"][coach]["star_players"] = []
    for pick in state.get("team_picks", []):
        coach = pick.get("coach")
        team = canonical_team_name(pick.get("team"))
        if coach in state["teams"] and team not in state["teams"][coach]["national_teams"]:
            state["teams"][coach]["national_teams"].append(team)
    for pick in state.get("player_picks", []):
        coach = pick.get("coach")
        player = str(pick.get("player") or "").strip()
        if coach in state["teams"] and player not in state["teams"][coach]["star_players"]:
            state["teams"][coach]["star_players"].append(player)


def normalize_match(match, index):
    match = match if isinstance(match, dict) else {}
    goals = match.get("goals") if isinstance(match.get("goals"), list) else []
    score_node = match.get("score_node") if isinstance(match.get("score_node"), dict) else {}
    return {
        "id": str(match.get("id") or f"match-{index + 1:03d}"),
        "date": str(match.get("date") or ""),
        "stage": str(match.get("stage") or "Group Stage"),
        "group": match.get("group"),
        "matchday": none_or_int(match.get("matchday")),
        "home": canonical_team_name(match.get("home")),
        "away": canonical_team_name(match.get("away")),
        "home_score": none_or_int(match.get("home_score")),
        "away_score": none_or_int(match.get("away_score")),
        "status": str(match.get("status") or "Scheduled"),
        "score_node": score_node,
        "goals": [normalize_goal_event(goal) for goal in goals],
    }


def none_or_int(value):
    if value in [None, "", "None", "TBD", "-"]:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_player_stats(raw_stats, players):
    stats = {}
    raw_stats = raw_stats if isinstance(raw_stats, dict) else {}
    for player in players:
        prior = raw_stats.get(player) if isinstance(raw_stats.get(player), dict) else {}
        stats[player] = {
            "goals": none_or_int(prior.get("goals")) or 0,
            "assists": none_or_int(prior.get("assists")) or 0,
            "group_goals": none_or_int(prior.get("group_goals")) or 0,
            "group_assists": none_or_int(prior.get("group_assists")) or 0,
        }
    return stats


def extract_score_node(match):
    score = match.get("score") if isinstance(match.get("score"), dict) else {}
    full_time = score.get("fullTime") if isinstance(score.get("fullTime"), dict) else {}
    regular_time = score.get("regularTime") if isinstance(score.get("regularTime"), dict) else {}
    penalties = score.get("penalties") if isinstance(score.get("penalties"), dict) else {}
    return {
        "winner": score.get("winner"),
        "full_time": {
            "home": none_or_int(full_time.get("home")),
            "away": none_or_int(full_time.get("away")),
        },
        "regular_time": {
            "home": none_or_int(regular_time.get("home")),
            "away": none_or_int(regular_time.get("away")),
        },
        "penalties": {
            "home": none_or_int(penalties.get("home")),
            "away": none_or_int(penalties.get("away")),
        },
    }


def normalize_goal_event(goal):
    goal = goal if isinstance(goal, dict) else {}
    scorer = goal.get("scorer") if isinstance(goal.get("scorer"), dict) else {}
    assist = goal.get("assist") if isinstance(goal.get("assist"), dict) else {}
    team = goal.get("team") if isinstance(goal.get("team"), dict) else {}
    return {
        "minute": none_or_int(goal.get("minute")),
        "injury_time": none_or_int(goal.get("injuryTime")),
        "type": str(goal.get("type") or ""),
        "team": canonical_team_name(team.get("name") or team.get("shortName")),
        "scorer": str(scorer.get("name") or "").strip(),
        "assist": str(assist.get("name") or "").strip(),
    }


def parse_match_payload_item(item, index):
    score_node = extract_score_node(item)
    full_time = score_node["full_time"]
    goals = [normalize_goal_event(goal) for goal in (item.get("goals") or []) if isinstance(goal, dict)]
    return normalize_match(
        {
            "id": str(item.get("id") or f"match-{index + 1:03d}"),
            "date": str(item.get("utcDate") or ""),
            "stage": str(item.get("stage") or "GROUP_STAGE").replace("_", " ").title(),
            "home": (item.get("homeTeam") or {}).get("name"),
            "away": (item.get("awayTeam") or {}).get("name"),
            "home_score": full_time.get("home"),
            "away_score": full_time.get("away"),
            "status": str(item.get("status") or "Scheduled").title(),
            "score_node": score_node,
            "goals": goals,
            "group": item.get("group"),
            "matchday": item.get("matchday"),
        },
        index,
    )


def parse_friendly_match_payload_item(item, index):
    match = parse_match_payload_item(item, index)
    competition = item.get("competition") if isinstance(item.get("competition"), dict) else {}
    competition_name = str(competition.get("name") or "").strip()
    stage = str(match.get("stage") or "")
    if "friendly" in competition_name.lower() or "friendly" in stage.lower():
        match["stage"] = "FRIENDLY"
    else:
        match["stage"] = f"FRIENDLY - {competition_name or stage or 'International'}"
    return normalize_match(match, index)


def github_file_url():
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{STATE_FILE_PATH}"


def load_state_from_github(show_warning=True):
    if not GITHUB_TOKEN:
        try:
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as state_file:
                return normalize_state(json.load(state_file)), None
        except Exception as exc:
            if show_warning:
                st.warning(f"Could not load local {STATE_FILE_PATH}: {exc}")
            return default_state(), None

    try:
        resp = requests.get(github_file_url(), headers=GITHUB_HEADERS, timeout=10)
        if resp.status_code == 200:
            payload = resp.json()
            content = base64.b64decode(payload["content"]).decode("utf-8")
            return normalize_state(json.loads(content)), payload["sha"]
        if resp.status_code == 404:
            return default_state(), None
        if show_warning:
            st.warning(f"Could not load {STATE_FILE_PATH}. Status code: {resp.status_code}")
    except Exception as exc:
        if show_warning:
            st.warning(f"Could not load {STATE_FILE_PATH}: {exc}")
    return default_state(), None


def save_state_to_github(state, sha, message_prefix="Update draft state"):
    state = normalize_state(state)
    if not GITHUB_TOKEN:
        try:
            with open(STATE_FILE_PATH, "w", encoding="utf-8") as state_file:
                json.dump(state, state_file, indent=2, ensure_ascii=False)
            return True
        except Exception as exc:
            st.error(f"Could not save local {STATE_FILE_PATH}: {exc}")
            return False

    content_str = json.dumps(state, indent=2, ensure_ascii=False)
    payload = {
        "message": f"{message_prefix} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": base64.b64encode(content_str.encode("utf-8")).decode("utf-8"),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    try:
        resp = requests.put(github_file_url(), headers=GITHUB_HEADERS, json=payload, timeout=15)
        return resp.status_code in [200, 201]
    except Exception:
        return False


def mutate_shared_state(mutator, message_prefix):
    for _ in range(3):
        fresh_state, fresh_sha = load_state_from_github(show_warning=False)
        result = mutator(fresh_state)
        if result is False:
            return False, fresh_state
        if save_state_to_github(fresh_state, fresh_sha, message_prefix):
            return result, fresh_state
        time.sleep(0.5)
    st.error("Could not save after retrying. Please try again.")
    return False, None


@lru_cache(maxsize=96)
def _image_to_data_uri_cached(path, modified_at):
    mime_type = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


@lru_cache(maxsize=128)
def _resized_image_to_data_uri_cached(path, modified_at, max_width, max_height, quality):
    if Image is None:
        return _image_to_data_uri_cached(path, modified_at)
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_width, max_height), Image.LANCZOS)
        output = BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def image_to_data_uri(path, max_width=None, max_height=None, quality=78):
    try:
        abs_path = os.path.abspath(path)
        modified_at = os.path.getmtime(abs_path)
        if max_width and max_height:
            return _resized_image_to_data_uri_cached(abs_path, modified_at, int(max_width), int(max_height), int(quality))
        return _image_to_data_uri_cached(abs_path, modified_at)
    except OSError:
        return ""


def top_thumbnail_html():
    data_uri = image_to_data_uri(TITLE_THUMBNAIL_PATH, max_width=960, max_height=320, quality=72)
    if not data_uri:
        return ""
    return f"<div class='top-thumbnail-wrap'><img class='top-thumbnail' src='{html.escape(data_uri, quote=True)}' alt='World Cup FC'></div>"


def coach_image_html(coach, color):
    image_path = coach_photo_filename(coach)
    data_uri = image_to_data_uri(image_path, max_width=120, max_height=120, quality=76)
    if data_uri:
        return f"<img class='coach-face' src='{html.escape(data_uri, quote=True)}' alt=''>"
    return f"<div class='coach-face-placeholder'>{html.escape(coach)}</div>"


def pick_by_number(picks):
    return {pick["pick"]: pick for pick in picks}


def current_pick(sequence, picks):
    if len(picks) >= len(sequence):
        return None
    return sequence[len(picks)]


def team_draft_complete(state):
    return len(state.get("team_picks", [])) >= len(TEAM_DRAFT_SEQUENCE)


def player_draft_complete(state):
    return len(state.get("player_picks", [])) >= len(PLAYER_DRAFT_SEQUENCE)


def full_draft_complete(state):
    return team_draft_complete(state) and player_draft_complete(state)


def drafted_teams(state):
    return {pick["team"] for pick in state.get("team_picks", [])}


def drafted_players(state):
    return {pick["player"] for pick in state.get("player_picks", [])}


def score_match_for_team(match, team_name):
    if "friendly" in str(match.get("stage") or "").lower():
        return 0
    home = canonical_team_name(match.get("home"))
    away = canonical_team_name(match.get("away"))
    if team_name not in [home, away]:
        return 0
    home_score = match.get("home_score")
    away_score = match.get("away_score")
    if home_score is None or away_score is None:
        return 0
    status = str(match.get("status", "")).lower()
    if status in ["scheduled", "timed", "postponed", "cancelled", "canceled", "suspended"]:
        return 0
    goals_for = home_score if team_name == home else away_score
    goals_against = away_score if team_name == home else home_score
    result_points = 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0
    clean_sheet = 1 if goals_against == 0 else 0
    return result_points + goals_for + clean_sheet


def stage_is_group(stage):
    return "group" in str(stage or "").lower()


def team_goals_in_matches(matches, team_name):
    goals = 0
    for match in matches:
        if "friendly" in str(match.get("stage") or "").lower():
            continue
        if match.get("home") == team_name and match.get("home_score") is not None:
            goals += int(match.get("home_score") or 0)
        if match.get("away") == team_name and match.get("away_score") is not None:
            goals += int(match.get("away_score") or 0)
    return goals


def team_fantasy_points(state, team_name):
    team_name = canonical_team_name(team_name)
    match_points = sum(score_match_for_team(match, team_name) for match in state.get("matches", []))
    advancement = state["advancement"].get(team_name, "Group Stage")
    return match_points + ADVANCEMENT_BONUSES.get(advancement, 0)


def cinderella_team_rows(state):
    rows = []
    for coach, data in state["teams"].items():
        for team_name in data.get("national_teams", []):
            current = team_fantasy_points(state, team_name)
            baseline = fifa_expected_points(team_name)
            rows.append(
                {
                    "coach": coach,
                    "coach_name": data.get("team_name") or coach,
                    "color": data.get("color") or "#FFD54A",
                    "team": team_name,
                    "rank": FIFA_RANKINGS.get(team_name, {}).get("rank"),
                    "baseline": baseline,
                    "current": current,
                    "cinderella": current - baseline,
                }
            )
    return sorted(rows, key=lambda item: (item["cinderella"], item["current"]), reverse=True)


def calculate_scores(state):
    matches = state.get("matches", [])
    scores = {}
    for coach, data in state["teams"].items():
        team_points = 0
        group_stage_points = 0
        empire_count = 0
        empire_goals = 0
        team_breakdown = []
        best_cinderella = None
        for team_name in data.get("national_teams", []):
            group_points = sum(score_match_for_team(match, team_name) for match in matches if stage_is_group(match.get("stage")))
            advancement = state["advancement"].get(team_name, "Group Stage")
            total = team_fantasy_points(state, team_name)
            baseline = fifa_expected_points(team_name)
            cinderella = total - baseline
            team_points += total
            group_stage_points += group_points
            if advancement in ["Round of 16", "Quarterfinals", "Semifinals", "Final", "Champion"]:
                empire_count += 1
                empire_goals += team_goals_in_matches(matches, team_name)
            team_breakdown.append((team_name, total, baseline, cinderella))
            if best_cinderella is None or cinderella > best_cinderella["cinderella"]:
                best_cinderella = {"team": team_name, "current": total, "baseline": baseline, "cinderella": cinderella}

        player_points = 0
        player_group_points = 0
        player_breakdown = []
        for player in data.get("star_players", []):
            stats = state["player_stats"].get(player, {})
            points = int(stats.get("goals", 0)) * 4 + int(stats.get("assists", 0)) * 3
            group_points = int(stats.get("group_goals", 0)) * 4 + int(stats.get("group_assists", 0)) * 3
            player_points += points
            player_group_points += group_points
            player_breakdown.append((player, points))

        total_points = team_points + player_points
        scores[coach] = {
            "coach": coach,
            "color": data["color"],
            "display_name": data.get("team_name") or coach,
            "team_points": team_points,
            "player_points": player_points,
            "total_points": total_points,
            "group_stage_points": group_stage_points + player_group_points,
            "empire_count": empire_count,
            "empire_goals": empire_goals,
            "cinderella": best_cinderella["cinderella"] if best_cinderella else 0,
            "cinderella_team": best_cinderella["team"] if best_cinderella else "",
            "fifa_expected": best_cinderella["baseline"] if best_cinderella else 0,
            "team_breakdown": team_breakdown,
            "player_breakdown": player_breakdown,
        }
    return scores


def ordered_scores(scores):
    return sorted(scores.values(), key=lambda item: item["total_points"], reverse=True)


def award_leaders(scores):
    values = list(scores.values())
    if not values:
        return {}
    leaders = {}
    if max(item.get("group_stage_points", 0) for item in values) > 0:
        leaders["Group Stage Winner"] = max(values, key=lambda item: item["group_stage_points"])
    if max(item.get("empire_count", 0) for item in values) > 0:
        leaders["Empire Builder"] = max(values, key=lambda item: (item["empire_count"], item["empire_goals"], item["total_points"]))
    cinderella_candidates = [item for item in values if item.get("cinderella_team") and item.get("cinderella", 0) > 0]
    if cinderella_candidates:
        leaders["Cinderella Award"] = max(cinderella_candidates, key=lambda item: item["cinderella"])
    return leaders


@st.cache_data(ttl=180, show_spinner=False)
def fetch_matches_from_football_data(token):
    if not token:
        return []
    headers = {"X-Auth-Token": token, "X-Unfold-Goals": "true"}
    resp = requests.get(
        "https://api.football-data.org/v4/competitions/WC/matches",
        headers=headers,
        params={"season": "2026"},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    return [
        parse_match_payload_item(item, index)
        for index, item in enumerate(payload.get("matches", []))
        if (item.get("homeTeam") or {}).get("name") and (item.get("awayTeam") or {}).get("name")
    ]


@st.cache_data(ttl=180, show_spinner=False)
def fetch_friendly_matches_from_football_data(token):
    if not token:
        return []
    headers = {"X-Auth-Token": token, "X-Unfold-Goals": "true"}
    team_names = {team["name"] for team in WORLD_CUP_TEAMS}
    teams_resp = requests.get(
        "https://api.football-data.org/v4/competitions/WC/teams",
        headers=headers,
        params={"season": "2026"},
        timeout=15,
    )
    teams_resp.raise_for_status()
    team_payload = teams_resp.json()
    team_ids = {}
    for item in team_payload.get("teams", []):
        team_id = item.get("id")
        team_name = canonical_team_name(item.get("name"))
        if team_name in team_names and team_id:
            team_ids[team_name] = int(team_id)
    if not team_ids:
        raise RuntimeError("Football-Data returned no World Cup team ids for friendly lookup.")

    matches_by_id = {}
    for team_name, team_id in team_ids.items():
        resp = requests.get(
            f"https://api.football-data.org/v4/teams/{team_id}/matches",
            headers=headers,
            params={"dateFrom": "2026-05-15", "dateTo": "2026-06-12", "limit": 100},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        for item in payload.get("matches", []):
            competition = item.get("competition") if isinstance(item.get("competition"), dict) else {}
            competition_name = str(competition.get("name") or "").strip()
            competition_code = str(competition.get("code") or "").strip().upper()
            stage = str(item.get("stage") or "")
            home = canonical_team_name((item.get("homeTeam") or {}).get("name"))
            away = canonical_team_name((item.get("awayTeam") or {}).get("name"))
            if home not in team_names and away not in team_names:
                continue
            if competition_code == "WC":
                continue
            match = parse_friendly_match_payload_item(item, len(matches_by_id))
            if "friendly" not in f"{competition_name} {stage}".lower():
                match["stage"] = f"FRIENDLY - {competition_name or 'International'}"
            matches_by_id[match["id"]] = match
    return sorted(matches_by_id.values(), key=lambda match: match.get("date") or "")


@st.cache_data(ttl=180, show_spinner=False)
def fetch_scorers_from_football_data(token):
    if not token:
        return {}
    headers = {"X-Auth-Token": token}
    resp = requests.get(
        "https://api.football-data.org/v4/competitions/WC/scorers",
        headers=headers,
        params={"season": "2026", "limit": 100},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    scorers = {}
    for item in payload.get("scorers", []):
        player = item.get("player") if isinstance(item.get("player"), dict) else {}
        name = str(player.get("name") or "").strip()
        if not name:
            continue
        scorers[name] = {
            "goals": none_or_int(item.get("goals")) or 0,
            "assists": none_or_int(item.get("assists")) or 0,
        }
    return scorers


def stage_to_advancement(stage):
    key = clean_key(str(stage or "").replace("_", " "))
    if key in ["last 32", "round of 32"]:
        return "Round of 32"
    if key in ["last 16", "round of 16"]:
        return "Round of 16"
    if key in ["quarter finals", "quarterfinals", "quarter finals"]:
        return "Quarterfinals"
    if key in ["semi finals", "semifinals"]:
        return "Semifinals"
    if key == "final":
        return "Final"
    return ""


def advancement_rank(level):
    return ADVANCEMENT_LEVELS.index(level) if level in ADVANCEMENT_LEVELS else 0


def derive_advancement_from_matches(matches):
    advancement = {team["name"]: "Group Stage" for team in WORLD_CUP_TEAMS}
    for match in matches:
        stage_level = stage_to_advancement(match.get("stage"))
        if not stage_level:
            continue
        for team_name in [match.get("home"), match.get("away")]:
            team_name = canonical_team_name(team_name)
            if team_name and advancement_rank(stage_level) > advancement_rank(advancement.get(team_name, "Group Stage")):
                advancement[team_name] = stage_level
        if stage_level == "Final" and str(match.get("status", "")).lower() in ["finished", "final", "post", "complete", "completed"]:
            winner = match_winner_team(match)
            if winner:
                advancement[winner] = "Champion"
    return advancement


def match_winner_team(match):
    score_node = match.get("score_node") if isinstance(match.get("score_node"), dict) else {}
    winner = str(score_node.get("winner") or "").upper()
    if winner == "HOME_TEAM":
        return canonical_team_name(match.get("home"))
    if winner == "AWAY_TEAM":
        return canonical_team_name(match.get("away"))
    home_score = match.get("home_score")
    away_score = match.get("away_score")
    if home_score is None or away_score is None:
        return ""
    if home_score > away_score:
        return canonical_team_name(match.get("home"))
    if away_score > home_score:
        return canonical_team_name(match.get("away"))
    return ""


def player_stats_from_matches(matches, players):
    stats = {player: {"goals": 0, "assists": 0, "group_goals": 0, "group_assists": 0} for player in players}
    for match in matches:
        if "friendly" in str(match.get("stage") or "").lower():
            continue
        is_group = stage_is_group(match.get("stage"))
        for goal in match.get("goals", []):
            scorer = match_player_to_pool(goal.get("scorer"), players)
            if scorer:
                stats[scorer]["goals"] += 1
                if is_group:
                    stats[scorer]["group_goals"] += 1
            assist = match_player_to_pool(goal.get("assist"), players)
            if assist:
                stats[assist]["assists"] += 1
                if is_group:
                    stats[assist]["group_assists"] += 1
    return stats


def merge_scorer_aggregates(stats, scorers, players):
    merged = copy.deepcopy(stats)
    for api_name, values in scorers.items():
        player = match_player_to_pool(api_name, players)
        if not player:
            continue
        merged[player]["goals"] = max(merged[player]["goals"], int(values.get("goals", 0)))
        merged[player]["assists"] = max(merged[player]["assists"], int(values.get("assists", 0)))
    return merged


def refresh_api_scores():
    def mutator(state):
        state = normalize_state(state)
        state["last_score_refresh_attempt_at"] = int(time.time())
        try:
            matches = fetch_matches_from_football_data(FOOTBALL_DATA_TOKEN)
            state["last_friendly_api_error"] = ""
            matches = sorted(
                [match for match in matches if "friendly" not in str(match.get("stage") or "").lower()],
                key=lambda match: match.get("date") or "",
            )
            if matches:
                state["matches"] = matches
                match_stats = player_stats_from_matches(matches, state["players"])
                try:
                    scorers = fetch_scorers_from_football_data(FOOTBALL_DATA_TOKEN)
                except Exception:
                    scorers = {}
                state["player_stats"] = merge_scorer_aggregates(match_stats, scorers, state["players"])
                state["advancement"] = derive_advancement_from_matches(matches)
                state["last_score_refresh_at"] = int(time.time())
                state["last_api_error"] = ""
                return True
            state["last_api_error"] = "No Football-Data token configured or no matches returned."
            return True
        except Exception as exc:
            state["last_api_error"] = str(exc)
            return True

    return mutate_shared_state(mutator, "Refresh World Cup match data")


def render_header(state):
    st.markdown(top_thumbnail_html(), unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="hero-title">
  <div>
    <div class="hero-kicker">Fantasy Challenge</div>
    <h1>{html.escape(state.get("app_title") or "World Cup FC")}</h1>
  </div>
  <div class="deadline-pill">Draft locks before {html.escape(KICKOFF_DEADLINE)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_payout_descriptions():
    with st.expander("Payout Descriptions", expanded=False):
        st.markdown(
            f"""
<div class='payout-desc'><b>Gold - $300</b><br>
Awarded to the coach who finishes first overall in total fantasy points. Total fantasy points are the sum of every drafted national team's match points and advancement bonuses plus every drafted star player's goal and assist points. National teams earn 3 points for a win, 1 for a draw, 1 for each goal scored, and 1 for a clean sheet. Players earn 4 points per goal and 3 per assist.</div>

<div class='payout-desc'><b>Silver - $150</b><br>
Awarded to the coach who finishes second overall by total fantasy points, using the same full-tournament scoring calculation as Gold.</div>

<div class='payout-desc'><b>Bronze - $100</b><br>
Awarded to the coach who finishes third overall by total fantasy points, using the same full-tournament scoring calculation as Gold and Silver.</div>

<div class='payout-desc'><b>Group Stage Winner - $90</b><br>
Awarded to the coach with the most fantasy points earned during group-stage matches only. This includes group-stage national-team match points plus group-stage star-player goals and assists. Knockout advancement bonuses and knockout player production do not count for this side bet.</div>

<div class='payout-desc'><b>Empire Builder - $80</b><br>
Awarded to the coach with the most drafted national teams that reach the Round of 16 or later. The app counts each drafted team whose advancement status is Round of 16, Quarterfinals, Semifinals, Final, or Champion. If coaches are tied on teams advanced, the tiebreaker is total goals scored by those advanced teams.</div>

<div class='payout-desc'><b>Cinderella Award - $80</b><br>
Awarded to the coach who owns the single drafted national team with the largest overperformance against its locked FIFA ranking baseline. This is not a coach portfolio total. For each drafted team, the app calculates: current team fantasy points minus FIFA expected points. FIFA expected points are locked from the {html.escape(FIFA_RANKING_LOCK_DATE)} FIFA/Coca-Cola Men's World Ranking and scaled across the 48 qualified World Cup teams. The team with the highest positive delta wins the award for its coach.</div>
""",
            unsafe_allow_html=True,
        )


def render_standings(state, scores):
    st.markdown("<div class='section-title'>Standings</div>", unsafe_allow_html=True)
    leaders = award_leaders(scores)
    rank_by_coach = {item["coach"]: index + 1 for index, item in enumerate(ordered_scores(scores))}
    cards = ["<div class='standings-grid'>"]
    for item in ordered_scores(scores):
        coach = item["coach"]
        color = item["color"]
        coach_state = state["teams"][coach]
        teams = ", ".join(display_team_html(team, include_info=False) for team in coach_state.get("national_teams", [])) or "No teams drafted yet"
        players = ", ".join(display_player_html(player, include_info=False) for player in coach_state.get("star_players", [])) or "No players drafted yet"
        badge = f"#{rank_by_coach[coach]}"
        if rank_by_coach[coach] == 1:
            badge = "Gold"
        awards = []
        for award_name, leader in leaders.items():
            if leader and leader["coach"] == coach:
                awards.append(award_name)
        award_html = "<div class='award-lines'></div>"
        if awards:
            award_html = "<div class='award-lines'>" + "".join(
                f"<div class='award-line'>{html.escape(award)}</div>" for award in awards
            ) + "</div>"
        cards.append(
            f"""
<div class='coach-card' style='--coach-color:{html.escape(color)}'>
  <div class='coach-head'>
    {coach_image_html(coach, color)}
    <div>
      <div class='coach-name'>{html.escape(item["display_name"])}</div>
      {award_html}
    </div>
    <div class='score-badge'>{int(item["total_points"])}</div>
  </div>
  <div class='metric-row'><span>Overall</span><b>{html.escape(badge)}</b></div>
  <div class='metric-row points-pair'><span>Team Points <b>{int(item["team_points"])}</b></span><span>Player Points <b>{int(item["player_points"])}</b></span></div>
  <div class='metric-row'><span>Group Stage</span><b>{int(item["group_stage_points"])}</b></div>
  <div class='metric-row'><span>Empire Builder</span><b>{int(item["empire_count"])} teams / {int(item["empire_goals"])} goals</b></div>
  <div class='metric-row'><span>Best Cinderella</span><b>{html.escape(item["cinderella_team"] or "None")} {item["cinderella"]:+.1f}</b></div>
  <div class='asset-list'><b>Teams:</b> {teams}</div>
  <div class='asset-list'><b>Players:</b> {players}</div>
</div>
"""
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def coach_mini_html(coach, color):
    image_path = coach_photo_filename(coach)
    data_uri = image_to_data_uri(image_path, max_width=44, max_height=44, quality=70)
    escaped_color = html.escape(color)
    if data_uri:
        return f"<img class='coach-mini-face' style='--coach-color:{escaped_color}' src='{html.escape(data_uri, quote=True)}' alt=''>"
    return f"<span class='coach-mini-placeholder' style='--coach-color:{escaped_color}'>{html.escape(coach[:1])}</span>"


def render_cinderella_standings(state):
    rows = cinderella_team_rows(state)[:10]
    st.markdown("<div class='section-title'>Cinderella Standings</div>", unsafe_allow_html=True)
    if not rows:
        st.caption("No drafted teams yet.")
        return
    html_rows = [
        "<table class='data-table'><thead><tr>"
        "<th>#</th><th>Team</th><th>Coach</th><th>FIFA</th><th>Baseline</th><th>Current</th><th>Cinderella</th>"
        "</tr></thead><tbody>"
    ]
    for index, row in enumerate(rows, start=1):
        color = html.escape(row["color"])
        html_rows.append(
            f"""
<tr>
  <td>{index}</td>
  <td>{display_team_html(row["team"], "", include_info=False)}</td>
  <td><span class='coach-dot' style='--coach-color:{color}'></span>{html.escape(row["coach_name"])}</td>
  <td>#{html.escape(str(row["rank"] or "n/a"))}</td>
  <td>{row["baseline"]:.1f}</td>
  <td>{row["current"]:.1f}</td>
  <td><b>{row["cinderella"]:+.1f}</b></td>
</tr>
"""
        )
    html_rows.append("</tbody></table>")
    st.markdown("".join(html_rows), unsafe_allow_html=True)


def drafted_player_rows(state):
    rows = []
    for coach, data in state["teams"].items():
        for player in data.get("star_players", []):
            stats = state["player_stats"].get(player, {})
            goals = int(stats.get("goals", 0))
            assists = int(stats.get("assists", 0))
            rows.append(
                {
                    "coach": coach,
                    "coach_name": data.get("team_name") or coach,
                    "color": data.get("color") or "#FFD54A",
                    "player": player,
                    "goals": goals,
                    "assists": assists,
                    "points": goals * 4 + assists * 3,
                }
            )
    return sorted(rows, key=lambda item: (item["points"], item["goals"], item["assists"], item["player"]), reverse=True)


def render_drafted_player_stats(state):
    rows = drafted_player_rows(state)
    st.markdown("<div class='section-title'>Drafted Player Stats</div>", unsafe_allow_html=True)
    if not rows:
        st.caption("No players drafted yet.")
        return
    html_rows = [
        "<table class='data-table'><thead><tr>"
        "<th>Player</th><th>Coach</th><th>Goals</th><th>Assists</th><th>Total</th>"
        "</tr></thead><tbody>"
    ]
    for row in rows:
        color = html.escape(row["color"])
        html_rows.append(
            f"""
<tr>
  <td>{display_player_html(row["player"], include_info=True)}</td>
  <td><span class='coach-dot' style='--coach-color:{color}'></span>{html.escape(row["coach_name"])}</td>
  <td>{row["goals"]}</td>
  <td>{row["assists"]}</td>
  <td><b>{row["points"]}</b></td>
</tr>
"""
        )
    html_rows.append("</tbody></table>")
    st.markdown("".join(html_rows), unsafe_allow_html=True)


def match_is_completed(match):
    status = str(match.get("status") or "").lower()
    if status in ["scheduled", "timed", "postponed", "cancelled", "canceled", "suspended"]:
        return False
    return match.get("home_score") is not None and match.get("away_score") is not None


def match_group_label(match):
    raw_group = str(match.get("group") or "").strip()
    if raw_group:
        cleaned = raw_group.replace("_", " ").strip()
        match_obj = re.search(r"\bGroup\s+([A-Z0-9]+)\b", cleaned, flags=re.IGNORECASE)
        if match_obj:
            return match_obj.group(1).upper()
        if len(cleaned) <= 3:
            return cleaned.upper()
    stage = str(match.get("stage") or "").strip()
    match_obj = re.search(r"\bGroup\s+([A-Z0-9]+)\b", stage, flags=re.IGNORECASE)
    return match_obj.group(1).upper() if match_obj else ""


def team_group_label(state, team_name):
    team_name = canonical_team_name(team_name)
    for match in state.get("matches", []):
        if not stage_is_group(match.get("stage")):
            continue
        if team_name in [canonical_team_name(match.get("home")), canonical_team_name(match.get("away"))]:
            group = match_group_label(match)
            if group:
                return group
    return "TBD"


def team_record_and_result_points(state, team_name):
    team_name = canonical_team_name(team_name)
    wins = draws = losses = result_points = 0
    for match in state.get("matches", []):
        if "friendly" in str(match.get("stage") or "").lower():
            continue
        home = canonical_team_name(match.get("home"))
        away = canonical_team_name(match.get("away"))
        if team_name not in [home, away] or not match_is_completed(match):
            continue
        home_score = int(match.get("home_score") or 0)
        away_score = int(match.get("away_score") or 0)
        goals_for = home_score if team_name == home else away_score
        goals_against = away_score if team_name == home else home_score
        if goals_for > goals_against:
            wins += 1
            result_points += 3
        elif goals_for == goals_against:
            draws += 1
            result_points += 1
        else:
            losses += 1
    return f"{wins}-{draws}-{losses}", result_points


def next_match_for_team(state, team_name):
    team_name = canonical_team_name(team_name)
    now = datetime.now(ZoneInfo("UTC"))
    candidates = []
    for match in state.get("matches", []):
        if "friendly" in str(match.get("stage") or "").lower():
            continue
        home = canonical_team_name(match.get("home"))
        away = canonical_team_name(match.get("away"))
        if team_name not in [home, away] or match_is_completed(match):
            continue
        date_text = str(match.get("date") or "")
        try:
            parsed = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        except Exception:
            parsed = datetime.max.replace(tzinfo=ZoneInfo("UTC"))
        if parsed >= now or parsed == datetime.max.replace(tzinfo=ZoneInfo("UTC")):
            candidates.append((parsed, match))
    if not candidates:
        return "TBD"
    _, match = sorted(candidates, key=lambda item: item[0])[0]
    opponent = canonical_team_name(match.get("away")) if canonical_team_name(match.get("home")) == team_name else canonical_team_name(match.get("home"))
    stage = str(match.get("stage") or "")
    return f"{flag_for_team(opponent)} {opponent} - {stage} - {format_match_date(match.get('date'))}"


def owned_players_for_team_html(state, team_name):
    team_name = canonical_team_name(team_name)
    rows = []
    for coach, data in state["teams"].items():
        color = data.get("color") or "#FFD54A"
        for player in data.get("star_players", []):
            if player_country(player) != team_name:
                continue
            stats = state["player_stats"].get(player, {})
            points = int(stats.get("goals", 0)) * 4 + int(stats.get("assists", 0)) * 3
            rows.append((points, f"{coach_mini_html(coach, color)}{html.escape(player_base_name(player))}"))
    if not rows:
        return "<span class='subtle'>None</span>"
    return ", ".join(item[1] for item in sorted(rows, key=lambda item: item[0], reverse=True)[:4])


def team_standings_rows(state):
    rows = []
    for team in WORLD_CUP_TEAMS:
        team_name = team["name"]
        coach = drafted_coach_for_team(state, team_name)
        coach_data = state["teams"].get(coach, {}) if coach else {}
        record, result_points = team_record_and_result_points(state, team_name)
        rows.append(
            {
                "team": team_name,
                "coach": coach,
                "coach_name": coach_data.get("team_name") or coach or "Undrafted",
                "coach_color": coach_data.get("color") or "#777777",
                "group": team_group_label(state, team_name),
                "record": record,
                "result_points": result_points,
                "next_match": next_match_for_team(state, team_name),
                "fifa_rank": FIFA_RANKINGS.get(team_name, {}).get("rank"),
                "team_points": team_fantasy_points(state, team_name),
                "players": owned_players_for_team_html(state, team_name),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            -int(item["result_points"]),
            -float(item["team_points"]),
            int(item["fifa_rank"] or 999),
            item["team"],
        ),
    )


def team_standings_table_html(rows):
    html_rows = [
        "<table class='data-table team-standings-table'><thead><tr>"
        "<th>Team</th><th>Coach</th><th>Group</th><th>Record</th><th>Points</th><th>FIFA</th>"
        "</tr></thead><tbody>"
    ]
    for row in rows:
        color = html.escape(row["coach_color"])
        coach_html = (
            f"<span class='coach-dot' style='--coach-color:{color}'></span>{html.escape(row['coach_name'])}"
            if row["coach"]
            else "<span class='subtle'>Undrafted</span>"
        )
        html_rows.append(
            f"""
<tr class='team-main-row'>
  <td class='team-name-cell'>{display_team_html(row["team"], "", include_info=True)}</td>
  <td>{coach_html}</td>
  <td>{html.escape(row["group"])}</td>
  <td>{html.escape(row["record"])}</td>
  <td>{int(row["result_points"])}</td>
  <td>#{html.escape(str(row["fifa_rank"] or "n/a"))}</td>
</tr>
<tr class='team-detail-row'>
  <td colspan='6'>
    <div class='team-detail-grid'>
      <span><b>Next:</b> {html.escape(row["next_match"])}</span>
      <span><b>Owned:</b> {row["players"]}</span>
    </div>
  </td>
</tr>
"""
        )
    html_rows.append("</tbody></table>")
    return "".join(html_rows)


def render_team_standings(state):
    rows = team_standings_rows(state)
    st.markdown("<div class='section-title'>Team Standings</div>", unsafe_allow_html=True)
    st.caption(
        f"FIFA rank is the locked {FIFA_RANKING_LOCK_DATE} FIFA/Coca-Cola men's world ranking. "
        "FIFA determines it from national-team results and ranking points; this app keeps that baseline fixed for the tournament."
    )
    st.markdown(team_standings_table_html(rows[:10]), unsafe_allow_html=True)
    if len(rows) > 10:
        with st.expander("More Teams", expanded=False):
            st.markdown(team_standings_table_html(rows[10:]), unsafe_allow_html=True)


def draft_total_for_stage(stage_label):
    return len(TEAM_DRAFT_SEQUENCE) if stage_label == "Team" else len(TEAM_DRAFT_SEQUENCE) + len(PLAYER_DRAFT_SEQUENCE)


def render_pick_timer(stage_label, current, color, started_at):
    total_picks = draft_total_for_stage(stage_label)
    payload = {
        "stage": str(stage_label),
        "pick": int(current["pick"]),
        "total": int(total_picks),
        "coach": str(current["coach"]),
        "color": str(color),
        "startedAt": int(started_at),
    }
    components.html(
        f"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
html, body {{
  margin:0;
  padding:0;
  background:#000;
  color:#fff;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
body {{ padding:10px 0 8px; }}
.current-pick-box {{
  box-sizing:border-box;
  width:100%;
  border:3px solid {html.escape(payload["color"])};
  box-shadow:0 0 18px {html.escape(payload["color"])};
  border-radius:8px;
  padding:12px;
  margin:0;
  text-align:center;
  font-size:clamp(1.05rem, 4vw, 1.65rem);
  line-height:1.2;
  font-weight:1000;
}}
.accent {{ color:{html.escape(payload["color"])}; }}
</style>
</head>
<body>
<div class="current-pick-box">
  {html.escape(payload["stage"])} Pick {payload["pick"]} of {payload["total"]}: <span class="accent">{html.escape(payload["coach"])}</span> is On The Clock
  <span class="accent">🕒 <span id="timer">00:00:00</span></span>
</div>
<script>
const startedAt = {payload["startedAt"]};
const timer = document.getElementById("timer");
function pad(value) {{
  return String(value).padStart(2, "0");
}}
function tick() {{
  const elapsed = Math.max(0, Math.floor(Date.now() / 1000) - startedAt);
  const hours = Math.floor(elapsed / 3600);
  const minutes = Math.floor((elapsed % 3600) / 60);
  const seconds = elapsed % 60;
  timer.textContent = `${{pad(hours)}}:${{pad(minutes)}}:${{pad(seconds)}}`;
}}
tick();
setInterval(tick, 1000);
</script>
</body>
</html>
""",
        height=112,
    )


def button_text_color_for_background(color):
    value = str(color or "").strip().lstrip("#")
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        return "#F5F5F5"
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    luminance = (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)
    return "#111111" if luminance >= 170 else "#F5F5F5"


def render_draft_status(stage_label, current, state):
    if current:
        color = state["teams"][current["coach"]]["color"]
        try:
            started_at = int(state.get("current_pick_started_at") or time.time())
        except (TypeError, ValueError):
            started_at = int(time.time())
        render_pick_timer(stage_label, current, color, started_at)
    st.markdown(
        f"<div class='draft-status-line'><b>Deadline:</b> {html.escape(KICKOFF_DEADLINE)} <b>Status:</b> {'Live' if state.get('draft_active') else 'Paused'}</div>",
        unsafe_allow_html=True,
    )


def set_draft_active(active):
    def mutator(state):
        state = normalize_state(state)
        state["draft_enabled"] = True
        state["draft_active"] = bool(active)
        if active:
            state["current_pick_started_at"] = int(time.time())
        return True
    return mutate_shared_state(mutator, "Update draft status")


def set_draft_enabled(enabled):
    def mutator(state):
        state = normalize_state(state)
        state["draft_enabled"] = bool(enabled)
        if not enabled:
            state["draft_active"] = False
        return True
    return mutate_shared_state(mutator, "Update draft visibility")


def undo_last_pick():
    def mutator(state):
        state = normalize_state(state)
        if state.get("player_picks"):
            state["player_picks"].pop()
        elif state.get("team_picks"):
            state["team_picks"].pop()
        else:
            return False
        apply_picks_to_rosters(state)
        state["current_pick_started_at"] = int(time.time())
        return True
    return mutate_shared_state(mutator, "Undo last draft pick")


def reset_rosters_and_draft():
    def mutator(state):
        state = normalize_state(state)
        state["team_picks"] = []
        state["player_picks"] = []
        for coach in COACHES:
            state["teams"][coach]["national_teams"] = []
            state["teams"][coach]["star_players"] = []
        state["current_pick_started_at"] = int(time.time())
        return True
    return mutate_shared_state(mutator, "Reset rosters and draft picks")


def rerun_draft_scope():
    st.rerun()


def save_draft_pick(action, value, label, status_placeholder=None):
    st.session_state["draft_saving"] = True
    st.toast("Updating roster...")
    if status_placeholder is not None:
        status_placeholder.markdown("<div class='draft-save-note'>Updating roster...</div>", unsafe_allow_html=True)
    with st.spinner("Updating roster and saving pick..."):
        ok, _ = action(value)
    if ok:
        st.session_state["draft_saving"] = False
        rerun_draft_scope()
    st.session_state["draft_saving"] = False
    st.warning(f"Could not save {label}. It may already be drafted, or the draft may be paused.")


def render_draft_controls(state, key_prefix="draft-controls"):
    draft_live = bool(state.get("draft_active"))
    has_any_picks = bool(state.get("team_picks") or state.get("player_picks"))
    st.markdown("<div class='draft-control-row'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1], gap="small")
    with c1:
        st.markdown("<div class='draft-start-control'>", unsafe_allow_html=True)
        if st.button("Start Draft", key=f"{key_prefix}-start", width="stretch", disabled=draft_live):
            ok, _ = set_draft_active(True)
            if ok:
                rerun_draft_scope()
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='draft-stop-control'>", unsafe_allow_html=True)
        if st.button("Stop Draft", key=f"{key_prefix}-stop", width="stretch", disabled=not draft_live):
            ok, _ = set_draft_active(False)
            if ok:
                rerun_draft_scope()
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='draft-undo-control'>", unsafe_allow_html=True)
        if st.button("Undo Last Pick", key=f"{key_prefix}-undo", width="stretch", disabled=not has_any_picks):
            ok, _ = undo_last_pick()
            if ok:
                rerun_draft_scope()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_draft_board(title, sequence, picks, field, state):
    st.markdown(f"<div class='section-title'>{html.escape(title)}</div>", unsafe_allow_html=True)
    pick_map = pick_by_number(picks)
    rounds = max(item["round"] for item in sequence)
    rows = []
    rows.append("<div class='draft-board'><table><thead><tr>")
    rows.append("<th class='round-head'>Round</th>")
    for coach in COACHES:
        color = state["teams"][coach]["color"]
        rows.append(f"<th style='border-top:4px solid {html.escape(color)}'>{html.escape(coach)}</th>")
    rows.append("</tr></thead><tbody>")
    for round_number in range(1, rounds + 1):
        rows.append("<tr>")
        rows.append(f"<th class='round-head'>{round_number}</th>")
        for coach in COACHES:
            item = next(seq for seq in sequence if seq["round"] == round_number and seq["coach"] == coach)
            pick = pick_map.get(item["pick"])
            cell_color = state["teams"][item["coach"]]["color"]
            if pick:
                choice = pick[field]
                label = display_team_html(choice, include_info=False) if field == "team" else display_player_html(choice, include_info=False)
            else:
                label = "Open"
            rows.append(
                f"""
<td><div class='pick-cell' style='--coach-color:{html.escape(cell_color)}'>
  <div class='pick-num'>Pick {item["pick"]}</div>
  <div class='pick-choice'>{label}</div>
</div></td>
"""
            )
        rows.append("</tr>")
    rows.append("</tbody></table></div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def make_team_pick(team_name):
    def mutator(state):
        state = normalize_state(state)
        if not state.get("draft_enabled") or not state.get("draft_active"):
            return False
        pick = current_pick(TEAM_DRAFT_SEQUENCE, state["team_picks"])
        team_name_clean = canonical_team_name(team_name)
        if not pick or team_name_clean in drafted_teams(state):
            return False
        state["team_picks"].append(
            {
                "pick": pick["pick"],
                "round": pick["round"],
                "coach": pick["coach"],
                "team": team_name_clean,
                "picked_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
            }
        )
        apply_picks_to_rosters(state)
        state["current_pick_started_at"] = int(time.time())
        return True

    return mutate_shared_state(mutator, f"Draft {team_name}")


def make_player_pick(player):
    def mutator(state):
        state = normalize_state(state)
        if not state.get("draft_enabled") or not state.get("draft_active"):
            return False
        if not team_draft_complete(state):
            return False
        pick = current_pick(PLAYER_DRAFT_SEQUENCE, state["player_picks"])
        player_clean = str(player or "").strip()
        if not pick or player_clean in drafted_players(state):
            return False
        state["player_picks"].append(
            {
                "pick": pick["pick"],
                "round": pick["round"],
                "coach": pick["coach"],
                "player": player_clean,
                "picked_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
            }
        )
        apply_picks_to_rosters(state)
        state["current_pick_started_at"] = int(time.time())
        return True

    return mutate_shared_state(mutator, f"Draft {player}")


def render_available_teams(state):
    available = [team for team in WORLD_CUP_TEAMS if team["name"] not in drafted_teams(state)]
    saving = st.session_state.get("draft_saving", False)
    current = current_pick(TEAM_DRAFT_SEQUENCE, state["team_picks"])
    coach_color = state["teams"][current["coach"]]["color"] if current else "#FFD54A"
    button_text_color = button_text_color_for_background(coach_color)
    base_color = f"color-mix(in srgb, {coach_color} 34%, #101010)"
    hover_color = f"color-mix(in srgb, {coach_color} 48%, #101010)"
    st.markdown(
        f"""
<style>
.st-key-team-pick-buttons {{
    --draft-button-bg:{base_color};
    --draft-button-border:{coach_color};
    --draft-button-hover:{hover_color};
    --draft-button-fg:{button_text_color};
}}
</style>
""",
        unsafe_allow_html=True,
    )
    with st.container(key="team-pick-buttons"):
        for row_start in range(0, len(available), DRAFT_BUTTON_COLUMNS):
            cols = st.columns(DRAFT_BUTTON_COLUMNS, gap="small")
            for col, team in zip(cols, available[row_start:row_start + DRAFT_BUTTON_COLUMNS]):
                with col:
                    label = display_team(team["name"], state["odds"].get(team["name"], ""))
                    pressed = st.button(label, key=f"draft-team-{team['name']}", width="stretch", disabled=(not state.get("draft_active") or saving))
                    status_placeholder = st.empty()
                    if pressed:
                        save_draft_pick(make_team_pick, team["name"], label, status_placeholder=status_placeholder)


def render_available_players(state):
    used = drafted_players(state)
    available = [player for player in state["players"] if player not in used]
    saving = st.session_state.get("draft_saving", False)
    current = current_pick(PLAYER_DRAFT_SEQUENCE, state["player_picks"])
    coach_color = state["teams"][current["coach"]]["color"] if current else "#FFD54A"
    button_text_color = button_text_color_for_background(coach_color)
    base_color = f"color-mix(in srgb, {coach_color} 34%, #101010)"
    hover_color = f"color-mix(in srgb, {coach_color} 48%, #101010)"
    st.markdown(
        f"""
<style>
.st-key-player-pick-buttons {{
    --draft-button-bg:{base_color};
    --draft-button-border:{coach_color};
    --draft-button-hover:{hover_color};
    --draft-button-fg:{button_text_color};
}}
</style>
""",
        unsafe_allow_html=True,
    )
    with st.container(key="player-pick-buttons"):
        for row_start in range(0, len(available), DRAFT_BUTTON_COLUMNS):
            cols = st.columns(DRAFT_BUTTON_COLUMNS, gap="small")
            for col, player in zip(cols, available[row_start:row_start + DRAFT_BUTTON_COLUMNS]):
                with col:
                    label = display_player(player)
                    pressed = st.button(label, key=f"draft-player-{player}", width="stretch", disabled=(not state.get("draft_active") or saving))
                    status_placeholder = st.empty()
                    if pressed:
                        save_draft_pick(make_player_pick, player, label, status_placeholder=status_placeholder)


def render_drafts(state):
    if not state.get("draft_enabled") or full_draft_complete(state):
        return

    team_complete = team_draft_complete(state)
    team_pick = current_pick(TEAM_DRAFT_SEQUENCE, state["team_picks"])
    active_sequence = TEAM_DRAFT_SEQUENCE
    active_picks = state["team_picks"]
    active_stage = "Team"
    if team_complete:
        active_sequence = PLAYER_DRAFT_SEQUENCE
        active_picks = state["player_picks"]
        active_stage = "Player"
    active_pick = current_pick(active_sequence, active_picks)

    st.markdown("<div class='section-title'>Draft Room</div>", unsafe_allow_html=True)
    render_draft_status(active_stage, active_pick, state)
    st.markdown(
        "<div class='draft-help'>Tap a draft button once. The app will show \"Updating roster\" while it saves the pick and refreshes the board.</div>",
        unsafe_allow_html=True,
    )
    render_draft_controls(state, key_prefix=f"{active_stage.lower()}-draft-top")

    if not team_complete:
        render_draft_board("Team Draft", TEAM_DRAFT_SEQUENCE, state["team_picks"], "team", state)
        render_draft_status(active_stage, active_pick, state)
        render_available_teams(state)
        return

    if st.toggle("Show Completed Team Draft Board", value=False, key="show-completed-team-board"):
        render_draft_board("Team Draft", TEAM_DRAFT_SEQUENCE, state["team_picks"], "team", state)
    if not player_draft_complete(state):
        st.success("Team draft complete. Player draft is open.")

    render_draft_board("Player Draft", PLAYER_DRAFT_SEQUENCE, state["player_picks"], "player", state)
    render_draft_status(active_stage, active_pick, state)
    player_pick = current_pick(PLAYER_DRAFT_SEQUENCE, state["player_picks"])
    if player_pick:
        render_draft_controls(state, key_prefix="player-draft-bottom")
        render_available_players(state)


def drafted_coach_for_team(state, team_name):
    team_name = canonical_team_name(team_name)
    for coach, data in state["teams"].items():
        if team_name in data.get("national_teams", []):
            return coach
    return ""


def match_status_label(match):
    status = str(match.get("status") or "").strip()
    return "" if status.lower() == "timed" else status


def render_match_cards(state, matches, show_group=False):
    matches = [match for match in matches if "friendly" not in str(match.get("stage") or "").lower()]
    if not matches:
        st.caption("No matches in this section yet.")
        return
    cards = ["<div class='matches-grid'>"]
    for match in matches:
        home = canonical_team_name(match.get("home"))
        away = canonical_team_name(match.get("away"))
        home_coach = drafted_coach_for_team(state, home)
        away_coach = drafted_coach_for_team(state, away)
        score_text = "vs"
        if match.get("home_score") is not None and match.get("away_score") is not None:
            score_text = f"{match['home_score']} - {match['away_score']}"
        chips = []
        for team_name, coach in [(home, home_coach), (away, away_coach)]:
            if coach:
                color = state["teams"][coach]["color"]
                points = score_match_for_team(match, team_name)
                chips.append(
                    f"<span class='drafted-chip' style='--coach-color:{html.escape(color)}'>{html.escape(coach)} +{points}</span>"
                )
        date_text = format_match_date(match.get("date"))
        stage = str(match.get("stage") or "")
        if show_group and stage_is_group(stage):
            group = match_group_label(match)
            if group:
                stage = f"Group {group}"
        detail_parts = [stage, match_status_label(match), date_text]
        detail_text = " | ".join(html.escape(part) for part in detail_parts if part)
        cards.append(
            f"""
<div class='match-card'>
  <div class='match-line'>
    <span>{display_team_html(home, '', include_info=True)}</span>
    <span class='match-score'>{html.escape(score_text)}</span>
    <span>{display_team_html(away, '', include_info=True)}</span>
  </div>
  <div class='subtle'>{detail_text}</div>
  <div>{''.join(chips) or "<span class='subtle'>No drafted teams in this match yet.</span>"}</div>
</div>
"""
        )
    cards.append("</div>")
    st.markdown("".join(cards), unsafe_allow_html=True)


def match_section_name(match):
    stage = str(match.get("stage") or "")
    if "friendly" in stage.lower():
        return ""
    stage_level = stage_to_advancement(stage)
    if not stage_level and stage_is_group(stage):
        return "Group Stages"
    if stage_level == "Round of 32":
        return "Round of 32"
    if stage_level == "Round of 16":
        return "Round of 16"
    if stage_level == "Quarterfinals":
        return "Quarterfinals"
    if stage_level in ["Semifinals", "Final"]:
        return "Championship"
    return "Group Stages"


def render_group_stage_match_groups(state, matches):
    groups = {}
    for match in matches:
        group = match_group_label(match) or "TBD"
        groups.setdefault(group, []).append(match)
    if not groups:
        st.caption("No group-stage matches loaded yet.")
        return
    group_options = sorted(groups, key=lambda value: (value == "TBD", value))
    selected_group = st.selectbox("Group", group_options, key="match-tracker-group")
    render_match_cards(state, groups[selected_group], show_group=True)


def render_live_matches(state):
    st.markdown("<div class='match-section-spacer'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>World Cup Tracker</div>", unsafe_allow_html=True)
    with st.expander("Past, Present, and Live Matches", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            if st.button("Refresh Scores"):
                ok, _ = refresh_api_scores()
                if ok:
                    st.rerun()
        with c2:
            if state.get("last_score_refresh_at"):
                refreshed = datetime.fromtimestamp(int(state["last_score_refresh_at"]), tz=ZoneInfo("America/New_York"))
                st.caption(f"Last API refresh: {refreshed.strftime('%b %d, %I:%M %p ET')}")
            if state.get("last_api_error"):
                st.caption(state["last_api_error"])
        st.caption("Data provided by football-data.org")

        matches = sorted(
            [match for match in state.get("matches", []) if "friendly" not in str(match.get("stage") or "").lower()],
            key=lambda match: match.get("date") or "",
        )
        if not matches:
            st.info("No World Cup matches loaded yet. Configure Football-Data token or refresh scores.")
            return

        sections = {name: [] for name in ["Group Stages", "Round of 32", "Round of 16", "Quarterfinals", "Championship"]}
        for match in matches:
            section_name = match_section_name(match)
            if section_name in sections:
                sections[section_name].append(match)
        section_options = [name for name in sections if sections[name]]
        selected_section = st.selectbox("Match section", section_options or list(sections), key="match-tracker-section")
        if selected_section == "Group Stages":
            render_group_stage_match_groups(state, sections[selected_section])
        else:
            render_match_cards(state, sections[selected_section])


def format_match_date(value):
    text = str(value or "").strip()
    if not text:
        return "Date TBD"
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(ZoneInfo("America/New_York")).strftime("%b %d, %I:%M %p ET")
    except Exception:
        return text


def draft_status_summary(state):
    team_picks = len(state.get("team_picks", []))
    player_picks = len(state.get("player_picks", []))
    team_total = len(TEAM_DRAFT_SEQUENCE)
    player_total = len(PLAYER_DRAFT_SEQUENCE)
    teams_per_coach = team_total // len(COACHES)
    players_per_coach = player_total // len(COACHES)
    if full_draft_complete(state):
        return (
            "Completed",
            f"Full rosters are locked: {teams_per_coach} teams and {players_per_coach} players per coach "
            f"({team_picks}/{team_total} team picks, {player_picks}/{player_total} player picks).",
        )
    if state.get("draft_enabled") and state.get("draft_active"):
        current = current_pick(
            PLAYER_DRAFT_SEQUENCE if team_draft_complete(state) else TEAM_DRAFT_SEQUENCE,
            state["player_picks"] if team_draft_complete(state) else state["team_picks"],
        )
        on_clock = f" {current['coach']} is on the clock." if current else ""
        return (
            "On-going",
            f"{team_picks}/{team_total} team picks and {player_picks}/{player_total} player picks complete.{on_clock}",
        )
    if state.get("draft_enabled"):
        return (
            "Stopped",
            f"The draft room is enabled but paused at {team_picks}/{team_total} team picks and {player_picks}/{player_total} player picks.",
        )
    return (
        "Disabled",
        f"The draft room is hidden. Current progress: {team_picks}/{team_total} team picks and {player_picks}/{player_total} player picks.",
    )


def render_admin(state):
    st.markdown("<div class='section-title'>Admin</div>", unsafe_allow_html=True)
    if st.session_state.pop("clear_admin_password", False):
        st.session_state["admin-password-entry"] = ""
    if not st.session_state.get("admin_unlocked", False):
        with st.expander("Admin", expanded=False):
            password = st.text_input("Admin Password", type="password", key="admin-password-entry")
            if st.button("Unlock Admin", key="admin-unlock-button", width="stretch"):
                if password == "0102":
                    st.session_state["admin_unlocked"] = True
                    st.session_state["admin_open"] = True
                    st.rerun()
                else:
                    st.warning("Incorrect admin password.")
        return

    with st.expander("Admin", expanded=True):
        if st.button("Lock / Close Admin", key="admin-lock-button", width="stretch"):
            st.session_state["admin_unlocked"] = False
            st.session_state["admin_open"] = False
            st.session_state["clear_admin_password"] = True
            st.rerun()
        st.caption("Admin controls are open for this private league app.")

        status_label, status_text = draft_status_summary(state)
        st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
        st.subheader("Draft Controls")
        st.caption(f"Status: {status_label}")
        st.caption(status_text)
        st.caption("Draft order is fixed and intentionally not editable.")
        draft_live = bool(state.get("draft_active"))
        has_any_picks = bool(state.get("team_picks") or state.get("player_picks"))
        c1, c2, c3, c4 = st.columns(4, gap="small")
        with c1:
            if st.button("Enable Draft", key="admin-enable-draft"):
                ok, _ = set_draft_enabled(True)
                if ok:
                    st.rerun()
        with c2:
            if st.button("Disable Draft", key="admin-disable-draft"):
                ok, _ = set_draft_enabled(False)
                if ok:
                    st.rerun()
        with c3:
            if st.button("Start Draft", key="admin-start-draft", disabled=draft_live):
                ok, _ = set_draft_active(True)
                if ok:
                    st.rerun()
        with c4:
            if st.button("Stop Draft", key="admin-stop-draft", disabled=not draft_live):
                ok, _ = set_draft_active(False)
                if ok:
                    st.rerun()
        if st.button("Undo Last Pick", key="admin-undo-last-pick-top", width="stretch", disabled=not has_any_picks):
            ok, _ = undo_last_pick()
            if ok:
                st.rerun()

        st.markdown("**Protected Reset**")
        reset_confirmed = st.checkbox("I understand this clears every roster and every draft pick.", key="reset-rosters-confirm-checkbox")
        reset_text = st.text_input("Type RESET to confirm roster reset", key="reset-rosters-confirm-text")
        if st.button("Reset Rosters", key="admin-reset-rosters", disabled=not (reset_confirmed and reset_text.strip().upper() == "RESET")):
            ok, _ = reset_rosters_and_draft()
            if ok:
                st.session_state["admin_unlocked"] = False
                st.session_state["admin_open"] = False
                st.session_state["clear_admin_password"] = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
        st.subheader("Coach Colors")
        color_labels = [label for label, _ in TEAM_COLOR_OPTIONS]
        label_by_hex = {hex_value: label for label, hex_value in TEAM_COLOR_OPTIONS}
        color_by_label = {label: hex_value for label, hex_value in TEAM_COLOR_OPTIONS}
        changed_colors = {}
        for row_start in range(0, len(COACHES), 4):
            cols = st.columns(4, gap="small")
            for col, coach in zip(cols, COACHES[row_start:row_start + 4]):
                with col:
                    current_hex = state["teams"][coach]["color"]
                    selected = st.selectbox(
                        coach,
                        color_labels,
                        index=color_labels.index(label_by_hex.get(current_hex, color_labels[0])),
                        key=f"admin-color-{coach}",
                    )
                    changed_colors[coach] = color_by_label[selected]
        if st.button("Save Coach Colors"):
            def mutator(fresh):
                fresh = normalize_state(fresh)
                for coach, color in changed_colors.items():
                    fresh["teams"][coach]["color"] = color
                return True
            ok, _ = mutate_shared_state(mutator, "Update coach colors")
            if ok:
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("Emergency Manual Overrides", expanded=False):
            st.caption("Normal scoring is automatic from Football-Data. Use these only if the API is wrong, delayed, or unavailable.")

            st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
            st.subheader("Editable Player Pool")
            players_text = st.text_area("25 players, one per line", value="\n".join(state["players"]), height=260)
            if st.button("Save Player Pool"):
                players = [line.strip() for line in players_text.splitlines() if line.strip()]
                def mutator(fresh):
                    fresh = normalize_state(fresh)
                    fresh["players"] = players[:25]
                    fresh["player_stats"] = normalize_player_stats(fresh.get("player_stats"), fresh["players"])
                    return True
                ok, _ = mutate_shared_state(mutator, "Update player pool")
                if ok:
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
            st.subheader("Odds")
            st.caption(f"Cinderella baselines are locked to FIFA men's rankings from {FIFA_RANKING_LOCK_DATE}, not edited here.")
            odds_df = pd.DataFrame(
                [
                    {
                        "Team": team["name"],
                        "Odds": state["odds"].get(team["name"], ""),
                        "FIFA Rank": FIFA_RANKINGS.get(team["name"], {}).get("rank"),
                        "FIFA Expected": round(fifa_expected_points(team["name"]), 1),
                    }
                    for team in WORLD_CUP_TEAMS
                ]
            )
            edited_odds = st.data_editor(
                odds_df,
                hide_index=True,
                width="stretch",
                num_rows="fixed",
                disabled=["Team", "FIFA Rank", "FIFA Expected"],
            )
            if st.button("Save Odds"):
                def mutator(fresh):
                    fresh = normalize_state(fresh)
                    for _, row in edited_odds.iterrows():
                        team_name = canonical_team_name(row["Team"])
                        fresh["odds"][team_name] = str(row["Odds"]).strip()
                    return True
                ok, _ = mutate_shared_state(mutator, "Update World Cup odds")
                if ok:
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
            st.subheader("Manual Match Results")
            matches_df = pd.DataFrame(state.get("matches", []))
            edited_matches = st.data_editor(matches_df, hide_index=True, width="stretch", num_rows="dynamic")
            if st.button("Save Matches"):
                def mutator(fresh):
                    fresh = normalize_state(fresh)
                    fresh["matches"] = [normalize_match(row.to_dict(), index) for index, row in edited_matches.iterrows()]
                    return True
                ok, _ = mutate_shared_state(mutator, "Update matches")
                if ok:
                    st.rerun()
            st.caption("Finished matches should use status Finished or Final. Dates can be ISO timestamps.")
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
            st.subheader("Manual Player Stats")
            stats_df = pd.DataFrame(
                [
                    {"Player": player, **state["player_stats"].get(player, {"goals": 0, "assists": 0, "group_goals": 0, "group_assists": 0})}
                    for player in state["players"]
                ]
            )
            edited_stats = st.data_editor(stats_df, hide_index=True, width="stretch", num_rows="fixed")
            if st.button("Save Player Stats"):
                def mutator(fresh):
                    fresh = normalize_state(fresh)
                    stats = {}
                    for _, row in edited_stats.iterrows():
                        player = str(row["Player"]).strip()
                        if not player:
                            continue
                        stats[player] = {
                            "goals": none_or_int(row.get("goals")) or 0,
                            "assists": none_or_int(row.get("assists")) or 0,
                            "group_goals": none_or_int(row.get("group_goals")) or 0,
                            "group_assists": none_or_int(row.get("group_assists")) or 0,
                        }
                    fresh["player_stats"] = stats
                    return True
                ok, _ = mutate_shared_state(mutator, "Update player stats")
                if ok:
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='admin-box'>", unsafe_allow_html=True)
            st.subheader("Manual Advancement Override")
            advancement_rows = [{"Team": team["name"], "Advancement": state["advancement"].get(team["name"], "Group Stage")} for team in WORLD_CUP_TEAMS]
            advancement_df = pd.DataFrame(advancement_rows)
            edited_advancement = st.data_editor(
                advancement_df,
                hide_index=True,
                width="stretch",
                num_rows="fixed",
                column_config={"Advancement": st.column_config.SelectboxColumn(options=ADVANCEMENT_LEVELS)},
            )
            if st.button("Save Advancement"):
                def mutator(fresh):
                    fresh = normalize_state(fresh)
                    for _, row in edited_advancement.iterrows():
                        team_name = canonical_team_name(row["Team"])
                        level = str(row["Advancement"] or "Group Stage")
                        fresh["advancement"][team_name] = level if level in ADVANCEMENT_BONUSES else "Group Stage"
                    return True
                ok, _ = mutate_shared_state(mutator, "Update advancement bonuses")
                if ok:
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
state, sha = load_state_from_github()
state = normalize_state(state)
draft_in_progress = state.get("draft_active") and not full_draft_complete(state)
if not draft_in_progress:
    st_autorefresh(interval=5 * 60 * 1000, key="world_cup_fc_refresh")
if FOOTBALL_DATA_TOKEN and (not draft_in_progress) and int(time.time()) - int(state.get("last_score_refresh_attempt_at") or 0) >= AUTO_SCORE_REFRESH_SECONDS:
    _, refreshed_state = refresh_api_scores()
    if refreshed_state:
        state = normalize_state(refreshed_state)
scores = calculate_scores(state)

render_header(state)
draft_visible = state.get("draft_enabled") and not full_draft_complete(state)
if draft_visible:
    render_drafts(state)
    render_standings(state, scores)
    show_draft_extras = st.toggle("Show Match Tracker and Tables During Draft", value=False, key="show-draft-extras")
    if not show_draft_extras:
        st.caption("Draft focus mode is on to keep picks faster on mobile. Turn on the tracker and tables when you need them.")
else:
    render_standings(state, scores)
    show_draft_extras = True
if show_draft_extras:
    render_live_matches(state)
    render_team_standings(state)
    render_drafted_player_stats(state)
    render_cinderella_standings(state)
render_payout_descriptions()
render_admin(state)
