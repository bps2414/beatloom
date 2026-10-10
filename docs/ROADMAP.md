# Roadmap

Escrito em 10/10/2026, depois das quatro fatias do redesenho ([plan/README.md](plan/README.md)). A ordem dentro de cada bloco é a sugerida. Nada aqui está decidido além do bloco 1, que o dono pediu como próxima etapa.

## 1. Próxima etapa: ouvir melhor a música e mapear mais como gente

Pedido do dono: detector melhor, mapa mais humano, mais intenso e mais realista; vocais melhor detectados; "sentir" a música; notas mais coerentes.

Como está hoje (depois dos blocos 1.1 e 1.2), para saber de onde se parte: batidas pelo beat_this, ataques pelo librosa na música inteira e em cada uma das quatro faixas do Demucs (bateria, baixo, voz, resto), altura cantada pelo pYIN, peças da bateria por faixa de frequência, partes da música (intro, verso, subida, queda, pausa), intensidade por compasso, e os golpes vêm de trechos de 1, 2 ou 4 batidas tirados de mapas humanos, escolhidos ensaiando 8 batidas à frente; compasso repetido reaproveita o desenho, espelhado ou com um acento a mais nas voltas; pilhas nos acentos; braços cruzados com teto.

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

Pedido do dono: melhorar o mapa, deixar mais bonito, usar mais recursos do próprio Beat Saber. Hoje o mapa usa notas, arcos, paredes de enfeite e luzes básicas, num ambiente só.

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
11. **Escolher o que vai no mapa** (pedido do dono, a partir da tela do Beat Sage). No diálogo de mapa novo, além das dificuldades:
   - Modos de jogo: Padrão (já faz), Sem Setas, Um Sabre, 90 Graus, 360 Graus. Cada modo marcado sai como mais um conjunto de dificuldades no mesmo mapa. Sem Setas é o mais barato (as mesmas notas, sem direção); Um Sabre e os de giro são os do item 8.
   - O que entra: bombas, notas sem direção (ponto), paredes, luzes dinâmicas. Cada um liga e desliga; o padrão de cada um fica guardado na Configuração, junto das preferências, e vale também no "Refazer as notas".
   - Só aparece na tela o que o gerador já sabe fazer; nada de opção cinza prometendo o que não existe.

### 1.4 Ferramentas de terceiros a aproveitar

