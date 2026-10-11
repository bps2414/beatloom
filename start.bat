@echo off
rem Abre o Beatloom. Na primeira vez baixa o Python e os pacotes para dentro desta pasta; nada e instalado no Windows.
rem Opens Beatloom. The first time it downloads Python and the packages into this folder; nothing is installed on Windows.
setlocal
cd /d "%~dp0"
rem start.bat bandeja: o mesmo, com a janela minimizada e o Beatloom na bandeja do Windows (icone perto do relogio)
rem start.bat bandeja: the same, with the window minimized and Beatloom in the Windows tray (icon near the clock)
if /i "%~1"=="bandeja" start "Beatloom" /min "%~f0" _bandeja & exit /b 0
title Beatloom
set "UV_CACHE_DIR=%~dp0.cache\uv"
set "UV_PYTHON_INSTALL_DIR=%~dp0bin\python"
set "PY=.venv\Scripts\python.exe"

set "UV=uv"
where uv >nul 2>nul && goto python
set "UV=%~dp0bin\uv\uv.exe"
if exist "%UV%" goto python
echo.
echo [1/3] Baixando o instalador, 15 MB  /  Downloading the installer, 15 MB
if not exist "%~dp0bin\uv" mkdir "%~dp0bin\uv"
curl -L --fail --progress-bar -o "%~dp0bin\uv\uv.zip" https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip || goto erro
tar -xf "%~dp0bin\uv\uv.zip" -C "%~dp0bin\uv" || goto erro
del "%~dp0bin\uv\uv.zip"

:python
if exist "%PY%" goto pacotes
echo.
echo [2/3] Preparando o Python 3.12  /  Setting up Python 3.12
"%UV%" venv --python 3.12 .venv || goto erro

:pacotes
echo.
echo [3/3] Conferindo os pacotes. Na primeira vez sao uns 2 GB e pode levar varios minutos.
echo       Checking the packages. The first time it is about 2 GB and can take several minutes.
"%UV%" pip install --python "%PY%" --torch-backend auto -r requirements.txt || goto erro
rem o YouTube muda sempre: o yt-dlp precisa estar em dia (sem internet, segue com o que tem)
"%UV%" pip install --python "%PY%" -q -U yt-dlp 2>nul

if /i "%~1"=="_bandeja" (
    start "" powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0tools\bandeja.ps1"
    exit /b 0
)
echo.
echo Beatloom aberto no navegador. Deixe esta janela aberta; feche-a para encerrar.
echo Beatloom is open in your browser. Keep this window open; close it to quit.
"%PY%" app.py && exit /b 0

:erro
rem na bandeja a janela esta minimizada: abre uma janela normal para a pessoa ver o que deu errado
if /i "%~1"=="_bandeja" start "" "%~f0" & exit /b 1
echo.
echo Algo deu errado. Confira a internet e abra o start.bat de novo.
echo Something went wrong. Check your internet connection and open start.bat again.
echo Se continuar / if it keeps failing: https://github.com/bps2414/beatloom/issues
pause
exit /b 1
