# Fatia 1: executar, preparo, configuração e Quest (feita)

Feita em 10/10/2026, commit `56172c6`. Este documento descreve o que existe, como funciona, o que foi verificado e o que ficou pendente.

## O que o usuário ganhou

1. Abre o programa com dois cliques em `start.bat`, sem instalar Python nem nada antes.
2. Na primeira abertura a página mostra uma tela de preparo em três passos (idioma, dependências, Quest) e baixa o que falta com barra de progresso.
3. Um botão "Configuração" reabre o mesmo painel com tudo junto, mais os padrões de geração e o cache.
4. O envio ao Quest funciona só com o repositório: parear pelo cabo, ver se está conectado, ver quais mapas já estão lá, apagar.

## Arquivos

| Arquivo | Papel |
|---|---|
| `start.bat` | Baixa o uv, cria `.venv` com Python 3.12, instala os pacotes, abre `app.py` |
| `beatloom/__init__.py` | `BIN` e `caminhos()`: põe `bin\ffmpeg`, `bin\node`, `bin\platform-tools` no fim do `PATH` |
| `beatloom/preparo.py` | Estado de cada dependência e os downloads |
| `beatloom/quest.py` | Conversa com o Quest por ADB |
| `app.py` | Rotas novas, `config()`, `gravar_config()`, `enviados()`, `estado_quest()` |
| `site/app.html` | Painel `<dialog id="painel">`, indicador do Quest, frases novas nos dois idiomas |
| `requirements.txt` | Ganhou `yt-dlp` |
| `.gitignore` | Ganhou `bin/` e `beatloom.json` |
| `.gitattributes` | `*.bat` sempre com CRLF, senão o zip do GitHub quebra o `start.bat` |

## `start.bat`

Passos, com mensagem em português e inglês sem acento (acento em `.bat` depende da página de código):

1. Se não há `uv` no `PATH` nem em `bin\uv\uv.exe`: baixa o zip do uv com `curl --progress-bar` (vem no Windows 10 e 11) e extrai com `tar`.
2. Se não há `.venv\Scripts\python.exe`: `uv venv --python 3.12 .venv`. O uv baixa o Python sozinho se a máquina não tiver.
3. `uv pip install --torch-backend auto -r requirements.txt`. O `auto` escolhe o torch com CUDA quando há placa NVIDIA e o de CPU nos outros casos. Com tudo instalado esse passo leva cerca de um segundo.
4. `uv pip install -q -U yt-dlp`, ignorando falha: o YouTube muda sempre e yt-dlp velho para de funcionar.
5. `python app.py`. Se sair com erro, cai no rótulo `:erro`, que explica e faz `pause` para a janela não sumir.

`UV_CACHE_DIR` e `UV_PYTHON_INSTALL_DIR` apontam para dentro da pasta do projeto: nada vai para o disco C, que em algumas máquinas (a do dono inclusive) não tem espaço.

## `beatloom/preparo.py`

- `ITENS = ("ffmpeg", "node", "padroes", "visor", "adb")`. Obrigatórios: os três primeiros. Sem `visor` some o visualizador 3D; sem `adb` some o Quest.
- `tem(item)`: ffmpeg = `ffmpeg` e `ffprobe` no `PATH`; node = `node` no `PATH` e `check/node_modules/bsmap` existe; adb = `adb` no `PATH`; visor = `arcviewer/index.html`; padroes = os cinco `dados/padroes_<dif>.pkl`.
- `ZIPS`: endereço e pasta de destino de cada zip. Todos são extraídos sem a pasta de cima; `so=` guarda só os arquivos citados (do ffmpeg só `ffmpeg.exe` e `ffprobe.exe`).
- `baixar(item)`: baixa em blocos para `.cache/baixar/<item>.zip` atualizando `andamento[item] = {"feito", "total"}`, extrai, apaga o zip, chama `caminhos()`.
- `instalar_node()`: baixa o Node se faltar e roda `npm ci` em `check/`.
- `baixar_padroes()`: roda `tools/download_maps.py 1000` como subprocesso, lê a contagem na saída ("pagina X | N mapas") para o andamento, depois roda `tools/extract_patterns.py`. Interrompido, continua de onde parou (o script guarda `dados/estado.json`).
- `instalar(item)`: dispara uma thread; erro fica em `andamento[item]["erro"]`.
- `estado()`: `{item: {"ok", "obrigatorio", "rodando", "feito"?, "total"?, "erro"?}}`.
- `extrair()` recusa caminho que saia da pasta de destino. Coberto por `python -m beatloom.preparo --demo`.

