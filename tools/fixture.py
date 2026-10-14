"""Musica de mentira para conferir o gerador onde nao ha o detector de batidas, o Demucs nem a biblioteca de padroes (a sessao na nuvem).

  python tools/fixture.py [--clima pesado] [--nome Fixture]       cria musicas/<nome>.egg e deixa a analise dele pronta no .cache
  python tools/fixture.py --gerar [args do generate.py]           cria e gera o mapa (com --sem-padroes se faltar a biblioteca)
  python tools/fixture.py --demo

A musica e sintetizada por instrumento (bateria, baixo, acordes e voz), a 120 BPM, com partes conhecidas: introducao, verso, subida, queda, pausa,
verso, subida, queda, final. O que o detector de batidas e o Demucs dariam (batidas.json e stems/) ja vai para o cache da analise, entao a analise
de verdade (ataques, forca, intensidade, voz, bateria) roda em cima dela; as partes e o clima sao gravados por cima com os valores conhecidos.
Sem a biblioteca de padroes, --sem-padroes troca o motor de golpes por um simples (as maos alternando para baixo e para cima): serve para ver luzes,
cenario e mods, nao a qualidade das notas.
"""
import json, runpy, subprocess, sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from beatloom.audio import CACHE, CAMADAS, analisar  # noqa: E402

SR, BPM, T0 = 44100, 120, 0.5  # a primeira batida em 0,5 s; compasso de 4 batidas = 2 s
PARTES = [("intro", 4), ("verso", 8), ("subida", 4), ("queda", 8), ("pausa", 2), ("verso", 4), ("subida", 4), ("queda", 8), ("verso", 2)]


def sintetizar(semente=0):
    """-> {instrumento: audio mono}, rotulo de cada compasso, tempo de cada batida."""
    rng = np.random.default_rng(semente)
    rot = [p for p, n in PARTES for _ in range(n)]
    nb = 4 * len(rot)
    bat = T0 + 60 / BPM * np.arange(nb + 1)
    dur = float(bat[-1]) + 2.5
    n = int(dur * SR)
    st = {k: np.zeros(n) for k in ("drums", "bass", "other", "vocals")}
    t = lambda s: np.arange(int(s * SR)) / SR

    def poe(k, ini, som):
        i = int(ini * SR)
        st[k][i:i + len(som)] += som[:max(0, n - i)]

    bumbo = np.sin(2 * np.pi * np.cumsum(np.linspace(150, 45, int(0.18 * SR))) / SR) * np.exp(-t(0.18) * 22)
    caixa = rng.normal(0, 1, int(0.14 * SR)) * np.exp(-t(0.14) * 30) * 0.7 + np.sin(2 * np.pi * 190 * t(0.14)) * np.exp(-t(0.14) * 40) * 0.5
    chimbal = np.diff(rng.normal(0, 1, int(0.04 * SR) + 1)) * np.exp(-t(0.04) * 90) * 0.25
    prato = np.diff(rng.normal(0, 1, int(1.2 * SR) + 1)) * np.exp(-t(1.2) * 3) * 0.35
    tons = [55.0, 65.41, 49.0, 58.27]  # a fundamental de cada compasso, em ciclo
    melodia = [69, 72, 74, 72, 76, 74, 72, 69]
    for k, p in enumerate(rot):
        b0, raiz = bat[4 * k], tons[k % 4]
        dt = 60 / BPM
        if p == "pausa":
            poe("other", b0, 0.12 * np.sin(2 * np.pi * raiz * 4 * t(4 * dt)) * np.hanning(len(t(4 * dt))))
            continue
        for j in range(4):
            tb = b0 + j * dt
            if p == "queda" or j in (0, 2):
                poe("drums", tb, bumbo * (0.6 if p == "intro" else 1.0))
            if p in ("verso", "queda") and j in (1, 3):
                poe("drums", tb, caixa)
            if p in ("verso", "queda"):
                poe("drums", tb, chimbal); poe("drums", tb + dt / 2, chimbal)
        if p == "subida":  # caixa cada vez mais rapida ate a queda
            passos = 4 * (1 + next(j for j in range(k + 1) if rot[k - j - 1] != "subida"))  # 4, 8, 12, 16 golpes por compasso
            for j in range(passos):
                poe("drums", b0 + j * 4 * dt / passos, caixa * (0.4 + 0.6 * j / passos))
        if p == "queda" and (k == 0 or rot[k - 1] != "queda" or k % 4 == 0):
            poe("drums", b0, prato)
        # baixo: a fundamental em colcheias na queda, em minimas no resto
        passo = dt / 2 if p == "queda" else 2 * dt
        for j in range(int(4 * dt / passo)):
            nota = t(passo * 0.9)
            poe("bass", b0 + j * passo, 0.5 * np.sign(np.sin(2 * np.pi * raiz * nota)) * np.exp(-nota * 3))
        # acordes: tres tons um pouco desafinados, o compasso inteiro
        nota = t(4 * dt)
        acorde = sum(np.sin(2 * np.pi * raiz * 4 * r * nota * (1 + 0.002 * i)) for i, r in enumerate((1, 1.26, 1.5)))
        poe("other", b0, (0.08 if p == "intro" else 0.12) * acorde * np.minimum(1, nota * 20) * np.exp(-nota * 0.4))
        # voz: notas de uma e duas batidas no verso e na queda, com vibrato
        if p in ("verso", "queda"):
            j = 0
            while j < 4:
                d = 2 if (k + j) % 3 == 0 else 1
                m = melodia[(k * 3 + j) % len(melodia)] + (5 if p == "queda" else 0)
                nota = t(d * dt * 0.92)
                f = 440 * 2 ** ((m - 69) / 12) * (1 + 0.006 * np.sin(2 * np.pi * 5.5 * nota))
                fase = 2 * np.pi * np.cumsum(f) / SR
                poe("vocals", b0 + j * dt, 0.22 * (np.sin(fase) + 0.4 * np.sin(2 * fase) + 0.2 * np.sin(3 * fase)) * np.minimum(1, nota * 30) * np.minimum(1, (nota[::-1]) * 20))
                j += d
    return st, rot, bat


