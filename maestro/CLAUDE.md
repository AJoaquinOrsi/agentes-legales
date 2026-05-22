# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descripción del proyecto

Sistema de automatización para **Estudio Jurídico Arrechea** (ART — Accidentes de Trabajo). El bot extrae notificaciones judiciales del portal SCBA, las clasifica con la API de Claude Haiku, las guarda en Google Sheets y opcionalmente las registra en Lex Doctor 11 (software de gestión jurídica).

**Repositorio:** `C:\Users\M01\Desktop\` — todos los scripts viven directamente en el escritorio.

---

## Arquitectura del sistema

### Flujo principal (diario)

```
SCBA Portal (Selenium)
  └─→ claude_query.py (Claude Haiku API)
        └─→ sheets_writer2.py (Google Sheets)
              └─→ [Opcional] lexdoctor_login.ps1 / lex_buscar.ps1 (Lex Doctor UI)
```

### Scripts principales

| Script | Propósito |
|---|---|
| `SCBA_extractor_diario.ps1` | **Script principal.** Extrae notificaciones de ayer, clasifica con Claude, guarda en Sheets. Ejecutar manualmente o programar. |
| `procuracion_completo.ps1` | Igual que el diario pero con fecha fija (para pruebas/reprocesos). Cambiar `$fechaDesde` / `$fechaHasta` manualmente. |
| `claude_query.py` | Lee `texto_notif.txt` → llama a Claude Haiku → imprime `observacion|||etapa|||responsable`. |
| `sheets_writer2.py` | Lee `datos_temp.json` → autentica con JWT de service account → append a Google Sheets (5 columnas: Carátula, Fecha, Observacion, Etapa, Responsable). |
| `lexdoctor_login.ps1` | Abre Lex Doctor, hace login (alexis/43719731) y busca expediente por carátula completa con OCR. |
| `lex_buscar.ps1` | Solo búsqueda (asume Lex Doctor ya abierto y logueado). Param: `-termino "GOMEZ KAREN"`. |
| `monitor_consultas.py` | Loop que lee `consulta_pendiente.json` y ejecuta búsqueda en Lex Doctor con pyautogui + OCR. Se comunica con `servidor_lex.py`. |
| `servidor_lex.py` | Flask HTTP en `:5000`. Endpoint POST `/consultar` recibe `{"caratula":"..."}` y devuelve movimientos vía `monitor_consultas.py`. |

### Archivos temporales de comunicación

```
texto_notif.txt       ← PS escribe texto de notificación → claude_query.py lo lee
datos_temp.json       ← PS escribe array de notificaciones → sheets_writer2.py lo lee
consulta_pendiente.json  ← servidor_lex.py escribe → monitor_consultas.py lee
resultado_consulta.json  ← monitor_consultas.py escribe → servidor_lex.py devuelve
```

---

## Stack y dependencias

### PowerShell (scripts .ps1)
- Selenium WebDriver .NET via `C:\Users\M01\Desktop\selenium4\lib\netstandard2.0\WebDriver.dll`
- Newtonsoft.Json via `C:\Users\M01\Desktop\selenium4\lib\netstandard2.0\Newtonsoft.Json.dll`
- chromedriver.exe en `C:\Users\M01\Desktop\`
- Win32 API inline (C# embebido) para mouse clicks y window focus: `user32.dll` — `SetCursorPos`, `mouse_event`, `SetForegroundWindow`, `ShowWindow`

### Python (scripts .py)
```
firebirdsql     # conexión directa a Firebird (pendiente activar)
requests        # Supabase API
flask           # servidor_lex.py
pytesseract     # OCR de pantalla Lex Doctor
pyautogui       # control de teclado/mouse en monitor_consultas.py
pywinauto       # obtener título de ventana de Lex Doctor
Pillow (PIL)    # capturas de pantalla
cryptography    # JWT para Google Sheets (RS256)
```

Tesseract OCR instalado en `C:\Program Files\Tesseract-OCR\tesseract.exe`, idioma `spa`.

### Credenciales y archivos de config
| Archivo | Contenido |
|---|---|
| `C:\Users\M01\Desktop\credenciales.json` | Service account Google (JWT RS256 para Sheets) |
| `C:\LEX\CLIENTE\LEX.INI` | Conexión Lex Doctor: `host=192.168.10.94`, `port=211` |
| API key Anthropic | Hardcodeada en `claude_query.py` (línea 97) |

---

## Comandos para ejecutar

```powershell
# Extracción diaria (notificaciones de ayer)
powershell -ExecutionPolicy Bypass -File "C:\Users\M01\Desktop\SCBA_extractor_diario.ps1"

# Extracción con fecha fija (modificar fechas dentro del script primero)
powershell -ExecutionPolicy Bypass -File "C:\Users\M01\Desktop\procuracion_completo.ps1"

# Buscar expediente en Lex Doctor (Lex ya abierto y logueado)
powershell -ExecutionPolicy Bypass -File "C:\Users\M01\Desktop\lex_buscar.ps1" -termino "GOMEZ KAREN"

# Buscar + login completo desde cero
powershell -ExecutionPolicy Bypass -File "C:\Users\M01\Desktop\lexdoctor_login.ps1" -caratulaCompleta "GOMEZ KAREN MAGALI"

# Servidor Flask + monitor (ejecutar en dos consolas separadas)
py C:\Users\M01\Desktop\servidor_lex.py
py C:\Users\M01\Desktop\monitor_consultas.py

