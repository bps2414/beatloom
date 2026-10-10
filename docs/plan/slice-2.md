# Fatia 2: redesenho, i18n e relatório estruturado (a fazer)

Leia antes: [README.md](README.md) (decisões e ambiente na nuvem) e [slice-1.md](slice-1.md) (rotas e painel que já existem). Leia também `site/app.html` e `app.py` inteiros: são curtos e esta fatia mexe em quase tudo neles.

## Objetivo

Refazer a página para que fique bonita e óbvia para um leigo, com as frases em arquivos de idioma e o relatório escrito no idioma escolhido. Nenhuma função que existe hoje pode sumir.

## O que não muda

- Servidor em `http.server`, sem framework. Página em HTML, CSS e JS puros, sem build.
- A lógica de geração (`generate.py`, `beatloom/engine.py`, `beatloom/checks.py`): os mapas gerados têm de sair idênticos aos de antes. Exceções permitidas nesta fatia: o relatório ganhar uma versão em JSON e a separação de instrumentos imprimir o andamento.
- As proteções do servidor: só responde a `localhost`, `POST` exige `X-Automapper: 1`, nomes de arquivo passam por `Path(...).name`.
- O texto de `<zip>.relatorio.txt` continua igual, byte a byte. `tools/batch.py` e `tools/blind_test.py` dependem dele; confira os dois antes de mexer em `report.py`.

## Inventário: o que a página faz hoje

Confira cada item no fim. Tudo isto precisa existir na página nova.

1. Colar link (YouTube etc.) e ver a prévia: capa, nome, artista, álbum, ano; nome e artista editáveis antes de gerar.
2. Escolher arquivo de áudio (mp3, ogg, wav, m4a, flac, opus, egg; até 300 MB), com prévia da capa embutida ou aviso de capa genérica.
3. Escolher dificuldades e quantidade de notas (0,8 a 1,3), partindo do padrão da config.
4. Fila de gerações, uma por vez, com a etapa atual de cada uma e o erro quando falha.
5. Lista de mapas prontos, do mais novo ao mais velho, com nome, artista, BPM, resultado das conferências e marca "no Quest".
6. Abrir um mapa: visualizador 3D (ArcViewer num `iframe`), troca de dificuldade (recarrega o `iframe`), link para abrir em tela cheia.
7. Ficha do mapa: capa, nome, artista, álbum, ano, BPM, link da fonte.
8. Resumo das conferências (passou ou não) e relatório completo.
9. Trocar nome e artista. Apagar (vai para `saida\lixeira`). Baixar o zip.
10. Regerar uma dificuldade com outra quantidade de notas.
11. Quest: indicador de conexão, enviar, reenviar, atualizar versão antiga, apagar do Quest.
12. Tela de preparo em três passos e painel de configuração (idioma, itens, Quest, padrões de geração, cache, versão do torch).
13. Troca de idioma em qualquer momento, sem recarregar.
14. Aviso quando o visualizador 3D não está instalado.

Novo nesta fatia: seleção de vários mapas para enviar ao Quest, barra de progresso real na separação de instrumentos, arrastar e soltar arquivo, duração e notas por segundo na lista e no detalhe.

## Passo 0: mapas de mentira para desenvolver

Num clone novo não há mapas. Crie `tools/fixture.py`, que monta em `saida/` mapas com áudio sintético (nada protegido):

- Áudio: `ffmpeg -f lavfi -i "sine=frequency=220:duration=60" -c:a libvorbis -q:a 4 -ar 44100 -f ogg song.egg`.
- Capa: `ffmpeg -f lavfi -i "gradients=s=512x512:c0=0x1e3a8a:c1=0xdb2777" -frames:v 1 cover.png` (o mesmo de `generate.py`).
- `Info.dat` e arquivos de dificuldade no mesmo formato que `generate.py` escreve (veja `gerar()`: `Info.dat` v2 com `_customData._beatloom`, dificuldades v3 `3.2.0` com `colorNotes`). Notas simples alternando as mãos, uma por batida, a 120 BPM.
- Três mapas, para exercitar os estados: um com as cinco dificuldades e relatório aprovado; um com duas dificuldades e uma conferência reprovada; um com nome e artista bem longos e sem relatório.
- Grava também o `.relatorio.txt` e, depois do passo 3, o `.relatorio.json`.
- `--demo` confere que os zips abrem e têm os arquivos esperados.

