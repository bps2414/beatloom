r"""Monta a biblioteca de padroes a partir dos mapas humanos em dados\mapas (ver baixar_mapas.py).

  .venv\Scripts\python.exe ferramentas\extrair_padroes.py

Um padrao e o que um mapper humano colocou numa janela de 1, 2 ou 4 batidas, guardado pela "mascara" de ritmo
(quantas notas em cada casa de 1/4). So entram janelas limpas: tudo na grade de 1/4, sem bombas, sem notas de ponto,
sem pilhas, sem aviso de paridade. Cada padrao guarda tambem a nota anterior de cada mao, para o motor encaixar
onde o braco esta no mesmo lugar. Tambem calcula NJS e densidade tipicos por dificuldade.
"""
import json, pickle, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ))  # a raiz do projeto, onde esta a pasta beatloom
from beatloom import checks

DADOS = RAIZ / "dados"
ESPELHO = {0: 0, 1: 1, 2: 3, 3: 2, 4: 5, 5: 4, 6: 7, 7: 6}
JANELAS = (4, 2, 1)
MAX_POR_MASCARA = 4000


def ler(arq):
    """-> (notas [(batida, x, y, cor, dir, angulo)], batidas com bomba, intervalos de correntes) ou None."""
    m = json.loads(arq.read_text(encoding="utf-8-sig"))
    if "_notes" in m:
        ns = [(n["_time"], n["_lineIndex"], n["_lineLayer"], n["_type"], n["_cutDirection"], 0) for n in m["_notes"]]
        return [n for n in ns if n[3] in (0, 1)], [n[0] for n in ns if n[3] == 3], []
    if "colorNotes" in m:
        ns = [(n.get("b", 0), n.get("x", 0), n.get("y", 0), n.get("c", 0), n.get("d", 0), n.get("a", 0)) for n in m["colorNotes"]]
        return ns, [b.get("b", 0) for b in m.get("bombNotes", [])], [(c.get("b", 0), c.get("tb", 0)) for c in m.get("burstSliders", [])]
    return None


def espelhar(notas, pre):
    return (tuple(sorted((o, 3 - x, y, 1 - c, ESPELHO[d]) for o, x, y, c, d in notas)),
            tuple(None if p is None else (3 - p[0], p[1], ESPELHO[p[2]], p[3]) for p in (pre[1], pre[0])))


def janelas_do_mapa(notas, bombas, correntes):
    """Gera (L, mascara, notas_da_janela, pre) para cada janela limpa."""
    notas = sorted(notas)
    if not notas:
        return
    # casa de cada nota e se ela e "limpa"; estado de paridade por mao ao longo do mapa
    suja = set()  # casas que invalidam a janela
    por_casa = defaultdict(list)
    est, ult = {0: None, 1: None}, {0: None, 1: None}
    entrada = {}  # indice da nota -> (nota anterior da mesma mao (x, y, d, casas de distancia) ou None)
    eventos = sorted([(b, 0, None) for b in bombas] + [(n[0], 1, n) for n in notas], key=lambda e: (e[0], e[1]))
    for b, tipo, n in eventos:
        casa = round(b * 4)
        if tipo == 0 or abs(b * 4 - casa) > 0.03:
            suja.add(casa)
            if tipo == 0:
                suja.update((casa - 4 + k for k in range(4)))  # bomba suja a batida seguinte tambem
                est = {0: None, 1: None}
            else:
                est[n[3]] = None
            continue
        _, x, y, c, d, ang = n
        ok = 0 <= x <= 3 and 0 <= y <= 2 and 0 <= d <= 7 and ang == 0
        if ok and est[c] is not None:
            st, e, r = checks.paridade(*est[c], c, d)
            ok = st == "ok"
            novo = (e, r) if ok else None
        elif ok:  # primeira nota (ou depois de bomba/ponto/erro): a janela nao serve, mas o estado recomeca daqui
            ok, novo = False, None
        else:
            novo = None
        if novo is None and 0 <= d <= 7:
            lado = "b" if checks.paridade_inicial(c, d) == "f" else "f"
            novo = (lado, checks.ROT[c][lado][d])
        est[c] = novo
        if not ok or any(o[3] == c for o in por_casa[casa]):
            suja.add(casa)
        por_casa[casa].append((x, y, c, d, ult[c]))
        ult[c] = (x, y, d, casa) if 0 <= d <= 7 else None
    for a, b in correntes:
        suja.update(range(round(a * 4) - 1, round(b * 4) + 2))
    casas = sorted(por_casa)
    if not casas:
        return
    b0, b1 = casas[0] // 4, casas[-1] // 4
    for B in range(b0, b1 + 1):
        for L in JANELAS:
            if B % L:
                continue
            ini, fim = B * 4, (B + L) * 4
            if any(s in suja for s in range(ini, fim)):
                continue
            jan, pre, cont = [], [None, None], [0] * (L * 4)
            for s in range(ini, fim):
                for x, y, c, d, ant in por_casa.get(s, ()):
                    if not any(q[3] == c for q in jan):  # primeira nota desta mao na janela: guarda de onde o braco veio
                        pre[c] = None if ant is None else (ant[0], ant[1], ant[2], min(s - ant[3], 16))
                    jan.append((s - ini, x, y, c, d))
                    cont[s - ini] += 1
            if not jan or max(cont) > 2:
                continue
            yield L, "".join(map(str, cont)), tuple(sorted(jan)), tuple(pre)


