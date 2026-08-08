#!/usr/bin/env python3
"""
Baixador de video do YouTube -> MP3

Requisitos:
    pip install yt-dlp
    ffmpeg instalado no sistema (https://ffmpeg.org/download.html)

Uso:
    python youtube_para_mp3.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
    python youtube_para_mp3.py "URL1" "URL2" ...
    python youtube_para_mp3.py            (pede o link interativamente)

Aviso: baixe apenas conteudo que voce tem direito de baixar (seu proprio
video, dominio publico, licenca Creative Commons, etc.). Respeite os
Termos de Servico do YouTube e leis de direitos autorais.
"""

import os
import sys

try:
    import yt_dlp
except ImportError:
    print("Falta a biblioteca 'yt-dlp'. Instale com: pip install yt-dlp")
    sys.exit(1)

PASTA_SAIDA = os.path.join(os.path.expanduser("~"), "Downloads", "mp3_youtube")


def baixar_mp3(url: str, pasta_saida: str = PASTA_SAIDA) -> None:
    os.makedirs(pasta_saida, exist_ok=True)

    opcoes = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(pasta_saida, "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "noplaylist": True,
        "quiet": False,
    }

    print(f"\nBaixando: {url}")
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        ydl.download([url])
    print("Concluido!\n")


def main():
    urls = sys.argv[1:]
    if not urls:
        entrada = input("Cole o link do video do YouTube: ").strip()
        if not entrada:
            print("Nenhum link informado.")
            sys.exit(1)
        urls = [entrada]

    for url in urls:
        try:
            baixar_mp3(url)
        except Exception as e:
            print(f"Erro ao baixar '{url}': {e}")

    print(f"Arquivos MP3 salvos em: {PASTA_SAIDA}")


if __name__ == "__main__":
    main()
    input("\nPressione ENTER para fechar...")
