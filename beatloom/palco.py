"""Palco (so com o Chroma): o que o mapa poe no cenario alem das luzes dele.

Letreiro (letreiro): o artista grande e a musica embaixo, em letras de pixels no fundo, no lugar do nome de banda que alguns cenarios trazem escrito.
Colunas (colunas): uma fila de cada lado, longe da pista, que acendem junto com os lasers do seu lado.

Cada peca e um cubo do Chroma com material de luz e um ILightWithId: entra num tipo de luz do cenario com um ID proprio (LETREIRO, COLUNAS), entao
acende, apaga e muda de cor com os eventos basicos daquele tipo. As colunas seguem os eventos de laser que ja existem. O letreiro (tipo 4, o centro) tem
eventos so dele (coreografia); os do centro do proprio cenario passam a mirar so nas luzes do cenario, e cada evento do letreiro que cai numa batida sem
evento do centro e seguido do estado de agora do centro com alvo vazio (estado), que o Chroma ignora. Sem o Chroma o jogo ignora o alvo dos eventos e
vale o ultimo da mesma batida, entao quem joga sem o mod ve as luzes de sempre.
"""
import re, sys, unicodedata

import numpy as np

from beatloom.luzes import CENTRO, DIR, ESQ, LUZES

LETREIRO, COLUNAS = 1001, 1501  # IDs de luz das pecas; os do proprio cenario vao no maximo ate 80
ONDE = (0.0, 6.5, 55.0)  # o letreiro: x do centro, altura da base e distancia ate o jogador (m)
LARGURA = 40.0  # largura maxima de uma linha (m): uns 40 graus a 55 m
PIXEL, MINIMO = (0.9, 0.42), (0.5, 0.22)  # pixel maximo do artista e da musica (m); menor que o minimo, a linha quebra em duas
TETO = 320  # pecas de geometria no maximo (o que o Quest aguenta: a medir no mapa de prova); acima disso a musica sai e fica so o artista
MATERIAIS = {"beatloom_letreiro": {"shader": "TransparentLight"}, "beatloom_coluna": {"shader": "OpaqueLight"}}  # um material para cada tipo de peca, compartilhado
# pecas do cenario que somem quando o mapa tem letreiro (o nome de banda escrito); so entra o que foi visto funcionando no jogo. Ver tools/prova_visual.py
ESCONDE = {}

# fonte de 5 x 7 (os sinais estreitos tem menos colunas); "#" acende
FONTE = {k: v.split() for k, v in {
    "A": ".###. #...# #...# ##### #...# #...# #...#", "B": "####. #...# #...# ####. #...# #...# ####.", "C": ".###. #...# #.... #.... #.... #...# .###.",
    "D": "####. #...# #...# #...# #...# #...# ####.", "E": "##### #.... #.... ####. #.... #.... #####", "F": "##### #.... #.... ####. #.... #.... #....",
    "G": ".###. #...# #.... #.### #...# #...# .####", "H": "#...# #...# #...# ##### #...# #...# #...#", "I": ".###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.",
    "J": "..### ...#. ...#. ...#. ...#. #..#. .##..", "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#", "L": "#.... #.... #.... #.... #.... #.... #####",
    "M": "#...# ##.## #.#.# #.#.# #...# #...# #...#", "N": "#...# #...# ##..# #.#.# #..## #...# #...#", "O": ".###. #...# #...# #...# #...# #...# .###.",
    "P": "####. #...# #...# ####. #.... #.... #....", "Q": ".###. #...# #...# #...# #.#.# #..#. .##.#", "R": "####. #...# #...# ####. #.#.. #..#. #...#",
    "S": ".#### #.... #.... .###. ....# ....# ####.", "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..", "U": "#...# #...# #...# #...# #...# #...# .###.",
    "V": "#...# #...# #...# #...# #...# .#.#. ..#..", "W": "#...# #...# #...# #.#.# #.#.# #.#.# .#.#.", "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..", "Z": "##### ....# ...#. ..#.. .#... #.... #####",
    "0": ".###. #...# #..## #.#.# ##..# #...# .###.", "1": "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.", "2": ".###. #...# ....# ...#. ..#.. .#... #####",
    "3": "##### ...#. ..#.. ...#. ....# #...# .###.", "4": "...#. ..##. .#.#. #..#. ##### ...#. ...#.", "5": "##### #.... ####. ....# ....# #...# .###.",
    "6": "..##. .#... #.... ####. #...# #...# .###.", "7": "##### ....# ...#. ..#.. .#... .#... .#...", "8": ".###. #...# #...# .###. #...# #...# .###.",
    "9": ".###. #...# #...# .#### ....# ...#. .##..",
    ".": ". . . . . . #", ",": ".. .. .. .. .. .# #.", "!": "# # # # # . #", "?": ".###. #...# ....# ...#. ..#.. ..... ..#..", "'": "# # . . . . .",
    "-": "... ... ... ### ... ... ...", ":": ". . # . . # .", "&": ".##.. #..#. #.#.. .#... #.#.# #..#. .##.#", "/": "....# ...#. ...#. ..#.. .#... .#... #....",
    "(": ".# #. #. #. #. #. .#", ")": "#. .# .# .# .# .# #.", "+": "..... ..#.. ..#.. ##### ..#.. ..#.. .....", "#": ".#.#. ##### .#.#. .#.#. .#.#. ##### .#.#.",
    "$": "..#.. .#### #.#.. .###. ..#.# ####. ..#..", "*": "..... #.#.# .###. ##### .###. #.#.# .....", "%": "##..# ##..# ...#. ..#.. .#... #..## #..##",
}.items()}


