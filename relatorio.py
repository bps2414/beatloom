r"""Relatorio automatico de um mapa (zip ou pasta). Funciona com mapa nosso, do Beat Sage ou humano.

  .venv\Scripts\python.exe relatorio.py <mapa.zip> [--humano <pasta do mapa humano>]

Escreve <mapa>.relatorio.txt ao lado do zip. Sai com codigo 1 se alguma meta falhar.
Os numeros nao dizem se o mapa e bom; dizem se ele tem os defeitos que os jogadores mais citam.
"""
import bisect, json, subprocess, sys, tempfile, zipfile
from pathlib import Path

import numpy as np

import checks
from audio import RAIZ, analisar

# faixa de notas por segundo de cada dificuldade (wiki do BSMG)
NPS = {"Easy": (0.82, 2.29), "Normal": (1.05, 3.41), "Hard": (1.73, 5.22), "Expert": (2.42, 7.81), "ExpertPlus": (3.21, 10.66)}


def perto(a, b, tol):
    """Fracao dos tempos de a que tem algum tempo de b a ate tol segundos."""
    b, hit = sorted(b), 0
    for t in a:
        i = bisect.bisect_left(b, t)
        hit += any(abs(t - b[j]) <= tol for j in (i - 1, i) if 0 <= j < len(b))
    return hit / max(len(a), 1)


