import pandas as pd, warnings, json, unicodedata
warnings.filterwarnings('ignore')

def fix(s):
    try: return str(s).encode('latin1').decode('utf-8')
    except: return str(s)

def norm_prog(s):
    """Normalize program name for matching across sources."""
    s = str(s).upper().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    for prefix in ['LICENCIATURAS EN ','LICENCIATURA EN ','MAESTRIAS EN ','MAESTRIA EN ',
                   'MAESTRIA: ','MAESTRIAS: ','DOCTORADO EN ','ESPECIALIZACION EN ',
                   'BACHELOR OF SCIENCE IN ','BACHELOR OF BUSINESS ADMINISTRATION IN ',
                   'MASTER OF ','MASTER IN ']:
        if s.startswith(prefix): s = s[len(prefix):]
    return s.strip()

# ── CONFIG ────────────────────────────────────────────────────────────────────
NEW_FILE    = r'C:\Users\USUARIO\Downloads\data - 2026-06-01T211234.164.xlsx'
MATS_FILE   = r'C:\Users\USUARIO\Downloads\data - 2026-06-01T211234.164.xlsx'
FUNNEL_FILE = r'C:\Users\USUARIO\Downloads\CUADRO EVOLUTIVO (6).xlsx'
PRECIO_FILE = r'C:\Users\USUARIO\Downloads\TABLA_PRECIOS_2026_ABRIL_COMPLETA (15).xlsx'
RESUMEN_FILE = r'C:\Users\USUARIO\Downloads\RESUMEN (2).xlsx'
FUNNEL_PROG_FILE = r'C:\Users\USUARIO\Downloads\data - 2026-06-01T215409.317.xlsx'
FUNNEL_PROG_MEDIO_FILE = r'C:\Users\USUARIO\Downloads\data - 2026-06-01T221257.291.xlsx'

# ── LOAD PRICING REFERENCE ────────────────────────────────────────────────────
# New programs (launched April or June 2026)
_np_df = pd.read_excel(PRECIO_FILE, sheet_name='nuevos programas', header=1)
_np_df = _np_df.dropna(subset=['Programa'])
_np_df['_ini'] = _np_df['Inicio venta'].astype(str)
_nuevos_lanzados = set(
    norm_prog(p) for p in _np_df[~_np_df['_ini'].str.contains('Proxim', na=True)]['Programa']
)
print(f'Nuevos lanzados (pricing ref): {len(_nuevos_lanzados)}')

# Pricing tier per program from CONSOLIDADO
_cons_df = pd.read_excel(PRECIO_FILE, sheet_name='CONSOLIDADO PROGRAMAS', header=0)
_cons_df = _cons_df.dropna(subset=[_cons_df.columns[3]])
_pricing_map = {}
for _, row in _cons_df.iterrows():
    pname = str(row.iloc[3]).strip()
    tipo  = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ''
    if pname and pname != 'nan':
        _pricing_map[norm_prog(pname)] = tipo
print(f'Pricing tiers loaded: {len(_pricing_map)}')

# ── LOAD REAL MAY MATRÍCULAS ──────────────────────────────────────────────────
# Two modes:
#   A) Separate mats file: PROGRAMA | may 2026__MATRÍCULAS | ... (old format)
#   B) Same as leads file: PAIS | NIVEL | CANAL | DESCRIPCIÓN PROGRAMA | monthly data

_real_may_mats = {}

_mats_raw = pd.read_excel(MATS_FILE, header=None)
_r0 = [fix(str(x)).lower() for x in _mats_raw.iloc[0].tolist()]
_r1 = [fix(str(x)).upper() for x in _mats_raw.iloc[1].tolist()]

_mats_same_as_leads = any('CANAL' in c for c in _r1)

if _mats_same_as_leads:
    # Mode B: leads file used as mats source — extract from main dataframe
    # Find column indices for DESCRIPCIÓN PROGRAMA and may 2026 MATRÍCULAS
    _prog_col_idx = next((i for i, c in enumerate(_r1) if 'PROGRAMA' in c), None)
    # Find may 2026 MATRÍCULAS column: row0 has 'may 2026', row1 has 'MATR'
    _may_mat_idx = None
    for i, (m, met) in enumerate(zip(_r0, _r1)):
        if 'may 2026' in m and 'MATR' in met:
            _may_mat_idx = i
            break
    if _prog_col_idx is not None and _may_mat_idx is not None:
        _mdf2 = _mats_raw.iloc[2:].copy().reset_index(drop=True)
        for _, row in _mdf2.iterrows():
            prog = fix(str(row.iloc[_prog_col_idx])).strip()
            if prog in ('nan', '', 'Total', 'NaN') or not prog:
                continue
            val = pd.to_numeric(row.iloc[_may_mat_idx], errors='coerce')
            if pd.notna(val) and val > 0:
                nk = norm_prog(prog)
                _real_may_mats[nk] = _real_may_mats.get(nk, 0) + int(val)
    print(f'Real May mats (from leads file): {len(_real_may_mats)} programs, total={sum(_real_may_mats.values())}')
else:
    # Mode A: separate mats file with PROGRAMA column
    _mats_months  = _r0
    _mats_metrics = _r1
    _mats_cols = []
    for m, met in zip(_mats_months, _mats_metrics):
        if m in ('nan', 'mes y año', ''):
            _mats_cols.append('PROGRAMA')
        else:
            _mats_cols.append(f'{m}__{met.strip()}')
    _mats_raw.columns = _mats_cols
    _mdf = _mats_raw.iloc[2:].copy(); _mdf.columns = _mats_cols
    _mdf['PROGRAMA'] = _mdf['PROGRAMA'].apply(fix).str.strip()
    _mdf = _mdf[~_mdf['PROGRAMA'].isin(['nan','','Total','NaN'])]
    _may_mat_col = next((c for c in _mats_cols if 'may 2026' in c.lower()), None)
    if _may_mat_col:
        _mdf[_may_mat_col] = pd.to_numeric(_mdf[_may_mat_col], errors='coerce').fillna(0)
        for _, row in _mdf.iterrows():
            nk = norm_prog(row['PROGRAMA'])
            _real_may_mats[nk] = int(row[_may_mat_col])
    print(f'Real May mats (separate file): {len(_real_may_mats)} programs, total={sum(_real_may_mats.values())}')