Não versione o que ele gera (`saida/` já está no `.gitignore`). O ArcViewer também não existe no clone: a página precisa ficar correta sem ele (item 14), e para vê-lo funcionando rode `python -c "from beatloom import preparo; preparo.baixar('visor')"`, que no Linux também funciona porque é só um zip.

## Passo 1: separar a página em arquivos

```
site/app.html        só a marcação
site/app.css
site/app.js          pode virar dois ou três módulos (<script type="module">) se ficar grande; não mais que isso
site/i18n/pt.json
site/i18n/en.json
site/fonts/          Bricolage Grotesque e Instrument Sans em woff2, com os arquivos de licença (OFL)
```

No servidor, uma rota `GET /site/<caminho>` que serve arquivos de `site/` com lista de extensões permitidas (`css`, `js`, `json`, `woff2`, `svg`, `png`, `webp`) e a mesma checagem de contenção da rota `/arcviewer/` (o caminho resolvido tem de ficar dentro de `site/`). Tire os `<link>` do Google Fonts: a página não pode pedir nada fora de `localhost`, com uma exceção inevitável, a miniatura do vídeo na prévia de link.

Faça este passo sem mudar o visual e confira que tudo continua funcionando antes de seguir.

## Passo 2: i18n

- Um arquivo por idioma, chaves planas em `snake_case`, valores com marcadores `{nome}`. Exemplo: `"passo": "Passo {n} de 3"`.
- `t(chave, valores)` troca os marcadores. Para plural, duas chaves (`mapas_um`, `mapas_varios`). Números, durações e tamanhos com `Intl.NumberFormat(lingua)`.
- Atributos na marcação: `data-t` (texto), `data-tp` (placeholder e `aria-label`), `data-ta` (`aria-label`), `data-tt` (`title`). Os dois primeiros já existem.
- O servidor nunca devolve frase para o usuário, só códigos. Padronize as chaves de erro como `erro_<codigo>`. Códigos que existem hoje: `recusado`, `nao_existe`, `sem_mapa`, `grande`, `tipo`, `invalido`, `link`, `vazio`, `ytdlp`, `gerador`, `ocupado`, `sem_quest`, `sem_adb`, `sem_cabo`, `sem_permissao`, `sem_wifi`, `adb`. O detalhe depois de `|` (fim da saída do gerador ou do yt-dlp) é texto técnico e pode aparecer como está, num bloco recolhido "detalhe técnico".
- Etapas da geração também são códigos (`baixando`, `ouvindo`, `golpes|Hard (2/4)`, `empacotando`, `conferindo`).
- Idioma inicial: `beatloom.json`; se vazio, o do navegador (`pt*` vira `pt`, o resto `en`).
- Teste executável: `tools/check_i18n.py` (ou `--demo` de algum arquivo) que falha se os dois JSON não tiverem exatamente as mesmas chaves, ou se alguma chave usada em `site/*.html` e `site/*.js` (`data-t*="..."`, `t("...")`) não existir, ou se sobrar chave que ninguém usa. Chaves montadas em tempo de execução (`"i_" + item`, `"erro_" + codigo`) precisam de uma lista explícita no teste.

## Passo 3: relatório estruturado

Hoje `report.relatorio(mapa, humano)` devolve `(texto, passou)` e a página procura "TODAS AS METAS OK" no texto.

