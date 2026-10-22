@echo off
chcp 65001 >nul
if "%~1"=="" (
    python "%~dp0img2pdf.py" --help
    pause
    exit /b
)
python "%~dp0img2pdf.py" %*
pause
