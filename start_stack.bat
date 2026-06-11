@echo off
rem Start the ComfyUI toolchain stack: ComfyUI server + web UI.
rem Each runs in its own window; close the windows (or run stop_stack.bat) to stop.

setlocal
set COMFY_DIR=D:\Projects\ComfyUI
set TOOLCHAIN_DIR=D:\Projects\comfyui-toolchain
set WEBUI_PORT=5055

rem --- ComfyUI (skip if already running) ---
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://localhost:8188/system_stats -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
    echo ComfyUI already running on :8188
) else (
    echo Starting ComfyUI...
    start "ComfyUI" /D "%COMFY_DIR%" "%COMFY_DIR%\venv\Scripts\python.exe" main.py --port 8188
)

rem --- wait for ComfyUI to come up (max ~3 min: custom node packs are slow) ---
echo Waiting for ComfyUI to be ready...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(180); while((Get-Date) -lt $d){ try { Invoke-WebRequest -Uri http://localhost:8188/system_stats -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep 3 } }; exit 1"
if not %errorlevel%==0 (
    echo WARNING: ComfyUI did not respond within 3 minutes. Web UI will start anyway.
)

rem --- Web UI (skip if already running) ---
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:%WEBUI_PORT%/api/status -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
    echo Web UI already running on :%WEBUI_PORT%
) else (
    echo Starting web UI...
    start "ComfyUI WebUI" /D "%TOOLCHAIN_DIR%" "%TOOLCHAIN_DIR%\.venv\Scripts\comfyui-webui.exe" --port %WEBUI_PORT%
)

rem --- open the browser ---
timeout /t 2 /nobreak >nul
start http://127.0.0.1:%WEBUI_PORT%
echo Stack is up: ComfyUI :8188, WebUI :%WEBUI_PORT%
endlocal
