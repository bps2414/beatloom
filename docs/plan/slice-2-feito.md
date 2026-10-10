# Fatia 2: redesenho, i18n e relatório estruturado (feita)

Feita em 10/10/2026, na máquina do dono. O plano está em [slice-2.md](slice-2.md); este documento diz o que existe, o que foi verificado, o que não foi e o que ficou diferente do plano.

## O que o usuário ganhou

1. Página nova: palco escuro, biblioteca à esquerda no jeito da lista de músicas do jogo (capa, nome, artista, BPM e duração), detalhe à direita com abas de dificuldade nas cores conhecidas, visualizador, números e conferências.
2. Tudo em português ou inglês, inclusive as conferências e os erros. Trocar o idioma muda a página na hora.
3. Conferências legíveis: um veredito e as dez metas da dificuldade aberta, cada uma com ícone e valor. Os números técnicos ficam recolhidos.
4. Barra de progresso de verdade enquanto os instrumentos são separados.
5. "Novo mapa" num diálogo, com arrastar e soltar arquivo em qualquer lugar da página.
6. Marcar vários mapas e mandar todos ao Quest de uma vez.
7. Nenhuma janela do navegador (`prompt`, `confirm`, `alert`): tudo são diálogos e avisos da própria página.
8. A página não pede mais nada à internet (as fontes vieram para `site/fonts/`), tirando a miniatura do vídeo na prévia de link.

## Arquivos

| Arquivo | Papel |
|---|---|
| `site/app.html` | Só a marcação: topo, biblioteca, detalhe, cinco `<dialog>`, um `<template>` da linha da lista |
| `site/app.css` | Cores e fontes em variáveis no `:root`; o fundo inclinado dos botões e linhas fica em `::before` com `--inclina` |
| `site/app.js` | Um módulo só. `t(chave, valores)`, `api()`, `avisar()`, `confirmar()`, e uma função `pintar…` por parte da tela |
| `site/i18n/pt.json`, `en.json` | Frases, chaves planas, marcadores `{nome}` |
| `site/fonts/` | Bricolage Grotesque e Instrument Sans (variáveis, woff2, subconjunto latino) e as duas licenças OFL |
| `tools/check_i18n.py` | Falha se os idiomas tiverem chaves diferentes, chave usada que não existe, chave sobrando ou marcadores diferentes |
| `report.py` | `conferir()` devolve os dados, `texto()` escreve o `.txt` de sempre, `gravar_json()` grava o `.relatorio.json`. `--so-json`, `--demo` |
| `generate.py` | Grava o `.relatorio.json` com o resumo do gerador em números (`gerador` no mapa e em cada dificuldade) |
| `beatloom/engine.py` | `golpes()` devolve também as contagens do resumo (quarto valor). As notas não mudam |
| `beatloom/audio.py` | `_separar()` imprime `[sep] N` pelo `callback` do `apply_model` do Demucs, e `[sep] fim` |
| `app.py` | Rotas e funções abaixo |

## Servidor

- `GET /site/<caminho>`: arquivos de `site/` com extensão em `TIPOS` (css, js, json, woff2, svg, png, webp) e caminho resolvido dentro de `site/`. `app.html` só sai por `/`.
- `GET /api/estado`: cada mapa tem `zip, nome, sub, artista, bpm, ok, dur, v, difs`. `ok` é `true`, `false` ou `null` (ainda sem `.relatorio.json`); `v` é a data do zip e vai na URL da capa. `lista_de_mapas()` guarda cada linha em `lidos` e só reabre o zip quando a data dele ou do relatório muda. Cada trabalho ganhou `progresso` (0 a 100 durante a separação, `null` fora dela) e `capa`.
- `GET /api/mapa`: `relatorio` é o objeto do `.relatorio.json` ou `null`, mais `conferindo` e `v`. Sem o JSON, `conferir(zp)` roda `report.py <zip> --so-json` numa thread, uma vez por versão do zip; a página pergunta de novo a cada 3 s. `--so-json` não toca no `.txt`, que nos mapas gerados tem também o resumo do gerador.
- `GET /api/capa?zip=…&v=…`: com `v`, `Cache-Control: max-age=31536000, immutable`.
- `GET /api/config`: `torch` vem vazio se o pacote não estiver instalado (pendência 5 da fatia 1).
- `POST /api/gerar`: aceita `capa` (endereço `http(s)` ou `/api/capa?…`), só para o cartão da fila.
- `POST /api/trabalho/dispensar {"id"}`: tira da lista um trabalho que acabou.
- `POST /api/apagar`: leva também o `.relatorio.json` para a lixeira.

## `.relatorio.json`

Formato do plano, com estas diferenças: `direcoes` é a lista de nove contagens (índice = direção do jogo) e `trechos` é uma lista de `[início, intensidade, nps]`; `gerador` por dificuldade tem as chaves que o motor já contava (`padrao4`, `padrao2`, `padrao1`, `regra`, `descartadas`, `rep_tentou`, `rep_igual`, `rep_inv`); `gerador` do mapa tem `etapa`, `capa` (`escolhida`, `audio` ou `generica`) e `densidade`. Mapa conferido depois (por `report.py`) não tem `gerador`.

