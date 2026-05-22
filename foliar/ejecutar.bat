@echo off
echo =========================================
echo  Agente Rellenador - Anexo I Incapacidad
echo =========================================
echo.

if "%~1"=="" (
    echo USO: Arrastrar el documento PDF fuente sobre este archivo
    echo   o ejecutar: ejecutar.bat documento_fuente.pdf
    echo.
    set /p PDF_FUENTE="Ingresa la ruta del PDF fuente: "
) else (
    set PDF_FUENTE=%~1
)

if "%ANTHROPIC_API_KEY%"=="" (
    echo.
    echo ATENCION: No se encontro la variable ANTHROPIC_API_KEY
    set /p ANTHROPIC_API_KEY="Ingresa tu API Key de Anthropic: "
)

echo.
echo Procesando: %PDF_FUENTE%
echo.

python "%~dp0form_filler_agent.py" "%PDF_FUENTE%"

echo.
if %ERRORLEVEL%==0 (
    echo LISTO! Formulario generado en el Escritorio: anexo_i_rellenado.pdf
) else (
    echo ERROR: Revisa el mensaje de error arriba
)

pause
