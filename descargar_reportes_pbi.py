"""
DESCARGADOR AUTOMÁTICO DE REPORTES POWER BI
============================================
Corre este script ANTES de actualizar el dashboard.
Abre Chrome, se loguea en Power BI y descarga los 4 reportes.

Uso:
  python descargar_reportes_pbi.py

Requiere: pip install playwright && python -m playwright install chromium
"""

import sys, time, re, shutil
from pathlib import Path
from datetime import datetime

# ── Config local (no se sube a GitHub) ────────────────────────────────────────
try:
    from pbi_config import PBI_EMAIL, PBI_PASSWORD, REPORTES
except ImportError:
    print("ERROR: No se encontró pbi_config.py en la carpeta Temp")
    print("Creá el archivo C:\\Users\\USUARIO\\AppData\\Local\\Temp\\pbi_config.py")
    input("\nPresioná Enter para salir...")
    sys.exit(1)

DOWNLOADS = Path(r'C:\Users\USUARIO\Downloads')

# ── Playwright ────────────────────────────────────────────────────────────────
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

def login(page):
    """Loguea en Microsoft / Power BI."""
    print("  Navegando a Power BI...")
    page.goto("https://app.powerbi.com", wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    # Si ya está logueado, salir
    if 'app.powerbi.com' in page.url and 'login' not in page.url.lower():
        print("  Ya estaba logueado OK")
        return

    # Ingresar email
    try:
        page.wait_for_selector('input[type="email"]', timeout=10000)
        page.fill('input[type="email"]', PBI_EMAIL)
        page.click('input[type="submit"], button[type="submit"]')
        time.sleep(2)
    except PWTimeout:
        print("  AVISO: no apareció campo de email — puede que ya esté logueado")

    # Ingresar contraseña
    try:
        page.wait_for_selector('input[type="password"]', timeout=10000)
        page.fill('input[type="password"]', PBI_PASSWORD)
        page.click('input[type="submit"], button[type="submit"]')
        time.sleep(3)
    except PWTimeout:
        print("  AVISO: no apareció campo de contraseña")

    # "¿Mantener sesión iniciada?" → Sí
    try:
        btn = page.wait_for_selector('#idBtn_Back, input[value="No"], input[value="Yes"], #KmsiCheckboxField', timeout=5000)
        # Buscar el botón de "Sí"
        yes = page.query_selector('input[value="Yes"], #idBtn_Accept')
        if yes:
            yes.click()
        else:
            # Hacer click en "No" para no preguntar en el futuro (igualmente continúa)
            page.click('#idBtn_Back')
        time.sleep(3)
    except PWTimeout:
        pass  # No apareció el prompt

    # Verificar login exitoso
    try:
        page.wait_for_url('**/app.powerbi.com/**', timeout=15000)
        print("  Login OK")
    except PWTimeout:
        print("  AVISO: verificá si hay MFA (autenticación de dos factores)")
        print("  Si aparece una pantalla de verificación, completala manualmente y luego el script continúa...")
        # Esperar hasta 60 segundos para MFA manual
        for i in range(60):
            if 'app.powerbi.com' in page.url and 'login' not in page.url.lower():
                print("  Login completado OK")
                break
            time.sleep(1)
        else:
            print("  ERROR: no se pudo completar el login")
            return False
    return True


def click_text(page, texts, timeout=5000):
    """Busca y hace click en el primer elemento que contenga alguno de los textos."""
    for text in texts:
        for selector in [
            f'button:has-text("{text}")',
            f'[aria-label*="{text}"]',
            f'[title*="{text}"]',
            f'span:has-text("{text}")',
            f'div[role="menuitem"]:has-text("{text}")',
            f'li:has-text("{text}")',
        ]:
            try:
                el = page.wait_for_selector(selector, timeout=timeout)
                if el and el.is_visible():
                    el.click()
                    return True
            except PWTimeout:
                continue
    return False


def esperar_descarga_reciente(download_dir, segundos=90):
    """Espera hasta que aparezca un .xlsx nuevo en download_dir."""
    t0 = time.time()
    antes = {f for f in download_dir.glob('*.xlsx')}
    while time.time() - t0 < segundos:
        ahora = {f for f in download_dir.glob('*.xlsx')}
        nuevos = ahora - antes
        if nuevos:
            f = sorted(nuevos, key=lambda x: x.stat().st_mtime, reverse=True)[0]
            return f
        time.sleep(1)
    return None


def flujo_vista_amplia_exportar(page, nombre):
    """Flujo 1: Click en Vista Amplia → click en Exportar."""
    print(f"  [{nombre}] Hover sobre el visual...")
    # Hacer hover para que aparezcan los botones del visual
    for sel in ['[class*="visual-container"]', '[class*="visualContainer"]',
                '[class*="visual"]', 'div[data-testid*="visual"]']:
        try:
            vis = page.query_selector(sel)
            if vis:
                vis.hover()
                time.sleep(1)
                break
        except Exception:
            continue

    print(f"  [{nombre}] Click en Vista amplia...")
    ok = click_text(page, ['Vista amplia', 'Focus mode', 'Modo de enfoque',
                            'Ampliar', 'Expand', 'Expandir'], timeout=6000)
    if not ok:
        for sel in ['[aria-label*="Focus"]', '[aria-label*="Ampliar"]',
                    '[aria-label*="Vista amplia"]', '[title*="Vista amplia"]',
                    '[title*="Focus"]', '.focusModeButton']:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el and el.is_visible():
                    el.click(); ok = True; break
            except PWTimeout:
                continue

    if ok:
        print(f"    Vista amplia: OK")
        time.sleep(3)
    else:
        print(f"    Vista amplia: no encontrada, continuando igual...")

    print(f"  [{nombre}] Click en Exportar...")
    return click_text(page, ['Exportar', 'Export data', 'Exportar datos',
                              'Export', 'Descargar', 'Download'], timeout=8000)


def flujo_filtro_anio_exportar(page, nombre, anio='2026'):
    """Flujo 2: Aplicar filtro Año=2026 → Exportar."""
    print(f"  [{nombre}] Aplicando filtro Año {anio}...")
    time.sleep(3)

    # Buscar el panel de filtros o slicer de Mes y Año
    filter_applied = False

    # Intentar buscar slicer con "2026" o "Mes y Año"
    for sel in [
        f'div[aria-label*="2026"]',
        f'button:has-text("2026")',
        f'[title*="2026"]',
        f'div[class*="slicer"] button',
        f'div[class*="slicerItem"]',
    ]:
        try:
            items = page.query_selector_all(sel)
            for item in items:
                txt = item.inner_text() if hasattr(item, 'inner_text') else ''
                if '2026' in str(txt) or '2026' in (item.get_attribute('aria-label') or ''):
                    item.click()
                    filter_applied = True
                    print(f"    Filtro 2026 aplicado OK")
                    time.sleep(2)
                    break
            if filter_applied:
                break
        except Exception:
            continue

    if not filter_applied:
        print(f"    AVISO: no se encontró filtro 2026 automáticamente")
        print(f"    Seleccioná manualmente 'Todo 2026' en el filtro y presioná Enter...")
        input()

    print(f"  [{nombre}] Click en Exportar...")
    return click_text(page, ['Exportar', 'Export data', 'Exportar datos',
                              'Export', 'Descargar'], timeout=8000)


def flujo_vista_combinada_exportar(page, nombre):
    """Flujo 3: Click en Vista Combinada (arriba derecha) → seleccionar 2026 → Exportar."""
    print(f"  [{nombre}] Buscando 'Vista combinada' (arriba derecha)...")
    time.sleep(3)

    ok = click_text(page, ['Vista combinada', 'Combined view', 'Vista combinada',
                            'All', 'Todo', 'Combinar'], timeout=8000)

    if not ok:
        for sel in ['[aria-label*="combinada"]', '[aria-label*="combined"]',
                    '[title*="combinada"]', '[title*="combined"]',
                    'button:has-text("Vista")', '.combinedViewButton']:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el and el.is_visible():
                    el.click(); ok = True
                    print(f"    Vista combinada: {sel}")
                    break
            except PWTimeout:
                continue

    if ok:
        print(f"    Vista combinada: OK")
        time.sleep(3)
    else:
        print(f"    AVISO: no encontré 'Vista combinada' — seleccioná manualmente y presioná Enter...")
        input()

    # Seleccionar todos los meses de 2026
    print(f"  [{nombre}] Seleccionando todos los meses 2026...")
    for sel_all in ['button:has-text("Seleccionar todo")', 'button:has-text("Select all")',
                    '[aria-label*="Select all"]', '[aria-label*="Seleccionar todo"]',
                    'input[type="checkbox"][aria-label*="all"]']:
        try:
            el = page.wait_for_selector(sel_all, timeout=4000)
            if el and el.is_visible():
                el.click()
                print(f"    Seleccionar todo: OK")
                time.sleep(2)
                break
        except PWTimeout:
            continue

    print(f"  [{nombre}] Click en Exportar...")
    return click_text(page, ['Exportar', 'Export data', 'Exportar datos',
                              'Export', 'Descargar'], timeout=8000)


def exportar_reporte(page, reporte, download_dir):
    """Navega al reporte, hace click en Vista Amplia → Exportar y descarga el Excel."""
    nombre = reporte['nombre']
    url    = reporte['url']

    if not url:
        print(f"  SALTANDO {nombre} — URL no configurada aún")
        return None

    flujo = reporte.get('flujo', 'vista_amplia_exportar')

    print(f"\n  [{nombre}] Abriendo reporte (flujo: {flujo})...")
    page.goto(url, wait_until='domcontentloaded', timeout=40000)
    time.sleep(5)

    # ── Ejecutar flujo específico ──────────────────────────────────────────────
    exportar_ok = False
    if flujo == 'vista_amplia_exportar':
        exportar_ok = flujo_vista_amplia_exportar(page, nombre)
    elif flujo == 'filtro_anio_exportar':
        exportar_ok = flujo_filtro_anio_exportar(page, nombre, reporte.get('filtro_anio', '2026'))
    elif flujo == 'vista_combinada_exportar':
        exportar_ok = flujo_vista_combinada_exportar(page, nombre)
    else:
        exportar_ok = flujo_vista_amplia_exportar(page, nombre)

    if not exportar_ok:
        print(f"    No se encontró Exportar automáticamente.")
        print(f"    Exportá manualmente y presioná Enter cuando el archivo esté en Downloads...")
        input()
        files = sorted(DOWNLOADS.glob('*.xlsx'), key=lambda f: f.stat().st_mtime, reverse=True)
        return files[0] if files else None

    # ── Confirmar formato y esperar descarga ───────────────────────────────────
    time.sleep(2)
    # A veces aparece diálogo de confirmación de formato
    for confirm_sel in [
        'button:has-text("Exportar")', 'button:has-text("Export")',
        'button:has-text(".xlsx")',    'button:has-text("Excel")',
        'button[type="submit"]',
    ]:
        try:
            el = page.wait_for_selector(confirm_sel, timeout=4000)
            if el and el.is_visible():
                el.click()
                print(f"    Confirmado: {confirm_sel}")
                break
        except PWTimeout:
            continue

    print(f"    Esperando descarga...")
    archivo = esperar_descarga_reciente(download_dir, segundos=90)
    if archivo:
        print(f"    Descargado: {archivo.name}")
        return archivo

    print(f"    No se detectó descarga automática.")
    print(f"    Si ya descargó, presioná Enter...")
    input()
    files = sorted(DOWNLOADS.glob('*.xlsx'), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None

    print(f"    No se detectó descarga. Verificá manualmente.")
    return None


def main():
    print("=" * 60)
    print("  DESCARGADOR AUTOMÁTICO POWER BI")
    print("=" * 60)
    print()

    # Verificar URLs configuradas
    sin_url = [r['nombre'] for r in REPORTES if not r['url']]
    if sin_url:
        print(f"AVISO: los siguientes reportes no tienen URL configurada:")
        for n in sin_url:
            print(f"  - {n}")
        print("Editá C:\\Users\\USUARIO\\AppData\\Local\\Temp\\pbi_config.py para completarlos")
        print()

    with sync_playwright() as pw:
        # Abrir browser con carpeta de descarga en Downloads
        browser = pw.chromium.launch(
            headless=False,      # visible para poder ver si hay MFA
            downloads_path=str(DOWNLOADS),
            args=['--start-maximized']
        )
        context = browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # Login
        print("[1/5] Iniciando sesión en Power BI...")
        ok = login(page)
        if not ok:
            print("ERROR: no se pudo loguear")
            browser.close()
            input("\nPresioná Enter para salir...")
            sys.exit(1)

        # Descargar cada reporte
        descargados = []
        for i, reporte in enumerate(REPORTES, 2):
            print(f"[{i}/5] Descargando: {reporte['nombre']}...")
            archivo = exportar_reporte(page, reporte, DOWNLOADS)
            if archivo:
                descargados.append((reporte['nombre'], archivo))

        browser.close()

    # Resumen
    print()
    print("=" * 60)
    print(f"  DESCARGA COMPLETA — {len(descargados)}/{len(REPORTES)} reportes")
    for nombre, arch in descargados:
        print(f"  {nombre}: {arch.name}")
    print("=" * 60)
    print()

    if len(descargados) >= 3:
        print("Archivos listos. Podés correr el actualizador del dashboard ahora.")
    else:
        print("AVISO: algunos reportes no se descargaron. Verificá las URLs en pbi_config.py")

    input("\nPresioná Enter para cerrar...")


if __name__ == '__main__':
    main()
