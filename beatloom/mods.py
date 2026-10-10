"""Mods opcionais (Chroma e Noodle Extensions), aplicados por ultimo sobre o mapa ja gerado: aplicar() le a pasta do mapa, mexe e regrava.

Conferido no Quest do dono (Beat Saber 1.40.8): Chroma 2.10.3, Noodle Extensions 1.6.3, Tracks 2.5.4, CustomJSONData 0.24.5. Todos leem o customData do formato v3.

Chroma entra como sugestao: quem nao tem o mod joga o mesmo mapa com as cores de sempre. So existe cor por evento nos eventos basicos, entao com a chave
ligada o gerador escolhe o cenario classico do clima (generate.py); num cenario de grupos de luzes nao ha o que colorir e o mapa fica como esta.
Noodle Extensions entra como exigencia: sem o mod o mapa nem abre, entao vai num conjunto a parte (Lawless), copia das dificuldades normais com os efeitos.
"""
import colorsys, copy, json, sys, zipfile
from pathlib import Path

import numpy as np

from beatloom.audio import CASAS, partes, voz
from beatloom.luzes import COR

CONJUNTO = "Lawless"  # a caracteristica do SongCore para mapa que foge do padrao
BARRAS = 60  # teto de notas cantadas que viram barra (duas paredes cada): enfeite, nao arte de parede


def mistura(a, b, x):
    """De uma cor a outra pela roda de cores, pelo caminho mais curto: o meio continua vivo (em RGB, duas cores opostas dao cinza)."""
    (h0, s0, v0), (h1, s1, v1) = colorsys.rgb_to_hsv(*a), colorsys.rgb_to_hsv(*b)
    dh = (h1 - h0 + 0.5) % 1 - 0.5
    return [round(c, 3) for c in colorsys.hsv_to_rgb((h0 + dh * x) % 1, s0 + (s1 - s0) * x, v0 + (v1 - v0) * x)]


def chroma(ev, sec, pal):
    """Poe a cor do Chroma em cada evento basico de luz. Mexe em `ev`. -> quantos ganharam cor

    sec = [(batida, parte)] de cada compasso; pal = ((A, B), (A2, B2)), a paleta da capa (luzes.paleta).
    Cada parte tem o seu par (cor principal, outra cor), que volta quando a parte volta: introducao A2 e B2, verso B e A2, queda A e B, os dois tons
    mais fortes da capa. A subida vai do par da parte anterior ao da queda, e nela cada luz acende uma vez e depois so muda aos poucos (evento de
    transicao), para o degrade ser continuo. Branco, apagar e os eventos de anel e de laser ficam como estao."""
    (a, b), (a2, b2) = pal
    par = {"intro": (a2, b2), "verso": (b, a2), "queda": (a, b)}
    bs, pt = [s[0] for s in sec], [s[1] for s in sec]
    n, aceso = 0, {}
    for e in sorted(ev, key=lambda e: e["b"]):
        k = max(int(np.searchsorted(bs, e["b"] + 0.01)) - 1, 0)
        if e["et"] > 4 or not 1 <= e["i"] <= 8 or pt[k] == "pausa":
            continue
        qual = 0 if (e["i"] > 4) == (COR.get(pt[k], 1) == 0) else 1  # 5 a 8 e a cor 0 do mapa, 1 a 4 a cor 1; a principal da parte e COR[parte]
        if pt[k] == "subida":
            k0 = next(j for j in range(k, -1, -1) if j == 0 or pt[j - 1] != "subida")
            k1 = next(j for j in range(k, len(pt) + 1) if j == len(pt) or pt[j] != "subida")
            de, ate = par.get(pt[k0 - 1] if k0 else "", par["verso"]), par.get(pt[k1] if k1 < len(pt) else "", par["queda"])
            fim = bs[k1] if k1 < len(bs) else bs[-1] + (bs[-1] - bs[-2] if len(bs) > 1 else 4)
            cor = mistura(de[qual], ate[qual], min(max((e["b"] - bs[k0]) / (fim - bs[k0]), 0), 1))
            extra = {}
            if e["i"] in (1, 5):
                if aceso.get(e["et"]) == k0:
                    e["i"], extra = e["i"] + 3, {"lerpType": "HSV"}
                aceso[e["et"]] = k0
        else:
            cor, extra = list(par[pt[k]][qual]), {}
        e["customData"] = {"color": cor, **extra}
        n += 1
    return n


