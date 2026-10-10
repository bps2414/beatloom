# Beatloom

[English](README.md)

O Beatloom transforma uma música em um mapa de Beat Saber (Hard, Expert e Expert+) usando regras e padrões tirados de mapas humanos bem avaliados. Nenhum modelo é treinado. Tudo roda no seu computador, só com o processador.

Você cola um link do YouTube ou escolhe um arquivo de áudio, espera alguns minutos, assiste ao resultado em um visualizador 3D e recebe um zip pronto para o SongCore.

É um projeto de hobby, não oficial, sem ligação com a Beat Games.

## O que ele faz

1. Acha as batidas e os compassos com o [beat_this](https://github.com/CPJKU/beat_this) e os ataques das notas com o librosa, em uma grade de quatro casas por batida.
2. Separa bateria, baixo, voz e o resto com o [Demucs](https://github.com/adefossez/demucs), para as notas fortes seguirem a bateria.
3. Distribui as notas por compasso conforme a energia da música e repete o ritmo dos compassos repetidos (refrões).
4. Escolhe os golpes em uma biblioteca de janelas de 1, 2 e 4 batidas cortadas de mapas humanos, mantendo a paridade (o pulso nunca é forçado a torcer). Compassos repetidos reaproveitam o mesmo desenho quando a paridade deixa.
5. Põe luzes simples e paredes laterais nas pausas, empacota o zip e confere.

Todo mapa sai com um relatório. Ele confere: formato válido ([bsmap](https://github.com/KivalEvan/BeatSaber-JSMap)), erros de paridade, bloqueios de visão, palmas (mãos se batendo), notas empilhadas, notas na batida, folga no começo e no fim, e notas por segundo dentro da faixa de cada dificuldade.

## Até onde foi testado

Sem exagero: foi desenvolvido em cima de uma música eletrônica de andamento fixo que tem mapa humano para comparar (cerca de 90% dos nossos tempos também estão no mapa humano; cobrimos cerca de 70% dos tempos do humano) e depois rodado em mais quatro músicas (indie pop e um rock pesado). Todas passam nas conferências automáticas. Passar quer dizer "jogável e sem defeito conhecido", não "divertido". Poucos desses mapas foram jogados no headset até agora.

Limites conhecidos: só grade de 1/4 (sem tercinas nem swing), sem bombas, arcos ou correntes, sem notas de ponto, luzes básicas, e músicas lentas ganham muitas notas duplas no Expert+ para chegar à densidade alvo.

## Instalação

Precisa de Python 3.12, [ffmpeg](https://ffmpeg.org/), [Node.js](https://nodejs.org/) e, para colar links, [yt-dlp](https://github.com/yt-dlp/yt-dlp). Feito no Windows; nada é sabidamente exclusivo do Windows, mas outros sistemas não foram testados.

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd check && npm install && cd ..
```

Monte a biblioteca de padrões. Ela não vem no repositório porque é derivada do trabalho de outros mappers. Este passo baixa só as notas (sem áudio) de até 1000 mapas bem avaliados do BeatSaver, um pedido por segundo, uns 20 minutos:

```
.venv\Scripts\python baixar_mapas.py 1000
.venv\Scripts\python extrair_padroes.py
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

Abre http://localhost:8777 e só responde ao seu próprio computador.

Pelo terminal:

```
.venv\Scripts\python gerar.py "musica.mp3" --nome "Nome" --artista "Artista"
```

O mapa sai em `saida\<nome>-v4.zip`, com `saida\<nome>-v4.relatorio.txt` ao lado. Copie a pasta descompactada para a pasta de mapas personalizados (no Quest: `ModData/com.beatgames.beatsaber/Mods/SongCore/CustomLevels`).

`--etapa 1|2|3|4` escolhe a versão do gerador (padrão 4): 1 ritmo simples com golpes do BeatKenja, 2 densidade segue a energia e refrões repetem, 3 golpes de padrões humanos, 4 separação de instrumentos e paredes.

Outras ferramentas: `relatorio.py <zip>` refaz as conferências, `teste_cego.py <a.zip> <b.zip>` monta um par A/B embaralhado da mesma música para comparar sem saber qual é qual.

## Tenha consideração

Os mapas desta ferramenta são automáticos. Se compartilhar um, avise, e siga as regras do site (o BeatSaver exige marcar mapas gerados por IA). Use só músicas que você tem o direito de usar.

## Créditos

As conferências de paridade e de mapa foram portadas do [bsmap e do BeatSaber-MapCheck](https://github.com/KivalEvan), de Kival Evan. Batidas pelo beat_this (CPJKU), separação pelo Demucs, visualizador ArcViewer (AllPoland), golpes da etapa 1 pelo BeatKenja. Os padrões vêm de mapas publicados no [BeatSaver](https://beatsaver.com) pelos seus mappers.

Licença MIT, veja [LICENSE](LICENSE).
