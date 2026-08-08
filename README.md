# 🎵 YouTube para MP3

Ferramenta de linha de comando em Python que baixa o áudio de um vídeo do YouTube e converte automaticamente para MP3, usando [yt-dlp](https://github.com/yt-dlp/yt-dlp) e [FFmpeg](https://ffmpeg.org/).

Criado como projeto de estudo/portfólio para praticar automação, manipulação de mídia e distribuição de scripts multiplataforma.

## Funcionalidades

- Baixa o áudio de qualquer link do YouTube e converte para MP3 (192 kbps)
- Aceita um ou vários links de uma vez
- Modo interativo (pede o link) ou por argumento de linha de comando
- Extrai o título do vídeo automaticamente para nomear o arquivo
- Launcher `.bat` para Windows que verifica dependências e instala o que faltar
- Tratamento de erros por link, sem interromper o restante da fila

## Como funciona

1. O usuário informa a URL de um vídeo do YouTube.
2. O `yt-dlp` extrai o melhor stream de áudio disponível.
3. O `FFmpeg` converte esse stream para `.mp3`.
4. O arquivo final é salvo em `Downloads/mp3_youtube`.

## Requisitos

- [Python 3.8+](https://www.python.org/downloads/)
- [FFmpeg](https://ffmpeg.org/download.html) instalado e disponível no PATH
- Biblioteca [`yt-dlp`](https://pypi.org/project/yt-dlp/)

## Instalação

```bash
git clone https://github.com/seu-usuario/youtube-para-mp3.git
cd youtube-para-mp3
pip install -r requirements.txt
```

No Windows, se preferir não usar o terminal, basta dar duplo clique em `iniciar.bat` — ele confere se o Python está instalado, instala o `yt-dlp` automaticamente e roda o programa.

## Uso

Modo interativo:

```bash
python youtube_para_mp3.py
```

Passando o link direto:

```bash
python youtube_para_mp3.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
```

Vários links de uma vez:

```bash
python youtube_para_mp3.py "URL1" "URL2" "URL3"
```

Os arquivos `.mp3` são salvos em `~/Downloads/mp3_youtube`.

## Estrutura do projeto

```
youtube-para-mp3/
├── youtube_para_mp3.py   # script principal
├── iniciar.bat           # launcher para Windows
├── requirements.txt      # dependências Python
└── README.md
```

## Tecnologias e habilidades demonstradas

- Python (manipulação de processos, argumentos de CLI, tratamento de exceções)
- Integração com bibliotecas de terceiros (`yt-dlp`) e ferramentas externas (`FFmpeg`)
- Scripting de automação para Windows (`.bat`)
- Boas práticas de UX em CLI (modo interativo + modo por argumento, mensagens claras de erro)

## Possíveis melhorias futuras

- [ ] Interface gráfica (Tkinter ou PySide)
- [ ] Barra de progresso customizada
- [ ] Suporte a playlists inteiras
- [ ] Seleção de qualidade de áudio pelo usuário
- [ ] Empacotamento como executável (PyInstaller)

## Aviso legal

Este projeto tem fins educacionais e de portfólio. Baixe apenas conteúdo que você tem o direito de baixar (vídeos próprios, domínio público, licença Creative Commons, etc.). O uso para baixar conteúdo protegido por direitos autorais sem autorização pode violar os Termos de Serviço do YouTube e leis de direitos autorais aplicáveis. O autor não se responsabiliza pelo uso indevido desta ferramenta.

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para mais detalhes.