def pixels(texto):
    """Texto -> ([(x, y, largura, altura, letra)], largura total), em pixels, y de cima para baixo; `letra` conta so as letras desenhadas.
    Maiusculas sem acento; o que a fonte nao tem fica de fora. Pixels seguidos na mesma linha viram um retangulo, e o mesmo retangulo em linhas
    seguidas vira um so: menos pecas no jogo."""
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().upper().replace('"', "'")
    t = re.sub(r"\s+", " ", "".join(c for c in t if c in FONTE or c.isspace())).strip()
    rets, x, k = [], 0, -1
    for c in t:
        if c == " ":
            x += 3
            continue
        k, abertos = k + 1, {}
        for y, linha in enumerate(FONTE[c]):
            agora = {}
            for m in re.finditer("#+", linha):
                r = (m.start(), m.end())
                agora[r] = abertos.get(r) or rets.append([x + r[0], y, r[1] - r[0], 0, k]) or rets[-1]
                agora[r][3] += 1
            abertos = agora
        x += len(FONTE[c][0]) + 1
    return [tuple(r) for r in rets], max(x - 1, 0)


def linhas(texto, pmax, pmin):
    """O texto numa linha, ou em duas (quebrando entre palavras, o mais parelho possivel) se numa so o pixel ficaria menor que `pmin`.
    -> ([(retangulos, largura)], tamanho do pixel em m)"""
    um = pixels(texto)
    if not um[1]:
        return [], 0.0
    ps = str(texto).split()
    if min(pmax, LARGURA / um[1]) >= pmin or len(ps) < 2:
        return [um], min(pmax, LARGURA / um[1])
    dois = min(([pixels(" ".join(ps[:i])), pixels(" ".join(ps[i:]))] for i in range(1, len(ps))), key=lambda l: (max(x[1] for x in l), -l[0][1]))  # no empate, a linha de cima mais comprida
    return [l for l in dois if l[1]], min(0.75 * pmax, LARGURA / max(x[1] for x in dois))  # em duas linhas, letra um pouco menor: o letreiro nao sobe demais


