# Resultados

O que já foi feito no gerador, bloco por bloco, com o que foi medido, o que cada item faz e os limites conhecidos. Saiu do [roadmap](ROADMAP.md) em 10/10/2026 para ele ficar só com o que falta. Os itens numerados no fim de cada bloco são o texto original do pedido.

## Ouvir melhor a música e mapear mais como gente

Pedido do dono: detector melhor, mapa mais humano, mais intenso e mais realista; vocais melhor detectados; "sentir" a música; notas mais coerentes.

Como está hoje (depois dos blocos 1.1, 1.2 e da primeira parte do 1.3), para saber de onde se parte: batidas pelo beat_this, ataques pelo librosa na música inteira e em cada uma das quatro faixas do Demucs (bateria, baixo, voz, resto), altura cantada pelo pYIN, peças da bateria por faixa de frequência, partes da música (intro, verso, subida, queda, pausa), intensidade por compasso, e os golpes vêm de trechos de 1, 2 ou 4 batidas tirados de mapas humanos, escolhidos ensaiando 8 batidas à frente; compasso repetido reaproveita o desenho, espelhado ou com um acento a mais nas voltas; pilhas nos acentos; braços cruzados com teto. As luzes seguem as partes da música e a bateria, com as cores da capa, num cenário escolhido pelo clima da música.

**Ordem.** O 1.0 vem primeiro, porque os outros medem com ele. O 1.4 (pesquisa) pode vir a qualquer hora e rende mais antes do 1.1, porque pode poupar trabalho. O 1.1 vem antes do 1.2 e de parte do 1.3: as luzes (1.3 item 1) usam as partes da música (1.1 item 3) e os arcos (1.3 item 6) usam a voz (1.1 item 1). Do 1.3, os itens 2, 3, 7 e 8 não dependem de nada. Os blocos 2, 3 e 4 são livres.

**Modelo.** O dono decidiu rodar tudo em Opus 5.5, esforço médio (10/10/2026).

### 1.0 Antes de mexer: saber medir "melhor"

Sem isto qualquer mudança vira gosto. Ferramentas que já existem: `tools/blind_test.py` (par A/B às cegas) e `--humano` (compara os tempos com um mapa humano da mesma música).

- Montar um conjunto fixo de umas 10 músicas de estilos diferentes, com mapa humano bem avaliado de cada uma.
- Números por mudança: quantos ataques fortes viraram nota, quantas notas caem em ataque, parecido com o humano em densidade por trecho, e o teste cego do dono jogando.
- Cada item abaixo só entra se ganhar nesse conjunto.
- **Comparar com os outros geradores.** Meta do dono: ser o melhor. Gerar as mesmas músicas no Beat Sage e no TopMapper, passar os zips pela nossa conferência (`report.py`; a conferir se aceita zip de fora) e pelo script de medição, e jogar às cegas com `tools/blind_test.py`. Sem isso não há como dizer quem é melhor.

