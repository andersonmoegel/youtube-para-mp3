# 🎵 YouTube para MP3

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=flat&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

Aplicativo de desktop com interface gráfica que baixa o áudio de um vídeo do YouTube e converte automaticamente para MP3, usando yt-dlp e FFmpeg. Distribuído como um único executável (.exe) — a pessoa que for usar não precisa instalar Python nem nada além do programa em si.

Criado como projeto de estudo/portfólio para praticar automação, manipulação de mídia, interfaces gráficas e empacotamento de aplicações.

## Funcionalidades

- Interface gráfica moderna, com tema escuro/neon (CustomTkinter)
- Pré-visualização automática: basta colar o link e a miniatura, o título e o canal aparecem sozinhos (via API pública oEmbed do YouTube)
- Barra de progresso em tempo real durante o download
- Escolha da pasta onde os MP3s são salvos (padrão: `Downloads/mp3_youtube`)
- Histórico de downloads e avisos direto na tela
- Ao concluir, mostra uma confirmação e limpa os campos automaticamente para o próximo link
- Prepara sozinho, em segundo plano, os componentes externos necessários (FFmpeg para converter o áudio, Deno para contornar as proteções do YouTube) — sem precisar de configuração manual
- Tela de carregamento própria enquanto o programa se prepara
- Distribuído como um único `.exe`: não abre janela de console, não precisa de Python instalado para usar

## Como funciona

1. A pessoa cola o link do vídeo do YouTube.
2. O app busca automaticamente miniatura, título e canal via oEmbed.
3. Ao clicar em "Baixar MP3", o yt-dlp extrai o melhor áudio disponível, resolvendo os desafios de JavaScript exigidos atualmente pelo YouTube com o runtime Deno.
4. O FFmpeg converte esse áudio para `.mp3` (192 kbps).
5. O arquivo final é salvo na pasta escolhida.

## Requisitos para usar

- Windows 10/11
- Nada além disso — o próprio programa instala FFmpeg e Deno na primeira abertura, se ainda não estiverem no computador.

## Requisitos para gerar o executável (desenvolvimento)

- Python 3.10+
- Dependências de build: `yt-dlp[default]`, `pillow`, `customtkinter`, `pyinstaller`

## Como usar

Basta dar duplo clique em `Baixador de MP3.exe`. Não precisa instalar nada.

### Gerando o executável a partir do código-fonte

1. Tenha o Python instalado.
2. Dê duplo clique em `gerar_executavel.bat`.
3. Aguarde a compilação (ele instala o PyInstaller e as demais dependências e empacota tudo em um único arquivo).
4. O arquivo `Baixador de MP3.exe` aparece na mesma pasta — pode copiar ou enviar esse único arquivo para qualquer outro computador com Windows.

## Estrutura do projeto

```
youtube-para-mp3/
├── youtube_para_mp3_gui.py   # codigo-fonte do aplicativo (interface grafica)
├── gerar_executavel.bat      # gera o .exe standalone (PyInstaller)
├── icone.ico                 # icone do aplicativo
├── Baixador de MP3.exe       # gerado apos rodar gerar_executavel.bat
└── README.md
```

## Tecnologias e habilidades demonstradas

- Python (threading, filas para comunicação entre thread de download e a interface, subprocess)
- Interface gráfica com CustomTkinter/Tkinter (tema customizado, layout responsivo, janela maximizada)
- Consumo de API pública (oEmbed do YouTube) para pré-visualização de conteúdo
- Integração com yt-dlp e FFmpeg para download e conversão de mídia
- Automação de setup: detecção e instalação silenciosa de dependências externas (winget, scripts de instalação), com atualização do PATH em tempo de execução e fallback quando a instalação automática falha
- Empacotamento de aplicação Python como executável standalone com PyInstaller, incluindo coleta manual de dados de pacotes (`--collect-all`) para dependências que carregam arquivos além de código
- Tratamento de erros amigável, pensado para usuários não técnicos

## Possíveis melhorias futuras

- Suporte a playlists inteiras
- Seleção de qualidade/formato de áudio pelo usuário
- Fila com múltiplos downloads simultâneos
- Instalador (.msi) com atalho automático no menu iniciar

## Aviso legal

Este projeto tem fins educacionais e de portfólio. Baixe apenas conteúdo que você tem o direito de baixar (vídeos próprios, domínio público, licença Creative Commons, etc.). O uso para baixar conteúdo protegido por direitos autorais sem autorização pode violar os Termos de Serviço do YouTube e leis de direitos autorais aplicáveis. O autor não se responsabiliza pelo uso indevido desta ferramenta.

## Licença

Distribuído sob a licença MIT. Veja LICENSE para mais detalhes.
