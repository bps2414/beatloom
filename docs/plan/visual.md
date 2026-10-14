# Plano: subir o nível visual dos mapas

Pedido do dono em 14/10/2026: "expandir o nível visual dos mapas; em alguns mapas, tipo do Green Day, fica o nome deles escrito, queria que ficasse o do artista da música que está tocando; e elevar mesmo a experiência visual para quem tem Chroma e algum outro mod".

**Estado: só planejado, nada feito. Aguarda o dono responder as perguntas do fim e aprovar o nível 0.** Um nível por vez, como na melhoria de UI/UX: ao terminar um, atualizar este documento e `README.md`, parar e esperar a aprovação.

## O que acontece hoje (lido no código)

- O cenário sai de `AMBIENTE` em `beatloom/luzes.py`, um par por clima: calmo (Big Mirror, The Second), **pesado (Green Day, Rock Mixtape)**, **eletrônico (Monstercat, Weave)**. Sem Chroma o par é sorteado pelo hash do áudio (`luzes.ambiente`); **com a chave do Chroma ligada é sempre o primeiro** (`generate.py`, linha do `ambiente = ...`), porque só os eventos básicos aceitam cor por evento.
- Por isso, para quem joga com Chroma (o dono), **toda música pesada cai no Green Day, com o letreiro "GREEN DAY" no fundo, e toda eletrônica no Monstercat, com o logo da gravadora.** Sem Chroma, metade delas.
- O que o Chroma faz hoje (`beatloom/mods.py`): uma cor por evento básico, um par por parte da música, degradê na subida. Nada de mexer no cenário, nada de luz por luz, nada de cor por nota (ficaram de fora no bloco 1.3, item 10).
- O Noodle faz um conjunto a mais (Lawless) com notas que chegam de lado nas cabeças de parte e barras finas na melodia cantada.
- **Nada disso foi visto no jogo** (ROADMAP, seção 1). Este plano começa por aí.

## O que o Chroma permite (conferido no código do mod, repositório Aeroluna/Heck, MIT)

- `customData.environment` em cada dificuldade (v3): cada item acha peças do cenário por `id` + `lookupMethod` (`Regex`, `Exact`, `Contains`, `StartsWith`, `EndsWith`) e pode `active: false` (esconder), `duplicate`, `position`, `rotation`, `scale`, `track`.
- Geometria nova no mesmo array: `{"geometry": {"type": "Cube", "material": ..., "collision": false}, "position", "scale", "components": {"ILightWithId": {"type", "lightID"}}}`. Tipos: Sphere, Capsule, Cylinder, Cube, Plane, Quad, Triangle. Shaders: Standard, OpaqueLight, TransparentLight, BaseWater, BillieWater, BTSPillar, InterscopeConcrete, InterscopeCar, Obstacle, WaterfallMirror, Glowing.
- **Geometria com shader OpaqueLight ou TransparentLight vira uma luz do cenário**: com `ILightWithId` num tipo de luz, os eventos básicos que o gerador já escreve acendem, apagam e colorem a peça. O mod desliga sombra e colisão e usa material compartilhado (`customData.materials`, por nome).
- Tabelas de IDs de luz de todos os cenários clássicos (`Chroma/LightIDTables/*.json`): quantas luzes cada tipo tem em cada cenário. Isso resolve o "os números de cada luz mudam de cenário para cenário" que deixou o luz por luz de fora. Exemplos (tipos 1 a 5 da tabela): Big Mirror 10/60/8/8/16, Green Day 16/60/6/6/3, Triangle 10/60/11/11/12, Nice 8/40/11/11/14, Panic 2/62/7/7/8. A correspondência exata entre a chave da tabela e o tipo de evento a confirmar no código do Chroma antes de usar.
- Para achar o `id` de uma peça (o letreiro, por exemplo): a opção `PrintEnvironmentEnhancementDebug` no `Chroma.json` do PC escreve no log todas as peças do cenário. No Quest não sei se existe; daí o mapa de prova do nível 0.