def melodia(an, bt):
    """As notas cantadas que duram meia batida ou mais -> [(batida, duracao em batidas, altura de 0 a 1)], as mais longas primeiro, no maximo BARRAS."""
    alt, g = voz(an)["altura"], an["grade"]
    tem = [v for v in alt if v is not None]
    if not tem:
        return []
    lo, hi = np.percentile(tem, 5), np.percentile(tem, 95)
    out, i = [], 0
    while i < len(alt):
        j = i
        while j + 1 < len(alt) and alt[j + 1] == alt[i]:
            j += 1
        if alt[i] is not None and j + 1 - i >= CASAS // 2 and j + 1 < len(g):
            out.append((bt(float(g[i])), round(bt(float(g[j + 1])) - bt(float(g[i])), 3), round(float(np.clip((alt[i] - lo) / max(hi - lo, 1), 0, 1)), 2)))
        i = j + 1
    return sorted(sorted(out, key=lambda v: -v[1])[:BARRAS])


def noodle(d, sec, mel):
    """A dificuldade `d` (v3) -> (copia com os efeitos leves do Noodle Extensions, notas que ganharam chegada, paredes de enfeite).

    Chegada: a nota que cai na cabeca de um compasso da queda, ou do primeiro compasso de qualquer parte, nasce 2 casas para fora do lado da sua
    mao e 1 acima, e chega ao lugar em um quarto do caminho ate o jogador; dali em diante e uma nota comum. Ponta de arco e cabeca de corrente ficam de fora.
    Enfeite: cada nota cantada de `mel` vira uma barra fina de cada lado, fora das quatro colunas, na altura da nota; nao encosta em ninguem."""
    d = copy.deepcopy(d)
    presas = {(round(s[k], 3), s[x], s[y]) for s in d["sliders"] for k, x, y in (("b", "x", "y"), ("tb", "tx", "ty"))} | {(round(s["b"], 3), s["x"], s["y"]) for s in d["burstSliders"]}
    marcos = [b for k, (b, p) in enumerate(sec) if p == "queda" or (p != "pausa" and (k == 0 or sec[k - 1][1] != p))]
    n = 0
    for nota in d["colorNotes"]:
        if any(abs(nota["b"] - m) < 0.05 for m in marcos) and (round(nota["b"], 3), nota["x"], nota["y"]) not in presas:
            nota["customData"] = {"animation": {"offsetPosition": [[-2 if nota["c"] == 0 else 2, 1, 0, 0], [0, 0, 0, 0.25, "easeOutCubic"]]}}
            n += 1
    enfeite = [{"b": b, "d": dur, "x": x, "y": 0, "w": 1, "h": 1, "customData": {"coordinates": [cx, round(0.5 + 2.5 * h, 2)], "size": [0.15, 0.15], "uninteractable": True}}
               for b, dur, h in mel for x, cx in ((0, -3.6), (3, 3.45))]
    d["obstacles"] = sorted(d["obstacles"] + enfeite, key=lambda o: o["b"])
    return d, n, len(enfeite)


def aplicar(pasta, an, bt, pal, usar):
    """Aplica os mods pedidos em `usar` ("chroma", "noodle") ao mapa da pasta. -> o que foi feito, em texto, para o resumo do gerador ("" = nada)"""
    if not {"chroma", "noodle"} & set(usar):
        return ""  # sem as chaves, nenhum arquivo e tocado: o mapa sai identico
    pasta = Path(pasta)
    info = json.loads((pasta / "Info.dat").read_text(encoding="utf-8"))
    normais = next(s for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == "Standard")["_difficultyBeatmaps"]
    sec = [(bt(float(an["batidas"][i])), p) for i, p in zip(an["ini_comp"], partes(an))]
    mel = melodia(an, bt) if "noodle" in usar and "forca_inst" in an else []
    feito, extras = [], []
    for m in normais:
        arq = pasta / m["_beatmapFilename"]
        d = json.loads(arq.read_text())
        if "chroma" in usar and pal and (n := chroma(d["basicBeatmapEvents"], sec, pal)):
            m.setdefault("_customData", {})["_suggestions"] = ["Chroma"]
            arq.write_text(json.dumps(d))
            feito += [f"Chroma: {n} eventos de luz com cor"] * (not feito)  # as luzes sao as mesmas em todas as dificuldades
        if "noodle" in usar:
            nd, n, w = noodle(d, sec, mel)
            nome = m["_beatmapFilename"].replace("Standard", CONJUNTO)
            (pasta / nome).write_text(json.dumps(nd))
            extras.append({**copy.deepcopy(m), "_beatmapFilename": nome, "_customData": {**m.get("_customData", {}), "_requirements": ["Noodle Extensions"]}})
            feito.append(f"{m['_difficulty']} com Noodle Extensions: {n} notas com chegada, {w} paredes de enfeite")
    if extras:
        info["_difficultyBeatmapSets"].append({"_beatmapCharacteristicName": CONJUNTO, "_difficultyBeatmaps": extras})
    (pasta / "Info.dat").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return " | ".join(feito)


