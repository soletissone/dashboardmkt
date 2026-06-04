"""
ACTUALIZADOR DE DASHBOARD SEMANAL
==================================
Corre este script con doble clic (o desde terminal: python actualizar_dashboard.py)

Lo que hace:
1. Detecta automáticamente los archivos más recientes en Downloads
2. Actualiza extract_data.py con los nuevos paths
3. Corre extract_data.py → genera dashboard_data.json
4. Corre build_dashboard.py → genera analisis_semanal.html
5. Abre el dashboard en el navegador

Archivos que detecta (toma siempre el más reciente de cada tipo):
  - "data - *.xlsx"                    → archivo principal de leads/programas
  - "data - *.xlsx" (segundo más reciente) → archivo de matrículas
  - "CUADRO EVOLUTIVO*.xlsx"           → contactación
  - "TABLA_PRECIOS*.xlsx"              → precios (solo si cambia)
"""

import os, re, glob, subprocess, sys, webbrowser
from pathlib import Path
from datetime import datetime

DOWNLOADS = Path(r'C:\Users\USUARIO\Downloads')
TEMP      = Path(r'C:\Users\USUARIO\AppData\Local\Temp')
EXTRACT   = TEMP / 'extract_data.py'
BUILD     = TEMP / 'build_dashboard.py'
OUTPUT    = DOWNLOADS / 'analisis_semanal.html'

# ── Detectar archivos más recientes ──────────────────────────────────────────
def newest(pattern):
    files = sorted(glob.glob(str(DOWNLOADS / pattern)), key=os.path.getmtime, reverse=True)
    return files[0] if files else None

def newest_nth(pattern, n=0):
    files = sorted(glob.glob(str(DOWNLOADS / pattern)), key=os.path.getmtime, reverse=True)
    return files[n] if len(files) > n else None

def detect_file_type(path):
    """Detecta si es el archivo de leads/programas (tiene CANAL/PAIS) o de mats (solo programas x mes)."""
    try:
        raw = pd.read_excel(path, header=None, nrows=2)
        row1 = [str(x).upper() for x in raw.iloc[1].tolist()]
        # Leads file: row 1 tiene PAIS, CANAL, NIVEL
        if any('CANAL' in c or 'PAIS' in c for c in row1):
            return 'leads'
        # Mats file: row 1 tiene MATRICULAS repetido y PROGRAMA
        if row1.count('MATR') > 3 or any('PROGRAMA' in c for c in row1):
            return 'mats'
    except Exception:
        pass
    return 'unknown'

import pandas as pd_detect

data_files = sorted(
    glob.glob(str(DOWNLOADS / 'data - *.xlsx')),
    key=os.path.getmtime, reverse=True
)

leads_file = None
mats_file  = None

import pandas as pd_tmp

# Solo buscar mats en archivos de la misma semana que el leads file más reciente
leads_mtime = os.path.getmtime(data_files[0]) if data_files else 0
ONE_WEEK = 7 * 24 * 3600

for f in data_files:
    try:
        raw  = pd_tmp.read_excel(f, header=None, nrows=2)
        row1 = [str(x).upper() for x in raw.iloc[1].tolist()]

        # Leads file: MUST have CANAL in row1
        is_leads = any('CANAL' in c for c in row1)
        # Mats file: PROGRAMA + 3+ MATR columns, no CANAL, mismo período (7 días)
        file_age = leads_mtime - os.path.getmtime(f)
        is_mats  = (not is_leads and
                    any('PROGRAMA' in c for c in row1) and
                    sum(1 for c in row1 if 'MATR' in c) >= 3 and
                    file_age <= ONE_WEEK)

        if leads_file is None and is_leads:
            leads_file = f
        elif mats_file is None and is_mats:
            mats_file = f
    except Exception:
        continue
    if leads_file and mats_file:
        break

# Fallback: si no hay mats separado de esta semana, extraer del archivo de leads
if not mats_file and leads_file:
    mats_file = leads_file
    print(f"  AVISO: sin mats separado esta semana — usando matriculas del archivo de leads")

funnel_prog_medio_file = None
for f in data_files:
    try:
        raw = pd_tmp.read_excel(f, header=None, nrows=2)
        r0c0 = str(raw.iloc[0, 0]).strip().upper()
        r1 = [str(x).upper() for x in raw.iloc[1].tolist()[:3]]
        if r0c0 == 'MES' and 'MEDIO' in r1:
            funnel_prog_medio_file = f
            break
    except:
        continue

