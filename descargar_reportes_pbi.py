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


def exportar_reporte(page, reporte, download_dir):
    """Navega al reporte, hace click en Vista Amplia → Exportar y descarga el Excel."""
    nombre = reporte['nombre']
    url    = reporte['url']

    if not url:
        print(f"  SALTANDO {nombre} — URL no configurada aún")
        return None

    print(f"\n  [{nombre}] Abriendo reporte...")
    page.goto(url, wait_until='domcontentloaded', timeout=40000)
    time.sleep(5)  # esperar que cargue el visual

    # ── Paso 1: Click en "Vista amplia" (Focus mode / Expand) ─────────────────
    print(f"  [{nombre}] Buscando botón Vista amplia...")
    vista_amplia_encontrada = click_text(page,
        ['Vista amplia', 'Focus mode', 'Expand', 'Expandir', 'Ver en pantalla completa'],
        timeout=8000
    )

    if not vista_amplia_encontrada:
        # Intentar con íconos de expansión (botones sin texto)
        for sel in [
            '[aria-label*="Focus"]', '[aria-label*="Ampliar"]', '[aria-label*="focus"]',
            'button[aria-label*="Vista"]', '[data-testid*="focus"]',
            'button.focusModeButton', '[class*="focusMode"]',
        ]:
            try:
                el = page.wait_for_selector(sel, timeout=3000)
                if el and el.is_visible():
                    el.click()
                    vista_amplia_encontrada = True
                    print(f"    Vista amplia: {sel}")
                    break
            except PWTimeout:
                continue

    if not vista_amplia_encontrada:
        # Hover sobre el visual para que aparezcan los botones
        try:
            visual = page.wait_for_selector('[class*="visual-container"], [class*="visualContainer"]', timeout=5000)
            if visual:
                visual.hover()
                time.sleep(1)
                vista_amplia_encontrada = click_text(page,
                    ['Vista amplia', 'Focus mode', 'Expand'], timeout=3000)
        except PWTimeout:
            pass

    if vista_amplia_encontrada:
        print(f"    Vista amplia: OK")
        time.sleep(3)
    else:
        print(f"    AVISO: no se encontró Vista amplia — intentando exportar directamente")

    # ── Paso 2: Click en "Exportar" ───────────────────────────────────────────
    print(f"  [{nombre}] Buscando botón Exportar...")

    # Intentar con context menu (right-click sobre la tabla si hay)
    exportar_ok = False

    # Primero buscar botón directo
    exportar_ok = click_text(page,
        ['Exportar', 'Export', 'Exportar datos', 'Export data', 'Descargar', 'Download'],
        timeout=8000
    )

    if not exportar_ok:
        # Botón de más opciones (⋯) → Exportar
        for more_sel in [
            'button[aria-label*="opciones"]', 'button[aria-label*="options"]',
            'button[aria-label*="More"]', 'button[aria-label*="Más"]',
            '[class*="moreOptions"]', 'button[title*="opciones"]',
        ]:
            try:
                el = page.wait_for_selector(more_sel, timeout=3000)
                if el and el.is_visible():
                    el.click()
                    time.sleep(1)
                    exportar_ok = click_text(page,
                        ['Exportar', 'Export data', 'Exportar datos'], timeout=3000)
                    if exportar_ok:
                        break
            except PWTimeout:
                continue

    if not exportar_ok:
        print(f"    No se encontró Exportar automáticamente.")
        print(f"    Por favor hacé clic en 'Vista amplia' y luego 'Exportar' manualmente.")
        print(f"    Cuando el archivo esté descargado en Downloads, presioná Enter...")
        input()
        files = sorted(DOWNLOADS.glob('*.xlsx'), key=lambda f: f.stat().st_mtime, reverse=True)
        if files:
            print(f"    Usando: {files[0].name}")
            return files[0]
        return None

    # ── Paso 3: Confirmar formato y esperar descarga ───────────────────────────
    time.sleep(2)

    # A veces aparece un diálogo de formato → elegir .xlsx o confirmar
    for confirm_sel in [
        'button:has-text(".xlsx")', 'button:has-text("Excel")',
        'input[value*="xlsx"]', 'button:has-text("Exportar")',
        'button:has-text("Export")', 'button[type="submit"]',
    ]:
        try:
            el = page.wait_for_selector(confirm_sel, timeout=3000)
            if el and el.is_visible():
                with page.expect_download(timeout=90000) as dl_info:
                    el.click()
                download = dl_info.value
                archivo = download_dir / download.suggested_filename
                download.save_as(str(archivo))
                print(f"    Descargado: {archivo.name}")
                return archivo
        except PWTimeout:
            continue

    # Si no apareció diálogo, la descarga puede haber iniciado sola
    print(f"    Esperando descarga automática...")
    time.sleep(8)
    files = sorted(DOWNLOADS.glob('*.xlsx'), key=lambda f: f.stat().st_mtime, reverse=True)
    if files and (time.time() - files[0].stat().st_mtime) < 30:
        print(f"    Descargado: {files[0].name}")
        return files[0]

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