- Separe em duas funções: uma que calcula e devolve um dicionário, e outra que escreve o texto em português a partir dele. O texto final tem de ser idêntico ao atual (compare o `.txt` de um mapa antes e depois).
- Grave `<zip>.relatorio.json` ao lado do `.txt`, em `generate.py` e em `report.py`.
- Formato sugerido (ajuste nomes se precisar, mas mantenha tudo em números e códigos):

```json
{
  "versao": 1, "zip": "musica-v4.zip", "musica": "Nome", "dur": 213.4,
  "bpm": 128, "bpm_detectado": 128.0, "bpm_fixo": true, "info_ok": true, "passou": true,
  "difs": [{
    "nome": "Hard", "njs": 14, "offset": 0.12, "esquema_ok": true, "erro": null,
    "metas": [
      {"id": "esquema", "ok": true},
      {"id": "paridade", "ok": true, "erros": 0, "avisos": 2, "golpes": 480},
      {"id": "visao", "ok": true, "n": 0, "ex": []},
      {"id": "palmas", "ok": true, "n": 0, "ex": []},
      {"id": "empilhadas", "ok": true, "n": 0, "ex": []},
      {"id": "atravessadas", "ok": true, "n": 0, "ex": []},
      {"id": "grade", "ok": true, "fracao": 1.0},
      {"id": "folga_inicio", "ok": true, "s": 2.1},
      {"id": "folga_fim", "ok": true, "s": 3.4},
      {"id": "nps", "ok": true, "valor": 2.45, "faixa": [1.73, 5.22]}
    ],
    "notas": 522, "tempos": 480, "duplas": 42, "bombas": 0, "paredes": 6, "luzes": 910, "arcos": 3,
    "cruzadas": {"n": 0, "ex": []}, "corridas": {"n": 4, "ex": [12.3]},
    "maior_pausa": 3.2, "sobra_fim": 3.4, "salto_m": 18.2, "reacao_ms": 650,
    "ataques_precisao": 0.93, "ataques_cobertura": 0.61,
    "direcoes": {"cima": 100, "baixo": 120, "esq": 60, "dir": 62, "diagonais": 180, "ponto": 0},
    "linhas": [300, 150, 72],
    "trechos": [{"t": 0, "intens": 0.2, "nps": 1.1}], "correlacao": 0.71,
    "gerador": {"janelas4": 37, "janelas2": 37, "janelas1": 32, "regra": 0, "seguradas": 3}
  }],
  "gerador": {"etapa": 4, "capa": "arquivo", "densidade": 1.0}
}
```

- As dez metas e o que cada uma mede estão em `report.py` (lista `metas`). A página mostra cada uma com ícone de passou ou falhou, frase curta no idioma e o valor.
- `gerador` por dificuldade vem do resumo de `engine.golpes()`, que hoje é uma frase em português. Faça o motor devolver os números e monte a frase em `generate.py`. É a única mudança permitida no motor e não pode alterar as notas geradas. Deixe por último dentro deste passo.
- `/api/mapa` passa a devolver `relatorio` como esse objeto. `lista_de_mapas()` lê `passou`, `dur` e as notas por segundo do JSON.
- Mapa antigo, que só tem `.txt` (ou nada): ao abrir, o servidor dispara `report.py` numa thread, uma vez por zip, e responde `{"relatorio": null, "conferindo": true}`; a página mostra "conferindo…" e pergunta de novo. Não bloqueie a requisição: a conferência pode levar dezenas de segundos se a análise não estiver no cache.
- `lista_de_mapas()` roda a cada poucos segundos: guarde o resultado por `(zip, data de modificação)` num dicionário em memória em vez de reabrir todos os zips.
- Capas: quando a URL tem `&v=<data>`, responda com `Cache-Control: max-age=31536000, immutable`. Hoje é `no-store` e a lista com capas piscaria a cada atualização.

## Passo 4: progresso real na separação de instrumentos

A separação (Demucs, em `beatloom/audio.py`, função `_separar`) é a parte longa. Hoje a página só mostra "Ouvindo a música…".

