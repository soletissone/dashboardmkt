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


def exportar_reporte(page, reporte, download_dir):
    """Navega al reporte y descarga el Excel."""
    nombre = reporte['nombre']
    url    = reporte['url']

    if not url:
        print(f"  SALTANDO {nombre} — URL no configurada")
        return None

    print(f"\n  Abriendo: {nombre}")
    page.goto(url, wait_until='domcontentloaded', timeout=30000)
    time.sleep(4)

    # Intentar varios métodos de exportación
    archivo = None

    # Método 1: Botón "Export" o "Exportar" en la barra superior
    for selector in [
        'button[aria-label*="Export"]',
        'button[aria-label*="export"]',
        'button[aria-label*="Exportar"]',
        'button[title*="Export"]',
        'button[title*="Exportar"]',
        '[data-testid="export-button"]',
    ]:
        try:
            btn = page.wait_for_selector(selector, timeout=3000)
            if btn:
                print(f"    Encontrado botón export: {selector}")
                with page.expect_download(timeout=60000) as dl:
                    btn.click()
                    time.sleep(1)
                    # Si aparece un submenu, buscar "Excel"
                    for sub in ['button:has-text("Excel")', 'li:has-text("Excel")',
                                'button:has-text(".xlsx")', '[aria-label*="Excel"]']:
                        try:
                            sub_btn = page.wait_for_selector(sub, timeout=3000)
                            if sub_btn:
                                sub_btn.click()
                                break
                        except PWTimeout:
                            continue
                download = dl.value
                archivo = download_dir / download.suggested_filename
                download.save_as(str(archivo))
                print(f"    Descargado: {archivo.name}")
                return archivo
        except PWTimeout:
            continue

    # Método 2: Menú File → Download / Descargar
    for file_selector in [
        'button[aria-label*="File"]',
        'button[aria-label*="Archivo"]',
        '[data-testid="file-menu"]',
        'button:has-text("File")',
    ]:
        try:
            file_btn = page.wait_for_selector(file_selector, timeout=3000)
            if file_btn:
                file_btn.click()
                time.sleep(1)
                for dl_sel in ['button:has-text("Download")', 'button:has-text("Descargar")',
                               'li:has-text("Export")', 'li:has-text("Exportar")']:
                    try:
                        dl_btn = page.wait_for_selector(dl_sel, timeout=3000)
                        if dl_btn:
                            with page.expect_download(timeout=60000) as dl:
                                dl_btn.click()
                            download = dl.value
                            archivo = download_dir / download.suggested_filename
                            download.save_as(str(archivo))
                            print(f"    Descargado: {archivo.name}")
                            return archivo
                    except PWTimeout:
                        continue
        except PWTimeout:
            continue

    print(f"    AVISO: no se encontró botón de export automático para {nombre}")
    print(f"    Por favor exportá manualmente y presioná Enter cuando el archivo esté en Downloads...")
    input()
    # Buscar el archivo más reciente en Downloads
    files = sorted(DOWNLOADS.glob('*.xlsx'), key=lambda f: f.stat().st_mtime, reverse=True)
    if files:
        print(f"    Usando archivo más reciente: {files[0].name}")
        return files[0]
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
