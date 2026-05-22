@echo off
cd /d "%~dp0"
call venv\Scripts\activate

:: Detectar IP local
set LOCAL_IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "169.254"') do (
    set LOCAL_IP=%%a
    goto :ip_found
)
:ip_found
set LOCAL_IP=%LOCAL_IP: =%

echo.
echo  =====================================================
echo   Foliar - Agente de formularios
echo  =====================================================
echo.
echo   Esta computadora:   http://localhost:5000
if not "%LOCAL_IP%"=="" (
echo   Red local:          http://%LOCAL_IP%:5000
)
echo.
echo   Ctrl+C para detener el servidor
echo  =====================================================
echo.

python app.py
pause