funnel_prog_file = None
for f in data_files:
    try:
        raw = pd_tmp.read_excel(f, header=None, nrows=2)
        r0 = str(raw.iloc[0, 0]).strip().upper()
        r1 = [str(x).upper() for x in raw.iloc[1].tolist()]
        if r0 == 'MES' and any('CONTACTO' in c for c in r1) and f != funnel_prog_medio_file:
            funnel_prog_file = f
            break
    except:
        continue

funnel_file  = newest('CUADRO EVOLUTIVO*.xlsx')
precio_file  = newest('TABLA_PRECIOS*.xlsx')
resumen_file = newest('RESUMEN*.xlsx')

print("=" * 60)
print("  ACTUALIZADOR DE DASHBOARD SEMANAL")
print("=" * 60)
print()
print("Archivos detectados:")
print(f"  Leads/Programas : {Path(leads_file).name if leads_file else 'ERROR NO ENCONTRADO'}")
print(f"  Matrículas      : {Path(mats_file).name  if mats_file  else 'ERROR NO ENCONTRADO'}")
print(f"  Funnel x Prog   : {Path(funnel_prog_file).name if funnel_prog_file else 'OPCIONAL - no encontrado'}")
print(f"  Funnel Prog×Med : {Path(funnel_prog_medio_file).name if funnel_prog_medio_file else 'OPCIONAL - no encontrado'}")
print(f"  Contactación    : {Path(funnel_file).name if funnel_file else 'ERROR NO ENCONTRADO'}")
print(f"  Precios         : {Path(precio_file).name if precio_file else 'ERROR NO ENCONTRADO'}")
print(f"  Resumen (inv)   : {Path(resumen_file).name if resumen_file else 'ERROR NO ENCONTRADO'}")
print()

# Verificar que están todos
missing = []
if not leads_file:   missing.append("Archivo de leads (data - FECHA.xlsx)")
if not mats_file:    missing.append("Archivo de matrículas (segundo data - FECHA.xlsx)")
if not funnel_file:  missing.append("CUADRO EVOLUTIVO.xlsx")
if not precio_file:  missing.append("TABLA_PRECIOS.xlsx")
if not resumen_file: missing.append("RESUMEN.xlsx (inversión por canal)")

if not funnel_prog_file:
    print("  AVISO: archivo de funnel x programa (data - *.xlsx con CONTACTO) no encontrado — tab Diagnóstico estará vacío")
if not funnel_prog_medio_file:
    print("  AVISO: archivo de funnel x programa×medio no encontrado — sección diagnóstico por medio estará vacía")

if missing:
    print("ERROR Faltan archivos en Downloads:")
    for m in missing:
        print(f"   - {m}")
    input("\nPresioná Enter para salir...")
    sys.exit(1)

# ── Actualizar paths en extract_data.py ──────────────────────────────────────
def escape_path(p):
    return p.replace('\\', '\\\\')

with open(EXTRACT, encoding='utf-8') as f:
    code = f.read()

# Detectar mes actual y días reales del archivo
_MONTH_DAYS  = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
_MONTH_NAMES = {1:'ene',2:'feb',3:'mar',4:'abr',5:'may',6:'jun',
                7:'jul',8:'ago',9:'sep',10:'oct',11:'nov',12:'dic'}
fname = Path(leads_file).name
m_date = re.search(r'data - 2026-(\d{2})-(\d{2})T', fname)

may_days    = 31       # días de mayo completados (siempre completo cuando hay archivo posterior)
cur_month   = 'may 2026'
cur_days    = 31

if m_date:
    file_month = int(m_date.group(1))
    file_day   = int(m_date.group(2))
    if file_month == 5:                  # archivo de mayo
        may_days  = file_day - 1
        cur_month = 'may 2026'
        cur_days  = may_days
        print(f"  Archivo mayo dia {file_day} -> dias reales: {may_days}")
    else:                                # archivo de junio o posterior
        may_days   = 31                  # mayo completo
        _new_month = f'{_MONTH_NAMES[file_month]} 2026'
        _new_days  = file_day - 1        # datos al día anterior del archivo
        if _new_days <= 0:
            # Día 1 del mes nuevo → todavía sin datos del mes nuevo, usar mes anterior completo
            cur_month = f'{_MONTH_NAMES[file_month-1]} 2026'
            cur_days  = _MONTH_DAYS[file_month - 1]
            print(f"  Archivo dia 1 de {_new_month} -> usando {cur_month} completo ({cur_days}d)")
        else:
            cur_month = _new_month
            cur_days  = _new_days
            print(f"  Archivo {cur_month} dia {file_day} -> mayo completo, {cur_month}: {cur_days} dias reales")
else:
    print(f"  AVISO: no se pudo detectar fecha del archivo, usando defaults")