def letreiro(artista, musica, onde=ONDE):
    """-> (pecas para o customData.environment, [IDs de cada letra do artista], [IDs de cada letra da musica]). Artista desconhecido: nada.
    Por cima o artista (uma ou duas linhas), um vao e a musica, menor. Cada retangulo e um cubo fino com um ID de luz so dele, no tipo do centro."""
    if not artista or str(artista).strip().lower() in ("desconhecido", "unknown"):
        return [], [], []
    corta = lambda t, n: t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(" -,(&") + "..."  # nome que nao cabe em duas linhas legiveis
    blocos = [linhas(corta(str(artista).strip(), 36), PIXEL[0], MINIMO[0]), linhas(corta(str(musica or "").strip(), 52), PIXEL[1], MINIMO[1])]
    if not blocos[0][0]:
        return [], [], []
    (la, pa), (lm, pm) = blocos
    x0, base, z = onde
    pilha = [(l, pa, 0) for l in la] + [(l, pm, 1) for l in lm]  # (linha, pixel, 0 = artista / 1 = musica)
    vao = lambda i: 0 if i == 0 else (2 * pilha[i][1] if pilha[i][2] == pilha[i - 1][2] else 3 * pa)
    topo = base + sum(7 * p for _, p, _ in pilha) + sum(vao(i) for i in range(len(pilha)))
    pecas, ids, n, y = [], ([], []), LETREIRO, topo
    for i, ((rets, larg), p, qual) in enumerate(pilha):
        y -= vao(i)
        primeira = len(ids[qual])
        for x, yy, w, h, k in rets:
            while len(ids[qual]) <= primeira + k:
                ids[qual].append([])
            ids[qual][primeira + k].append(n)
            pecas.append({"geometry": {"type": "Cube", "material": "beatloom_letreiro"}, "position": [round(x0 + (x + w / 2 - larg / 2) * p, 3), round(y - (yy + h / 2) * p, 3), z],
                          "scale": [round(w * p, 3), round(h * p, 3), round(0.3 * p, 3)], "components": {"ILightWithId": {"type": CENTRO, "lightID": n}}})
            n += 1
        y -= 7 * p
    if len(pecas) > TETO:  # nome muito comprido: so o artista, e dele as letras que couberem
        fica, letras = 0, []
        for l in ids[0]:
            if fica + len(l) > TETO:
                break
            fica, letras = fica + len(l), letras + [l]
        return pecas[:fica], letras, []
    return pecas, ids[0], ids[1]


def colunas(n=5, x=12.0, z0=20.0, passo=12.0, altura=14.0):
    """Uma fila de `n` colunas de luz de cada lado, a `x` m do meio da pista, da distancia z0 em diante. -> (pecas, IDs da esquerda, IDs da direita).
    Cada uma entra no tipo dos lasers do seu lado: acende com os eventos de laser que o mapa ja tem."""
    pecas, ids = [], ([], [])
    for lado, tipo, sx in ((0, ESQ, -1), (1, DIR, 1)):
        for k in range(n):
            i = COLUNAS + 100 * lado + k
            ids[lado].append(i)
            pecas.append({"geometry": {"type": "Cube", "material": "beatloom_coluna"}, "position": [sx * (x + 2 * k), altura / 2, z0 + passo * k],
                          "scale": [0.35, altura, 0.35], "components": {"ILightWithId": {"type": tipo, "lightID": i}}})
    return pecas, ids[0], ids[1]


def mistura(a, b, x):
    from beatloom.mods import mistura as m  # o mods importa este modulo
    return m(a, b, x)


