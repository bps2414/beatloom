# Como o Beatloom funciona

[English](ARCHITECTURE.md)

Os arquivos citados ficam em: `generate.py`, `app.py` e `report.py` na raiz; `audio.py`, `engine.py` e `checks.py` em `beatloom\`; o resto em `tools\` e `site\`.

Este texto explica o caminho que uma música percorre até virar um mapa, peça por peça, sem pressupor que você programa.

## A ideia em uma frase

O Beatloom responde a duas perguntas, uma depois da outra: **quando** vai ter nota (ouvindo a música) e **qual** nota vai ser (copiando pedacinhos de mapas feitos por pessoas). Depois ele confere o resultado com regras e só então entrega o zip.

```
 música (mp3, link)
        │
        ▼
 1. OUVIR        audio.py     batidas, ataques, energia, refrões, instrumentos
        │
        ▼
 2. QUANDO       generate.py     escolhe em quais instantes vai ter nota
        │
        ▼
 3. QUAL NOTA    engine.py     posição, cor e direção de cada nota
        │
        ▼
 4. ENFEITAR     generate.py, luzes.py     notas seguradas, luzes, cores, cenário e paredes
        │
        ▼
 5. EMPACOTAR    generate.py     Info.dat, dificuldades, song.egg, capa → zip
        │
        ▼
 6. CONFERIR     report.py relatório com as metas, ao lado do zip
