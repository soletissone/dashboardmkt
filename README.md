# Dashboard Semanal UTEL

Herramienta de análisis semanal de canales, programas y matrículas para el equipo de marketing/comercial de UTEL.

## Archivos

| Archivo | Descripción |
|---|---|
| `actualizar_dashboard.py` | **Script principal** — doble clic para actualizar el dashboard |
| `extract_data.py` | Procesa los Excel y genera `dashboard_data.json` |
| `build_dashboard.py` | Genera el HTML final `analisis_semanal.html` |

## Uso semanal

1. Descargar en `Downloads` los archivos actualizados:
   - `data - FECHA.xlsx` (leads + programas)
   - `data - FECHA.xlsx` (matrículas — segundo más reciente)
   - `CUADRO EVOLUTIVO*.xlsx` (contactación)
   - `TABLA_PRECIOS*.xlsx` (precios, solo si cambia)
2. Doble clic en el acceso directo **"Actualizar Dashboard"** del escritorio
3. El dashboard se abre automáticamente en el navegador

## Requisitos

```
pip install pandas openpyxl
```

## Salida

- `Downloads/analisis_semanal.html` — dashboard interactivo (se abre en cualquier navegador)
- `Downloads/dashboard_data.json` — datos procesados
