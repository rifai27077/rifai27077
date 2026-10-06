#!/usr/bin/env python3
import urllib.request, json, datetime, os

GH_USER = "rifai27077"
GL_URL = "https://git.wellmagic.id"
GL_USER_ID = 33
GL_TOKEN = os.environ.get("GITLAB_TOKEN", "")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
STATS_OUT = os.path.join(REPO_ROOT, "stats.svg")
HEATMAP_OUT = os.path.join(REPO_ROOT, "contrib-heatmap.svg")

# 1. Fetch GitHub
print("1. Mengambil data GitHub...")
gh_url = f"https://github-contributions-api.jogruber.de/v4/{GH_USER}?y=last"
req = urllib.request.Request(gh_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=15) as r:
    gh_data = json.loads(r.read().decode())

gh_days = gh_data.get("contributions", [])
days_map = {d["date"]: d["count"] for d in gh_days}

# 2. Fetch GitLab
print("2. Mengambil data GitLab...")
one_year_ago = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
headers = {"PRIVATE-TOKEN": GL_TOKEN, "User-Agent": "Mozilla/5.0"}
gl_total = 0
page = 1

while True:
    events_url = f"{GL_URL}/api/v4/users/{GL_USER_ID}/events?after={one_year_ago}&per_page=100&page={page}"
    req = urllib.request.Request(events_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            events = json.loads(r.read().decode())
            if not events:
                break
            for ev in events:
                date_str = ev.get("created_at", "")[:10]
                if not date_str:
                    continue
                cnt = ev.get("push_data", {}).get("commit_count", 1) or 1 if ev.get("action_name") == "pushed" else 1
                days_map[date_str] = days_map.get(date_str, 0) + cnt
                gl_total += cnt
            page += 1
    except Exception as e:
        break

# Build unified days array
combined_days = []
for d in gh_days:
    dt = d["date"]
    cnt = days_map.get(dt, 0)
    lvl = 0 if cnt == 0 else (1 if cnt <= 3 else (2 if cnt <= 9 else (3 if cnt <= 19 else 4)))
    combined_days.append({"date": dt, "count": cnt, "level": lvl})

combined_days.sort(key=lambda d: d["date"])

# 3. Compute metrics
def compute_current_streak(days):
    idx = len(days) - 1
    if days and days[idx]["count"] == 0:
        idx -= 1
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]

def compute_longest_streak(days):
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end

total = sum(d["count"] for d in combined_days)
active_days = sum(1 for d in combined_days if d["count"] > 0)
best = max(combined_days, key=lambda d: d["count"]) if combined_days else {"date": "", "count": 0}
cur_len, cur_start, cur_end = compute_current_streak(combined_days)
long_len, long_start, long_end = compute_longest_streak(combined_days)

monthly = {}
for d in combined_days:
    key = d["date"][:7]
    monthly[key] = monthly.get(key, 0) + d["count"]
monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

print(f"Total: {total} (GitHub: {gh_data['total']['lastYear']}, GitLab: {gl_total}) | Active days: {active_days} | Current streak: {cur_len} hari")

# 4. Generate stats.svg
BG, BG2 = "#0d1117", "#111722"
TILE, FRAME, MUTED, INK = "#161b22", "#30363d", "#7d8590", "#e6edf3"
GREEN, BAR = "#39d353", "#26a641"
W, H = 840, 880
PAD, TITLEBAR_H = 20, 30
COLS, ROWS, GAP = 2, 3, 16
TILE_W = (W - PAD * 2 - GAP * (COLS - 1)) / COLS
TILE_H = 150
TILES_TOP = TITLEBAR_H + PAD + 4
CHART_TOP = TILES_TOP + ROWS * TILE_H + (ROWS - 1) * GAP + GAP

TILE_STAGGER, SLIDE_DUR, COUNT_DUR, FRAMES = 0.15, 0.45, 1.2, 16
BAR_START = TILE_STAGGER * COLS * ROWS + 0.4
BAR_STAGGER, BAR_DUR = 0.06, 0.6

def short(d):
    return datetime.date.fromisoformat(d).strftime("%b %-d") if d else "—"