def criar(nome="Fixture", clima="pesado", pasta=None):
    """Grava musicas/<nome>.egg e a analise dele no .cache (com as partes e o clima por cima). -> caminho do .egg"""
    import soundfile as sf
    pasta = Path(pasta or RAIZ / "musicas")
    pasta.mkdir(parents=True, exist_ok=True)
    st, rot, bat = sintetizar()
    mix = sum(st.values())
    escala = 0.9 / np.abs(mix).max()
    wav = pasta / f"{nome}.wav"
    sf.write(wav, mix * escala, SR)
    egg = pasta / f"{nome}.egg"  # do mesmo jeito que o generate.py grava o song.egg: o mesmo arquivo da a mesma analise
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-vn", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-c:a", "libvorbis",
                    "-q:a", "6", "-ar", "44100", "-f", "ogg", str(egg)], check=True)
    wav.unlink()
    import hashlib
    cache = CACHE / "analise" / hashlib.sha1(egg.read_bytes()).hexdigest()[:16]
    (cache / "stems").mkdir(parents=True, exist_ok=True)
    (cache / "batidas.json").write_text(json.dumps({"b": [float(x) for x in bat], "d": [float(x) for x in bat[::4]]}))
    for k, y in st.items():
        sf.write(cache / "stems" / f"{k}.wav", y * escala, SR)
    an = analisar(egg, instrumentos=True)
    for f in CAMADAS:  # as camadas de cima saem da analise de verdade, menos as partes e o clima, que sao as conhecidas
        if f in ("partes.json", "clima.json"):
            nc = len(an["ini_comp"]) - 1  # a analise estende as batidas ate o fim do audio: os compassos a mais ficam com a ultima parte
            (cache / f).write_text(json.dumps((rot + [rot[-1]] * nc)[:nc] if f == "partes.json" else clima))
    return egg


def golpes_simples(tempos, an, dif, reacao, etapa, njs=16, arcos=(), prefs=()):
    """No lugar do motor de golpes, sem a biblioteca de padroes: cada mao alterna para baixo e para cima; nota dupla = as duas maos juntas."""
    g, notas, vez, prox = an["grade"], [], 0, [1, 1]
    for i, q in sorted(tempos.items()):
        for c in ((0, 1) if q == 2 else (vez,)):
            d = prox[c]
            notas.append((float(g[i]), 1 + c, 0, c, d))
            prox[c] = 1 - d
        vez = 1 - vez if q == 1 else vez
    return notas, " | motor simples (tools/fixture.py --sem-padroes)", [], {}, []


def demo():
    st, rot, bat = sintetizar()
    assert len(rot) == 44 and rot[12:16] == ["subida"] * 4 and abs(bat[1] - bat[0] - 0.5) < 1e-9 and set(st) == {"drums", "bass", "other", "vocals"}
    pausa = slice(int(bat[4 * 24] * SR) + 2000, int(bat[4 * 26] * SR))  # compassos 24 e 25: pausa
    assert np.abs(st["drums"][pausa]).max() < 1e-6 and np.abs(st["vocals"][pausa]).max() < 1e-6 and np.abs(st["other"][pausa]).max() > 0.01
    notas = golpes_simples({0: 1, 4: 1, 8: 2, 12: 1}, {"grade": np.arange(20) / 4}, "Hard", 0.5, 4)[0]
    assert [(n[3], n[4]) for n in notas] == [(0, 1), (1, 1), (0, 0), (1, 0), (0, 1)]  # as maos alternam e cada uma vai para baixo e para cima
    print("fixture ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--demo"]:
        sys.exit(demo())
    opc = lambda k, pad: a[a.index(k) + 1] if k in a else pad
    egg = criar(opc("--nome", "Fixture"), opc("--clima", "pesado"))
    print(f"musica: {egg}")
    if "--gerar" in a:
        resto = a[a.index("--gerar") + 1:]
        if "--sem-padroes" in resto or not (RAIZ / "dados" / "padroes_Easy.pkl").exists() or (RAIZ / "dados" / "padroes_Easy.pkl").stat().st_size == 0:
            from beatloom import engine
            engine.golpes = golpes_simples
        resto = [x for x in resto if x != "--sem-padroes"]
        sys.argv = [str(RAIZ / "generate.py"), str(egg), *resto]
        runpy.run_path(str(RAIZ / "generate.py"), run_name="__main__")
