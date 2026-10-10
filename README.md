# Beatloom

[Português (Brasil)](README.pt-BR.md)

Beatloom turns a song into a Beat Saber map (Hard, Expert and Expert+) using rules and patterns taken from well-rated human maps. No model is trained. Everything runs on your own computer, on CPU.

You paste a YouTube link or pick an audio file, wait a few minutes, watch the result in a 3D viewer, and get a zip ready for SongCore.

Beatloom is an unofficial hobby project and is not affiliated with Beat Games.

## What it does

1. Finds beats and bars with [beat_this](https://github.com/CPJKU/beat_this) and note onsets with librosa, on a grid of four slots per beat.
2. Separates drums, bass, vocals and the rest with [Demucs](https://github.com/adefossez/demucs), so strong notes follow the drums.
3. Spends a note budget per bar that follows the energy of the song, and reuses the rhythm of repeated bars (choruses).
4. Picks swings from a library of 1, 2 and 4 beat windows cut from human maps, keeping wrist parity valid. Repeated bars reuse the same swing pattern when parity allows.
5. Adds simple lights and side walls in pauses, packs the zip, and checks it.

Every map comes with a report. It checks: valid schema ([bsmap](https://github.com/KivalEvan/BeatSaber-JSMap)), parity errors, vision blocks, handclaps, stacked notes, notes on the beat grid, slack at the start and end, and notes per second within the range of each difficulty.

## How far it has been tested

Be realistic about this. It was developed against one fixed-tempo electronic song with a human map as reference (about 90% of our note times also appear in the human map; we cover about 70% of the human's times), and then run on four more songs (indie pop and one heavy rock track). All of them pass the automatic checks. Passing the checks means "playable, no known defect", not "fun". Few of these maps have been played in a headset yet.

Known limits: 1/4 grid only (no triplets or swing), no bombs, arcs or chains, no dot notes, lights are basic, and slow songs get many double notes on Expert+ to reach the target density.

## Setup

You need Python 3.12, [ffmpeg](https://ffmpeg.org/), [Node.js](https://nodejs.org/), and optionally [yt-dlp](https://github.com/yt-dlp/yt-dlp) for links. Developed on Windows; nothing is known to be Windows-only, but other systems are untested.

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd check && npm install && cd ..
```

Build the pattern library. The repository does not ship it, because it is derived from other mappers' work. This downloads the note data (no audio) of up to 1000 well-rated maps from BeatSaver at one request per second, which takes about 20 minutes:

```
.venv\Scripts\python baixar_mapas.py 1000
.venv\Scripts\python extrair_padroes.py
```

Optional, for the 3D viewer inside the web page, get a copy of [ArcViewer](https://github.com/AllPoland/ArcViewer) (GPL-3, about 80 MB):

```
git clone --depth 1 -b deploy https://github.com/AllPoland/ArcViewer.git arcviewer
```

Optional, only for generator stages 1 and 2: Java and `BeatKenja.jar` from [BeatKenja](https://github.com/Chrisvenator/BeatKenja) inside a `beatkenja` folder.

## Use

Web page (English and Portuguese):

```
.venv\Scripts\python app.py
```

It opens http://localhost:8777 and only answers your own computer.

Command line:

```
.venv\Scripts\python gerar.py "song.mp3" --nome "Song name" --artista "Artist"
```

The map goes to `saida\<name>-v4.zip` with `saida\<name>-v4.relatorio.txt` next to it. Copy the unzipped folder to your custom levels folder (on Quest: `ModData/com.beatgames.beatsaber/Mods/SongCore/CustomLevels`).

`--etapa 1|2|3|4` picks the generator stage (default 4): 1 simple rhythm with BeatKenja swings, 2 density follows energy and choruses repeat, 3 swings from human patterns, 4 instrument separation and walls.

Other tools: `relatorio.py <zip>` re-runs the checks, `teste_cego.py <a.zip> <b.zip>` builds a blind A/B pair of the same song.

The code, command-line output and the report are written in Portuguese. The web page is translated.

## Please be considerate

Maps made by this tool are automatic. If you share one, say so, and follow the rules of the site you upload to (BeatSaver requires AI-generated maps to be flagged). Only use music you have the right to use.

## Credits

Parity and map checks are ported from [bsmap and BeatSaber-MapCheck](https://github.com/KivalEvan) by Kival Evan. Beat tracking by beat_this (CPJKU), source separation by Demucs, viewer by ArcViewer (AllPoland), stage 1 swings by BeatKenja. Pattern data comes from maps published on [BeatSaver](https://beatsaver.com) by their mappers.

MIT license, see [LICENSE](LICENSE).
