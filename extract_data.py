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
NEW_FILE    = r'C:\Users\USUARIO\Downloads\data - 2026-05-29T143324.732.xlsx'
MATS_FILE   = r'C:\Users\USUARIO\Downloads\data - 2026-05-21T133752.317.xlsx'
FUNNEL_FILE = r'C:\Users\USUARIO\Downloads\CUADRO EVOLUTIVO (5).xlsx'
PRECIO_FILE = r'C:\Users\USUARIO\Downloads\TABLA_PRECIOS_2026_ABRIL_COMPLETA (15).xlsx'

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

# ── LOAD REAL MAY MATRÍCULAS (separate file, mats only by program) ─────────────
_mats_raw = pd.read_excel(MATS_FILE, header=None)
_mats_months  = [fix(str(x)) for x in _mats_raw.iloc[0].tolist()]
_mats_metrics = [fix(str(x)) for x in _mats_raw.iloc[1].tolist()]
_mats_cols = []
for m, met in zip(_mats_months, _mats_metrics):
    if m in ('nan', 'Mes y Año', ''):
        _mats_cols.append('PROGRAMA')
    else:
        _mats_cols.append(f'{m}__{met.strip()}')
_mats_raw.columns = _mats_cols
_mdf = _mats_raw.iloc[2:].copy(); _mdf.columns = _mats_cols
_mdf['PROGRAMA'] = _mdf['PROGRAMA'].apply(fix).str.strip()
_mdf = _mdf[~_mdf['PROGRAMA'].isin(['nan','','Total','NaN'])]
_may_mat_col = [c for c in _mats_cols if 'may 2026' in c.lower()][0]
_mdf[_may_mat_col] = pd.to_numeric(_mdf[_may_mat_col], errors='coerce').fillna(0)
# Build lookup: norm_prog(name) → real may mats
_real_may_mats = {}
for _, row in _mdf.iterrows():
    nk = norm_prog(row['PROGRAMA'])
    _real_may_mats[nk] = int(row[_may_mat_col])
print(f'Real May mats loaded: {len(_real_may_mats)} programs, total={sum(_real_may_mats.values())}')

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

MAY_DAYS_DONE  = 28   # auto-detectado del nombre del archivo
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

# ── SAVE ─────────────────────────────────────────────────────────────────────
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
    'may_days':     MAY_DAYS_DONE
}
with open(r'C:\Users\USUARIO\AppData\Local\Temp\dashboard_data.json','w',encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
print('JSON saved OK.')