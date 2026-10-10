# Roadmap

Escrito em 10/10/2026, depois das quatro fatias do redesenho ([plan/README.md](plan/README.md)). A ordem dentro de cada bloco é a sugerida. Nada aqui está decidido além do bloco 1, que o dono pediu como próxima etapa.

## 1. Próxima etapa: ouvir melhor a música e mapear mais como gente

Pedido do dono: detector melhor, mapa mais humano, mais intenso e mais realista; vocais melhor detectados; "sentir" a música; notas mais coerentes.

Como está hoje, para saber de onde se parte: batidas pelo beat_this, ataques pelo librosa na música inteira e em cada uma das quatro faixas do Demucs (bateria, baixo, voz, resto), intensidade por compasso, compassos repetidos reaproveitam o desenho, a altura da nota só distingue "voz/melodia" de "bateria/baixo", e os golpes vêm de trechos de 1, 2 ou 4 batidas tirados de mapas humanos.

**Ordem.** O 1.0 vem primeiro, porque os outros medem com ele. O 1.4 (pesquisa) pode vir a qualquer hora e rende mais antes do 1.1, porque pode poupar trabalho. O 1.1 vem antes do 1.2 e de parte do 1.3: as luzes (1.3 item 1) usam as partes da música (1.1 item 3) e os arcos (1.3 item 6) usam a voz (1.1 item 1). Do 1.3, os itens 2, 3, 7 e 8 não dependem de nada. Os blocos 2, 3 e 4 são livres.

**Modelo sugerido por bloco** (opinião de quem escreveu, 10/10/2026): Opus 5.5 em esforço médio para 1.1 e 1.2, onde o erro sai como mapa esquisito que nenhum teste pega; Sonnet 5.5 em esforço alto para 1.0, 1.3 e 1.4 e para os blocos 3 e 4, que são trabalho mais direto.

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

1. **Voz de verdade.** Na faixa de voz, seguir a altura cantada (pYIN do librosa) em vez de só o ataque: sílaba nova vira nota, melodia subindo ou descendo decide a altura e a direção do corte, nota longa cantada vira nota segurada.
2. **Bateria por peça.** Separar bumbo, caixa e pratos dentro da faixa de bateria (por faixa de frequência). Bumbo embaixo, caixa no meio, prato forte vira dupla.
3. **Partes da música.** Reconhecer introdução, verso, refrão, subida e queda. Subida vira sequência que acelera, queda vira o trecho mais cheio, pausa vira respiro de verdade. Hoje a intensidade é só por compasso.
4. **Força de cada ataque.** Ataque forte ganha dupla ou golpe largo; ataque fraco, golpe curto. Hoje a força decide se há nota, não como ela é.
5. **BPM variável.** Músicas que mudam de andamento saem sem eventos de BPM no mapa; o jogo e os editores mostram a grade errada.
6. Avaliar o modelo de seis faixas do Demucs (guitarra e piano separados). Custa mais tempo; só vale se o item 1.0 mostrar ganho.

### 1.2 Golpes mais humanos

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
10. **Com mods, opcional** (o dono tem Chroma e Noodle Extensions no Quest). Regra: desligado por padrão, uma opção para cada mod, e nada que pese no óculos.
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

Um por sessão, para colar como está. Entre parênteses, o modelo sugerido.

1.0: feito em 10/10/2026 (`tools/medir.py`), não precisa rodar de novo. Falta só a parte opcional, comparar com o Beat Sage e o TopMapper.

1.1 inteira (Opus 5.5 médio):

```text
Execute o bloco 1.1 do roadmap inteiro, um item por vez. A cada item: meça antes e depois com o script do 1.0, desfaça se piorar, e faça commit. Não pare para aprovar entre itens. No fim, push e me diga duas músicas para eu testar.
```

1.2 inteira (Opus 5.5 médio):

```text
Execute o bloco 1.2 do roadmap inteiro, um item por vez. A cada item: meça antes e depois com o script do 1.0, desfaça se piorar, e faça commit. Não pare para aprovar entre itens. No fim, push e me diga duas músicas para eu testar.
```

1.3 inteira (Sonnet 5.5 alto):

```text
Execute o bloco 1.3 do roadmap inteiro, um item por vez, menos o item 10 (mods). A cada item: confira que o mapa passa na conferência e faça commit. Não pare para aprovar entre itens. No fim, push e me diga duas músicas para eu ver.
```

Só as opções do mapa, 1.3 item 11 (Sonnet 5.5 alto):

```text
Roadmap 1.3 item 11 (escolher o que vai no mapa): comece por Sem Setas e pelos liga e desliga de bombas, pontos e paredes; os modos que o gerador ainda não faz ficam de fora da tela. Commit e push ao final.
```

1.4 (Sonnet 5.5 alto):

```text
Roadmap 1.4: pesquise as ferramentas de terceiros da lista e diga quais valem a pena. Sem código, só atualize o roadmap, commit e push.
```

Versões de um mapa, bloco 3 item 8 (Sonnet 5.5 alto):

```text
Roadmap bloco 3 item 8 (versões de um mapa): confira primeiro como o envio ao Quest nomeia a pasta, depois faça. Commit e push ao final.
```

Atualizar os mapas antigos de uma vez, bloco 3 item 9 (Sonnet 5.5 alto):

```text
Roadmap bloco 3 item 9 (atualizar os mapas antigos de uma vez): meça primeiro com tools/timing.py o que o cache guarda e o que roda de novo, depois faça. Commit e push ao final.
```

Mods, 1.3 item 10, depois dos itens 1 e 2 do mesmo bloco (Sonnet 5.5 alto):

```text
Roadmap 1.3 item 10 (mods): faça só a parte do Chroma como sugestão (paleta da capa, degradê, cor por parte da música), desligada por padrão. Noodle fica para depois. Commit e push ao final.
```

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