def span(s_len, s_start, s_end):
    return f"{short(s_start)} – {short(s_end)}" if s_len else "—"

n_days = len(combined_days) or 365
tiles = [
    ("current streak", cur_len, " days", span(cur_len, cur_start, cur_end), GREEN),
    ("longest streak", long_len, " days", span(long_len, long_start, long_end), INK),
    ("contributions", total, "", "GitHub + GitLab (1 yr)", INK),
    ("active days", active_days, f" / {n_days}", f"{active_days / n_days:.0%} of the year", INK),
    ("best day", best["count"], "", short(best["date"]), INK),
    ("avg / active day", round(total / active_days, 1) if active_days else 0, "", "contributions", INK),
]

def fmt(v, like):
    return f"{v:,.1f}" if isinstance(like, float) else f"{int(round(v)):,}"

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<style>'
    f'.t{{opacity:0;animation:in {SLIDE_DUR}s ease-out both}}'
    '@keyframes in{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:translateY(0)}}'
    f'.b{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:grow {BAR_DUR}s ease-out both}}'
    '@keyframes grow{to{transform:scaleY(1)}}'
    '@media (prefers-reduced-motion: reduce){.t,.b{opacity:1!important;transform:none!important;animation:none!important}}'
    '</style>',
    f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
]
for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>')
parts.append(f'<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{MUTED}" font-size="12" '
             f'text-anchor="middle">{GH_USER}@github: ~$ ./stats.sh</text>')

for i, (label, value, suffix, caption, accent) in enumerate(tiles):
    col, row = i % COLS, i // COLS
    x = PAD + col * (TILE_W + GAP)
    y = TILES_TOP + row * (TILE_H + GAP)
    start = i * TILE_STAGGER
    count_start = start + SLIDE_DUR * 0.6

    parts.append(f'<g class="t" style="animation-delay:{start:.2f}s">')
    parts.append(f'<rect x="{x:.1f}" y="{y}" width="{TILE_W:.1f}" height="{TILE_H}" rx="10" '
                 f'fill="{TILE}" stroke="{FRAME}"/>')
    parts.append(f'<text x="{x+24:.1f}" y="{y+40}" fill="{MUTED}" font-size="22">$ {label}</text>')

    num_y = y + 100
    for k in range(1, FRAMES + 1):
        p = k / FRAMES
        v = value * (1 - (1 - p) ** 3)
        t_on = count_start + COUNT_DUR * (k - 1) / FRAMES
        t_off = count_start + COUNT_DUR * k / FRAMES
        anim = f'<set attributeName="opacity" to="1" begin="{t_on:.3f}s"/>'
        if k < FRAMES:
            anim += f'<set attributeName="opacity" to="0" begin="{t_off:.3f}s"/>'
        parts.append(
            f'<text x="{x+24:.1f}" y="{num_y}" opacity="0" font-size="54" font-weight="700" fill="{accent}">'
            f'{fmt(v, value)}<tspan font-size="24" font-weight="400" fill="{MUTED}">{suffix}</tspan>'
            f'{anim}</text>'
        )
    parts.append(f'<text x="{x+24:.1f}" y="{y+132}" fill="{MUTED}" font-size="20">{caption}</text>')
    parts.append('</g>')

chart_x, chart_w = PAD, W - PAD * 2
chart_h = H - PAD - CHART_TOP
parts.append(f'<g class="t" style="animation-delay:{BAR_START - 0.3:.2f}s">')
parts.append(f'<rect x="{chart_x}" y="{CHART_TOP}" width="{chart_w}" height="{chart_h}" rx="10" '
             f'fill="{TILE}" stroke="{FRAME}"/>')
parts.append(f'<text x="{chart_x+24}" y="{CHART_TOP+40}" fill="{MUTED}" font-size="22">$ contributions / month</text>')
parts.append('</g>')