def coreografia(ev, sec, pal, ids_a, ids_m, n4, fim):
    """Os eventos do letreiro, ja no meio dos eventos `ev` do mapa (mexe em `ev`). -> quantos eventos entraram.

    sec = [(batida, parte)] de cada compasso; pal = paleta da capa (luzes.paleta) ou None; n4 = luzes do centro do cenario; fim = batida do fim da musica.
    Comeca apagado; na entrada da musica as letras do artista acendem uma a uma e a musica aparece devagar embaixo. Cada parte tem a sua cor e o seu
    brilho (os mesmos pares do Chroma nas luzes); na subida o letreiro clareia e muda de cor compasso a compasso; na entrada da queda um clarao branco
    corre pelas letras; na queda o artista pisca no bumbo e a musica na caixa; o acento branco do centro passa tambem pelo letreiro; na pausa fica so uma
    brasa; no fim some devagar."""
    if not ids_a or not sec:
        return 0
    todos_a, todos_m = [i for l in ids_a for i in l], [i for l in ids_m for i in l]
    if pal:
        (a, b), (a2, b2) = pal
        par = {"intro": (a2, b2), "verso": (b, a2), "queda": (a, b)}
    else:
        par = {}
    bs, pt = [s[0] for s in sec], [s[1] for s in sec]
    parte = lambda b: pt[max(next((k for k in range(len(bs) - 1, -1, -1) if bs[k] <= b + 0.001), 0), 0)]
    cor_de = lambda p, q, k: (par.get(p) or par.get(pt[k - 1] if k else "", None) or par.get("verso") or (None, None))[q] if par else None
    brilho = {"intro": 0.6, "verso": 0.75, "subida": 0.45, "queda": 1.0, "pausa": 0.15}
    L = []  # (batida, ids, acao, cor (None = a da familia), brilho, branco?)
    um = lambda b, ids, acao, cor, f, branco=False: L.append((round(b, 3), ids, acao, cor, round(f, 2), branco))
    um(0, todos_a + todos_m, 0, None, 0)
    base = []  # (batida, ids, cor, brilho): o estado de base do letreiro, para voltar depois de um clarao branco
    t1 = bs[0]
    passo = min(max(3 / max(len(ids_a), 1), 0.25), 0.5)
    for k, (b, p) in enumerate(sec):
        if k and pt[k - 1] == p and p != "subida":
            continue
        ca, cm = cor_de(p, 0, k), cor_de(p, 1, k)
        if p == "pausa":
            ca, cm = cor_de(pt[k - 1] if k else "verso", 1, k), cor_de(pt[k - 1] if k else "verso", 0, k)
        if p == "subida":  # do par da parte anterior ao da queda, compasso a compasso, e cada vez mais claro
            k0 = next(j for j in range(k, -1, -1) if j == 0 or pt[j - 1] != "subida")
            k1 = next(j for j in range(k, len(pt) + 1) if j == len(pt) or pt[j] != "subida")
            x = (k - k0 + 1) / (k1 - k0)
            de, ate = (par.get(pt[k0 - 1] if k0 else "", par.get("verso")), par.get("queda")) if par else (None, None)
            ca, cm = (mistura(de[0], ate[0], x), mistura(de[1], ate[1], x)) if par else (None, None)
            fim_k = bs[k + 1] if k + 1 < len(bs) else b + 4
            for j in range(4):  # o artista carrega: a cada batida mais letras acesas, da esquerda para a direita, ate todas na ultima batida antes da queda
                xb = (k - k0 + (j + 1) / 4) / (k1 - k0)
                cb, nl = (mistura(de[0], ate[0], xb) if par else None), max(1, int(np.ceil(xb * len(ids_a) - 1e-9)))
                um(b + j * (fim_k - b) / 4, [i for l in ids_a[:nl] for i in l], 1, cb, 0.45 + 0.55 * xb)
                if nl < len(ids_a):
                    um(b + j * (fim_k - b) / 4, [i for l in ids_a[nl:] for i in l], 1, cb, 0.08)
            um(b, todos_m, 1 if k == k0 else 4, cm, 0.3 + 0.4 * x)
            base += [(b, todos_a, ca, 0.45 + 0.55 * x), (b, todos_m, cm, 0.3 + 0.4 * x)]
            continue
        f = brilho.get(p, 0.7)
        if k == 0 and p != "pausa":  # a entrada: as letras do artista uma a uma, e a musica aparece devagar
            for j, letra in enumerate(ids_a):
                um(t1 + j * passo, letra, 2, ca, f)
            tr = t1 + len(ids_a) * passo
            um(tr, todos_m, 1, cm, 0); um(tr + 2, todos_m, 4, cm, 0.6)
            base += [(t1, todos_a, ca, f), (tr + 2, todos_m, cm, 0.6)]
            continue
        if p == "queda":  # o clarao branco corre pelas letras em uma batida e deixa a cor da queda
            for j, letra in enumerate(ids_a):
                um(b + j / len(ids_a), letra, 2, None, 1.0, True)
            um(b + 1, todos_a, 4, ca, f)
        else:
            um(b, todos_a, 1, ca, f)
        um(b, todos_m, 1, cm, f * 0.8)
        base += [(b + (1 if p == "queda" else 0), todos_a, ca, f), (b, todos_m, cm, f * 0.8)]
    agora = lambda b, ids: next(((c, f) for t, i, c, f in reversed(base) if i is ids and t <= b + 0.001), (None, 0.7))
    for e in ev:
        if not 0 < e["b"] < fim:
            continue
        p = parte(e["b"])
        if p == "queda" and e["et"] == 1 and e["i"] in (2, 6, 10):  # bumbo
            c, f = agora(e["b"], todos_a)
            um(e["b"], todos_a, 2, c, f)
        elif p == "queda" and e["et"] in (2, 3) and e["i"] in (2, 6, 10):  # caixa
            c, f = agora(e["b"], todos_m)
            um(e["b"], todos_m, 2, c, f)
        elif e["et"] == CENTRO and e["i"] in (10, 11) and not any(abs(e["b"] - b) < 0.01 and q == "queda" for b, q in sec):  # acento: clarao branco e volta a cor
            c, f = agora(e["b"], todos_a)
            um(e["b"], todos_a, 2, None, 1.0, True)
            um(e["b"] + 0.5, todos_a, 4, c, f)
    c, f = agora(fim, todos_a)
    um(fim, todos_a, 3, c, f)
    c, f = agora(fim, todos_m)
    um(fim, todos_m, 3, c, f)
    # os eventos do centro do cenario passam a mirar so nas luzes dele; e onde o letreiro muda numa batida sem evento do centro, o estado do centro vem
    # logo depois, com alvo vazio: o Chroma nao acende nada com ele, e sem o Chroma vale o ultimo da batida, entao o centro fica como estava
    mira = list(range(1, n4 + 1))
    centro = sorted((e for e in ev if e["et"] == CENTRO), key=lambda e: e["b"])
    for e in centro:
        e.setdefault("customData", {})["lightID"] = mira
    tem = {e["b"] for e in centro}
    novos = []
    for b, ids, acao, cor, f, branco in sorted(L, key=lambda x: x[0]):
        fam = 9 if branco else 5 if ids and ids[0] in todos_a else 1
        novos.append({"b": b, "et": CENTRO, "i": 0 if acao == 0 else fam + acao - 1, "f": f, "customData": {"lightID": ids, **({"color": [1, 1, 1]} if branco else {"color": list(cor)} if cor else {})}})
    volta = [{"b": b, "et": CENTRO, **estado(centro, b)} for b in sorted({x["b"] for x in novos} - tem)]
    ev += novos + volta
    meus = {id(x) for x in novos}
    ev.sort(key=lambda e: (e["b"], id(e) not in meus))  # na mesma batida, o letreiro antes: o ultimo, que o jogo sem o Chroma le, e do centro do cenario
    return len(novos) + len(volta)


