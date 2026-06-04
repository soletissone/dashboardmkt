import json

with open(r'C:\Users\USUARIO\AppData\Local\Temp\dashboard_data.json', encoding='utf-8') as f:
    D = json.load(f)

MONTHS          = D['months']
PROG_MX         = D['prog_mx']
PROG_INT        = D['prog_int']
INT_C           = D['int_countries']
CANAL_MX        = D['canal_mx']
CANAL_INT       = D['canal_int']
T_MX            = D['trend_mx']
T_INT           = D['trend_int']
T_ALL           = D['trend_all']
T_MX_2025       = D['trend_mx_2025']
T_INT_2025      = D['trend_int_2025']
T_ALL_2025      = D['trend_all_2025']
MEDIO           = D['medio_stats']
CANAL_TREND_MX  = D.get('canal_trend_mx', {})
MAY_F           = D['may_factor']
MAY_D           = D['may_days']
CUR_MONTH_LABEL = D.get('cur_month', 'may 2026').capitalize()   # e.g. "Jun 2026"
CUR_DAYS        = D.get('cur_days', MAY_D)

# Build human-readable date string for subtitles
_cm = D.get('cur_month', 'may 2026')
_cd = D.get('cur_days', MAY_D)
_MONTH_ES = {'ene':'Ene','feb':'Feb','mar':'Mar','abr':'Abr','may':'May',
             'jun':'Jun','jul':'Jul','ago':'Ago','sep':'Sep','oct':'Oct','nov':'Nov','dic':'Dic'}
_m_abbr  = _cm[:3].lower()
_m_label = _MONTH_ES.get(_m_abbr, _m_abbr.capitalize())
_m_year  = _cm[-4:]
FECHA_DATOS = (f'{_m_label} {_m_year} · {_cd} días reales' if _cd < 28
               else f'{_m_label} {_m_year} completo')  # e.g. "Jun 2026 · 3 días reales"
INV_CANAL       = D.get('inv_canal', [])
_FP             = D.get('funnel_prog', {'programs': [], 'totals': {}})
FUNNEL_PROG     = _FP.get('programs', [])
FUNNEL_TOTALS   = _FP.get('totals', {})
FUNNEL_PROG_MEDIO = D.get('funnel_prog_medio', [])

# Global set of NEW program names (used for badges across all views)
NEW_PROGS = {p['prog'] for p in PROG_MX if p.get('is_new')}
# also add from INT countries
for _c in INT_C.values():
    for _p in _c.get('progs', []):
        if _p.get('is_new'): NEW_PROGS.add(_p['prog'])

def new_badge(prog_name, size=8):
    if prog_name in NEW_PROGS:
        return (f'<span style="background:#7c3aed;color:white;padding:1px 5px;'
                f'border-radius:6px;font-size:{size}px;font-weight:800;margin-right:4px;">NUEVO</span>')
    return ''

# Dynamic CR floor: Abril MX (last complete month) — used instead of hardcoded 2.0
ABR_CR_MX = T_MX[3]['cr']   # Abril 2026 MX CR (index 3)

# Countries sorted by abr_leads desc
INT_SORTED = sorted(INT_C.items(), key=lambda x: -x[1]['abr_leads'])
# Only countries with meaningful data
INT_SORTED = [(k,v) for k,v in INT_SORTED if v['abr_leads'] >= 100]

def fmt_k(n):
    n = n or 0
    if n >= 1000000: return f'{n/1000000:.1f}M'
    if n >= 1000: return f'{n/1000:.1f}k'
    return str(int(n))

def fmt_cr(cr):
    """Always show CR with 1 decimal place: 2.2% not 2%"""
    return f'{float(cr):.1f}'

# ── YoY comparison chart ──────────────────────────────────────────────────────
def yoy_chart(trend_2025, trend_2026, key, label, color, W=520, H=150):
    vals_25 = [g[key] for g in trend_2025]   # 12 months
    vals_26 = [g[key] for g in trend_2026]   # 5 months (Jan-May)
    n = 12
    all_vals = [v for v in vals_25 + vals_26 if v > 0]
    mx = max(all_vals) * 1.18 if all_vals else 1
    mn = min(all_vals) * 0.85 if all_vals else 0
    sx = 38; ex = W - 16
    def px(i): return round(sx + i * (ex - sx) / (n - 1))
    def py(v): return round(H - 26 - (v - mn) / (mx - mn) * (H - 44))
    is_cr = key == 'cr'
    lbl_fn = lambda v: f'{fmt_cr(v)}%' if is_cr else fmt_k(v)
    month_labels = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

    svg = f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
    # Y grid (4 lines)
    for i in range(5):
        y = py(mn + (mx - mn) * i / 4)
        val = mn + (mx - mn) * i / 4
        svg += f'<line x1="{sx-4}" y1="{y}" x2="{ex}" y2="{y}" stroke="#f1f5f9" stroke-width="1"/>'
        svg += f'<text x="{sx-6}" y="{y+3}" font-size="8" fill="#cbd5e1" text-anchor="end">{lbl_fn(val)}</text>'
    # 2025 line — full year, dashed gray
    pts_25 = [(px(i), py(v)) for i, v in enumerate(vals_25)]
    path_25 = 'M ' + ' L '.join(f'{x},{y}' for x, y in pts_25)
    svg += f'<path d="{path_25}" fill="none" stroke="#94a3b8" stroke-width="1.8" stroke-dasharray="5,3" opacity=".65"/>'
    for x, y in pts_25:
        svg += f'<circle cx="{x}" cy="{y}" r="2.5" fill="#94a3b8" opacity=".5"/>'
    # 2025 last label
    lx, ly = pts_25[-1]; v25_last = vals_25[-1]
    svg += f'<text x="{lx+4}" y="{ly+3}" font-size="8" fill="#94a3b8">{lbl_fn(v25_last)}</text>'
    # 2026 line — Jan–May, solid color
    pts_26 = [(px(i), py(v)) for i, v in enumerate(vals_26)]
    # Fill area under 2026 line
    fp = ('M ' + ' L '.join(f'{x},{y}' for x, y in pts_26)
          + f' L {pts_26[-1][0]},{H-26} L {pts_26[0][0]},{H-26} Z')
    svg += f'<path d="{fp}" fill="{color}" opacity=".08"/>'
    path_26 = 'M ' + ' L '.join(f'{x},{y}' for x, y in pts_26)
    svg += f'<path d="{path_26}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>'
    for i, (x, y) in enumerate(pts_26):
        is_last = (i == len(pts_26) - 1)
        svg += f'<circle cx="{x}" cy="{y}" r="{4 if is_last else 3}" fill="{color}"/>'
        if is_last:
            v26 = vals_26[i]; v25 = vals_25[i]
            diff = round(v26 - v25, 1) if is_cr else round((v26 - v25) / v25 * 100, 0) if v25 else 0
            diff_col = '#16a34a' if diff >= 0 else '#dc2626'
            diff_str = (f'+{fmt_cr(diff)}pp' if is_cr else f'+{int(diff)}%') if diff >= 0 else (f'{fmt_cr(diff)}pp' if is_cr else f'{int(diff)}%')
            svg += (f'<text x="{x}" y="{max(14, y-8)}" font-size="9" fill="{color}" '
                    f'text-anchor="middle" font-weight="700">{lbl_fn(v26)}</text>')
            svg += (f'<text x="{x}" y="{max(24, y+2) if y < 30 else y-18}" font-size="8" fill="{diff_col}" '
                    f'text-anchor="middle" font-weight="700">({diff_str} vs 2025)</text>')
    # Month labels
    for i, ml in enumerate(month_labels):
        bold = i < len(vals_26)
        col  = color if bold else '#cbd5e1'
        svg += f'<text x="{px(i)}" y="{H-8}" font-size="8" fill="{col}" text-anchor="middle" font-weight="{"700" if bold else "400"}">{ml}</text>'
    # Legend
    svg += (f'<rect x="4" y="4" width="16" height="2.5" fill="#94a3b8" opacity=".65" rx="1"/>'
            f'<text x="22" y="10" font-size="8" fill="#94a3b8">2025</text>'
            f'<rect x="50" y="4" width="16" height="2.5" fill="{color}" rx="1"/>'
            f'<text x="68" y="10" font-size="8" fill="{color}" font-weight="700">2026</text>')
    svg += '</svg>'
    return f'<div class="chart-card"><div class="ch-title">{label}</div>{svg}</div>'

def build_yoy_section(t_2025, t_2026):
    leads = yoy_chart(t_2025, t_2026, 'leads', 'LEADS POR MES — 2026 vs 2025', '#3b82f6')
    cr    = yoy_chart(t_2025, t_2026, 'cr',    'CR% POR MES — 2026 vs 2025',   '#16a34a')
    return f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:18px;">{leads}{cr}</div>'

def shorten(s, n=46):
    s = (s.replace('LICENCIATURA EN ','Lic. ').replace('MAESTRÍA EN ','Mtra. ')
          .replace('INGENIERÍA ','Ing. ').replace('ADMINISTRACIÓN','Adm.')
          .replace('COMPUTACIONALES','Comp.').replace('ORGANIZACIONAL','Org.')
          .replace('BACHELOR OF SCIENCE IN ','BSc. ')
          .replace('BACHELOR OF BUSINESS ADMINISTRATION','BBA')
          .replace('MASTER OF ','MSc. ').replace('MASTER IN ','MSc. '))
    return s[:n] + ('...' if len(s) > n else '')

def cr_col(cr, avg):
    if cr >= avg * 1.25: return '#16a34a'
    if cr >= avg * 0.7:  return '#d97706'
    return '#dc2626'

def cr_bg(cr, avg):
    if cr >= avg * 1.25: return '#f0fdf4'
    if cr >= avg * 0.7:  return '#fffbeb'
    return '#fef2f2'

def avg_cr(prog_list):
    valid = [p for p in prog_list if p['may_l'] > 0]
    return round(sum(p['may_cr'] for p in valid) / max(1, len(valid)), 2)

# ── SVG spark line ─────────────────────────────────────────────────────────────
def spark(values, w=175, h=46, color='#3b82f6', fill=True, proj_i=4, is_cr=False):
    vals = [v or 0 for v in values]
    mx = max(vals) * 1.15 or 1
    lbl = lambda v: f'{fmt_cr(v)}%' if is_cr else fmt_k(v)
    def px(i): return round(8 + i * (w - 16) / (len(vals) - 1), 1)
    def py(v):  return round(h - 6 - v / mx * (h - 12), 1)
    pts = [(px(i), py(v)) for i, v in enumerate(vals)]
    solid = pts[:proj_i]; dash = pts[proj_i - 1:]
    ps  = 'M ' + ' L '.join(f'{x},{y}' for x, y in solid)
    pd_ = 'M ' + ' L '.join(f'{x},{y}' for x, y in dash)
    fp  = ps + f' L {solid[-1][0]},{h-6} L {solid[0][0]},{h-6} Z'
    s = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    if fill: s += f'<path d="{fp}" fill="{color}" opacity=".12"/>'
    s += f'<path d="{ps}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/>'
    s += f'<path d="{pd_}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="4,3" opacity=".7"/>'
    for i, (x, y) in enumerate(pts):
        op = '1' if i < proj_i else '.65'
        s += f'<circle cx="{x}" cy="{y}" r="3" fill="{color}" opacity="{op}"/>'
        # Label at every point
        label_y = max(9, y - 5)
        s += (f'<text x="{x}" y="{label_y}" font-size="7.5" fill="{color}" '
              f'text-anchor="middle" font-weight="700" opacity="{op}">{lbl(vals[i])}</text>')
    return s + '</svg>'

# ── Bar chart ──────────────────────────────────────────────────────────────────
def bar_chart(trend_list, key, label, color, unit='', W=330, H=100):
    vals = [g[key] for g in trend_list]
    mx = max(vals) * 1.2 or 1
    bw = 44; gap = 10; sx = 14
    bars = ''
    for i, (g, v) in enumerate(zip(trend_list, vals)):
        x = sx + i * (bw + gap)
        bh = round((v / mx) * (H - 32))
        ip = (i == 4)
        fill_ = 'none' if ip else color
        st = f'stroke="{color}" stroke-width="2" stroke-dasharray="5,3"' if ip else ''
        op = '.5' if ip else '.88'
        bars += f'<rect x="{x}" y="{H-28-bh}" width="{bw}" height="{bh}" rx="4" fill="{fill_}" {st} opacity="{op}"/>'
        bars += f'<text x="{x+bw//2}" y="{H-30-bh}" font-size="8" fill="{color}" text-anchor="middle" font-weight="700">{fmt_k(v)}{unit}</text>'
        mc = "#38bdf8" if ip else "#64748b"
        bars += f'<text x="{x+bw//2}" y="{H-10}" font-size="9" fill="{mc}" text-anchor="middle">{_m_label if ip else g["mes"]}</text>'
    return f'<div class="chart-card"><div class="ch-title">{label}</div><svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bars}</svg></div>'

# ── KPI row ────────────────────────────────────────────────────────────────────
def kpi_row(trend, prog_list, label):
    may = trend[4]; abr = trend[3]
    ac = avg_cr(prog_list)
    g = lambda cr: 'g' if cr >= 2.3 else ('o' if cr >= 1.5 else 'r')
    diff_cr   = round(may['cr'] - abr['cr'], 2)
    diff_str  = (f'+{diff_cr}pp vs Abr' if diff_cr >= 0 else f'{diff_cr}pp vs Abr')
    trend_cls = 'g' if may['cr'] >= abr['cr'] else 'r'
    return f'''<div class="kpi-row" id="kpis-{label}">
  <div class="kpi b"><div class="lbl">Leads {_m_label} ({_cd}d reales)</div><div class="val">{fmt_k(may["leads"])}</div><div class="sub">Abr: {fmt_k(abr["leads"])}</div></div>
  <div class="kpi n"><div class="lbl">Mats {_m_label} ({_cd}d reales)</div><div class="val">{fmt_k(may["mats"])}</div><div class="sub">Abr: {fmt_k(abr["mats"])}</div></div>
  <div class="kpi {g(may["cr"])}"><div class="lbl">CR {_m_label} (real)</div><div class="val">{fmt_cr(may["cr"])}%</div><div class="sub">Prom progs: {fmt_cr(ac)}%</div></div>
  <div class="kpi {trend_cls}"><div class="lbl">Tendencia CR</div><div class="val">{"↑ Sube" if may["cr"] >= abr["cr"] else "↓ Baja"}</div><div class="sub">{diff_str}</div></div>
</div>'''

# ── Program card ───────────────────────────────────────────────────────────────
def prog_card(p, avg, show_contact=True):
    cr  = p['may_cr'] if p.get('may_cr', 0) > 0 else p['abr_cr']  # Mayo real; fallback Abril
    cls = 'mas' if cr >= avg * 1.25 else ('mal' if cr < avg * 0.7 else 'ok')
    col = '#16a34a' if cls == 'mas' else ('#dc2626' if cls == 'mal' else '#d97706')
    tag = ('<span class="tag-mas">TRAER MAS</span>' if cls == 'mas' else
           '<span class="tag-cut">TRAER MENOS</span>' if cls == 'mal' else
           '<span class="tag-opt">MANTENER</span>')
    new_badge  = '<span style="background:#7c3aed;color:white;padding:2px 7px;border-radius:10px;font-size:9px;font-weight:800;">NUEVO</span>' if p.get('is_new') else ''
    vdrop      = p.get('vol_drop_pct', 0)
    drop_badge = (f'<span title="Caída de leads vs Abril 2025 (mismo mes)" style="background:#fee2e2;color:#dc2626;padding:2px 7px;border-radius:10px;font-size:9px;font-weight:800;border:1px solid #fca5a5;">📉 −{vdrop}% YoY</span>') if vdrop >= 25 else ''
    pricing = p.get('pricing','')
    pr_col  = {'PRICING ALTO':'#0369a1','PRICING MEDIO':'#0e7490','PRICING BAJO':'#64748b'}.get(pricing,'')
    pricing_badge = (f'<span style="background:{pr_col}22;color:{pr_col};padding:2px 7px;border-radius:10px;font-size:9px;font-weight:700;border:1px solid {pr_col}44;">'
                     f'{pricing.replace("PRICING ","")}</span>') if pr_col else ''
    diff_may  = round(cr - p['abr_cr'], 2)
    diff_str  = (f'+{diff_may}pp vs Abr' if diff_may >= 0 else f'{diff_may}pp vs Abr')
    diff_col  = '#16a34a' if diff_may >= 0 else '#dc2626'
    sp_cr    = spark(p['cr'],    w=175, h=46, color=col, is_cr=True)
    sp_leads = spark(p['leads'], w=175, h=46, color='#64748b', fill=False)
    tbl = '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:2px;margin-top:5px;">'
    for i, (m, l, mt, crm) in enumerate(zip(MONTHS, p['leads'], p['mats'], p['cr'])):
        ip = (i == 4)
        bg = 'rgba(56,189,248,.08)' if ip else 'transparent'
        bo = '2px dashed #38bdf8' if ip else '1px solid #f1f5f9'
        tbl += f'<div style="text-align:center;padding:3px 1px;background:{bg};border:{bo};border-radius:4px;">'
        if ip:
            tbl += f'<div style="color:#38bdf8;font-size:8px;font-weight:800;">May*</div>'
            tbl += f'<div style="color:#94a3b8;font-size:8px;font-style:italic;">proyec.</div>'
            tbl += f'<div style="color:#38bdf8;font-size:9px;font-weight:700;">{fmt_k(l)} leads</div>'
        else:
            tbl += f'<div style="color:#94a3b8;font-size:8px;">{m}</div>'
            tbl += f'<div style="font-weight:800;color:{col};font-size:10px;">{fmt_cr(crm)}%</div>'
            tbl += f'<div style="color:#64748b;font-size:9px;">{fmt_k(l)}</div>'
            tbl += f'<div style="color:#1e293b;font-weight:600;font-size:9px;">{fmt_k(mt)} mats</div>'
        tbl += '</div>'
    tbl += '</div>'
    return f'''<div class="prog-card {cls}">
  <div class="prog-head"><div class="prog-name">{shorten(p["prog"])}</div><div class="prog-cr" style="color:{col}">{fmt_cr(cr)}%</div>{tag}{new_badge}{pricing_badge}{drop_badge}</div>
  <div class="prog-meta">
    <span>May ({MAY_D}d): <b>{fmt_k(p["real_may_l"])}</b> leads · <b>{p["real_may_m"]}</b> mat</span>
    <span>Abr: <b>{fmt_k(p["abr_l"])}</b> leads</span>
    <span style="color:{diff_col};font-weight:700">{diff_str}</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:4px;">
    <div><div style="font-size:8px;color:#94a3b8;margin-bottom:1px;">CR % por mes</div>{sp_cr}</div>
    <div><div style="font-size:8px;color:#94a3b8;margin-bottom:1px;">Leads por mes</div>{sp_leads}</div>
  </div>{tbl}</div>'''

def build_vol_drop_section(prog_list, threshold=25):
    """YoY lead variation table — all programs with Abr 2025 baseline, sorted by variation."""
    # Include all programs with enough 2025 history (abr_2025_l >= 100)
    with_history = [p for p in prog_list if p.get('abr_2025_l', 0) >= 100]
    if not with_history:
        return ''

    # Compute variation for ALL (not just drops)
    def yoy_pct(p):
        a25 = p['abr_2025_l']
        a26 = p['abr_l']
        return round((a26 - a25) / a25 * 100, 1) if a25 > 0 else 0

    all_sorted = sorted(with_history, key=lambda x: yoy_pct(x))  # worst first

    rows = ''
    for p in all_sorted:
        a25  = p['abr_2025_l']
        a26  = p['abr_l']
        pct  = yoy_pct(p)
        diff = a26 - a25

        if pct <= -threshold:
            row_bg = '#fff8f8'; pct_c = '#dc2626' if pct <= -50 else '#d97706' if pct <= -35 else '#f59e0b'
            arrow = '↓'; sign = ''
        elif pct >= 15:
            row_bg = '#f0fdf4'; pct_c = '#16a34a'
            arrow = '↑'; sign = '+'
        else:
            row_bg = 'white'; pct_c = '#64748b'
            arrow = '→'; sign = '+' if pct >= 0 else ''

        bar_pct = min(100, abs(pct) * 1.5)
        bar_c   = pct_c

        may_cr  = p.get('may_cr', 0) or p.get('abr_cr', 0)
        cr_c2   = '#16a34a' if may_cr >= 2.5 else ('#d97706' if may_cr >= 1.5 else '#dc2626')

        rows += (
            f'<div style="display:grid;grid-template-columns:2fr 70px 70px 140px 80px 80px;'
            f'align-items:center;padding:6px 14px;border-bottom:1px solid #f1f5f9;gap:8px;background:{row_bg};">'
            f'<div style="font-size:11px;font-weight:600;color:#1e293b;">{new_badge(p["prog"])}{shorten(p["prog"],52)}</div>'
            f'<div style="font-size:11px;color:#64748b;text-align:right;">{fmt_k(a25)}</div>'
            f'<div style="font-size:11px;font-weight:700;color:{pct_c};text-align:right;">{fmt_k(a26)}</div>'
            f'<div style="display:flex;align-items:center;gap:6px;">'
            f'  <div style="width:80px;background:#f1f5f9;border-radius:4px;height:7px;">'
            f'    <div style="width:{bar_pct:.0f}%;height:7px;background:{bar_c};border-radius:4px;opacity:.75;"></div></div>'
            f'  <span style="font-size:11px;font-weight:800;color:{pct_c};white-space:nowrap;">'
            f'    {arrow} {sign}{pct:.1f}%</span>'
            f'</div>'
            f'<div style="font-size:10px;color:{pct_c};font-weight:700;text-align:right;">'
            f'{"+" if diff>=0 else ""}{fmt_k(diff)} leads</div>'
            f'<div style="font-size:11px;font-weight:700;color:{cr_c2};text-align:right;">'
            f'CR {fmt_cr(may_cr)}%</div>'
            f'</div>'
        )

    n_drops = sum(1 for p in with_history if yoy_pct(p) <= -threshold)
    n_gains = sum(1 for p in with_history if yoy_pct(p) >= 15)

    header = (
        f'<div style="display:grid;grid-template-columns:2fr 70px 70px 140px 80px 80px;'
        f'padding:7px 14px;gap:8px;background:#f8fafc;border-bottom:2px solid #e2e8f0;">'
        f'<div style="font-size:9px;font-weight:700;color:#475569;text-transform:uppercase;">Programa</div>'
        f'<div style="font-size:9px;font-weight:700;color:#475569;text-align:right;">Abr 2025</div>'
        f'<div style="font-size:9px;font-weight:700;color:#475569;text-align:right;">Abr 2026</div>'
        f'<div style="font-size:9px;font-weight:700;color:#475569;">Variación YoY</div>'
        f'<div style="font-size:9px;font-weight:700;color:#475569;text-align:right;">Leads ±</div>'
        f'<div style="font-size:9px;font-weight:700;color:#475569;text-align:right;">CR {_m_label}</div>'
        f'</div>'
    )

    return (
        f'<div style="background:white;border-radius:12px;border:1px solid #e2e8f0;'
        f'margin-bottom:18px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);">'
        f'<div style="background:#0f172a;padding:10px 16px;display:flex;align-items:center;gap:16px;">'
        f'<span style="color:white;font-size:13px;font-weight:800;">📊 Variación de leads vs mismo mes año anterior</span>'
        f'<span style="background:#fee2e2;color:#dc2626;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;">↓ {n_drops} programas caída ≥{threshold}%</span>'
        f'<span style="background:#dcfce7;color:#16a34a;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;">↑ {n_gains} programas crecimiento ≥15%</span>'
        f'<span style="color:#94a3b8;font-size:10px;">Abr 2025 → Abr 2026 · mismo mes, sin sesgo estacional</span>'
        f'</div>'
        f'{header}{rows}'
        f'</div>'
    )


