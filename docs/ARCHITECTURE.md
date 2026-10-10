# How Beatloom works

[Português (Brasil)](ARCHITECTURE.pt-BR.md)

Where the files are: `gerar.py`, `app.py` and `relatorio.py` in the root; `audio.py`, `motor.py` and `checks.py` in `beatloom\`; the rest in `ferramentas\` and `site\`.

This document follows a song on its way to becoming a map, one piece at a time. It does not assume you can program. File and function names are in Portuguese, like the code.

## The idea in one sentence

Beatloom answers two questions, one after the other: **when** there is a note (by listening to the song) and **which** note it is (by copying small pieces of maps made by people). Then it checks the result against rules, and only then hands over the zip.

```
 song (mp3, link)
        │
        ▼
 1. LISTEN       audio.py     beats, onsets, energy, choruses, instruments
        │
        ▼
 2. WHEN         gerar.py     picks the moments that get a note
        │
        ▼
 3. WHICH NOTE   motor.py     position, colour and direction of each note
        │
        ▼
 4. DECORATE     gerar.py     held notes, lights and walls
        │
        ▼
 5. PACK         gerar.py     Info.dat, difficulties, song.egg, cover → zip
        │
        ▼
 6. CHECK        relatorio.py report with the goals, next to the zip
```

## Three words used everywhere

- **Beat**: the pulse of the song, the one you tap your foot to. BPM is how many beats fit in a minute.
- **Slot** (`casa` in the code): each beat is split into 4 equal parts. Each part is a slot. A note can only sit on a slot, never between two. All the slots of a song form the **grid**.
- **Parity**: after a downward swing your arm is low, so the natural next swing for that hand is upward. A map that asks for two downward swings in a row with the same hand forces you to twist your wrist or reset your arm in the air. That is a parity error, and Beatloom lets none through.

## 1. Listen (`audio.py`)

First the song is converted to the format the game uses (`song.egg`). The analysis runs on that file, so the map lines up with what you will hear in the game.

- **Beats and bars.** A program called beat_this finds each beat and the start of each bar (a group of beats, nearly always 4). It tends to mark beats about 17 milliseconds late, so Beatloom corrects that by comparing with the real onsets in the sound.
- **Changing tempo.** A song played by a band speeds up and slows down a little. The grid follows the song instead of assuming a fixed BPM, with smoothing so it does not jitter.
- **Songs read at half speed.** If the song is read as very slow (under 100 BPM with 2-beat bars), Beatloom doubles the BPM.
- **Onsets.** An onset is the moment a sound starts (a snare hit, a guitar note). For each slot we record whether there is a strong onset, a weak one or none, and how strong it is.
- **Energy per bar.** A number from 0 to 1 that says how intense each bar is. This is what gives the chorus more notes than the verse.
- **Repeated bars.** The sound of each bar is compared with the others. When a bar matches an earlier one (the chorus coming back), we record which bar it copies.
- **Long notes.** When the vocals or the melody hit and hold the same note for at least a beat and a half (the "ahhh"), with no other strong onset in between, the stretch is marked to become a held note.
- **Separated instruments.** A program called Demucs splits the song into drums, bass, vocals and the rest. This is the slow part (a few minutes). We measured that onsets from the isolated drums are more accurate than onsets from the full mix, so they count for more.

All of this is stored in `.cache\`, so generating the same song again takes seconds instead of minutes.

## 2. When there is a note (`gerar.py`, function `escolher_tempos`)

Each difficulty has a **budget**: how many note moments per second it aims for (Normal 1.8, Hard 2.45, Expert 3.3, Expert+ 4.1) and the smallest gap allowed between two notes. The numbers sit near the lightest quarter of the human maps of each difficulty.

1. **Candidates.** Every slot with an onset is a candidate, except in the first 2 seconds and the last 3 (room for you to get ready and for the song to end).
2. **Priority.** Each candidate gets a priority: onset strength × position in the beat. On the beat counts most, halfway counts a little less, and quarter slots count little on Expert and zero on Normal and Hard. That is why they have no fast notes.
3. **Budget per bar.** The total budget is shared among the bars according to their energy. Inside a bar, the highest-priority candidates go in first, respecting the minimum gap.
4. **Repeated chorus.** A bar marked as a copy of another gets the same rhythm as the original instead of being chosen again. If it has onsets the original did not have, it is topped up to its own budget.
5. **Empty stretch.** If a stretch of 2 beats or more (4 on Normal) is left without notes and has at least 3 strong onsets inside, the strongest onset gets a note, until no such stretch is left.
6. **A breath before the chorus.** When the energy jumps from one bar to the next, the beat before is left empty and the first beat of the strong part comes in with a double note.
7. **Double notes.** The strongest onsets on the beat, with space before and after, become doubles (both hands together). If the song is slow and does not reach the minimum density for the difficulty, the share of doubles goes up, instead of inventing notes where there is no sound.

The output of this step is just a list: "these slots get a note; these get a double".

## 3. Which note (`motor.py`)

This is where the pattern library comes in. It was built by cutting hundreds of well-rated human maps into **windows** of 4, 2 and 1 beats. Each window keeps the layout of its notes and is labelled by its **rhythm** (which slots have a note). The library holds no music, only these layouts.

The engine walks through the song beat by beat:

1. It looks at the rhythm of the next 4 beats and searches the library for human windows with **exactly the same rhythm**.
2. It tests the candidates against the current state of your arms: where each saber is, which way the last swing went, how far the wrist is rotated. It drops the ones that break parity, the ones that need a move too fast for the hand, and the ones that create a defect (see below).
3. Among those left, it prefers windows where the arm arrives from the same place as in the original human map, and windows that leave the next beat easy to continue.
4. If no 4-beat window fits, it tries 2 beats, then 1. If nothing fits, it uses the last resort: straight up and down, each hand on its own side.

**Same chorus, same layout.** In a repeated bar, the engine tries to reuse the layout it used the first time. There is a catch: every note flips the side your arm is on, so about half the time you arrive at the chorus "from the other side" and the identical layout would be impossible. In that case it uses the same layout flipped top to bottom: same rhythm, same hands, same columns.

**Height by instrument.** Among equivalent patterns, drums tend to go low and vocals and melody go high.

**Verse differs from chorus.** An intense part prefers open layouts (upper rows, outer columns, diagonals); a calm part prefers simple up and down swings low. A layout that has already been used many times loses points, so the same one does not keep coming back.

**Arm speed.** Each difficulty has a cap on how far the same hand travels between two notes (6, 8, 10 and 12 slots per second), taken from the fastest 1% of the human maps. On Normal and Hard the arms never cross; on Expert and Expert+ crossing loses points. Normal also avoids diagonals.

**Held notes.** Where the song has a long note, both hands cut together at the start (upward from the bottom, or the reverse if the arm is on the other side), an arc links each note to the end note, which is cut the opposite way, and there is nothing in between. Normal does not use them.

**Safety net.** At the end, one pass fixes rare leftovers by changing only note positions (this never changes parity).

The defects it avoids:

- **Vision block**: a note in the middle of the view hiding the one right behind it.
- **Handclap**: both hands forced to cross or hit each other.
- **Stacked note**: two notes in the same place at the same time.
- **Saber passing through**: in a double, one hand's saber passing through the other colour's note.

## 4. Lights and walls (`gerar.py`)

- **Lights**: it is never dark; they flash on the beat and change colour in intense bars. Simple on purpose.
- **Walls**: only in pauses of 1.6 seconds or more, in the outer column. They are decoration; none of them makes you move.

## 5. Pack (`gerar.py`)

Through the whole process time is counted in seconds. Only when the file is written is it converted to the game's unit (beats). This avoids rounding errors.

The zip contains `Info.dat` (name, BPM, difficulties), one file per difficulty (v3 format, the one that accepts arcs), `song.egg` and the cover. The preview that plays in the game menu starts at the most intense part of the song. Note speed is 12, 14, 16 and 18 (the typical value in the human maps of the library).

**Name, artist and cover.** In this order: what you typed; the track and artist reported by yt-dlp; the file tags; the video title or the cleaned file name ("Artist - Song", without "Official Video" or "feat."). The cover comes from the picture you point to, the video thumbnail or the image embedded in the file, cropped to a square; the generic one is used only when all of those are missing. Album, year and link have no field of their own in `Info.dat`: they go in `_customData`, which the game ignores and the web page shows.

## 6. Check (`relatorio.py`, `checks.py`, `check\check.mjs`)

The finished map is read back and goes before two judges:

- **bsmap**, a community library, checks that the format is valid and counts parity errors. This is the outside opinion.
- **Our own rules** (`checks.py`), the same ones the engine uses in step 3: vision blocks, handclaps, stacked notes, saber passing through a note, notes on the grid, slack at the start and end, notes per second within range.

The report marks each goal `[ok]` or `[FALHOU]` (failed) and is saved next to the zip. Passing everything means "playable, no known defect". It does not mean "fun": no rule measures that.

## The four generator stages

`--etapa` switches the pieces on gradually. It exists to compare versions and see what each idea added.

| Stage | When | Which note |
|---|---|---|
| 1 | one budget for the whole song | BeatKenja (third-party program) |
| 2 | budget per bar, choruses repeat | BeatKenja |
| 3 | same as 2 | own engine with human patterns |
| 4 | same as 2, with separated instruments | own engine, height by instrument, walls |

## The web page (`app.py`, `site\app.html`)

A small server that only answers your own computer. Before generating it shows the cover and song data so you can fix them, and lets you choose difficulties and the amount of notes. It does three things: takes the link or file and calls `gerar.py` (one map at a time, because the analysis uses the whole processor), lists the zips in `saida\`, and hands the zip to ArcViewer, the 3D viewer embedded in the page. Links are downloaded with yt-dlp. Nothing is sent anywhere. It also renames a finished map, moves it to `saida\lixeira`, and sends it to the Quest (with the time in the folder name, so it is not mistaken for an older version).

## The pattern library (`ferramentas\baixar_mapas.py`, `ferramentas\extrair_padroes.py`)

`ferramentas\baixar_mapas.py` searches BeatSaver for maps with a high rating and many votes, made by people, without mods, and keeps only the note files (the audio is discarded). `ferramentas\extrair_padroes.py` cuts those maps into the windows described above, also in a mirrored version (left ↔ right), and writes one file per difficulty into `dados\`.

## What it cannot do yet

- Notes faster than a quarter of a beat, triplets and swing.
- Bombs, chains and dot notes.
- Understand song structure beyond "this bar equals that one" and "this one is more intense".
- Know whether the map is fun. That is what `ferramentas\teste_cego.py` is for: it shuffles two versions of the same song as A and B so you can play them without knowing which is which.