- [BeatSaber-JSMap](https://github.com/KivalEvan/BeatSaber-JSMap) (o pacote `bsmap`) já é usado em `check\` para validar o formato, e as regras de paridade e de mapa em `beatloom/checks.py` foram portadas dele e do BeatSaber-MapCheck. Falta aproveitar: as outras checagens do MapCheck que ainda não foram portadas, e a conversão de formato (gravar em v4).
- Estimadores de dificuldade da comunidade (estrelas do BeatLeader e do ScoreSaber) para calibrar se o nosso Expert+ é mesmo um Expert+.
- **Pesquisar o que mais existe** (pedido do dono), antes de escrever do zero cada item dos blocos 1.1 a 1.3. Candidatos a avaliar, nenhum ainda testado aqui: reconhecimento de partes da música (all-in-one, MSAF), transcrição de melodia e voz (basic-pitch, CREPE), separação de bateria por peça, outros geradores para comparar e aprender (Beat Sage, de 2020, rede neural, código fechado; TopMapper, que também faz luzes; InfernoSaber e DeepSaber, a confirmar; o Mapperatorinator é do osu! e só serve de ideia), conferência de paridade (JoshaParity), geradores de luzes (Lightmap do ChroMapper, Lolighter) e as ferramentas de script de mapa (ReMapper, Heck). Para cada um anotar: licença, peso da instalação, se roda sem GPU, e o ganho no conjunto do item 1.0.

### Pedidos prontos

Um por sessão, para colar como está, na ordem sugerida. Todos em Opus 5.5, esforço médio (escolha do dono, 10/10/2026).

1.0: feito em 10/10/2026 (`tools/medir.py`), não precisa rodar de novo.

1.1: feito em 10/10/2026, não precisa rodar de novo. Resultados no bloco 1.1.

Atualizar os mapas antigos de uma vez, bloco 3 item 9 (bom logo depois do 1.1, antes de refazer a lista toda):

```text
Roadmap bloco 3 item 9 (atualizar os mapas antigos de uma vez, análise em camadas, só as luzes, mapa travado): meça primeiro com tools/timing.py o que o cache guarda e o que roda de novo, depois faça. Atualize o roadmap, commit e push ao final.
```

1.2: feito em 10/10/2026, não precisa rodar de novo. Resultados no bloco 1.2.

1.3, primeira parte (luzes, cores da capa, ambiente, o mapa reagindo à música: itens 1 a 5):

```text
Execute os itens 1 a 5 do bloco 1.3 do roadmap, um por vez. Antes do item 2, confira se o Beat Saber do Quest respeita as cores gravadas no mapa. A cada item: confira que o mapa passa na conferência e faça commit. Não pare para aprovar entre itens. No fim, atualize o roadmap, push, e me diga duas músicas para eu ver.
```

1.3, segunda parte (correntes e arcos, bombas e paredes, modos de jogo, opções do mapa: itens 6 a 9 e 11):

```text
Execute os itens 6, 7, 8, 9 e 11 do bloco 1.3 do roadmap, um por vez. No item 11 só aparece na tela o que o gerador já sabe fazer. A cada item: meça com tools/medir.py, confira que o mapa passa na conferência e faça commit. Não pare para aprovar entre itens. No fim, atualize o roadmap, push, e me diga duas músicas para eu testar.
```

1.3 item 10, Chroma (depois da primeira parte do 1.3):

```text
Roadmap 1.3 item 10, só o Chroma como sugestão: chave "Tenho Chroma" na Configuração, desligada por padrão; ligada, o mapa usa a paleta da capa, degradê e cor por parte da música; desligada, o mapa sai igual ao de hoje. Confira antes que versão do Chroma o Quest tem. Atualize o roadmap, commit e push ao final.
```

1.3 item 10, Noodle Extensions (por último, e só se o Chroma tiver agradado):

```text
Roadmap 1.3 item 10, só o Noodle Extensions leve: chave "Tenho Noodle Extensions" na Configuração, desligada por padrão; ligada, o mapa ganha um conjunto de dificuldades a mais com os efeitos leves do roadmap, sem tocar nas dificuldades normais. Nada de arte de parede nem nota falsa. Atualize o roadmap, commit e push ao final.
```

1.4 (pesquisa, a qualquer hora):

```text
Roadmap 1.4: pesquise as ferramentas de terceiros da lista e diga quais valem a pena e para qual item. Sem código, só atualize o roadmap, commit e push.
```

Versões de um mapa, bloco 3 item 8:

```text
Roadmap bloco 3 item 8 (versões de um mapa): confira primeiro como o envio ao Quest nomeia a pasta e se o jogo mantém a pontuação quando o mapa muda, depois faça. Atualize o roadmap, commit e push ao final.
```

Comparar com os outros geradores (opcional; o dono põe antes os zips do Beat Sage e do TopMapper numa pasta):

```text
Roadmap 1.0, comparar com os outros geradores: os zips deles estão em <pasta>. Passe pela conferência e pelo tools/medir.py ao lado dos nossos das mesmas músicas e me mostre a tabela. Sem mudar o gerador. Atualize o roadmap, commit e push.
```

Para proteger as músicas que já ficaram boas, acrescente a qualquer pedido: "Estas músicas ficaram perfeitas: <nomes>. Se o mapa delas mudar muito, me mostre antes de manter."

## 2. Pendências do que já foi feito

- Instalador nunca testado numa máquina limpa (instalar, atalho, preparo, gerar, desinstalar).
- Caderno do Colab/Kaggle nunca rodou de verdade; é também o primeiro teste do caminho da placa NVIDIA.
- Botões novos da página (fila, refazer as notas, marcar todos, mandar os que faltam) não foram vistos num navegador por quem os escreveu.
- Decisões do dono em aberto: DirectML na RX 6600, 300 ou 1000 mapas na biblioteca, apagar `dados\mapas` depois de montar.
- Nunca conferido: envio real ao Quest em lote, telas da primeira vez no visual novo.

## 3. Uso no dia a dia

1. **Página e servidor de versões diferentes.** Aconteceu: a página nova falando com o servidor antigo. A página deve perceber e pedir para reabrir o Beatloom.
2. **Aviso de versão nova**, com o link da release.
3. **Playlist no jogo.** Gravar um `.bplist` com os mapas gerados para eles aparecerem agrupados no Quest.
4. **Fila.** Cancelar a música que está rodando, reordenar.
5. **Preferências por mapa**, além das gerais; e uma versão mais branda da linha de cima (só proibir corte para baixo lá).
6. **Quest.** Apagar vários de uma vez.
7. Mostrar na ficha do mapa com quais preferências ele foi feito.
8. **Versões de um mapa** (pedido do dono). Refazer um mapa e mandar ao Quest deve trocar a música que já está lá, não criar outra na lista do jogo: mesma pasta e mesmo nome no óculos a cada envio. No computador, cada versão anterior fica guardada (numerada, com data e com o que mudou: modo, preferências, versão do Beatloom), e a ficha do mapa deixa voltar a uma delas ou apagar as antigas. A conferir antes de fazer: como o envio nomeia a pasta hoje e se o jogo mantém a pontuação quando o conteúdo do mapa muda.
9. **Atualizar os mapas antigos de uma vez** (pedido do dono: não ter que regerar música por música a cada melhoria do gerador).
   - Cada mapa já guarda com que versão do gerador foi feito. A lista mostra quantos estão atrás da versão atual e um botão só: "Atualizar os N mapas antigos". Usa a fila e o "Refazer as notas" que já existem.
   - Análise guardada em camadas: separação dos instrumentos (a parte cara, que quase nunca muda), ataques e batidas, e o que cada melhoria acrescenta (voz, partes da música). Mudou uma camada, só ela e as de cima rodam de novo. Hoje qualquer mudança na análise joga fora o conjunto e separa tudo outra vez. A conferir antes: o que o cache guarda hoje e quanto tempo cada camada leva (`tools/timing.py`).
   - Só as luzes: quando a melhoria for só de luzes ou cores, refazer só elas e deixar as notas como estão. Protege o mapa que já ficou bom de jogar.
   - Mapa "travado": marcar um mapa de que se gosta para as atualizações em lote não tocarem nas notas dele.
   - Anda junto com o item 8: a versão anterior fica guardada antes de atualizar.

## 4. Projeto

- Rodar os `--demo` e o `tools/check_i18n.py` na CI a cada push.
- Notas de release agrupadas (novidades, correções) em vez da lista crua de commits.
- Assinar o instalador, para o SmartScreen não assustar. Custa um certificado.

## Fora do roadmap

O que as decisões em [plan/README.md](plan/README.md) deixam de fora: hospedar como serviço, embutir a biblioteca de padrões, terceiro idioma, tema claro, Linux e Mac como alvo de usuário final.