def combo_bar_line_chart(programs, key_leads, key_cr, title='', W=860, H=270):
    """Bar chart (leads) + line chart (CR%) for a list of programs, sorted by CR ascending."""
    if not programs: return ''
    progs = sorted(programs, key=lambda x: x[key_cr])  # ascending CR
    n = len(progs)
    pad_l, pad_r, pad_t, pad_b = 48, 90, 32, 72  # bottom room for labels
    inner_w = W - pad_l - pad_r
    inner_h = H - pad_t - pad_b
    bar_w   = max(12, min(40, inner_w / n - 4))
    gap     = inner_w / n

    leads_vals = [p[key_leads] for p in progs]
    cr_vals    = [p[key_cr]    for p in progs]
    max_leads  = max(leads_vals) * 1.20 if leads_vals else 1
    max_cr     = max(cr_vals)    * 1.25 if cr_vals    else 1

    def bx(i): return pad_l + gap * i + gap / 2  # bar center x
    def by(v): return pad_t + inner_h - (v / max_leads * inner_h)  # bar top y
    def ly(v): return pad_t + inner_h - (v / max_cr    * inner_h)  # line y

    svg = f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="font-family:\'Segoe UI\',Arial,sans-serif;">'

    # Background
    svg += f'<rect width="{W}" height="{H}" fill="white" rx="8"/>'

    # Title
    if title:
        svg += f'<text x="{pad_l}" y="18" font-size="11" font-weight="700" fill="#475569">{title}</text>'

    # Y grid lines (leads, left scale)
    for i in range(5):
        yv = max_leads * i / 4
        y  = by(yv)
        svg += f'<line x1="{pad_l}" y1="{y}" x2="{W-pad_r}" y2="{y}" stroke="#f1f5f9" stroke-width="1"/>'
        svg += f'<text x="{pad_l-4}" y="{y+4}" font-size="9" fill="#94a3b8" text-anchor="end">{fmt_k(yv)}</text>'

    # Right Y axis labels (CR%)
    for i in range(5):
        cv = max_cr * i / 4
        y  = ly(cv)
        svg += f'<text x="{W-pad_r+6}" y="{y+4}" font-size="9" fill="#f97316" text-anchor="start">{fmt_cr(cv)}%</text>'

    # Bars (leads) + lead count label on top
    for i, p in enumerate(progs):
        x  = bx(i) - bar_w / 2
        bh = (p[key_leads] / max_leads * inner_h) if max_leads > 0 else 0
        yb = pad_t + inner_h - bh
        svg += f'<rect x="{x:.1f}" y="{yb:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="#4a90d9" rx="2" opacity=".85"/>'
        # Labels above bar: leads (blue) + mats (dark)
        lbl_leads = fmt_k(p[key_leads])
        lbl_mats  = str(int(p.get('real_may_m', 0)))
        label_y = max(pad_t + 20, yb - 4)
        svg += (f'<text x="{bx(i):.1f}" y="{label_y:.1f}" font-size="9" font-weight="700" '
                f'fill="#2563eb" text-anchor="middle">{lbl_leads}</text>')
        svg += (f'<text x="{bx(i):.1f}" y="{label_y + 11:.1f}" font-size="9" font-weight="700" '
                f'fill="#0f172a" text-anchor="middle">{lbl_mats} mats</text>')

    # Line (CR%)
    pts = [(bx(i), ly(p[key_cr])) for i, p in enumerate(progs)]
    if len(pts) > 1:
        path = 'M ' + ' L '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        svg += f'<path d="{path}" fill="none" stroke="#f97316" stroke-width="2.5" stroke-linejoin="round"/>'
    for i, (x, y) in enumerate(pts):
        cr_v = progs[i][key_cr]
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#f97316"/>'
        # Label: above point, avoid top edge
        lbl_y = max(pad_t + 10, y - 7)
        svg += f'<text x="{x:.1f}" y="{lbl_y:.1f}" font-size="9" font-weight="700" fill="#f97316" text-anchor="middle">{fmt_cr(cr_v)}%</text>'

    # X axis program labels (rotated, truncated)
    for i, p in enumerate(progs):
        x = bx(i)
        name = p['prog']
        # Strip "LICENCIATURA EN " / "MAESTRÍA EN " for brevity
        for pfx in ['LICENCIATURA EN ','MAESTRÍA EN ','MAESTRIA EN ','MÁSTER EN ','MASTER EN ','DOCTORADO EN ']:
            if name.upper().startswith(pfx): name = name[len(pfx):]; break
        name = name[:32] + ('…' if len(name) > 32 else '')
        # Add NEW dot if new
        dot = '● ' if p.get('is_new') else ''
        svg += (f'<text transform="translate({x:.1f},{pad_t+inner_h+10}) rotate(-38)" '
                f'font-size="9" fill="#475569" text-anchor="end" dominant-baseline="middle">'
                f'{dot}{name}</text>')

    # Axis lines
    ax_y = pad_t + inner_h
    svg += f'<line x1="{pad_l}" y1="{ax_y}" x2="{W-pad_r}" y2="{ax_y}" stroke="#e2e8f0" stroke-width="1.5"/>'
    svg += f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{ax_y}" stroke="#e2e8f0" stroke-width="1.5"/>'

    # Legend
    lx = W - pad_r + 8
    svg += f'<rect x="{lx}" y="{pad_t+8}" width="12" height="10" fill="#4a90d9" rx="2"/>'
    svg += f'<text x="{lx+16}" y="{pad_t+18}" font-size="9" fill="#475569">Leads</text>'
    svg += f'<line x1="{lx}" y1="{pad_t+30}" x2="{lx+12}" y2="{pad_t+30}" stroke="#f97316" stroke-width="2.5"/>'
    svg += f'<circle cx="{lx+6}" cy="{pad_t+30}" r="3.5" fill="#f97316"/>'
    svg += f'<text x="{lx+16}" y="{pad_t+34}" font-size="9" fill="#f97316">CR %</text>'

    svg += '</svg>'
    return svg


def build_nuevos_section(prog_list):
    """Highlighted panel for new programs launched in 2026 — with combo chart."""
    nuevos = [p for p in prog_list if p.get('is_new')]
    if not nuevos:
        return ''

    chart_svg = combo_bar_line_chart(
        nuevos, key_leads='real_may_l', key_cr='may_cr',
        title=f'Nuevos programas 2026 — {_m_label} real ({_cd} días) · barras = leads · línea = CR% · sin proyección',
        W=860, H=280
    )

    rows = ''
    for p in sorted(nuevos, key=lambda x: -x['may_cr']):
        may_cr  = p.get('may_cr', 0)
        cr_c    = '#16a34a' if may_cr >= 2 else '#d97706' if may_cr >= 1 else '#dc2626'
        tier    = p.get('pricing','')
        tier_html = (f'<span style="background:#1e40af;color:white;font-size:8px;font-weight:700;'
                     f'padding:1px 6px;border-radius:8px;margin-left:4px;">{tier}</span>') if tier else ''
        cr_str   = f'{fmt_cr(may_cr)}%' if may_cr > 0 else '—'
        rl_str   = fmt_k(p['real_may_l'])
        rm_str   = str(int(p['real_may_m']))
        rows += (
            f'<div style="display:flex;align-items:center;padding:7px 14px;border-bottom:1px solid rgba(124,58,237,.08);gap:10px;">'
            f'<div style="flex:1;font-size:11px;font-weight:600;color:#1e293b;">{p["prog"]}</div>'
            f'{tier_html}'
            f'<div style="font-size:10px;color:#94a3b8;white-space:nowrap;">{rl_str} leads</div>'
            f'<div style="font-size:10px;color:#475569;white-space:nowrap;margin-left:6px;">{rm_str} mats</div>'
            f'<div style="font-size:14px;font-weight:800;color:{cr_c};white-space:nowrap;margin-left:8px;min-width:50px;text-align:right;">{cr_str}</div>'
            f'</div>'
        )

    return (
        f'<div style="background:linear-gradient(135deg,#faf5ff 0%,#f3e8ff 100%);'
        f'border-radius:12px;border:2px solid #c4b5fd;margin-bottom:20px;overflow:hidden;">'
        f'<div style="background:#7c3aed;padding:10px 16px;display:flex;align-items:center;gap:10px;">'
        f'<span style="color:white;font-size:13px;font-weight:800;">✨ Nuevos Programas 2026</span>'
        f'<span style="color:rgba(255,255,255,.8);font-size:10px;">{len(nuevos)} programas · {_m_label} real {_cd} días · sin proyección</span>'
        f'</div>'
        f'<div style="padding:14px 14px 4px;">{chart_svg}</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid rgba(124,58,237,.15);margin-top:8px;">{rows}</div>'
        f'</div>'
    )

def prog_section(prog_list, avg, show_contact=True):
    mas = [p for p in prog_list if p['abr_cr'] >= avg * 1.25]
    ok  = [p for p in prog_list if avg * 0.7 <= p['abr_cr'] < avg * 1.25]
    mal = [p for p in prog_list if p['abr_cr'] < avg * 0.7]
    h  = f'<div class="alert ag"><span></span><div><b>TRAER MAS LEADS</b> — CR >= {round(avg*1.25,2)}%</div></div>'
    h += '<div class="prog-grid">' + ''.join(prog_card(p, avg) for p in mas) + '</div>'
    if ok:
        h += '<div class="sec-hdr" style="margin-top:20px;">Mantener volumen</div>'
        h += '<div class="prog-grid">' + ''.join(prog_card(p, avg) for p in ok) + '</div>'
    h += f'<div class="alert ae" style="margin-top:20px;"><span></span><div><b>TRAER MENOS / REVISAR</b> — CR < {round(avg*0.7,2)}%</div></div>'
    h += '<div class="prog-grid">' + ''.join(prog_card(p, avg) for p in mal) + '</div>'
    return h

# ── Programa × Canal: best/worst channels per program ─────────────────────────
def invert_canal_prog(canal_dict, min_canal_leads=30):
    prog_dict = {}
    for canal, rows in canal_dict.items():
        for r in rows:
            prog = r['prog']
            if r['leads'] < min_canal_leads:
                continue
            if prog not in prog_dict:
                prog_dict[prog] = []
            prog_dict[prog].append({'canal': canal, 'leads': r['leads'], 'mats': r['mats'], 'cr': r['cr']})
    for prog in prog_dict:
        prog_dict[prog].sort(key=lambda x: -x['cr'])
    return prog_dict

def build_prog_canal_section(canal_dict, prog_list, min_canal_leads=30):
    prog_canals = invert_canal_prog(canal_dict, min_canal_leads)
    prog_leads_map = {p['prog']: p['abr_l'] for p in prog_list} if prog_list else {}

    # Canal average CR: weighted by leads (true canal CR = total mats / total leads)
    canal_avg_cr = {}
    for canal, rows in canal_dict.items():
        total_leads = sum(r['leads'] for r in rows)
        total_mats  = sum(r['mats']  for r in rows)
        canal_avg_cr[canal] = round(total_mats / total_leads * 100, 2) if total_leads > 0 else 0

    progs_sorted = sorted(
        [(prog, canals) for prog, canals in prog_canals.items() if len(canals) >= 2],
        key=lambda x: -(prog_leads_map.get(x[0], 0) or sum(c['leads'] for c in x[1]))
    )
    if not progs_sorted:
        return '<p style="color:#94a3b8;padding:14px;">Sin datos suficientes.</p>'

    html = ''
    for prog, canals in progs_sorted:
        tot_l = sum(c['leads'] for c in canals)
        tot_m = sum(c['mats']  for c in canals)
        tot_cr = round(tot_m / tot_l * 100, 2) if tot_l > 0 else 0
        cr_c = '#16a34a' if tot_cr >= 3 else ('#d97706' if tot_cr >= 1.5 else '#dc2626')
        max_cr = max(c['cr'] for c in canals) if canals else 1

        html += (f'<div style="margin-bottom:18px;">'
                 f'<div style="display:flex;align-items:center;gap:12px;padding:9px 14px;'
                 f'background:#0f172a;border-radius:8px 8px 0 0;">'
                 f'<div style="font-size:12px;font-weight:800;color:white;flex:1;">{new_badge(prog, 9)}{shorten(prog, 56)}</div>'
                 f'<div style="font-size:10px;color:#94a3b8;">{fmt_k(tot_l)} leads acum.</div>'
                 f'<div style="font-size:14px;font-weight:800;color:{cr_c};">CR prom {fmt_cr(tot_cr)}%</div>'
                 f'</div>'
                 f'<div style="background:white;border-radius:0 0 8px 8px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,.07);">')

        for c in canals:
            bw = round(c['cr'] / max_cr * 100) if max_cr > 0 else 0
            c_avg = canal_avg_cr.get(c['canal'], tot_cr)
            above_canal  = c['cr'] >= c_avg * 1.25   # programa supera promedio del canal
            below_canal  = c['cr'] <  c_avg * 0.75   # programa está por debajo
            # Canales con volumen orgánico/limitado — no se escalan con presupuesto
            CANALES_TECHO = {'Google Brand', 'Google - Brand', 'Inbound', 'RRSS - Organico',
                             'RRSS Organico', 'Blog', 'Referidos', 'Sitio Web'}
            canal_techo = any(t.lower() in c['canal'].lower() for t in
                              ['brand', 'inbound', 'organico', 'orgánico', 'blog', 'referido', 'sitio web'])

            ABS_MIN_ESCALAR = ABR_CR_MX        # piso dinámico = CR real Abr MX
            ABS_MIN_MEJOR   = ABR_CR_MX * 0.75
            if above_canal and c['cr'] >= ABS_MIN_ESCALAR and not canal_techo:
                bar_c = '#16a34a'; verdict = 'ESCALAR'; v_bg = '#dcfce7'; v_col = '#15803d'
            elif above_canal and c['cr'] >= ABS_MIN_ESCALAR and canal_techo:
                bar_c = '#16a34a'; verdict = 'OPTIMIZAR'; v_bg = '#dcfce7'; v_col = '#15803d'
            elif above_canal and c['cr'] >= ABS_MIN_MEJOR:
                bar_c = '#d97706'; verdict = 'MEJOR DEL CANAL'; v_bg = '#fef9c3'; v_col = '#92400e'
            elif below_canal:
                bar_c = '#d97706'; verdict = 'REVISAR'; v_bg = '#fef3c7'; v_col = '#92400e'
            else:
                bar_c = '#94a3b8'; verdict = 'MANTENER'; v_bg = '#f1f5f9'; v_col = '#475569'

            techo_note = ' · volumen limitado por demanda orgánica' if canal_techo else ''
            avg_label = f'prom canal {fmt_cr(c_avg)}%{techo_note}'
            verdict_html = (f'<span title="vs {avg_label}" style="background:{v_bg};color:{v_col};padding:2px 8px;'
                            f'border-radius:10px;font-size:9px;font-weight:800;">{verdict}</span>')

            html += (f'<div style="display:flex;align-items:center;gap:10px;padding:7px 14px;'
                     f'border-bottom:1px solid #f8fafc;">'
                     f'<div style="width:170px;font-size:11px;font-weight:600;color:#374151;flex-shrink:0;">{c["canal"]}</div>'
                     f'<div style="flex:1;background:#f1f5f9;border-radius:4px;height:9px;">'
                     f'<div style="width:{bw}%;height:9px;background:{bar_c};border-radius:4px;opacity:.8;"></div></div>'
                     f'<div style="width:46px;text-align:right;font-weight:800;font-size:14px;color:{bar_c};">{fmt_cr(c["cr"])}%</div>'
                     f'<div style="width:60px;text-align:right;font-size:10px;color:#94a3b8;">{fmt_k(c["leads"])} leads</div>'
                     f'<div style="width:80px;text-align:right;">{verdict_html}</div>'
                     f'</div>')

        html += '</div></div>'
    return html

# ── Canal recommendations: per canal, which programs to push/cut ───────────────
def canal_recommendations_html(canal_dict):
    """For each canal: ranked table of ALL programs — shares sum to 100%."""
    if not canal_dict:
        return ''

    CANALES_TECHO = ['brand', 'inbound', 'organico', 'orgánico', 'blog', 'referido', 'sitio web']
    ABS_MIN_ESCALAR = ABR_CR_MX   # piso dinámico = CR real Abr MX

    cards = ''
    for canal, rows in canal_dict.items():
        if not rows: continue
        # ── Use MAY data throughout ──
        total_leads = sum(r.get('may_leads', 0) for r in rows)
        total_mats  = sum(r.get('may_mats',  0) for r in rows)
        # fallback to cumulative if May has no data yet
        if total_leads == 0:
            total_leads = sum(r['leads'] for r in rows)
            total_mats  = sum(r['mats']  for r in rows)
            use_may = False
        else:
            use_may = True
        canal_cr    = round(total_mats / total_leads * 100, 2) if total_leads > 0 else 0
        canal_techo = any(t in canal.lower() for t in CANALES_TECHO)

        # Sort all programs by May leads desc — all shown so shares sum to 100%
        def _sort_key(r):
            return -(r.get('may_leads', 0) if use_may else r['leads'])
        all_sorted = sorted(rows, key=_sort_key)
        top_leads  = max((_sort_key(r) * -1 for r in all_sorted), default=1)
        max_share  = top_leads / total_leads * 100 if total_leads > 0 else 1

        if canal_cr >= 3:     hcol = '#16a34a'; hbg = '#f0fdf4'
        elif canal_cr >= 1.5: hcol = '#d97706'; hbg = '#fffbeb'
        else:                 hcol = '#dc2626'; hbg = '#fef2f2'

        period_lbl = f'{_m_label} {_cd}d' if use_may else 'Acum.'
        techo_badge = ('<span style="font-size:9px;background:#e0e7ff;color:#3730a3;'
                       'padding:2px 7px;border-radius:8px;font-weight:700;">VOLUMEN LIMITADO</span>'
                       if canal_techo else '')
        header = (
            f'<div style="background:{hbg};border-bottom:2px solid {hcol};'
            f'padding:9px 14px;display:flex;align-items:center;gap:10px;">'
            f'<div style="font-size:13px;font-weight:800;color:#0f172a;flex:1;">{canal}</div>'
            f'<div style="font-size:11px;font-weight:700;color:{hcol};">CR {_m_label} {fmt_cr(canal_cr)}%</div>'
            f'<div style="font-size:10px;color:#64748b;">{fmt_k(total_leads)} leads {period_lbl}</div>'
            f'{techo_badge}</div>'
        )

        col_hdr = (
            '<div style="display:grid;grid-template-columns:1fr 120px 50px 56px 72px;'
            'padding:4px 12px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">'
            '<div style="font-size:8px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;">Programa</div>'
            '<div style="font-size:8px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;text-align:center;">% del canal ({_m_label})</div>'
            '<div style="font-size:8px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;text-align:right;">CR Acum</div>'
            '<div style="font-size:8px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;text-align:right;">CR {_m_label}</div>'
            '<div style="font-size:8px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;text-align:right;">Acción</div>'
            '</div>'
        )

        prog_rows_html = ''
        for i, r in enumerate(all_sorted):
            row_leads = r.get('may_leads', 0) if use_may else r['leads']
            share     = round(row_leads / total_leads * 100, 1) if total_leads > 0 else 0
            cr_val    = r.get('may_cr') or r['cr']
            above     = cr_val >= canal_cr * 1.25
            below     = cr_val <  canal_cr * 0.75
            if above and cr_val >= ABS_MIN_ESCALAR and not canal_techo:
                bdg_txt = 'PRIORIZAR'; bdg_bg = '#dcfce7'; bdg_col = '#15803d'
            elif above and cr_val >= ABS_MIN_ESCALAR and canal_techo:
                bdg_txt = 'MANTENER';  bdg_bg = '#dbeafe'; bdg_col = '#1d4ed8'
            elif below:
                bdg_txt = 'REVISAR';   bdg_bg = '#fef3c7'; bdg_col = '#92400e'
            else:
                bdg_txt = 'NORMAL';    bdg_bg = '#f1f5f9'; bdg_col = '#94a3b8'

            cr_col  = '#16a34a' if cr_val >= canal_cr else '#dc2626'
            row_bg  = '#ffffff' if i % 2 == 0 else '#f8fafc'
            bar_pct = round(share / max_share * 90) if max_share > 0 else 0

            cr_acum     = r['cr']
            cr_acum_col = '#16a34a' if cr_acum >= canal_cr else '#dc2626'
            prog_rows_html += (
                f'<div style="display:grid;grid-template-columns:1fr 120px 50px 56px 72px;'
                f'padding:5px 12px;background:{row_bg};border-bottom:1px solid #f1f5f9;align-items:center;">'
                # Name with NEW badge
                f'<div style="font-size:10px;font-weight:600;color:#1e293b;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding-right:6px;" '
                f'title="{r["prog"]}">{new_badge(r["prog"])}{r["prog"]}</div>'
                # Share bar + %
                f'<div style="display:flex;align-items:center;gap:5px;padding:0 8px;">'
                f'<div style="flex:1;background:#e2e8f0;border-radius:3px;height:5px;">'
                f'<div style="width:{bar_pct}%;height:5px;background:{hcol};border-radius:3px;opacity:.65;"></div>'
                f'</div>'
                f'<span style="font-size:9px;font-weight:700;color:#475569;white-space:nowrap;min-width:32px;text-align:right;">{share:.1f}%</span>'
                f'</div>'
                # CR Acum
                f'<div style="font-size:10px;font-weight:800;color:{cr_acum_col};text-align:right;">{fmt_cr(cr_acum)}%</div>'
                # CR {_m_label}
                f'<div style="font-size:10px;font-weight:800;color:{cr_col};text-align:right;">{fmt_cr(cr_val)}%</div>'
                # Badge
                f'<div style="text-align:right;">'
                f'<span style="font-size:8px;font-weight:800;background:{bdg_bg};color:{bdg_col};'
                f'padding:2px 6px;border-radius:4px;white-space:nowrap;">{bdg_txt}</span>'
                f'</div>'
                f'</div>'
            )

        card = (
            f'<div style="background:white;border-radius:10px;border:1px solid #e2e8f0;'
            f'overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);">'
            f'{header}{col_hdr}{prog_rows_html}</div>'
        )
        cards += card

    return f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:14px;margin-bottom:24px;">{cards}</div>'