def main():
    meta = [json.loads(l) for l in (DADOS / "meta.jsonl").read_text(encoding="utf-8").splitlines()]
    meta = list({m["id"]: m for m in meta}.values())  # mapa baixado de novo (dificuldades a mais): vale a ultima linha
    lib = {d: {L: defaultdict(Counter) for L in JANELAS} for d in ("Normal", "Hard", "Expert", "ExpertPlus")}
    usados = Counter()
    for m in meta:
        for dif in m["diffs"]:
            arq = DADOS / "mapas" / m["id"] / f"{dif}.dat"
            try:
                lido = ler(arq)
            except Exception as e:
                print("pulei", arq, e)
                continue
            if lido is None or dif not in lib:
                continue
            usados[dif] += 1
            for L, masc, jan, pre in janelas_do_mapa(*lido):
                lib[dif][L][masc][(jan, pre)] += 1
                lib[dif][L][masc][espelhar(jan, pre)] += 1
    for dif, por_l in lib.items():
        saida = {L: {masc: [(j, p, n) for (j, p), n in c.most_common(MAX_POR_MASCARA)] for masc, c in por_m.items()} for L, por_m in por_l.items()}
        with open(DADOS / f"padroes_{dif}.pkl", "wb") as f:
            pickle.dump(saida, f)
        print(f"{dif}: {usados[dif]} mapas | " + " | ".join(
            f"janela de {L}: {len(saida[L])} mascaras, {sum(len(v) for v in saida[L].values())} padroes" for L in JANELAS))
    # numeros tipicos por dificuldade (mediana): NJS, e NPS dividido pelo BPM
    tip = {}
    for dif in lib:
        ds = [(m["bpm"], m["diffs"][dif]) for m in meta if dif in m["diffs"] and 60 <= m["bpm"] <= 300]
        tip[dif] = {"njs": statistics.median(d["njs"] for _, d in ds), "nps": statistics.median(d["nps"] for _, d in ds),
                    "nps_p25": statistics.quantiles([d["nps"] for _, d in ds], n=4)[0],
                    "notas_por_batida": statistics.median(d["nps"] * 60 / b for b, d in ds), "mapas": len(ds)}
    (DADOS / "tipico.json").write_text(json.dumps(tip, indent=1))
    print(json.dumps(tip))


def demo():
    # sobe-desce de uma mao em 4 casas: a 1a nota abre o estado, as outras formam janelas limpas de 1 batida
    ns = [(b, 1, 0 if i % 2 == 0 else 2, 0, 1 if i % 2 == 0 else 0, 0) for i, b in enumerate(range(10))]
    js = list(janelas_do_mapa(ns, [], []))
    assert all(L in JANELAS for L, *_ in js) and any(L == 4 and m == "1000100010001000" for L, m, *_ in js), js
    assert not [j for j in js if j[0] == 1 and j[2][0][0] == 0 and j[3][0] is None]  # a primeira nota do mapa nao vira padrao
    j, p = espelhar(((0, 1, 0, 0, 6),), ((0, 2, 4, 2), None))
    assert j == ((0, 2, 0, 1, 7),) and p == (None, (3, 2, 5, 2))
    print("extrair ok")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