## Níveis

### Nível 0: mapa de prova no Quest (antes de qualquer coisa)

Um `tools/prova_visual.py --quest` que monta um mapa curto (30 s, áudio sintético de cliques, como o `tools/fixture.py` pensado na fatia 2) em cada cenário candidato e manda ao Quest pelo `beatloom.quest`. Cada dificuldade testa uma coisa, e o dono só diz qual funcionou:

- Easy, Normal, Hard: esconder o letreiro com um palpite de `id` em cada uma (`Contains "Logo"`, `Regex "GreenDay.*Logo"`, `Regex "\]Logo$"`...), no Green Day e no Monstercat.
- Expert: a palavra "BEATLOOM" em cubos de luz no fundo, piscando com o centro.
- Expert+: 400 cubos de luz e 3 luzes acendendo uma a uma, para ver se o Quest aguenta.

Sai daqui: os `id` dos letreiros, se a geometria do Chroma funciona no Quest 1.40.8, um teto de peças, e a primeira visão das cores de Chroma que já existem. Barato e tira o maior risco de todo o resto. `--demo` confere o formato com o `check/` (bsmap).

### Nível 1: o letreiro (o pedido direto)

Sem mod, para todo mundo:

1. **Cenário da própria banda.** Tabela pequena de artista → cenário com a marca dele (Green Day, Linkin Park, BTS, Imagine Dragons, Panic! at the Disco, Timbaland, Skrillex, Billie Eilish, K/DA...; só os clássicos, que já acendem com os eventos básicos). Nome comparado sem acento, sem caixa e sem "feat.". Música do Green Day vai para o palco do Green Day, com o letreiro certo.
2. **Fora disso, nada de cenário com marca no sorteio.** Trocar Green Day e Monstercat em `AMBIENTE` por clássicos sem letreiro (candidatos pelas tabelas do Chroma: Triangle, Nice, Panic, Origins, KDA; a escolha final o dono faz olhando no mapa de prova). Mapas antigos só mudam ao "Refazer".

Com Chroma:

3. **O nome do artista no lugar do letreiro.** Novo `beatloom/palco.py`: uma fonte de pixels 5×7 embutida (A–Z, 0–9, `& ! ? . ' -`; acento tirado por `unicodedata`, o resto ignorado), cada linha de pixels contínua vira um cubo só (Green Day ≈ 80 cubos). Material único `TransparentLight` em `customData.materials`, cada cubo com `ILightWithId` num tipo de luz já usado pelo gerador (o centro, por exemplo), então o nome **acende, apaga, muda de cor e dá o clarão branco junto com a música, sem nenhum evento novo**. Nome longo vira duas linhas ou encolhe; "Desconhecido" não escreve nada. Posição: a do letreiro escondido, ou fixa no alto do fundo nos cenários sem letreiro.
4. Com isso o dono decide (pergunta 2) se, com Chroma, o Green Day volta ao sorteio do pesado: o palco é bonito e o letreiro já não aparece. O preço: quem jogar o mesmo mapa sem Chroma vê o letreiro.

Onde entra: `luzes.ambiente(clima, marca, artista)`, `generate.py` passa o artista; o nome no palco vai em `mods.aplicar`, junto do resto do Chroma. O Info.dat continua igual, o mapa sem mod continua jogável. A ficha mostra "Chroma: nome do artista no palco"; frases novas em `site/i18n/pt.json` e `en.json`.

### Nível 2: mais luz para todo mundo (sem mod)

- **Transições sem Chroma.** Os eventos de transição (valores 4, 8, 12) existem no jogo puro; hoje só o caminho do Chroma usa. A subida passa a acender devagar para todos.
- **Ondas nos cenários novos.** `luzes.grupos` manda `"w": 0` (sem distribuição): cada grupo acende inteiro de uma vez. Com distribuição por batida, a luz corre de uma ponta à outra do grupo (na subida, de dentro para fora; na queda, no bumbo). Mesma coisa no giro dos lasers. Nenhum evento a mais no arquivo, é o mesmo evento com outro campo.
- **Translação** (`lightTranslationEventBoxGroups`, ainda não usada) nos cenários que têm: lasers subindo na subida e abrindo na queda.