# ── Canal monthly trend chart ──────────────────────────────────────────────────
def canal_monthly_chart(months_data, W=780, H=200):
    """Bar (leads) + line (CR%) chart for monthly canal data."""
    if not months_data: return ''
    n = len(months_data)
    pad_l, pad_r, pad_t, pad_b = 44, 50, 28, 42
    inner_w = W - pad_l - pad_r
    inner_h = H - pad_t - pad_b
    bar_w   = max(10, inner_w / n - 5)
    gap     = inner_w / n

    leads_vals = [m['leads'] for m in months_data]
    cr_vals    = [m['cr']    for m in months_data]
    max_l = max(leads_vals) * 1.25 if any(leads_vals) else 1
    max_cr = max(cr_vals)   * 1.35 if any(cr_vals) else 1

    def bx(i): return pad_l + gap * i + gap / 2
    def by(v): return pad_t + inner_h - (v / max_l * inner_h)  if max_l > 0 else pad_t + inner_h
    def ly(v): return pad_t + inner_h - (v / max_cr * inner_h) if max_cr > 0 else pad_t + inner_h

    # Separator index: where 2026 starts (after 8 months of 2025)
    sep_i = 8

    svg = f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="font-family:\'Segoe UI\',Arial,sans-serif;display:block;">'
    svg += f'<rect width="{W}" height="{H}" fill="white" rx="6"/>'

    # Shaded 2026 region
    x_sep = bx(sep_i) - gap / 2
    svg += f'<rect x="{x_sep:.1f}" y="{pad_t}" width="{W - pad_r - x_sep:.1f}" height="{inner_h}" fill="#eff6ff" rx="0" opacity="0.6"/>'
    svg += f'<text x="{x_sep + 4:.1f}" y="{pad_t + 10}" font-size="8" fill="#93c5fd">2026</text>'
    svg += f'<text x="{pad_l + 4}" y="{pad_t + 10}" font-size="8" fill="#cbd5e1">2025</text>'

    # Grid lines
    for i in range(4):
        yv = max_l * i / 3
        y  = by(yv)
        svg += f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W-pad_r}" y2="{y:.1f}" stroke="#f1f5f9" stroke-width="1"/>'
        svg += f'<text x="{pad_l-4}" y="{y+4:.1f}" font-size="8" fill="#94a3b8" text-anchor="end">{fmt_k(yv)}</text>'

    # Right axis CR%
    for i in range(4):
        cv = max_cr * i / 3
        y  = ly(cv)
        svg += f'<text x="{W-pad_r+4}" y="{y+4:.1f}" font-size="8" fill="#f97316" text-anchor="start">{fmt_cr(cv)}%</text>'

    # Bars
    for i, m in enumerate(months_data):
        is_proj = m['mes'].endswith('*')
        x  = bx(i) - bar_w / 2
        bh = (m['leads'] / max_l * inner_h) if max_l > 0 else 0
        yb = pad_t + inner_h - bh
        fill = '#93c5fd' if is_proj else ('#4a90d9' if i >= sep_i else '#94a3b8')
        svg += f'<rect x="{x:.1f}" y="{yb:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{fill}" rx="2" opacity=".85"/>'
        # Lead label above bar (only if enough height)
        if bh > 14:
            lbl = fmt_k(m['leads'])
            lbl_y = max(pad_t + 12, yb - 3)
            svg += (f'<text x="{bx(i):.1f}" y="{lbl_y:.1f}" font-size="7.5" font-weight="700" '
                    f'fill="#1e40af" text-anchor="middle">{lbl}</text>')

    # CR% line
    pts = [(bx(i), ly(m['cr'])) for i, m in enumerate(months_data) if m['cr'] > 0]
    if len(pts) > 1:
        path = 'M ' + ' L '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        svg += f'<path d="{path}" stroke="#f97316" stroke-width="2" fill="none" opacity=".9"/>'
    for i, m in enumerate(months_data):
        if m['cr'] > 0:
            x, y = bx(i), ly(m['cr'])
            svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#f97316"/>'
            lbl_y = max(pad_t + 8, y - 5)
            svg += (f'<text x="{x:.1f}" y="{lbl_y:.1f}" font-size="7.5" font-weight="700" '
                    f'fill="#ea580c" text-anchor="middle">{fmt_cr(m["cr"])}%</text>')

    # X axis labels
    for i, m in enumerate(months_data):
        svg += (f'<text x="{bx(i):.1f}" y="{H - 6}" font-size="8" fill="#64748b" '
                f'text-anchor="middle">{m["mes"]}</text>')

    # Legend
    svg += (f'<circle cx="{pad_l}" cy="14" r="4" fill="#4a90d9"/>'
            f'<text x="{pad_l+8}" y="18" font-size="8" fill="#475569">Leads</text>'
            f'<circle cx="{pad_l+60}" cy="14" r="4" fill="#f97316"/>'
            f'<text x="{pad_l+68}" y="18" font-size="8" fill="#475569">CR%</text>')
    svg += '</svg>'
    return svg

# ── Canal x Prog table (kept for internal use) ─────────────────────────────────
def canal_section(canal_dict, prefix, trend_dict=None):
    if not canal_dict:
        return '<p style="color:#94a3b8;padding:14px;">Sin datos de canal para este filtro.</p>'
    trend_dict = trend_dict or {}
    tabs = '<div class="canal-tabs">'
    panes = ''
    for i, (canal, rows) in enumerate(canal_dict.items()):
        on = ' on' if i == 0 else ''
        safe = canal.replace(' ', '_').replace('/', '_').replace('-', '_')
        avg_c = sum(r['cr'] for r in rows) / max(1, len(rows))
        rows_s = sorted(rows, key=lambda r: -r['leads'])
        tabs += f'<button class="canal-tab{on}" onclick="showCanal(\'{prefix}\',\'{safe}\')" id="ctab-{prefix}-{safe}">{canal}</button>'

        # Monthly trend chart for this canal
        trend_chart = ''
        if canal in trend_dict:
            trend_chart = (
                f'<div style="margin-bottom:14px;background:#f8fafc;border-radius:8px;padding:10px 12px;">'
                f'<div style="font-size:10px;font-weight:700;color:#64748b;margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em;">'
                f'Evolución mensual · Leads &amp; CR% · May 2025 → May 2026</div>'
                f'{canal_monthly_chart(trend_dict[canal])}'
                f'</div>'
            )

        panes += f'<div class="canal-pane{on}" id="cpane-{prefix}-{safe}">{trend_chart}</div>'
    tabs += '</div>'
    return tabs + panes

# ── Medio card (MX ONLY) ───────────────────────────────────────────────────────
MEDIO_META = {
    'Infobip':              ('cut','#dc2626','AUDITAR','86% de leads nunca contactados. Problema CRM, no el canal.'),
    'Cleverclick':          ('cut','#dc2626','AUDITAR','CR bajo. Revisar calidad de leads y segmentacion.'),
    'Facebook - Regular':   ('cut','#dc2626','CORTAR','CR < 1%. Muy bajo retorno vs volumen invertido.'),
    'Atom':                 ('cut','#dc2626','CORTAR','CR 0.06%. Cero ROI.'),
    'Click To Whatsapp Bot':('cut','#dc2626','CORTAR','CR ~0.07%. Sin conversion.'),
    'Google Search':        ('opt','#d97706','OPTIMIZAR','CR 2-3%. Alto volumen. Revisar palabras clave.'),
    'Educaedu':             ('opt','#d97706','OPTIMIZAR','CR variable por programa.'),
    'Lqqa':                 ('cut','#dc2626','AUDITAR','CR < 1%.'),
    'Edukapp':              ('cut','#dc2626','AUDITAR','CR muy bajo.'),
    'Sitio Web':            ('inv','#16a34a','INVERTIR MAS','CR estable 2.5%+.'),
    'RRSS - Organico':      ('inv','#16a34a','INVERTIR MAS','CR 5%+. Costo bajo.'),
    'Tiktok':               ('opt','#d97706','OPTIMIZAR','CR moderado.'),
    'Inbound':              ('inv','#16a34a','INVERTIR MAS','Mejor CR del mix. 14%+.'),
    'Bing':                 ('inv','#16a34a','INVERTIR MAS','CR 7%+. Muy eficiente.'),
    'Referidos':            ('inv','#16a34a','INVERTIR MAS','CR alto historico. Auditar caida reciente.'),
}

def _medio_rows(medio_key):
    """Get rows list from MEDIO dict (handles both old list and new {'rows':...} format)."""
    d = MEDIO.get(medio_key, {})
    return d['rows'] if isinstance(d, dict) else d

def _medio_alert(medio_key):
    d = MEDIO.get(medio_key, {})
    return d.get('alert') if isinstance(d, dict) else None

def medio_card(medio_key, rows, alert=None):
    note = MEDIO_META.get(medio_key, ('opt','','',''))[3]
    may_row  = next((r for r in rows if 'May' in r['mes']), None)
    hist     = [r for r in rows if 'May' not in r['mes'] and r['leads'] > 0]
    may_cr   = may_row['cr']   if may_row else 0
    may_l    = may_row['leads'] if may_row else 0
    hist_cr  = round(sum(r['cr'] for r in hist) / len(hist), 2) if hist else may_cr

    if may_cr >= 2.5:   cls = 'inv'; col = '#16a34a'; verdict = 'INVERTIR MAS'
    elif may_cr >= 1.5: cls = 'opt'; col = '#d97706'; verdict = 'OPTIMIZAR'
    else:               cls = 'cut'; col = '#dc2626'; verdict = 'REVISAR'

    if hist_cr > 0:
        chg = round((may_cr - hist_cr) / hist_cr * 100, 0)
        if chg >= 15:   trend_badge = f'<span style="background:#dcfce7;color:#15803d;padding:2px 7px;border-radius:8px;font-size:9px;font-weight:800;margin-left:6px;">↑ +{chg:.0f}% vs hist.</span>'
        elif chg <= -15:trend_badge = f'<span style="background:#fee2e2;color:#dc2626;padding:2px 7px;border-radius:8px;font-size:9px;font-weight:800;margin-left:6px;">↓ {chg:.0f}% vs hist.</span>'
        else:            trend_badge = ''
    else:
        trend_badge = ''

    tag_cls = 'tag-mas' if cls == 'inv' else ('tag-cut' if cls == 'cut' else 'tag-opt')
    h = f'<div class="medio-card {cls}"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">'
    h += f'<div style="font-size:13px;font-weight:800;">{medio_key}</div>'
    h += f'<span class="{tag_cls}">{verdict}</span>'
    h += f'<span style="font-size:10px;color:#64748b;">CR {_m_label}:<b style="color:{col}">{fmt_cr(may_cr)}%</b></span>'
    h += trend_badge
    h += '</div>'

    # ── YoY contactación alert ──
    if alert:
        parts = []
        if alert['diff_pc'] <= -5:
            parts.append(f'Contactación: {alert["pc_26"]:.0f}% vs {alert["pc_25"]:.0f}% en {alert["mes"]} 2025 (<b style="color:#dc2626">{alert["diff_pc"]:+.1f}pp</b>)')
        if alert['diff_pce'] <= -5:
            parts.append(f'Contactación efectiva: {alert["pce_26"]:.0f}% vs {alert["pce_25"]:.0f}% (<b style="color:#dc2626">{alert["diff_pce"]:+.1f}pp</b>)')
        if parts:
            h += (f'<div style="background:#fef2f2;border-left:3px solid #dc2626;padding:7px 10px;'
                  f'border-radius:4px;margin-bottom:8px;font-size:10px;color:#1e293b;">'
                  f'<span style="font-weight:800;color:#dc2626;">⚠ Contactación baja vs año anterior &nbsp;·&nbsp; {alert["mes"]} 2025→2026</span><br>'
                  + '<br>'.join(parts) + '</div>')

    if note: h += f'<div style="font-size:10px;color:#64748b;margin-bottom:8px;">{note}</div>'

    # Table header with prior year columns
    h += '<table style="width:100%;border-collapse:collapse;font-size:10px;"><thead><tr style="color:#94a3b8;font-size:9px;">'
    h += ('<th style="padding:3px 4px;text-align:left">Mes</th>'
          '<th style="text-align:right;padding:3px 4px">Leads</th>'
          '<th style="text-align:right;padding:3px 4px">%Cont.</th>'
          '<th style="text-align:right;padding:3px 4px;color:#94a3b8;">aa</th>'
          '<th style="text-align:right;padding:3px 4px">%Ef.</th>'
          '<th style="text-align:right;padding:3px 4px;color:#94a3b8;">aa</th>'
          '<th style="text-align:right;padding:3px 4px">Ventas</th>'
          '<th style="text-align:right;padding:3px 4px">CR%</th></tr></thead><tbody>')

    for r in rows:
        ip  = any(ml in r['mes'] for ml in [_m_label, 'May*', 'Jun*'])
        rs  = 'background:rgba(56,189,248,.07);' if ip else ''
        cc  = cr_col(r['cr'], 2.0); cb = cr_bg(r['cr'], 2.0)
        pc  = r.get('pct_contact', 0)
        pce = r.get('pct_contact_efectivo', 0)
        py  = r.get('py')  # prior year dict or None

        pc_col  = '#16a34a' if pc  >= 50 else ('#d97706' if pc  >= 25 else '#dc2626')
        pce_col = '#16a34a' if pce >= 35 else ('#d97706' if pce >= 20 else '#dc2626')

        # Prior year cells
        if py and py['leads'] > 0:
            pc_py  = py['pct_contact']
            pce_py = py['pct_contact_efectivo']
            pc_diff  = pc  - pc_py
            pce_diff = pce - pce_py
            pc_aa_col  = '#16a34a' if pc_diff  >= 0 else '#dc2626'
            pce_aa_col = '#16a34a' if pce_diff >= 0 else '#dc2626'
            pc_aa_html  = f'<td style="padding:4px;text-align:right;color:{pc_aa_col};font-size:9px;">{pc_diff:+.0f}pp</td>'
            pce_aa_html = f'<td style="padding:4px;text-align:right;color:{pce_aa_col};font-size:9px;">{pce_diff:+.0f}pp</td>'
        else:
            pc_aa_html  = '<td style="padding:4px;text-align:right;color:#cbd5e1;font-size:9px;">—</td>'
            pce_aa_html = '<td style="padding:4px;text-align:right;color:#cbd5e1;font-size:9px;">—</td>'

        h += f'<tr style="{rs}"><td style="padding:4px;font-weight:{"800" if ip else "600"};color:{"#38bdf8" if ip else "#475569"}">{r["mes"]}</td>'
        h += f'<td style="padding:4px;text-align:right">{fmt_k(r["leads"])}</td>'
        h += f'<td style="padding:4px;text-align:right;color:{pc_col};font-weight:700">{pc:.0f}%</td>'
        h += pc_aa_html
        h += f'<td style="padding:4px;text-align:right;color:{pce_col};font-weight:700">{pce:.0f}%</td>'
        h += pce_aa_html
        h += f'<td style="padding:4px;text-align:right;font-weight:700">{fmt_k(r["ventas"])}</td>'
        h += f'<td style="padding:4px;text-align:right"><span style="background:{cb};color:{cc};padding:2px 6px;border-radius:10px;font-weight:800;font-size:10px">{fmt_cr(r["cr"])}%</span></td></tr>'
    h += '</tbody></table>'
    cr_vals = [r['cr'] for r in rows]; lv = [r['leads'] for r in rows]
    h += f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">'
    h += f'<div><div style="font-size:8px;color:#94a3b8;margin-bottom:1px;">CR% tendencia</div>{spark(cr_vals,w=175,h=44,color=col,is_cr=True)}</div>'
    h += f'<div><div style="font-size:8px;color:#94a3b8;margin-bottom:1px;">Leads tendencia</div>{spark(lv,w=175,h=44,color="#64748b",fill=False)}</div>'
    h += '</div></div>'
    return h

# ── Country summary card (for overview ranking) ────────────────────────────────
def country_summary_card(pais, info):
    trend = info['trend']
    may = trend[4]; abr = trend[3]
    cr_c = '#16a34a' if may['cr'] >= 2.5 else ('#d97706' if may['cr'] >= 1.5 else '#dc2626')
    diff = round(may['cr'] - abr['cr'], 2)
    diff_str = (f'+{diff}pp vs Abr' if diff >= 0 else f'{diff}pp vs Abr')
    diff_col = '#16a34a' if diff >= 0 else '#dc2626'
    sp = spark([g['cr'] for g in trend], w=120, h=36, color=cr_c, fill=False, is_cr=True)
    return f'''<div style="background:white;border-radius:8px;padding:10px 12px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:3px solid {cr_c};display:flex;align-items:center;gap:10px;">
  <div style="flex:1;">
    <div style="font-size:12px;font-weight:800;">{pais}</div>
    <div style="font-size:10px;color:#64748b;margin-top:2px;">{fmt_k(may["leads"])} leads · {fmt_k(may["mats"])} mat · {_m_label}</div>
  </div>
  {sp}
  <div style="text-align:right;">
    <div style="font-size:18px;font-weight:800;color:{cr_c}">{fmt_cr(may["cr"])}%</div>
    <div style="font-size:10px;color:{diff_col};font-weight:700">{diff_str}</div>
  </div>
</div>'''

# ── Pricing × CR matrix ────────────────────────────────────────────────────────
def build_pricing_matrix_html(prog_list, avg_cr_val):
    # Use combined_cr (full-year real mats/leads) — stable, no partial-month distortion
    # may_cr is unreliable: 20-day leads vs full-month mats from prior-month leads
    def pcr(p): return p.get('combined_cr') or p.get('abr_cr', 0)

    def split(progs):
        good = sorted([p for p in progs if pcr(p) >= avg_cr_val], key=lambda x: -x['abr_l'])
        bad  = sorted([p for p in progs if pcr(p) <  avg_cr_val], key=lambda x: -x['abr_l'])
        return good, bad

    alto  = [p for p in prog_list if p.get('pricing') == 'PRICING ALTO']
    medio = [p for p in prog_list if p.get('pricing') == 'PRICING MEDIO']
    bajo  = [p for p in prog_list if p.get('pricing') == 'PRICING BAJO']

    alto_good,  alto_bad  = split(alto)
    medio_good, medio_bad = split(medio)
    bajo_good,  bajo_bad  = split(bajo)

    high_bad  = sorted(alto_bad  + medio_bad,  key=lambda x: -x['abr_l'])
    high_good = sorted(alto_good + medio_good, key=lambda x: -x['abr_l'])

    def prog_row(p):
        cr = pcr(p)
        cr_c = '#16a34a' if cr >= avg_cr_val else '#dc2626'
        new_dot = new_badge(p['prog'], 8)
        return (f'<div style="display:flex;align-items:center;padding:5px 10px;border-bottom:1px solid #f1f5f9;font-size:10px;">'
                f'<div style="flex:1;font-weight:600;">{new_dot}{shorten(p["prog"],40)}</div>'
                f'<div style="font-weight:800;color:{cr_c};white-space:nowrap;margin-left:8px;">{fmt_cr(cr)}%</div>'
                f'<div style="color:#94a3b8;white-space:nowrap;margin-left:6px;">{fmt_k(p["abr_l"])} leads Abr</div>'
                f'</div>')

    def quadrant(icon, title, color, bg, progs, desc):
        body = ''.join(prog_row(p) for p in progs[:15])
        if len(progs) > 15:
            body += f'<div style="color:#94a3b8;font-size:9px;padding:4px 10px;">+{len(progs)-15} más</div>'
        if not progs:
            body = '<div style="color:#94a3b8;font-size:10px;padding:10px;">Sin programas en este cuadrante</div>'
        return (f'<div style="background:{bg};border-radius:10px;border:2px solid {color};overflow:hidden;">'
                f'<div style="background:{color};padding:8px 12px;">'
                f'<div style="color:white;font-size:12px;font-weight:800;">{icon} {title}</div>'
                f'<div style="color:rgba(255,255,255,.85);font-size:9px;margin-top:2px;">{desc}</div></div>'
                f'{body}</div>')

    q_urgente  = quadrant('🔴','PRIORIDAD MÁXIMA','#dc2626','#fff8f8', high_bad,
                          f'Precio ALTO/MEDIO + CR < {avg_cr_val}% → cada mat perdida vale más. Revisar seguimiento y creatividades.')
    q_escalar  = quadrant('🟢','ESCALAR CAPTACIÓN','#16a34a','#f0fdf4', high_good,
                          f'Precio ALTO/MEDIO + CR ≥ {avg_cr_val}% → los leads acá generan más ingreso. Aumentar presupuesto.')
    q_precio   = quadrant('🟡','EVALUAR PRECIO','#d97706','#fffbeb', bajo_good,
                          f'Precio BAJO + CR alto → convierten bien pero el ticket es bajo. ¿Se puede subir precio?')
    q_depurar  = quadrant('⚫','DEPURAR','#64748b','#f8fafc', bajo_bad,
                          f'Precio BAJO + CR bajo → bajo retorno. Revisar si vale la pena mantener volumen de captación.')

    note = (f'<div class="alert ainfo"><span>i</span><div>CR anual combinado (mats reales / leads reales 2026) vs promedio MX ({avg_cr_val}%) · '
            f'Pricing tier desde tabla oficial · Solo programas MX con precio asignado · '
            f'<span style="background:#7c3aed;color:white;padding:1px 5px;border-radius:8px;font-size:9px;font-weight:800;">NEW</span> = lanzado en 2026</div></div>')

    matrix = (f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
              f'<div>{q_urgente}</div><div>{q_escalar}</div>'
              f'<div>{q_depurar}</div><div>{q_precio}</div>'
              f'</div>')

    return note + matrix

# ── Medios section ─────────────────────────────────────────────────────────────
PRIO = ['Inbound','Bing','RRSS - Organico','Sitio Web','Referidos',
        'Google Search','Educaedu','Tiktok','Google pmax','Cyceducaedu',
        'Facebook - Regular','Infobip','Cleverclick','Lqqa','Edukapp','Atom','Click To Whatsapp Bot',
        'Primerpaso','Linkedin','Otros Organico','Pixel','NO IDENTIFICADO','Test - Google']

def _may_cr_of(medio_key):
    rows = _medio_rows(medio_key)
    row = next((r for r in rows if 'May' in r['mes']), None)
    return row['cr'] if row else 0

def build_medios_html():
    EXCLUIR = {'NO IDENTIFICADO', 'Test - Google', 'Pixel', 'Otros Organico'}
    # Classify dynamically from May CR — not from hardcoded MEDIO_META
    all_keys = [k for k in MEDIO.keys() if k not in EXCLUIR]
    inv  = sorted([k for k in all_keys if _may_cr_of(k) >= 2.5],  key=lambda k: -_may_cr_of(k))
    opt  = sorted([k for k in all_keys if 1.5 <= _may_cr_of(k) < 2.5], key=lambda k: -_may_cr_of(k))
    cut  = sorted([k for k in all_keys if _may_cr_of(k) < 1.5],   key=lambda k: -_may_cr_of(k))

    h  = '<div class="alert ae"><span>!</span><div>Datos de contactación son <b>solo de México</b>. Los canales internacionales no se muestran aquí.</div></div>'
    h += f'<div class="alert ag"><span>i</span><div>Veredictos basados en <b>CR de {_m_label} {_cd} días reales</b> (sin proyección). La flecha ↑/↓ muestra cambio vs promedio histórico Ene-Abr. <b>%Cont.</b> = leads contactados.</div></div>'
    if inv:
        h += '<div class="sec-hdr">INVERTIR MÁS · CR {_m_label} ≥ 2.5%</div><div class="medio-grid">' + ''.join(medio_card(k, _medio_rows(k), _medio_alert(k)) for k in inv) + '</div>'
    if opt:
        h += '<div class="sec-hdr" style="margin-top:20px;">OPTIMIZAR · CR {_m_label} 1.5–2.5%</div><div class="medio-grid">' + ''.join(medio_card(k, _medio_rows(k), _medio_alert(k)) for k in opt) + '</div>'
    if cut:
        h += '<div class="sec-hdr" style="margin-top:20px;">REVISAR · CR {_m_label} &lt; 1.5%</div><div class="medio-grid">' + ''.join(medio_card(k, _medio_rows(k), _medio_alert(k)) for k in cut) + '</div>'
    return h