**Medição mínima (feita em 10/10/2026):** `tools/medir.py` confere de novo, sem mapa humano, o zip mais novo de cada música em `saida\` e mostra por dificuldade as notas por segundo, a cobertura (ataques fortes que viraram nota), a precisão (notas que caem num ataque forte, 50 ms) e a correlação entre intensidade e notas por trecho. Rode antes e depois de cada mudança. Ponto de partida, 15 músicas (6 em Easy, 12 em Normal, 15 nas demais):

| Dificuldade | Notas | NPS | Cobertura | Precisão | Correlação |
|---|---|---|---|---|---|
| Easy | 229 | 1,16 | 38% | 68% | 0,75 |
| Normal | 416 | 1,80 | 62% | 68% | 0,84 |
| Hard | 545 | 2,50 | 72% | 59% | 0,73 |
| Expert | 755 | 3,48 | 84% | 52% | 0,75 |
| Expert+ | 917 | 4,26 | 89% | 48% | 0,65 |

13 de 15 passam em todas as conferências (falham: 1am-freestyle, NPS do Expert+; sk8er-boi-gerado, sabre atravessando a outra nota no Expert e Expert+). Pontos fora da curva: sk8er-boi tem precisão de 16 a 29% (ou o detector de ataques erra nela, ou o mapa foi gerado de outro áudio) e when-love-and-death-embrace tem correlação 0,12 no Expert+. Falta o resto do item: o conjunto fixo de 10 músicas com mapa humano e o teste cego.

### 1.1 Detector

**Feito em 10/10/2026**, um commit por item. Medido em 18 músicas (o zip mais novo de cada uma em `saida\`, regerado do `song.egg` com o código de antes e de depois; a análise sai do cache). Os números do `tools/medir.py`, antes → depois:

| Dificuldade | Notas | Cobertura | Precisão | Correlação |
|---|---|---|---|---|
| Easy | 262 → 259 | 47% → 47% | 73% → 73% | 0,83 → 0,88 |
| Normal | 389 → 390 | 62% → 62% | 67% → 66% | 0,87 → 0,91 |
| Hard | 540 → 534 | 72% → 70% | 62% → 61% | 0,76 → 0,82 |
| Expert | 747 → 748 | 85% → 83% | 55% → 53% | 0,78 → 0,83 |
| Expert+ | 910 → 917 | 90% → 88% | 51% → 49% | 0,68 → 0,75 |

Passam em todas as conferências: 16 de 18 → 18 de 18 (1am-freestyle e past-won-t-leave-my-bed caíam do piso de notas do Expert+).

O que os números dizem e o que não dizem:

- A cobertura e a precisão do `medir.py` só conhecem os ataques fortes da mixagem. Nota posta numa sílaba cantada sem ataque forte conta contra as duas. A queda de 2 pontos no Hard, Expert e Expert+ vem do item 1 (voz) e é esse efeito; nas músicas de voz longa ela é maior (in-joy-and-sorrow, Expert: 95% → 86%; back-to-you: 94% → 86%). É a troca que o item pedia, mas é uma perda no número do 1.0 e fica registrada como tal.
- A correlação subiu em todas as dificuldades, quase toda pelo item 3 (partes) e um pouco pelo 2 (prato de ataque vira dupla).
- A correlação por trecho mudou de conta no meio do caminho (`report.py`: 5 ms de folga na barra do compasso, porque a nota em cima da barra caía num trecho ou no outro pelo arredondamento). O "antes" da tabela já foi medido com a conta nova. Com a antiga, o ponto de partida era 0,81 / 0,85 / 0,74 / 0,77 / 0,67.
- Nenhum mapa foi jogado. O teste cego do dono e o conjunto com mapa humano (item 1.0) continuam faltando.

O que cada item mudou, com a medida própria dele (scripts de bancada, fora do repositório; mesmas 18 músicas; "antes" é o código de antes do bloco):

| Item | Medida | Antes | Depois |
|---|---|---|---|
| 1 Voz | sílabas cantadas que viraram nota (Hard / Expert / Expert+) | 47% / 60% / 67% | 49% / 66% / 76% |
| 1 Voz | notas em sílaba na linha que a altura da voz pede | 30 a 33% | 40 a 44% |
| 1 Voz | notas em sílaba cortando no sentido da melodia | 46 a 49% | 50 a 55% |
| 1 Voz | notas seguradas por mapa (Hard, Expert, Expert+) | 8 | 17 |
| 2 Bateria | notas de caixa na linha do meio | 16 a 28% | 36 a 44% |
| 2 Bateria | pratos de ataque com nota que saíram dupla (Hard / Expert / Expert+) | 25% / 36% / 38% | 68% / 50% / 48% |
| 4 Força | tamanho do golpe no quarto mais forte contra o mais fraco (Hard, em casas) | 1,44 contra 1,41 | 1,54 contra 1,37 |
| 5 BPM | maior distância entre a nota e a grade, com o tempo calculado pelo bsmap a partir dos eventos | – | 0,07 ms |

Limites conhecidos:

- **Voz.** A altura e o sentido são preferência na escolha do padrão; a paridade, os defeitos e o compasso repetido vêm antes. Por isso só 4 em cada 10 notas de sílaba ficam na linha pedida (ao acaso seriam 3). Para a voz mandar mais é preciso mexer na escolha do padrão, que é o bloco 1.2.
- **Bateria.** "Prato de ataque" é só os 10% de agudo que mais continuam soando; caixa aberta entra junto. Não há gabarito para conferir; o que confere é o bumbo cair nas batidas 1 e 3 e a caixa nas 2 e 4 nas músicas de rock, e cai.
- **Partes.** Refrão e drop são o mesmo rótulo ("queda"). Em música alta do começo ao fim quase tudo vira queda e o item não muda nada (take-a-bite, sojourn).
- **BPM.** Em 17 das 18 músicas o BPM não é fixo e a grade de um BPM só fugia de 0,06 a 56 s até o fim. Os mapas saem com 7 a 73 eventos de BPM. **Não conferido no jogo nem no ArcViewer**: só pelo bsmap. Onde o detector de batidas lê um trecho em tempo dobrado, o evento sai com o BPM dobrado (joseph vai de 117 a 326).
- A análise nova (voz, bateria, partes) acrescenta uns 5 a 25 s por música na primeira vez e fica em cache, um arquivo por camada (`voz.json`, `bateria.json`, `partes.json`), ao lado dos instrumentos separados. As partes e os eventos de BPM valem também no modo rápido; voz e bateria precisam dos instrumentos separados.

1. **Voz de verdade.** Na faixa de voz, seguir a altura cantada (pYIN do librosa) em vez de só o ataque: sílaba nova vira nota, melodia subindo ou descendo decide a altura e a direção do corte, nota longa cantada vira nota segurada.
2. **Bateria por peça.** Separar bumbo, caixa e pratos dentro da faixa de bateria (por faixa de frequência). Bumbo embaixo, caixa no meio, prato forte vira dupla.
3. **Partes da música.** Reconhecer introdução, verso, refrão, subida e queda. Subida vira sequência que acelera, queda vira o trecho mais cheio, pausa vira respiro de verdade. Hoje a intensidade é só por compasso.
4. **Força de cada ataque.** Ataque forte ganha dupla ou golpe largo; ataque fraco, golpe curto. Hoje a força decide se há nota, não como ela é.
5. **BPM variável.** Músicas que mudam de andamento saem sem eventos de BPM no mapa; o jogo e os editores mostram a grade errada.
6. Avaliar o modelo de seis faixas do Demucs (guitarra e piano separados). Custa mais tempo; só vale se o item 1.0 mostrar ganho. **Avaliado em 10/10/2026 e não adotado.** Em três músicas (koro-disco, sk8er-boi, born-to-die), com guitarra e piano entrando como candidatos: a cobertura ficou igual ou pior (born-to-die, Expert: 93% → 88%), a guitarra e o piano trouxeram só 2 a 3% de ataques fortes que as quatro faixas ainda não tinham (13 a 29 por música) e a faixa de voz do modelo de seis rendeu menos sílabas (5 a 9% a menos). O tempo de separação foi parecido (49, 72 e 94 s contra 40, 81 e 106 s, no processador, com outra carga rodando junto). O próprio Demucs avisa que a faixa de piano desse modelo é fraca.

### 1.2 Golpes mais humanos

**Feito em 10/10/2026**, um commit por item. Medido nas mesmas 18 músicas do 1.1 (o zip mais novo de cada uma em `saida\`, regerado do `song.egg`, sem preferências). Os números do `tools/medir.py`, antes do bloco → depois:

| Dificuldade | Notas | Cobertura | Precisão | Correlação |
|---|---|---|---|---|
| Easy | 259 → 261 | 47% → 47% | 73% → 73% | 0,88 → 0,87 |
| Normal | 390 → 391 | 62% → 62% | 66% → 66% | 0,91 → 0,91 |
| Hard | 534 → 537 | 70% → 70% | 61% → 61% | 0,82 → 0,82 |
| Expert | 748 → 754 | 83% → 83% | 53% → 53% | 0,83 → 0,83 |
| Expert+ | 917 → 932 | 88% → 88% | 49% → 49% | 0,75 → 0,76 |

Passam em todas as conferências: 18 de 18 antes e depois, sem preferências e com as do dono (`sem_topo`, `sem_fila`). Nenhum aviso de paridade.

O que os números dizem e o que não dizem:

- O `medir.py` só enxerga os tempos das notas, e este bloco quase não mexe neles: a tabela acima mostra que nada piorou, não que melhorou. As notas a mais são as pilhas. A correlação do Easy foi de 0,878 para 0,874 no bloco, 0,003 disso no item 5; as outras ficaram iguais ou subiram (Expert+ 0,748 → 0,755). Foi tratado como ruído e o item 5 ficou; é a única queda do bloco no `medir.py`.
- Por isso cada item tem medida própria (scripts de bancada, fora do repositório). A principal é nova: **trocas de posição raras**. Dos mil mapas humanos saem todas as trocas de posição da mesma mão (casa e direção de uma nota para a seguinte, até 4 batidas); as mais raras, que somam 2% do total, contam como "raras". Mapa humano tem 2% por definição. Notas seguradas ficam de fora da conta (o desenho delas é do bloco 1.3).
- Essa medida balança: no Easy ela foi de 2,3% a 3,0% entre os itens 1 e 3, que quase não mexem nele. Diferença de meio ponto não quer dizer nada.
- Nenhum mapa foi jogado. O botão novo da Configuração foi visto no navegador; o resto é número.

| Item | Medida | Antes | Depois |
|---|---|---|---|
| 1 Contexto | trocas de posição raras (Easy / Normal / Hard / Expert / Expert+) | 6,6% / 4,0% / 3,6% / 2,9% / 2,0% | 2,3% / 3,1% / 2,6% / 2,8% / 1,2% |
| 1 Contexto | Expert+: janelas que caíram na regra simples, e notas descartadas (soma das 18 músicas) | 43 e 47 | 30 e 26 |
| 2 Variação | janelas de compasso repetido que voltaram espelhadas (Easy / Normal / Hard / Expert / Expert+) | 0 | 207 / 147 / 145 / 143 / 150 |
| 2 Variação | janelas de compasso repetido com um acento a mais (mesma ordem) | 0 | 35 / 15 / 16 / 2 / 2 |
| 2 Variação | janelas de compasso repetido que reaproveitaram o desenho, em qualquer versão (Hard / Expert / Expert+) | 80% / 72% / 62% | 80% / 72% / 63% |
| 3 Pilhas | pilhas a cada mil notas (Hard / Expert / Expert+); nos mapas humanos a mediana é 6 / 16 / 30 e o quarto mais leve 0 / 3 / 11 | 0 | 2,6 / 6,6 / 13,1 |
| 3 Pilhas | torres (Expert, Expert+) | 0 | uma por mapa, em quase todos |
| 4 Cruzados | a cada mil notas, com as preferências do dono (Expert / Expert+) | 16,9 / 46,3 | pouco 5,7 / 18,2; nunca 0 / 0; livre 16,9 / 46,3 |
| 4 Cruzados | a cada mil notas, sem preferências (Expert / Expert+) | 9,8 / 25,7 | pouco 4,3 / 17,2 |
| 5 Qualidade | peso médio dos mapas de origem dos padrões escolhidos, de 0,5 a 2 (Hard / Expert / Expert+, em 6 músicas) | 1,35 / 1,33 / 1,30 | 1,41 / 1,40 / 1,37 |

"Antes" e "depois" de cada linha são o código logo antes e logo depois daquele item. No fim do bloco, com tudo junto, as trocas raras ficaram em 2,7% / 2,3% / 2,5% / 2,4% / 1,0%.

O que cada item faz:

- **1 Contexto.** Duas coisas. A emenda entre dois padrões agora é comparada com o que os mapas humanos fazem: troca de posição rara perde pontos (a tabela sai da própria biblioteca, sem arquivo novo). E os cinco melhores encaixes de cada janela são ensaiados até 8 batidas à frente; ganha o que deixa o resto da frase sair melhor. Só o ensaio, sem a tabela, deu empate com o ponto de partida; só a tabela deu 4,4% / 3,3% / 3,5% / 2,2% / 1,3%; os dois juntos, o resultado acima.
- **2 Variação.** Na 2ª, 6ª... vez que um compasso volta, o desenho vem espelhado (as mãos trocam de papel); na 3ª, 7ª..., com um acento a mais (a outra mão entra junto no ataque mais forte). Se a variação não cabe, vale o desenho igual, e depois o invertido na vertical, como antes.
- **3 Pilhas e torres.** Nos acentos mais fortes dos trechos intensos a nota ganha outra da mesma cor na casa vizinha, na linha do corte. Cota por dificuldade perto do quarto mais leve dos mapas humanos. Uma torre por mapa no Expert e no Expert+. A primeira versão punha as pilhas onde a mão estava livre, que é o trecho calmo, e a correlação caía (Expert 0,83 → 0,81); pesar o acento pela intensidade do compasso resolveu.
- **4 Braços cruzados.** Chave nova na Configuração, em "Seu jeito de jogar": Nunca, Pouco (padrão), Livre. "Pouco" é um teto de 8 cruzamentos a cada mil notas no Expert e 20 no Expert+ (o quarto dos mapas humanos que menos cruza). Na linha de comando, `--prefs cruzar_nunca` ou `cruzar_livre`.
- **5 Qualidade.** Na biblioteca, cada padrão pesa conforme a avaliação do mapa de onde veio (0,5 no pior avaliado dos mil, 2 no melhor, pela posição na fila) e guarda a qualidade média das fontes, que do Hard para cima soma pontos na escolha.

Limites conhecidos:

- **Contexto.** A voz perdeu um pouco: notas de sílaba na linha que a altura da voz pede foram de 45% para 43% no Hard e de 44% para 42% no Expert (o sentido do corte subiu de 54% para 59% no Hard). A emenda humana e a voz disputam os mesmos pontos. Desenho idêntico em compasso repetido também caiu um pouco (Expert+: 290 → 258 janelas), compensado pelo invertido.
- **Variação.** Desenho idêntico ao original caiu para a metade (no Hard, de 252 janelas para 139), porque metade das voltas agora vem espelhada: é o que o item pede, mas só jogando se sabe se o refrão continua reconhecível. O acento a mais quase não aparece no Expert e no Expert+ (2 em 18 músicas): ele só cabe onde a outra mão não bate mais na janela, e nessas dificuldades as duas mãos se alternam o tempo todo. Lá o acento vem das pilhas.
- **Torres.** Mapper humano quase não usa (0,1 a 0,2 a cada mil notas, mais ou menos uma a cada sete mapas). Aqui sai uma por mapa porque o item pede; se incomodar, é um trecho curto para tirar (`empilhar` em `generate.py`). Com "sem notas na linha de cima" não há torre, porque ela ocupa as três linhas.
- **Cruzados.** Com as preferências do dono ligadas, segurar os braços custa encaixe no Expert+: as janelas resolvidas pela regra simples sobem de 148 para 223 (soma das 18 músicas, uns 4 a mais por mapa) e as notas descartadas de 106 para 138. Com "nunca", 293 e 148.
- **Qualidade.** O efeito é pequeno: os mil mapas têm avaliação entre 0,96 e 0,99, então há pouco o que separar. No Easy e no Normal o peso na escolha ficou desligado: com ele as trocas raras subiam (Easy 3,0% → 4,1%, Normal 2,2% → 2,7%) e o ganho de qualidade era de 0,02 a 0,04. Quem já tem a biblioteca instalada continua com a antiga, que funciona igual, sem o peso; para ganhar o peso é preciso montar de novo (`tools\extract_patterns.py`, um minuto, precisa de `dados\mapas`). Nesta máquina já foi montada.
- Corrigido no caminho: o motor conferia braço cruzado com uma janela curta demais e sem folga de arredondamento, e em música de 150 BPM (batida de exatamente 0,4 s) podia escapar um cruzamento no Hard.

1. **Contexto maior.** Escolher o trecho olhando 8 batidas e o que vem depois, não só o encaixe com o estado atual dos braços.
2. **Motivo e variação.** Refrão repete o desenho (já faz), mas a segunda vez pode vir espelhada ou com um acento a mais, como mapper faz.
3. **Vocabulário que falta.** Torres e pilhas em acento; correntes, bombas e paredes estão no bloco 1.3.
4. **Braços cruzados sob controle.** Com as preferências ligadas eles dobram no Expert+ (medido). Virar um botão: nunca, pouco, livre.
5. **Peso por qualidade.** Na biblioteca, trecho de mapa mais bem avaliado pesa mais; hoje pesa a frequência.

### 1.3 Mapa mais bonito: usar mais do que o jogo oferece

Pedido do dono: melhorar o mapa, deixar mais bonito, usar mais recursos do próprio Beat Saber. Antes deste bloco o mapa usava notas, arcos, paredes de enfeite e luzes básicas, num ambiente só.

**Itens 1 a 5 feitos em 10/10/2026**, um commit por item. Conferido nas mesmas 18 músicas dos blocos 1.1 e 1.2 (regeradas do `song.egg`, com as preferências do dono): 18 de 18 passam em todas as conferências com os cinco itens juntos; depois de cada item, as 2 a 4 músicas regeradas também passaram. As notas não mudam neste bloco, então o `tools/medir.py` não tem o que medir aqui. **Nenhum mapa foi visto no jogo**: o que há abaixo é contagem e validação de formato (bsmap). Se ficou bonito, só o dono consegue dizer.

Conferido no Quest do dono antes do item 2 (só leitura, por ADB): Beat Saber 1.40.8, SongCore com as três chaves ligadas (cores de nota, de parede e de ambiente vindas do mapa). O dono joga com cores próprias ligadas no jogo (`overrideDefaultColors`); pelo código do SongCore do Quest, as cores gravadas no mapa (`_customData` de cada dificuldade: `_envColorLeft`, `_envColorRight`, os dois `...Boost`, `_colorLeft`, `_colorRight`) entram por cima do esquema escolhido, inclusive o do jogador. Isso foi lido no código, não visto no jogo. Não é preciso ligar nada. O jogo não está com cenário forçado (`overrideEnvironments` desligado), então o cenário do mapa vale. Chroma e Noodle Extensions estão instalados (serve ao item 10).

| Item | Medida (18 músicas) | Antes | Depois |
|---|---|---|---|
| 1 Luzes | o que decide a luz | intensidade do compasso e a batida | parte da música, peça da bateria, intensidade |
| 1 Luzes | compassos de pausa no escuro | 0 | 51 |
| 2 Cores | mapas com cores próprias gravadas (das 11 capas de verdade) | 0 | 11 |
| 2 Cores | capas com dois tons a 60 graus ou mais um do outro | – | 1 de 11; nas outras o segundo tom é o oposto do primeiro |
| 2 Cores | capas cujo par serve para sabre e nota (90 graus ou mais) | – | 10 de 11 |
| 3 Cenário | clima: calmo / pesado / eletrônico | um cenário só | 7 / 9 / 2 |
| 4 Reação | entradas de queda com apagão logo antes | 0 | 33 de 37 |
| 4 Reação | compassos de subida acendendo aos poucos | 0 | 111 |
| 4 Reação | paredes, soma dos mapas (Easy / Normal / Hard / Expert / Expert+) | 69 / 88 / 55 / 32 / 29 | 87 / 131 / 75 / 45 / 36 |
| 5 Luzes novas | mapas em cenário novo, aceso por grupos de luzes | 0 | 7 de 18 (The Second 4, Rock Mixtape 2, Weave 1) |

O "antes" das paredes são os zips que estavam em `saida\`, feitos em momentos diferentes; parte da diferença pode vir das notas, não só do corredor.

O que cada item faz (o código está em `beatloom/luzes.py`):

- **1 Luzes.** O gerador escreve "deixas" (em que segundo, qual luz, o que ela faz, em que cor, com que brilho) e só no fim elas viram evento do mapa. Introdução e verso: fundo aceso numa cor, com brilho conforme a intensidade, anéis pulsando no bumbo. Queda: a outra cor, tudo aceso, lasers dos dois lados trocando de cor a cada compasso e batendo na caixa, anéis girando e abrindo, clarão branco na entrada. Pausa: escuro. Prato de ataque: clarão branco no centro. Velocidade dos lasers conforme a intensidade. No modo rápido (sem a bateria separada) o pulso vai na batida.
- **2 Cores.** Da capa saem dois pares: o do mapa e o do reforço ("boost"), que entra em cada queda e sai no fim dela. Luzes sempre com as cores da capa; sabres e notas só com a chave ligada (Configuração, "Seu jeito de jogar", e o diálogo de mapa novo; `--prefs sabres_capa`) e só quando os dois tons estão a 90 graus ou mais na roda de cores. Capa cinza (menos de 8% de pixels com cor) e capa genérica ficam com as cores do jogo. "Refazer as notas" de um mapa passa a levar a capa dele ao gerador.
- **3 Cenário.** Três climas, por três números: andamento de máquina ou bateria com 60% ou mais do volume = eletrônico; som com muito ruído (guitarra distorcida, pratos) = pesado; o resto = calmo. Guardado em `clima.json` no cache. Refazer uma dificuldade só mantém o cenário do mapa (`--ambiente`); refazer o mapa inteiro adota o novo.
- **4 Reação.** A subida começa quase apagada e acende batida a batida (fundo, depois anéis, lasers, centro e o giro dos anéis, que dobra no último compasso). Na última batida antes da queda (ou meia batida), se não há ataque forte ali, apaga tudo. Os anéis giram no bumbo em vez de na batida. Na entrada de cada queda, uma parede em cada ponta onde aquela ponta está livre de notas.
- **5 Luzes novas.** Cada clima tem dois cenários, um clássico (eventos básicos) e um novo (grupos de luzes): calmo Big Mirror ou The Second, pesado Green Day ou Rock Mixtape, eletrônico Monstercat ou Weave. A música decide qual (pelo hash do áudio, sempre o mesmo para a mesma música). Nos novos, as mesmas deixas viram eventos de cor nos grupos que fazem cada papel e um leque de rotação nos lasers. A conferência passou a contar esses eventos em "eventos de luz".

Limites conhecidos e decisões que fogem do texto original:

- **Cores: mudei uma garantia.** O item dizia "capa de uma cor só cai nas cores padrão". Medido: 10 das 11 capas de verdade têm um tom só, então a regra apagava o item quase inteiro. Agora o tom da capa fica e o segundo é o oposto dele na roda de cores. Se o dono preferir a regra original, é uma linha em `paleta` (`beatloom/luzes.py`).
- **Cores.** A cor sai com brilho cheio e saturação de 70% para cima, então capa escura dá luz viva do mesmo tom, não a cor exata da capa. A miniatura do vídeo vale como capa (é o que o download guarda). A ficha do mapa ainda não mostra as cores; o relatório em texto mostra. Mapa antigo de capa genérica não tem a origem da capa anotada e fica com as cores do jogo ao refazer.
- **Cenário.** Os três limites saíram destas 18 músicas, sem gabarito. Indie de guitarra limpa cai em "calmo" (take-a-bite, a 182 BPM, está em calmo).
- **Reação.** O apagão sai em quase toda queda (33 de 37), porque meia batida sem ataque forte é comum; "no silêncio" ficou mais largo do que o item pedia. O corredor de paredes quase não cabe do Hard para cima com as preferências do dono: as pontas estão sempre ocupadas, então sai uma parede de cada lado em momentos diferentes, e às vezes nenhuma. Corredor de verdade pediria parede fora das quatro colunas (não conferido se o jogo aceita sem mod) ou o motor de golpes deixar as pontas livres nesse trecho. "Cada parte com a sua cara" vale por tipo de parte (verso, queda...): dois versos diferentes têm a mesma luz.
- **Luzes novas: o maior risco do bloco.** Os números dos grupos vêm da tabela do bsmap e o formato passa no validador, mas nada disso foi visto aceso. Se um cenário novo sair apagado ou estranho no jogo, tirar ele de `AMBIENTE` (uma linha) devolve aquelas músicas ao cenário clássico. Nos cenários novos o mapa vai sem eventos básicos, então o visualizador da página pode mostrar essas músicas sem luz. Zoom dos anéis e velocidade dos lasers não existem nos grupos.
- Não conferido aqui: "Refazer as notas" pela página com os itens novos (só as funções por trás foram testadas) e o caderno do Colab. A chave nova foi vista no navegador, no diálogo de mapa novo e na Configuração.

**Itens 6 e 7 feitos em 10/10/2026**, um commit por item. Medido em 17 músicas regeradas do `song.egg` com as preferências do dono (`sem_topo`, `sem_fila`), antes, depois do item 6 e depois do item 7. As notas não mudam (nenhuma nota entra, sai ou troca de lugar), então o `tools/medir.py` deu o mesmo nas três rodadas: Easy 264 notas, Normal 391, Hard 534, Expert 750, Expert+ 919 em média, com os mesmos números de acerto no ataque. 17 de 17 passam em todas as conferências antes e depois, com e sem as preferências, e nenhuma tem erro de paridade. **Nada disso foi visto no jogo.**

| Item | Medida (17 músicas) | Antes | Depois |
|---|---|---|---|
| 6 Arcos | a cada mil notas, Hard / Expert / Expert+ (mediana humana: 59) | 33 / 24 / 16 | 68 / 52 / 41 |
| 6 Correntes | a cada mil notas, Hard / Expert / Expert+ | 0 | 1,5 / 1,2 / 2,5 |
| 7 Bombas | soma dos mapas, Hard / Expert / Expert+ | 0 | 36 / 23 / 25 |
| 7 Paredes de desviar | soma dos mapas, Easy / Normal / Hard / Expert / Expert+ | 0 | 64 / 40 / 20 / 12 / 11 |
| 7 Paredes de agachar | soma dos mapas, sem a preferência "sem notas na linha de cima" | 0 | 13 / 6 / 5 / 2 / 2 |

O que cada item faz (o código está em `generate.py` e `beatloom/engine.py`):

- **6 Arcos seguindo a voz** (`arcos_de_frase`). Quando a mesma mão bate duas vezes enquanto o cantor segura a mesma nota, de 1 a 4 batidas entre os dois golpes, um arco liga as duas notas. Sai no sentido do primeiro corte e chega no do segundo, que é o caminho que o braço já faz. Até 40 a cada mil notas, os mais longos primeiro.
- **6 Correntes** (`acorrentar`). No ataque seco (forte, nada na meia batida seguinte, sem voz segurando) a nota vira a cabeça de uma corrente de 4 elos, 1 casa na linha do corte, como nos mapas humanos da biblioteca. O golpe é o mesmo. Só do Hard para cima, até 4, 6 e 8 a cada mil notas, e só onde a cauda cabe na grade e nenhuma nota passa por ali em 0,4 segundo.
- **7 Bombas de reinício** (`engine.reiniciar`). Na volta de um respiro (mão parada há 2 batidas e 1,2 segundo ou mais) num ataque forte, a mão que iria subir ganha uma bomba embaixo, na coluna do meio dela, uma batida antes, e o golpe da volta desce. Toda bomba do conjunto tem corte para baixo antes e depois. Do Hard para cima, até uma a cada 30 segundos.
- **7 Paredes** (`desvios`, `paredes`). Nos respiros mais longos, paredes de desviar que começam numa batida e trocam de lado a cada 0,75 segundo ou mais, até 4 por respiro e uma a cada 45 segundos de música. A última de uma fila pode ser de agachar (até 2 por mapa); com "sem notas na linha de cima" não sai nenhuma de agachar. Respiro que tem bomba de reinício fica só com parede de enfeite.

Limites conhecidos:

- Correntes ficaram raras (1 a 3 a cada mil notas; nos humanos metade dos mapas não tem nenhuma e o quarto de cima tem de 6 a 10). O que segura é a regra de ataque seco e a casa da cauda livre, não a cota.
- A bomba só aparece na volta de um respiro. Bomba no meio de um trecho com notas, e parede entre notas, o gerador não faz.
- Com as preferências do dono o Easy é quem mais ganha paredes de desviar (64 nas 17 músicas), porque é onde há mais respiro longo. A cota era uma a cada 20 segundos e caiu para 45 porque o Easy saía com 7 por mapa.
- O relatório em texto conta arcos, correntes, bombas e paredes; a ficha do mapa na página não.

1. **Luzes de verdade.** Seguir as partes da música (item 1.1.3): cor por seção, pulso no bumbo, clarão no acento, apagar na pausa, anéis girando e abrindo na queda, velocidade dos lasers conforme a intensidade. É o que mais muda a cara do mapa.
2. **Cores da música** (pedido do dono). Tirar da capa (ou da miniatura do vídeo) as duas cores dominantes que mais contrastam entre si e gravar como cores do mapa. Hoje toda luz sai vermelha e azul.
   - Luzes sempre com as cores da capa; sabres e notas com elas só se a pessoa ligar (opção na Configuração e no diálogo de mapa novo), porque cor de sabre é gosto e precisa de contraste para ler a nota.
   - Sem mod o jogo dá mais do que duas cores de luz: as duas do ambiente, as duas do modo "boost" (trocadas por evento) e o branco. Usar o boost no refrão e na queda com um segundo par tirado da capa; o branco fica para o clarão do acento.
   - Garantias: as duas cores nunca parecidas demais entre si nem escuras demais; capa cinza ou de uma cor só cai nas cores padrão.
   - A conferir antes: se o SongCore do Quest respeita as cores gravadas no mapa e se o jogador precisa ligar algo nas opções do jogo.
3. **Ambiente por música.** Escolher o cenário do jogo conforme o clima (calmo, pesado, eletrônico) em vez de um fixo.
4. **O mapa reage à música** (pedido do dono: mais bonito, mais "interativo", mais a ver com a música). O que já agrada fica e cresce: escuro na parte lenta, luz caindo na queda. Somar: subida que vai acendendo aos poucos até estourar na queda, apagão seco no silêncio antes dela, paredes abrindo um corredor no refrão, anéis e lasers no pulso do bumbo, e cada parte da música com uma cara própria que volta quando a parte volta.
5. **Luzes novas (v3).** Os ambientes recentes usam grupos de luzes com eventos de cor, rotação e translação; sem eles esses cenários ficam apagados.
6. **Correntes e arcos melhores.** Correntes (burst sliders) em ataque seco e arcos seguindo a nota cantada (item 1.1.1), com curva que acompanha o braço.
7. **Bombas e paredes com função.** Bomba para forçar o reset do braço, parede para fazer desviar e agachar no ritmo, com parcimônia e respeitando as preferências.
8. **Um Braço, 360 e 90 graus.** Modos do próprio jogo que o gerador ainda não faz. O de um braço é o mais barato.
9. **Velocidade por trecho.** NJS e distância de salto ajustados à dificuldade (já faz) e eventos de BPM para a grade acompanhar (item 1.1.5).
10. **Com mods, opcional** (o dono tem Chroma e Noodle Extensions no Quest). Regra: desligado por padrão e nada que pese no óculos. Na Configuração do Beatloom, em "Seu jeito de jogar", uma chave para cada mod ("Tenho Chroma", "Tenho Noodle Extensions"); ligada, os mapas novos e os refeitos passam a usar o mod; desligada, sai o mapa padrão de sempre. A ficha do mapa mostra com quais mods ele foi feito.
   - **Chroma, como sugestão e não exigência**: quem não tem o mod joga o mesmo mapa com as cores do item 2. Com ele: qualquer cor em cada evento de luz, então a paleta inteira da capa (4 ou 5 cores) em vez de dois pares; degradê de uma cor a outra na subida; cor diferente por parte da música; acender luzes uma a uma em vez do grupo todo. É cor em evento que já existe, então não custa desempenho.
   - **Chroma, mais caro, só depois de medir no Quest**: esconder ou mexer em peças do cenário, cor por nota.
   - **Noodle Extensions, como exigência** (sem o mod o mapa nem abre, então sai como um conjunto de dificuldades à parte, nunca no lugar do normal). Só o leve: nota que nasce de outro ponto ou faz uma curva curta na chegada em momentos marcados, parede fina de enfeite acompanhando a melodia. Fora: arte de parede com centenas de peças, notas falsas, animação longa de trilha. É o que trava o Quest e atrapalha a leitura.
   - A conferir antes: que versões dos dois mods o Beat Saber do dono tem e o que elas aceitam; limite de paredes e de eventos por segundo que o Quest aguenta sem cair de quadros.
   - **Feito em 10/10/2026, os dois (`beatloom/mods.py`), ainda não visto no jogo.** Conferido no Quest por ADB, só leitura: Chroma 2.10.3 (com "Custom Color Events" ligado), Noodle Extensions 1.6.3, Tracks 2.5.4, CustomJSONData 0.24.5, no Beat Saber 1.40.8; todos leem o `customData` do formato v3 que o gerador escreve. Os mods entram como última etapa, sobre o mapa pronto. Com as duas chaves desligadas nenhum arquivo é tocado: o zip sai idêntico, byte a byte, ao do gerador anterior (medido em born-to-die). As chaves são mais dois gostos (`chroma` e `noodle` em `beatloom.json` e em `--prefs`), então valem para mapa novo, para "Refazer" e para refazer uma dificuldade só. A ficha lê do próprio `Info.dat` com quais mods o mapa foi feito.
     - **Chroma.** Cada evento básico de luz ganha a cor do Chroma (`customData.color`) e cada dificuldade a sugestão `Chroma`. Cada parte tem o seu par, tirado dos quatro tons da capa: introdução com o terceiro e o quarto tons, verso com o segundo e o terceiro, queda com os dois mais fortes. Na subida cada luz acende uma vez e depois só muda por eventos de transição, indo do par da parte anterior ao da queda pela roda de cores (em RGB o meio do caminho entre duas cores opostas é cinza). Branco, apagar, anéis e lasers ficam como estão. Em born-to-die: 605 dos 1073 eventos de luz com cor, 102 deles de transição; fora as luzes e o cenário, o mapa é o mesmo.
     - **Chroma: decisão que foge do texto.** Só os eventos básicos aceitam cor por evento; os grupos de luzes dos cenários novos (item 5) não. Então, com a chave ligada, o cenário é sempre o clássico do clima (Big Mirror, Green Day ou Monstercat). Refazer uma dificuldade só de um mapa de cenário novo deixa as luzes dela como estão.
     - **Chroma, ficou de fora:** acender luzes uma a uma (os números de cada luz mudam de cenário para cenário e não há como conferir sem ver no jogo), quinta cor (a paleta da capa tem quatro) e tudo do item "mais caro". Capa genérica não tem paleta: o mapa sai sem as cores do Chroma.
     - **Noodle Extensions.** Um segundo conjunto de dificuldades, `Lawless` (a característica do SongCore para mapa fora do padrão), com a exigência `Noodle Extensions`: cópia de cada dificuldade normal, que não é tocada (conferido: com só esta chave, os arquivos normais saem idênticos). Dois efeitos. Chegada: a nota que cai na cabeça de um compasso da queda, ou do primeiro compasso de cada parte, nasce 2 casas para fora do lado da sua mão e 1 acima, e está no lugar com um quarto do caminho andado (animação da própria nota, sem trilha); ponta de arco e cabeça de corrente não entram. Enfeite: cada nota cantada de meia batida ou mais vira uma barra fina de cada lado, fora das quatro colunas, na altura da nota, sem encostar em ninguém; no máximo 60 notas, 120 paredes por dificuldade. Em born-to-die: de 61 (Easy) a 72 (Expert+) notas com chegada; em if-the-sun-burns-out-tonight, de 27 a 34. No modo rápido sem a voz separada, só a chegada.
     - **Conferência.** O relatório passou a validar o esquema dos arquivos do conjunto a mais (bsmap) e reprova o mapa se um deles for inválido; as regras de jogabilidade valem pelo conjunto normal, que tem as mesmas notas. Passou com cada chave ligada, com as duas e com nenhuma. A página ainda não mostra esse resultado (só o `.relatorio.txt`), nem lista o conjunto a mais nas abas de dificuldade.
     - **Não conferido:** nada disto foi visto no jogo. Em especial: se o Chroma do Quest respeita a cor nos eventos de transição, se a posição das barras fica boa de ver, se 120 paredes pesam, e se o ArcViewer mostra as cores e os efeitos. A chave foi vista na Configuração e a ficha mostrou "Feito com Chroma, Noodle Extensions"; ligar a chave pela página e gerar por ela não foi feito (só o gerador direto). Os dois pedidos prontos deste item, mais abaixo, ficaram sem função.
11. **Escolher o que vai no mapa** (pedido do dono, a partir da tela do Beat Sage). No diálogo de mapa novo, além das dificuldades:
   - Modos de jogo: Padrão (já faz), Sem Setas, Um Sabre, 90 Graus, 360 Graus. Cada modo marcado sai como mais um conjunto de dificuldades no mesmo mapa. Sem Setas é o mais barato (as mesmas notas, sem direção); Um Sabre e os de giro são os do item 8.
   - O que entra: bombas, notas sem direção (ponto), paredes, luzes dinâmicas. Cada um liga e desliga; o padrão de cada um fica guardado na Configuração, junto das preferências, e vale também no "Refazer as notas".
   - Só aparece na tela o que o gerador já sabe fazer; nada de opção cinza prometendo o que não existe.