_CONNECTORS = {'Y','E','O','EN','DE','A','CON','E','I','AL'}

def _is_new_prog(nk):
    """Check if normalized program name matches any new program.
    Data uses short names (e.g. 'INTELIGENCIA ARTIFICIAL');
    pricing sheet uses full names ('INTELIGENCIA ARTIFICIAL Y CIENCIA DE DATOS').
    Exact match first; then prefix match ONLY if the next word is a connector
    (Y, EN, DE, CON…) — prevents 'ADMINISTRACION DE NEGOCIOS' from matching
    'ADMINISTRACION DE NEGOCIOS GASTRONOMICOS'."""
    if nk in _nuevos_lanzados:
        return True
    if ' ' in nk:
        for nuevo in _nuevos_lanzados:
            if nuevo.startswith(nk + ' '):
                suffix_first = nuevo[len(nk)+1:].split()[0] if nuevo[len(nk)+1:].split() else ''
                if suffix_first in _CONNECTORS:
                    return True
    return False

def _get_pricing(nk):
    """Lookup pricing tier with same prefix-fallback logic."""
    if nk in _pricing_map:
        return _pricing_map[nk]
    if ' ' in nk:
        for pk, pv in _pricing_map.items():
            if pk.startswith(nk + ' ') or nk.startswith(pk + ' '):
                return pv
    return ''

MAY_DAYS_DONE  = 31   # auto-detectado del nombre del archivo
MAY_DAYS_TOTAL = 31
MAY_FACTOR     = MAY_DAYS_TOTAL / MAY_DAYS_DONE

# ── PARSE NEW FILE ────────────────────────────────────────────────────────────
raw = pd.read_excel(NEW_FILE, header=None)

months_row = [fix(str(x)) for x in raw.iloc[0].tolist()]
sub_row    = [fix(str(x)) for x in raw.iloc[1].tolist()]

# Build column names
cols = []
cur_m = None
for m, s in zip(months_row, sub_row):
    if m not in ('nan','Mes y A\xf1o','') and 'Filtros' not in m:
        cur_m = m
    s2 = s.strip() if s != 'nan' else ''
    cols.append(f'{cur_m}__{s2}' if s2 and cur_m else f'__{s2}' if s2 else 'SKIP')
cols[0] = 'PAIS'
cols[1] = 'NIVEL'
cols[2] = 'CANAL'
cols[3] = 'PROGRAMA'

raw.columns = cols
data = raw.iloc[2:].copy()
data.columns = cols

for c in ['PAIS','NIVEL','CANAL','PROGRAMA']:
    data[c] = data[c].apply(fix).str.strip()

# Valid countries
SKIP_PAISES = {'nan','Total','NO IDENTIFICADO','EMERGENTES','GLOBAL',
               'INDIA','INDONESIA','PHILIPPINES'}
data = data[~data['PAIS'].str.startswith('Filtros', na=False)]
data = data[~data['PAIS'].isin(SKIP_PAISES)]

# ── Two views of the data ────────────────────────────────────────────────────
# 1. TOTALS: use country-level aggregate rows (NIVEL==Total, no canal/prog)
#    These match Power BI exactly and include unattributed leads.
data_totals = data[
    (data['NIVEL'] == 'Total') &
    (data['CANAL'].isin(['nan','Total']) | data['CANAL'].isna()) &
    (data['PROGRAMA'].isin(['nan','Total']) | data['PROGRAMA'].isna())
].copy()

# 2. PROGRAMS: leaf rows with specific canal + programa
SKIP_NIVELES = {'BOOTCAMP','CURSO','IDIOMAS','NAN','SIN PROGRAMA','BLANCO','BLANK',
                'ESPECIALIZACION','ESPECIALIZACI\xd3N','NOT','UNIDENTIFIED'}
SKIP_CANALES = {'nan','Total','PIXEL','Test','Test - Facebook','Test - Google'}
SKIP_PROGS   = {'Total','nan','NaN','','TOTAL'}

data_progs = data[
    ~data['NIVEL'].str.upper().isin({x.upper() for x in SKIP_NIVELES}) &
    ~data['CANAL'].isin(SKIP_CANALES) &
    ~data['PROGRAMA'].isin(SKIP_PROGS) &
    (data['CANAL'] != 'Total') &
    (data['PROGRAMA'] != 'Total')
].copy()

# Month columns available
month_labels_all = []
seen = set()
for c in cols:
    if '__' in c:
        m = c.split('__')[0]
        if m and m not in seen and m not in ('None','nan',''):
            seen.add(m)
            month_labels_all.append(m)

MONTHS_2026 = [m for m in month_labels_all if '2026' in m]
MONTHS_2025 = [m for m in month_labels_all if '2025' in m]  # full 2025
MONTHS_SHOW = MONTHS_2026   # ene 2026 ... may 2026
MONTHS_LABELS      = ['Ene','Feb','Mar','Abr','May*']
MONTHS_LABELS_2025 = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

def get_col(month, metric):
    """Find column for given month and metric (LEADS 2, MATRÍCULAS, % CR)"""
    for c in cols:
        if c.startswith(month+'__') and metric.upper() in c.upper():
            return c
    return None