medios_html = build_medios_html()

# ── Canal ranking for overview (left panel, always MX from MEDIO) ──────────────
def canal_ranking_left_html():
    EXCLUIR_RANKING = {'NO IDENTIFICADO', 'Test - Google', 'Pixel', 'Otros Organico'}
    rows = []
    for medio in MEDIO.keys():
        if medio in EXCLUIR_RANKING: continue
        r_list = _medio_rows(medio)
        may = next((r for r in r_list if 'May' in r['mes']), None)
        if not may or may['leads'] < 100: continue
        rows.append({'canal':medio,'leads':may['leads'],'ventas':may['ventas'],'cr':may['cr'],
                     'pct_contact':round(may['contact']/may['leads']*100,0) if may['leads']>0 else 0})
    rows.sort(key=lambda r: -r['cr'])
    mx_cr = rows[0]['cr'] if rows else 1

    tbl = '<table style="width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">'
    tbl += '<thead><tr style="background:#f8fafc;"><th style="padding:7px 10px;font-size:9px;color:#94a3b8;text-transform:uppercase;text-align:left">#</th><th style="padding:7px 10px;font-size:9px;color:#94a3b8;text-align:left">Canal</th><th style="padding:7px 10px;font-size:9px;color:#94a3b8;text-align:right">Leads</th><th style="padding:7px 10px;font-size:9px;color:#94a3b8;text-align:right">%Contacto</th><th style="padding:7px 10px;font-size:9px;color:#94a3b8;text-align:right">Ventas</th><th style="padding:7px 10px;font-size:9px;color:#94a3b8">CR%</th></tr></thead><tbody>'
    for i, r in enumerate(rows):
        c = cr_col(r['cr'],2.0); b = cr_bg(r['cr'],2.0)
        bw = min(100, round(r['cr']/mx_cr*100))
        pc_col = '#16a34a' if r['pct_contact']>=50 else ('#d97706' if r['pct_contact']>=25 else '#dc2626')
        bar_col = '#16a34a' if r['cr']>=2.5 else ('#d97706' if r['cr']>=1.0 else '#dc2626')
        tbl += f'''<tr><td style="padding:6px 10px;color:#94a3b8;font-weight:700">{i+1}</td>
          <td style="padding:6px 10px;font-weight:700">{r["canal"]}</td>
          <td style="padding:6px 10px;text-align:right">{fmt_k(r["leads"])}</td>
          <td style="padding:6px 10px;text-align:right;color:{pc_col};font-weight:700">{int(r["pct_contact"])}%</td>
          <td style="padding:6px 10px;text-align:right;font-weight:700">{fmt_k(r["ventas"])}</td>
          <td style="padding:6px 30px 6px 10px">
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="flex:1;background:#f1f5f9;border-radius:4px;height:10px;"><div style="width:{bw}%;height:10px;background:{bar_col};border-radius:4px;"></div></div>
              <span style="background:{b};color:{c};padding:2px 8px;border-radius:12px;font-weight:800;font-size:11px;white-space:nowrap">{fmt_cr(r["cr"])}%</span>
            </div></td></tr>'''
    tbl += '</tbody></table>'
    return f'<div><div class="sec-hdr">Ranking canales MX — {_m_label} {_m_year} <span>({MAY_D} días reales · contactación solo México)</span></div>{tbl}</div>'

# ── Top/bottom programs panel (right side, country-aware) ──────────────────────
def build_top_progs_panel(prog_list, min_leads=100):
    p_sorted = sorted(prog_list, key=lambda p: -p['may_cr'])
    p_min    = [p for p in p_sorted if p['may_l'] >= min_leads]
    if not p_min:
        return '<div style="color:#94a3b8;padding:14px;font-size:12px;">Sin datos suficientes para este filtro.</div>'
    top6 = p_min[:6]
    bot6 = sorted(p_min, key=lambda p: p['abr_cr'])[:6]
    max_top = max(p['abr_cr'] for p in top6) if top6 else 1

    def mini_bar(p, col):
        bw = round(p['abr_cr'] / max_top * 100) if max_top > 0 else 0
        new_dot = new_badge(p['prog'], 8)
        return f'''<div style="display:flex;align-items:center;gap:6px;padding:6px 10px;border-bottom:1px solid #f8fafc;">
          <div style="flex:1;font-size:10px;font-weight:600;min-width:0;">{new_dot}{shorten(p["prog"],34)}</div>
          <div style="color:#94a3b8;font-size:9px;white-space:nowrap;">{fmt_k(p["abr_l"])} leads</div>
          <div style="width:50px;background:#f1f5f9;border-radius:3px;height:8px;flex-shrink:0;"><div style="width:{bw}%;height:8px;background:{col};border-radius:3px;"></div></div>
          <div style="width:36px;text-align:right;font-weight:800;color:{col};font-size:12px;flex-shrink:0;">{fmt_cr(p["abr_cr"])}%</div></div>'''

    h = '<div>'
    h += f'<div class="sec-hdr">Top CR — {_m_label} {_m_year} <span>{MAY_D} días reales</span></div>'
    h += '<div style="background:white;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden;margin-bottom:12px;">'
    h += ''.join(mini_bar(p, '#16a34a') for p in top6) + '</div>'
    h += f'<div class="sec-hdr">Menor CR — {_m_label} {_m_year} <span>{MAY_D} días reales</span></div>'
    h += '<div style="background:white;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden;">'
    h += ''.join(mini_bar(p, '#dc2626') for p in bot6) + '</div>'
    h += '</div>'
    return h

# ── Country comparison grid ────────────────────────────────────────────────────
def country_grid_html():
    h = f'<div class="sec-hdr">Comparación por país — {_m_label} {_m_year} <span>CR% real {MAY_D} días</span></div>'
    # MX first
    mx_t = T_MX
    mx_abr = mx_t[3]; mx_may = mx_t[4]
    mx_sp = spark([g['cr'] for g in mx_t], w=120, h=36, color='#16a34a', fill=False, is_cr=True)
    h += f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-bottom:16px;">'
    h += f'''<div style="background:#f0fdf4;border-radius:8px;padding:10px 12px;border:2px solid #16a34a;display:flex;align-items:center;gap:10px;">
      <div style="flex:1;"><div style="font-size:13px;font-weight:800;">MEXICO</div>
      <div style="font-size:10px;color:#64748b;margin-top:2px;">{fmt_k(mx_abr["leads"])} leads / {fmt_k(mx_abr["mats"])} mat</div></div>
      {mx_sp}<div style="text-align:right;"><div style="font-size:18px;font-weight:800;color:#16a34a">{fmt_cr(mx_abr["cr"])}%</div>
      <div style="font-size:10px;color:{"#16a34a" if mx_may["cr"]>=mx_abr["cr"] else "#dc2626"};font-weight:700">{_m_label} {"▲" if mx_may["cr"]>=mx_abr["cr"] else "▼"}</div></div></div>'''
    for pais, info in INT_SORTED:
        h += country_summary_card(pais, info)
    h += '</div>'
    return h

# ── Dynamic actions table (MX only, no international conclusions) ──────────────
def build_acciones_html(prog_list, medio_dict, avg_cr_val):
    """Resumen ejecutivo completo — cruza todas las fuentes de datos."""

    def card(icon, urgencia, urgencia_cls, titulo, porque, fuente):
        urg_colors = {'u-hoy': ('#dc2626','#fff8f8','#fca5a5'),
                      'u-sem': ('#d97706','#fffbeb','#fcd34d'),
                      'u-qui': ('#2563eb','#eff6ff','#93c5fd'),
                      'u-ops': ('#16a34a','#f0fdf4','#86efac')}
        tc, bg, bc = urg_colors.get(urgencia_cls, ('#64748b','#f8fafc','#cbd5e1'))
        return (
            f'<div style="background:{bg};border-radius:10px;border:1px solid {bc};'
            f'padding:12px 14px;display:flex;gap:12px;align-items:flex-start;">'
            f'<div style="font-size:20px;line-height:1;flex-shrink:0;">{icon}</div>'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
            f'<span style="background:{tc};color:white;padding:2px 8px;border-radius:20px;'
            f'font-size:9px;font-weight:800;">{urgencia}</span>'
            f'<span style="font-size:9px;color:#94a3b8;font-weight:600;">{fuente}</span>'
            f'</div>'
            f'<div style="font-size:12px;font-weight:800;color:#1e293b;margin-bottom:3px;">{titulo}</div>'
            f'<div style="font-size:11px;color:#475569;line-height:1.4;">{porque}</div>'
            f'</div></div>'
        )

    acciones_hoy  = []
    acciones_sem  = []
    acciones_escalar = []

    EXCLUIR_MED = {'NO IDENTIFICADO','Test - Google','Pixel','Otros Orgánico','Otros Organico'}
    EXCLUIR_ORG = {'Inbound','Referidos','Sitio Web','Blog','Primerpaso','Otros Organico','Islas/Hub','Empresarial'}

    # ── 1. FUNNEL: programas con contactación bajísima (< 40%) por canal ──────
    if FUNNEL_PROG_MEDIO:
        # Worst contact rate combos with high leads
        contact_issues = sorted(
            [r for r in FUNNEL_PROG_MEDIO
             if r.get('months', {}).get('may', {}).get('leads', r.get('may_leads',0)) >= 300
             and r.get('months', {}).get('may', {}).get('pct_cont', r.get('pct_cont',100)) < 40
             and r['medio'] not in EXCLUIR_ORG],
            key=lambda r: -r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0))
        )[:3]
        for r in contact_issues:
            ml = r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0))
            pc = r.get('months',{}).get('may',{}).get('pct_cont', r.get('pct_cont',0))
            acciones_hoy.append(card('🚨','HOY — URGENTE','u-hoy',
                f'Contactación crítica: <b>{shorten(r["prog"],35)}</b> en <b>{r["medio"]}</b>',
                f'Solo {pc:.0f}% de los {fmt_k(ml)} leads de mayo son contactados. '
                f'Revisar asignación en CRM — leads cayendo sin ser llamados.',
                'Funnel · Programa × Canal'))

        # Programs where efectividad dropped vs March
        ef_drops = sorted(
            [r for r in FUNNEL_PROG_MEDIO
             if r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0)) >= 200
             and r.get('delta_ef', 0) < -8
             and r['medio'] not in EXCLUIR_ORG],
            key=lambda r: r.get('delta_ef', 0)
        )[:3]
        for r in ef_drops:
            ml = r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0))
            d  = r.get('delta_ef', 0)
            pe = r.get('months',{}).get('may',{}).get('pct_ef', r.get('pct_ef',0))
            acciones_sem.append(card('📉','ESTA SEMANA','u-sem',
                f'Efectividad cayó: <b>{shorten(r["prog"],35)}</b> en <b>{r["medio"]}</b>',
                f'%Efectividad: {pe:.0f}% (Δ {d:.0f}pp vs Marzo). Se contacta pero no convence. '
                f'Revisar discurso del asesor y calidad del lead.',
                'Funnel · Programa × Canal'))

    # ── 2. INVERSIÓN: canales con alto gasto y CR bajo ────────────────────────
    if INV_CANAL:
        paid = [c for c in INV_CANAL if c['inversion'] > 500_000 and c['cr'] < avg_cr_val * 0.6
                and c['canal'] not in EXCLUIR_ORG and 'org' not in c['canal'].lower()]
        paid_sorted = sorted(paid, key=lambda c: -c['inversion'])[:2]
        for c in paid_sorted:
            def fmt_mx_l(n):
                return f'${n/1_000_000:.1f}M' if n>=1_000_000 else f'${n/1_000:.0f}K'
            cpa_s = f'CPA ${c["cpa"]:,.0f}' if c['cpa'] else 'sin dato de CPA'
            acciones_hoy.append(card('💸','HOY — REVISAR','u-hoy',
                f'Alto gasto, bajo retorno: <b>{c["canal"]}</b>',
                f'{fmt_mx_l(c["inversion"])} invertidos en mayo · CR {fmt_cr(c["cr"])}% · {cpa_s}. '
                f'CR es {round((avg_cr_val - c["cr"])/avg_cr_val*100):.0f}% por debajo del promedio MX. '
                f'Revisar segmentación o reasignar presupuesto.',
                'Inversión · Canal'))

        # Canal con mejor ROI → escalar
        best = sorted([c for c in INV_CANAL if c['inversion'] > 0 and c['ventas'] >= 30
                       and 'org' not in c['canal'].lower()],
                      key=lambda c: c['cpa'] or 99999)
        if best:
            b = best[0]
            def fmt_mx_b(n): return f'${n/1_000_000:.1f}M' if n>=1_000_000 else f'${n/1_000:.0f}K'
            acciones_escalar.append(card('📈','ESCALAR','u-ops',
                f'Mejor ROI: aumentar inversión en <b>{b["canal"]}</b>',
                f'CPA ${b["cpa"]:,.0f} — el más eficiente. CR {fmt_cr(b["cr"])}% con {fmt_k(b["ventas"])} ventas en mayo. '
                f'Cada peso invertido acá genera más retorno que en cualquier otro canal pago.',
                'Inversión · Canal'))

    # ── 3. PROGRAMAS MX: alto volumen, CR muy bajo ────────────────────────────
    progs_sorted_vol = sorted(prog_list, key=lambda x: -x.get('may_l', x.get('abr_l',0)))
    oportunidades = [p for p in progs_sorted_vol
                     if p.get('may_l', p.get('abr_l',0)) >= 1000
                     and (p.get('may_cr') or p.get('abr_cr',0)) < avg_cr_val * 0.65][:3]
    for p in oportunidades:
        cr_v = p.get('may_cr') or p.get('abr_cr',0)
        vol  = p.get('may_l', p.get('abr_l',0))
        gap  = round(avg_cr_val - cr_v, 2)
        extra_mats = round(vol * gap / 100)
        acciones_sem.append(card('🎯','ESTA SEMANA','u-sem',
            f'Oportunidad de cierre: <b>{shorten(p["prog"],40)}</b>',
            f'{fmt_k(vol)} leads en mayo al {fmt_cr(cr_v)}% CR (promedio: {fmt_cr(avg_cr_val)}%). '
            f'Si llega al promedio: +{extra_mats} matrículas extra sin más inversión. '
            f'Priorizar seguimiento y contactación.',
            'Programas MX'))

    # ── 4. PROGRAMAS MX: CR alto → escalar captación ─────────────────────────
    top_progs = sorted([p for p in prog_list if p.get('may_l', p.get('abr_l',0)) >= 200],
                       key=lambda x: -(x.get('may_cr') or x.get('abr_cr',0)))[:2]
    for p in top_progs:
        cr_v = p.get('may_cr') or p.get('abr_cr',0)
        if cr_v >= avg_cr_val * 1.8:
            acciones_escalar.append(card('🟢','ESCALAR','u-ops',
                f'Aumentar captación: <b>{shorten(p["prog"],40)}</b>',
                f'CR {fmt_cr(cr_v)}% — {round(cr_v/avg_cr_val,1)}x el promedio MX. '
                f'Cada lead extra en este programa tiene alto retorno. Aumentar presupuesto en canales donde convierte mejor.',
                'Programas MX'))

    # ── 5. CONTACTACIÓN YoY: alerta si cayó ──────────────────────────────────
    for medio_key, mdata in medio_dict.items():
        if not isinstance(mdata, dict): continue
        alert = mdata.get('alert')
        if not alert: continue
        acciones_hoy.append(card('⚠️','HOY — ALERTA','u-hoy',
            f'Contactación YoY cayó en <b>{medio_key}</b>',
            f'%Contacto {alert["pc_26"]:.0f}% vs {alert["pc_25"]:.0f}% año anterior '
            f'({alert["diff_pc"]:+.1f}pp). Mismo período, mucho menos contacto. '
            f'Investigar cambio en proceso o asignación.',
            'Medios MX · Contactación'))
        break  # solo la primera alerta aquí, no repetir

    # ── Ensamblar output ──────────────────────────────────────────────────────
    html = ''

    if acciones_hoy:
        html += f'<div class="sec-hdr">🚨 Atención inmediata <span>Requieren acción hoy o mañana</span></div>'
        html += f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px;margin-bottom:20px;">'
        html += ''.join(acciones_hoy)
        html += '</div>'

    if acciones_sem:
        html += f'<div class="sec-hdr">📋 Esta semana <span>Importante pero no urgente — planificar antes del viernes</span></div>'
        html += f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px;margin-bottom:20px;">'
        html += ''.join(acciones_sem)
        html += '</div>'

    if acciones_escalar:
        html += f'<div class="sec-hdr">📈 Escalar <span>Lo que está funcionando — aumentar volumen o inversión</span></div>'
        html += f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px;margin-bottom:20px;">'
        html += ''.join(acciones_escalar)
        html += '</div>'

    if not html:
        html = '<div class="alert ag"><span>✓</span><div>Sin alertas críticas esta semana. Todo el funnel dentro de parámetros normales.</div></div>'

    note = (f'<div class="alert ainfo"><span>i</span><div>'
            f'Generado automáticamente cruzando: Funnel por programa×canal · Inversión por canal · '
            f'Programas MX · Contactación MX vs año anterior · {_m_label} {_m_year}'
            f'</div></div>')

    return note + html