# Probar conexión Firebird directa (requiere abrir puerto 3050 en servidor)
py C:\Users\M01\Desktop\lexdoctor_firebird_directo.py
```

---

## Base de datos Lex Doctor (Firebird)

- **Servidor:** `192.168.10.94:211` (protocolo Lex Doctor, NO Firebird directo)
- **Firebird escucha en:** `192.168.10.94:3050` pero bloqueado por firewall del servidor
- **Archivo de base:** `C:\LEX11E\DATOS\lex11e.fdb` (confirmado vía WinRM)
- **Credenciales Firebird:** `SYSDBA` / `masterkey`
- **Acceso remoto al servidor:** WinRM (`192.168.10.94:5985`) con credenciales Windows del servidor

### Tablas clave (del data dictionary `DD_Lex-Doctor 11.xlsx`)
| Tabla | Descripción |
|---|---|
| `PROC` | Expedientes/procesos. Campos: `PROC` (PK), `ACTO` (actor varchar 200), `DEMA` (demandado varchar 200), `CARP` (carpeta), `EXP1/EXP2/EXP3` (nros expediente), `MIEM` (FK responsable) |
| `MOVI` | Movimientos y agenda por proceso |
| `MIEM` | Miembros del estudio (abogados) |
| `SUJE` | Personas/clientes: `APEL`, `NOMB`, `DOCU`, `ITR2` (CUIT) |
| `OJUD` | Oficinas judiciales (juzgados) |

Búsqueda recomendada cuando el puerto 3050 esté accesible:
```sql
SELECT PROC, ACTO, DEMA, CARP, EXP1
FROM PROC
WHERE UPPER(ACTO) LIKE UPPER('%GOMEZ KAREN%')
   OR UPPER(DEMA) LIKE UPPER('%GOMEZ KAREN%')
```

---

## Clasificación de notificaciones (claude_query.py)

Claude Haiku clasifica cada notificación en **9 etapas procesales** y asigna un responsable:

| Etapa | Responsable |
|---|---|
| INICIO TRASLADO | RENATTA |
| PRUEBA PENDIENTE DE APERTURA | MEL |
| TRABA DE LITIS - PENDIENTE DE AUDIENCIA PRELIMINAR | MEL |
| ETAPA PROBATORIA - ESTADO 1 | MEL |
| ETAPA PROBATORIA - ESTADO 2 (traslado/impugnación pericia) | EDBER |
| ETAPA PROBATORIA - ESTADO 2 (otros vencimientos) | MEL |
| ESPERA DE SENTENCIA | LEANDRO |
| SENTENCIA DE 1° | LEANDRO |
| APELADO EN CAMARA | LEANDRO |
| EN CORTE | LEANDRO |

Salida del script: `observacion|||etapa|||responsable` (pipe-delimitado, parseado por PowerShell).
Máximo 20 palabras en la observación. Nunca escribir "requiere descarga" ni frases de incertidumbre.

---

## Google Sheets

- **Spreadsheet ID:** `1u1PH27lsrcD5zZ7LgbEqH8EMhBF2MnXvkh8rny_Ivto`
- **Hoja:** `Hoja 1`, rango append: `A2:E2`
- **Columnas:** A=Carátula, B=Fecha, C=Observacion, D=Etapa, E=Responsable
- Auth: JWT RS256 con service account de `credenciales.json` (sin librerías de Google, solo `urllib` + `cryptography`)

---

## Automatización Lex Doctor (UI)

Lex Doctor 11 es una aplicación Win32/Delphi. La automatización usa coordenadas absolutas de pantalla en resolución 1920×1080:

| Elemento | Coordenadas |
|---|---|
| Carpeta Procesos | `(19, 105)` |
| Grilla de resultados (fila 1) | `(820, 241)`, incremento 20px por fila |
| Botón Movimientos | `(334, 331)` |
| Campo usuario login | `(1048, 679)` |
| Campo contraseña login | `(1044, 709)` |

**Popup "Búsquedas":** al escribir en el campo de búsqueda aparece un popup que pide elegir tipo. Enviar `"2"` + `{ENTER}` para seleccionar "Busca libre".

**Similitud carátula:** umbral mínimo 75% (coincidencia de palabras) para abrir un expediente.

**Toggle Lex Doctor:** `$usarLex = $false` en `SCBA_extractor_diario.ps1` — cambiar a `$true` para activar la sección de carga en Lex.

---

## Encoding

- **PowerShell:** siempre incluir al inicio: `$env:PYTHONUTF8 = "1"` y `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
- **Python:** `sys.stdout.reconfigure(encoding='utf-8')` al inicio de cualquier script llamado desde PowerShell
- **Strings en .ps1:** usar SOLO comillas ASCII rectas (`"` y `'`). Nunca comillas tipográficas (`"` `"` `'` `'`) ni caracteres Unicode en strings (`→` etc.) — causan `TerminatorExpectedAtEndOfString`.

---

## SCBA Portal

- **URL login:** `https://notificaciones.scba.gov.ar/InterfazBootstrap/Login.aspx`
- **Credenciales:** `20326081885@notificaciones.scba.gov.ar` / `43719731`
- Login vía JS: `driver.ExecuteScript("ingresar();")`
- Paginación vía JS: `driver.ExecuteScript("buscar($pag); return false;")`
- Total de páginas: `driver.FindElement(By.Id("cantPag")).GetAttribute("value")`
- Links de detalle: `driver.FindElements(By.CssSelector("a.Detalle"))`
- Iframes: hacer `SwitchTo().Frame()` y `SwitchTo().DefaultContent()` para leer documentos embebidos