plot_top = CHART_TOP + 64
plot_bot = CHART_TOP + chart_h - 40
plot_l, plot_r = chart_x + 24, chart_x + chart_w - 24
slot = (plot_r - plot_l) / (len(monthly_list) or 1)
bar_w = slot * 0.62
peak = max((m["total"] for m in monthly_list), default=1) or 1
for i, m in enumerate(monthly_list):
    h = max(2, (plot_bot - plot_top) * m["total"] / peak)
    bx = plot_l + i * slot + (slot - bar_w) / 2
    fill = GREEN if m["total"] == peak else BAR
    delay = BAR_START + i * BAR_STAGGER
    parts.append(f'<rect class="b" x="{bx:.1f}" y="{plot_bot - h:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                 f'rx="3" fill="{fill}" style="animation-delay:{delay:.2f}s"/>')
    mon = datetime.date.fromisoformat(m["month"] + "-01").strftime("%b")[0]
    parts.append(f'<text x="{bx + bar_w/2:.1f}" y="{plot_bot + 28}" fill="{MUTED}" font-size="18" '
                 f'text-anchor="middle">{mon}</text>')
    if m["total"] == peak:
        parts.append(f'<text class="t" style="animation-delay:{delay + BAR_DUR:.2f}s" x="{bx + bar_w/2:.1f}" '
                     f'y="{plot_bot - h - 10:.1f}" fill="{INK}" font-size="18" text-anchor="middle">{peak:,}</text>')

parts.append('</svg>')
svg = "".join(parts)
with open(STATS_OUT, "w") as f:
    f.write(svg)
print(f"Berhasil membuat: {STATS_OUT}")

# 5. Generate contrib-heatmap.svg
CELL, GAP, RAD, LEFT, TOP = 13, 3, 2.5, 34, 24
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FLASH = "#b4ffaa"
GRAY = "#7d8590"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

n = len(combined_days)
NW = (n + 6) // 7
HM_W = LEFT + NW*(CELL+GAP) + 6
HM_H = TOP + 7*(CELL+GAP) + 22
REVEAL, DUR = 3.6, 0.55
maxorder = (NW-1) + 6*0.55

rects, labels = [], []
sd = datetime.date.fromisoformat(combined_days[0]["date"])
last_m = None
for wk in range(NW):
    d = sd + datetime.timedelta(days=wk*7)
    if d.month != last_m:
        last_m = d.month
        labels.append(f'<text class="lbl" x="{LEFT+wk*(CELL+GAP)}" y="{TOP-8}">{MONTHS[d.month-1]}</text>')
for name, r in [("Mon",1),("Wed",3),("Fri",5)]:
    labels.append(f'<text class="lbl" x="2" y="{TOP+r*(CELL+GAP)+CELL-2}">{name}</text>')

for i, c in enumerate(combined_days):
    wk, row, lvl = i//7, i%7, c["level"]
    x = LEFT + wk*(CELL+GAP); y = TOP + row*(CELL+GAP)
    delay = round((wk + row*0.55)/maxorder * REVEAL, 3)
    cls = "c g" if lvl >= 1 else "c e"
    rects.append(
        f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RAD}" '
        f'fill="{COLORS[lvl]}" style="animation-delay:{delay}s"/>'
    )

hm_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{HM_W}" height="{HM_H}" viewBox="0 0 {HM_W} {HM_H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill:{GRAY}; font-size:13px; font-weight:600; }}
  text.total {{ fill:#e6edf3; font-size:15px; font-weight:700; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop {DUR}s ease-out both; }}
  .g {{ animation:pop {DUR}s ease-out both, flash {DUR+0.15}s ease-out both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} 60%{{opacity:1;transform:scale(1.1)}} 100%{{opacity:1;transform:scale(1)}} }}
  @keyframes flash {{ 0%{{filter:brightness(2.4)}} 45%{{filter:brightness(2.4)}} 100%{{filter:brightness(1)}} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ opacity:1 !important; animation:none !important; }} }}
</style>
<rect width="{HM_W}" height="{HM_H}" fill="none"/>
{''.join(labels)}
{''.join(rects)}
<text class="total" x="{LEFT}" y="{HM_H-6}">{total:,} contributions in the last year</text>
</svg>'''

with open(HEATMAP_OUT, "w") as f:
    f.write(hm_svg)
print(f"Berhasil membuat: {HEATMAP_OUT}")
