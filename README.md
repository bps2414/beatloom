# Beatloom

[Português (Brasil)](README.pt-BR.md)

Beatloom turns a song into a Beat Saber map (Easy, Normal, Hard, Expert and Expert+) using rules and patterns taken from well-rated human maps. No model is trained. Everything runs on your own computer, on CPU.

You paste a YouTube link or pick an audio file, wait a few minutes, watch the result in a 3D viewer, and get a zip ready for SongCore.

Beatloom is an unofficial hobby project and is not affiliated with Beat Games.

## What it does

1. Finds beats and bars with [beat_this](https://github.com/CPJKU/beat_this) and note onsets with librosa, on a grid of four slots per beat.
2. Separates drums, bass, vocals and the rest with [Demucs](https://github.com/adefossez/demucs), so strong notes follow the drums.
3. Spends a note budget per bar that follows the energy of the song, and reuses the rhythm of repeated bars (choruses).
4. Picks swings from a library of 1, 2 and 4 beat windows cut from human maps, keeping wrist parity valid. Repeated bars reuse the same swing pattern when parity allows.
5. Turns long vocal or melody notes into held notes (arcs), links with arcs the swings the voice carries across, adds chains on dry attacks, reset bombs after rests, lights that follow the song sections and the drums, with the cover colours and an environment picked by the mood of the song, walls where there is no note (decorative, dodge and crouch), packs the zip, and checks it.
6. Uses the cover and song data (name, artist, album, year, link) found in the file or the link.

Every map comes with a report. It checks: valid schema ([bsmap](https://github.com/KivalEvan/BeatSaber-JSMap)), parity errors, vision blocks, handclaps, stacked notes, one hand's saber passing through the other hand's note, notes on the beat grid, slack at the start and end, and notes per second within the range of each difficulty.

## How far it has been tested

Be realistic about this. It was developed against one fixed-tempo electronic song with a human map as reference (87% to 96% of our note times also appear in the human map, depending on the difficulty; we cover about 72% of the human's times), and then run on five more songs (indie pop and one heavy rock track). All of them pass the automatic checks. Passing the checks means "playable, no known defect", not "fun". Few of these maps have been played in a headset yet.

Known limits: 1/4 grid only (no triplets or swing), no dot notes, chains, bombs and dodge walls have not been seen in the game yet, the long-note detection behind arcs is simple and has not been checked by ear on many songs, the lights of the newer environments have not been checked in the game yet, and slow songs get many double notes on Expert+ to reach the target density.

How it works, step by step: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Setup

On Windows, download `beatloom-setup.exe` from the latest [release](https://github.com/bps2414/beatloom/releases) and open it. It copies Beatloom to `%LOCALAPPDATA%\Beatloom` (no administrator needed), creates the shortcuts and opens it. You do not need to install anything first.

The installer is not signed, so Windows SmartScreen shows "Windows protected your PC": click "More info", then "Run anyway". If you prefer, download the source zip from the same release, unzip it and double-click `start.bat`; it is the same thing without the shortcuts.

The first time, `start.bat` downloads Python 3.12 and the packages (about 2 GB, several minutes) into the Beatloom folder, then opens the page. The page shows what is still missing and downloads it with a progress bar, also into the Beatloom folder:

- ffmpeg and Node.js (required).
- The pattern library (required). The repository does not ship it, because it is derived from other mappers' work. The page downloads the note data (no audio) of 1000 well-rated maps from BeatSaver at one request per second, which takes about 20 minutes. If you close it, it resumes where it stopped.
- [ArcViewer](https://github.com/AllPoland/ArcViewer) (GPL-3, about 80 MB), for the 3D viewer inside the page. Optional.
- ADB, to send maps to a Quest over Wi-Fi. Optional.

Everything stays inside the Beatloom folder; uninstalling (or deleting the folder) removes it all, and the uninstaller asks whether to keep the generated maps. On a PC with an NVIDIA card `start.bat` installs the CUDA build of torch, otherwise the CPU build.

### By hand

You need Python 3.12, [ffmpeg](https://ffmpeg.org/) and [Node.js](https://nodejs.org/). Developed on Windows; nothing in the generator is known to be Windows-only, but other systems are untested and the setup screen only knows the Windows downloads.

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd check && npm install && cd ..
.venv\Scripts\python tools\download_maps.py 1000
.venv\Scripts\python tools\extract_patterns.py
git clone --depth 1 -b deploy https://github.com/AllPoland/ArcViewer.git arcviewer
```

The last line is optional (3D viewer). Also optional, only for generator stages 1 and 2: Java and `BeatKenja.jar` from [BeatKenja](https://github.com/Chrisvenator/BeatKenja) inside a `beatkenja` folder.

## Use

Web page (English and Portuguese): double-click `start.bat`, or run `.venv\Scripts\python app.py`.

It opens http://localhost:8777 and only answers your own computer. Before generating, the page shows the cover, name and artist so you can fix them, and lets you choose the difficulties and the amount of notes. Each finished map can be renamed, deleted (it goes to `saida\lixeira`) and sent to the Quest.

Quest: the first time, plug the headset in with a USB cable (developer mode on), accept the prompt inside the headset and click "Find the Quest over USB" in Settings. After that maps go over Wi-Fi. The page shows whether the Quest is reachable and which maps are already on it, and can delete them from the headset. Your choices (language, Quest address, default difficulties) are kept in `beatloom.json`.

Command line:

```
.venv\Scripts\python generate.py "song.mp3" --nome "Song name" --artista "Artist" --capa "picture.jpg"
```

Name and artist are optional: without them the file tags are used, and failing that the cleaned file name ("Artist - Song"). The cover comes from `--capa`, else from the image embedded in the file, else a generic one. `--difs Normal,Hard` generates only some difficulties and `--densidade 0.8` (up to `1.3`) makes the map lighter or fuller.

The map goes to `saida\<name>-v4.zip` with `saida\<name>-v4.relatorio.txt` next to it (and `.relatorio.json`, the same checks as data, which the page shows in your language). Copy the unzipped folder to your custom levels folder (on Quest: `ModData/com.beatgames.beatsaber/Mods/SongCore/CustomLevels`).

`--etapa 1|2|3|4` picks the generator stage (default 4): 1 simple rhythm with BeatKenja swings, 2 density follows energy and choruses repeat, 3 swings from human patterns, 4 instrument separation and walls.

Other tools: `report.py <zip>` re-runs the checks, `tools\blind_test.py <a.zip> <b.zip>` builds a blind A/B pair of the same song, and `tools\batch.py <list.txt> <folder>` generates several songs at once and summarises the reports. `tools\check_i18n.py` checks that both languages have the same phrases and `tools\timing.py <audio>` measures how long each part of the generation takes.

The link can be a YouTube playlist: each track is queued and becomes a map, one at a time. Pasting the same playlist again does not repeat work: a track that already has a map is left out, one whose check failed is redone, and only the missing ones are queued. You can pause the queue, clear it or remove one item; it is saved to disk, so closing Beatloom does not lose it (the song that was being made starts over).

In Settings, "The way you play" has three preferences: no notes on the top row, no note hidden behind another (two notes in a row in the same spot less than 0.3 s apart), and how much the arms may cross on Expert and Expert+ (never, a little, free). They apply to new maps and to the ones you redo: select maps in the list and use "Redo the maps", or "Redo all maps" for the whole list. The map is made again from scratch with the current generator (notes, lights, environment, colours) and keeps its name, artist, link, cover, mode and difficulties; the previous version is kept in `saida\versoes`. The saved analysis is reused while it is still valid, and then it takes about 10 seconds per map. On the command line it is `--prefs sem_topo,sem_fila,cruzar_nunca` (or `cruzar_livre`; with neither, a little).

The installer and the release come from CI (`.github\workflows\release.yml`): `git tag v1.0.1` and `git push origin v1.0.1` build `beatloom-setup.exe` with Inno Setup (`installer\beatloom.iss`) and publish the release with the list of commits since the previous tag.

To generate in bulk on a Google Colab GPU (a YouTube playlist or a folder of audio files in your Drive), open [colab/beatloom.ipynb](https://colab.research.google.com/github/bps2414/beatloom/blob/main/colab/beatloom.ipynb). The same notebook runs on Kaggle (import the file there; the zips come out in the Output tab). Each person runs it in their own account; on Colab the zips go to their Drive. It has no page and no viewer.

On the page, "fast mode" (in the new-map dialog, or as the default in settings) generates at stage 3: about 6 times faster, without separating the instruments, so no held notes and no walls.

## Folders

```
start.bat                        installs what is missing and opens the page
generate.py, app.py, report.py   the three commands
beatloom\                        the core: listening (audio.py), choosing swings (engine.py), checking (checks.py),
                                 first-run downloads (preparo.py), Quest over ADB (quest.py)
bin\                             programs the setup screen downloads (not in the repository)
tools\                     pattern library, blind test, batch generation
site\                            the web page: app.html, app.css, app.js, the phrases in i18n\pt.json and en.json, the fonts
check\                           bsmap validation (Node)
docs\                            how it works
```

The code, command-line output and the report are written in Portuguese. The web page is translated.

## Please be considerate

Maps made by this tool are automatic. If you share one, say so, and follow the rules of the site you upload to (BeatSaver requires AI-generated maps to be flagged). Only use music you have the right to use.

## Credits

Parity and map checks are ported from [bsmap and BeatSaber-MapCheck](https://github.com/KivalEvan) by Kival Evan. Beat tracking by beat_this (CPJKU), source separation by Demucs, viewer by ArcViewer (AllPoland), stage 1 swings by BeatKenja. Pattern data comes from maps published on [BeatSaver](https://beatsaver.com) by their mappers.

MIT license, see [LICENSE](LICENSE).
