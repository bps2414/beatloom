"""Mods opcionais (Chroma e Noodle Extensions), aplicados por ultimo sobre o mapa ja gerado: aplicar() le a pasta do mapa, mexe e regrava.

Conferido no Quest do dono (Beat Saber 1.40.8): Chroma 2.10.3, Noodle Extensions 1.6.3, Tracks 2.5.4, CustomJSONData 0.24.5. Todos leem o customData do formato v3.

Chroma entra como sugestao: quem nao tem o mod joga o mesmo mapa com as cores de sempre. So existe cor por evento nos eventos basicos, entao com a chave
ligada o gerador escolhe um cenario classico (generate.py); num cenario de grupos de luzes nao ha o que colorir e o mapa fica como esta.
Com o Chroma, alem da cor: luz por luz (luz_por_luz), o palco (beatloom.palco: o letreiro com o artista e a musica, as colunas de luz) e paredes na cor
da parte. Tudo escolhido para que, sem o mod, o jogo leia os mesmos eventos de antes: o Chroma so acrescenta alvo e cor.
Noodle Extensions entra como exigencia: sem o mod o mapa nem abre, entao vai num conjunto a parte (Lawless), copia das dificuldades normais com os efeitos.
"""
import colorsys, copy, json, sys, zipfile
from pathlib import Path

import numpy as np

from beatloom import palco
from beatloom.audio import CASAS, partes, voz
from beatloom.luzes import COR, LUZES

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
            extra = {"lerpType": "HSV"} if e["i"] in (4, 8) else {}
            if e["i"] in (1, 5):
                if aceso.get(e["et"]) == k0:
                    e["i"], extra = e["i"] + 3, {"lerpType": "HSV"}
                aceso[e["et"]] = k0
        else:
            cor, extra = list(par[pt[k]][qual]), {}
        e["customData"] = {"color": cor, **extra}
        n += 1
    return n


def parte_de(sec):
    """[(batida, parte)] de cada compasso -> funcao batida -> (indice do compasso, parte)."""
    bs = [x[0] for x in sec]
    return lambda b: (k := max(int(np.searchsorted(bs, b + 0.01)) - 1, 0), sec[k][1])


def luz_por_luz(ev, sec, pal, amb, col_e=(), col_d=()):
    """Luz por luz com o Chroma, no cenario classico `amb` (luzes.LUZES diz quantas luzes cada tipo tem). Mexe em `ev`. -> quantos eventos mudaram.

    Subida: os aneis vao enchendo, do primeiro ate o ultimo, conforme ela chega perto da queda. Queda: cada bumbo acende os aneis com as quatro cores da
    capa espalhadas, e o desenho anda uma luz a cada bumbo; cada caixa acende um terco dos lasers do lado (e as colunas do palco nesse terco), e o terco
    anda a cada caixa; o primeiro giro de cada queda e um giro largo, em onda, e os outros trocam de sentido. Velocidade dos lasers na subida sem pular
    de posicao. Sem o Chroma o jogo le os mesmos eventos de antes: so entra alvo e cor, e a queda dividida em varios eventos na mesma batida, com o
    mesmo valor (vale o ultimo)."""
    if amb not in LUZES:
        return 0
    n = LUZES[amb]
    em = parte_de(sec)
    bs = [x[0] for x in sec]
    cores = [list(c) for c in (pal[0][0], pal[0][1], pal[1][0], pal[1][1])] if pal else None
    bumbo, caixa, giro, mudou, novos = 0, [0, 0], {}, 0, []
    for e in sorted(ev, key=lambda e: e["b"]):
        k, p = em(e["b"])
        if e["et"] == 1 and p == "subida" and 1 <= e["i"] <= 8:
            k0 = next(j for j in range(k, -1, -1) if j == 0 or sec[j - 1][1] != "subida")
            k1 = next(j for j in range(k, len(sec) + 1) if j == len(sec) or sec[j][1] != "subida")
            fim = bs[k1] if k1 < len(bs) else bs[-1] + 4
            x = min(max((e["b"] - bs[k0]) / max(fim - bs[k0], 1e-9), 0), 1)
            e.setdefault("customData", {})["lightID"] = list(range(1, max(1, int(np.ceil(x * n[1]))) + 1))
            mudou += 1
        elif e["et"] == 1 and p == "queda" and e["i"] in (2, 6) and cores:
            fatias = [[i for i in range(1, n[1] + 1) if (i + bumbo) % 4 == j] for j in range(4)]
            base = {k_: v for k_, v in e.get("customData", {}).items() if k_ not in ("color", "lightID")}
            e["customData"] = {**base, "lightID": fatias[0], "color": cores[0]}
            novos += [{**e, "customData": {**base, "lightID": f, "color": c}} for f, c in zip(fatias[1:], cores[1:]) if f]
            bumbo, mudou = bumbo + 1, mudou + 1
        elif e["et"] in (2, 3) and p == "queda" and e["i"] in (2, 6, 10):
            lado, nl = e["et"] - 2, n[e["et"]]
            cols = (col_e, col_d)[lado]
            e.setdefault("customData", {})["lightID"] = [i for i in range(1, nl + 1) if i % 3 == caixa[lado] % 3] + [c for j, c in enumerate(cols) if j % 3 == caixa[lado] % 3]
            caixa[lado] += 1
            mudou += 1
        elif e["et"] == 8 and p == "queda":
            primeiro = (k == 0 or sec[k - 1][1] != "queda") and k not in giro
            giro[k] = True
            e["customData"] = {"rotation": 90, "step": 12, "prop": 1.5, "speed": 2.5, "direction": 1} if primeiro else {"direction": k % 2}
            mudou += 1
        elif e["et"] in (12, 13) and p == "subida":
            e["customData"] = {"lockRotation": True}
            mudou += 1
    ev += novos
    ev.sort(key=lambda e: e["b"])
    return mudou


