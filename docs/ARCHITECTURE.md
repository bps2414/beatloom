# How Beatloom works

[Português (Brasil)](ARCHITECTURE.pt-BR.md)

Where the files are: `generate.py`, `app.py` and `report.py` in the root; `audio.py`, `engine.py` and `checks.py` in `beatloom\`; the rest in `tools\` and `site\`.

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
 2. WHEN         generate.py     picks the moments that get a note
        │
        ▼
 3. WHICH NOTE   engine.py     position, colour and direction of each note
        │
        ▼
 4. DECORATE     generate.py, luzes.py     held notes, lights, colours, environment and walls
        │
        ▼
 5. PACK         generate.py     Info.dat, difficulties, song.egg, cover → zip
        │
        ▼
 6. CHECK        report.py report with the goals, next to the zip
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
- **Song parts.** Neighbouring bars that sound alike in timbre and harmony are grouped into sections, and each bar gets a label: intro, verse, build-up (the bars leading into the full part), drop (the full part: chorus or drop) or break (near silence with no onsets).
- **Sung voice.** On the separated vocal track, Beatloom follows the sung pitch (pYIN, from librosa). That gives the syllables (where a new note starts), the pitch of each one and the long notes.
- **Drum pieces.** On the separated drum track, each onset is classified by frequency band: kick (low), snare (mid), cymbal (high) and crash (highs that keep ringing).
- **Long notes.** A sung note held for at least a beat and a half (the "ahhh") is marked to become a held note. For the melody it counts when the instrument hits and holds the same note, with no other strong onset in between.
- **Separated instruments.** A program called Demucs splits the song into drums, bass, vocals and the rest. This is the slow part (a few minutes). We measured that onsets from the isolated drums are more accurate than onsets from the full mix, so they count for more.

All of this is stored in `.cache\`, so generating the same song again takes seconds instead of minutes.

## 2. When there is a note (`generate.py`, function `escolher_tempos`)

Each difficulty has a **budget**: how many note moments per second it aims for (Easy 1.25, Normal 1.8, Hard 2.45, Expert 3.3, Expert+ 4.1) and the smallest gap allowed between two notes. The numbers sit near the lightest quarter of the human maps of each difficulty.

1. **Candidates.** Every slot with an onset is a candidate, except in the first 2 seconds and the last 3 (room for you to get ready and for the song to end). The start of a sung syllable is also a candidate, weighted between a strong onset and a weak one.
2. **Priority.** Each candidate gets a priority: onset strength × position in the beat. On the beat counts most, halfway counts a little less, and quarter slots count little on Expert and zero on Easy, Normal and Hard. That is why they have no fast notes.
3. **Budget per bar.** The total budget is shared among the bars according to their energy and the part of the song: the drop gets 10% more, the build-up starts 20% lower and reaches the drop 20% higher, and a break gets no notes. Inside a bar, the highest-priority candidates go in first, respecting the minimum gap.
4. **Repeated chorus.** A bar marked as a copy of another gets the same rhythm as the original instead of being chosen again. If it has onsets the original did not have, it is topped up to its own budget.
5. **Empty stretch.** If a stretch of 2 beats or more (4 on Normal) is left without notes and has at least 3 strong onsets inside, the strongest onset gets a note, until no such stretch is left.
6. **A breath before the chorus.** When the energy jumps from one bar to the next, the beat before is left empty and the first beat of the strong part comes in with a double note.
7. **Double notes.** The strongest onsets on the beat, with space before and after, become doubles (both hands together); crash cymbals go first. If the song is slow and does not reach the minimum density for the difficulty, the share of doubles goes up, instead of inventing notes where there is no sound.

The output of this step is just a list: "these slots get a note; these get a double".

## 3. Which note (`engine.py`)

This is where the pattern library comes in. It was built by cutting hundreds of well-rated human maps into **windows** of 4, 2 and 1 beats. Each window keeps the layout of its notes and is labelled by its **rhythm** (which slots have a note). The library holds no music, only these layouts.

The engine walks through the song beat by beat:

1. It looks at the rhythm of the next 4 beats and searches the library for human windows with **exactly the same rhythm**.
2. It tests the candidates against the current state of your arms: where each saber is, which way the last swing went, how far the wrist is rotated. It drops the ones that break parity, the ones that need a move too fast for the hand, and the ones that create a defect (see below).
3. Among those left, it prefers windows where the arm arrives from the same place as in the original human map. A join between two windows that human maps almost never make (the rarest position changes, which add up to 2% of all of them in the library) loses points. From Hard up, a window that comes from better-rated maps gains a little.
4. The five best candidates are then rehearsed up to 8 beats ahead, each one followed by the best choice for every next window. The one that leaves the rest of the phrase in better shape wins: larger windows that still fit, a repeated layout that can come back, no fall to the last resort.
5. If no 4-beat window fits, it tries 2 beats, then 1. If nothing fits, it uses the last resort: straight up and down, each hand on its own side.

**Same chorus, same layout.** In a repeated bar, the engine tries to reuse the layout it used the first time. There is a catch: every note flips the side your arm is on, so about half the time you arrive at the chorus "from the other side" and the identical layout would be impossible. In that case it uses the same layout flipped top to bottom: same rhythm, same hands, same columns.

**Motif and variation.** A repeat is not always a copy. The second time a bar comes back (and the sixth, the tenth...) the engine first tries the layout mirrored left to right, so the hands swap roles. The third time it tries the same layout with one more accent: on the strongest on-beat hit where only one hand plays, the other joins in beside it. If the variation does not fit, the plain layout is used.

**Height by instrument.** Among equivalent patterns, drums tend to go low (kick on the bottom row, snare on the middle one) and vocals and melody go high. Where a sung syllable starts with no strong drum hit on it, the voice decides: a note higher than the phrase around it goes up, a lower one goes down, and a rising melody prefers an upward cut. This is a preference, not a rule: parity and defects come first, so only part of the notes follow the voice.

**Swing size.** The strongest quarter of the onsets in the map prefers a note far from where the hand was (wide arm); the weakest quarter prefers a near one (short swing).

**Verse differs from chorus.** An intense part prefers open layouts (upper rows, outer columns, diagonals); a calm part prefers simple up and down swings low. A layout that has already been used many times loses points, so the same one does not keep coming back.

**Arm speed.** Each difficulty has a cap on how far the same hand travels between two notes (6, 8, 10 and 12 slots per second), taken from the fastest 1% of the human maps. Normal also avoids diagonals.

**Crossed arms.** On Easy, Normal and Hard the arms never cross. On Expert and Expert+ it is the player's choice, in Settings: never, a little (the default: at most 8 crossings per thousand notes on Expert and 20 on Expert+, which is the quarter of the human maps that crosses least) or free (crossing only loses points).

**Stacks.** After the swings are chosen, the strongest accents of the intense parts get a stack: a second note of the same colour in the next cell along the cut, so one swing goes through both. Hard gets about 3 per thousand notes, Expert 8 and Expert+ 15, close to the lighter human maps. On Expert and Expert+ one stack per map becomes a tower of three notes. A stack only goes where the hand is free for a quarter of a second before and after and where it creates no defect.

**Held notes.** Where the song has a long note, both hands cut together at the start (upward from the bottom, or the reverse if the arm is on the other side), an arc links each note to the end note, which is cut the opposite way, and there is nothing in between. Normal does not use them. They go in from longest to shortest, at most one for every 20 seconds of song.

**Safety net.** At the end, one pass fixes rare leftovers by changing only note positions (this never changes parity).

The defects it avoids:

- **Vision block**: a note in the middle of the view hiding the one right behind it.
- **Handclap**: both hands forced to cross or hit each other.
- **Stacked note**: two notes in the same place at the same time.
- **Saber passing through**: in a double, one hand's saber passing through the other colour's note.

## 4. Lights, colours, environment and walls (`beatloom/luzes.py`, `generate.py`)

- **Lights**: they follow the song sections and the drums. The generator writes "cues" (when, which light, what it does, colour, brightness) and only at the end turns them into map events. Intro and verse keep the back lights on and pulse the rings on the kick; the build-up starts almost dark and turns on one light after another; right before the drop everything goes off; the drop comes in with a white flash, everything on, lasers hitting on the snare and rings spinning on the kick; a break stays dark. A crash cymbal gives a white flash.
- **Colours**: taken from the cover. The most common tone and the second one (or its opposite, when the cover has a single tone) are the light colours; another pair comes in on the drops. Sabers and notes only use them if you turn the option on, and only when the two tones are clearly different. A grey cover keeps the game colours.
- **Environment**: follows the mood of the song. Machine tempo or drums in front of everything is "electronic", a noisy sound is "heavy", the rest is "calm". Each mood has a classic environment and a new one; the song decides which. Classic ones light up with basic events, new ones with light groups, and the same cue script feeds both.
- **Walls**: in pauses of 1.6 seconds or more and at the start of each drop, in the outer column, where there is no note. They are decoration; none of them makes you move.

## 5. Pack (`generate.py`)

Through the whole process time is counted in seconds. Only when the file is written is it converted to the game's unit (beats). This avoids rounding errors.

**Changing tempo.** When the BPM is not fixed, each difficulty file carries BPM events: one for each stretch where the tempo changes, keeping bar starts within 10 milliseconds of the grid. That way the game and the editors draw the grid in the right place. The BPM in `Info.dat` is still the median one.

The zip contains `Info.dat` (name, BPM, difficulties), one file per difficulty (v3 format, the one that accepts arcs), `song.egg` and the cover. The preview that plays in the game menu starts at the most intense part of the song. Note speed is 10, 12, 14, 16 and 18 (the typical value in the human maps of the library).

**Name, artist and cover.** In this order: what you typed; the track and artist reported by yt-dlp; the file tags; the video title or the cleaned file name ("Artist - Song", without "Official Video" or "feat."). The cover comes from the picture you point to, the video thumbnail or the image embedded in the file, cropped to a square; the generic one is used only when all of those are missing. Album, year and link have no field of their own in `Info.dat`: they go in `_customData`, which the game ignores and the web page shows.

## 6. Check (`report.py`, `checks.py`, `check\check.mjs`)

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

The page generates at stage 4. Its "fast mode" is stage 3: separating the instruments is about 70% of the time, so it runs about 6 times faster, without held notes or walls. The analysis runs on the graphics card when the installed torch has CUDA (NVIDIA) and falls back to the processor if the card fails (`dispositivo()` and `na_placa()` in `beatloom\audio.py`). `tools\timing.py <audio>` measures how long each part takes.

## The web page (`app.py`, `site\`)

A small server that only answers your own computer. Before generating it shows the cover and song data so you can fix them, and lets you choose difficulties and the amount of notes. It does three things: takes the link or file and calls `generate.py` (one map at a time, because the analysis uses the whole processor), lists the zips in `saida\`, and hands the zip to ArcViewer, the 3D viewer embedded in the page. Links are downloaded with yt-dlp. Nothing is sent anywhere. It also regenerates a single difficulty of a finished map with a different amount of notes, renames it, moves it to `saida\lixeira`, and sends it to the Quest over ADB (`beatloom\quest.py`; each map becomes the folder `beatloom-<zip name>`, so sending again replaces the old version). On first run it checks what is missing and downloads it into the project folder (`beatloom\preparo.py`).

The page is plain HTML, CSS and JS with no build step (`site\app.html`, `app.css`, `app.js`) and asks for nothing outside your computer except the video thumbnail when you paste a link. Every phrase lives in `site\i18n\pt.json` and `en.json`; the server only answers with codes and numbers. That includes the checks: `report.py` writes `<zip>.relatorio.json` next to the text report and the page writes each check in the chosen language. A map made before that file existed is checked in the background the first time you open it. While instruments are being separated the generator prints `[sep] N` and the page turns it into a progress bar.

## The pattern library (`tools\download_maps.py`, `tools\extract_patterns.py`)

`tools\download_maps.py` searches BeatSaver for maps with a high rating and many votes, made by people, without mods, and keeps only the note files (the audio is discarded). `tools\extract_patterns.py` cuts those maps into the windows described above, also in a mirrored version (left ↔ right), and writes one file per difficulty into `dados\`. A window from a better-rated map weighs more: by its position in the rating order, from 0.5 for the lowest-rated map of the set to 2 for the best.

## What it cannot do yet

- Notes faster than a quarter of a beat, triplets and swing.
- Bombs, chains and dot notes.
- Understand song structure beyond "this bar equals that one" and "this one is more intense".
- Know whether the map is fun. That is what `tools\blind_test.py` is for: it shuffles two versions of the same song as A and B so you can play them without knowing which is which.
