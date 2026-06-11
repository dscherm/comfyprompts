@echo off
rem Stop the ComfyUI toolchain stack (ComfyUI server + web UI) by window title.
taskkill /FI "WINDOWTITLE eq ComfyUI" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq ComfyUI WebUI" /T /F >nul 2>&1
rem Fallback: kill by port owner if windows were renamed
powershell -NoProfile -Command "foreach ($p in 8188,5055) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"
echo Stack stopped.