- `generate.py` imprime linhas `[sep] 37` (porcentagem) com `flush=True` durante a separação. `app.rodar()` lê e guarda em `trab["progresso"]`; fora da separação o valor é `None` e a barra fica indeterminada.
- Como obter a porcentagem sem mudar o resultado: veja a assinatura de `demucs.apply.apply_model` na versão instalada (`inspect.signature`). Se houver `callback`, use. Se não, a função usa `tqdm` quando `progress=True`; troque `demucs.apply.tqdm.tqdm` por um embrulho mínimo que imprime a porcentagem a cada volta e devolve os mesmos itens. Não altere `split`, `overlap`, `segment` nem divida o áudio à mão: isso mudaria as faixas separadas e, com elas, os mapas. Isto não foi verificado; confira na versão instalada antes de escolher.
- Para testar na nuvem: instale `torch` (CPU), `demucs` e `beat-this`, e rode a análise com instrumentos no áudio sintético do passo 0. O modelo (uns 80 MB) é baixado na primeira vez.
- Cada trabalho em `/api/estado` ganha `progresso`, `capa` (endereço da miniatura, para o cartão) e `difs`. Trabalho com erro precisa de um jeito de ser dispensado da lista (uma rota `POST /api/trabalho/dispensar` com o `id`).

Cancelar uma geração em andamento não foi pedido e fica fora.

## Passo 5: o visual

Se houver uma skill de design de interface disponível (por exemplo `frontend-design`), use-a. A direção é esta; os valores são ponto de partida, ajuste pelo resultado na tela.

**Clima.** Palco escuro de show, com os dois sabres como luz: vermelho à esquerda, azul à direita. Sóbrio, sem neon por toda parte: o brilho aparece em seleção, foco e ação principal.

**Cores (variáveis CSS em `:root`).**

| Variável | Valor | Uso |
|---|---|---|
| `--fundo` | `#0b0a14` | fundo da página |
| `--palco` | `#12111f` | colunas e barras |
| `--painel` | `#1b1a2e` | cartões, diálogos |
| `--borda` | `rgba(255,255,255,.09)` | divisórias |
| `--texto` | `#ecebf5` | texto principal |
| `--texto-2` | `#a5a3bf` | texto secundário (confira contraste mínimo de 4,5:1 sobre `--painel`) |
| `--esq` | `#ff3355` | sabre vermelho, destaque |
| `--dir` | `#2f8fff` | sabre azul, ação principal e foco |
| `--ok` | `#3ddc97` | conferência aprovada |
| `--alerta` | `#ffb020` | conferência reprovada, avisos |
| `--erro` | `#ff5c7a` | erros |

Dificuldades com as cores que a comunidade já reconhece: Easy `#3cb371`, Normal `#59b0f4`, Hard `#ff6347`, Expert `#bf2a42`, Expert+ `#8f48db`. Nunca dependa só da cor: sempre junto de texto ou ícone.

**Tipografia.** Bricolage Grotesque nos títulos e Instrument Sans no texto (as mesmas de hoje, agora em `site/fonts/`). Não use a fonte nem o logotipo do Beat Saber.

**Estrutura** (escolhida pelo dono):

```
+------------------------------------------------------------+
| Beatloom      [+ Novo mapa]            Quest ok   PT   (*) |
+------------------+-----------------------------------------+
| [capa] Música    | [capa] Nome                             |
|  Artista         |  Artista · Álbum · 2024 · 128 BPM · 3:24 |
|        128  3:24 |  [Easy][Normal][Hard][Expert][Expert+]  |
| [capa] Música    |  +-----------------------------------+  |
|  Artista         |  |        visualizador 3D            |  |
|        174  2:58 |  +-----------------------------------+  |
| [capa] gerando…  |  notas  nps  velocidade  paredes  arcos |
|  ▓▓▓▓░░░ 37%     |  conferências            [Mandar ao Quest]|
+------------------+-----------------------------------------+
```