def do_mapa(info):
    """Com quais mods o mapa foi feito, pelo que o Info.dat diz -> lista com "chroma" e/ou "noodle"."""
    cd = [b.get("_customData", {}) for s in info["_difficultyBeatmapSets"] for b in s["_difficultyBeatmaps"]]
    return ["chroma"] * any("Chroma" in c.get("_suggestions", ()) for c in cd) + ["noodle"] * any("Noodle Extensions" in c.get("_requirements", ()) for c in cd)


def conjunto(zp, novo, difs):
    """Mapa refeito: o conjunto do Noodle das dificuldades `difs` no zip `zp` fica igual ao do zip `novo` (entra, troca ou sai). As outras ficam."""
    de = lambda info: next((s for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == CONJUNTO), {"_beatmapCharacteristicName": CONJUNTO, "_difficultyBeatmaps": []})
    with zipfile.ZipFile(novo) as z:
        entram = [b for b in de(json.loads(z.read("Info.dat").decode("utf-8-sig")))["_difficultyBeatmaps"] if b["_difficulty"] in difs]
        dados = {b["_beatmapFilename"]: z.read(b["_beatmapFilename"]) for b in entram}
    tmp = Path(zp).with_suffix(".tmp")
    with zipfile.ZipFile(zp) as z, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
        s = de(info)
        fora = {b["_beatmapFilename"] for b in s["_difficultyBeatmaps"] if b["_difficulty"] in difs} | set(dados) | {"Info.dat"}
        s["_difficultyBeatmaps"] = sorted([b for b in s["_difficultyBeatmaps"] if b["_difficulty"] not in difs] + entram, key=lambda b: b["_difficultyRank"])
        info["_difficultyBeatmapSets"] = [x for x in info["_difficultyBeatmapSets"] if x["_beatmapCharacteristicName"] != CONJUNTO] + [s] * bool(s["_difficultyBeatmaps"])
        out.writestr("Info.dat", json.dumps(info, ensure_ascii=False, indent=2))
        for n in z.namelist():
            if n not in fora:
                out.writestr(n, z.read(n))
        for n, dado in dados.items():
            out.writestr(n, dado)
    tmp.replace(zp)


