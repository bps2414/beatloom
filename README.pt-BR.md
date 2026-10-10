# Beatloom

[English](README.md)

O Beatloom transforma uma música em um mapa de Beat Saber (Easy, Normal, Hard, Expert e Expert+) usando regras e padrões tirados de mapas humanos bem avaliados. Nenhum modelo é treinado. Tudo roda no seu computador, só com o processador.

Você cola um link do YouTube ou escolhe um arquivo de áudio, espera alguns minutos, assiste ao resultado em um visualizador 3D e recebe um zip pronto para o SongCore.

É um projeto de hobby, não oficial, sem ligação com a Beat Games.

## O que ele faz

1. Acha as batidas e os compassos com o [beat_this](https://github.com/CPJKU/beat_this) e os ataques das notas com o librosa, em uma grade de quatro casas por batida.
2. Separa bateria, baixo, voz e o resto com o [Demucs](https://github.com/adefossez/demucs), para as notas fortes seguirem a bateria.
3. Distribui as notas por compasso conforme a energia da música e repete o ritmo dos compassos repetidos (refrões).
4. Escolhe os golpes em uma biblioteca de janelas de 1, 2 e 4 batidas cortadas de mapas humanos, mantendo a paridade (o pulso nunca é forçado a torcer). Compassos repetidos reaproveitam o mesmo desenho quando a paridade deixa.
5. Transforma notas longas de voz ou melodia em notas seguradas (arcos), põe luzes simples e paredes laterais nas pausas, empacota o zip e confere.
6. Usa a capa e os dados da música (nome, artista, álbum, ano, link) que vierem do arquivo ou do link.

Todo mapa sai com um relatório. Ele confere: formato válido ([bsmap](https://github.com/KivalEvan/BeatSaber-JSMap)), erros de paridade, bloqueios de visão, palmas (mãos se batendo), notas empilhadas, sabre de uma mão passando pela nota da outra, notas na batida, folga no começo e no fim, e notas por segundo dentro da faixa de cada dificuldade.

## Até onde foi testado

Sem exagero: foi desenvolvido em cima de uma música eletrônica de andamento fixo que tem mapa humano para comparar (entre 87% e 96% dos nossos tempos também estão no mapa humano, conforme a dificuldade; cobrimos cerca de 72% dos tempos do humano) e depois rodado em mais cinco músicas (indie pop e um rock pesado). Todas passam nas conferências automáticas. Passar quer dizer "jogável e sem defeito conhecido", não "divertido". Poucos desses mapas foram jogados no headset até agora.

Limites conhecidos: só grade de 1/4 (sem tercinas nem swing), sem bombas nem correntes, sem notas de ponto, a detecção de nota longa para os arcos é simples e ainda não foi conferida de ouvido em muitas músicas, luzes básicas, e músicas lentas ganham muitas notas duplas no Expert+ para chegar à densidade alvo.

Como funciona, passo a passo: [docs/ARCHITECTURE.pt-BR.md](docs/ARCHITECTURE.pt-BR.md).

## Instalação

Precisa de Python 3.12, [ffmpeg](https://ffmpeg.org/), [Node.js](https://nodejs.org/) e, para colar links, [yt-dlp](https://github.com/yt-dlp/yt-dlp). Feito no Windows; nada é sabidamente exclusivo do Windows, mas outros sistemas não foram testados.

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd check && npm install && cd ..
```

Monte a biblioteca de padrões. Ela não vem no repositório porque é derivada do trabalho de outros mappers. Este passo baixa só as notas (sem áudio) de até 1000 mapas bem avaliados do BeatSaver, um pedido por segundo, uns 20 minutos:

```
.venv\Scripts\python tools\download_maps.py 1000
.venv\Scripts\python tools\extract_patterns.py
```

Opcional, para o visualizador 3D dentro da página: uma cópia do [ArcViewer](https://github.com/AllPoland/ArcViewer) (GPL-3, uns 80 MB):

```
git clone --depth 1 -b deploy https://github.com/AllPoland/ArcViewer.git arcviewer
```

Opcional, só para as etapas 1 e 2 do gerador: Java e o `BeatKenja.jar` do [BeatKenja](https://github.com/Chrisvenator/BeatKenja) em uma pasta `beatkenja`.

## Uso

Site (português e inglês):

```
.venv\Scripts\python app.py
```

Abre http://localhost:8777 e só responde ao seu próprio computador. Antes de gerar, a página mostra a capa, o nome e o artista para você corrigir, e deixa escolher as dificuldades e a quantidade de notas. Em cada mapa pronto dá para trocar o nome, apagar (vai para `saida\lixeira`) e mandar ao Quest.

Pelo terminal:

```
.venv\Scripts\python generate.py "musica.mp3" --nome "Nome" --artista "Artista" --capa "foto.jpg"
```

Nome e artista são opcionais: sem eles valem as tags do arquivo e, na falta, o nome do arquivo limpo ("Artista - Música"). A capa vem de `--capa`, senão da imagem embutida no arquivo, senão sai uma genérica. `--difs Normal,Hard` gera só algumas dificuldades e `--densidade 0.8` (até `1.3`) deixa o mapa mais leve ou mais cheio.

O mapa sai em `saida\<nome>-v4.zip`, com `saida\<nome>-v4.relatorio.txt` ao lado. Copie a pasta descompactada para a pasta de mapas personalizados (no Quest: `ModData/com.beatgames.beatsaber/Mods/SongCore/CustomLevels`).

`--etapa 1|2|3|4` escolhe a versão do gerador (padrão 4): 1 ritmo simples com golpes do BeatKenja, 2 densidade segue a energia e refrões repetem, 3 golpes de padrões humanos, 4 separação de instrumentos e paredes.

Outras ferramentas: `report.py <zip>` refaz as conferências, `tools\blind_test.py <a.zip> <b.zip>` monta um par A/B embaralhado da mesma música para comparar sem saber qual é qual, e `tools\batch.py <lista.txt> <pasta>` gera várias músicas de uma vez e resume os relatórios.

## Pastas

```
generate.py, app.py, report.py   os três comandos
beatloom\                        o miolo: ouvir (audio.py), escolher golpes (engine.py), conferir (checks.py)
tools\                     biblioteca de padrões, teste cego, geração em lote
site\                            a página
check\                           conferência com o bsmap (Node)
docs\                            como funciona
```

## Tenha consideração

Os mapas desta ferramenta são automáticos. Se compartilhar um, avise, e siga as regras do site (o BeatSaver exige marcar mapas gerados por IA). Use só músicas que você tem o direito de usar.

## Créditos

As conferências de paridade e de mapa foram portadas do [bsmap e do BeatSaber-MapCheck](https://github.com/KivalEvan), de Kival Evan. Batidas pelo beat_this (CPJKU), separação pelo Demucs, visualizador ArcViewer (AllPoland), golpes da etapa 1 pelo BeatKenja. Os padrões vêm de mapas publicados no [BeatSaver](https://beatsaver.com) pelos seus mappers.

Licença MIT, veja [LICENSE](LICENSE).