leads_cols = [get_col(m, 'LEADS') for m in MONTHS_SHOW]
mats_cols  = [get_col(m, 'MATR') for m in MONTHS_SHOW]

leads_cols_2025 = [get_col(m, 'LEADS') for m in MONTHS_2025]
mats_cols_2025  = [get_col(m, 'MATR')  for m in MONTHS_2025]
print(f'2025 months: {len(MONTHS_2025)} | 2026 months: {len(MONTHS_2026)}')
cr_cols    = [get_col(m, 'CR')   for m in MONTHS_SHOW]

print('Leads cols:', leads_cols)
print('Mats cols:', mats_cols)

for c in leads_cols + mats_cols:
    if c:
        data_totals[c] = pd.to_numeric(data_totals[c], errors='coerce').fillna(0)
        data_progs[c]  = pd.to_numeric(data_progs[c],  errors='coerce').fillna(0)

# Countries of interest
ALL_COUNTRIES = sorted(data_totals['PAIS'].unique())
print('Countries:', ALL_COUNTRIES)

MX_PAIS  = 'M\xc9XICO'  # MÉXICO
INT_PAISES = [p for p in ALL_COUNTRIES if p != MX_PAIS]
print('MX:', MX_PAIS, '| INT:', INT_PAISES)

# ── HELPER: aggregate by (pais, canal, programa) ──────────────────────────────
def get_monthly(row, cols_list):
    return [int(row[c]) if c and c in row.index and pd.notna(row[c]) else 0 for c in cols_list]

def project_may(vals):
    return vals[:-1] + [round(vals[-1] * MAY_FACTOR)]

def build_prog_stats(pais_filter=None, nivel_filter=None, min_may_leads=50):
    """Leaf-level program rows. Primary metric = May* projected."""
    sub = data_progs.copy()
    if pais_filter:
        sub = sub[sub['PAIS'].isin(pais_filter)] if isinstance(pais_filter, list) else sub[sub['PAIS'] == pais_filter]
    if nivel_filter:
        sub = sub[sub['NIVEL'].str.upper().isin({n.upper() for n in nivel_filter})]
    grouped = sub.groupby('PROGRAMA')
    stats = []
    for prog, grp in grouped:
        leads_by_m = [int(grp[c].sum()) if c else 0 for c in leads_cols]
        mats_by_m  = [int(grp[c].sum()) if c else 0 for c in mats_cols]
        leads_proj = project_may(leads_by_m)
        may_l = leads_proj[4]           # leads proyectados (para comparar volumen)
        may_m = mats_by_m[4]            # mats reales sin proyectar (no es lineal)
        abr_l, abr_m = leads_by_m[3], mats_by_m[3]
        # April 2025 leads for YoY comparison (same month, prior year)
        abr25_col  = leads_cols_2025[3]  # abril 2025
        abr_2025_l = int(grp[abr25_col].sum()) if abr25_col else 0
        real_may_l = leads_by_m[4]   # real May leads (partial, not projected)
        real_may_m = mats_by_m[4]    # real May mats from leads file (often 0 at prog level)
        if may_l < min_may_leads: continue
        # Override real_may_m with dedicated mats file if available (more complete)
        nk_prog = norm_prog(fix(prog))
        if nk_prog in _real_may_mats:
            real_may_m = _real_may_mats[nk_prog]
        may_cr  = round(real_may_m/real_may_l*100, 2) if real_may_l > 0 else 0
        abr_cr  = round(abr_m/abr_l*100, 2) if abr_l > 0 else 0
        tot_l   = sum(leads_by_m[:4])
        tot_m   = sum(mats_by_m[:4])
        tot_cr  = round(tot_m/tot_l*100, 2) if tot_l > 0 else 0
        # combined_cr: real accumulated CR across all months (incl. partial May, no projection)
        # For new programs launched Apr 28, abr_cr ≈ 0 (only 3 days); combined_cr uses real May data
        comb_l  = sum(leads_by_m)   # real leads Jan-May (May partial, not projected)
        comb_m  = sum(mats_by_m)    # real mats  Jan-May
        combined_cr = round(comb_m/comb_l*100, 2) if comb_l > 0 else 0
        cr_by_m = [round(mj/lj*100,2) if lj>0 else 0 for lj,mj in zip(leads_proj,mats_by_m)]
        prog_fix = fix(prog)
        nk = norm_prog(prog_fix)
        is_new  = _is_new_prog(nk)
        pricing = _get_pricing(nk)
        # Volume drop: Abr 2026 vs Abr 2025 (YoY same month — no seasonality bias)
        vol_drop_pct = round((abr_2025_l - abr_l) / abr_2025_l * 100, 1) if abr_2025_l >= 200 else 0
        stats.append({
            'prog': prog_fix,
            'may_l': may_l, 'may_m': may_m, 'may_cr': may_cr,
            'real_may_l': real_may_l, 'real_may_m': real_may_m,
            'abr_l': abr_l, 'abr_m': abr_m, 'abr_cr': abr_cr,
            'abr_2025_l': abr_2025_l, 'vol_drop_pct': vol_drop_pct,
            'tot_cr': tot_cr, 'combined_cr': combined_cr,
            'is_new': is_new, 'pricing': pricing,
            'leads': leads_proj, 'mats': mats_by_m, 'cr': cr_by_m
        })
    stats.sort(key=lambda x: -x['may_l'])
    return stats