- Barra do topo: marca, botão principal "Novo mapa", indicador do Quest (clicar leva à parte do Quest na configuração), idioma, configuração.
- Coluna esquerda (uns 360 px, rola sozinha): a biblioteca.
- Direita: o detalhe do mapa selecionado.
- Abaixo de 900 px de largura: uma coluna só; escolher um mapa mostra o detalhe com botão de voltar.

**Biblioteca no estilo da lista de músicas do jogo.** Cada linha: capa quadrada à esquerda, nome em destaque, artista embaixo, e à direita BPM e duração empilhados com um ícone pequeno cada. Linha selecionada com faixa clara e borda no azul. Um traço emprestado do jogo, usado com parcimônia: painéis e botões levemente inclinados (`transform: skewX(-8deg)` no fundo, texto reto). Marcas na linha: conferência reprovada e "no Quest" (ou "versão antiga no Quest").

- Seleção múltipla: uma caixa aparece na linha ao passar o mouse, ao focar pelo teclado ou quando já há alguma marcada. Com uma ou mais marcadas surge uma barra de ação "Mandar N ao Quest" (usa `POST /api/quest` com `zips`) e mostra o resultado por mapa.
- Geração em andamento: cartão no topo da lista com a capa, o nome, a etapa e a barra. Erro: cartão com a mensagem, "detalhe técnico" recolhido e botão de dispensar.
- Lista vazia: em vez do detalhe, uma chamada grande com o formulário de novo mapa já aberto.
- Atualize a lista por chave (nome do zip), sem refazer tudo: refazer rouba o foco e faz as capas piscarem.

**Detalhe**, como a tela de nível do jogo: cabeçalho com capa, nome, artista, álbum, ano, BPM, duração e link da fonte; abas de dificuldade na cor de cada uma; visualizador em 16:9; uma fileira de números da dificuldade aberta (notas, notas por segundo, velocidade, paredes, notas seguradas); conferências; ações.

- Conferências: uma frase de veredito e a lista das dez metas da dificuldade aberta, cada uma com ícone e valor. Os números técnicos do relatório ficam num bloco recolhido.
- Ações: "Mandar ao Quest" é a principal quando o Quest está conectado (o rótulo muda para "Mandar de novo" ou "Atualizar no Quest"); "Baixar zip"; "Regerar esta dificuldade"; e, num menu ou em botões discretos, trocar nome, apagar do Quest, apagar o mapa.
- Sem ArcViewer instalado: no lugar do `iframe`, um cartaz explicando e um botão que instala (`POST /api/preparo` com `visor`) mostrando a barra ali mesmo.
- Trocar de dificuldade recarrega o `iframe`; não recarregue quando nada mudou.

**Novo mapa**, num `<dialog>`: um campo que aceita colar link e uma área de soltar arquivo (arrastar e soltar, e clique para escolher). Depois a prévia com capa, nome e artista editáveis, as dificuldades como botões de alternar na cor de cada uma, a quantidade de notas com as palavras "mais leve", "normal", "mais cheio", e "Gerar mapa". Ao enviar, o diálogo fecha e o cartão aparece na lista.

**Diálogos.** Troque todo `prompt()`, `confirm()` e `alert()` por `<dialog>` da página: trocar nome (dois campos), regerar (o mesmo controle de quantidade de notas), confirmar apagar mapa, confirmar apagar do Quest, confirmar limpar o cache. Enviar ao Quest não precisa de confirmação. Resultados e erros curtos aparecem em avisos temporários numa região `aria-live`.

**Preparo e configuração.** Mesmo comportamento da fatia 1, com o visual novo. No preparo, um item por linha com nome, para que serve em uma frase, tamanho e a barra; "Instalar tudo o que falta" como ação principal; a lista atualiza por item, sem ser refeita. Na configuração, as cinco partes viram seções ou abas.

