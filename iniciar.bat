@echo off
title Baixador YouTube para MP3
cd /d "%~dp0"

echo Verificando Python...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERRO: Python nao foi encontrado no seu computador.
    echo Instale em https://www.python.org/downloads/ e marque a opcao
    echo "Add Python to PATH" durante a instalacao. Depois rode este
    echo arquivo de novo.
    echo.
    pause
    exit /b 1
)

echo Verificando/instalando yt-dlp...
python -m pip install --quiet --upgrade yt-dlp

echo.
python youtube_para_mp3.py %*

pause
