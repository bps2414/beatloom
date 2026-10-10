r"""Relatorio automatico de um mapa (zip ou pasta). Funciona com mapa nosso, do Beat Sage ou humano.

  .venv\Scripts\python.exe report.py <mapa.zip> [--humano <pasta do mapa humano>]

Escreve <mapa>.relatorio.txt (texto) e <mapa>.relatorio.json (os mesmos dados, que o site le) ao lado do zip.
Sai com codigo 1 se alguma meta falhar. --so-json grava so o .json e nao imprime nada.
Os numeros nao dizem se o mapa e bom; dizem se ele tem os defeitos que os jogadores mais citam.
"""
import bisect, json, subprocess, sys, tempfile, zipfile
from pathlib import Path

import numpy as np

from beatloom import checks
from beatloom.audio import RAIZ, analisar

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


def conferir(mapa, humano=None):
    """-> dicionario com tudo o que o relatorio diz, em numeros e codigos: o site escreve no idioma de quem le, texto() escreve o .txt.

    `mapa` e zip ou pasta; `humano` e a pasta de um mapa humano da mesma musica.
    """
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
            hum[nome] = sorted({round(s, 3) for s in r["seg"]})

    R = {"versao": 1, "zip": mapa.name, "musica": info["_songName"], "dur": dur, "bpm": bpm, "bpm_detectado": an["bpm"], "bpm_fixo": bool(an["bpm_fixo"]),
         "info_ok": res[0]["ok"], "info_erro": res[0].get("erro", ""), "difs": []}
    fortes = grade[an["nivel"] == 2]
    for (nome, (arq, njs, off)), r in zip(difs.items(), res[1:]):
        D = {"nome": nome, "njs": njs, "offset": off, "esquema_ok": r["ok"], "erro": r.get("erro"), "notas": 0, "metas": []}
        R["difs"].append(D)
        if not r["ok"]:
            continue
        notas = sorted((s, n[1], n[2], n[3], n[4]) for n, s in zip(r["notas"], r["seg"]))  # seg = o tempo em segundos, ja com os eventos de BPM
        if not notas:
            continue
        ts = sorted({round(n[0], 4) for n in notas})
        hjd = checks.meio_salto(njs, bpm, off)
        reacao, salto = 60 / bpm * hjd, njs * 60 / bpm * hjd * 2
        casa = grade[np.clip(np.searchsorted(grade, ts), 1, len(grade) - 1)]
        casa0 = grade[np.clip(np.searchsorted(grade, ts) - 1, 0, len(grade) - 1)]
        na_grade = float(np.mean(np.minimum(np.abs(casa - ts), np.abs(casa0 - ts)) <= 0.03))
        nps = len(notas) / dur
        lo, hi = NPS.get(nome, (0, 99))
        ini, fim = ts[0], dur - ts[-1]
        onde = lambda v: {"n": len(v), "ex": [float(t) for t in v[:3]]}
        defeito = lambda i, v: {"id": i, "ok": not v, **onde(v)}
        D["metas"] = [
            {"id": "esquema", "ok": True},
            {"id": "paridade", "ok": r["erros"] == 0, "erros": r["erros"], "avisos": r["avisos"], "golpes": r["golpes"]},
            defeito("visao", checks.bloqueios_de_visao(notas, nome, reacao)), defeito("palmas", checks.palmas(notas)),
            defeito("empilhadas", checks.empilhadas(notas)), defeito("atravessadas", checks.atravessadas(notas)),
            {"id": "grade", "ok": na_grade >= 0.95, "fracao": na_grade},
            {"id": "folga_inicio", "ok": ini >= 1.5, "s": ini}, {"id": "folga_fim", "ok": fim >= 2, "s": fim},
            {"id": "nps", "ok": lo <= nps <= hi, "valor": nps, "faixa": [lo, hi]},
        ]
        dirs = np.bincount([n[4] for n in notas], minlength=9)
        D.update(notas=len(notas), tempos=len(ts), duplas=sum(1 for a, b in zip(notas, notas[1:]) if abs(a[0] - b[0]) < 0.005), bombas=len(r["bombas"]),
                 paredes=len(r["paredes"]), luzes=r["eventos"], arcos=r.get("arcos", 0), correntes=r.get("correntes", 0), nps=nps,
                 cruzadas=onde(checks.cruzadas(notas)), corridas=onde(checks.corridas(notas, checks.VEL_MAO.get(nome, 12))),
                 maior_pausa=float(max(np.diff(ts))) if len(ts) > 1 else 0, sobra_fim=fim, salto_m=salto, reacao_ms=reacao * 1000,
                 ataques_precisao=perto(ts, fortes, 0.05), ataques_cobertura=perto(fortes, ts, 0.05),
                 direcoes=[int(v) for v in dirs], linhas=[int(v) for v in np.bincount([n[2] for n in notas], minlength=3)])
        if nome in hum:
            D["humano"] = {"precisao": perto(ts, hum[nome], 0.05), "cobertura": perto(hum[nome], ts, 0.05)}
        if "ExpertPlus" in hum and nome != "ExpertPlus":
            D["humano_expertplus"] = perto(ts, hum["ExpertPlus"], 0.05)
        # notas por segundo por trecho de 4 compassos, ao lado da intensidade
        bat, ic, intens = an["batidas"], an["ini_comp"], an["intens"]
        D["trechos"] = []
        for k in range(0, len(ic) - 1, 4):
            a, b = bat[ic[k]], bat[ic[min(k + 4, len(ic) - 1)]]
            # 5 ms de folga: a nota em cima da barra do compasso e do trecho que comeca ali, mesmo com o arredondamento da batida
            D["trechos"].append([float(a), float(np.mean(intens[k:k + 4])), sum(1 for x in notas if a - 0.005 <= x[0] < b - 0.005) / max(b - a, 1e-9)])
        cor = np.corrcoef([t[1] for t in D["trechos"]], [t[2] for t in D["trechos"]])[0, 1] if len(D["trechos"]) > 2 else float("nan")
        D["correlacao"] = None if np.isnan(cor) else float(cor)
    R["passou"] = R["info_ok"] and all(d["esquema_ok"] and d["notas"] and all(m["ok"] for m in d["metas"]) for d in R["difs"])
    return R