def build_trend(pais_filter=None):
    """Uses country-level Total rows — matches Power BI exactly."""
    sub = data_totals.copy()
    if pais_filter:
        sub = sub[sub['PAIS'].isin(pais_filter)] if isinstance(pais_filter, list) else sub[sub['PAIS'] == pais_filter]
    result = []
    for mi, (lc, mc, ml) in enumerate(zip(leads_cols, mats_cols, MONTHS_LABELS)):
        tl = int(sub[lc].sum()) if lc else 0
        tm = int(sub[mc].sum()) if mc else 0
        if mi == len(MONTHS_SHOW) - 1:
            cr = round(tm/tl*100, 2) if tl > 0 else 0  # CR con leads/mats reales (sin proyectar)
            tl = round(tl * MAY_FACTOR)  # proyectar leads solo para mostrar volumen
        else:
            cr = round(tm/tl*100, 2) if tl > 0 else 0
        result.append({'mes': ml, 'leads': tl, 'mats': tm, 'cr': cr})
    return result

def build_trend_2025(pais_filter=None):
    """Full 2025 monthly trend — real data, no projection."""
    sub = data_totals.copy()
    if pais_filter:
        sub = sub[sub['PAIS'].isin(pais_filter)] if isinstance(pais_filter, list) else sub[sub['PAIS'] == pais_filter]
    result = []
    for lc, mc, ml in zip(leads_cols_2025, mats_cols_2025, MONTHS_LABELS_2025):
        tl = int(sub[lc].sum()) if lc else 0
        tm = int(sub[mc].sum()) if mc else 0
        cr = round(tm/tl*100, 2) if tl > 0 else 0
        result.append({'mes': ml, 'leads': tl, 'mats': tm, 'cr': cr})
    return result

def build_canal_prog(pais_filter=None, nivel_filter=None, min_leads=50):
    sub = data_progs.copy()
    if pais_filter:
        sub = sub[sub['PAIS'].isin(pais_filter)] if isinstance(pais_filter, list) else sub[sub['PAIS'] == pais_filter]
    if nivel_filter:
        sub = sub[sub['NIVEL'].str.upper().isin({n.upper() for n in nivel_filter})]

    lc_all = [c for c in leads_cols if c]
    mc_all = [c for c in mats_cols  if c]
    # May 2026 = index 4 (current month, real data so far)
    may_l_col = leads_cols[4]
    may_m_col = mats_cols[4]

    sub = sub[sub['CANAL'] != 'Total'].copy()
    sub['_tot_leads'] = sub[lc_all].sum(axis=1)
    sub['_tot_mats']  = sub[mc_all].sum(axis=1)
    sub['_may_leads'] = pd.to_numeric(sub[may_l_col], errors='coerce').fillna(0) if may_l_col else 0
    sub['_may_mats']  = pd.to_numeric(sub[may_m_col], errors='coerce').fillna(0) if may_m_col else 0

    grouped = sub.groupby('CANAL').apply(
        lambda g: g.groupby('PROGRAMA')[['_tot_leads','_tot_mats','_may_leads','_may_mats']].sum().reset_index()
    ).reset_index(level=0)

    result = {}
    for canal, grp in grouped.groupby('CANAL'):
        canal_total = grp['_tot_leads'].sum()
        # Threshold: max(min_leads, 1% of canal total) — prevents tiny programs swamping small channels
        # but also allows small channels (like Inbound) to show all their programs
        dyn_min = max(20, min(min_leads, canal_total * 0.01))
        grp = grp[grp['_tot_leads'] >= dyn_min].copy()
        if len(grp) == 0: continue
        grp['cr']     = (grp['_tot_mats'] / grp['_tot_leads'] * 100).round(2)
        grp['may_cr'] = (grp['_may_mats'] / grp['_may_leads'].replace(0, float('nan')) * 100).round(2).fillna(0)
        grp = grp.sort_values('_tot_leads', ascending=False).head(12)
        rows = [{'prog':fix(str(r['PROGRAMA'])),
                 'leads':int(r['_tot_leads']), 'mats':int(r['_tot_mats']), 'cr':float(r['cr']),
                 'may_leads':int(r['_may_leads']), 'may_mats':int(r['_may_mats']), 'may_cr':float(r['may_cr'])}
                for _,r in grp.iterrows()]
        result[canal] = rows
    return result

def build_canal_trend(pais_filter=None):
    """Monthly leads/mats/CR per canal — last 12 months of 2025 + 2026 YTD."""
    sub = data_progs.copy()
    if pais_filter:
        sub = sub[sub['PAIS'].isin(pais_filter)] if isinstance(pais_filter, list) else sub[sub['PAIS'] == pais_filter]
    sub = sub[sub['CANAL'] != 'Total'].copy()

    # Ensure 2025 cols are numeric
    for c in leads_cols_2025 + mats_cols_2025:
        if c:
            sub[c] = pd.to_numeric(sub[c], errors='coerce').fillna(0)

    result = {}
    for canal, grp in sub.groupby('CANAL'):
        months = []
        # 2025 months (May-Dec to keep chart readable: last 8 of 2025)
        show_2025 = list(zip(MONTHS_LABELS_2025, leads_cols_2025, mats_cols_2025))[4:]  # May-Dic
        for ml, lc, mc in show_2025:
            tl = int(grp[lc].sum()) if lc else 0
            tm = int(grp[mc].sum()) if mc else 0
            cr = round(tm/tl*100, 2) if tl > 0 else 0
            months.append({'mes': ml[:3] + "'25", 'leads': tl, 'mats': tm, 'cr': cr})
        # 2026 months (Ene-May, with May projected)
        for i, (ml, lc, mc) in enumerate(zip(MONTHS_LABELS, leads_cols, mats_cols)):
            tl = int(grp[lc].sum()) if lc else 0
            tm = int(grp[mc].sum()) if mc else 0
            if i == len(MONTHS_SHOW) - 1:
                tl = round(tl * MAY_FACTOR)
                tm = round(tm * MAY_FACTOR)
            cr = round(tm/tl*100, 2) if tl > 0 else 0
            months.append({'mes': ml[:3] + ("'26*" if i == len(MONTHS_SHOW)-1 else "'26"), 'leads': tl, 'mats': tm, 'cr': cr})
        result[canal] = months
    return result

