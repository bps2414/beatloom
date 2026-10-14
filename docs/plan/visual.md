# Visual dos mapas

Pedido do dono em 14/10/2026: "expandir o nível visual dos mapas; em alguns mapas, tipo do Green Day, fica o nome deles escrito, queria que ficasse o do artista da música que está tocando; e elevar mesmo a experiência visual para quem tem Chroma e algum outro mod". Depois, na mesma conversa: "pode ser assim, artista grande e música embaixo, começa todos os níveis até o final", "vai muito fundo, cada mapa com experiência fodástica, total liberdade". O dono está fora de casa e valida no Quest quando voltar.

**Estado: feito em 14/10/2026, os quatro níveis e o "refazer só as luzes". Nada foi visto no jogo.** O formato passa no bsmap e na conferência; o resto é o dono no Quest, começando pelos mapas de prova (ver "Como conferir no Quest").

## O que causava o "Green Day" escrito

O cenário saía de um par por clima, e o par do clima pesado era (Green Day, Rock Mixtape); o do eletrônico, (Monstercat, Weave). Com a chave do Chroma ligada valia sempre o primeiro do par, porque só os cenários clássicos aceitam cor por evento. Então, com Chroma, toda música pesada ia para o palco do Green Day, com o nome da banda escrito no fundo, e toda eletrônica para o do Monstercat.

## O que foi feito

### Nível 1: cenário e letreiro

- **Sorteio sem nome de banda** (`luzes.AMBIENTE`). Cada clima tem dois clássicos e um novo, nenhum com nome de banda ou gravadora: calmo (Big Mirror, Origins, The Second), pesado (Triangle, Kaleidoscope, Rock Mixtape), eletrônico (Nice, FitBeat, Weave). Com Chroma, sorteia entre os dois clássicos (antes era sempre o mesmo).
- **Palco da própria banda** (`luzes.BANDA`, `luzes.banda`). Música de Green Day, Linkin Park, BTS, Imagine Dragons, Panic! at the Disco, Timbaland, Skrillex, Billie Eilish, K/DA ou Noisestorm vai para o palco dela, com o letreiro certo. Vale qualquer nome do artista ("Linkin Park & Steve Aoki", "BTS (방탄소년단)"). Nesses palcos os eventos 8 e 9 querem dizer outra coisa (chuva e sol da Billie, modo dos lasers do Linkin Park e do Skrillex) e não são escritos (`luzes.FORA`).
- **Letreiro** (`beatloom/palco.py`, só com Chroma). O artista grande e a música embaixo, em letras de pixels (fonte 5×7 embutida, sem acento, o que a fonte não tem fica de fora), no fundo, a 55 m, centrado, com até 40 m de largura. Nome comprido quebra em duas linhas; nome que nem assim cabe é cortado com "...". Cada retângulo de pixels é um cubo do Chroma com material de luz e um ID de luz próprio no tipo do centro, então ele acende, apaga e muda de cor por evento. Teto de 320 peças (acima disso sai a música e fica só o artista). Green Day / Basket Case = 101 peças; Falling In Reverse / Watch The World Burn = 164.
- **Coreografia do letreiro** (`palco.coreografia`). Começa apagado; na entrada as letras do artista acendem uma a uma e a música aparece devagar; cada parte com o seu par de cores (os mesmos do Chroma nas luzes) e o seu brilho; no verso a música pisca com a voz; na subida o artista "carrega", mais letras acesas a cada batida, mudando de cor até a da queda; na entrada da queda um clarão branco corre pelas letras; na queda o artista pisca no bumbo e a música na caixa; o acento branco do centro passa também pelo letreiro; na pausa fica uma brasa; no fim some devagar.
- **Sem Chroma, as mesmas luzes de sempre.** Os eventos do centro do cenário passam a mirar só nas luzes dele (`lightID` de 1 até o número de luzes do centro, das tabelas do Chroma, `luzes.LUZES`). Onde o letreiro muda numa batida sem evento do centro, vem logo depois um evento com o estado de agora do centro e alvo vazio: o Chroma não acende nada com alvo vazio (conferido no código dele) e o jogo sem o mod lê o último evento da batida. Medido no mapa do fixture: comparando o mapa com Chroma e o mesmo mapa sem, nenhum evento que existia mudou e todos os eventos novos repetem o estado do centro.
- **Palcos com nome de banda continuam fora do sorteio** até se saber esconder o nome deles (`palco.ESCONDE`, vazio). Isso responde, por enquanto, à pergunta 2 do plano: como o nome da peça do letreiro do Green Day não está documentado em lugar nenhum que deu para alcançar, o mapa de prova testa palpites. Achado o certo: o palpite vai para `ESCONDE`, e aí o cenário pode voltar ao sorteio do Chroma com o letreiro do artista por cima (uma linha em `luzes.AMBIENTE`).