ROTULO = {"esquema": "esquema valido (bsmap)", "paridade": "erros de paridade = 0", "visao": "bloqueios de visao = 0", "palmas": "palmas = 0",
          "empilhadas": "notas empilhadas = 0", "atravessadas": "duplas com sabre passando pela outra nota = 0",
          "grade": ">= 95% dos tempos na grade de 1/4 (30 ms)", "folga_inicio": "folga no inicio >= 1,5 s", "folga_fim": "folga no fim >= 2 s"}


def _valor(m):
    i = m["id"]
    if i == "esquema":
        return "ok"
    if i == "paridade":
        return f"{m['erros']} erros, {m['avisos']} avisos em {m['golpes']} golpes"
    if i == "grade":
        return f"{m['fracao']:.1%}"
    if i in ("folga_inicio", "folga_fim"):
        return f"{m['s']:.2f} s"
    if i == "nps":
        return f"{m['valor']:.2f}"
    return f"{m['n']}" + (f" (ex.: {m['ex'][0]:.1f}s)" if m["ex"] else "")


def texto(R):
    """O relatorio em texto (portugues), a partir do que conferir() devolveu."""
    L, falhas = [], []
    L.append(f"RELATORIO  {R['zip']}")
    L.append(f"musica: {R['musica']} | {R['dur']:.0f} s | BPM do mapa {R['bpm']} | BPM detectado {R['bpm_detectado']} ({'fixo' if R['bpm_fixo'] else 'variavel'})")
    L.append(f"Info.dat: {'esquema ok' if R['info_ok'] else 'ESQUEMA INVALIDO ' + R['info_erro']}")
    if not R["info_ok"]:
        falhas.append("Info.dat invalido")
    for D in R["difs"]:
        nome = D["nome"]
        L.append("")
        L.append(f"== {nome}  (NJS {D['njs']}, offset {D['offset']})")
        if not D["esquema_ok"]:
            L.append(f"  ESQUEMA INVALIDO: {D['erro']}")
            falhas.append(f"{nome}: esquema invalido")
            continue
        if not D["notas"]:
            L.append("  sem notas"); falhas.append(f"{nome}: sem notas"); continue
        for m in D["metas"]:
            txt, val = ROTULO.get(m["id"]) or f"NPS na faixa {m['faixa'][0]}-{m['faixa'][1]}", _valor(m)
            L.append(f"  [{'ok' if m['ok'] else 'FALHOU'}] {txt}: {val}")
            if not m["ok"]:
                falhas.append(f"{nome}: {txt} ({val})")
        L.append(f"  notas {D['notas']} em {D['tempos']} tempos | {D['duplas']} duplas | bombas {D['bombas']} | paredes {D['paredes']} | eventos de luz {D['luzes']}")
        ex = lambda v: f"{v['n']} ({1000 * v['n'] / D['notas']:.0f} a cada mil notas" + (", ex.: " + ", ".join(f"{t:.1f}s" for t in v["ex"]) if v["ex"] else "") + ")"
        L.append(f"  notas seguradas (arcos) {D['arcos']} | correntes {D.get('correntes', 0)} | bracos cruzados {ex(D['cruzadas'])} | trocas de posicao rapidas demais para a mao {ex(D['corridas'])}")
        L.append(f"  maior pausa sem nota {D['maior_pausa']:.1f} s | sobra de musica depois da ultima nota {D['sobra_fim']:.1f} s | distancia de salto {D['salto_m']:.1f} m | tempo de reacao {D['reacao_ms']:.0f} ms")
        L.append(f"  tempos com ataque forte detectado a ate 50 ms: {D['ataques_precisao']:.0%} | ataques fortes que viraram nota: {D['ataques_cobertura']:.0%}")
        dirs, lin = D["direcoes"], D["linhas"]
        L.append(f"  direcoes cima/baixo/esq/dir/diagonais/ponto: {dirs[0]}/{dirs[1]}/{dirs[2]}/{dirs[3]}/{sum(dirs[4:8])}/{dirs[8]} | linhas baixo/meio/cima: {lin[0]}/{lin[1]}/{lin[2]}")
        if "humano" in D:
            L.append(f"  contra o mapa humano {nome}: precisao {D['humano']['precisao']:.0%} (nossos tempos que o humano tambem usou) | cobertura {D['humano']['cobertura']:.0%} (tempos do humano que temos)")
        if "humano_expertplus" in D:
            L.append(f"  contra o humano Expert+: precisao {D['humano_expertplus']:.0%}")
        cor = float("nan") if D["correlacao"] is None else D["correlacao"]
        L.append(f"  NPS por trecho de 4 compassos (inicio, intensidade 0-1, NPS) | correlacao intensidade x NPS: {cor:.2f}")
        linha = [f"{a:4.0f}s i{i:.1f} {n:4.1f}" for a, i, n in D["trechos"]]
        for i in range(0, len(linha), 6):
            L.append("    " + " | ".join(linha[i:i + 6]))
    L.append("")
    L.append("RESULTADO: " + ("TODAS AS METAS OK" if not falhas else f"{len(falhas)} META(S) FALHARAM"))
    L.extend("  - " + f for f in falhas)
    return "\n".join(L)