# ── Inversión x Canal tab ─────────────────────────────────────────────────────
def build_inv_canal_html(inv_canal):
    if not inv_canal:
        return '<div class="alert aw"><span>!</span><div>Sin datos de inversión. Asegurate de que RESUMEN*.xlsx esté en Downloads.</div></div>'

    paid    = [c for c in inv_canal if c['inversion'] > 0]
    organic = [c for c in inv_canal if c['inversion'] == 0 and (c['leads'] > 0 or c['ventas'] > 0)]

    def fmt_mx(n):
        if n >= 1_000_000: return f'${n/1_000_000:.1f}M'
        if n >= 1_000:     return f'${n/1_000:.0f}K'
        return f'${int(n)}'

    def cr_col_inv(cr):
        if cr >= 2.0: return '#16a34a'
        if cr >= 1.0: return '#d97706'
        return '#dc2626'

    # ── KPI summary ──────────────────────────────────────────────────────────
    total_inv  = sum(c['inversion'] for c in paid)
    total_ven  = sum(c['ventas']    for c in paid)
    total_lead = sum(c['leads']     for c in paid)
    overall_cpl = round(total_inv / total_lead, 0) if total_lead > 0 else 0
    overall_cpa = round(total_inv / total_ven,  0) if total_ven  > 0 else 0

    kpi_bar = (
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">'
        f'<div class="kpi b"><div class="lbl">Total Inversión {_m_label}</div><div class="val">{fmt_mx(total_inv)}</div><div class="sub">{len(paid)} canales pago</div></div>'
        f'<div class="kpi n"><div class="lbl">CPL Promedio</div><div class="val">${overall_cpl:,.0f}</div><div class="sub">Inversión / Leads</div></div>'
        f'<div class="kpi n"><div class="lbl">CPA Promedio</div><div class="val">${overall_cpa:,.0f}</div><div class="sub">Inversión / Ventas</div></div>'
        f'<div class="kpi g"><div class="lbl">Ventas Totales (pago)</div><div class="val">{fmt_k(total_ven)}</div><div class="sub">{fmt_k(total_lead)} leads</div></div>'
        f'</div>'
    )

    # ── Build program × canal pivot ──────────────────────────────────────────
    # Collect all programs from all canales
    prog_totals = {}  # prog → {leads, ventas}
    canal_prog  = {}  # canal → {prog → {leads, ventas}}
    for c in inv_canal:
        cname = c['canal']
        canal_prog[cname] = {}
        for p in c['progs']:
            pn = p['prog']
            canal_prog[cname][pn] = {'leads': p['leads'], 'ventas': p['ventas']}
            if pn not in prog_totals:
                prog_totals[pn] = {'leads': 0, 'ventas': 0}
            prog_totals[pn]['leads']  += p['leads']
            prog_totals[pn]['ventas'] += p['ventas']

    # Sort programs by total ventas desc
    all_progs = sorted(prog_totals.keys(), key=lambda p: -prog_totals[p]['ventas'])

    # Use only paid canales as columns (sorted by inversion desc)
    col_canales = paid  # already sorted by inversion

    # ── Table header ─────────────────────────────────────────────────────────
    # Row 1: canal names (spanning 2 sub-cols each)
    # Row 2: Leads | Ventas per canal
    th_canal_names = '<th style="background:#1e293b;color:white;font-size:9px;font-weight:700;padding:6px 10px;text-align:left;position:sticky;left:0;z-index:2;min-width:200px;">PROGRAMA</th>'
    th_canal_names += '<th colspan="3" style="background:#334155;color:#94a3b8;font-size:9px;font-weight:700;padding:5px 8px;text-align:center;border-left:2px solid #1e293b;">TOTAL</th>'
    for c in col_canales:
        cpl_str = f'CPL ${c["cpl"]:,.0f}' if c['cpl'] else ''
        cpa_str = f'CPA ${c["cpa"]:,.0f}' if c['cpa'] else ''
        inv_str = fmt_mx(c['inversion'])
        subtitle = f'{inv_str} · {cpl_str} · {cpa_str}'
        th_canal_names += (
            f'<th colspan="3" style="background:#1e3a5f;color:white;font-size:9px;font-weight:800;'
            f'padding:5px 8px;text-align:center;border-left:2px solid #0f172a;white-space:nowrap;">'
            f'{c["canal"]}<br><span style="font-weight:400;color:#94a3b8;font-size:8px;">{subtitle}</span></th>'
        )

    th_sub = '<th style="background:#0f172a;color:#64748b;font-size:8px;padding:4px 6px;text-align:right;position:sticky;left:0;"></th>'
    th_sub += '<th style="background:#0f172a;color:#94a3b8;font-size:8px;padding:4px 8px;text-align:right;white-space:nowrap;">Leads</th>'
    th_sub += '<th style="background:#0f172a;color:#94a3b8;font-size:8px;padding:4px 8px;text-align:right;white-space:nowrap;">Ventas</th>'
    th_sub += '<th style="background:#0f172a;color:#94a3b8;font-size:8px;padding:4px 8px;text-align:right;white-space:nowrap;">CR%</th>'
    for c in col_canales:
        cr_c = cr_col_inv(c['cr'])
        cr_str = f'<span style="color:{cr_c};font-weight:800;">{fmt_cr(c["cr"])}%</span>'
        th_sub += (
            f'<th style="background:#0f172a;color:#94a3b8;font-size:8px;padding:4px 6px;'
            f'text-align:right;border-left:1px solid #1e293b;white-space:nowrap;">L</th>'
            f'<th style="background:#0f172a;color:#94a3b8;font-size:8px;padding:4px 6px;'
            f'text-align:right;white-space:nowrap;">V</th>'
            f'<th style="background:#0f172a;font-size:8px;padding:4px 6px;'
            f'text-align:right;white-space:nowrap;">{cr_str}</th>'
        )

    # ── Table rows ────────────────────────────────────────────────────────────
    tbody = ''
    for i, pn in enumerate(all_progs[:60]):
        tot = prog_totals[pn]
        tot_cr = round(tot['ventas']/tot['leads']*100, 1) if tot['leads'] > 0 else 0
        cr_c = cr_col_inv(tot_cr)
        bg = '#ffffff' if i % 2 == 0 else '#f8fafc'
        pn_short = shorten(pn, 42)
        is_new_row = 'true' if pn in NEW_PROGS else 'false'
        row = (
            f'<td style="background:{bg};font-size:10px;font-weight:600;color:#1e293b;'
            f'padding:5px 10px;position:sticky;left:0;white-space:nowrap;border-bottom:1px solid #f1f5f9;'
            f'border-right:1px solid #e2e8f0;" title="{pn}">{new_badge(pn,7)}{pn_short}</td>'
            f'<td style="background:{bg};font-size:10px;text-align:right;padding:5px 8px;border-bottom:1px solid #f1f5f9;color:#475569;">{fmt_k(tot["leads"])}</td>'
            f'<td style="background:{bg};font-size:10px;font-weight:700;text-align:right;padding:5px 8px;border-bottom:1px solid #f1f5f9;">{tot["ventas"]}</td>'
            f'<td style="background:{bg};font-size:10px;font-weight:800;text-align:right;padding:5px 8px;border-bottom:1px solid #f1f5f9;color:{cr_c};">{fmt_cr(tot_cr)}%</td>'
        )
        for c in col_canales:
            cp = canal_prog.get(c['canal'], {}).get(pn)
            if cp and (cp['leads'] > 0 or cp['ventas'] > 0):
                p_cr = round(cp['ventas']/cp['leads']*100, 1) if cp['leads'] > 0 else 0
                p_cr_c = cr_col_inv(p_cr)
                row += (
                    f'<td style="background:{bg};font-size:10px;text-align:right;padding:5px 6px;'
                    f'border-bottom:1px solid #f1f5f9;border-left:1px solid #e8edf2;color:#475569;">{fmt_k(cp["leads"])}</td>'
                    f'<td style="background:{bg};font-size:10px;font-weight:700;text-align:right;padding:5px 6px;border-bottom:1px solid #f1f5f9;">{cp["ventas"]}</td>'
                    f'<td style="background:{bg};font-size:10px;font-weight:800;text-align:right;padding:5px 6px;border-bottom:1px solid #f1f5f9;color:{p_cr_c};">{fmt_cr(p_cr)}%</td>'
                )
            else:
                row += (
                    f'<td style="background:{bg};border-bottom:1px solid #f1f5f9;border-left:1px solid #e8edf2;"></td>'
                    f'<td style="background:{bg};border-bottom:1px solid #f1f5f9;"></td>'
                    f'<td style="background:{bg};border-bottom:1px solid #f1f5f9;"></td>'
                )
        tbody += f'<tr data-new="{is_new_row}">{row}</tr>'

    # ── Totals footer ─────────────────────────────────────────────────────────
    foot = (
        f'<td style="background:#0f172a;color:white;font-size:10px;font-weight:800;'
        f'padding:6px 10px;position:sticky;left:0;">TOTAL CANALES</td>'
        f'<td style="background:#0f172a;color:#94a3b8;font-size:10px;text-align:right;padding:6px 8px;">{fmt_k(total_lead)}</td>'
        f'<td style="background:#0f172a;color:white;font-size:10px;font-weight:800;text-align:right;padding:6px 8px;">{fmt_k(total_ven)}</td>'
        f'<td style="background:#0f172a;color:#94a3b8;font-size:10px;text-align:right;padding:6px 8px;">{fmt_cr(round(total_ven/total_lead*100,1) if total_lead else 0)}%</td>'
    )
    for c in col_canales:
        foot += (
            f'<td style="background:#0f172a;color:#94a3b8;font-size:10px;text-align:right;padding:6px 6px;border-left:1px solid #334155;">{fmt_k(c["leads"])}</td>'
            f'<td style="background:#0f172a;color:white;font-size:10px;font-weight:800;text-align:right;padding:6px 6px;">{fmt_k(c["ventas"])}</td>'
            f'<td style="background:#0f172a;color:#94a3b8;font-size:10px;text-align:right;padding:6px 6px;">{fmt_cr(c["cr"])}%</td>'
        )

    table = (
        f'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);">'
        f'<table style="border-collapse:collapse;width:max-content;min-width:100%;font-family:inherit;">'
        f'<thead>'
        f'<tr>{th_canal_names}</tr>'
        f'<tr>{th_sub}</tr>'
        f'</thead>'
        f'<tbody>{tbody}</tbody>'
        f'<tfoot><tr>{foot}</tr></tfoot>'
        f'</table></div>'
    )

    # ── Organic summary row ───────────────────────────────────────────────────
    org_rows = ''
    for c in organic:
        cr_c = cr_col_inv(c['cr'])
        org_rows += (
            f'<div style="display:flex;align-items:center;gap:12px;padding:6px 14px;'
            f'border-bottom:1px solid #f1f5f9;font-size:11px;">'
            f'<div style="flex:1;font-weight:600;color:#475569;">{c["canal"]}</div>'
            f'<div style="color:#64748b;white-space:nowrap;">{fmt_k(c["leads"])} leads</div>'
            f'<div style="font-weight:700;white-space:nowrap;">{fmt_k(c["ventas"])} ventas</div>'
            f'<div style="font-weight:800;color:{cr_c};white-space:nowrap;">{fmt_cr(c["cr"])}%</div>'
            f'<div style="color:#94a3b8;white-space:nowrap;">sin inversión directa</div>'
            f'</div>'
        )
    org_section = ''
    if org_rows:
        org_section = (
            f'<div class="sec-hdr" style="margin-top:4px;">Canales Orgánicos <span>Sin inversión directa · {_m_label} {_m_year}</span></div>'
            f'<div style="background:white;border-radius:10px;border:1px solid #e2e8f0;overflow:hidden;">{org_rows}</div>'
        )

    info = (
        f'<div class="alert ainfo" style="margin-bottom:14px;"><span>i</span><div>'
        f'Programas ordenados por <b>ventas totales desc</b> · Canales por <b>inversión desc</b> · '
        f'L=Leads · V=Ventas · CR% por celda · CPL/CPA en header de cada canal · '
        f'<span style="color:#16a34a;font-weight:700;">Verde ≥ 2%</span> · '
        f'<span style="color:#d97706;font-weight:700;">Naranja ≥ 1%</span> · '
        f'<span style="color:#dc2626;font-weight:700;">Rojo &lt; 1%</span> · MX · {_m_label} {_m_year}'
        f'</div></div>'
    )

    # ── Recomendaciones programa × canal ─────────────────────────────────────
    def conclusiones():
        if not paid: return ''

        # CR promedio por canal (para comparar cada programa contra su propio canal)
        canal_avg_cr = {c['canal']: c['cr'] for c in paid}

        invertir = []   # (canal, prog, leads, ventas, cr, canal_avg)
        pausar   = []   # idem

        # Excluir orgánicos (inversion=0) y canales con "organico/inbound/referido" en el nombre
        EXCLUIR_REC = {'Inbound', 'Referidos', 'Sitio Web', 'Blog', 'Primerpaso',
                       'Otros Organico', 'Otros Orgánico', 'Islas/Hub', 'Empresarial'}
        def es_organico(canal):
            return ('org' in canal.lower() or canal in EXCLUIR_REC)

        for c in paid:
            cname    = c['canal']
            if es_organico(cname): continue
            avg_cr_c = c['cr']  # CR promedio del canal completo
            for pn, pdata in canal_prog.get(cname, {}).items():
                l = pdata['leads']; v = pdata['ventas']
                if l < 100: continue  # muy poco volumen para concluir
                cr = round(v / l * 100, 2) if l > 0 else 0

                # INVERTIR: CR del programa > 1.5x promedio del canal y mínimo 3 ventas
                if avg_cr_c > 0 and cr >= avg_cr_c * 1.5 and v >= 3:
                    invertir.append({'canal': cname, 'prog': pn, 'leads': l,
                                     'ventas': v, 'cr': cr, 'canal_avg': avg_cr_c})

                # PAUSAR: CR < 50% del promedio del canal con volumen significativo
                elif avg_cr_c > 0 and cr < avg_cr_c * 0.5 and l >= 300:
                    pausar.append({'canal': cname, 'prog': pn, 'leads': l,
                                   'ventas': v, 'cr': cr, 'canal_avg': avg_cr_c})

        # Sort: invertir por CR relativo desc, pausar por leads desc (más dinero quemado)
        invertir.sort(key=lambda x: -(x['cr'] / x['canal_avg']) if x['canal_avg'] > 0 else 0)
        pausar.sort(key=lambda x: -x['leads'])

        def inv_row(r, i):
            bg = '#f0fdf4' if i % 2 == 0 else '#ffffff'
            ratio = round(r['cr'] / r['canal_avg'], 1) if r['canal_avg'] > 0 else '?'
            return (
                f'<div style="display:grid;grid-template-columns:1fr 130px 80px 70px 70px 60px;'
                f'align-items:center;padding:7px 14px;background:{bg};border-bottom:1px solid #f0fdf4;gap:8px;">'
                f'<div style="font-size:11px;font-weight:700;color:#1e293b;">{new_badge(r["prog"],7)}{shorten(r["prog"],42)}</div>'
                f'<div style="font-size:10px;color:#475569;font-weight:600;">{r["canal"]}</div>'
                f'<div style="font-size:10px;text-align:right;color:#64748b;">{fmt_k(r["leads"])} leads</div>'
                f'<div style="font-size:10px;text-align:right;font-weight:700;">{r["ventas"]} ventas</div>'
                f'<div style="font-size:11px;text-align:right;font-weight:800;color:#16a34a;">{fmt_cr(r["cr"])}%</div>'
                f'<div style="font-size:10px;text-align:right;color:#16a34a;font-weight:700;">{ratio}×</div>'
                f'</div>'
            )

        def pau_row(r, i):
            bg = '#fff8f8' if i % 2 == 0 else '#ffffff'
            ratio = round(r['cr'] / r['canal_avg'], 2) if r['canal_avg'] > 0 else '?'
            return (
                f'<div style="display:grid;grid-template-columns:1fr 130px 80px 70px 70px 60px;'
                f'align-items:center;padding:7px 14px;background:{bg};border-bottom:1px solid #fff8f8;gap:8px;">'
                f'<div style="font-size:11px;font-weight:700;color:#1e293b;">{new_badge(r["prog"],7)}{shorten(r["prog"],42)}</div>'
                f'<div style="font-size:10px;color:#475569;font-weight:600;">{r["canal"]}</div>'
                f'<div style="font-size:10px;text-align:right;color:#64748b;">{fmt_k(r["leads"])} leads</div>'
                f'<div style="font-size:10px;text-align:right;font-weight:700;">{r["ventas"]} ventas</div>'
                f'<div style="font-size:11px;text-align:right;font-weight:800;color:#dc2626;">{fmt_cr(r["cr"])}%</div>'
                f'<div style="font-size:10px;text-align:right;color:#dc2626;font-weight:700;">{ratio}×</div>'
                f'</div>'
            )

        def col_hdr(bg):
            return (
                f'<div style="display:grid;grid-template-columns:1fr 130px 80px 70px 70px 60px;'
                f'padding:6px 14px;background:{bg};gap:8px;">'
                f'<div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;">Programa</div>'
                f'<div style="font-size:9px;color:#94a3b8;font-weight:700;text-transform:uppercase;">Canal</div>'
                f'<div style="font-size:9px;color:#94a3b8;text-align:right;text-transform:uppercase;">Leads</div>'
                f'<div style="font-size:9px;color:#94a3b8;text-align:right;text-transform:uppercase;">Ventas</div>'
                f'<div style="font-size:9px;color:#94a3b8;text-align:right;text-transform:uppercase;">CR%</div>'
                f'<div style="font-size:9px;color:#94a3b8;text-align:right;text-transform:uppercase;">vs canal</div>'
                f'</div>'
            )

        html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:4px;">'

        # Invertir más
        inv_body = col_hdr('#166534') + ''.join(inv_row(r, i) for i, r in enumerate(invertir[:20]))
        if not invertir:
            inv_body += '<div style="padding:14px;color:#94a3b8;font-size:11px;">Sin programas con CR destacado en este período.</div>'
        html += (
            f'<div>'
            f'<div style="background:#166534;border-radius:10px 10px 0 0;padding:10px 14px;">'
            f'<div style="color:white;font-size:13px;font-weight:800;">📈 INVERTIR MÁS</div>'
            f'<div style="color:#bbf7d0;font-size:10px;margin-top:2px;">CR del programa ≥ 1.5× el promedio del canal · mínimo 100 leads</div>'
            f'</div>'
            f'<div style="background:white;border-radius:0 0 10px 10px;border:1px solid #dcfce7;overflow:hidden;">'
            f'{inv_body}</div></div>'
        )

        # Pausar / revisar
        pau_body = col_hdr('#7f1d1d') + ''.join(pau_row(r, i) for i, r in enumerate(pausar[:20]))
        if not pausar:
            pau_body += '<div style="padding:14px;color:#94a3b8;font-size:11px;">Sin programas con CR crítico en este período.</div>'
        html += (
            f'<div>'
            f'<div style="background:#7f1d1d;border-radius:10px 10px 0 0;padding:10px 14px;">'
            f'<div style="color:white;font-size:13px;font-weight:800;">🛑 PAUSAR / REVISAR</div>'
            f'<div style="color:#fecaca;font-size:10px;margin-top:2px;">CR del programa &lt; 50% del promedio del canal · mínimo 300 leads</div>'
            f'</div>'
            f'<div style="background:white;border-radius:0 0 10px 10px;border:1px solid #fee2e2;overflow:hidden;">'
            f'{pau_body}</div></div>'
        )

        html += '</div>'
        return (
            f'<div class="sec-hdr" style="margin-top:16px;">Recomendaciones por programa × canal '
            f'<span>CR de cada programa comparado contra el promedio real del canal · {_m_label} {_m_year}</span></div>'
            + html
        )

    n_new = sum(1 for p in all_progs[:60] if p in NEW_PROGS)
    n_old = len(all_progs[:60]) - n_new

    filtros = (
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">'
        f'<span style="font-size:11px;color:#64748b;font-weight:600;">Filtrar programas:</span>'
        f'<button onclick="filtrarInv(\'all\')" id="finv-all" '
        f'style="padding:4px 14px;border-radius:20px;border:1px solid #cbd5e1;background:#1e293b;color:white;'
        f'font-size:11px;font-weight:700;cursor:pointer;">Todos ({len(all_progs[:60])})</button>'
        f'<button onclick="filtrarInv(\'new\')" id="finv-new" '
        f'style="padding:4px 14px;border-radius:20px;border:1px solid #7c3aed;background:white;color:#7c3aed;'
        f'font-size:11px;font-weight:700;cursor:pointer;">✨ Nuevos ({n_new})</button>'
        f'<button onclick="filtrarInv(\'old\')" id="finv-old" '
        f'style="padding:4px 14px;border-radius:20px;border:1px solid #cbd5e1;background:white;color:#475569;'
        f'font-size:11px;font-weight:700;cursor:pointer;">Existentes ({n_old})</button>'
        f'</div>'
        f'<script>'
        f'function filtrarInv(f){{'
        f'  document.querySelectorAll("#tab-inv tbody tr").forEach(r=>{{'
        f'    var isNew=r.dataset.new==="true";'
        f'    r.style.display=(f==="all"||(f==="new"&&isNew)||(f==="old"&&!isNew))?"":"none";'
        f'  }});'
        f'  ["all","new","old"].forEach(id=>{{'
        f'    var b=document.getElementById("finv-"+id);'
        f'    b.style.background=id===f?"#1e293b":"white";'
        f'    b.style.color=id===f?"white":(id==="new"?"#7c3aed":"#475569");'
        f'  }});'
        f'}}'
        f'</script>'
    )

    hdr = f'<div class="sec-hdr">Programas × Canales <span>{_m_label} {_m_year} · {len(all_progs)} programas · scroll horizontal →</span></div>'
    return kpi_bar + info + filtros + hdr + table + org_section + conclusiones()


inv_canal_html = build_inv_canal_html(INV_CANAL)