def bsmap(bpm, dur, arquivos):
    r = subprocess.run(["node", "check.mjs", "--json", str(bpm), str(dur), *[str(Path(a).resolve()) for a in arquivos]],
                       cwd=RAIZ / "check", capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit("verificador bsmap falhou: " + r.stderr[-500:])
    return json.loads(r.stdout)


def ler_mapa(pasta):
    """-> (info, {dificuldade: (arquivo, njs, offset)}) do modo Standard."""
    info_p = next(p for p in Path(pasta).rglob("*") if p.name.lower() == "info.dat")
    info = json.loads(info_p.read_text(encoding="utf-8-sig"))
    difs = {b["_difficulty"]: (info_p.parent / b["_beatmapFilename"], b["_noteJumpMovementSpeed"], b.get("_noteJumpStartBeatOffset", 0))
            for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == "Standard" for b in s["_difficultyBeatmaps"]}
    return info_p, info, difs


def relatorio(mapa, humano=None):
    """-> (texto, passou). `mapa` e zip ou pasta; `humano` e a pasta de um mapa humano da mesma musica."""
    mapa = Path(mapa)
    with tempfile.TemporaryDirectory(dir=RAIZ / ".cache") as tmp:
        pasta = mapa
        if mapa.suffix.lower() == ".zip":
            zipfile.ZipFile(mapa).extractall(tmp)
            pasta = Path(tmp)
        info_p, info, difs = ler_mapa(pasta)
        bpm = info["_beatsPerMinute"]
        an = analisar(info_p.parent / info["_songFilename"])
        dur, grade = an["dur"], an["grade"]
        res = bsmap(bpm, dur, [info_p, *[d[0] for d in difs.values()]])
    hum = {}
    if humano:
        _, hinfo, hdifs = ler_mapa(humano)
        for nome, r in zip(hdifs, bsmap(hinfo["_beatsPerMinute"], dur, [d[0] for d in hdifs.values()])):
            hum[nome] = sorted({round(n[0] * 60 / hinfo["_beatsPerMinute"], 3) for n in r["notas"]})

    L, falhas = [], []
    L.append(f"RELATORIO  {mapa.name}")
    L.append(f"musica: {info['_songName']} | {dur:.0f} s | BPM do mapa {bpm} | BPM detectado {an['bpm']} ({'fixo' if an['bpm_fixo'] else 'variavel'})")
    L.append(f"Info.dat: {'esquema ok' if res[0]['ok'] else 'ESQUEMA INVALIDO ' + res[0].get('erro', '')}")
    if not res[0]["ok"]:
        falhas.append("Info.dat invalido")
    fortes = grade[an["nivel"] == 2]
    for (nome, (arq, njs, off)), r in zip(difs.items(), res[1:]):
        L.append("")
        L.append(f"== {nome}  (NJS {njs}, offset {off})")
        if not r["ok"]:
            L.append(f"  ESQUEMA INVALIDO: {r['erro']}")
            falhas.append(f"{nome}: esquema invalido")
            continue
        notas = sorted((n[0] * 60 / bpm, n[1], n[2], n[3], n[4]) for n in r["notas"])
        if not notas:
            L.append("  sem notas"); falhas.append(f"{nome}: sem notas"); continue
        ts = sorted({round(n[0], 4) for n in notas})
        hjd = checks.meio_salto(njs, bpm, off)
        reacao, salto = 60 / bpm * hjd, njs * 60 / bpm * hjd * 2
        vb = checks.bloqueios_de_visao(notas, nome, reacao)
        pal, emp = checks.palmas(notas), checks.empilhadas(notas)
        casa = grade[np.clip(np.searchsorted(grade, ts), 1, len(grade) - 1)]
        casa0 = grade[np.clip(np.searchsorted(grade, ts) - 1, 0, len(grade) - 1)]
        na_grade = float(np.mean(np.minimum(np.abs(casa - ts), np.abs(casa0 - ts)) <= 0.03))
        nps = len(notas) / dur
        lo, hi = NPS.get(nome, (0, 99))
        ini, fim = ts[0], dur - ts[-1]
        pausa = max(np.diff(ts)) if len(ts) > 1 else 0
        duplas = sum(1 for a, b in zip(notas, notas[1:]) if abs(a[0] - b[0]) < 0.005)
        metas = [
            ("esquema valido (bsmap)", True, "ok"),
            ("erros de paridade = 0", r["erros"] == 0, f"{r['erros']} erros, {r['avisos']} avisos em {r['golpes']} golpes"),
            ("bloqueios de visao = 0", not vb, f"{len(vb)}" + (f" (ex.: {vb[0]:.1f}s)" if vb else "")),
            ("palmas = 0", not pal, f"{len(pal)}" + (f" (ex.: {pal[0]:.1f}s)" if pal else "")),
            ("notas empilhadas = 0", not emp, f"{len(emp)}" + (f" (ex.: {emp[0]:.1f}s)" if emp else "")),
            (">= 95% dos tempos na grade de 1/4 (30 ms)", na_grade >= 0.95, f"{na_grade:.1%}"),
            ("folga no inicio >= 1,5 s", ini >= 1.5, f"{ini:.2f} s"),
            ("folga no fim >= 2 s", fim >= 2, f"{fim:.2f} s"),
            (f"NPS na faixa {lo}-{hi}", lo <= nps <= hi, f"{nps:.2f}"),
        ]
        for txt, ok, val in metas:
            L.append(f"  [{'ok' if ok else 'FALHOU'}] {txt}: {val}")
            if not ok:
                falhas.append(f"{nome}: {txt} ({val})")
        L.append(f"  notas {len(notas)} em {len(ts)} tempos | {duplas} duplas | bombas {len(r['bombas'])} | paredes {len(r['paredes'])} | eventos de luz {r['eventos']}")
        L.append(f"  maior pausa sem nota {pausa:.1f} s | sobra de musica depois da ultima nota {fim:.1f} s | distancia de salto {salto:.1f} m | tempo de reacao {reacao * 1000:.0f} ms")
        L.append(f"  tempos com ataque forte detectado a ate 50 ms: {perto(ts, fortes, 0.05):.0%} | ataques fortes que viraram nota: {perto(fortes, ts, 0.05):.0%}")
        dirs = np.bincount([n[4] for n in notas], minlength=9)
        lin = np.bincount([n[2] for n in notas], minlength=3)
        L.append(f"  direcoes cima/baixo/esq/dir/diagonais/ponto: {dirs[0]}/{dirs[1]}/{dirs[2]}/{dirs[3]}/{dirs[4:8].sum()}/{dirs[8]} | linhas baixo/meio/cima: {lin[0]}/{lin[1]}/{lin[2]}")
        if nome in hum:
            L.append(f"  contra o mapa humano {nome}: precisao {perto(ts, hum[nome], 0.05):.0%} (nossos tempos que o humano tambem usou) | cobertura {perto(hum[nome], ts, 0.05):.0%} (tempos do humano que temos)")
        if "ExpertPlus" in hum and nome != "ExpertPlus":
            L.append(f"  contra o humano Expert+: precisao {perto(ts, hum['ExpertPlus'], 0.05):.0%}")
        # notas por segundo por trecho de 4 compassos, ao lado da intensidade
        bat, ic, intens = an["batidas"], an["ini_comp"], an["intens"]
        linha, dados = [], []
        for k in range(0, len(ic) - 1, 4):
            a, b = bat[ic[k]], bat[ic[min(k + 4, len(ic) - 1)]]
            n = sum(1 for x in notas if a <= x[0] < b)
            dados.append((float(np.mean(intens[k:k + 4])), n / max(b - a, 1e-9)))
            linha.append(f"{a:4.0f}s i{dados[-1][0]:.1f} {dados[-1][1]:4.1f}")
        cor = np.corrcoef([d[0] for d in dados], [d[1] for d in dados])[0, 1] if len(dados) > 2 else float("nan")
        L.append(f"  NPS por trecho de 4 compassos (inicio, intensidade 0-1, NPS) | correlacao intensidade x NPS: {cor:.2f}")
        for i in range(0, len(linha), 6):
            L.append("    " + " | ".join(linha[i:i + 6]))
    L.append("")
    L.append("RESULTADO: " + ("TODAS AS METAS OK" if not falhas else f"{len(falhas)} META(S) FALHARAM"))
    L.extend("  - " + f for f in falhas)
    return "\n".join(L), not falhas


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    hum = a[a.index("--humano") + 1] if "--humano" in a else None
    txt, ok = relatorio(a[0], hum)
    Path(a[0]).with_suffix(".relatorio.txt").write_text(txt, encoding="utf-8")
    print(txt)
    sys.exit(0 if ok else 1)