### Nível 3: Chroma de verdade

Tudo como sugestão, como hoje: quem não tem o mod joga o mapa normal.

- **Luz por luz** (`lightID` nos eventos, pelas tabelas do Chroma): na subida as luzes dos anéis acendem uma a uma até fechar a volta; na queda a paleta inteira da capa espalhada pelas luzes em vez de duas cores; "perseguição" de laser no ritmo da caixa.
- **Palco maior**: duplicar anéis ou lasers (`duplicate` + `position`) só nas quedas não dá (é fixo no mapa todo); então uma vez por mapa, medido no Quest pelo teto do nível 0. Esconder entulho do cenário que atrapalha a vista.
- **Névoa** (`BloomFogEnvironment`, `attenuation`) diferente por clima: mais fechada no calmo, aberta no pesado.
- **Cor por nota**, só um puxão de tom por parte da música, sempre a menos de 20° do tom do sabre (vermelho continua vermelho). Por último e só se o dono quiser: é o que mais arrisca a leitura do mapa.

### Nível 4: Noodle + Chroma (conjunto Lawless)

Só depois de ver o nível 3 no Quest. O Noodle já exige mod, então aqui pode animar:

- O nome do artista com `track`: entra de baixo no começo, cresce um pouco a cada queda.
- Notas que "aparecem" (`dissolve`, `dissolveArrow`) nas cabeças de parte, além da chegada de lado que já existe.
- Anéis e lasers se mexendo com `AnimateTrack` nas quedas.

## Junto com isto: refazer só as luzes

Para levar o novo visual aos mapas que já ficaram bons sem mexer nas notas, o item "só as luzes" do ROADMAP (uso no dia a dia, item 9) vira pré-requisito do nível 1: refazer luzes, cenário, Chroma e palco a partir da análise guardada, deixando `colorNotes`, arcos, correntes, bombas e paredes como estão. A conferência roda igual (luz não muda jogabilidade, mas o cenário entra no relatório).

## Regras para todos os níveis

- Sem a chave do Chroma (e sem a do Noodle), o que muda é só o nível 1 itens 1 e 2 e o nível 2; nada que exija mod.
- Cada lógica nova com `demo()` e `assert`: fonte (cada letra, junção de cubos, nome longo, acento, nome vazio), escolha do cenário pelo artista, distribuição dos grupos, `lightID` dentro do tamanho de cada cenário.
- Teto de peças de geometria vindo do nível 0, conferido no `--demo`.
- `--demo` de `luzes`, `mods`, `checks`, `generate.py` e `check_i18n` passando antes de cada commit.

## Não verificável na nuvem

Tudo que é visual só o dono vê: o mapa de prova, os letreiros, a fonte no fundo, o desempenho no Quest. Aqui dá para conferir o formato (bsmap), os testes de cada função e o ArcViewer, que mostra luzes mas talvez não a geometria do Chroma.

## Perguntas para o dono

1. **Cenário da banda:** música do Green Day no palco do Green Day (com o letreiro certo) e as outras em cenários sem marca. Pode ser assim?
2. **Com Chroma:** manter o Green Day e o Monstercat no sorteio, com o nome do artista no lugar do letreiro, ou usar só cenários sem marca e escrever o nome neles?
3. **O que escrever:** só o artista, ou o artista grande e o nome da música menor embaixo?
4. **Você tem o Beat Saber no PC?** Se tiver, o log de depuração do Chroma dá os nomes de todas as peças de uma vez e o nível 0 fica menor.
5. **Ordem:** a sugerida é 0 → 1 (com "só as luzes") → 2 → 3 → 4. Algum nível que não interessa?
