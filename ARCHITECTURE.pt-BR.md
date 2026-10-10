# Como o Beatloom funciona

[English](ARCHITECTURE.md)

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
 2. QUANDO       gerar.py     escolhe em quais instantes vai ter nota
        │
        ▼
 3. QUAL NOTA    motor.py     posição, cor e direção de cada nota
        │
        ▼
 4. ENFEITAR     gerar.py     luzes e paredes
        │
        ▼
 5. EMPACOTAR    gerar.py     Info.dat, dificuldades, song.egg, capa → zip
        │
        ▼
 6. CONFERIR     relatorio.py relatório com as metas, ao lado do zip
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
- **Instrumentos separados.** Um programa chamado Demucs separa a música em bateria, baixo, voz e resto. É a parte demorada (alguns minutos). Medimos que os ataques da bateria isolada acertam mais que os da música inteira, então eles valem mais.

Tudo isso fica guardado em `.cache\`, então gerar de novo a mesma música é rápido.

## 2. Quando vai ter nota (`gerar.py`, função `escolher_tempos`)

Cada dificuldade tem um **orçamento**: quantos instantes com nota por segundo ela mira (Hard 2,3; Expert 3,1; Expert+ 3,9) e o menor intervalo permitido entre duas notas.

1. **Candidatas.** Toda casa com ataque é candidata, menos as dos primeiros 2 segundos e dos últimos 3 (folga para você se preparar e para a música acabar).
2. **Prioridade.** Cada candidata ganha uma nota de prioridade: força do ataque × posição na batida. Em cima da batida vale mais; no meio vale um pouco menos; nas casas de 1/4 vale pouco no Expert e zero no Hard. É por isso que o Hard não tem notas rápidas.
3. **Orçamento por compasso.** O orçamento total é repartido entre os compassos conforme a energia de cada um. Dentro do compasso, as candidatas de maior prioridade entram primeiro, respeitando o intervalo mínimo.
4. **Refrão repetido.** Um compasso marcado como cópia de outro recebe o mesmo ritmo do original, em vez de sortear de novo.
5. **Notas duplas.** Os ataques mais fortes em cima da batida, com espaço antes e depois, viram dupla (as duas mãos juntas). Se a música é lenta e não chega à densidade mínima da dificuldade, a proporção de duplas sobe, em vez de inventar nota onde não há som.

O resultado desta etapa é só uma lista: "nestas casas tem nota; nestas, dupla".

## 3. Qual nota (`motor.py`)

Aqui entra a biblioteca de padrões. Ela foi montada cortando centenas de mapas humanos bem avaliados em **janelas** de 4, 2 e 1 batidas. Cada janela guarda o desenho das notas e é etiquetada pelo **ritmo** dela (quais casas têm nota). A biblioteca não guarda músicas, só esses desenhos.

O motor anda pela música batida a batida:

1. Olha o ritmo das próximas 4 batidas e procura na biblioteca janelas humanas com **exatamente o mesmo ritmo**.
2. Testa as candidatas contra o estado atual dos seus braços: onde cada sabre está, para que lado foi o último golpe, quanto o pulso está girado. Descarta as que quebram a paridade, as que pedem um movimento rápido demais para a mão, e as que criam defeito (ver abaixo).
3. Entre as que sobram, prefere aquelas em que o braço chega vindo do mesmo lugar que no mapa humano original, e as que deixam a próxima batida fácil de continuar.
4. Se nenhuma janela de 4 batidas serve, tenta de 2, depois de 1. Se nada serve, usa o último recurso: sobe e desce reto, cada mão no seu lado.

**Refrão igual, desenho igual.** Em compasso repetido, o motor tenta reusar o desenho que usou no original. Há um detalhe: cada nota inverte o lado do braço, então metade das vezes você chega ao refrão "pelo outro lado" e o desenho idêntico seria impossível. Nesses casos ele usa o mesmo desenho espelhado de cima para baixo: mesmo ritmo, mesmas mãos, mesmas colunas.

**Altura por instrumento.** Entre padrões equivalentes, bateria tende a ficar embaixo e voz e melodia em cima.

**Rede de segurança.** No fim, uma passada conserta sobras raras mexendo só na posição das notas (isso nunca altera a paridade).

Os defeitos evitados:

- **Bloqueio de visão**: uma nota no meio da tela escondendo a que vem logo atrás.
- **Palma**: as duas mãos obrigadas a se cruzar ou se bater.
- **Nota empilhada**: duas notas no mesmo lugar ao mesmo tempo.

## 4. Luzes e paredes (`gerar.py`)

- **Luzes**: nunca fica escuro; pisca na batida e muda de cor nos compassos intensos. É simples de propósito.
- **Paredes**: só nas pausas de 1,6 segundo ou mais, na coluna da ponta. São decoração; nenhuma exige que você se mova.

## 5. Empacotar (`gerar.py`)

Durante todo o processo o tempo é contado em segundos. Só na hora de escrever o arquivo ele é convertido para a unidade do jogo (batidas). Isso evita erros de arredondamento.

O zip leva: `Info.dat` (nome, BPM, dificuldades), um arquivo por dificuldade, `song.egg` e a capa. A prévia que toca no menu do jogo começa no trecho mais intenso da música. A velocidade das notas é 14, 16 e 18 (o valor típico dos mapas humanos da biblioteca).

## 6. Conferir (`relatorio.py`, `checks.py`, `check\check.mjs`)

O mapa pronto é lido de volta e passa por dois juízes:

- **bsmap**, uma biblioteca da comunidade, confere se o formato é válido e conta erros de paridade. É a opinião de fora.
- **Nossas regras** (`checks.py`), que são as mesmas usadas pelo motor na etapa 3: bloqueio de visão, palma, nota empilhada, notas na batida, folga no começo e no fim, notas por segundo dentro da faixa.

O relatório marca cada meta com `[ok]` ou `[FALHOU]` e fica salvo ao lado do zip. Passar em tudo quer dizer "jogável e sem defeito conhecido". Não quer dizer "divertido": isso nenhuma regra mede.

## As quatro etapas do gerador

`--etapa` liga as peças aos poucos. Serve para comparar versões e ver o que cada ideia acrescentou.

| Etapa | Quando | Qual nota |
|---|---|---|
| 1 | orçamento único para a música toda | BeatKenja (programa de terceiros) |
| 2 | orçamento por compasso, refrão repete | BeatKenja |
| 3 | igual à 2 | motor próprio com padrões humanos |
| 4 | igual à 2, com instrumentos separados | motor próprio, altura por instrumento, paredes |

## O site (`app.py`, `app.html`)

É um servidor pequeno que só atende o seu próprio computador. Ele faz três coisas: recebe o link ou arquivo e chama o `gerar.py` (um mapa por vez, porque a análise usa o processador inteiro), lista os zips de `saida\`, e entrega o zip ao ArcViewer, o visualizador 3D embutido na página. Os links são baixados pelo yt-dlp. Nada é enviado para fora.

## A biblioteca de padrões (`baixar_mapas.py`, `extrair_padroes.py`)

`baixar_mapas.py` busca no BeatSaver mapas com nota alta e muitos votos, feitos por pessoas, sem mods, e guarda só os arquivos de notas (o áudio é descartado). `extrair_padroes.py` corta esses mapas nas janelas descritas acima, também em versão espelhada (esquerda ↔ direita), e grava um arquivo por dificuldade em `dados\`.

## O que ele ainda não sabe fazer

- Notas mais rápidas que 1/4 de batida, tercinas e swing.
- Bombas, arcos, correntes e notas de ponto.
- Entender a estrutura da música além de "este compasso é igual àquele" e "este é mais intenso".
- Saber se o mapa ficou divertido. Para isso existe o `teste_cego.py`: ele embaralha duas versões da mesma música como A e B para você jogar sem saber qual é qual.