### Nível 2: mais luz para todo mundo, sem mod

- **Transições.** Na subida cada luz acende uma vez e depois sobe por transição, batida a batida (antes isso só existia com o Chroma). A música entra com o fundo subindo do escuro.
- **Ondas nos cenários novos.** Clarão e pulso correm pelo grupo de luzes de uma ponta à outra no tempo que sobra até a próxima deixa (no máximo meia batida), e a onda troca de sentido a cada vez; o giro dos lasers abre em leque em onda.
- **Pausa que respira.** Em vez de escuro total, o fundo dá um pulso fraco a cada compasso, na cor da parte que acabou.
- **O centro canta.** Na introdução e no verso, um clarão do centro a cada nota cantada de meia batida ou mais, mais forte quanto mais aguda (só no modo completo, que separa a voz).

### Nível 3: Chroma de verdade

- **Luz por luz** (`mods.luz_por_luz`). Na subida os anéis vão enchendo, do primeiro ao último; em cada bumbo da queda os anéis acendem com as quatro cores da capa espalhadas, e o desenho anda uma luz a cada bumbo; cada caixa acende um terço dos lasers do lado (e das colunas), e o terço anda; o primeiro giro de cada queda é largo, em onda, e os outros trocam de sentido; na subida a velocidade dos lasers sobe sem eles pularem de posição. Tudo isso só acrescenta alvo e cor a eventos que já existem, ou divide um evento em vários na mesma batida com o mesmo valor: sem o Chroma, o jogo lê o mesmo.
- **Colunas de luz** (`palco.colunas`). Cinco de cada lado, a 12 m da pista e mais longe a cada uma, de 14 m de altura, no tipo dos lasers do seu lado: acendem com os eventos de laser que o mapa já tem.
- **Paredes na cor da parte**, um pouco transparentes (`mods.paredes`).
- **A respiração da pausa** na cor da parte que acabou.

### Nível 4: Noodle e Chroma (conjunto Lawless)

- **Letreiro animado**: as peças viram uma trilha presa a um pai que se mexe (`AssignTrackParent` e `AnimateTrack`): sobe do horizonte na entrada, pula a cada queda e balança nela, afunda na pausa e volta, sobe para o céu no fim.
- **Corredor de colunas animado**: sobe do chão na entrada, pula a cada compasso da queda, afunda na pausa, desce no fim.
- **Notas**: a chegada de lado nas cabeças de parte agora surge do nada (`dissolve`); na entrada de cada queda as outras notas do primeiro compasso caem de cima. Ponta de arco e cabeça de corrente ficam de fora (o arco não acompanharia).
- **Barras da melodia** com cor (branca, meio transparente) para quem tem o Chroma.

### Refazer só as luzes

`generate.py --so-luzes <zip>` refaz cenário, luzes, reforço, cores, Chroma, palco e o conjunto do Noodle de um mapa pronto, com o gerador e as preferências de agora. Notas, arcos, correntes, bombas, paredes, eventos de BPM, nome, capa e áudio ficam. As luzes caem na grade das notas pela conta do jogo ao contrário (`relogio_do_mapa`). Conferido no fixture: o "só luzes" dá exatamente as mesmas dificuldades que a geração completa, e voltar com as chaves desligadas devolve o mapa idêntico ao original.

Na página: "Refazer só as luzes" na barra dos marcados e no menu "⋯" da ficha, e "Novo visual em todos" na lista. Vai pela fila, como o "Refazer", e a versão anterior fica em `saida\versoes`. Renomear um mapa que tem letreiro (ou trocar o artista para um que tem palco próprio, ou de um que tinha) põe o visual dele na fila sozinho, para o letreiro escrever o nome novo. A ficha mostra "letreiro do artista" junto dos mods.

### Ferramentas

