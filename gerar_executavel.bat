@echo off
title Gerando o executavel...
cd /d "%~dp0"

echo ============================================
echo   Gerando "Baixador de MP3.exe"
echo   Isso so precisa ser feito uma vez.
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado neste computador.
    echo Instale em https://www.python.org/downloads/ marcando a opcao
    echo "Add Python to PATH" e rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

echo Instalando as ferramentas necessarias para gerar o executavel...
echo (pode levar alguns minutos na primeira vez)
python -m pip install --quiet --upgrade pyinstaller "yt-dlp[default]" pillow customtkinter
if errorlevel 1 (
    echo.
    echo ERRO ao instalar as dependencias. Verifique sua internet e tente de novo.
    pause
    exit /b 1
)

echo.
echo Compilando o programa em um unico arquivo .exe...
rem --collect-all garante que os arquivos de dados do yt-dlp (incluindo o
rem pacote yt-dlp-ejs, que resolve o desafio de JavaScript do YouTube) vao
rem junto no .exe. Sem isso, o programa pode achar que o Deno nao tem o
rem que executar e cair em erro 403 mesmo com tudo instalado.
python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --name "Baixador de MP3" ^
    --icon "icone.ico" ^
    --collect-all yt_dlp ^
    --collect-all yt_dlp_ejs ^
    youtube_para_mp3_gui.py

if not exist "dist\Baixador de MP3.exe" (
    echo.
    echo ERRO: a geracao do executavel falhou. Veja as mensagens acima.
    pause
    exit /b 1
)

echo.
echo Copiando o executavel para esta pasta...
copy /y "dist\Baixador de MP3.exe" "Baixador de MP3.exe" >nul

echo Limpando arquivos temporarios da compilacao...
rmdir /s /q build >nul 2>nul
rmdir /s /q dist >nul 2>nul
del /q "Baixador de MP3.spec" >nul 2>nul

echo.
echo ============================================
echo   Pronto! O arquivo "Baixador de MP3.exe"
echo   foi criado nesta pasta. Basta dar dois
echo   cliques nele para abrir o programa - pode
echo   copiar/enviar esse arquivo para qualquer
echo   outro computador com Windows.
echo ============================================
echo.
pause
