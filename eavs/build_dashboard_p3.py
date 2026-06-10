import json
import re

import pandas as pd
from loguru import logger

from eavs.config import PROCESSED_DATA_DIR, PROJ_ROOT

CPS_PATH       = PROCESSED_DATA_DIR / "cps_voting_clean.parquet"
EAVS_PATH      = PROCESSED_DATA_DIR / "state_rates.parquet"
DASHBOARDS_DIR = PROJ_ROOT / "dashboards"
OUTPUT_PATH    = DASHBOARDS_DIR / "eavs_dashboard_page3.html"

GROUP_ORDER = ["Total", "White non-Hispanic", "Black", "Hispanic", "Asian"]
GROUP_COLORS = {
    "Total":              "#f0c040",
    "White non-Hispanic": "#4f8ef7",
    "Black":              "#2dc4b2",
    "Hispanic":           "#f0a500",
    "Asian":              "#a78bfa",
}
EAVS_RATE_COLS = [
    "reg_rejection_rate",
    "purge_rate",
    "mail_rejection_rate",
    "provisional_rejection_rate",
]
EAVS_RATE_LABELS = {
    "reg_rejection_rate":         "Reg. Rejection",
    "purge_rate":                 "Purge Rate",
    "mail_rejection_rate":        "Mail Ballot Rejection",
    "provisional_rejection_rate": "Provisional Rejection",
}
EAVS_RATE_FORMULAS = {
    "reg_rejection_rate":         "Rejected applications (A3e) ÷ Total applications received (A3a)",
    "purge_rate":                 "Voters removed (A9a) ÷ Total registered voters (A1a)",
    "mail_rejection_rate":        "Mail ballots rejected (C9a) ÷ Mail ballots returned (C1b)",
    "provisional_rejection_rate": "Provisional ballots rejected (E1d) ÷ Provisional ballots cast (E1a)",
}


def _title_fix(s: str) -> str:
    return re.sub(r"\b(Of|And)\b", lambda m: m.group().lower(), s.title())


def _to_float(val):
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return float(val)


