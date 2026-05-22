@echo off
:: ── Foliar — Configuración de red local ──────────────────────────────────────
:: Ejecutar UNA SOLA VEZ como Administrador (clic derecho → Ejecutar como administrador)

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo  ERROR: Este archivo debe ejecutarse como Administrador.
    echo  Clic derecho sobre el archivo ^> "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

echo.
echo  =====================================================
echo   Foliar — Configuracion de red local
echo  =====================================================
echo.

:: Abrir puerto 5000 en el firewall de Windows
echo  [1/2] Abriendo puerto 5000 en el Firewall de Windows...
netsh advfirewall firewall delete rule name="Foliar Puerto 5000" >nul 2>&1
netsh advfirewall firewall add rule name="Foliar Puerto 5000" dir=in action=allow protocol=TCP localport=5000
if %errorLevel% == 0 (
    echo       OK - Puerto 5000 habilitado.
) else (
    echo       ADVERTENCIA: No se pudo configurar el firewall.
)

:: Detectar IP local automaticamente
echo.
echo  [2/2] Detectando IP de red local...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "169.254"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
set LOCAL_IP=%LOCAL_IP: =%

echo       IP detectada: %LOCAL_IP%

echo.
echo  =====================================================
echo   Configuracion completada.
echo.
echo   Compartir esta direccion con tus companeros:
echo.
echo      http://%LOCAL_IP%:5000
echo.
echo   (Deben estar conectados a la misma red WiFi/LAN)
echo  =====================================================
echo.
pause