def paredes(obs, sec, pal):
    """Cada parede com a cor principal da parte em que ela comeca (Chroma), um pouco transparente. Mexe em `obs`. -> quantas"""
    if not pal or not obs:
        return 0
    (a, b), (a2, b2) = pal
    par = {"intro": a2, "verso": b, "subida": a2, "queda": a}
    em = parte_de(sec)
    for o in obs:
        k, p = em(o["b"])
        while p == "pausa" and k > 0:
            k, p = k - 1, sec[k - 1][1]
        o.setdefault("customData", {})["color"] = list(par.get(p, b)) + [0.6]
    return len(obs)


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


def noodle(d, sec, mel, fim=None, letreiro=False):
    """A dificuldade `d` (v3) -> (copia com os efeitos do Noodle Extensions, notas que ganharam efeito, paredes de enfeite).

    Chegada: a nota que cai na cabeca de um compasso da queda, ou do primeiro compasso de qualquer parte, nasce 2 casas para fora do lado da sua
    mao e 1 acima, aparecendo do nada, e chega ao lugar em um quarto do caminho ate o jogador; dali em diante e uma nota comum. Chuva: as outras notas
    do primeiro compasso de cada queda caem de cima. Ponta de arco e cabeca de corrente ficam de fora (o arco nao acompanharia).
    Enfeite: cada nota cantada de `mel` vira uma barra fina de cada lado, fora das quatro colunas, na altura da nota; nao encosta em ninguem.
    Letreiro (com o palco do Chroma): as pecas viram uma trilha presa a um pai que se mexe: sobe do horizonte na entrada, pula a cada queda e balanca
    nela, afunda na pausa e sobe para o ceu no fim."""
    d = copy.deepcopy(d)
    presas = {(round(s[k], 3), s[x], s[y]) for s in d["sliders"] for k, x, y in (("b", "x", "y"), ("tb", "tx", "ty"))} | {(round(s["b"], 3), s["x"], s["y"]) for s in d["burstSliders"]}
    marcos = [b for k, (b, p) in enumerate(sec) if p == "queda" or (p != "pausa" and (k == 0 or sec[k - 1][1] != p))]
    entradas = [(b, sec[k + 1][0] if k + 1 < len(sec) else b + 4) for k, (b, p) in enumerate(sec) if p == "queda" and (k == 0 or sec[k - 1][1] != "queda")]
    aparece = [[0, 0], [1, 0.12]]
    n = 0
    for nota in d["colorNotes"]:
        if (round(nota["b"], 3), nota["x"], nota["y"]) in presas:
            continue
        if any(abs(nota["b"] - m) < 0.05 for m in marcos):
            nota["customData"] = {"animation": {"offsetPosition": [[-2 if nota["c"] == 0 else 2, 1, 0, 0], [0, 0, 0, 0.25, "easeOutCubic"]], "dissolve": aparece, "dissolveArrow": aparece}}
            n += 1
        elif any(a < nota["b"] < z for a, z in entradas):
            nota["customData"] = {"animation": {"offsetPosition": [[0, 2.5, 0, 0], [0, 0, 0, 0.3, "easeOutQuad"]], "dissolve": aparece}}
            n += 1
    enfeite = [{"b": b, "d": dur, "x": x, "y": 0, "w": 1, "h": 1, "customData": {"coordinates": [cx, round(0.5 + 2.5 * h, 2)], "size": [0.15, 0.15], "uninteractable": True, "color": [1, 1, 1, 0.5]}}
               for b, dur, h in mel for x, cx in ((0, -3.6), (3, 3.45))]
    d["obstacles"] = sorted(d["obstacles"] + enfeite, key=lambda o: o["b"])
    if letreiro and sec:
        trilha, pai = "beatloom_letreiro", "beatloom_palco"
        for peca in d.get("customData", {}).get("environment", []):
            if peca.get("geometry", {}).get("material") == "beatloom_letreiro":
                peca["track"] = trilha
        anima = lambda b, dur, **kw: {"b": round(b, 3), "t": "AnimateTrack", "d": {"track": pai, "duration": dur, **kw}}
        t1 = sec[0][0]
        ce = [{"b": 0, "t": "AssignTrackParent", "d": {"childrenTracks": [trilha], "parentTrack": pai}}, anima(0, 0, position=[[0, -30, 0, 0]]),
              anima(t1, 6, position=[[0, -30, 0, 0], [0, 0, 0, 1, "easeOutCubic"]])]
        for k, (b, p) in enumerate(sec):
            if k == 0 or sec[k - 1][1] == p:
                continue
            ate = next((x for x, q in sec[k:] if q != p), fim or b + 8)
            if p == "queda":  # pulo na entrada e balanco ate o fim dela
                ce += [anima(b, 1.5, position=[[0, 0, 0, 0], [0, 2.5, 0, 0.2, "easeOutQuad"], [0, 0, 0, 1, "easeOutBounce"]]),
                       anima(b, ate - b, localRotation=[[0, 0, -2, 0], [0, 0, 2, 0.25, "easeInOutSine"], [0, 0, -2, 0.5, "easeInOutSine"], [0, 0, 2, 0.75, "easeInOutSine"], [0, 0, 0, 1, "easeInOutSine"]])]
            elif p == "pausa":  # afunda um pouco e volta quando a musica volta
                ce += [anima(b, 2, position=[[0, 0, 0, 0], [0, -4, 0, 1, "easeInOutSine"]]), anima(ate, 2, position=[[0, -4, 0, 0], [0, 0, 0, 1, "easeOutBack"]])]
        if fim:
            ce.append(anima(fim, 8, position=[[0, 0, 0, 0], [0, 40, 0, 1, "easeInCubic"]]))
        d.setdefault("customData", {})["customEvents"] = sorted(ce, key=lambda e: e["b"])
    return d, n, len(enfeite)