# ── Diagnóstico tab ────────────────────────────────────────────────────────────
def build_diagnostico_html():
    if not FUNNEL_PROG:
        return ('<div class="alert aw"><span>!</span><div>Sin datos de diagnóstico. '
                'Asegurate de que el archivo <b>data - FECHA.xlsx</b> con columna CONTACTO esté en Downloads.</div></div>')

    totals = FUNNEL_TOTALS
    mar_t = totals.get('Marzo', {})
    # Try current month label first, fallback to 'Mayo' for backward compat
    may_t = totals.get('Mayo', totals.get(_m_label, {}))

    mar_pc  = mar_t.get('pct_cont', 0)
    mar_ef  = mar_t.get('pct_ef',   0)
    mar_cr  = mar_t.get('cr',       0)
    may_pc  = may_t.get('pct_cont', 0)
    may_ef  = may_t.get('pct_ef',   0)
    may_cr  = may_t.get('cr',       0)

    d_pc = round(may_pc - mar_pc, 1)
    d_ef = round(may_ef - mar_ef, 1)
    d_cr = round(may_cr - mar_cr, 2)

    def delta_html(d, unit='pp'):
        arrow = '▲' if d >= 0 else '▼'
        col   = '#16a34a' if d >= 0 else '#dc2626'
        sign  = '+' if d >= 0 else ''
        return f'<span style="color:{col};font-size:22px;font-weight:900;">{arrow} {sign}{d}{unit}</span>'

    def metric_card(title, mar_val, may_val, delta, unit='%', delta_unit='pp'):
        d = round(may_val - mar_val, 1 if delta_unit == 'pp' else 2)
        col = '#16a34a' if d >= 0 else '#dc2626'
        bg  = '#f0fdf4' if d >= 0 else '#fef2f2'
        bdr = '#16a34a' if d >= 0 else '#dc2626'
        sign = '+' if d >= 0 else ''
        return (
            f'<div style="background:{bg};border-radius:12px;border:2px solid {bdr};padding:16px 18px;text-align:center;">'
            f'<div style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">{title}</div>'
            f'<div style="display:flex;align-items:center;justify-content:center;gap:14px;">'
            f'<div><div style="font-size:9px;color:#94a3b8;margin-bottom:2px;">Marzo</div>'
            f'<div style="font-size:20px;font-weight:800;color:#475569;">{mar_val}{unit}</div></div>'
            f'<div style="font-size:18px;color:#cbd5e1;">→</div>'
            f'<div><div style="font-size:9px;color:#94a3b8;margin-bottom:2px;">{_m_label}</div>'
            f'<div style="font-size:20px;font-weight:800;color:{col};">{may_val}{unit}</div></div>'
            f'</div>'
            f'<div style="margin-top:10px;font-size:24px;font-weight:900;color:{col};">'
            f'{"▲" if d >= 0 else "▼"} {sign}{d}{delta_unit}</div>'
            f'</div>'
        )

    # Alert banners for drops > 3pp
    alerts_html = ''
    if d_pc < -3:
        alerts_html += (f'<div class="alert ae" style="font-size:12px;font-weight:700;">'
                        f'<span>⚠</span><div>CAIDA DETECTADA: %Contacto bajó {abs(d_pc):.1f}pp desde marzo '
                        f'({mar_pc:.1f}% → {may_pc:.1f}%). El equipo está llegando a menos leads.</div></div>')
    if d_ef < -3:
        alerts_html += (f'<div class="alert ae" style="font-size:12px;font-weight:700;">'
                        f'<span>⚠</span><div>CAIDA DETECTADA: %Efectividad bajó {abs(d_ef):.1f}pp desde marzo '
                        f'({mar_ef:.1f}% → {may_ef:.1f}%). Se llama más pero se convence menos.</div></div>')
    if d_cr < -0.3:
        alerts_html += (f'<div class="alert ae" style="font-size:12px;font-weight:700;">'
                        f'<span>⚠</span><div>CAIDA DETECTADA: CR bajó {abs(d_cr):.2f}pp desde marzo '
                        f'({mar_cr:.2f}% → {may_cr:.2f}%). El cierre está fallando.</div></div>')
    if not alerts_html and d_pc >= 0 and d_ef >= 0 and d_cr >= 0:
        alerts_html = ('<div class="alert ag"><span>✓</span><div>'
                       'Las tres métricas del funnel mejoraron o se mantienen estables desde marzo. No hay caídas detectadas.</div></div>')

    # Section 1: ¿Qué cambió?
    s1 = (
        f'<div class="sec-hdr">¿Qué cambió? — Marzo vs {_m_label} <span>Totales MX · todas las carreras</span></div>'
        f'{alerts_html}'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:24px;">'
        f'{metric_card("%Contacto", mar_pc, may_pc, d_pc)}'
        f'{metric_card("%Efectividad", mar_ef, may_ef, d_ef)}'
        f'{metric_card("CR%", mar_cr, may_cr, d_cr, unit="%", delta_unit="pp")}'
        f'</div>'
    )

    # ── Section 2: 4 buckets ─────────────────────────────────────────────────
    bucket_contacto    = [p for p in FUNNEL_PROG if p.get('bottleneck') == 'contacto']
    bucket_efectividad = [p for p in FUNNEL_PROG if p.get('bottleneck') == 'efectividad']
    bucket_cierre      = [p for p in FUNNEL_PROG if p.get('bottleneck') == 'cierre']
    bucket_escalar     = [p for p in FUNNEL_PROG if p.get('bottleneck') == 'escalar']

    _total_leads_b = sum(p.get('may_leads', 0) for p in FUNNEL_PROG)
    def pct_total(bucket):
        s = sum(p.get('may_leads', 0) for p in bucket)
        return round(s / _total_leads_b * 100) if _total_leads_b > 0 else 0

    # Lookup: prog → list of medio rows (for worst-canal chip)
    _prog_medios_b = {}
    for r in FUNNEL_PROG_MEDIO:
        pn = r['prog']
        if pn not in _prog_medios_b: _prog_medios_b[pn] = []
        _prog_medios_b[pn].append(r)

    def _worst_canal(prog, metric):
        rows = [r for r in _prog_medios_b.get(prog, [])
                if r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0)) >= 50]
        if not rows: return None, None
        w = min(rows, key=lambda r: r.get('months',{}).get('may',{}).get(metric, r.get(metric, 100)))
        val = w.get('months',{}).get('may',{}).get(metric, w.get(metric, 0))
        return w['medio'], val

    def canal_chip_b(canal, value, fmt='pct'):
        if not canal: return ''
        val_str = f'{value:.0f}%' if fmt == 'pct' else f'{value:.2f}%'
        return (f'<span style="background:#fee2e2;color:#dc2626;padding:1px 6px;border-radius:8px;'
                f'font-size:9px;font-weight:700;white-space:nowrap;margin-left:4px;">'
                f'↓{canal}: {val_str}</span>')

    def mini_funnel_b(pc, pe, cr, delta, lbl='Δ'):
        def fc(v, lo, hi): return '#16a34a' if v >= hi else ('#d97706' if v >= lo else '#dc2626')
        cc=fc(pc,50,57); ec=fc(pe,20,27); rc=fc(cr,1.0,1.5)
        sign='+' if delta>=0 else ''; dc='#16a34a' if delta>=0 else '#dc2626'
        return (f'<div style="display:flex;align-items:center;gap:4px;font-size:10px;white-space:nowrap;">'
                f'<span style="color:{cc};font-weight:800;">{pc:.0f}%</span>'
                f'<span style="color:#cbd5e1;">→</span>'
                f'<span style="color:{ec};font-weight:800;">{pe:.0f}%</span>'
                f'<span style="color:#cbd5e1;">→</span>'
                f'<span style="color:{rc};font-weight:800;">{cr:.2f}%</span>'
                f'<span style="color:{dc};font-weight:600;font-size:9px;margin-left:4px;">{sign}{delta:.1f}pp</span>'
                f'</div>')

    def medio_funnel_sub(prog):
        medios = sorted([r for r in _prog_medios_b.get(prog, [])
                         if r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0)) >= 50],
                        key=lambda r: -r.get('months',{}).get('may',{}).get('leads', r.get('may_leads',0)))[:5]
        if not medios: return ''
        html = ''
        for r in medios:
            m = r.get('months',{}).get('may',{})
            ml=m.get('leads', r.get('may_leads',0))
            pc=m.get('pct_cont', r.get('pct_cont',0))
            pe=m.get('pct_ef',   r.get('pct_ef',0))
            cr=m.get('cr',       r.get('cr',0))
            def fc(v,lo,hi): return '#16a34a' if v>=hi else ('#d97706' if v>=lo else '#dc2626')
            html += (f'<div style="display:flex;align-items:center;gap:6px;padding:3px 10px 3px 22px;'
                     f'background:#f8fafc;border-bottom:1px solid #f1f5f9;font-size:10px;">'
                     f'<div style="color:#64748b;font-weight:600;min-width:90px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{r["medio"]}</div>'
                     f'<div style="color:#94a3b8;white-space:nowrap;">{fmt_k(ml)} L</div>'
                     f'<div style="display:flex;align-items:center;gap:3px;white-space:nowrap;">'
                     f'<span style="color:{fc(pc,50,57)};font-weight:700;">{pc:.0f}%</span>'
                     f'<span style="color:#e2e8f0;">→</span>'
                     f'<span style="color:{fc(pe,20,27)};font-weight:700;">{pe:.0f}%</span>'
                     f'<span style="color:#e2e8f0;">→</span>'
                     f'<span style="color:{fc(cr,1.0,1.5)};font-weight:700;">{cr:.2f}%</span>'
                     f'</div></div>')
        return html

    def prog_bucket_row(p, metric, delta_key, color):
        delta = p.get(delta_key, p.get('trend_' + metric.replace('pct_',''), 0))
        may   = p.get('may', {})
        pc    = may.get('pct_cont', 0); pe = may.get('pct_ef', 0); cr = may.get('cr', 0)
        canal, val = _worst_canal(p['prog'], metric)
        fmt   = 'cr' if metric == 'cr' else 'pct'
        return (f'<div style="border-bottom:1px solid rgba(0,0,0,.07);">'
                f'<div style="display:flex;align-items:center;gap:8px;padding:5px 10px;font-size:11px;">'
                f'<div style="flex:1;font-weight:700;color:#1e293b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" '
                f'title="{p["prog"]}">{shorten(p["prog"],30)}{canal_chip_b(canal, val, fmt)}</div>'
                f'<div style="color:#64748b;white-space:nowrap;font-size:10px;">{fmt_k(p.get("may_leads",0))} leads</div>'
                f'{mini_funnel_b(pc, pe, cr, delta)}'
                f'</div>'
                f'{medio_funnel_sub(p["prog"])}'
                f'</div>')

    def bucket_rows(progs, metric, delta_key, color, limit=8):
        if not progs:
            return '<div style="color:#94a3b8;font-size:10px;padding:8px;">Sin programas en este cuadrante.</div>'
        return ''.join(prog_bucket_row(p, metric, delta_key, color) for p in progs[:limit])

    col_hdr_b = (
        '<div style="display:flex;gap:8px;padding:4px 10px;background:rgba(0,0,0,.06);'
        'font-size:9px;font-weight:700;color:rgba(255,255,255,.7);text-transform:uppercase;">'
        '<div style="flex:1;">Programa · <span style="font-weight:400;opacity:.8;">↓canal peor</span></div>'
        '<div style="white-space:nowrap;">Leads</div>'
        '<div style="white-space:nowrap;">%Cont→%Ef→CR · Δ</div>'
        '</div>'
    )

    def bucket_card(icon, title, subtitle, desc, color, bg_card, progs_html, n_progs, pct_tot):
        return (
            f'<div style="background:white;border-radius:12px;border:2px solid {color};overflow:hidden;">'
            f'<div style="background:{color};padding:10px 14px;">'
            f'<div style="display:flex;align-items:baseline;gap:10px;">'
            f'<div style="color:white;font-size:13px;font-weight:800;">{icon} {title}</div>'
            f'<div style="color:rgba(255,255,255,.95);font-size:18px;font-weight:900;">{pct_tot}%</div>'
            f'<div style="color:rgba(255,255,255,.7);font-size:10px;">del total · {n_progs} prog</div>'
            f'</div>'
            f'<div style="color:rgba(255,255,255,.85);font-size:10px;margin-top:2px;">{subtitle}</div>'
            f'</div>'
            f'{col_hdr_b}'
            f'<div style="background:{bg_card};">{progs_html}</div>'
            f'<div style="padding:6px 10px;background:{bg_card};border-top:1px solid {color}22;">'
            f'<span style="font-size:10px;color:#64748b;">{desc}</span></div>'
            f'</div>'
        )

    b1 = bucket_card('🔴','CONTACTO BAJO','%Contacto &lt; 50% en {_m_label}',
                     'El equipo no llega a estos leads. Revisar asignación y CRM.',
                     '#dc2626','#fff8f8',
                     bucket_rows(bucket_contacto,'pct_cont','trend_pct_cont','#dc2626'),
                     len(bucket_contacto), pct_total(bucket_contacto))
    b2 = bucket_card('🟠','EFECTIVIDAD BAJA','%Cont ≥ 50% pero %Ef < 20%',
                     'Se llama pero no convence. Revisar pitch y calidad del lead.',
                     '#ea580c','#fff7ed',
                     bucket_rows(bucket_efectividad,'pct_ef','trend_pct_ef','#ea580c'),
                     len(bucket_efectividad), pct_total(bucket_efectividad))
    b3 = bucket_card('🟡','CIERRE BAJO','%Cont ≥ 50%, %Ef ≥ 20%, CR < 1.2%',
                     'Lead interesado pero no cierra. Revisar seguimiento y propuesta.',
                     '#d97706','#fffbeb',
                     bucket_rows(bucket_cierre,'cr','trend_cr','#d97706'),
                     len(bucket_cierre), pct_total(bucket_cierre))
    b4 = bucket_card('🟢','ESCALAR','%Cont ≥ 50%, %Ef ≥ 20%, CR ≥ 1.2%',
                     'Funnel sano — necesitan más leads para crecer.',
                     '#16a34a','#f0fdf4',
                     bucket_rows(bucket_escalar,'cr','trend_cr','#16a34a'),
                     len(bucket_escalar), pct_total(bucket_escalar))

    s2 = (
        f'<div class="sec-hdr">¿Dónde rompe el funnel? <span>Por programa · {_m_label} {_m_year} · % del total de leads · expandido por canal</span></div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px;">'
        f'{b1}{b2}{b3}{b4}'
        f'</div>'
    )

    return s1 + s2

# ── Diagnóstico por Programa × Medio ──────────────────────────────────────────
def build_diag_medio_html():
    if not FUNNEL_PROG_MEDIO:
        return ('<div class="alert aw"><span>!</span><div>Sin datos de diagnóstico por medio. '
                'Asegurate de que el archivo con columnas DESCRIPCIÓN PROGRAMA y MEDIO esté en Downloads.</div></div>')

    PAID_MEDIOS = {'Google Search', 'Facebook - Regular', 'Google pmax', 'Tiktok',
                   'Cleverclick', 'Bing', 'Lqqa', 'Edukapp', 'Educaedu', 'Atom',
                   'Infobip', 'Click To Whatsapp Bot', 'Facebook'}

    def medio_chip(medio):
        is_paid = any(pm.lower() in medio.lower() for pm in PAID_MEDIOS)
        if is_paid:
            bg, col = '#fff3e0', '#e65100'
        else:
            bg, col = '#f5f5f5', '#546e7a'
        return (f'<span style="background:{bg};color:{col};padding:2px 7px;border-radius:10px;'
                f'font-size:9px;font-weight:700;white-space:nowrap;">{medio}</span>')

    def pct_cont_cell(v):
        if v < 50:   col = '#dc2626'
        elif v < 57: col = '#d97706'
        else:        col = '#16a34a'
        return f'<td style="padding:4px 8px;text-align:right;font-weight:800;font-size:10px;color:{col};">{v:.0f}%</td>'

    def pct_ef_cell(v):
        if v < 20:   col = '#dc2626'
        elif v < 27: col = '#d97706'
        else:        col = '#16a34a'
        return f'<td style="padding:4px 8px;text-align:right;font-weight:800;font-size:10px;color:{col};">{v:.0f}%</td>'

    def cr_cell(v):
        if v < 1.0:   col = '#dc2626'
        elif v < 1.5: col = '#d97706'
        else:         col = '#16a34a'
        return f'<td style="padding:4px 8px;text-align:right;font-weight:800;font-size:10px;color:{col};">{v:.2f}%</td>'

    def delta_cell_med(v, unit='pp'):
        col = '#16a34a' if v >= 0 else '#dc2626'
        sign = '+' if v >= 0 else ''
        return f'<td style="padding:4px 8px;text-align:right;font-weight:700;font-size:10px;color:{col};">{sign}{v}{unit}</td>'

    def bottleneck_badge(b):
        MAP = {
            'contacto':     ('🔴', '#dc2626', '#fff8f8', 'Contacto'),
            'efectividad':  ('🟠', '#ea580c', '#fff7ed', 'Efectividad'),
            'cierre':       ('🟡', '#d97706', '#fffbeb', 'Cierre'),
            'bueno':        ('🟢', '#16a34a', '#f0fdf4', 'Bueno'),
        }
        icon, col, bg, lbl = MAP.get(b, ('⚪', '#64748b', '#f8fafc', b))
        return (f'<td style="padding:4px 8px;text-align:center;">'
                f'<span style="background:{bg};color:{col};padding:2px 7px;border-radius:10px;'
                f'font-size:9px;font-weight:800;white-space:nowrap;">{icon} {lbl}</span></td>')

    col_hdr_html = (
        '<thead><tr style="background:#f8fafc;">'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:left;text-transform:uppercase;">Programa</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:left;text-transform:uppercase;">Medio</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">Leads</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">%Cont</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">%Ef</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">CR%</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:center;text-transform:uppercase;">Problema</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">Δ Cont</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">Δ Ef</th>'
        '</tr></thead>'
    )

    def prog_short(s):
        s = str(s)
        for pfx in ['LICENCIATURA EN ', 'LICENCIATURA ', 'MAESTRÍA EN ', 'MAESTRIA EN ',
                    'BACHELOR OF SCIENCE IN ', 'BACHELOR OF BUSINESS ADMINISTRATION IN ',
                    'MASTER OF ', 'MASTER IN ', 'DOCTORADO EN ']:
            if s.upper().startswith(pfx):
                s = s[len(pfx):]
                break
        return s[:35] + ('…' if len(s) > 35 else '')

    def build_row(r, i):
        bg = '#ffffff' if i % 2 == 0 else '#f8fafc'
        prog_td = (f'<td style="padding:4px 8px;font-size:10px;font-weight:600;color:#1e293b;'
                   f'white-space:nowrap;background:{bg};" title="{r["prog"]}">{prog_short(r["prog"])}</td>')
        medio_td = f'<td style="padding:4px 8px;background:{bg};">{medio_chip(r["medio"])}</td>'
        leads_td = f'<td style="padding:4px 8px;text-align:right;font-size:10px;color:#475569;background:{bg};">{fmt_k(r["may_leads"])}</td>'
        return (f'<tr style="border-bottom:1px solid #f1f5f9;background:{bg};">'
                f'{prog_td}{medio_td}{leads_td}'
                f'{pct_cont_cell(r["pct_cont"])}'
                f'{pct_ef_cell(r["pct_ef"])}'
                f'{cr_cell(r["cr"])}'
                f'{bottleneck_badge(r["bottleneck"])}'
                f'{delta_cell_med(r["delta_cont"])}'
                f'{delta_cell_med(r["delta_ef"])}'
                f'</tr>')

    # ── Table A: Top combinaciones a intervenir ──────────────────────────────
    table_a_data = [
        r for r in FUNNEL_PROG_MEDIO
        if r['may_leads'] >= 200 and (r['pct_cont'] < 50 or r['pct_ef'] < 20)
    ]
    # Already sorted by may_leads desc from extract_data
    table_a_data = table_a_data[:15]

    rows_a = ''.join(build_row(r, i) for i, r in enumerate(table_a_data))
    if not rows_a:
        rows_a = '<tr><td colspan="9" style="padding:14px;color:#94a3b8;text-align:center;">Sin combinaciones críticas con ≥200 leads en mayo.</td></tr>'

    table_a = (
        f'<div style="background:white;border-radius:12px;border:1px solid #fca5a5;overflow:hidden;'
        f'box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:20px;">'
        f'<div style="background:#dc2626;padding:10px 16px;display:flex;align-items:center;gap:12px;">'
        f'<span style="color:white;font-size:13px;font-weight:800;">🎯 Top combinaciones a intervenir</span>'
        f'<span style="color:rgba(255,255,255,.8);font-size:10px;">≥200 leads + %Contacto &lt;50% o %Efectividad &lt;20% · {len(table_a_data)} combinaciones</span>'
        f'</div>'
        f'<div style="overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;font-family:inherit;">'
        f'{col_hdr_html}<tbody>{rows_a}</tbody>'
        f'</table></div></div>'
    )

    # ── Table B: Top deterioros vs Marzo ────────────────────────────────────
    table_b_data = [
        r for r in FUNNEL_PROG_MEDIO
        if r['may_leads'] >= 100 and (r['delta_cont'] < -5 or r['delta_ef'] < -5 or r['delta_cr'] < -0.5)
    ]
    # Sort by composite deterioration score
    table_b_data.sort(key=lambda r: -(abs(r['delta_cont']) + abs(r['delta_ef']) * 2 + abs(r['delta_cr']) * 10))
    table_b_data = table_b_data[:15]

    # Build col header with emphasized delta columns for Table B
    col_hdr_b = (
        '<thead><tr style="background:#1e293b;">'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:left;text-transform:uppercase;">Programa</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:left;text-transform:uppercase;">Medio</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">Leads</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">%Cont</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">%Ef</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:right;text-transform:uppercase;">CR%</th>'
        '<th style="padding:5px 8px;font-size:8px;font-weight:700;color:#94a3b8;text-align:center;text-transform:uppercase;">Problema</th>'
        '<th style="padding:5px 8px;font-size:9px;font-weight:800;color:#fbbf24;text-align:right;text-transform:uppercase;">Δ Cont ⚠</th>'
        '<th style="padding:5px 8px;font-size:9px;font-weight:800;color:#fbbf24;text-align:right;text-transform:uppercase;">Δ Ef ⚠</th>'
        '</tr></thead>'
    )

    def build_row_b(r, i):
        bg = '#ffffff' if i % 2 == 0 else '#fafafa'
        prog_td = (f'<td style="padding:4px 8px;font-size:10px;font-weight:600;color:#1e293b;'
                   f'white-space:nowrap;background:{bg};" title="{r["prog"]}">{prog_short(r["prog"])}</td>')
        medio_td = f'<td style="padding:4px 8px;background:{bg};">{medio_chip(r["medio"])}</td>'
        leads_td = f'<td style="padding:4px 8px;text-align:right;font-size:10px;color:#475569;background:{bg};">{fmt_k(r["may_leads"])}</td>'

        def delta_prominent(v, unit='pp'):
            col = '#16a34a' if v >= 0 else '#dc2626'
            sign = '+' if v >= 0 else ''
            size = '12px' if abs(v) >= 5 else '10px'
            return (f'<td style="padding:4px 8px;text-align:right;font-weight:800;font-size:{size};'
                    f'color:{col};background:{bg};">{sign}{v}{unit}</td>')

        return (f'<tr style="border-bottom:1px solid #f1f5f9;">'
                f'{prog_td}{medio_td}{leads_td}'
                f'{pct_cont_cell(r["pct_cont"])}'
                f'{pct_ef_cell(r["pct_ef"])}'
                f'{cr_cell(r["cr"])}'
                f'{bottleneck_badge(r["bottleneck"])}'
                f'{delta_prominent(r["delta_cont"])}'
                f'{delta_prominent(r["delta_ef"])}'
                f'</tr>')

    rows_b = ''.join(build_row_b(r, i) for i, r in enumerate(table_b_data))
    if not rows_b:
        rows_b = '<tr><td colspan="9" style="padding:14px;color:#94a3b8;text-align:center;">Sin combinaciones con deterioro significativo desde marzo.</td></tr>'

    table_b = (
        f'<div style="background:white;border-radius:12px;border:1px solid #fbbf24;overflow:hidden;'
        f'box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:20px;">'
        f'<div style="background:#92400e;padding:10px 16px;display:flex;align-items:center;gap:12px;">'
        f'<span style="color:white;font-size:13px;font-weight:800;">⚠️ Estas combinaciones empeoraron desde Marzo — acá está el problema</span>'
        f'<span style="color:rgba(255,255,255,.8);font-size:10px;">≥100 leads + Δ Cont &lt;−5pp o Δ Ef &lt;−5pp o Δ CR &lt;−0.5pp · {len(table_b_data)} combinaciones</span>'
        f'</div>'
        f'<div style="overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;font-family:inherit;">'
        f'{col_hdr_b}<tbody>{rows_b}</tbody>'
        f'</table></div></div>'
    )

    # ── Auto-generated insight ────────────────────────────────────────────────
    # Main bottleneck
    bn_counts = {}
    total_leads_by_bn = {}
    for r in FUNNEL_PROG_MEDIO:
        b = r['bottleneck']
        if b == 'bueno':
            continue
        bn_counts[b] = bn_counts.get(b, 0) + 1
        total_leads_by_bn[b] = total_leads_by_bn.get(b, 0) + r['may_leads']

    # By leads impact, not count
    if total_leads_by_bn:
        main_bn = max(total_leads_by_bn, key=lambda k: total_leads_by_bn[k])
        main_bn_n = bn_counts[main_bn]
        main_bn_leads = total_leads_by_bn[main_bn]
        bn_lbl = {'contacto': 'contactación', 'efectividad': 'efectividad', 'cierre': 'cierre'}.get(main_bn, main_bn)
        insight1 = (f'El principal problema es <b>{bn_lbl}</b>, afectando <b>{main_bn_n}</b> combinaciones '
                    f'con <b>{fmt_k(main_bn_leads)}</b> leads en mayo.')
    else:
        insight1 = 'No se detectaron cuellos de botella críticos en el funnel.'

    # Top medios with critical combos
    medio_crit = {}
    for r in FUNNEL_PROG_MEDIO:
        if r['bottleneck'] != 'bueno':
            m = r['medio']
            medio_crit[m] = medio_crit.get(m, 0) + 1
    top_medios = sorted(medio_crit.items(), key=lambda x: -x[1])[:3]
    if top_medios:
        med_str = ', '.join(f'<b>{m}</b> ({n})' for m, n in top_medios)
        insight2 = f'Los medios con más combinaciones críticas son: {med_str}.'
    else:
        insight2 = 'Sin medios con combinaciones críticas identificadas.'

    insight_html = (
        f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;padding:12px 16px;margin-bottom:16px;">'
        f'<div style="font-size:11px;color:#78350f;line-height:1.6;">'
        f'<p style="margin-bottom:6px;">📊 {insight1}</p>'
        f'<p>🎯 {insight2}</p>'
        f'</div></div>'
    )

    separator = (
        f'<hr style="border:none;border-top:2px solid #e2e8f0;margin:28px 0 20px;">'
        f'<div class="sec-hdr">Diagnóstico por Programa × Medio '
        f'<span>¿Qué combinación específica está fallando? · Mayo vs Marzo 2026 · ≥50 leads/mes</span></div>'
        f'<div class="alert ainfo" style="margin-bottom:14px;"><span>i</span><div>'
        f'<b>Cómo leer:</b> cada fila es una combinación programa+medio. '
        f'<b>Δ Cont</b> y <b>Δ Ef</b> muestran el cambio vs Marzo (negativo = empeoró). '
        f'<b>Problema</b> = cuello de botella en Mayo. Chip naranja = medio pago, gris = orgánico.'
        f'</div></div>'
    )

    return separator + insight_html + table_a


diagnostico_html         = build_diagnostico_html()
diag_medio_html          = build_diag_medio_html()