def demo():
    import tempfile
    A, B, A2, B2 = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0)
    assert mistura(A, B, 0) == [1.0, 0.0, 0.0] and mistura(A, B, 1) == [0.0, 0.0, 1.0] and mistura(A, B, 0.5) == [1.0, 0.0, 1.0]  # vermelho -> azul passa pelo magenta, nao pelo cinza
    # compassos de 4 batidas: verso, subida, subida, queda, pausa. No verso a cor 1 (eventos 1 a 4) e a principal; na queda, a cor 0 (5 a 8)
    sec = [(0, "verso"), (4, "subida"), (8, "subida"), (12, "queda"), (16, "pausa")]
    ev = [{"b": 0, "et": 0, "i": 1, "f": 0.5}, {"b": 0, "et": 2, "i": 5, "f": 0.5}, {"b": 1, "et": 4, "i": 9, "f": 1}, {"b": 2, "et": 8, "i": 0, "f": 1},
          {"b": 4, "et": 0, "i": 5, "f": 0.2}, {"b": 8, "et": 0, "i": 5, "f": 0.6}, {"b": 8, "et": 1, "i": 7, "f": 0.6}, {"b": 12, "et": 0, "i": 6, "f": 1}, {"b": 12, "et": 2, "i": 1, "f": 1}, {"b": 16, "et": 0, "i": 0, "f": 0}]
    antes = copy.deepcopy(ev)
    assert chroma(ev, sec, ((A, B), (A2, B2))) == 7
    cor = lambda k: ev[k].get("customData", {}).get("color")
    assert cor(0) == list(B) and cor(1) == list(A2) and [cor(k) for k in (2, 3, 9)] == [None] * 3 and ev[2] == antes[2] and ev[3] == antes[3]  # verso: B e A2; branco, anel e apagar ficam
    assert cor(4) == list(B) and ev[4]["i"] == 5 and ev[5]["i"] == 8 and ev[5]["customData"]["lerpType"] == "HSV" and cor(5) == mistura(B, A, 0.5), ev[4:6]  # subida: acende em B e vai a A por transicao
    assert ev[6]["i"] == 7 and cor(6) == mistura(B, A, 0.5) and cor(7) == list(A) and cor(8) == list(B)  # o pulso continua pulso; queda: A e B
    assert all({k: v for k, v in e.items() if k != "customData"} == o for e, o in zip(ev, antes) if e["i"] == o["i"])  # fora a transicao, so entra o customData
    # noodle: a nota da cabeca da queda (batida 12) ganha chegada, a vermelha vindo da esquerda; a do meio do verso nao; a ponta de arco tambem nao
    d = {"colorNotes": [{"b": 2, "x": 1, "y": 0, "c": 0, "d": 1, "a": 0}, {"b": 12, "x": 1, "y": 0, "c": 0, "d": 1, "a": 0}, {"b": 12, "x": 2, "y": 0, "c": 1, "d": 1, "a": 0}],
         "sliders": [{"b": 12, "x": 2, "y": 0, "tb": 14, "tx": 2, "ty": 1}], "burstSliders": [], "obstacles": [{"b": 1, "d": 1, "x": 0, "y": 0, "w": 1, "h": 5}]}
    nd, n, w = noodle(d, sec, [(5.0, 2.0, 0.0), (9.0, 1.0, 1.0)])
    assert (n, w) == (1, 4) and nd["colorNotes"][1]["customData"]["animation"]["offsetPosition"][0] == [-2, 1, 0, 0] and "customData" not in nd["colorNotes"][0] and "customData" not in nd["colorNotes"][2]
    assert "customData" not in d["colorNotes"][1] and len(d["obstacles"]) == 1  # a dificuldade normal nao e tocada
    enf = [o["customData"] for o in nd["obstacles"] if "customData" in o]
    assert [c["coordinates"] for c in enf] == [[-3.6, 0.5], [3.45, 0.5], [-3.6, 3.0], [3.45, 3.0]] and all(c["uninteractable"] for c in enf)
    # melodia: batida de 1 s, 4 casas; nota 60 por 1 batida, 64 por 1 casa (curta demais), 72 por meia batida
    an = {"hash": "demo-mods", "grade": np.arange(40) / 4}
    global voz
    real, voz = voz, lambda an: {"altura": [60.0] * 4 + [None] + [64.0] + [None] * 2 + [72.0] * 2 + [None] * 30}
    try:
        assert melodia(an, lambda t: t) == [(0.0, 1.0, 0.0), (2.0, 0.5, 1.0)], melodia(an, lambda t: t)
    finally:
        voz = real
    # do_mapa e conjunto: o zip refeito traz o Hard do Noodle; depois, refeito sem o mod, ele sai e o zip volta a ter so o normal
    b = lambda dif, arq, cd=None: {"_difficulty": dif, "_difficultyRank": 5, "_beatmapFilename": arq, **({"_customData": cd} if cd else {})}
    info = lambda *sets: json.dumps({"_difficultyBeatmapSets": [{"_beatmapCharacteristicName": c, "_difficultyBeatmaps": bs} for c, bs in sets]})
    assert do_mapa(json.loads(info(("Standard", [b("Hard", "a")])))) == [] and do_mapa(json.loads(info(("Standard", [b("Hard", "a", {"_suggestions": ["Chroma"]})]), (CONJUNTO, [b("Hard", "b", {"_requirements": ["Noodle Extensions"]})])))) == ["chroma", "noodle"]
    with tempfile.TemporaryDirectory() as tmp:
        zp, com, sem = (Path(tmp) / f"{n}.zip" for n in ("mapa", "com", "sem"))
        for arq, sets, dados in ((zp, [("Standard", [b("Hard", "HardStandard.dat")])], {"HardStandard.dat": "n"}), (sem, [("Standard", [b("Hard", "HardStandard.dat")])], {"HardStandard.dat": "n"}),
                                 (com, [("Standard", [b("Hard", "HardStandard.dat")]), (CONJUNTO, [b("Hard", "HardLawless.dat")])], {"HardStandard.dat": "n", "HardLawless.dat": "x"})):
            with zipfile.ZipFile(arq, "w") as z:
                z.writestr("Info.dat", info(*sets))
                for k, v in dados.items():
                    z.writestr(k, v)
        conjunto(zp, com, ["Hard"])
        with zipfile.ZipFile(zp) as z:
            assert sorted(z.namelist()) == ["HardLawless.dat", "HardStandard.dat", "Info.dat"] and z.read("HardLawless.dat") == b"x" and len(json.loads(z.read("Info.dat"))["_difficultyBeatmapSets"]) == 2
        conjunto(zp, sem, ["Hard"])
        with zipfile.ZipFile(zp) as z:
            assert sorted(z.namelist()) == ["HardStandard.dat", "Info.dat"] and len(json.loads(z.read("Info.dat"))["_difficultyBeatmapSets"]) == 1
    print("mods ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