# ── BUILD ALL DATASETS ────────────────────────────────────────────────────────

# MX
prog_mx   = build_prog_stats(pais_filter=MX_PAIS, min_may_leads=100)
trend_mx  = build_trend(pais_filter=MX_PAIS)
canal_mx       = build_canal_prog(pais_filter=MX_PAIS, min_leads=200)
canal_trend_mx = build_canal_trend(pais_filter=MX_PAIS)
print(f'MX progs: {len(prog_mx)}, canales: {len(canal_mx)}')
new_progs = [p['prog'] for p in prog_mx if p['is_new']]
print(f'NEW programs detected in MX: {len(new_progs)}')
for p in new_progs: print(f'  NEW: {p}')
print('MX trend:', [(g['mes'],g['leads'],g['cr']) for g in trend_mx])

# International per country
int_countries_data = {}
for pais in INT_PAISES:
    progs = build_prog_stats(pais_filter=pais, min_may_leads=5)
    trend = build_trend(pais_filter=pais)
    canal = build_canal_prog(pais_filter=pais, min_leads=10)
    may_l = sum(p['may_l'] for p in progs)
    if may_l < 10: continue  # skip micro countries
    int_countries_data[pais] = {
        'progs': progs[:30], 'trend': trend, 'canal': canal,
        'abr_leads': sum(p['abr_l'] for p in progs),
        'may_leads': may_l,
        'abr_cr': trend[3]['cr'],
        'may_cr':  trend[4]['cr']
    }
    print(f'  {pais}: {len(progs)} progs, may_leads={may_l}, may_cr={trend[4]["cr"]}%')

# All INT combined
prog_int  = build_prog_stats(pais_filter=INT_PAISES, min_may_leads=10)
trend_int = build_trend(pais_filter=INT_PAISES)
canal_int = build_canal_prog(pais_filter=INT_PAISES, min_leads=30)

# All combined
trend_all = build_trend(pais_filter=None)
print('ALL trend:', [(g['mes'],g['leads'],g['cr']) for g in trend_all])

# ── 2025 YoY baselines ────────────────────────────────────────────────────────
trend_mx_2025  = build_trend_2025(pais_filter=MX_PAIS)
trend_int_2025 = build_trend_2025(pais_filter=INT_PAISES)
trend_all_2025 = build_trend_2025(pais_filter=None)
print('MX 2025:', [(g['mes'],g['leads'],g['cr']) for g in trend_mx_2025])

# ── FUNNEL (MX ONLY) — CUADRO EVOLUTIVO ─────────────────────────────────────
# CUADRO EVOLUTIVO has sheet 'Export', col 'CONTACTO_UTIL_POS' (not 'UTIL POSITIVO')
# Months like 'Ene 2026', 'Set 2025' (Spanish Sep)
funnel_raw = pd.read_excel(FUNNEL_FILE, sheet_name='Export')
funnel_raw.columns = [fix(str(c)) for c in funnel_raw.columns]
funnel_raw['MES']   = funnel_raw.iloc[:,0].apply(fix).str.strip()
funnel_raw['MEDIO'] = funnel_raw['MEDIO'].apply(fix).str.strip()
funnel_raw = funnel_raw[
    ~funnel_raw['MES'].isin(['Total','nan','']) &
    ~funnel_raw['MES'].str.startswith('Filtros', na=True)
]
funnel_raw = funnel_raw[funnel_raw['MEDIO'].notna() & (funnel_raw['MEDIO'] != 'nan')]
# Rename CONTACTO_UTIL_POS → UTIL POSITIVO for compatibility
if 'CONTACTO_UTIL_POS' in funnel_raw.columns:
    funnel_raw = funnel_raw.rename(columns={'CONTACTO_UTIL_POS': 'UTIL POSITIVO'})

fmeses        = ['Ene 2026','Feb 2026','Mar 2026','Abr 2026','May 2026']
fmeses_labels = ['Ene','Feb','Mar','Abr','May*']
fmeses_2025   = ['Ene 2025','Feb 2025','Mar 2025','Abr 2025','May 2025']

def _funnel_metrics(r_sub):
    """Extract all funnel metrics from a filtered sub-DataFrame."""
    l = int(r_sub['LEADS'].sum())
    if l == 0:
        return {'leads':0,'contact':0,'util':0,'refs':0,'ventas':0,'cr':0,'pct_contact':0,'pct_contact_efectivo':0}
    c   = int(r_sub['CONTACTO GENERAL'].sum())
    u   = int(r_sub['UTIL POSITIVO'].sum())
    ref = int(r_sub['REFERENCIAS'].sum())
    v   = int(r_sub['VENTAS'].sum())
    return {
        'leads': l, 'contact': c, 'util': u, 'refs': ref, 'ventas': v,
        'cr':  round(v/l*100, 2),
        'pct_contact': round(c/l*100, 1),
        'pct_contact_efectivo': round(u/c*100, 1) if c > 0 else 0,
    }

_empty_funnel = {'leads':0,'contact':0,'util':0,'refs':0,'ventas':0,'cr':0,'pct_contact':0,'pct_contact_efectivo':0}

# Use 2026 leads to filter medios (min 500 leads across 2026)
medios_2026 = funnel_raw[funnel_raw['MES'].str.contains('2026', na=False)]
medios_with_data = medios_2026.groupby('MEDIO')['LEADS'].sum()
key_medios = [m for m in medios_with_data.index if medios_with_data[m] >= 500]