Os endereços são de Windows. Quem já tem o programa no sistema continua usando o seu, porque `bin\` entra no fim do `PATH`.

## `beatloom/quest.py`

- `DEST` = `/sdcard/ModData/com.beatgames.beatsaber/Mods/SongCore/CustomLevels` (Beat Saber 1.40.8 com SongCore).
- Cada mapa vira a pasta `beatloom-<nome do zip sem .zip>`. Reenviar substitui.
- `conectado(ip)`: `adb connect ip:5555` e procura `ip:5555\tdevice` em `adb devices`. Tempo limite de 6 s.
- `parear()`: procura aparelho no cabo, lê o IP de `wlan0`, roda `adb tcpip 5555`. Devolve `(ip, None)` ou `(None, codigo)` com `sem_adb`, `sem_cabo`, `sem_permissao` (falta aceitar o aviso no headset) ou `sem_wifi`.
- `no_quest(ip)`: nomes das pastas `beatloom-*` em `DEST`.
- `enviar(ip, zip)`: extrai o zip, sobe para `DEST/.part`, depois `rm -rf` no alvo e `mv`. Envio cortado no meio não deixa mapa pela metade.
- `apagar(ip, nome)`.

`app.py` guarda em `saida/quest.json` a data de modificação do zip no momento do envio. `estado_quest()` devolve por zip `"ok"` (a versão de agora está no Quest) ou `"velho"` (o zip mudou depois do envio, por exemplo ao trocar o nome ou regerar uma dificuldade).

## `beatloom.json`

```json
{"lingua": "pt", "quest_ip": "192.168.1.50", "difs": ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"], "densidade": 1.0, "pronto": true}
```

`lingua` nula = a página usa o idioma do navegador. `pronto` = a pessoa concluiu a primeira vez. `gravar_config()` aceita atualização parcial e ignora valor inválido (IP fora do formato, idioma desconhecido, densidade fora de 0,8 a 1,3).

## Rotas

Todas só respondem a `localhost:8777`; os `POST` exigem o cabeçalho `X-Automapper: 1`. Erros vêm como `{"erro": "codigo"}` ou `{"erro": "codigo|detalhe"}`, e a página traduz o código.

Novas nesta fatia:

| Rota | Entrada | Saída |
|---|---|---|
| `GET /api/preparo` | | `preparo.estado()` |
| `POST /api/preparo` | `{"item": "ffmpeg"}` ou `{"item": "tudo"}` | estado; o download segue em segundo plano |
| `GET /api/config` | | config + `cache` (bytes das análises) + `torch` (versão instalada) |
| `POST /api/config` | qualquer subconjunto das chaves | config gravada |
| `POST /api/cache` | `{}` | apaga `.cache/analise`, `regerar`, `quest`, `tmp_egg`, `baixar`. `409 ocupado` se há geração rodando. Os modelos em `.cache/torch` e `.cache/hf` ficam |
| `GET /api/quest` | | `{"adb", "ip", "conectado", "mapas": {zip: "ok" ou "velho"}}` |
| `POST /api/quest/parear` | `{}` | estado do Quest, ou erro de `parear()` |
| `POST /api/quest` | `{"zip": nome}` ou `{"zips": [nomes]}` | `{"resultados": {zip: null ou erro}}`; `400 sem_quest` se não conecta |
| `POST /api/quest/apagar` | `{"zip": nome}` | `{"ok": true}` |

Já existiam: `GET /`, `/api/estado`, `/api/mapa?zip=`, `/api/capa?zip=` ou `?arquivo=`, `/api/zip?zip=`, `/zip/<nome>` (para o ArcViewer), `/arcviewer/...`; `POST /api/arquivo?nome=`, `/api/gerar`, `/api/previa`, `/api/apagar`, `/api/regerar`, `/api/renomear`.

Outras mudanças em `app.py`: o yt-dlp é chamado como `python -m yt_dlp` (pacote do `.venv`); `/api/estado` não tem mais a chave `quest`; se a porta já está ocupada o programa só abre o navegador e sai (`allow_reuse_address = False`, porque no Windows o padrão deixava dois servidores na mesma porta).

## A página

O painel é um `<dialog id="painel">` com cinco `<section>`. As três primeiras têm `data-p="1|2|3"`.

- Primeira vez: `abrirPainel(1)`. O atributo `data-passo` no diálogo esconde as outras seções; "Continuar" avança, e no passo 2 fica desabilitado enquanto faltar obrigatório. `Esc` não fecha. "Concluir" grava `pronto: true`.
- Configuração: `abrirPainel(0)` mostra as cinco seções de uma vez.
- Ao carregar: se `pronto` é falso abre no passo 1; se é verdadeiro mas falta obrigatório, abre direto no passo 2.
- `verPreparo()` redesenha a lista de itens a cada 1 s enquanto há download e a cada 5 s parado. `verQuest()` roda a cada 15 s e alimenta o indicador do topo, a marca na lista e os botões do detalhe.
- O idioma agora mora no `beatloom.json`, não mais no `localStorage`.

## Verificado

- `start.bat` do zero numa pasta temporária, sem uv no `PATH`: baixou o uv, criou o ambiente, instalou e abriu o app.
- `uv pip install --torch-backend auto` na máquina com AMD: manteve o torch de CPU.
- Todas as rotas novas, incluindo valores inválidos de config e `POST` sem o cabeçalho (403).
- O painel nos três passos e no modo configuração, com estados simulados de download em andamento, tamanho desconhecido e erro. Sem erros no console.
- Erros do Quest: `sem_quest`, `sem_cabo`.
- Geração de um mapa pelo `generate.py` e prévia de link do YouTube depois das mudanças.
- `--demo` de `preparo`, `generate`, `checks` e `extract_patterns`.

## Não verificado

- **Envio, listagem e exclusão no Quest de verdade.** O headset não respondeu no dia. É a primeira coisa a testar com ele ligado.
- **Pareamento pelo cabo** com um Quest de verdade.
- **Os downloads reais** de ffmpeg, Node, ADB e ArcViewer: a máquina de teste já tinha todos. Foi conferido que os endereços respondem e a extração foi testada com um zip de teste.
- **O download dos padrões pela página** (os scripts chamados são os mesmos de antes; a leitura do andamento não rodou de verdade).
- **O uv baixando o Python**: a máquina de teste já tinha Python 3.12.
- **Máquina com NVIDIA**: a escolha do torch com CUDA.

## Pendências desta fatia

1. Caixa de seleção para enviar vários mapas: o servidor aceita `zips`, a página não tem a seleção. Entra na fatia 2 junto com a lista nova.
2. Mapas enviados pelo script antigo (pasta com data no nome) não aparecem como "no Quest".
3. Ainda não existe release no GitHub; o README manda baixar a última. Basta criar uma tag: o zip automático já inclui o `start.bat`.
4. A lista de itens do preparo é redesenhada inteira a cada atualização, o que tira o foco do teclado de um botão durante um download. Resolver na fatia 2.
5. Em `/api/config`, `importlib.metadata.version("torch")` estoura se o torch não estiver instalado. Tratar na fatia 2 (devolver vazio).