# ── Interactive funnel table (all 5 months, expandable canales) ───────────────
def build_funnel_interactivo_html():
    """Interactive program table with month filter bar and expandable canal sub-rows."""

    if not FUNNEL_PROG_MEDIO:
        return '<div class="alert aw"><span>!</span><div>Sin datos para tabla interactiva.</div></div>'

    MONTH_KEYS   = ['ene', 'feb', 'mar', 'abr', 'may']
    MONTH_LABELS = {str(D.get('months', ['Ene','Feb','Mar','Abr','May']))}

    # Build lookup: prog_name → list of medio rows (from FUNNEL_PROG_MEDIO)
    prog_medio_map = {}
    for r in FUNNEL_PROG_MEDIO:
        pn = r['prog']
        if pn not in prog_medio_map:
            prog_medio_map[pn] = []
        prog_medio_map[pn].append(r)

    # Aggregate program-level month data from FUNNEL_PROG_MEDIO (sum across medios)
    # Then compute derived metrics (pct_cont, pct_ef, cr) from aggregated raw counts
    def _agg_prog_months(medio_rows):
        agg = {}
        for mk in MONTH_KEYS:
            leads = sum(r.get('months', {}).get(mk, {}).get('leads', 0) for r in medio_rows)
            cont  = sum(r.get('months', {}).get(mk, {}).get('contacto', 0) for r in medio_rows)
            util  = sum(r.get('months', {}).get(mk, {}).get('util', 0) for r in medio_rows)
            refs  = sum(r.get('months', {}).get(mk, {}).get('refs', 0) for r in medio_rows)
            ven   = sum(r.get('months', {}).get(mk, {}).get('ventas', 0) for r in medio_rows)
            agg[mk] = {
                'leads': leads, 'contacto': cont, 'util': util, 'refs': refs, 'ventas': ven,
                'pct_cont': round(cont / leads * 100, 1) if leads > 0 else 0.0,
                'pct_ef':   round(util / cont  * 100, 1) if cont  > 0 else 0.0,
                'pct_ref':  round(refs / util  * 100, 1) if util  > 0 else 0.0,
                'cr':       round(ven  / leads * 100, 2) if leads > 0 else 0.0,
            }
        return agg

    # Build sorted list of programs: sorted by May CR desc (only progs with >=100 May leads initially)
    prog_list_for_table = []
    for prog_name, medio_rows in prog_medio_map.items():
        agg = _agg_prog_months(medio_rows)
        may_leads = agg['may']['leads']
        prog_list_for_table.append({'prog': prog_name, 'months': agg, 'may_leads': may_leads})
    prog_list_for_table.sort(key=lambda x: -x['months']['may']['cr'])

    # Build program rows HTML with all month data attributes
    prog_rows_html = ''
    n_progs = 0
    n_canales_total = 0

    for p in prog_list_for_table:
        months = p['months']
        prog_name = p['prog']
        prog_id = prog_name.replace(' ', '_').replace('/', '_').replace('.', '_').replace("'", '_')[:40]

        # Build data attributes for each month
        month_attrs = ''
        for mk in MONTH_KEYS:
            m = months.get(mk, {})
            month_attrs += (
                f' data-{mk}-leads="{m.get("leads", 0)}"'
                f' data-{mk}-cont="{m.get("contacto", 0)}"'
                f' data-{mk}-pc="{m.get("pct_cont", 0)}"'
                f' data-{mk}-util="{m.get("util", 0)}"'
                f' data-{mk}-pe="{m.get("pct_ef", 0)}"'
                f' data-{mk}-refs="{m.get("refs", 0)}"'
                f' data-{mk}-pr="{m.get("pct_ref", 0)}"'
                f' data-{mk}-ven="{m.get("ventas", 0)}"'
                f' data-{mk}-cr="{m.get("cr", 0)}"'
            )

        # Use may data for initial display
        may_m = months.get('may', {})
        may_leads = may_m.get('leads', 0)
        may_cont  = may_m.get('contacto', 0)
        may_pc    = may_m.get('pct_cont', 0)
        may_util  = may_m.get('util', 0)
        may_pe    = may_m.get('pct_ef', 0)
        may_refs  = may_m.get('refs', 0)
        may_pr    = may_m.get('pct_ref', 0)
        may_ven   = may_m.get('ventas', 0)
        may_cr    = may_m.get('cr', 0)

        # Escaped program name for JS
        prog_name_esc = prog_name.replace('"', '&quot;').replace("'", "\\'")
        prog_short    = shorten(prog_name, 48)

        # Build canal sub-rows for this program
        canal_rows = prog_medio_map.get(prog_name, [])
        canal_rows_sorted = sorted(canal_rows, key=lambda r: -(r.get('months', {}).get('may', {}).get('leads', r.get('may_leads', 0))))

        canal_html = ''
        n_canales = 0
        for cr_row in canal_rows_sorted:
            cr_months = cr_row.get('months', {})
            medio_name = cr_row['medio']

            # Only include canal if at least one month has >= 30 leads
            if not any(cr_months.get(mk, {}).get('leads', 0) >= 30 for mk in MONTH_KEYS):
                continue

            n_canales += 1
            canal_id = f'{prog_id}__{medio_name.replace(" ", "_").replace("/", "_")[:20]}'

            canal_month_attrs = ''
            for mk in MONTH_KEYS:
                m = cr_months.get(mk, {})
                canal_month_attrs += (
                    f' data-{mk}-leads="{m.get("leads", 0)}"'
                    f' data-{mk}-cont="{m.get("contacto", 0)}"'
                    f' data-{mk}-pc="{m.get("pct_cont", 0)}"'
                    f' data-{mk}-util="{m.get("util", 0)}"'
                    f' data-{mk}-pe="{m.get("pct_ef", 0)}"'
                    f' data-{mk}-refs="{m.get("refs", 0)}"'
                    f' data-{mk}-pr="{round(m.get('refs',0)/m.get('util',1)*100,1) if m.get('util',0)>0 else 0}"'
                    f' data-{mk}-ven="{m.get("ventas", 0)}"'
                    f' data-{mk}-cr="{m.get("cr", 0)}"'
                )

            c_may  = cr_months.get('may', {})
            c_leads= c_may.get('leads', 0)
            c_cont = c_may.get('contacto', 0)
            c_pc   = c_may.get('pct_cont', 0)
            c_util = c_may.get('util', 0)
            c_pe   = c_may.get('pct_ef', 0)
            c_refs = c_may.get('refs', 0)
            c_pr   = round(c_refs/c_util*100,1) if c_util > 0 else 0
            c_ven  = c_may.get('ventas', 0)
            c_cr   = c_may.get('cr', 0)
            def _rc(v): return '#16a34a' if v >= 15 else ('#d97706' if v >= 8 else '#dc2626')

            canal_html += (
                f'<tr class="canal-sub-row" data-prog-id="{prog_id}" id="crow-{canal_id}"{canal_month_attrs}'
                f' style="display:none;background:#f8fafc;">'
                f'<td style="padding:4px 10px 4px 28px;font-size:10px;font-weight:600;color:#475569;border-bottom:1px solid #f1f5f9;white-space:nowrap;">'
                f'↳ {medio_name}</td>'
                f'<td class="c-leads" style="padding:4px 6px;text-align:right;font-size:10px;color:#64748b;border-bottom:1px solid #f1f5f9;">{fmt_k(c_leads)}</td>'
                f'<td class="c-cont" style="padding:4px 6px;text-align:right;font-size:10px;color:#94a3b8;border-bottom:1px solid #f1f5f9;">{fmt_k(c_cont)}</td>'
                f'<td class="c-pc" style="padding:4px 6px;text-align:right;font-size:10px;font-weight:700;border-bottom:1px solid #f1f5f9;color:{_fi_pc_col(c_pc)};">{c_pc:.0f}%</td>'
                f'<td class="c-util" style="padding:4px 6px;text-align:right;font-size:10px;color:#94a3b8;border-bottom:1px solid #f1f5f9;">{fmt_k(c_util)}</td>'
                f'<td class="c-pe" style="padding:4px 6px;text-align:right;font-size:10px;font-weight:700;border-bottom:1px solid #f1f5f9;color:{_fi_pe_col(c_pe)};">{c_pe:.0f}%</td>'
                f'<td class="c-refs" style="padding:4px 6px;text-align:right;font-size:10px;color:#94a3b8;border-bottom:1px solid #f1f5f9;">{c_refs}</td>'
                f'<td class="c-pr" style="padding:4px 6px;text-align:right;font-size:10px;font-weight:600;border-bottom:1px solid #f1f5f9;color:{_rc(c_pr)};">{c_pr:.0f}%</td>'
                f'<td class="c-ven" style="padding:4px 6px;text-align:right;font-size:10px;font-weight:700;color:#1e293b;border-bottom:1px solid #f1f5f9;">{c_ven}</td>'
                f'<td class="c-cr" style="padding:4px 8px;text-align:right;font-size:11px;font-weight:800;border-bottom:1px solid #f1f5f9;color:{_fi_cr_col(c_cr)};">{c_cr:.2f}%</td>'
                f'<td style="border-bottom:1px solid #f1f5f9;"></td>'
                f'</tr>'
            )

        n_canales_total += n_canales
        n_progs += 1

        expand_btn = (
            f'<button onclick="toggleProg(\'{prog_id}\')" id="btn-{prog_id}" '
            f'style="background:#e2e8f0;border:none;border-radius:50%;width:20px;height:20px;'
            f'font-size:11px;font-weight:800;cursor:pointer;color:#475569;line-height:1;padding:0;" '
            f'title="Ver canales">+</button>'
        ) if canal_html else ''

        def _ref_col(v): return '#16a34a' if v >= 15 else ('#d97706' if v >= 8 else '#dc2626')
        prog_rows_html += (
            f'<tr class="prog-row" data-prog="{prog_name_esc}" data-prog-id="{prog_id}"{month_attrs}'
            f' style="border-bottom:1px solid #e2e8f0;">'
            f'<td style="padding:5px 10px;font-size:11px;font-weight:700;color:#1e293b;max-width:240px;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{prog_name_esc}">'
            f'{new_badge(prog_name,7)}{prog_short}</td>'
            f'<td class="p-leads" style="padding:5px 6px;text-align:right;font-size:11px;color:#64748b;">{fmt_k(may_leads)}</td>'
            f'<td class="p-cont" style="padding:5px 6px;text-align:right;font-size:10px;color:#94a3b8;">{fmt_k(may_cont)}</td>'
            f'<td class="p-pc" style="padding:5px 6px;text-align:right;font-size:11px;font-weight:700;color:{_fi_pc_col(may_pc)};">{may_pc:.0f}%</td>'
            f'<td class="p-util" style="padding:5px 6px;text-align:right;font-size:10px;color:#94a3b8;">{fmt_k(may_util)}</td>'
            f'<td class="p-pe" style="padding:5px 6px;text-align:right;font-size:11px;font-weight:700;color:{_fi_pe_col(may_pe)};">{may_pe:.0f}%</td>'
            f'<td class="p-refs" style="padding:5px 6px;text-align:right;font-size:10px;color:#94a3b8;">{fmt_k(may_refs)}</td>'
            f'<td class="p-pr" style="padding:5px 6px;text-align:right;font-size:10px;font-weight:600;color:{_ref_col(may_pr)};">{may_pr:.0f}%</td>'
            f'<td class="p-ven" style="padding:5px 6px;text-align:right;font-size:11px;font-weight:700;color:#1e293b;">{may_ven}</td>'
            f'<td class="p-cr" style="padding:5px 8px;text-align:right;font-size:14px;font-weight:900;color:{_fi_cr_col(may_cr)};">{may_cr:.2f}%</td>'
            f'<td style="padding:5px 6px;text-align:center;">{expand_btn}</td>'
            f'</tr>'
            f'{canal_html}'
        )

    # Month filter bar
    month_btns = ''
    for mk, ml in zip(MONTH_KEYS, MONTH_LABELS):
        active = 'background:#0f172a;color:white;border-color:#0f172a;' if mk == 'may' else 'background:white;color:#475569;border-color:#cbd5e1;'
        month_btns += (
            f'<button id="mbtn-{mk}" onclick="switchMonth(\'{mk}\')" '
            f'style="{active}padding:5px 16px;border-radius:20px;border:1.5px solid;'
            f'font-size:11px;font-weight:700;cursor:pointer;transition:all .15s;">{ml}</button>'
        )

    filter_bar = (
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">'
        f'<span style="font-size:11px;font-weight:700;color:#64748b;margin-right:4px;">Mes:</span>'
        f'{month_btns}'
        f'<span style="font-size:10px;color:#94a3b8;margin-left:8px;">Programas con ≥ 100 leads en mes seleccionado · ordenados por CR desc · expandir (+) para ver canales</span>'
        f'</div>'
    )

    def _th(label, cls='', color='#94a3b8'):
        return (f'<th style="padding:6px 6px;font-size:9px;font-weight:700;color:{color};'
                f'text-transform:uppercase;text-align:right;white-space:nowrap;">{label}</th>')

    # Table header — full funnel
    table_header = (
        f'<thead>'
        f'<tr style="background:#0f172a;position:sticky;top:0;z-index:3;">'
        f'<th colspan="1" style="padding:6px 10px;font-size:9px;font-weight:700;color:#94a3b8;text-align:left;min-width:220px;">PROGRAMA</th>'
        f'<th colspan="2" style="padding:6px 6px;font-size:9px;font-weight:700;color:#64748b;text-align:center;border-left:1px solid #1e293b;">LEADS → CONTACTO</th>'
        f'<th colspan="2" style="padding:6px 6px;font-size:9px;font-weight:700;color:#64748b;text-align:center;border-left:1px solid #1e293b;">CONT → ÚTIL</th>'
        f'<th colspan="2" style="padding:6px 6px;font-size:9px;font-weight:700;color:#64748b;text-align:center;border-left:1px solid #1e293b;">ÚTIL → REFS</th>'
        f'<th colspan="1" style="padding:6px 6px;font-size:9px;font-weight:700;color:#64748b;text-align:center;border-left:1px solid #1e293b;">VENTAS</th>'
        f'<th colspan="1" style="padding:6px 8px;font-size:9px;font-weight:700;color:white;text-align:right;border-left:1px solid #334155;">CR%</th>'
        f'<th style="padding:6px 4px;"></th>'
        f'</tr>'
        f'<tr style="background:#0f172a;border-bottom:1px solid #334155;">'
        f'<th style="padding:4px 10px;"></th>'
        f'{_th("Leads")}{_th("%Cont","","#7dd3fc")}'
        f'{_th("Útil","","#94a3b8")}{_th("%Ef","","#7dd3fc")}'
        f'{_th("Refs","","#94a3b8")}{_th("%Ref","","#7dd3fc")}'
        f'{_th("Ventas","","#f9a8d4")}'
        f'{_th("CR%","","white")}'
        f'<th style="padding:4px 4px;"></th>'
        f'</tr>'
        f'</thead>'
    )

    # JS for interactivity
    month_keys_js   = str(MONTH_KEYS)
    month_labels_js = str(MONTH_LABELS)

    js = f"""
<script>
(function() {{
  var currentMonth = 'may';
  var MONTH_KEYS   = {month_keys_js};
  var MONTH_LABELS = {month_labels_js};

  function pcCol(v) {{
    if (v < 50)  return '#dc2626';
    if (v < 57)  return '#d97706';
    return '#16a34a';
  }}
  function peCol(v) {{
    if (v < 20)  return '#dc2626';
    if (v < 27)  return '#d97706';
    return '#16a34a';
  }}
  function crCol(v) {{
    if (v < 1.0)  return '#dc2626';
    if (v < 1.5)  return '#d97706';
    return '#16a34a';
  }}

  window.switchMonth = function(m) {{
    currentMonth = m;

    // Update button styles
    MONTH_KEYS.forEach(function(mk) {{
      var btn = document.getElementById('mbtn-' + mk);
      if (!btn) return;
      if (mk === m) {{
        btn.style.background = '#0f172a';
        btn.style.color      = 'white';
        btn.style.borderColor = '#0f172a';
      }} else {{
        btn.style.background = 'white';
        btn.style.color      = '#475569';
        btn.style.borderColor = '#cbd5e1';
      }}
    }});

    // Collect prog rows with their CR for this month, then sort
    var tbody = document.getElementById('fi-tbody');
    var allRows = Array.from(tbody.querySelectorAll('tr.prog-row'));
    var rowData = allRows.map(function(tr) {{
      var leads = parseFloat(tr.getAttribute('data-' + m + '-leads') || 0);
      var pc    = parseFloat(tr.getAttribute('data-' + m + '-pc')    || 0);
      var pe    = parseFloat(tr.getAttribute('data-' + m + '-pe')    || 0);
      var cr    = parseFloat(tr.getAttribute('data-' + m + '-cr')    || 0);
      return {{ tr: tr, leads: leads, pc: pc, pe: pe, cr: cr }};
    }});

    // Hide rows with < 100 leads, sort rest by CR desc
    var visible = rowData.filter(function(d) {{ return d.leads >= 100; }});
    var hidden  = rowData.filter(function(d) {{ return d.leads < 100; }});
    visible.sort(function(a, b) {{ return b.cr - a.cr; }});

    // Re-order DOM: visible rows first, then hidden
    var toOrder = visible.concat(hidden);
    toOrder.forEach(function(d) {{
      var progId = d.tr.getAttribute('data-prog-id');
      // Move prog row
      tbody.appendChild(d.tr);
      // Move associated canal sub-rows right after prog row
      var subRows = Array.from(tbody.querySelectorAll('tr.canal-sub-row[data-prog-id="' + progId + '"]'));
      subRows.forEach(function(sr) {{ tbody.appendChild(sr); }});
    }});

  function refCol(v) {{
    if (v < 8)  return '#dc2626';
    if (v < 15) return '#d97706';
    return '#16a34a';
  }}
  function fmtK(n) {{
    if (n >= 1000) return (n/1000).toFixed(1) + 'k';
    return String(n);
  }}

    // Update visibility and cell values for prog rows
    visible.forEach(function(d) {{
      var tr = d.tr; var m = currentMonth;
      var cont = parseFloat(tr.getAttribute('data-'+m+'-cont')||0);
      var util = parseFloat(tr.getAttribute('data-'+m+'-util')||0);
      var refs = parseFloat(tr.getAttribute('data-'+m+'-refs')||0);
      var pr   = parseFloat(tr.getAttribute('data-'+m+'-pr')||0);
      var ven  = parseFloat(tr.getAttribute('data-'+m+'-ven')||0);
      tr.style.display = '';
      tr.querySelector('.p-leads').textContent = fmtK(d.leads);
      tr.querySelector('.p-cont').textContent  = fmtK(cont);
      tr.querySelector('.p-pc').textContent    = d.pc.toFixed(0) + '%';
      tr.querySelector('.p-pc').style.color    = pcCol(d.pc);
      tr.querySelector('.p-util').textContent  = fmtK(util);
      tr.querySelector('.p-pe').textContent    = d.pe.toFixed(0) + '%';
      tr.querySelector('.p-pe').style.color    = peCol(d.pe);
      tr.querySelector('.p-refs').textContent  = refs;
      tr.querySelector('.p-pr').textContent    = pr.toFixed(0) + '%';
      tr.querySelector('.p-pr').style.color    = refCol(pr);
      tr.querySelector('.p-ven').textContent   = ven;
      tr.querySelector('.p-cr').textContent    = d.cr.toFixed(2) + '%';
      tr.querySelector('.p-cr').style.color    = crCol(d.cr);
    }});
    hidden.forEach(function(d) {{
      d.tr.style.display = 'none';
      // Also hide their canal sub-rows
      var progId = d.tr.getAttribute('data-prog-id');
      var subRows = Array.from(tbody.querySelectorAll('tr.canal-sub-row[data-prog-id="' + progId + '"]'));
      subRows.forEach(function(sr) {{ sr.style.display = 'none'; }});
    }});

    // Update canal sub-rows cell values for visible progs
    var allCanal = Array.from(tbody.querySelectorAll('tr.canal-sub-row'));
    allCanal.forEach(function(cr_tr) {{
      var progId = cr_tr.getAttribute('data-prog-id');
      // Only update if its prog-row is visible
      var progRow = tbody.querySelector('tr.prog-row[data-prog-id="' + progId + '"]');
      if (!progRow || progRow.style.display === 'none') return;
      if (cr_tr.style.display === 'none') return;  // collapsed — update when expanded

      var leads = parseFloat(cr_tr.getAttribute('data-' + m + '-leads') || 0);
      if (leads < 30) {{ cr_tr.style.display = 'none'; return; }}
      var cont = parseFloat(cr_tr.getAttribute('data-' + m + '-cont') || 0);
      var pc   = parseFloat(cr_tr.getAttribute('data-' + m + '-pc')   || 0);
      var util = parseFloat(cr_tr.getAttribute('data-' + m + '-util') || 0);
      var pe   = parseFloat(cr_tr.getAttribute('data-' + m + '-pe')   || 0);
      var refs = parseFloat(cr_tr.getAttribute('data-' + m + '-refs') || 0);
      var pr   = parseFloat(cr_tr.getAttribute('data-' + m + '-pr')   || 0);
      var ven  = parseFloat(cr_tr.getAttribute('data-' + m + '-ven')  || 0);
      var cr   = parseFloat(cr_tr.getAttribute('data-' + m + '-cr')   || 0);
      cr_tr.querySelector('.c-leads').textContent = fmtK(leads);
      cr_tr.querySelector('.c-cont').textContent  = fmtK(cont);
      cr_tr.querySelector('.c-pc').textContent    = pc.toFixed(0) + '%';
      cr_tr.querySelector('.c-pc').style.color    = pcCol(pc);
      cr_tr.querySelector('.c-util').textContent  = fmtK(util);
      cr_tr.querySelector('.c-pe').textContent    = pe.toFixed(0) + '%';
      cr_tr.querySelector('.c-pe').style.color    = peCol(pe);
      cr_tr.querySelector('.c-refs').textContent  = refs;
      cr_tr.querySelector('.c-pr').textContent    = pr.toFixed(0) + '%';
      cr_tr.querySelector('.c-pr').style.color    = refCol(pr);
      cr_tr.querySelector('.c-ven').textContent   = ven;
      cr_tr.querySelector('.c-cr').textContent    = cr.toFixed(2) + '%';
      cr_tr.querySelector('.c-cr').style.color    = crCol(cr);
    }});
  }};

  window.toggleProg = function(progId) {{
    var btn     = document.getElementById('btn-' + progId);
    var tbody   = document.getElementById('fi-tbody');
    var subRows = Array.from(tbody.querySelectorAll('tr.canal-sub-row[data-prog-id="' + progId + '"]'));
    var expanded = btn && btn.textContent === '-';

    if (expanded) {{
      subRows.forEach(function(sr) {{ sr.style.display = 'none'; }});
      if (btn) btn.textContent = '+';
    }} else {{
      subRows.forEach(function(sr) {{
        var cm = currentMonth;
        var leads= parseFloat(sr.getAttribute('data-'+cm+'-leads')||0);
        if (leads < 30) {{ sr.style.display = 'none'; return; }}
        var cont= parseFloat(sr.getAttribute('data-'+cm+'-cont')||0);
        var pc  = parseFloat(sr.getAttribute('data-'+cm+'-pc')  ||0);
        var util= parseFloat(sr.getAttribute('data-'+cm+'-util')||0);
        var pe  = parseFloat(sr.getAttribute('data-'+cm+'-pe')  ||0);
        var refs= parseFloat(sr.getAttribute('data-'+cm+'-refs')||0);
        var pr  = parseFloat(sr.getAttribute('data-'+cm+'-pr')  ||0);
        var ven = parseFloat(sr.getAttribute('data-'+cm+'-ven') ||0);
        var cr  = parseFloat(sr.getAttribute('data-'+cm+'-cr')  ||0);
        sr.querySelector('.c-leads').textContent= fmtK(leads);
        sr.querySelector('.c-cont').textContent = fmtK(cont);
        sr.querySelector('.c-pc').textContent   = pc.toFixed(0)+'%';
        sr.querySelector('.c-pc').style.color   = pcCol(pc);
        sr.querySelector('.c-util').textContent = fmtK(util);
        sr.querySelector('.c-pe').textContent   = pe.toFixed(0)+'%';
        sr.querySelector('.c-pe').style.color   = peCol(pe);
        sr.querySelector('.c-refs').textContent = refs;
        sr.querySelector('.c-pr').textContent   = pr.toFixed(0)+'%';
        sr.querySelector('.c-pr').style.color   = refCol(pr);
        sr.querySelector('.c-ven').textContent  = ven;
        sr.querySelector('.c-cr').textContent   = cr.toFixed(2)+'%';
        sr.querySelector('.c-cr').style.color   = crCol(cr);
        sr.style.display = '';
      }});
      if (btn) btn.textContent = '-';
    }}
  }};
}})();
</script>
"""

    table_html = (
        f'<div style="overflow-x:auto;border-radius:10px;border:1px solid #e2e8f0;'
        f'box-shadow:0 1px 4px rgba(0,0,0,.06);max-height:72vh;overflow-y:auto;">'
        f'<table style="border-collapse:collapse;width:100%;font-family:inherit;">'
        f'{table_header}'
        f'<tbody id="fi-tbody">{prog_rows_html}</tbody>'
        f'</table></div>'
    )

    return (
        f'<div class="sec-hdr" style="margin-top:4px;">Funnel interactivo por programa '
        f'<span>Todas las carreras · {n_progs} programas · {n_canales_total} canales expandibles</span></div>'
        f'{filter_bar}'
        f'{table_html}'
        f'{js}'
    )