medio_stats = {}
for medio in key_medios:
    sub = funnel_raw[funnel_raw['MEDIO'] == medio]
    rows = []
    for mes, mes_lbl, mes_py in zip(fmeses, fmeses_labels, fmeses_2025):
        r26 = sub[sub['MES'] == mes]
        r25 = sub[sub['MES'] == mes_py]
        m26 = _funnel_metrics(r26) if len(r26) > 0 else dict(_empty_funnel)
        m25 = _funnel_metrics(r25) if len(r25) > 0 else None
        entry = {'mes': mes_lbl, **m26, 'py': m25}
        rows.append(entry)

    # ── YoY contact alert: compare last month with data vs same month prior year ──
    alert_contact = None
    for row in reversed(rows):
        if row['leads'] > 0 and row['py'] and row['py']['leads'] > 0:
            diff_pc  = round(row['pct_contact'] - row['py']['pct_contact'], 1)
            diff_pce = round(row['pct_contact_efectivo'] - row['py']['pct_contact_efectivo'], 1)
            if diff_pc <= -5 or diff_pce <= -5:
                alert_contact = {
                    'mes': row['mes'],
                    'pc_26':   row['pct_contact'],         'pc_25':   row['py']['pct_contact'],
                    'diff_pc': diff_pc,
                    'pce_26':  row['pct_contact_efectivo'],'pce_25':  row['py']['pct_contact_efectivo'],
                    'diff_pce': diff_pce,
                }
            break  # solo el mes más reciente con datos en ambos años

    medio_stats[medio] = {'rows': rows, 'alert': alert_contact}

print(f'MX medios loaded: {len(medio_stats)}')

# ── FUNNEL POR PROGRAMA (nuevo archivo data - 2026-06-01T215409.317.xlsx) ────
def build_funnel_prog():
    """Parse the per-program funnel file (Marzo, Abril, Mayo — 3 months, 28 cols).
    Col 0: PROGRAMA. Month blocks: Marzo=1-9, Abril=10-18, Mayo=19-27.
    Per-block cols: LEADS, CONTACTO GENERAL, CONTACTO_UTIL_POS, REFERENCIAS, VENTAS,
                    %CONTACTO LEAD, %CONTACTO EFECTO, %REFERENCIAS UTIL, %VENTAS REFERENCIAS
    Returns dict with 'programs' list and 'totals' dict.
    Min leads: any month >= 100.
    """
    try:
        fp_raw = pd.read_excel(FUNNEL_PROG_FILE, header=None)
    except Exception as e:
        print(f'AVISO: no se pudo leer FUNNEL_PROG_FILE: {e}')
        return {'programs': [], 'totals': {}}

    # Month offsets: (label, start_col) — file has only 3 months
    MONTH_OFFSETS = [
        ('mar', 1),
        ('abr', 10),
        ('may', 19),
    ]

    def _to_f(val):
        try:
            v = float(val)
            return 0.0 if pd.isna(v) else v
        except:
            return 0.0

    programs = []
    month_totals = {m: {'leads': 0, 'contacto': 0, 'util': 0, 'ventas': 0} for m, _ in MONTH_OFFSETS}

    for row_i in range(2, len(fp_raw)):
        row = fp_raw.iloc[row_i]
        prog_raw = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        if not prog_raw or prog_raw in ('nan', '', 'Total', 'NaN', 'NO IDENTIFICADO'):
            continue

        prog_name = fix(prog_raw)
        months = {}

        for month_label, start_col in MONTH_OFFSETS:
            leads    = _to_f(row.iloc[start_col])
            contacto = _to_f(row.iloc[start_col + 1])
            util     = _to_f(row.iloc[start_col + 2])
            refs     = _to_f(row.iloc[start_col + 3])
            ventas   = _to_f(row.iloc[start_col + 4])

            pct_cont = round(contacto / leads * 100, 1) if leads > 0 else 0.0
            pct_ef   = round(util / contacto * 100, 1) if contacto > 0 else 0.0
            cr       = round(ventas / leads * 100, 2) if leads > 0 else 0.0

            months[month_label] = {
                'leads': int(leads), 'contacto': int(contacto),
                'util': int(util), 'refs': int(refs), 'ventas': int(ventas),
                'pct_cont': pct_cont, 'pct_ef': pct_ef, 'cr': cr
            }

            if leads > 0:
                month_totals[month_label]['leads']    += int(leads)
                month_totals[month_label]['contacto'] += int(contacto)
                month_totals[month_label]['util']     += int(util)
                month_totals[month_label]['ventas']   += int(ventas)

        # Only include rows where at least one month has leads >= 100
        if not any(months[m]['leads'] >= 100 for m in months):
            continue

        may = months['may']
        mar = months['mar']

        may_leads    = may['leads']
        may_pct_cont = may['pct_cont']
        may_pct_ef   = may['pct_ef']
        may_cr       = may['cr']

        # Trends: Mayo - Marzo
        trend_pct_cont = round(may_pct_cont - mar['pct_cont'], 1)
        trend_pct_ef   = round(may_pct_ef   - mar['pct_ef'],   1)
        trend_cr       = round(may_cr        - mar['cr'],       2)

        # Bottleneck classification based on May data
        if may_pct_cont < 50:
            bottleneck = 'contacto'
        elif may_pct_ef < 20:
            bottleneck = 'efectividad'
        elif may_cr < 1.2:
            bottleneck = 'cierre'
        else:
            bottleneck = 'escalar'

        programs.append({
            'prog':         prog_name,
            'may_leads':    may_leads,
            'mar':          mar,
            'abr':          months['abr'],
            'may':          may,
            'months':       months,
            'trend_pct_cont': trend_pct_cont,
            'trend_pct_ef':   trend_pct_ef,
            'trend_cr':       trend_cr,
            'bottleneck':   bottleneck,
        })

    programs.sort(key=lambda x: -x['may_leads'])

    # Compute overall totals with derived metrics
    totals = {}
    for month_label, t in month_totals.items():
        l = t['leads']; c = t['contacto']; u = t['util']; v = t['ventas']
        totals[month_label] = {
            'leads':    l, 'contacto': c, 'util': u, 'ventas': v,
            'pct_cont': round(c / l * 100, 1) if l > 0 else 0.0,
            'pct_ef':   round(u / c * 100, 1) if c > 0 else 0.0,
            'cr':       round(v / l * 100, 2) if l > 0 else 0.0,
        }
    # Back-compat keys used by existing diagnostico ¿Qué cambió? section
    if 'mar' in totals: totals['Marzo'] = totals['mar']
    if 'may' in totals: totals['Mayo']  = totals['may']

    print(f'funnel_prog: {len(programs)} programas cargados')
    return {'programs': programs, 'totals': totals}