```

## Três palavras que aparecem o tempo todo

- **Batida**: o pulso da música, aquele em que você bate o pé. BPM é quantas batidas cabem em um minuto.
- **Casa**: cada batida é dividida em 4 partes iguais. Cada parte é uma casa. Uma nota só pode cair em uma casa, nunca entre duas. O conjunto de todas as casas da música é a **grade**.
- **Paridade**: depois de um golpe para baixo, o braço está embaixo, então o próximo golpe natural daquela mão é para cima. Um mapa que pede dois golpes seguidos para baixo com a mesma mão obriga a torcer o pulso ou "voltar" o braço no ar. Isso é um erro de paridade, e o Beatloom não deixa passar nenhum.

## 1. Ouvir (`audio.py`)

Antes de tudo, a música é convertida para o formato que o jogo usa (`song.egg`), e a análise é feita nesse arquivo, para o mapa ficar alinhado com o que você vai ouvir no jogo.

- **Batidas e compassos.** Um programa chamado beat_this acha onde está cada batida e onde começa cada compasso (grupo de batidas, quase sempre 4). Ele costuma marcar a batida uns 17 milésimos de segundo atrasada, então o Beatloom corrige isso comparando com os ataques reais do som.
- **Andamento que varia.** Música tocada por banda acelera e desacelera um pouco. A grade acompanha a música em vez de assumir um BPM fixo, com uma suavização para não tremer.
- **Música lida "pela metade".** Se o programa entende a música como muito lenta (menos de 100 BPM, com compassos de 2 batidas), o Beatloom dobra o BPM.
- **Ataques.** Um ataque é o instante em que um som começa (uma batida de caixa, uma nota de guitarra). Para cada casa da grade fica anotado se ali tem ataque forte, fraco ou nenhum, e a força dele.
- **Energia por compasso.** Um número de 0 a 1 que diz o quanto cada compasso é intenso. É isso que faz o refrão ter mais notas que o verso.
- **Compassos repetidos.** Compara o som dos compassos entre si. Quando um é igual a outro que já passou (o refrão voltando), fica anotado de qual ele é cópia.
- **Partes da música.** Compassos vizinhos parecidos em timbre e harmonia são juntados em trechos, e cada compasso ganha um rótulo: introdução, verso, subida (os compassos que levam ao trecho cheio), queda (o trecho cheio: refrão ou drop) ou pausa (quase silêncio e sem ataques).
- **Voz cantada.** Na faixa de voz separada, o Beatloom segue a altura cantada (pYIN, do librosa). Daí saem as sílabas (onde começa nota nova), a altura de cada uma e as notas longas.
- **Peças da bateria.** Na faixa de bateria separada, o ataque é classificado pela faixa de frequência: bumbo (grave), caixa (médio), prato (agudo) e prato de ataque (o agudo que continua soando).
- **Notas longas.** Nota cantada segurada por pelo menos uma batida e meia (o "ahhh") fica anotada para virar nota segurada. Na melodia vale quando o instrumento ataca e segura a mesma nota, sem outro ataque forte no meio.
- **Instrumentos separados.** Um programa chamado Demucs separa a música em bateria, baixo, voz e resto. É a parte demorada (alguns minutos). Medimos que os ataques da bateria isolada acertam mais que os da música inteira, então eles valem mais.

Tudo isso fica guardado em `.cache\`, então gerar de novo a mesma música leva segundos em vez de minutos.

## 2. Quando vai ter nota (`generate.py`, função `escolher_tempos`)

Cada dificuldade tem um **orçamento**: quantos instantes com nota por segundo ela mira (Easy 1,25; Normal 1,8; Hard 2,45; Expert 3,3; Expert+ 4,1) e o menor intervalo permitido entre duas notas. Os números ficam perto do quarto mais leve dos mapas humanos de cada dificuldade.

1. **Candidatas.** Toda casa com ataque é candidata, menos as dos primeiros 2 segundos e dos últimos 3 (folga para você se preparar e para a música acabar). Onde começa uma sílaba cantada também é candidata, com peso entre o do ataque forte e o do fraco.
2. **Prioridade.** Cada candidata ganha uma nota de prioridade: força do ataque × posição na batida. Em cima da batida vale mais; no meio vale um pouco menos; nas casas de 1/4 vale pouco no Expert e zero no Easy, no Normal e no Hard. É por isso que eles não têm notas rápidas.
3. **Orçamento por compasso.** O orçamento total é repartido entre os compassos conforme a energia de cada um e a parte da música: a queda leva 10% a mais, a subida começa com 20% a menos e chega nela com 20% a mais, e a pausa fica sem nota. Dentro do compasso, as candidatas de maior prioridade entram primeiro, respeitando o intervalo mínimo.
4. **Refrão repetido.** Um compasso marcado como cópia de outro recebe o mesmo ritmo do original, em vez de sortear de novo. Se ele tiver ataques que o original não tinha, completa até o orçamento dele.
5. **Trecho vazio.** Se sobra um trecho de 2 batidas ou mais sem nota (4 no Normal) com pelo menos 3 ataques fortes dentro, o ataque mais forte ganha nota, até não sobrar trecho assim.
6. **Respiro antes do refrão.** Quando a energia sobe de um compasso para o outro, a batida anterior fica sem nota e a primeira batida do trecho forte entra com nota dupla.
7. **Notas duplas.** Os ataques mais fortes em cima da batida, com espaço antes e depois, viram dupla (as duas mãos juntas); o prato de ataque passa na frente. Se a música é lenta e não chega à densidade mínima da dificuldade, a proporção de duplas sobe, em vez de inventar nota onde não há som.

O resultado desta etapa é só uma lista: "nestas casas tem nota; nestas, dupla".

## 3. Qual nota (`engine.py`)

Aqui entra a biblioteca de padrões. Ela foi montada cortando centenas de mapas humanos bem avaliados em **janelas** de 4, 2 e 1 batidas. Cada janela guarda o desenho das notas e é etiquetada pelo **ritmo** dela (quais casas têm nota). A biblioteca não guarda músicas, só esses desenhos.

O motor anda pela música batida a batida:

1. Olha o ritmo das próximas 4 batidas e procura na biblioteca janelas humanas com **exatamente o mesmo ritmo**.
2. Testa as candidatas contra o estado atual dos seus braços: onde cada sabre está, para que lado foi o último golpe, quanto o pulso está girado. Descarta as que quebram a paridade, as que pedem um movimento rápido demais para a mão, e as que criam defeito (ver abaixo).
3. Entre as que sobram, prefere aquelas em que o braço chega vindo do mesmo lugar que no mapa humano original. A emenda entre duas janelas que mapa humano quase nunca faz (as trocas de posição mais raras, que somam 2% de todas as da biblioteca) perde pontos. Do Hard para cima, a janela que vem de mapas mais bem avaliados ganha um pouco.
4. As cinco melhores candidatas são então ensaiadas até 8 batidas à frente, cada uma seguida pela melhor escolha de cada janela seguinte. Ganha a que deixa o resto da frase sair melhor: janelas maiores que ainda cabem, desenho repetido que consegue voltar, nada de cair no último recurso.
5. Se nenhuma janela de 4 batidas serve, tenta de 2, depois de 1. Se nada serve, usa o último recurso: sobe e desce reto, cada mão no seu lado.

**Refrão igual, desenho igual.** Em compasso repetido, o motor tenta reusar o desenho que usou no original. Há um detalhe: cada nota inverte o lado do braço, então metade das vezes você chega ao refrão "pelo outro lado" e o desenho idêntico seria impossível. Nesses casos ele usa o mesmo desenho espelhado de cima para baixo: mesmo ritmo, mesmas mãos, mesmas colunas.

**Motivo e variação.** Repetir nem sempre é copiar. Na segunda vez que um compasso volta (e na sexta, na décima...) o motor tenta primeiro o desenho espelhado da esquerda para a direita, com as mãos trocando de papel. Na terceira, tenta o mesmo desenho com um acento a mais: no ataque mais forte em cima da batida em que só uma mão bate, a outra entra junto, ao lado. Se a variação não cabe, vale o desenho normal.

**Altura por instrumento.** Entre padrões equivalentes, bateria tende a ficar embaixo (bumbo na linha de baixo, caixa na do meio) e voz e melodia em cima. Onde começa uma sílaba cantada sem batida forte da bateria junto, quem escolhe é a voz: nota mais aguda que a frase em volta vai para cima, mais grave vai para baixo, e melodia subindo prefere corte para cima. É uma preferência, não uma regra: a paridade e os defeitos vêm antes, então só parte das notas segue a voz.

**Tamanho do golpe.** O quarto mais forte dos ataques do mapa prefere a nota longe de onde a mão estava (braço largo); o quarto mais fraco prefere perto (golpe curto).

**Verso diferente de refrão.** Trecho intenso prefere desenhos abertos (linhas de cima, pontas, diagonais); trecho calmo prefere sobe e desce simples embaixo. Um desenho que já saiu muitas vezes perde pontos, para não repetir sempre o mesmo.

**Velocidade do braço.** Cada dificuldade tem um teto para a distância que a mesma mão percorre entre duas notas (6, 8, 10 e 12 casas por segundo), tirado do 1% mais rápido dos mapas humanos. O Normal também evita diagonais.

**Braços cruzados.** No Easy, no Normal e no Hard os braços nunca cruzam. No Expert e no Expert+ quem escolhe é o jogador, na Configuração: nunca, pouco (o padrão: no máximo 8 cruzamentos a cada mil notas no Expert e 20 no Expert+, que é o quarto dos mapas humanos que menos cruza) ou livre (cruzar só perde pontos).

**Pilhas.** Depois de escolhidos os golpes, os acentos mais fortes dos trechos intensos ganham uma pilha: uma segunda nota da mesma cor na casa vizinha, na linha do corte, e um golpe só passa pelas duas. O Hard recebe umas 3 a cada mil notas, o Expert 8 e o Expert+ 15, perto dos mapas humanos mais leves. No Expert e no Expert+ uma pilha por mapa vira torre de três notas. A pilha só entra onde a mão tem um quarto de segundo livre antes e depois e onde não cria defeito.

**Notas seguradas.** Onde há nota longa na música, as duas mãos cortam juntas no começo (de baixo para cima, ou o inverso se o braço estiver do outro lado), um arco liga cada nota à nota do fim, cortada no sentido contrário, e não há nada no meio. O Normal não usa. Entram das mais longas para as mais curtas, no máximo uma a cada 20 segundos de música.

**Rede de segurança.** No fim, uma passada conserta sobras raras mexendo só na posição das notas (isso nunca altera a paridade).

Os defeitos evitados:

- **Bloqueio de visão**: uma nota no meio da tela escondendo a que vem logo atrás.
- **Palma**: as duas mãos obrigadas a se cruzar ou se bater.
- **Nota empilhada**: duas notas no mesmo lugar ao mesmo tempo.
- **Sabre atravessando**: numa dupla, o sabre de uma mão passando pela nota da outra cor.

## 4. Luzes, cores, cenário e paredes (`beatloom/luzes.py`, `generate.py`)

- **Luzes**: seguem as partes da música e a bateria. O gerador escreve "deixas" (quando, qual luz, o que ela faz, cor, brilho) e só no fim elas viram evento do mapa. Introdução e verso têm o fundo aceso e os anéis pulsando no bumbo; a subida começa quase apagada e acende uma luz depois da outra; logo antes da queda apaga tudo; a queda entra com um clarão branco, tudo aceso, lasers batendo na caixa e anéis girando no bumbo; a pausa fica no escuro. Prato de ataque dá um clarão branco.
- **Cores**: saem da capa. O tom que mais aparece e o segundo (ou o oposto dele, se a capa tem um tom só) são as cores das luzes; outro par entra nas quedas. Sabres e notas só usam essas cores se você ligar a opção, e só quando os dois tons são bem diferentes. Capa cinza fica com as cores do jogo.
- **Cenário**: segue o clima da música. Andamento de máquina ou bateria na frente de tudo é "eletrônico", som cheio de ruído é "pesado", o resto é "calmo". Cada clima tem um cenário clássico e um novo; a música decide qual. Os clássicos acendem com eventos básicos; os novos, com grupos de luzes, e o mesmo roteiro de deixas serve aos dois.
- **Paredes**: nas pausas de 1,6 segundo ou mais e na entrada de cada queda, na coluna da ponta, onde não há nota. São decoração; nenhuma exige que você se mova.

## 5. Empacotar (`generate.py`)

Durante todo o processo o tempo é contado em segundos. Só na hora de escrever o arquivo ele é convertido para a unidade do jogo (batidas). Isso evita erros de arredondamento.

**Andamento que varia.** Quando o BPM não é fixo, o arquivo de cada dificuldade leva eventos de BPM: um a cada trecho em que o andamento muda, com os inícios de compasso a até 10 milésimos de segundo da grade. Assim o jogo e os editores desenham a grade no lugar certo. O BPM do `Info.dat` continua sendo o mediano.

O zip leva: `Info.dat` (nome, BPM, dificuldades), um arquivo por dificuldade (formato v3, que é o que aceita arcos), `song.egg` e a capa. A prévia que toca no menu do jogo começa no trecho mais intenso da música. A velocidade das notas é 10, 12, 14, 16 e 18 (o valor típico dos mapas humanos da biblioteca).

**Nome, artista e capa.** Valem, nesta ordem: o que você escreveu; a faixa e o artista que o yt-dlp informa; as tags do arquivo; o título do vídeo ou o nome do arquivo limpo ("Artista - Música", sem "Official Video" nem "feat."). A capa vem da imagem que você indicar, da miniatura do vídeo ou da imagem embutida no arquivo, cortada em quadrado; só na falta de tudo sai a genérica. Álbum, ano e link não têm campo próprio no `Info.dat`: ficam em `_customData`, que o jogo ignora e o site mostra.

## 6. Conferir (`report.py`, `checks.py`, `check\check.mjs`)

O mapa pronto é lido de volta e passa por dois juízes:

- **bsmap**, uma biblioteca da comunidade, confere se o formato é válido e conta erros de paridade. É a opinião de fora.
- **Nossas regras** (`checks.py`), que são as mesmas usadas pelo motor na etapa 3: bloqueio de visão, palma, nota empilhada, sabre atravessando nota, notas na batida, folga no começo e no fim, notas por segundo dentro da faixa.

O relatório marca cada meta com `[ok]` ou `[FALHOU]` e fica salvo ao lado do zip. Passar em tudo quer dizer "jogável e sem defeito conhecido". Não quer dizer "divertido": isso nenhuma regra mede.

## As quatro etapas do gerador

`--etapa` liga as peças aos poucos. Serve para comparar versões e ver o que cada ideia acrescentou.

| Etapa | Quando | Qual nota |
|---|---|---|
| 1 | orçamento único para a música toda | BeatKenja (programa de terceiros) |
| 2 | orçamento por compasso, refrão repete | BeatKenja |
| 3 | igual à 2 | motor próprio com padrões humanos |
| 4 | igual à 2, com instrumentos separados | motor próprio, altura por instrumento, paredes |

A página gera na etapa 4. O "modo rápido" dela é a etapa 3: separar os instrumentos é uns 70% do tempo, então sai umas 6 vezes mais rápido, sem notas seguradas nem paredes. A análise roda na placa de vídeo quando o torch instalado tem CUDA (NVIDIA) e volta ao processador se a placa falhar (`dispositivo()` e `na_placa()` em `beatloom\audio.py`). `tools\timing.py <audio>` mede quanto cada parte demora.

## O site (`app.py`, `site\`)

É um servidor pequeno que só atende o seu próprio computador. Antes de gerar ele mostra a capa e os dados da música para você corrigir e deixa escolher dificuldades e quantidade de notas. Ele faz três coisas: recebe o link ou arquivo e chama o `generate.py` (um mapa por vez, porque a análise usa o processador inteiro), lista os zips de `saida\`, e entrega o zip ao ArcViewer, o visualizador 3D embutido na página. Os links são baixados pelo yt-dlp. Nada é enviado para fora. Também refaz uma única dificuldade de um mapa pronto com outra quantidade de notas, troca o nome, manda para `saida\lixeira` e envia ao Quest por ADB (`beatloom\quest.py`; cada mapa vira a pasta `beatloom-<nome do zip>`, então mandar de novo substitui a versão antiga). Na primeira vez ele confere o que falta e baixa para dentro da pasta do projeto (`beatloom\preparo.py`).

A página é HTML, CSS e JS puros, sem etapa de build (`site\app.html`, `app.css`, `app.js`), e não pede nada fora do seu computador, tirando a miniatura do vídeo quando você cola um link. Toda frase mora em `site\i18n\pt.json` e `en.json`; o servidor só responde com códigos e números. Isso vale para as conferências: o `report.py` grava `<zip>.relatorio.json` ao lado do relatório em texto e a página escreve cada conferência no idioma escolhido. Mapa feito antes de esse arquivo existir é conferido em segundo plano na primeira vez que você abre. Enquanto os instrumentos são separados o gerador imprime `[sep] N` e a página transforma isso em barra de progresso.

## A biblioteca de padrões (`tools\download_maps.py`, `tools\extract_patterns.py`)

`tools\download_maps.py` busca no BeatSaver mapas com nota alta e muitos votos, feitos por pessoas, sem mods, e guarda só os arquivos de notas (o áudio é descartado). `tools\extract_patterns.py` corta esses mapas nas janelas descritas acima, também em versão espelhada (esquerda ↔ direita), e grava um arquivo por dificuldade em `dados\`. Janela de mapa mais bem avaliado pesa mais: pela posição na ordem das avaliações, de 0,5 no mapa pior avaliado do conjunto a 2 no melhor.

## O que ele ainda não sabe fazer

- Notas mais rápidas que 1/4 de batida, tercinas e swing.
- Bombas, correntes e notas de ponto.
- Entender a estrutura da música além de "este compasso é igual àquele" e "este é mais intenso".
- Saber se o mapa ficou divertido. Para isso existe o `tools\blind_test.py`: ele embaralha duas versões da mesma música como A e B para você jogar sem saber qual é qual.
