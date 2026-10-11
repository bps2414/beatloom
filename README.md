# Beatloom

[Português (Brasil)](README.pt-BR.md) · [Download](https://github.com/bps2414/beatloom/releases/latest) · [How it works](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md)

**Paste a YouTube link and get a Beat Saber map ready to play.**

![The Beatloom home: the map list on the left, the library numbers and a wall of covers on the right](docs/tela.jpg)

Beatloom listens to the song and builds the map (Easy, Normal, Hard, Expert and Expert+) with rules and with patterns taken from well-rated human maps. No model is trained. Everything runs on your own computer, in a local web page: you watch the map in 3D, read the report and send it to your Quest over Wi-Fi.

An unofficial hobby project, not affiliated with Beat Games.

## Getting started

1. Download `beatloom-setup.exe` from the [latest release](https://github.com/bps2414/beatloom/releases/latest) and open it. You do not need to install anything first, and no administrator account is needed.
2. Wait for the first-run setup. The page shows what is missing and downloads it with a progress bar.
3. Click **New map**, paste a YouTube link (or pick an audio file) and generate.

The installer is not signed, so Windows shows "Windows protected your PC". Click "More info", then "Run anyway". If you prefer, download the source zip from the same release, unzip it and double-click `start.bat`: it is the same thing without the shortcuts.

### What is downloaded the first time

Everything goes inside the Beatloom folder (`%LOCALAPPDATA%\Beatloom`). Uninstalling or deleting the folder removes it all; the uninstaller asks whether to keep the generated maps.

| What | Size and time | Required |
|---|---|---|
| Python 3.12 and the packages | about 2 GB, several minutes | yes |
| ffmpeg and Node.js | small | yes |
| Pattern library: the note data (no audio) of 1000 well-rated BeatSaver maps | about 20 minutes, one request per second; if you close it, it resumes where it stopped | yes |
| [ArcViewer](https://github.com/AllPoland/ArcViewer) (GPL-3), the 3D viewer in the page | about 80 MB | no |
| ADB, to send maps to the Quest | small | no |

The pattern library ships with neither the repository nor the release, because it is derived from other mappers' work. On a PC with an NVIDIA card `start.bat` installs the CUDA build of torch, otherwise the CPU build.

## On the page

The page opens at http://localhost:8777, in English or Portuguese, and only answers your own computer.

- **New map.** Before generating you see the cover, name and artist so you can fix them, and choose the difficulties and the amount of notes.
- **Playlist.** The link can be a YouTube playlist: each track is queued and becomes a map. Pasting the same playlist again does not repeat what is already done.
- **Playlist in the game.** With a playlist link, tick "Also create the playlist in the game": the maps show up grouped in Beat Saber under the playlist name. It needs a playlist mod (PlaylistManager) on the Quest. The playlist goes along when you send the maps; with no Quest connected, download the `.bplist` from the list. Not yet tested on a real Quest.
- **Queue.** You can pause it, clear it and remove one item. It is saved to disk: closing Beatloom does not lose it.
- **Map sheet.** 3D viewer, the numbers of each difficulty and the result of the checks. You can rename, download the zip, redo and delete (it goes to `saida\lixeira`).
- **The way you play** (in Settings). No notes on the top row, no note hidden behind another, how much the arms may cross (never, a little, free), and sabers and notes in the cover colors.
- **Redo the maps.** Select maps in the list and redo them with the current generator and preferences, or use "Redo all maps". Name, artist, cover and difficulties stay; the previous version goes to `saida\versoes`. With the saved analysis it takes about 10 seconds per map.
- **Fast mode.** About 6 times faster, without separating the instruments, so no held notes and no walls.
- **Mods, optional.** "I have Chroma" puts the cover palette in the lights. "I have Noodle Extensions" adds a separate difficulty set (Lawless) with light effects. With both off, the map depends on no mod.

### Quest

The first time, plug the headset in with a USB cable with developer mode on, accept the prompt inside the headset and click "Find the Quest over USB" in Settings. After that maps go over Wi-Fi. The page shows whether the Quest is reachable, which maps are already on it and which changed since they were sent, sends several at once and deletes from the headset.

Without a Quest: copy the unzipped folder to the SongCore custom levels folder.

## What the map has

| | |
|---|---|
| Rhythm | Beats and bars by [beat_this](https://github.com/CPJKU/beat_this), onsets by librosa on the song and on each instrument separated by [Demucs](https://github.com/adefossez/demucs) (drums, bass, vocals, rest). BPM events when the tempo varies. |
| Swings | Windows of 1, 2 and 4 beats cut from human maps, chosen by rehearsing 8 beats ahead and keeping wrist parity valid. A chorus repeats its pattern, sometimes mirrored. |
| Voice and drums | A sung syllable becomes a note, the pitch of the voice pulls the row and the cut direction, a long note becomes a held note. Kick low, snare in the middle, a strong cymbal becomes a double. |
| Vocabulary | Arcs, chains on dry attacks, stacks on accents, reset bombs after rests, decorative, dodge and crouch walls. |
| Lights | They follow the song sections (intro, verse, build-up, drop, break) and the drums, in the cover colors, in an environment picked by the mood of the song. |
| Data | Cover, name, artist, album, year and link found in the file or the video. |

Every map comes with a report. It checks: valid schema ([bsmap](https://github.com/KivalEvan/BeatSaber-JSMap)), parity errors, vision blocks, handclaps, stacked notes, one hand's saber passing through the other hand's note, notes on the beat grid, slack at the start and end, and notes per second within the range of each difficulty.

## How far it has been tested

Be realistic about this. On 18 songs of different styles (indie pop, rock, metal, electronic), all pass every automatic check. Passing means "playable, no known defect", not "fun". Few of these maps have been played in a headset.

Known limits:

- 1/4 grid only: no triplets or swing. No dot notes.
- Not yet seen in the game: chains, bombs, dodge walls, the lights of the newer environments, and the Chroma and Noodle Extensions effects. The format is validated, the result on screen is not.
- Slow songs get many double notes on Expert+ to reach the target density.
- The installer has not been tested on a clean machine yet.
- Built and tested on Windows. Other systems are not a target.

The numbers behind each generator change are in [docs/RESULTADOS.md](docs/RESULTADOS.md) (in Portuguese).

## For people working on the code

The code, command-line output and the report are written in Portuguese. The web page is translated.

### Install by hand

You need Python 3.12, [ffmpeg](https://ffmpeg.org/) and [Node.js](https://nodejs.org/).

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd check && npm install && cd ..
.venv\Scripts\python tools\download_maps.py 1000
.venv\Scripts\python tools\extract_patterns.py
git clone --depth 1 -b deploy https://github.com/AllPoland/ArcViewer.git arcviewer
.venv\Scripts\python app.py
```

The `git clone` is optional (3D viewer). Also optional, only for generator stages 1 and 2: Java and `BeatKenja.jar` from [BeatKenja](https://github.com/Chrisvenator/BeatKenja) inside a `beatkenja` folder.

### Command line

```
.venv\Scripts\python generate.py "song.mp3" --nome "Song name" --artista "Artist" --capa "picture.jpg"
```

The map goes to `saida\<name>-v4.zip`, with `.relatorio.txt` and `.relatorio.json` next to it.

| Option | What it does |
|---|---|
| `--nome`, `--artista` | Optional. Without them the file tags are used, and failing that the file name ("Artist - Song"). |
| `--capa` | Without it the image embedded in the file is used, and failing that a generic one. |
| `--difs Normal,Hard` | Generates only some difficulties. |
| `--densidade 0.8` | From `0.8` to `1.3`: a lighter or fuller map. |
| `--prefs sem_topo,sem_fila,cruzar_nunca,sabres_capa,chroma,noodle` | The "The way you play" preferences (`cruzar_livre` also exists; with neither, a little). |
| `--etapa 1\|2\|3\|4` | Generator stage (default 4): 1 simple rhythm with BeatKenja swings, 2 density follows energy and choruses repeat, 3 swings from human patterns, 4 instrument separation and walls. |

### Tools

| Command | What for |
|---|---|
| `report.py <zip>` | Re-runs the checks on a map. |
| `tools\medir.py` | Notes per second, coverage, precision and correlation of the maps in `saida\`. Run it before and after changing the generator. |
| `tools\blind_test.py <a.zip> <b.zip>` | A shuffled A/B pair of the same song, to compare without knowing which is which. |
| `tools\batch.py <list.txt> <folder>` | Generates several songs and summarises the reports. |
| `tools\timing.py <audio>` | Measures how long each stage of the generation takes. |
| `tools\check_i18n.py` | Checks that both languages have the same phrases. |

Each module has a minimal test: `python generate.py --demo`, `python -m beatloom.engine --demo` and so on (the list is in [CLAUDE.md](CLAUDE.md)).

### Release

Write the `## v1.2.0` section in [CHANGELOG.md](CHANGELOG.md) (in Portuguese), commit, and push the tag: `git tag v1.2.0` and `git push origin v1.2.0`. CI (`.github\workflows\release.yml`) builds `beatloom-setup.exe` with Inno Setup (`installer\beatloom.iss`) and publishes the release with that section and, folded, the list of commits since the previous tag.

On every push, `.github\workflows\ci.yml` runs the `--demo` checks and `tools\check_i18n.py`.

### Colab and Kaggle

To generate in bulk on a Google Colab GPU (a YouTube playlist or a folder of audio files in your Drive), open [colab/beatloom.ipynb](https://colab.research.google.com/github/bps2414/beatloom/blob/main/colab/beatloom.ipynb). The same notebook runs on Kaggle. Each person runs it in their own account; it has no page and no viewer. The notebook has not actually been run there yet.

### Folders

```
start.bat            installs what is missing and opens the page
app.py               local server and the /api routes
generate.py          generates a map (command line)
report.py            checks a map and writes the report
beatloom\            the core: listening (audio.py), choosing swings (engine.py), lights (luzes.py), mods (mods.py),
                     checking (checks.py), first-run downloads (preparo.py), Quest over ADB (quest.py)
site\                the web page: app.html, app.css, app.js, the phrases in i18n\, the fonts
check\               schema validation with bsmap (Node)
tools\               pattern library, measuring, blind test, batch
installer\           the installer (Inno Setup)
colab\               the Colab and Kaggle notebook
docs\                how it works, roadmap and the redesign plan
```

Not in the repository, created as you use it: `bin\`, `arcviewer\`, `dados\`, `musicas\`, `saida\` and `beatloom.json` (your choices).

## Please be considerate

Maps made by this tool are automatic. If you share one, say so, and follow the rules of the site you upload to (BeatSaver requires AI-generated maps to be flagged). Only use music you have the right to use.

## Credits

Parity and map checks are ported from [bsmap and BeatSaber-MapCheck](https://github.com/KivalEvan) by Kival Evan. Beat tracking by beat_this (CPJKU), source separation by Demucs, viewer by ArcViewer (AllPoland), stage 1 swings by BeatKenja. Pattern data comes from maps published on [BeatSaver](https://beatsaver.com) by their mappers.

MIT license, see [LICENSE](LICENSE).