## A página

- Idioma: `T.pt` e `T.en` são carregados no início; `traduzir()` reescreve `data-t` (texto), `data-tp` (placeholder e `aria-label`) e `data-ta` (`aria-label`) e chama todos os `pintar…`.
- Erros: `lerErro("codigo|detalhe")` devolve a frase `erro_<codigo>` e o detalhe, que aparece num bloco recolhido "Detalhe técnico".
- Lista: uma `<li>` por zip guardada em `linhas`, atualizada no lugar e reordenada com `insertBefore`. Os cartões de geração só são refeitos quando algo muda.
- Seleção múltipla: a caixa de cada linha só existe com o Quest conectado (`body.com-quest`); aparece ao passar o mouse, ao focar, e fica visível quando há alguma marcada.
- Abas de dificuldade: refeitas só quando o mapa muda; dificuldade com conferência reprovada leva um `!` e `aria-label`.
- Visualizador: o `iframe` só recarrega quando muda o zip, a versão dele ou a dificuldade. Sem ArcViewer aparece um cartaz com o botão de instalar e a barra ali mesmo.
- Avisos: `#avisos` é um `popover`, para ficar por cima até de um diálogo aberto.
- Preparo: uma linha por item criada uma vez e atualizada no lugar (pendência 4 da fatia 1).
- Abaixo de 900 px: uma coluna; abrir um mapa mostra o detalhe com um botão de voltar.

## Verificado

- `.relatorio.txt` idêntico byte a byte antes e depois em dois mapas reais (um aprovado, um reprovado), também depois de passar pelo JSON.
- Mesma música gerada antes e depois da mudança: `Info.dat`, `song.egg` e os cinco `.dat` idênticos, `.relatorio.txt` idêntico. Só a capa genérica difere, e já diferia a cada geração.
- Geração de verdade pela página (trecho de 40 s, Hard e Expert): `progresso` foi de 0 a 88 durante a separação, voltou a `null`, o mapa saiu com `.relatorio.json` e `gerador` preenchido.
- Mapa antigo aberto na página: conferido em segundo plano, a duração e as conferências apareceram sozinhas.
- No navegador, a 1440 px e a 390 px, sem rolagem horizontal e sem erro no console: biblioteca, mapa aberto com ArcViewer, conferências e números técnicos, diálogo de novo mapa com prévia de link do YouTube, configuração, troca de idioma. Com respostas simuladas: cartões de geração (em andamento com barra, na fila, erro com detalhe técnico), Quest conectado, marcas "no Quest" e "versão antiga", seleção de dois mapas com a barra de envio, biblioteca vazia, cartaz de visualizador não instalado.
- Rota `/site/`: caminho com `..` devolve 404, fonte e JSON saem com o tipo certo.
- `--demo` de `generate.py`, `report.py`, `beatloom.preparo`, `beatloom.checks`, `tools/extract_patterns.py` e `tools/check_i18n.py`.

## Não verificado

- Envio de verdade ao Quest (um e vários), apagar do Quest, pareamento. O Quest estava desligado; as rotas não mudaram desde a fatia 1.
- Os diálogos de trocar nome, regerar e apagar abrem com os dados certos e cancelam sem efeito (conferido); confirmar cada um até o fim não foi feito, para não mexer nos mapas do dono. As rotas que eles chamam não mudaram.
- A tela da primeira vez (passos 1 a 3) com o visual novo: a máquina já estava preparada. A lógica é a da fatia 1.
- A barra de download do visualizador dentro do cartaz.
- Arrastar e soltar um arquivo (a escolha por clique usa o mesmo caminho).
- Largura de 1024 px e contraste medido com ferramenta. As cores de texto são as do plano.
- Leitor de tela.

## Diferente do plano

1. `tools/fixture.py` não foi criado: servia para a nuvem, e o trabalho foi feito com mapas reais.
2. Biblioteca vazia mostra a chamada grande com o botão "Novo mapa", não o formulário já aberto.
3. A lista mostra a duração só depois que o mapa tem `.relatorio.json`; mapa antigo ganha o arquivo na primeira vez que é aberto. Notas por segundo aparecem no detalhe, não na lista.
4. Os trechos de 4 compassos (intensidade e notas por segundo) estão no JSON mas a página ainda não os desenha.
5. Menos commits que os dez do plano: servidor e relatório num, página noutro, documentos noutro.

## Pendências

1. Testar com o Quest ligado (vale desde a fatia 1).
2. Regerar uma dificuldade reescreve o `.relatorio.txt` sem o bloco "GERADOR" e o JSON sem `gerador` (já era assim com o `.txt`).
3. Mapas mandados ao Quest pelo script antigo continuam sem a marca "no Quest".
4. Ainda não existe release no GitHub.