def _fi_pc_col(v):
    if v < 50:  return '#dc2626'
    if v < 57:  return '#d97706'
    return '#16a34a'

def _fi_pe_col(v):
    if v < 20:  return '#dc2626'
    if v < 27:  return '#d97706'
    return '#16a34a'

def _fi_cr_col(v):
    if v < 1.0:  return '#dc2626'
    if v < 1.5:  return '#d97706'
    return '#16a34a'

funnel_interactivo_html  = build_funnel_interactivo_html()

# ══════════════════════════════════════════════════════════════════════════════
# BUILD ALL HTML SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
avg_mx  = avg_cr(PROG_MX)
avg_int = avg_cr(PROG_INT)

kpis_mx  = kpi_row(T_MX,  PROG_MX,  'mx')
kpis_int = kpi_row(T_INT, PROG_INT, 'int')
kpis_all = kpi_row(T_ALL, PROG_MX+PROG_INT, 'all')

# Per-country KPIs
kpis_country = {}
for pais, info in INT_SORTED:
    kpis_country[pais] = kpi_row(info['trend'], info['progs'], f'c_{pais}')

progs_mx_html  = prog_section(PROG_MX,  avg_mx)
progs_int_html = prog_section(PROG_INT, avg_int, show_contact=False)

# Per-country prog sections
progs_country = {}
for pais, info in INT_SORTED:
    a = avg_cr(info['progs'])
    progs_country[pais] = prog_section(info['progs'], a, show_contact=False)

prog_canal_mx_html = build_prog_canal_section(CANAL_MX, PROG_MX, min_canal_leads=50)
prog_canal_country = {}
for pais, info in INT_SORTED:
    prog_canal_country[pais] = build_prog_canal_section(info['canal'], info['progs'], min_canal_leads=10)

_no_mezclar = '<div class="alert aw" style="margin:16px 0;"><span>!</span><div>Seleccioná un <b>país específico</b> para ver el análisis de canal. Cada país opera de manera distinta y mezclarlos no tiene sentido.</div></div>'

# Canal-level monthly trend sections — MX only (INT countries don't have monthly breakdown)
canal_trend_mx_html = canal_section(CANAL_MX, 'ctrend_mx', CANAL_TREND_MX)

# Canal recommendations per country
canal_reco_mx_html = canal_recommendations_html(CANAL_MX)
canal_reco_country = {}
for pais, info in INT_SORTED:
    canal_reco_country[pais] = canal_recommendations_html(info['canal'])

country_grid = country_grid_html()
canal_left_html = canal_ranking_left_html()

# Top programs per country filter
top_progs_mx_html  = build_top_progs_panel(PROG_MX, min_leads=500)
top_progs_int_html = build_top_progs_panel(PROG_INT, min_leads=20)
top_progs_country_html = {}
for pais, info in INT_SORTED:
    top_progs_country_html[pais] = build_top_progs_panel(info['progs'], min_leads=5)

top_progs_groups  = f'<div class="top-progs-group on" data-pais="all">{top_progs_mx_html}</div>'
top_progs_groups += f'<div class="top-progs-group" data-pais="mx">{top_progs_mx_html}</div>'
top_progs_groups += f'<div class="top-progs-group" data-pais="int">{top_progs_int_html}</div>'
for pais, info in INT_SORTED:
    top_progs_groups += f'<div class="top-progs-group" data-pais="c_{pais}">{top_progs_country_html[pais]}</div>'

ranking_html = f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:18px;"><div>{top_progs_groups}</div>{canal_left_html}</div>'

# Use combined_cr average across all MX programs as threshold — stable annual benchmark
_avg_combined = round(sum(p.get('combined_cr',0) for p in PROG_MX if p.get('combined_cr',0) > 0) /
                      max(1, sum(1 for p in PROG_MX if p.get('combined_cr',0) > 0)), 2)
pricing_matrix_html = build_pricing_matrix_html(PROG_MX, _avg_combined)
nuevos_section_html = build_nuevos_section(PROG_MX)
vol_drop_html       = build_vol_drop_section(PROG_MX, threshold=25)
acciones_html       = build_acciones_html(PROG_MX, MEDIO, avg_mx)

# ── YoY groups (filter-aware) ──────────────────────────────────────────────────
yoy_html  = f'<div class="yoy-group on" data-pais="all">{build_yoy_section(T_ALL_2025, T_ALL)}</div>'
yoy_html += f'<div class="yoy-group" data-pais="mx">{build_yoy_section(T_MX_2025, T_MX)}</div>'
yoy_html += f'<div class="yoy-group" data-pais="int">{build_yoy_section(T_INT_2025, T_INT)}</div>'
for pais, info in INT_SORTED:
    # Per country: use country 2026 trend vs MX 2025 as proxy (no per-country 2025 data)
    yoy_html += f'<div class="yoy-group" data-pais="c_{pais}">{build_yoy_section(T_ALL_2025, info["trend"])}</div>'

# ── JS ─────────────────────────────────────────────────────────────────────────
# Build list of all country pais keys
all_pais_keys = ['all','mx','int'] + [f'c_{p}' for p, _ in INT_SORTED]

JS = """
var currentPais = 'all';

function setPais(p) {
  currentPais = p;
  document.querySelectorAll('.cfilter').forEach(b => b.classList.remove('on'));
  var btn = document.getElementById('cf-' + p);
  if (btn) btn.classList.add('on');

  ['kpi-group','prog-group','canal-group','canal-reco-group','canal-trend-group','top-progs-group','yoy-group'].forEach(function(cls) {
    document.querySelectorAll('.' + cls).forEach(g => g.classList.remove('on'));
    document.querySelectorAll('.' + cls + '[data-pais="' + p + '"]').forEach(g => g.classList.add('on'));
  });
}

function showTab(id) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('on'));
  document.querySelectorAll('.topnav a').forEach(a => a.classList.remove('on'));
  document.getElementById('tab-' + id).classList.add('on');
  document.getElementById('nav-' + id).classList.add('on');
}

function showCanal(prefix, name) {
  document.querySelectorAll('[id^="cpane-' + prefix + '"]').forEach(p => p.classList.remove('on'));
  document.querySelectorAll('[id^="ctab-' + prefix + '"]').forEach(t => t.classList.remove('on'));
  var pane = document.getElementById('cpane-' + prefix + '-' + name);
  var tab  = document.getElementById('ctab-' + prefix + '-' + name);
  if (pane) pane.classList.add('on');
  if (tab)  tab.classList.add('on');
}
"""

# ── CSS ─────────────────────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f4f8;color:#1e293b;font-size:13px}
.topnav{background:#0f172a;position:sticky;top:0;z-index:300;display:flex;align-items:center;border-bottom:2px solid #1e3a5f;flex-wrap:wrap}
.brand{color:#e2e8f0;padding:10px 18px;font-weight:800;font-size:13px;border-right:1px solid #1e3a5f;white-space:nowrap}
.topnav a{color:#94a3b8;text-decoration:none;padding:10px 16px;font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;border-bottom:3px solid transparent;margin-bottom:-2px;cursor:pointer;white-space:nowrap}
.topnav a:hover,.topnav a.on{color:#38bdf8;border-bottom-color:#38bdf8}
.country-bar{background:#1e293b;display:flex;align-items:center;padding:6px 16px;gap:6px;border-bottom:1px solid #334155;position:sticky;top:42px;z-index:299;flex-wrap:wrap}
.country-bar .lbl{font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-right:2px;white-space:nowrap}
.cfilter{padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:1.5px solid #334155;background:transparent;color:#64748b;transition:.15s;white-space:nowrap}
.cfilter:hover{background:#334155;color:#e2e8f0}
.cfilter.on{border-color:#38bdf8;background:rgba(56,189,248,.12);color:#38bdf8}
.cfilter.mx.on{border-color:#4ade80;background:rgba(74,222,128,.1);color:#4ade80}
.cfilter.int.on{border-color:#c084fc;background:rgba(192,132,252,.1);color:#c084fc}
.hero{background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);color:white;padding:16px 28px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.hero h1{font-size:17px;font-weight:800}.hero .sub{font-size:11px;color:#94a3b8;margin-top:2px}
.badges{display:flex;gap:7px;flex-wrap:wrap}
.badge{font-size:10px;padding:3px 10px;border-radius:20px;font-weight:700;border:1px solid}
.badge-b{background:rgba(56,189,248,.15);color:#38bdf8;border-color:rgba(56,189,248,.3)}
.badge-g{background:rgba(74,222,128,.15);color:#4ade80;border-color:rgba(74,222,128,.3)}
.badge-o{background:rgba(251,191,36,.15);color:#fbbf24;border-color:rgba(251,191,36,.3)}
.badge-p{background:rgba(192,132,252,.15);color:#c084fc;border-color:rgba(192,132,252,.3)}
.wrap{max-width:1440px;margin:0 auto;padding:16px 24px}
.tab{display:none}.tab.on{display:block}
.kpi-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}
.kpi-group{display:none}.kpi-group.on{display:block}
.kpi{background:white;border-radius:10px;padding:12px 14px;border-top:3px solid #cbd5e1;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.kpi .lbl{font-size:9px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.kpi .val{font-size:20px;font-weight:800;line-height:1}
.kpi .sub{font-size:10px;color:#94a3b8;margin-top:3px}
.kpi.g{border-color:#16a34a}.kpi.g .val{color:#16a34a}
.kpi.r{border-color:#dc2626}.kpi.r .val{color:#dc2626}
.kpi.o{border-color:#d97706}.kpi.o .val{color:#d97706}
.kpi.b{border-color:#2563eb}.kpi.b .val{color:#2563eb}
.kpi.n{border-color:#0f172a}.kpi.n .val{color:#0f172a}
.prog-group{display:none}.prog-group.on{display:block}
.prog-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.prog-card{background:white;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #cbd5e1}
.prog-card.mas{border-color:#16a34a}.prog-card.ok{border-color:#d97706}.prog-card.mal{border-color:#dc2626}
.prog-head{display:flex;align-items:center;gap:7px;margin-bottom:7px;flex-wrap:wrap}
.prog-name{font-size:12px;font-weight:700;flex:1;min-width:120px}
.prog-cr{font-size:17px;font-weight:800}
.prog-meta{display:flex;gap:12px;font-size:10px;color:#64748b;margin-bottom:8px;flex-wrap:wrap}
.canal-group{display:none}.canal-group.on{display:block}
.canal-reco-group{display:none}.canal-reco-group.on{display:block}
.canal-trend-group{display:none}.canal-trend-group.on{display:block}
.top-progs-group{display:none}.top-progs-group.on{display:block}
.yoy-group{display:none}.yoy-group.on{display:block}
.canal-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.canal-tab{padding:5px 12px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;border:2px solid #e2e8f0;background:white;color:#64748b;transition:.15s}
.canal-tab:hover,.canal-tab.on{background:#0f172a;color:white;border-color:#0f172a}
.canal-pane{display:none}.canal-pane.on{display:block}
.prog-table{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.prog-table th{font-size:9px;text-transform:uppercase;color:#94a3b8;font-weight:700;padding:7px 10px;background:#f8fafc;border-bottom:2px solid #f1f5f9;text-align:left}
.prog-table td{font-size:11px;padding:6px 10px;border-bottom:1px solid #f8fafc;vertical-align:middle}
.prog-table tr:last-child td{border:none}.prog-table tr:hover td{background:#f8fafc}
.medio-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px}
.medio-card{background:white;border-radius:10px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.06);border-top:3px solid #cbd5e1}
.medio-card.inv{border-color:#16a34a}.medio-card.opt{border-color:#d97706}.medio-card.cut{border-color:#dc2626}
.tag-mas{background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:800}
.tag-opt{background:#fef9c3;color:#92400e;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:800}
.tag-cut{background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:800}
.alert{border-radius:8px;padding:9px 13px;font-size:11px;display:flex;gap:8px;margin-bottom:12px;line-height:1.5;align-items:flex-start}
.ae{background:#fef2f2;border:1px solid #fca5a5;color:#7f1d1d}
.ag{background:#f0fdf4;border:1px solid #86efac;color:#14532d}
.aw{background:#fffbeb;border:1px solid #fcd34d;color:#78350f}
.ainfo{background:#eff6ff;border:1px solid #93c5fd;color:#1e3a8a}
.sec-hdr{font-size:13px;font-weight:800;color:#0f172a;border-bottom:2px solid #e2e8f0;padding-bottom:8px;margin-bottom:12px;display:flex;align-items:center;gap:10px}
.sec-hdr span{font-size:11px;font-weight:400;color:#94a3b8}
.chart-card{background:white;border-radius:10px;padding:13px 15px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.ch-title{font-size:11px;font-weight:700;color:#475569;margin-bottom:10px;text-transform:uppercase;letter-spacing:.3px}
.acc-table{width:100%;border-collapse:collapse;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.acc-table th{font-size:9px;text-transform:uppercase;color:#94a3b8;font-weight:700;padding:9px 14px;background:#f8fafc;border-bottom:2px solid #f1f5f9;text-align:left}
.acc-table td{font-size:11px;padding:9px 14px;border-bottom:1px solid #f8fafc;vertical-align:middle}
.acc-table tr:last-child td{border:none}
.urg{padding:3px 10px;border-radius:12px;font-size:9px;font-weight:800;white-space:nowrap}
.u-hoy{background:#dc2626;color:white}.u-sem{background:#d97706;color:white}.u-qui{background:#16a34a;color:white}
::-webkit-scrollbar{width:6px;height:6px}::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:3px}
@media(max-width:1000px){.kpi-row{grid-template-columns:repeat(3,1fr)}.prog-grid,.medio-grid{grid-template-columns:1fr}}
"""

# ── Country filter bar ─────────────────────────────────────────────────────────
may_mx_cr  = T_MX[4]['cr']
may_int_cr = T_INT[4]['cr']

filter_bar = '<div class="country-bar"><span class="lbl">Pais:</span>'
filter_bar += '<button class="cfilter on" id="cf-all" onclick="setPais(\'all\')">Todos</button>'
filter_bar += f'<button class="cfilter mx" id="cf-mx" onclick="setPais(\'mx\')">Mexico ({_m_label} {fmt_cr(may_mx_cr)}%)</button>'
filter_bar += f'<button class="cfilter int" id="cf-int" onclick="setPais(\'int\')">Internacional ({_m_label} {fmt_cr(may_int_cr)}%)</button>'
for pais, info in INT_SORTED:
    safe_id = f'c_{pais}'
    cr = info['may_cr']
    col_class = 'mx' if cr >= 2.0 else 'int'
    filter_bar += f'<button class="cfilter {col_class}" id="cf-{safe_id}" onclick="setPais(\'{safe_id}\')">{pais} ({fmt_cr(cr)}%)</button>'
filter_bar += f'<span style="margin-left:8px;font-size:10px;color:#475569;">{_m_label} = {_cd} dias reales</span></div>'

# ── KPI groups ─────────────────────────────────────────────────────────────────
kpi_html  = f'<div class="kpi-group on" data-pais="all">{kpis_all}</div>'
kpi_html += f'<div class="kpi-group" data-pais="mx">{kpis_mx}</div>'
kpi_html += f'<div class="kpi-group" data-pais="int">{kpis_int}</div>'
for pais, info in INT_SORTED:
    kpi_html += f'<div class="kpi-group" data-pais="c_{pais}">{kpis_country[pais]}</div>'

# ── Prog groups ────────────────────────────────────────────────────────────────
prog_html  = f'<div class="prog-group on" data-pais="all">{progs_mx_html}</div>'
prog_html += f'<div class="prog-group" data-pais="mx">{progs_mx_html}</div>'
prog_html += f'<div class="prog-group" data-pais="int">{_no_mezclar}</div>'
for pais, info in INT_SORTED:
    prog_html += f'<div class="prog-group" data-pais="c_{pais}">{progs_country[pais]}</div>'

# ── Canal groups (Programa×Canal view) — no INT aggregate ─────────────────────
canal_html  = f'<div class="canal-group on" data-pais="all">{prog_canal_mx_html}</div>'
canal_html += f'<div class="canal-group" data-pais="mx">{prog_canal_mx_html}</div>'
canal_html += f'<div class="canal-group" data-pais="int">{_no_mezclar}</div>'
for pais, info in INT_SORTED:
    canal_html += f'<div class="canal-group" data-pais="c_{pais}">{prog_canal_country[pais]}</div>'

# ── Canal reco groups — per country ───────────────────────────────────────────
canal_reco_html  = f'<div class="canal-reco-group on" data-pais="all">{canal_reco_mx_html}</div>'
canal_reco_html += f'<div class="canal-reco-group" data-pais="mx">{canal_reco_mx_html}</div>'
canal_reco_html += f'<div class="canal-reco-group" data-pais="int">{_no_mezclar}</div>'
for pais, info in INT_SORTED:
    canal_reco_html += f'<div class="canal-reco-group" data-pais="c_{pais}">{canal_reco_country[pais]}</div>'

# ── Canal trend groups — MX only, INT shows message ───────────────────────────
canal_trend_html  = f'<div class="canal-trend-group on" data-pais="all">{canal_trend_mx_html}</div>'
canal_trend_html += f'<div class="canal-trend-group" data-pais="mx">{canal_trend_mx_html}</div>'
canal_trend_html += f'<div class="canal-trend-group" data-pais="int">{_no_mezclar}</div>'
for pais, info in INT_SORTED:
    canal_trend_html += f'<div class="canal-trend-group" data-pais="c_{pais}"><div class="alert aw"><span>!</span><div>Evolución mensual por canal disponible solo para México por ahora.</div></div></div>'

# ── ASSEMBLE ───────────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard Conversion 2026</title>
<style>{CSS}</style>
</head>
<body>

<div class="topnav">
  <div class="brand">2026</div>
  <a id="nav-overview" class="on" onclick="showTab('overview')">Resumen</a>
  <a id="nav-programs" onclick="showTab('programs')">Programas <span id="new-badge-nav" style="background:#7c3aed;color:white;border-radius:10px;font-size:9px;padding:1px 6px;margin-left:3px;font-weight:800;">NEW</span></a>
  <a id="nav-canal"    onclick="showTab('canal')">Canal x Programa</a>
  <a id="nav-medios"   onclick="showTab('medios')">Medios MX</a>
  <a id="nav-acciones" onclick="showTab('acciones')">Acciones</a>
  <a id="nav-diag"     onclick="showTab('diag')">Diagnóstico</a>
  <a id="nav-inv"      onclick="showTab('inv')">Inversión</a>
</div>

{filter_bar}

<div class="hero">
  <div>
    <h1>Dashboard de Conversion 2026</h1>
    <div class="sub">Sin Diplomados · Datos al {FECHA_DATOS} · Sin proyección · Filtrar por pais arriba</div>
  </div>
  <div class="badges">
    <span class="badge badge-g">MX {_m_label}: {fmt_cr(may_mx_cr)}%</span>
    <span class="badge badge-p">INT {_m_label}: {fmt_cr(may_int_cr)}%</span>
    <span class="badge badge-o">{_m_label} = {_cd} dias reales</span>
  </div>
</div>

<div class="wrap">

<!-- OVERVIEW -->
<div class="tab on" id="tab-overview">
  {kpi_html}
  <div class="sec-hdr">Tendencia 2026 vs 2025 <span>Leads y CR mensual · gris = 2025 completo · color = 2026 hasta hoy · Filtrar pais arriba</span></div>
  {yoy_html}
  {country_grid}
  {ranking_html}
  <div class="sec-hdr" style="margin-top:8px;">Matriz Pricing × Conversión <span>Solo MX · {_m_label} · ¿Dónde vale más mejorar el CR?</span></div>
  {pricing_matrix_html}
  <div class="alert ainfo" style="margin-top:14px;"><span>i</span><div>Selecciona un pais en la barra superior para filtrar todas las secciones. <b>{_m_label}</b> = {_cd} días reales · sin proyección. Contactacion disponible solo para Mexico.</div></div>
</div>

<!-- PROGRAMAS -->
<div class="tab" id="tab-programs">
  <div class="sec-hdr">Programas por CR {_m_label} {_m_year} <span>CR real {MAY_D} días · Filtrar por país arriba</span></div>
  {nuevos_section_html}
  {vol_drop_html}
  {prog_html}
</div>

<!-- CANAL x PROGRAMA -->
<div class="tab" id="tab-canal">
  <div class="sec-hdr">Por canal: qué programas convienen <span>Para cada canal, los programas que convierten mejor vs el promedio del canal · acum. 2025-2026</span></div>
  <div class="alert ag" style="margin-bottom:14px;"><span>i</span><div><b>Cómo leer:</b> <b>Priorizar</b> = CR ≥ 2% y sobre el promedio del canal. <b>Optimizar</b> = canal con techo orgánico (Brand, Inbound). <b>Revisar segmentación</b> = convierte mal vs el promedio del canal.</div></div>
  {canal_reco_html}

  <div class="sec-hdr" style="margin-top:4px;">Evolución mensual por canal <span>Leads y CR% mes a mes · May 2025 → May 2026</span></div>
  {canal_trend_html}
  <div class="sec-hdr" style="margin-top:22px;">Dónde invertir por programa <span>Para cada programa: qué canales tienen mejor y peor CR · acum. 2025-2026</span></div>
  <div class="alert ag" style="margin-bottom:14px;"><span>i</span><div><b>Cómo leer esta tabla:</b> para cada programa, los chips verdes son los canales donde ese programa convierte mejor → poner más presupuesto ahí. Los rojos son donde convierte peor → revisar o cortar. Ordenado por volumen de leads.</div></div>
  {canal_html}
</div>

<!-- MEDIOS MX -->
<div class="tab" id="tab-medios">
  <div class="sec-hdr">Funnel por Medio <span>Solo Mexico · Ene-{_m_label} {_m_year} real · sin proyección ({_cd} días)</span></div>
  {medios_html}
</div>

<!-- ACCIONES -->
<div class="tab" id="tab-acciones">
  <div class="sec-hdr">Acciones concretas <span>Solo MX · generado desde datos reales de {_m_label} {_m_year} · ordenadas por urgencia</span></div>
  {acciones_html}
</div>

<!-- DIAGNÓSTICO -->
<div class="tab" id="tab-diag">
  <div class="sec-hdr">Diagnóstico de Funnel MX <span>¿Qué cambió y dónde rompe? · Enero–{_m_label} {_m_year} · por programa</span></div>
  {diagnostico_html}
  {funnel_interactivo_html}
  {diag_medio_html}
</div>

<!-- INVERSIÓN x CANAL -->
<div class="tab" id="tab-inv">
  <div class="sec-hdr">Inversión x Canal <span>{_m_label} {_m_year} · Fuente: RESUMEN · Top 5 programas por canal (MX)</span></div>
  {inv_canal_html}
</div>

</div>
<div style="text-align:center;font-size:10px;color:#94a3b8;padding:14px;border-top:1px solid #e2e8f0;margin-top:20px;">
Sin Diplomados · Datos reales sin proyección · {FECHA_DATOS} · Contactación solo MX
</div>
<script>{JS}</script>
</body>
</html>"""

OUT = r'C:\Users\USUARIO\Downloads\analisis_semanal.html'
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f'Saved: {len(HTML):,} chars')