def gravar_json(mapa, R):
    """O relatorio em dados, ao lado do zip: e o que o site le."""
    Path(mapa).with_suffix(".relatorio.json").write_text(json.dumps(R, ensure_ascii=False, default=float), encoding="utf-8")


def relatorio(mapa, humano=None):
    """-> (texto, passou)."""
    R = conferir(mapa, humano)
    return texto(R), R["passou"]


def demo():
    D = {"nome": "Hard", "njs": 14, "offset": 0.1, "esquema_ok": True, "erro": None, "notas": 2, "tempos": 2, "duplas": 0, "bombas": 0, "paredes": 0, "luzes": 3,
         "arcos": 0, "cruzadas": {"n": 0, "ex": []}, "corridas": {"n": 1, "ex": [3.25]}, "maior_pausa": 1, "sobra_fim": 3, "salto_m": 18, "reacao_ms": 600,
         "ataques_precisao": 1, "ataques_cobertura": 0.5, "direcoes": [1, 1, 0, 0, 0, 0, 0, 0, 0], "linhas": [2, 0, 0], "trechos": [[0, 0.5, 1]], "correlacao": None,
         "metas": [{"id": "palmas", "ok": False, "n": 2, "ex": [1.04, 2]}, {"id": "nps", "ok": True, "valor": 2, "faixa": [1.73, 5.22]}]}
    t = texto({"zip": "a.zip", "musica": "A", "dur": 60, "bpm": 120, "bpm_detectado": 120.0, "bpm_fixo": True, "info_ok": True, "info_erro": "", "difs": [D]})
    assert "  [FALHOU] palmas = 0: 2 (ex.: 1.0s)" in t and "  [ok] NPS na faixa 1.73-5.22: 2.00" in t, t
    assert "trocas de posicao rapidas demais para a mao 1 (500 a cada mil notas, ex.: 3.2s)" in t and t.endswith("1 META(S) FALHARAM\n  - Hard: palmas = 0 (2 (ex.: 1.0s))"), t
    print("relatorio ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a == ["--demo"]:
        sys.exit(demo())
    R = conferir(a[0], a[a.index("--humano") + 1] if "--humano" in a else None)
    gravar_json(a[0], R)
    if "--so-json" in a:  # mapa antigo conferido pelo site: o .txt dele (que tem tambem o resumo do gerador) fica como esta
        sys.exit(0)
    Path(a[0]).with_suffix(".relatorio.txt").write_text(texto(R), encoding="utf-8")
    print(texto(R))
    sys.exit(0 if R["passou"] else 1)