- `tools/fixture.py`: música de mentira (bateria, baixo, acordes e voz sintetizados, 120 BPM, partes conhecidas) com o que o detector de batidas e o Demucs dariam já no cache, então a análise de verdade roda em cima dela. `--gerar` gera o mapa; sem a biblioteca de padrões, um motor de golpes simples (mãos alternando) entra no lugar. Foi assim que tudo acima foi conferido na nuvem.
- `tools/prova_visual.py`: os mapas de prova para o Quest e `--previa <zip>`, que desenha o palco de um mapa (letreiro e colunas) visto do lugar do jogador.

## Como conferir no Quest

1. `python tools\prova_visual.py` grava três mapas em `saida\`: "Prova logo Green Day", "Prova logo Monstercat" e "Prova neblina e carga". Eles aparecem na lista do Beatloom; mande ao Quest por lá. O nome de cada dificuldade no jogo diz o que ela testa.
2. **Prova logo** (nos dois): Easy não esconde nada; Normal tenta pelo nome "logo"; Hard por "texto ou placa"; Expert pelo nome da banda; Expert+ os três juntos. Diga qual dificuldade ficou sem o nome da banda e se sumiu mais alguma coisa do cenário.
3. **Prova neblina e carga**: Normal com neblina mais fraca, Hard mais forte (diga se alguma ficou melhor que a Easy); Expert com 6 letreiros (uns 500 peças) e Expert+ com 11 (uns 900): diga se engasgou.
4. Depois, um mapa de verdade: ligue "Tenho Chroma" e "Tenho Noodle Extensions", use "Refazer só as luzes" num mapa que você conhece e jogue o Standard e o Lawless.

O que olhar no mapa de verdade: o letreiro aparece, é legível, está bem posicionado (`palco.ONDE`, `LARGURA`, `PIXEL`) e não atrapalha a leitura das notas; as colunas não atravessam peças do cenário (`palco.colunas`); os anéis com as quatro cores e o enchimento da subida; a pausa que respira; o centro cantando; no Lawless, o letreiro subindo, pulando e indo para o céu, e as colunas.

## Não verificado

Tudo que é visual: nada disto foi visto no jogo nem no ArcViewer (que talvez nem mostre a geometria do Chroma). Em especial:

- Se o Chroma do Quest (2.10.3) cria a geometria e registra as luzes dela como o do PC (o código lido foi o do PC, Aeroluna/Heck). Se não, o letreiro e as colunas não aparecem e o resto continua.
- Se as tabelas de IDs de luz do Chroma do Quest são as mesmas do PC. Se não forem, o centro do cenário pode acender só em parte com o Chroma.
- O nome da peça do letreiro do Green Day e do Monstercat (é o que o mapa de prova descobre).
- A posição e o tamanho do letreiro e das colunas em cada cenário (escolhidos no papel: 55 m, base a 6,5 m, colunas a 12 m).
- Se The Second, Rock Mixtape e Weave têm algo escrito no cenário (o The Second tem uma luz chamada "Logo" no bsmap).
- Se os palcos de banda abrem no Quest de quem não comprou o pacote (o do Green Day abre no do dono).
- O efeito dos campos de giro do Chroma (`rotation`, `step`, `prop`, `speed`, `direction`) e do `lockRotation`.
- No Lawless: `AssignTrackParent` com peças do Chroma, e se `position` do pai é em metros.
- O tamanho dos arquivos (uns 170 KB por dificuldade com o palco) no carregamento do Quest.
- A página: os botões novos foram clicados num Chromium sem tela (refazer só as luzes de um mapa, renomear para "Green Day" e o mapa ir sozinho para o palco da banda); o inglês só passou pelo `check_i18n`.

## Ajustes depois do Quest

- Letreiro mal posicionado: `palco.ONDE` (x, altura da base, distância), `LARGURA`, `PIXEL`, `MINIMO`.
- Colunas atravessando o cenário: os parâmetros de `palco.colunas` (quantas, distância da pista, início, passo, altura).
- Quest engasgando: baixar `palco.TETO`.
- Um cenário do sorteio ficou feio ou com algo escrito: tirar ele de `luzes.AMBIENTE`.
- Logo descoberto: o palpite em `palco.ESCONDE` (por exemplo `{"GreenDayEnvironment": [("(?i)logo", "Regex")]}`) e o cenário de volta ao par de clássicos do clima em `luzes.AMBIENTE`.
- Depois de qualquer ajuste: "Novo visual em todos" leva o ajuste aos mapas sem mexer nas notas.