def aplicar(pasta, an, bt, pal, usar):
    """Aplica os mods pedidos em `usar` ("chroma", "noodle") ao mapa da pasta. -> o que foi feito, em texto, para o resumo do gerador ("" = nada)"""
    if not {"chroma", "noodle"} & set(usar):
        return ""  # sem as chaves, nenhum arquivo e tocado: o mapa sai identico
    pasta = Path(pasta)
    info = json.loads((pasta / "Info.dat").read_text(encoding="utf-8"))
    normais = next(s for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == "Standard")["_difficultyBeatmaps"]
    sec = [(bt(float(an["batidas"][i])), p) for i, p in zip(an["ini_comp"], partes(an))]
    fim = bt(float(an["batidas"][an["ini_comp"][-1]]))
    mel = melodia(an, bt) if "noodle" in usar and "forca_inst" in an else []
    amb = info.get("_environmentName", "")
    cd_palco, ids_a, ids_m, col_e, col_d = palco.montar(amb, info.get("_songAuthorName"), info.get("_songName")) if "chroma" in usar else ({}, [], [], [], [])
    feito, extras = [], []
    for m in normais:
        arq = pasta / m["_beatmapFilename"]
        d = json.loads(arq.read_text())
        ev = d["basicBeatmapEvents"]
        if "chroma" in usar:
            n = chroma(ev, sec, pal) if pal else 0
            n_let = palco.coreografia(ev, sec, pal, ids_a, ids_m, LUZES[amb][4], fim) if ids_a else 0  # antes do luz por luz, que divide os bumbos
            n_luz = luz_por_luz(ev, sec, pal, amb, col_e, col_d)
            n_par = paredes(d["obstacles"], sec, pal)
            if cd_palco:
                d["customData"] = {**d.get("customData", {}), **copy.deepcopy(cd_palco)}
            if n or n_let or n_luz or cd_palco:
                m.setdefault("_customData", {})["_suggestions"] = ["Chroma"]
                arq.write_text(json.dumps(d, separators=(",", ":")))  # sem espacos: o palco e os alvos das luzes pesam
                if not feito:  # as luzes e o palco sao os mesmos em todas as dificuldades
                    feito.append(f"Chroma: {n} eventos de luz com cor, {n_luz} luz por luz, {n_par} paredes com cor" + (f" | palco: letreiro com {sum(map(len, ids_a)) + sum(map(len, ids_m))} pecas e {n_let} eventos" if ids_a else "")
                                 + (f", {len(col_e) + len(col_d)} colunas" if col_e else ""))
        if "noodle" in usar:
            nd, n, w = noodle(d, sec, mel, fim, bool(ids_a))
            nome = m["_beatmapFilename"].replace("Standard", CONJUNTO)
            (pasta / nome).write_text(json.dumps(nd, separators=(",", ":")))
            extras.append({**copy.deepcopy(m), "_beatmapFilename": nome, "_customData": {**m.get("_customData", {}), "_requirements": ["Noodle Extensions"]}})
            feito.append(f"{m['_difficulty']} com Noodle Extensions: {n} notas com chegada, {w} paredes de enfeite")
    if extras:
        info["_difficultyBeatmapSets"].append({"_beatmapCharacteristicName": CONJUNTO, "_difficultyBeatmaps": extras})
    if ids_a:  # a ficha do mapa mostra o letreiro
        info.setdefault("_customData", {}).setdefault("_beatloom", {})["letreiro"] = True
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
    # luz por luz no Nice (8, 40, 11, 11, 14 luzes): aneis enchendo na subida, quatro cores no bumbo da queda, um terco dos lasers na caixa
    van = lambda ev: {(e["b"], e["et"]): (e["i"], e["f"]) for e in ev}  # o que o jogo sem o Chroma le: o ultimo evento de cada luz em cada batida
    ev = [{"b": 4, "et": 1, "i": 7, "f": 0.5}, {"b": 6, "et": 1, "i": 7, "f": 0.6}, {"b": 10, "et": 1, "i": 7, "f": 0.9}, {"b": 12, "et": 1, "i": 6, "f": 1}, {"b": 13, "et": 1, "i": 6, "f": 1},
          {"b": 12.5, "et": 2, "i": 2, "f": 1}, {"b": 13.5, "et": 2, "i": 2, "f": 1}, {"b": 12, "et": 8, "i": 0, "f": 1}, {"b": 13, "et": 8, "i": 0, "f": 1}, {"b": 5, "et": 12, "i": 3, "f": 1}]
    antes = van(ev)
    assert luz_por_luz(ev, sec, ((A, B), (A2, B2)), "NiceEnvironment", [1501, 1502, 1503, 1504, 1505]) == 10 and van(ev) == antes
    alvo = lambda b, et: [e["customData"]["lightID"] for e in ev if e["b"] == b and e["et"] == et]
    assert alvo(4, 1) == [[1]] and alvo(6, 1) == [list(range(1, 11))] and alvo(10, 1) == [list(range(1, 31))]  # a subida enche os aneis
    assert sorted(i for l in alvo(12, 1) for i in l) == list(range(1, 41)) and len({str(e["customData"]["color"]) for e in ev if e["b"] == 12 and e["et"] == 1}) == 4
    assert alvo(13, 1)[0] == [3, 7, 11, 15, 19, 23, 27, 31, 35, 39] and alvo(12.5, 2) == [[3, 6, 9, 1501, 1504]] and alvo(13.5, 2) == [[1, 4, 7, 10, 1502, 1505]]
    assert [e["customData"] for e in ev if e["et"] == 8] == [{"rotation": 90, "step": 12, "prop": 1.5, "speed": 2.5, "direction": 1}, {"direction": 1}] and ev[0]["b"] == 4
    assert luz_por_luz(ev, sec, None, "WeaveEnvironment") == 0
    obs = [{"b": 1, "d": 1}, {"b": 17, "d": 1}]
    assert paredes(obs, sec, ((A, B), (A2, B2))) == 2 and [o["customData"]["color"] for o in obs] == [[0.0, 0.0, 1.0, 0.6], [1.0, 0.0, 0.0, 0.6]]  # verso: B; pausa: a da queda
    # aplicar de ponta a ponta, Chroma e Noodle, numa pasta com um mapa de 5 compassos no Nice: palco montado, letreiro, Lawless com o letreiro animado,
    # e o que o jogo sem o Chroma le nos eventos normais continua igual
    global partes
    real_p, partes = partes, lambda an: ["verso", "subida", "subida", "queda", "pausa"]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # como o gerador escreve: na subida cada luz acende uma vez e depois so muda por transicao
            ev0 = [{"b": float(b), "et": et, "i": i + 3 * (4 < b < 12 and i in (1, 5)), "f": 1.0} for b in range(0, 20) for et, i in ((0, 5), (1, 6 if 12 <= b < 16 else 7), (4, 1 if b % 4 else 10))]
            mapa = {"version": "3.2.0", "colorNotes": [{"b": 12, "x": 1, "y": 0, "c": 0, "d": 1, "a": 0}], "sliders": [], "burstSliders": [], "obstacles": [{"b": 13, "d": 1, "x": 0, "y": 0, "w": 1, "h": 5}], "basicBeatmapEvents": ev0}
            (Path(tmp) / "HardStandard.dat").write_text(json.dumps(mapa))
            (Path(tmp) / "Info.dat").write_text(json.dumps({"_songName": "Basket Case", "_songAuthorName": "Green Day Tribute", "_environmentName": "NiceEnvironment",
                                                             "_difficultyBeatmapSets": [{"_beatmapCharacteristicName": "Standard", "_difficultyBeatmaps": [b("Hard", "HardStandard.dat")]}]}))
            an = {"batidas": np.arange(21.0), "ini_comp": np.arange(0, 21, 4)}
            txt = aplicar(tmp, an, lambda t: t, ((A, B), (A2, B2)), {"chroma", "noodle"})
            info, d, nd = (json.loads((Path(tmp) / f).read_text()) for f in ("Info.dat", "HardStandard.dat", "HardLawless.dat"))
            assert "palco: letreiro" in txt and info["_customData"]["_beatloom"]["letreiro"] and do_mapa(info) == ["chroma", "noodle"], txt
            v1, v0 = van(d["basicBeatmapEvents"]), van(ev0)
            c0 = [{"b": b_, "i": i, "f": f} for (b_, et), (i, f) in sorted(v0.items()) if et == 4]
            assert all(v1[k] == (v0[k] if k in v0 else (palco.estado(c0, k[0])["i"], palco.estado(c0, k[0])["f"])) for k in v1) and set(v1) >= set(v0) and {k[1] for k in set(v1) - set(v0)} == {4}
            env = d["customData"]["environment"]
            assert sum(p_.get("geometry", {}).get("material") == "beatloom_letreiro" for p_ in env) > 50 and sum(p_.get("geometry", {}).get("material") == "beatloom_coluna" for p_ in env) == 10
            assert d["obstacles"][0]["customData"]["color"] == [1.0, 0.0, 0.0, 0.6] and nd["customData"]["customEvents"][0]["t"] == "AssignTrackParent"
            assert all(p_.get("track") == "beatloom_letreiro" for p_ in nd["customData"]["environment"] if p_["geometry"]["material"] == "beatloom_letreiro")
            assert [e["b"] for e in nd["customData"]["customEvents"] if "position" in e["d"]][-1] == 20 and "track" not in str(env)  # sobe ao ceu no fim; o Standard sem trilha
    finally:
        partes = real_p
    print("mods ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