# Reemplazar paths línea por línea (evita problemas con \ en paths de Windows)
new_lines = []
for line in code.splitlines():
    stripped = line.strip()
    if stripped.startswith('NEW_FILE'):
        line = f"NEW_FILE    = r'{leads_file}'"
    elif stripped.startswith('MATS_FILE'):
        line = f"MATS_FILE   = r'{mats_file}'"
    elif stripped.startswith('FUNNEL_FILE'):
        line = f"FUNNEL_FILE = r'{funnel_file}'"
    elif stripped.startswith('PRECIO_FILE'):
        line = f"PRECIO_FILE = r'{precio_file}'"
    elif stripped.startswith('RESUMEN_FILE'):
        line = f"RESUMEN_FILE = r'{resumen_file}'"
    elif stripped.startswith('FUNNEL_PROG_FILE') and funnel_prog_file:
        line = f"FUNNEL_PROG_FILE = r'{funnel_prog_file}'"
    elif stripped.startswith('FUNNEL_PROG_MEDIO_FILE') and funnel_prog_medio_file:
        line = f"FUNNEL_PROG_MEDIO_FILE = r'{funnel_prog_medio_file}'"
    elif stripped.startswith('MAY_DAYS_DONE'):
        line = f"MAY_DAYS_DONE  = {may_days}   # auto-detectado del nombre del archivo"
    elif stripped.startswith('CUR_MONTH'):
        line = f"CUR_MONTH      = '{cur_month}'   # mes actual auto-detectado"
    elif stripped.startswith('CUR_DAYS_DONE'):
        line = f"CUR_DAYS_DONE  = {cur_days}            # días reales del mes actual"
    new_lines.append(line)

with open(EXTRACT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("\nOK Paths actualizados en extract_data.py")

# ── Correr extract_data.py ────────────────────────────────────────────────────
print("\n[1/2] Procesando datos...")
result = subprocess.run(
    [sys.executable, str(EXTRACT)],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
if result.returncode != 0:
    print("ERROR Error en extract_data.py:")
    print(result.stderr[-2000:])
    input("\nPresioná Enter para salir...")
    sys.exit(1)

# Mostrar resumen del extract
for line in result.stdout.splitlines():
    if any(k in line for k in ['MX progs', 'ALL trend', 'medios', 'JSON saved', 'NEW programs', 'May_days']):
        print(" ", line)

print("OK Datos procesados OK")

# ── Correr build_dashboard.py ─────────────────────────────────────────────────
print("\n[2/2] Generando dashboard...")
result2 = subprocess.run(
    [sys.executable, str(BUILD)],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
if result2.returncode != 0:
    print("ERROR Error en build_dashboard.py:")
    print(result2.stderr[-2000:])
    input("\nPresioná Enter para salir...")
    sys.exit(1)

print("OK Dashboard generado OK")

# ── Publicar en GitHub Pages ──────────────────────────────────────────────────
REPO_DIR = Path(r'C:\Users\USUARIO\Documents\dashboard-semanal-utel')
INDEX    = REPO_DIR / 'index.html'
PAGES_URL = 'https://soletissone-hub.github.io/dashboardmkt/'

print("\n[3/3] Publicando en GitHub...")
try:
    import shutil
    shutil.copy(str(OUTPUT), str(INDEX))

    fecha_commit = datetime.now().strftime('%d/%m/%Y')
    cmds = [
        ['git', '-C', str(REPO_DIR), 'add', 'index.html'],
        ['git', '-C', str(REPO_DIR), 'commit', '-m', f'Dashboard actualizado {fecha_commit}'],
        ['git', '-C', str(REPO_DIR), 'push'],
    ]
    git_ok = True
    for cmd in cmds:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode != 0 and 'nothing to commit' not in r.stdout + r.stderr:
            print(f"  AVISO git: {r.stderr.strip()[:200]}")
            git_ok = False
            break

    if git_ok:
        print(f"OK Publicado en GitHub Pages")
        print(f"   URL: {PAGES_URL}")
    else:
        print("  (El dashboard se genero OK pero no se pudo subir a GitHub)")
        print("   Subilo manualmente desde GitHub Desktop o corriendo 'git push'")
except Exception as e:
    print(f"  AVISO: no se pudo subir a GitHub automaticamente: {e}")

# ── Resumen final ─────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("  OK DASHBOARD ACTUALIZADO")
print(f"  Archivo local : {OUTPUT}")
print(f"  URL publica   : {PAGES_URL}")
print(f"  Fecha datos   : {cur_month} ({cur_days} dias reales)")
print("=" * 60)
print()

# Abrir GitHub Pages en el navegador
webbrowser.open(PAGES_URL)
print(f"Abriendo GitHub Pages: {PAGES_URL}")
input("\nPresioná Enter para cerrar...")