# ── FUNNEL POR PROGRAMA × MEDIO (nuevo archivo data - 2026-06-01T221257.291.xlsx) ─
def build_funnel_prog_medio():
    """Parse the per-program × medio funnel file — all 5 months.
    Cols: 0=DESCRIPCIÓN PROGRAMA, 1=MEDIO
    Enero=2-10, Feb=11-19, Marzo=20-28, Abril=29-37, Mayo=38-46
    Each month block: LEADS, CONTACTO GENERAL, CONTACTO_UTIL_POS, REFERENCIAS, VENTAS,
                      %CONTACO LEAD, %CONTACO EFECTO, %REFERENCIAS UTIL, %VENTAS REFERENCIAS
    Min leads filter: at least one month >= 30.
    """
    try:
        fp_raw = pd.read_excel(FUNNEL_PROG_MEDIO_FILE, header=None)
    except Exception as e:
        print(f'AVISO: no se pudo leer FUNNEL_PROG_MEDIO_FILE: {e}')
        return []

    def _to_f(val):
        try:
            v = float(val)
            return 0.0 if pd.isna(v) else v
        except:
            return 0.0

    # Month offsets (col 0=PROG, col 1=MEDIO, months start at col 2)
    MONTH_OFFSETS = [
        ('ene', 2),
        ('feb', 11),
        ('mar', 20),
        ('abr', 29),
        ('may', 38),
    ]

    results = []

    for row_i in range(2, len(fp_raw)):
        row = fp_raw.iloc[row_i]

        prog_raw  = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        medio_raw = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''

        if not prog_raw or prog_raw in ('nan', '', 'NaN', 'Total', 'NO IDENTIFICADO'):
            continue
        if medio_raw in ('nan', '', 'NaN', 'Total'):
            continue

        prog_name  = fix(prog_raw)
        medio_name = fix(medio_raw)

        def _extract_month(start):
            leads    = _to_f(row.iloc[start + 0])
            contacto = _to_f(row.iloc[start + 1])
            util     = _to_f(row.iloc[start + 2])
            refs     = _to_f(row.iloc[start + 3])
            ventas   = _to_f(row.iloc[start + 4])
            pct_cont = round(contacto / leads * 100, 1) if leads > 0 else 0.0
            pct_ef   = round(util / contacto * 100, 1) if contacto > 0 else 0.0
            cr       = round(ventas / leads * 100, 2) if leads > 0 else 0.0
            return {
                'leads': int(leads), 'contacto': int(contacto),
                'util': int(util), 'refs': int(refs), 'ventas': int(ventas),
                'pct_cont': pct_cont, 'pct_ef': pct_ef, 'cr': cr
            }

        months = {}
        for month_label, start_col in MONTH_OFFSETS:
            months[month_label] = _extract_month(start_col)

        # Skip if no month has >= 30 leads
        if not any(months[m]['leads'] >= 30 for m in months):
            continue

        may = months['may']
        mar = months['mar']

        pct_cont = may['pct_cont']
        pct_ef   = may['pct_ef']
        cr       = may['cr']

        delta_cont = round(pct_cont - mar['pct_cont'], 1)
        delta_ef   = round(pct_ef   - mar['pct_ef'],   1)
        delta_cr   = round(cr       - mar['cr'],        2)

        # Bottleneck classification (May data)
        if pct_cont < 50:
            bottleneck = 'contacto'
        elif pct_ef < 20:
            bottleneck = 'efectividad'
        elif cr < 1.2:
            bottleneck = 'cierre'
        else:
            bottleneck = 'bueno'

        results.append({
            'prog':        prog_name,
            'medio':       medio_name,
            'months':      months,
            # Back-compat flat fields (used by existing diag_medio section)
            'may_leads':   may['leads'],
            'may_cont':    may['contacto'],
            'may_util':    may['util'],
            'may_ventas':  may['ventas'],
            'pct_cont':    pct_cont,
            'pct_ef':      pct_ef,
            'cr':          cr,
            'mar_pct_cont': mar['pct_cont'],
            'mar_pct_ef':   mar['pct_ef'],
            'mar_cr':       mar['cr'],
            'delta_cont':  delta_cont,
            'delta_ef':    delta_ef,
            'delta_cr':    delta_cr,
            'bottleneck':  bottleneck,
        })

    results.sort(key=lambda x: -x['may_leads'])
    print(f'funnel_prog_medio: {len(results)} combinaciones prog×medio cargadas')
    return results