**Movimento.** Transições de 150 a 200 ms em seleção, abertura de painel e barras. Respeite `prefers-reduced-motion`.

**Acessibilidade.** Tudo alcançável por teclado, foco sempre visível, `aria-current` na linha aberta, `aria-pressed` nos botões de alternar, rótulo em todo campo e botão de ícone, `lang` do documento acompanhando o idioma, dado de usuário sempre com `textContent` (nunca `innerHTML`).

## Ordem de trabalho e commits

Um commit por passo, cada um deixando a página funcionando:

1. `tools/fixture.py`.
2. Rota `/site/` e separação em arquivos, sem mudança visual. Fontes locais.
3. Frases em `site/i18n/*.json`, códigos `erro_*`, teste de i18n.
4. Relatório estruturado, `/api/mapa` e `lista_de_mapas()` novos, conferência de mapa antigo em segundo plano, cache das capas.
5. Progresso da separação e campos novos dos trabalhos.
6. Estrutura e visual novos: topo, biblioteca, detalhe.
7. Diálogo de novo mapa, cartões de geração, arrastar e soltar.
8. Diálogos de ação, avisos, seleção múltipla para o Quest.
9. Preparo e configuração no visual novo. Pendências 4 e 5 de [slice-1.md](slice-1.md).
10. READMEs e `docs/ARCHITECTURE*` nos dois idiomas, estado em [README.md](README.md), e um documento `slice-2-feito.md` no formato de `slice-1.md` (o que existe, verificado, não verificado, pendências).

## Critérios de aceite

- Os 14 itens do inventário funcionam, mais os quatro novos.
- Nenhuma frase visível fora dos arquivos de idioma; o teste de i18n passa; trocar o idioma muda tudo na hora, inclusive conferências e erros.
- Nenhum `prompt`, `confirm` ou `alert` no código da página.
- A página não pede nada fora de `localhost`, tirando a miniatura da prévia de link. Confira na aba de rede.
- O `.relatorio.txt` de um mapa é idêntico antes e depois; mapas gerados antes e depois são idênticos (compare os `.dat`).
- Sem erros no console. Sem rolagem horizontal em 1440, 1024 e 390 px de largura.
- Texto com contraste mínimo de 4,5:1.
- Os `--demo` passam: `generate.py`, `beatloom.preparo`, `beatloom.checks`, `tools/extract_patterns.py`, `tools/fixture.py`, e o teste de i18n.

## Como verificar

1. Suba o servidor com os mapas de mentira e percorra o inventário no navegador, nos dois idiomas.
2. Capturas de tela em 1440, 1024 e 390 px: biblioteca com mapa aberto, lista vazia, novo mapa com prévia, geração em andamento, erro de geração, preparo com download em andamento, configuração. Para estados difíceis de provocar (downloads, Quest conectado, erro), responda as rotas com dados de mentira no navegador, como foi feito na fatia 1.
3. Rode os `--demo` e o teste de i18n.

O que não dá para verificar na nuvem e precisa ser dito ao dono no relatório final: geração real com música de verdade, ArcViewer com mapa real, envio ao Quest, `start.bat`.

## Armadilhas conhecidas

- `ThreadingHTTPServer`: cada requisição é uma thread. `trabalhos` e `fila` são compartilhados; use `trava` ao alterar.
- O ArcViewer é servido com arquivos `.br` e `.gz` e o cabeçalho `Content-Encoding` certo; não mexa nessa rota.
- O ArcViewer lê o zip de `/zip/<nome>` com `noProxy=true`. O endereço é montado com `location.origin`.
- No Windows o console é cp1252: nada de acento em `print` de Python nem em `.bat`.
- Os nomes das dificuldades no arquivo são `Easy`, `Normal`, `Hard`, `Expert`, `ExpertPlus`; na tela, `Expert+`.
- `beatloom.json` pode não existir ou estar com chaves faltando: use sempre `config()`.