def estado(centro, b):
    """O evento que poe o centro do cenario como o jogo sem o Chroma o deixou na batida `b` (centro = os eventos do centro, em ordem), com alvo vazio:
    o Chroma nao acende nada com ele, so o jogo sem o mod o le. Clarao que nao assentou vira aceso; pulso que nao sumiu, apagado."""
    u = next((e for e in reversed(centro) if e["b"] < b), None)
    if u is None or u["i"] == 0 or u["i"] % 4 == 3:
        return {"i": 0, "f": 0, "customData": {"lightID": []}}
    return {"i": u["i"] - (u["i"] - 1) % 4, "f": u["f"], "customData": {**u.get("customData", {}), "lightID": []}}


def vanilla(ev, et=CENTRO):
    """O que o jogo sem o Chroma faz com os eventos do tipo `et`: {batida: (valor, brilho)} do ultimo evento de cada batida."""
    v = {}
    for e in ev:
        if e["et"] == et:
            v[e["b"]] = (e["i"], e["f"])
    return v


def montar(amb, artista, musica):
    """O palco do cenario `amb` -> (customData do mapa: environment e materials, IDs das letras do artista e da musica, IDs das colunas da esquerda e da
    direita). Sem letreiro: no palco da propria banda (o nome certo ja esta la), num palco com nome de banda cujo letreiro nao se sabe esconder
    (ESCONDE) e em cenario fora das tabelas de luz (nao da para mirar)."""
    from beatloom.luzes import BANDA, banda
    da_banda = amb in (banda(artista) or ()) or any(amb in v for v in BANDA.values()) and amb not in ESCONDE
    pecas, ids_a, ids_m = ([], [], []) if da_banda or amb not in LUZES else letreiro(artista, musica)
    col, ce, cd = colunas() if amb in LUZES else ([], [], [])
    if not pecas and not col:
        return {}, [], [], [], []
    env = [{"id": i, "lookupMethod": m, "active": False} for i, m in ESCONDE.get(amb, ())] * bool(pecas) + pecas + col
    return {"environment": env, "materials": MATERIAIS}, ids_a, ids_m, ce, cd