# ── SAVE ─────────────────────────────────────────────────────────────────────
# ── INVERSIÓN x CANAL (RESUMEN file, May 2026) ───────────────────────────────
def build_inv_canal():
    try:
        resumen_raw = pd.read_excel(RESUMEN_FILE, sheet_name='Export', header=None)
    except Exception as e:
        print(f'AVISO: no se pudo leer RESUMEN_FILE: {e}')
        return []

    # Identify May 2026 columns: row0='may 2026', row1=LEADS/VENTAS/INVERSION
    r0 = [str(x).lower().strip() for x in resumen_raw.iloc[0].tolist()]
    r1 = [str(x).upper().strip() for x in resumen_raw.iloc[1].tolist()]
    may_leads_idx = may_ventas_idx = may_inv_idx = None
    for i, (m, met) in enumerate(zip(r0, r1)):
        if m == 'may 2026':
            if met == 'LEADS'   and may_leads_idx  is None: may_leads_idx  = i
            if met == 'VENTAS'  and may_ventas_idx is None: may_ventas_idx = i
            if met == 'INVERSION' and may_inv_idx  is None: may_inv_idx    = i

    if None in (may_leads_idx, may_ventas_idx, may_inv_idx):
        print('AVISO: no se encontraron columnas May 2026 en RESUMEN')
        return []

    # Leaf rows: CANAL not nan/Total AND NIVEL not nan/Total
    data_r = resumen_raw.iloc[2:].copy()
    data_r.columns = list(range(resumen_raw.shape[1]))
    mask = (
        data_r[3].notna() & ~data_r[3].astype(str).isin(['nan','Total','']) &
        data_r[1].notna() & ~data_r[1].astype(str).isin(['nan','Total',''])
    )
    leaf = data_r[mask].copy()
    for col in [may_leads_idx, may_ventas_idx, may_inv_idx]:
        leaf[col] = pd.to_numeric(leaf[col], errors='coerce').fillna(0)

    grouped = leaf.groupby(3)[[may_leads_idx, may_ventas_idx, may_inv_idx]].sum().reset_index()
    grouped.columns = ['canal', 'leads', 'ventas', 'inversion']

    # Fix encoding for canal names
    grouped['canal'] = grouped['canal'].apply(fix)

    # Filter: at least some leads or ventas
    grouped = grouped[(grouped['leads'] > 0) | (grouped['ventas'] > 0)].copy()

    # Build programs per canal from NEW_FILE (MX, May 2026)
    may_l_col = leads_cols[4]   # May 2026 LEADS column
    may_m_col = mats_cols[4]    # May 2026 MATR column
    mx_progs  = data_progs[data_progs['PAIS'] == MX_PAIS].copy() if MX_PAIS in data_progs['PAIS'].values else data_progs.copy()
    for col in [may_l_col, may_m_col]:
        if col:
            mx_progs[col] = pd.to_numeric(mx_progs[col], errors='coerce').fillna(0)

    def get_progs_for_canal(canal_name):
        sub = mx_progs[mx_progs['CANAL'] == canal_name].copy()
        if sub.empty:
            return []
        if may_l_col:
            sub['_ml'] = sub[may_l_col]
        else:
            sub['_ml'] = 0
        if may_m_col:
            sub['_mm'] = sub[may_m_col]
        else:
            sub['_mm'] = 0
        grp = sub.groupby('PROGRAMA')[['_ml','_mm']].sum().reset_index()
        grp = grp[grp['_ml'] > 0].sort_values('_ml', ascending=False).head(50)
        rows = []
        for _, r in grp.iterrows():
            l = int(r['_ml']); m = int(r['_mm'])
            cr = round(m/l*100, 2) if l > 0 else 0
            rows.append({'prog': fix(str(r['PROGRAMA'])), 'leads': l, 'ventas': m, 'cr': cr})
        return rows

    result = []
    for _, row in grouped.iterrows():
        canal = row['canal']
        leads    = int(row['leads'])
        ventas   = int(row['ventas'])
        inversion = int(row['inversion'])
        cpl = round(inversion / leads,    1) if leads > 0 and inversion > 0 else None
        cpa = round(inversion / ventas,   1) if ventas > 0 and inversion > 0 else None
        cr  = round(ventas    / leads * 100, 2) if leads > 0 else 0
        progs = get_progs_for_canal(canal)
        result.append({
            'canal': canal, 'leads': leads, 'ventas': ventas, 'inversion': inversion,
            'cpl': cpl, 'cpa': cpa, 'cr': cr,
            'progs': progs
        })

    # Sort: paid (inversion>0) desc by inversion, then organic desc by leads
    paid    = sorted([r for r in result if r['inversion'] > 0], key=lambda x: -x['inversion'])
    organic = sorted([r for r in result if r['inversion'] == 0], key=lambda x: -x['leads'])
    combined = paid + organic
    print(f'inv_canal: {len(paid)} canales pago, {len(organic)} orgánicos')
    return combined

inv_canal = build_inv_canal()

payload = {
    'months':       MONTHS_LABELS,
    'prog_mx':      prog_mx[:60],
    'prog_int':     prog_int[:40],
    'int_countries': int_countries_data,
    'canal_mx':       canal_mx,
    'canal_trend_mx': canal_trend_mx,
    'canal_int':      canal_int,
    'trend_mx':     trend_mx,
    'trend_int':    trend_int,
    'trend_all':    trend_all,
    'medio_stats':  medio_stats,   # MX ONLY
    'trend_mx_2025':  trend_mx_2025,
    'trend_int_2025': trend_int_2025,
    'trend_all_2025': trend_all_2025,
    'may_factor':   round(MAY_FACTOR,2),
    'may_days':     MAY_DAYS_DONE,
    'inv_canal':    inv_canal,
    'funnel_prog':       build_funnel_prog(),
    'funnel_prog_medio': build_funnel_prog_medio(),
}
with open(r'C:\Users\USUARIO\AppData\Local\Temp\dashboard_data.json','w',encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
print('JSON saved OK.')