def _prepare() -> tuple[list[dict], list[dict], list[str]]:
    cps  = pd.read_parquet(CPS_PATH)
    eavs = pd.read_parquet(EAVS_PATH)

    cps_records = []
    for _, row in cps.iterrows():
        cps_records.append({
            "state":      str(row["state"]),
            "year":       int(row["year"]),
            "group":      str(row["demo_group"]),
            "reg":        _to_float(row["pct_registered"]),
            "voted":      _to_float(row["pct_voted"]),
            "moe_reg":    _to_float(row["moe_registered"]),
            "moe_voted":  _to_float(row["moe_voted"]),
            "unreliable": bool(row["unreliable"]) if pd.notna(row["unreliable"]) else False,
        })

    eavs_records = []
    for _, row in eavs.iterrows():
        rec = {"state": _title_fix(str(row["state"])), "year": int(row["year"])}
        for col in EAVS_RATE_COLS:
            v = _to_float(row[col]) if col in row.index else None
            if v is not None and v < 0:
                v = None
            rec[col] = v
        eavs_records.append(rec)

    all_states = sorted(cps["state"].dropna().unique())
    us = "United States"
    if us in all_states:
        all_states = [us] + [s for s in all_states if s != us]

    logger.info(
        f"CPS: {len(cps_records)} records, {len(all_states)} states; "
        f"EAVS: {len(eavs_records)} state-year rows"
    )
    return cps_records, eavs_records, all_states


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>EAVS Civic Participation by Race — Page 3</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg:      #0f1117;
      --surf:    #1a1d2e;
      --surf-hi: #21263a;
      --bdr:     #2d3154;
      --txt:     #dde1ee;
      --mut:     #8892b0;
      --blue:    #4f8ef7;
      --red:     #f76c5e;
      --gold:    #f0c040;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--txt); font-family: 'Inter', system-ui, sans-serif;
           min-height: 100vh; font-size: 14px; }

    .hdr { padding: 18px 24px 14px; border-bottom: 1px solid var(--bdr); }
    .hdr h1 { font-size: 18px; font-weight: 700; letter-spacing: -.01em; }
    .hdr p  { font-size: 12px; color: var(--mut); margin-top: 3px; }

    .ctrl { padding: 10px 24px; display: flex; gap: 20px; align-items: center;
            flex-wrap: wrap; border-bottom: 1px solid var(--bdr); background: var(--surf); }
    .tg  { display: flex; align-items: center; gap: 4px; }
    .tg-lbl { font-size: 11px; color: var(--mut); text-transform: uppercase;
              letter-spacing: .07em; margin-right: 2px; white-space: nowrap; }
    button.tb { background: transparent; border: 1px solid var(--bdr); color: var(--mut);
                border-radius: 5px; padding: 4px 11px; font-size: 12px; font-family: inherit;
                cursor: pointer; transition: all .12s; line-height: 1.5; }
    button.tb:hover { border-color: var(--blue); color: var(--txt); }
    button.tb.on  { background: var(--blue); border-color: var(--blue); color: #fff; font-weight: 600; }

    select#state-sel {
      background: var(--surf-hi); border: 1px solid var(--bdr); color: var(--txt);
      border-radius: 5px; padding: 4px 10px; font-size: 12px; font-family: inherit;
      cursor: pointer; outline: none; min-width: 180px;
    }
    select#state-sel:focus { border-color: var(--blue); }

    /* ── Part headers ── */
    .part-hdr { padding: 14px 24px 8px; border-top: 1px solid var(--bdr); }
    .part-hdr h2 { font-size: 12px; font-weight: 700; color: var(--txt);
                   text-transform: uppercase; letter-spacing: .08em; }
    .part-hdr h2 span { color: var(--blue); }
    .part-hdr p  { font-size: 11px; color: var(--mut); margin-top: 3px; line-height: 1.5; }
    .part-src { font-size: 10px; color: var(--mut); padding: 0 24px 8px;
                font-style: italic; }

    /* ── CPS bias note ── */
    .cps-bias { padding: 6px 24px 10px; font-size: 11px; color: var(--mut);
                font-style: italic; border-bottom: 1px solid var(--bdr);
                background: var(--surf); }

    /* ── Charts ── */
    .charts { padding: 10px 24px 0; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 820px) { .charts { grid-template-columns: 1fr; } }
    .cp { background: var(--surf); border: 1px solid var(--bdr); border-radius: 10px;
          padding: 10px 8px; }
    .cp svg { display: block; width: 100%; height: auto; }

    /* ── Section / gap table ── */
    .section { padding: 14px 24px 0; }
    .sec-title { font-size: 11px; font-weight: 600; color: var(--mut);
                 text-transform: uppercase; letter-spacing: .07em; margin-bottom: 4px; }
    .gap-desc { font-size: 11px; color: var(--mut); line-height: 1.65; margin-bottom: 10px; }

    .gap-wrap { background: var(--surf); border: 1px solid var(--bdr);
                border-radius: 10px; overflow: hidden; }
    .gtbl { width: 100%; border-collapse: collapse; font-size: 13px; }
    .gtbl th { background: var(--surf-hi); text-align: left; color: var(--mut); font-size: 10px;
               font-weight: 500; text-transform: uppercase; letter-spacing: .06em;
               border-bottom: 1px solid var(--bdr); padding: 7px 14px; }
    .gtbl td { padding: 8px 14px; border-bottom: 1px solid var(--bdr); vertical-align: middle; }
    .gtbl tr:last-child td { border-bottom: none; }
    .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
              margin-right: 6px; vertical-align: middle; flex-shrink: 0; }
    .pos    { color: #56d364; }
    .neg    { color: #f76c5e; }
    .neg-lg { color: #f76c5e; font-weight: 700; }
    .unrel  { color: var(--mut); font-style: italic; }

    /* ── EAVS context panel ── */
    .eavs-src-line { font-size: 10px; color: var(--mut); font-style: italic; margin-bottom: 8px; }
    .eavs-note-line { font-size: 10px; color: var(--mut); font-style: italic;
                      margin-top: 10px; line-height: 1.65; padding: 8px 12px;
                      border: 1px solid var(--bdr); border-radius: 6px; background: var(--surf-hi); }
    .eavs-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    @media (max-width: 820px) { .eavs-grid { grid-template-columns: repeat(2, 1fr); } }
    .ecard { background: var(--surf); border: 1px solid var(--bdr); border-radius: 8px;
             padding: 10px 14px; }
    .ecard-lbl     { font-size: 10px; color: var(--mut); text-transform: uppercase; letter-spacing: .07em; }
    .ecard-formula { font-size: 9px; color: var(--mut); margin-top: 3px; font-family: monospace;
                     opacity: .8; }
    .ecard-val     { font-size: 20px; font-weight: 700; margin-top: 6px; line-height: 1; }
    .ecard-note    { font-size: 10px; color: var(--mut); margin-top: 3px; }
    .eavs-na { background: var(--surf); border: 1px solid var(--bdr); border-radius: 8px;
               padding: 12px 16px; color: var(--mut); font-size: 12px; font-style: italic; }

    /* ── Legend ── */
    .legend { padding: 10px 24px 6px; display: flex; gap: 14px; flex-wrap: wrap; }
    .li { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--mut); }
    .sw { width: 12px; height: 9px; border-radius: 2px; flex-shrink: 0; }
    .sw-hash { width: 12px; height: 9px; border-radius: 2px; flex-shrink: 0;
      background: repeating-linear-gradient(45deg,#8892b0 0,#8892b0 2px,transparent 2px,transparent 5px); }

    /* ── About / methodology ── */
    .about-data { border-top: 1px solid var(--bdr); margin-top: 6px; }
    .about-hdr  { padding: 9px 24px; font-size: 12px; color: var(--mut); cursor: pointer;
                  font-weight: 600; user-select: none; }
    .about-hdr:hover { color: var(--txt); }
    .about-body { padding: 2px 24px 16px; }
    .about-section { margin-bottom: 12px; font-size: 11px; color: var(--mut); line-height: 1.75; }
    .about-section strong { color: var(--txt); font-weight: 600; }
    .about-tag { display: inline-block; background: var(--surf-hi); border: 1px solid var(--bdr);
                 border-radius: 3px; padding: 0 5px; font-size: 10px; margin-right: 4px; }
    .crossnote { font-size: 11px; color: var(--mut); font-style: italic;
                 border-top: 1px solid var(--bdr); padding-top: 10px; margin-top: 4px;
                 line-height: 1.7; }

    .footnote { padding: 6px 24px 10px; font-size: 11px; color: var(--mut);
                border-top: 1px solid var(--bdr); line-height: 1.7; margin-top: 12px; }
  </style>
</head>
<body>

<div class="hdr">
  <h1>Civic Participation by Race &amp; Ethnicity — Page 3</h1>
  <p>Self-reported survey data from the U.S. Census Bureau CPS Voting Supplement (race breakdown) and EAC EAVS (administrative context)</p>
</div>

<div class="ctrl">
  <div class="tg">
    <span class="tg-lbl">State</span>
    <select id="state-sel" onchange="render()"></select>
  </div>
  <div class="tg">
    <span class="tg-lbl">Year</span>
    <button class="tb on" id="y2024" onclick="setYear(2024)">2024</button>
    <button class="tb"    id="y2022" onclick="setYear(2022)">2022</button>
    <button class="tb"    id="y2020" onclick="setYear(2020)">2020</button>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════
     PART 1 — Self-reported participation rates by race
     Source: CPS Voting Supplement Table 4b
     ════════════════════════════════════════════════════════ -->
<div class="part-hdr">
  <h2><span>PART 1</span> — Self-reported participation rates by race</h2>
  <p>Source: U.S. Census Bureau, Current Population Survey (CPS) Voting Supplement, Table 4b — "Reported Voting and Registration by Sex, Race and Hispanic Origin, for States"</p>
</div>

<div class="cps-bias">
  Note: CPS data is self-reported and may overcount registration and turnout due to social desirability bias (respondents may indicate they voted when they did not).
  Estimates with margin of error &gt; 10 percentage points are flagged as unreliable (shown hatched with *).
</div>

<div class="charts">
  <div class="cp" id="reg-panel"></div>
  <div class="cp" id="turn-panel"></div>
</div>

<div class="legend">
  <div class="li"><div class="sw" style="background:#f0c040"></div>Total</div>
  <div class="li"><div class="sw" style="background:#4f8ef7"></div>White non-Hispanic</div>
  <div class="li"><div class="sw" style="background:#2dc4b2"></div>Black</div>
  <div class="li"><div class="sw" style="background:#f0a500"></div>Hispanic</div>
  <div class="li"><div class="sw" style="background:#a78bfa"></div>Asian</div>
  <div class="li"><div class="sw-hash"></div>Unreliable (MOE &gt; 10pp)</div>
</div>

<div class="section" style="padding-bottom:0">
  <div class="sec-title">Participation Gap vs. Total Population</div>
  <div class="gap-desc">
    Gap = difference in registration or turnout rate between each racial group and the Total population.
    A negative gap means the group participates at a lower rate than the overall population average.
    Bold red indicates a gap larger than 10 percentage points.
    Source: CPS Table 4b (self-reported). * = unreliable estimate (MOE &gt; 10pp).
  </div>
  <div class="gap-wrap"><table class="gtbl" id="gap-tbl"></table></div>
</div>

<!-- ════════════════════════════════════════════════════════
     PART 2 — Administrative barriers context (EAVS)
     Source: EAC Election Administration and Voting Survey
     ════════════════════════════════════════════════════════ -->
<div class="part-hdr" style="padding-top:18px">
  <h2><span>PART 2</span> — Administrative barriers context (EAVS, total population only)</h2>
  <p>Source: EAC Election Administration and Voting Survey (EAVS), aggregated to state level · 2020 &amp; 2022 only (2024 EAVS data not yet in pipeline)</p>
</div>

<div class="section" style="padding-top:6px;padding-bottom:4px">
  <div id="eavs-panel"></div>
</div>

<div class="footnote">
  <strong>Sources:</strong>
  CPS: U.S. Census Bureau, Current Population Survey Voting Supplement, Table 4b.
  EAVS: U.S. Election Assistance Commission, Election Administration and Voting Survey.
  2024 EAVS data not yet incorporated into this pipeline.
  * = unreliable CPS estimate.
</div>

<div class="about-data">
  <div class="about-hdr" onclick="const b=document.getElementById('about-body');b.style.display=b.style.display==='none'?'block':'none'">
    ▾ About the data &amp; methodology
  </div>
  <div class="about-body" id="about-body" style="display:none">
    <div class="about-section">
      <strong>Current Population Survey (CPS) Voting Supplement — Table 4b</strong><br>
      <span class="about-tag">Census Bureau</span> Biennial (November, federal election years) · Reported by: individual citizens (self-reported survey)<br>
      Measures: Self-reported registration and voting rates by race, Hispanic origin, sex, and age at state level.<br>
      Limitation: Known to overcount turnout due to social desirability bias. Small state samples produce wide margins
      of error for smaller racial groups — estimates with MOE &gt;10 percentage points are flagged as unreliable (shown hatched).<br>
      Coverage: 50 states + DC · Years in this dashboard: 2020, 2022, 2024
    </div>
    <div class="about-section">
      <strong>Election Administration and Voting Survey (EAVS)</strong><br>
      <span class="about-tag">EAC</span> Biennial (federal election years) · Reported by: state and local election administrators<br>
      Measures: Administrative counts — ballots cast, voter registrations, rejections, purges, mail ballot activity.<br>
      Limitation: Self-reported by election officials; anomalies reflect administrative practices, not necessarily voter behaviour.
      EAVS does <em>not</em> collect race-disaggregated administrative data — all rates shown here are for the total population.<br>
      Coverage: All 50 states + DC + territories · Years in this dashboard: 2020, 2022
    </div>
    <div class="about-section">
      <strong>American Community Survey (ACS) — CVAP Special Tabulation</strong><br>
      <span class="about-tag">Census Bureau</span> Annual (5-year rolling estimates used here)<br>
      Measures: Citizen Voting Age Population (CVAP) — U.S. citizens aged 18+ by race and geography.<br>
      Used for: Registration rate denominator on Page 1 (Registered voters ÷ CVAP).<br>
      Vintage used: ACS 2018–2022 5-year estimates
    </div>
    <div class="crossnote">
      Race-disaggregated participation rates (CPS) and administrative barrier rates (EAVS) use different denominators
      and methodologies and should not be directly compared. CPS denominators are survey-estimated citizen voting-age
      population. EAVS denominators are administratively reported registered voter counts.
    </div>
  </div>
</div>

<script>
const DATA_CPS    = __CPS_DATA__;
const DATA_EAVS   = __EAVS_DATA__;
const STATES      = __STATES__;
const GROUP_ORDER  = __GROUP_ORDER__;
const GROUP_COLORS = __GROUP_COLORS__;
const EAVS_LABELS  = __EAVS_LABELS__;
const EAVS_FORMULAS = __EAVS_FORMULAS__;
const EAVS_COLS    = ["reg_rejection_rate","purge_rate","mail_rejection_rate","provisional_rejection_rate"];

let year = 2024;

// ── Init ──────────────────────────────────────────────────────────────────
function init() {
  const sel = document.getElementById('state-sel');
  STATES.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    if (s === 'Pennsylvania') opt.selected = true;
    sel.appendChild(opt);
  });
  render();
}

function setYear(y) {
  year = y;
  [2024, 2022, 2020].forEach(k =>
    document.getElementById('y' + k).classList.toggle('on', k === y)
  );
  render();
}

// ── Data helpers ──────────────────────────────────────────────────────────
function getState() { return document.getElementById('state-sel').value; }

function getCpsRows(state, yr) {
  const rows = DATA_CPS.filter(d => d.state === state && d.year === yr);
  rows.sort((a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group));
  return rows;
}

function getEavsRow(state, yr) {
  return DATA_EAVS.find(d => d.state === state && d.year === yr) || null;
}

// ── Charts ────────────────────────────────────────────────────────────────
function pct(v, d = 1) { return v == null ? 'n/a' : (v * 100).toFixed(d) + '%'; }

function raceChart(panelId, rows, field, title, metricDesc) {
  const W = 640, ML = 152, MR = 68, MT = 56, MB = 26, RH = 32, BH = 15;
  const cw = W - ML - MR;
  const H  = MT + rows.length * RH + MB;
  const sc = v => Math.max(0, v * cw);

  const MUT = '#8892b0', GRD = '#1e2236', TXT = '#dde1ee';
  const totalVal = (rows.find(r => r.group === 'Total') || {})[field] ?? null;

  let s = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
  s += `<text x="${ML}" y="16" font-family="Inter,sans-serif" font-size="13" font-weight="600" fill="${TXT}">${title}</text>`;
  s += `<text x="${ML}" y="30" font-family="Inter,sans-serif" font-size="10" fill="${MUT}">Source: CPS Voting Supplement, Table 4b · Self-reported by citizens</text>`;
  s += `<text x="${ML}" y="44" font-family="Inter,sans-serif" font-size="10" fill="${MUT}">${metricDesc}</text>`;

  for (const t of [0, 0.25, 0.5, 0.75, 1.0]) {
    const x = ML + sc(t);
    s += `<line x1="${x}" y1="${MT}" x2="${x}" y2="${H-MB}" stroke="${GRD}" stroke-width="1"/>`;
    s += `<text x="${x}" y="${H-MB+14}" text-anchor="middle" font-family="Inter,sans-serif" font-size="9" fill="${MUT}">${Math.round(t*100)}%</text>`;
  }

  if (totalVal != null) {
    const tx = ML + sc(totalVal);
    s += `<line x1="${tx}" y1="${MT}" x2="${tx}" y2="${H-MB}" stroke="#f0c040" stroke-width="1.2" stroke-dasharray="4,3" stroke-opacity="0.55"/>`;
  }

  for (let i = 0; i < rows.length; i++) {
    const d  = rows[i];
    const y0 = MT + i * RH;
    const by = y0 + (RH - BH) / 2;
    const v  = d[field];
    const col = GROUP_COLORS[d.group] || MUT;
    const isTotal = d.group === 'Total';

    if (i % 2 === 0) s += `<rect x="0" y="${y0}" width="${W}" height="${RH}" fill="#ffffff" fill-opacity="0.010"/>`;

    s += `<text x="${ML-7}" y="${y0+RH/2+4}" text-anchor="end" font-family="Inter,sans-serif" font-size="11" fill="${isTotal ? TXT : MUT}">${d.group}</text>`;

    if (v == null) {
      s += `<text x="${ML+5}" y="${y0+RH/2+4}" font-family="Inter,sans-serif" font-size="10" font-style="italic" fill="${MUT}">no estimate</text>`;
    } else if (d.unreliable) {
      const bw = Math.max(sc(v), 2);
      const pid = `p${panelId}${i}`;
      s += `<defs><pattern id="${pid}" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="${col}" stroke-width="2.5" stroke-opacity="0.45"/>
            </pattern></defs>`;
      s += `<rect x="${ML}" y="${by}" width="${bw}" height="${BH}" rx="2" fill="url(#${pid})"/>`;
      s += `<rect x="${ML}" y="${by}" width="${bw}" height="${BH}" rx="2" fill="none" stroke="${col}" stroke-width="1" stroke-opacity="0.5"/>`;
      s += `<text x="${ML+bw+5}" y="${y0+RH/2+4}" font-family="Inter,sans-serif" font-size="10" fill="${MUT}" font-style="italic">${pct(v)} *</text>`;
    } else {
      const bw = Math.max(sc(v), 2);
      s += `<rect x="${ML}" y="${by}" width="${bw}" height="${BH}" rx="2" fill="${col}"/>`;
      s += `<text x="${ML+bw+5}" y="${y0+RH/2+4}" font-family="Inter,sans-serif" font-size="10" fill="${MUT}">${pct(v)}</text>`;
    }
  }
  s += '</svg>';
  document.getElementById(panelId).innerHTML = s;
}

// ── Gap table ─────────────────────────────────────────────────────────────
function buildGapTable(rows) {
  const tot   = rows.find(r => r.group === 'Total');
  const tReg  = tot ? tot.reg   : null;
  const tVote = tot ? tot.voted : null;

  function fmtRate(v, unrel) {
    if (v == null) return `<td class="unrel">—</td>`;
    const s = (v*100).toFixed(1)+'%' + (unrel ? ' *':'');
    return `<td class="${unrel?'unrel':''}">${s}</td>`;
  }
  function fmtGap(v, base, unrel) {
    if (v == null || base == null) return `<td class="unrel">—</td>`;
    const g = (v - base)*100;
    const sign = g >= 0 ? '+' : '';
    const cls  = unrel ? 'unrel' : (g >= 0 ? 'pos' : (g < -10 ? 'neg-lg' : 'neg'));
    return `<td class="${cls}">${sign}${g.toFixed(1)}pp${unrel?' *':''}</td>`;
  }

  let h = `<thead><tr>
    <th>Group</th>
    <th>Reg. rate</th><th>Gap vs. Total</th>
    <th>Turnout rate</th><th>Gap vs. Total</th>
  </tr></thead><tbody>`;
  for (const r of rows) {
    const col = GROUP_COLORS[r.group] || '#888';
    h += `<tr>
      <td><span class="swatch" style="background:${col}"></span>${r.group}</td>
      ${fmtRate(r.reg, r.unreliable)}${fmtGap(r.reg, tReg, r.unreliable)}
      ${fmtRate(r.voted, r.unreliable)}${fmtGap(r.voted, tVote, r.unreliable)}
    </tr>`;
  }
  h += '</tbody>';
  return h;
}

// ── EAVS panel ────────────────────────────────────────────────────────────
function buildEavsPanel(state, yr) {
  const el = document.getElementById('eavs-panel');
  if (yr === 2024 || state === 'United States') {
    el.innerHTML = `<div class="eavs-na">EAVS administrative rates not available for ${yr === 2024 ? '2024 (data not yet in pipeline)' : 'United States aggregate'}.</div>`;
    return;
  }
  const row = getEavsRow(state, yr);
  if (!row) {
    el.innerHTML = `<div class="eavs-na">No EAVS data for ${state} ${yr}.</div>`;
    return;
  }

  let html = '<div class="eavs-src-line">Source: EAC Election Administration and Voting Survey (EAVS), aggregated to state level · Rates shown at total population level — EAVS does not collect race-disaggregated administrative data.</div>';
  html += '<div class="eavs-grid">';
  for (const col of EAVS_COLS) {
    const v   = row[col];
    const val = v == null ? '—' : (v*100).toFixed(1)+'%';
    const kyNote = (col === 'reg_rejection_rate' && state === 'Kentucky')
               ? '<div class="ecard-note">⚠ Duplicate counting — not true rejections</div>' : '';
    html += `<div class="ecard">
      <div class="ecard-lbl">${EAVS_LABELS[col]}</div>
      <div class="ecard-formula">${EAVS_FORMULAS[col]}</div>
      <div class="ecard-val">${val}</div>${kyNote}
    </div>`;
  }
  html += '</div>';
  html += '<div class="eavs-note-line">EAVS data is self-reported by election administrators. Rates shown at total population level — EAVS does not collect race-disaggregated administrative data.</div>';
  el.innerHTML = html;
}

// ── Render ────────────────────────────────────────────────────────────────
function render() {
  const state = getState();
  const rows  = getCpsRows(state, year);
  if (!rows.length) {
    ['reg-panel','turn-panel'].forEach(id =>
      document.getElementById(id).innerHTML = '<p style="padding:16px;color:var(--mut)">No data.</p>'
    );
    document.getElementById('gap-tbl').innerHTML = '';
    document.getElementById('eavs-panel').innerHTML = '';
    return;
  }
  raceChart('reg-panel',  rows, 'reg',   'Voter Registration Rate',
    'Numerator: self-reported registered citizens · Denominator: total citizen voting-age population surveyed');
  raceChart('turn-panel', rows, 'voted', 'Voter Turnout Rate',
    'Numerator: self-reported voters · Denominator: total citizen voting-age population surveyed');
  document.getElementById('gap-tbl').innerHTML = buildGapTable(rows);
  buildEavsPanel(state, year);
}

window.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""


def _html(cps_records: list, eavs_records: list, states: list) -> str:
    return (
        HTML_TEMPLATE
        .replace("__CPS_DATA__",     json.dumps(cps_records,        separators=(",", ":")))
        .replace("__EAVS_DATA__",    json.dumps(eavs_records,       separators=(",", ":")))
        .replace("__STATES__",       json.dumps(states,             separators=(",", ":")))
        .replace("__GROUP_ORDER__",  json.dumps(GROUP_ORDER,        separators=(",", ":")))
        .replace("__GROUP_COLORS__", json.dumps(GROUP_COLORS,       separators=(",", ":")))
        .replace("__EAVS_LABELS__",  json.dumps(EAVS_RATE_LABELS,   separators=(",", ":")))
        .replace("__EAVS_FORMULAS__",json.dumps(EAVS_RATE_FORMULAS, separators=(",", ":")))
    )


def main():
    logger.info("Starting Page 3 dashboard build")
    for p in [CPS_PATH, EAVS_PATH]:
        if not p.exists():
            logger.error(f"Input not found: {p}")
            return

    cps_records, eavs_records, states = _prepare()
    html = _html(cps_records, eavs_records, states)
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    size = OUTPUT_PATH.stat().st_size
    logger.info(
        f"Saved: {OUTPUT_PATH}  "
        f"({size:,} bytes, {len(cps_records)} CPS records, {len(states)} states)"
    )


if __name__ == "__main__":
    main()