def demo():
    rets, w = pixels("Ação")
    assert w == 23 and {r[4] for r in rets} == {0, 1, 2, 3}, (w, rets)  # A, C, A, O: o acento sai, a cedilha tambem
    assert pixels("L")[0] == [(0, 0, 1, 6, 0), (0, 6, 5, 1, 0)]  # a haste do L vira um retangulo so, o pe outro
    assert pixels("방탄소년단") == ([], 0) and pixels("  ") == ([], 0) and pixels("a b")[1] == 5 + 3 + 5 + 1
    assert all(len(set(map(len, v))) == 1 and len(v) == 7 for v in FONTE.values())  # toda letra com 7 linhas da mesma largura
    l, p = linhas("Green Day", *PIXEL[:1], MINIMO[0])
    assert len(l) == 1 and l[0][1] == 50 and p == LARGURA / 50  # 8 letras de 5 pixels, 7 vaos de 1 e um espaco de 3
    l, p = linhas("Falling In Reverse", PIXEL[0], MINIMO[0])
    assert [x[1] for x in l] == [56, 41] and p == min(0.75 * PIXEL[0], LARGURA / 56), ([x[1] for x in l], p)  # numa linha o pixel seria 0,38 m: duas, o mais parelhas possivel
    pecas, ia, im = letreiro("Green Day", "Basket Case")
    assert len(ia) == 8 and len(im) == 10 and len(pecas) == sum(map(len, ia)) + sum(map(len, im)) <= TETO, (len(ia), len(im), len(pecas))
    xs = [q["position"][0] for q in pecas[:sum(map(len, ia))]]
    assert abs(min(xs) + max(xs)) < 1 and max(q["position"][0] + q["scale"][0] / 2 for q in pecas) <= LARGURA / 2 + 0.01  # centrado, dentro da largura
    ya, ym = min(q["position"][1] for q in pecas[:sum(map(len, ia))]), max(q["position"][1] for q in pecas[sum(map(len, ia)):])
    assert ya > ym and min(q["position"][1] - q["scale"][1] / 2 for q in pecas) >= ONDE[1] - 0.01  # o artista em cima da musica, nada abaixo da base
    assert len({q["components"]["ILightWithId"]["lightID"] for q in pecas}) == len(pecas) and all(q["components"]["ILightWithId"]["type"] == CENTRO for q in pecas)
    assert letreiro("Desconhecido", "x") == ([], [], []) and letreiro("", "x") == ([], [], [])
    assert len(letreiro("A" * 200, "B" * 200)[0]) <= TETO
    cd, a, m, ce, cdir = montar("GreenDayEnvironment", "Green Day", "Basket Case")
    assert a == [] and len(ce) == 5 and len(cd["environment"]) == 10  # palco da propria banda: so as colunas
    assert montar("GreenDayEnvironment", "Daft Punk", "x")[1] == []  # palco com nome de banda que nao se sabe esconder: sem letreiro por cima
    ESCONDE["GreenDayEnvironment"] = [("Logo", "Contains")]
    try:
        cd, a, *_ = montar("GreenDayEnvironment", "Daft Punk", "x")
        assert a and cd["environment"][0] == {"id": "Logo", "lookupMethod": "Contains", "active": False} and montar("GreenDayEnvironment", "Green Day", "x")[1] == []
    finally:
        del ESCONDE["GreenDayEnvironment"]
    cd, a, m, ce, cdir = montar("NiceEnvironment", "Daft Punk", "One More Time")
    assert len(a) == 8 and cd["materials"] == MATERIAIS and montar("WeaveEnvironment", "Daft Punk", "x")[0] == {}
    # coreografia: 120 BPM, compassos de 4 batidas: intro, verso, subida, subida, queda, queda, pausa. Bumbo nos aneis na queda, um acento branco no verso
    sec = [(0, "intro"), (4, "verso"), (8, "subida"), (12, "subida"), (16, "queda"), (20, "queda"), (24, "pausa")]
    ev = [{"b": 0, "et": 4, "i": 1, "f": 0.4}, {"b": 4, "et": 4, "i": 1, "f": 0.4}, {"b": 6, "et": 4, "i": 11, "f": 1}, {"b": 16, "et": 4, "i": 10, "f": 1},
          {"b": 16, "et": 1, "i": 6, "f": 1}, {"b": 18, "et": 1, "i": 6, "f": 1}, {"b": 17, "et": 2, "i": 2, "f": 1}, {"b": 24, "et": 4, "i": 0, "f": 0}, {"b": 28, "et": 4, "i": 3, "f": 0.6}]
    antes = vanilla(ev)
    pal = (((1, 0, 0), (0, 0, 1)), ((0, 1, 0), (1, 1, 0)))
    n = coreografia(ev, sec, pal, ia, im, 14, 28)
    alvo = lambda e: e.get("customData", {}).get("lightID")
    meus = [e for e in ev if alvo(e) and alvo(e)[0] >= LETREIRO]
    fantasmas = [e for e in ev if alvo(e) == []]
    assert n == len(meus) + len(fantasmas) and len(meus) > 20 and {e["b"] for e in fantasmas} == {e["b"] for e in meus} - set(antes)
    depois, orig = vanilla(ev), [{"b": b, "i": v[0], "f": v[1]} for b, v in sorted(antes.items())]
    assert all(depois[b] == (v if b in antes else (estado(orig, b)["i"], estado(orig, b)["f"])) for b, v in depois.items())  # sem o Chroma, o centro e o mesmo
    assert depois[0.375] == (1, 0.4) and depois[6.5] == (0, 0) and depois[16.125] == (9, 1)  # aceso como estava; o pulso branco ja sumiu; o clarao assentado
    assert all(alvo(e) == list(range(1, 15)) for e in ev if e["et"] == 4 and e["b"] in antes and alvo(e)[0] < LETREIRO)  # o centro do cenario so mira nas luzes dele
    letras = sorted(e["b"] for e in meus if alvo(e) in ia and e["b"] < 4)
    assert letras == [0.375 * j for j in range(8)], letras  # a entrada: uma letra a cada 3/8 de batida
    assert any(e["b"] == 18 and alvo(e) == [i for l in ia for i in l] and e["i"] == 6 for e in meus)  # bumbo na queda: o artista pisca
    assert any(e["b"] == 17 and alvo(e) == [i for l in im for i in l] and e["i"] == 2 for e in meus)  # caixa: a musica pisca
    br = [e for e in meus if e["customData"].get("color") == [1, 1, 1]]
    assert {e["b"] for e in br} >= {6, 16, 16.125} and all(e["i"] == 10 for e in br)  # acento e a corrida branca da queda
    cores = {e["b"]: e["customData"].get("color") for e in meus if alvo(e) == [i for l in ia for i in l] and e["i"] in (5, 8)}
    assert cores[4] == [0, 0, 1] and cores[17] == [1, 0, 0] and cores[24] == [0, 0, 1], cores  # verso: B; queda: A; pausa: a segunda cor da queda
    acesas = [len(alvo(e)) for e in meus if 8 <= e["b"] < 16 and e["f"] > 0.1 and set(alvo(e)) <= {i for l in ia for i in l}]
    assert acesas == sorted(acesas) and acesas[0] == len(ia[0]) and acesas[-1] == sum(map(len, ia)) and len(acesas) == 8, acesas  # a subida acende o artista letra a letra
    assert [e["f"] for e in meus if e["b"] == 15 and alvo(e) == [i for l in ia for i in l]] == [1.0]  # ... e na ultima batida ele esta inteiro, no brilho cheio
    assert ev == sorted(ev, key=lambda e: e["b"]) and any(e["b"] == 28 and e["i"] == 7 for e in meus)  # o fim some devagar
    print("palco ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
