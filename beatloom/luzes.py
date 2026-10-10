"""Luzes: o que acende em cada momento da musica (deixas) e como isso vira evento do mapa.

Uma deixa e (segundo, luz, acao, cor, brilho). luz: 0 fundo, 1 aneis, 2 lasers da esquerda, 3 lasers da direita, 4 centro.
acao: 0 apaga, 1 acende, 2 clarao (estoura e fica aceso), 3 pulso (estoura e some). cor: 0 e 1 sao as duas cores do mapa, 2 e branco.
As outras deixas sao (segundo, GIRO ou ZOOM, 0, 0, 0) para os aneis e (segundo, VEL_E ou VEL_D, velocidade, 0, 0) para os lasers.

Os cenarios classicos acendem com eventos basicos (basicos); os novos so com grupos de luzes (grupos), cada cenario com os seus (GRUPOS).
As cores saem da capa (cores): um par para o mapa e outro para o reforco ("boost"), que entra na queda (reforco).
"""
import colorsys, subprocess, sys

import numpy as np

from beatloom.audio import CASAS, bateria, partes

FUNDO, ANEIS, ESQ, DIR, CENTRO, GIRO, ZOOM, VEL_E, VEL_D = 0, 1, 2, 3, 4, 8, 9, 12, 13
APAGA, ACENDE, CLARAO, PULSO = 0, 1, 2, 3
# os cenarios do jogo para cada clima da musica (audio.clima): um classico, que acende com os eventos basicos, e um novo, que acende com grupos de luzes
AMBIENTE = {"calmo": ("BigMirrorEnvironment", "TheSecondEnvironment"), "pesado": ("GreenDayEnvironment", "RockMixtapeEnvironment"), "eletronico": ("MonstercatEnvironment", "WeaveEnvironment")}
# cenarios novos: que grupos de luzes fazem o papel de cada luz das deixas, e que grupos giram os lasers da esquerda e da direita (numeros dos grupos: tabela do bsmap)
GRUPOS = {
    "TheSecondEnvironment": {FUNDO: (2, 3), ANEIS: (0, 1), ESQ: (6, 8, 10, 12), DIR: (7, 9, 11, 13), CENTRO: (4, 5), GIRO: ((6, 8, 10, 12), (7, 9, 11, 13))},
    "RockMixtapeEnvironment": {FUNDO: tuple(range(2, 14)), ANEIS: (15, 16, 17), ESQ: (0, 18), DIR: (1, 19), CENTRO: (14, 22, 23), GIRO: ((20,), (21,))},
    "WeaveEnvironment": {FUNDO: (14, 15), ANEIS: (4, 5, 6, 7), ESQ: (0, 2, 8, 10), DIR: (1, 3, 9, 11), CENTRO: (12, 13), GIRO: ((0, 2, 8, 10), (1, 3, 9, 11))},
}
COR = {"intro": 1, "verso": 1, "subida": 0, "queda": 0}  # a cor de cada parte da musica; a pausa fica no escuro


def deixas(an, pt=None, pc=None):
    """A musica analisada -> as deixas, na ordem do tempo. `pt` (parte de cada compasso) e `pc` (peca da bateria de cada casa) so vem de fora no demo.

    Cada parte tem a sua cor e o seu jeito, que volta quando a parte volta: introducao e verso com o fundo aceso e os aneis pulsando no bumbo, queda com
    tudo aceso, aneis girando no bumbo e lasers batendo na caixa, pausa no escuro. A subida comeca quase apagada e acende uma luz depois da outra ate a
    queda; se a musica cala logo antes da queda, apaga tudo de uma vez nesse silencio. Prato de ataque da um clarao branco no centro.
    Sem a bateria separada (modo rapido) o pulso vai na batida.
    """
    bat, ic, it = np.asarray(an["batidas"], float), [int(i) for i in an["ini_comp"]], np.asarray(an["intens"], float)
    g, nivel = np.asarray(an["grade"], float), np.asarray(an["nivel"])
    pt = partes(an) if pt is None else pt
    if pc is None and "nivel_drums" in an:
        pc = bateria(an)
    forca = np.maximum(an["forca"], an["forca_inst"].max(0)) if "forca_inst" in an else np.asarray(an["forca"], float)
    acento = float(np.percentile(forca[nivel == 2], 90)) if (nivel == 2).any() else 9e9
    lado, escuros, D = 0, [], [(0.0, FUNDO, ACENDE, 1, 0.3)]  # antes do primeiro compasso: so o fundo, baixinho
    for k, (a, b) in enumerate(zip(ic[:-1], ic[1:])):
        p, i, t0 = pt[k], float(it[k]), float(bat[a])
        muda = k == 0 or pt[k - 1] != p
        if p == "pausa":
            if muda:
                D += [(t0, e, APAGA, 0, 0) for e in range(5)]
            continue
        cor, queda = COR[p], p == "queda"
        outra = 1 - cor
        if queda and muda and k:  # apagao seco: a ultima batida (ou meia batida) antes da queda, se nao ha ataque forte nela
            c0 = next((c for c in (a * CASAS - CASAS, a * CASAS - CASAS // 2) if not (nivel[c + 1:a * CASAS] == 2).any()), None)
            if c0 is not None:
                escuros.append((float(g[c0]), t0))
        if p == "subida":  # do escuro ate tudo aceso, batida a batida: fundo, depois aneis, lasers e por fim o centro e o giro dos aneis
            k0 = next(j for j in range(k, -1, -1) if j == 0 or pt[j - 1] != "subida")
            k1 = next(j for j in range(k, len(pt) + 1) if j == len(pt) or pt[j] != "subida")
            if muda:
                D += [(t0, e, APAGA, 0, 0) for e in (ANEIS, ESQ, DIR, CENTRO)]
            for j in range(a, b):
                t, x = float(bat[j]), (j - ic[k0]) / (ic[k1] - ic[k0])
                D += [(t, FUNDO, ACENDE, cor, 0.2 + 0.8 * x), (t, VEL_E, 1 + round(7 * x), 0, 0), (t, VEL_D, 1 + round(7 * x), 0, 0)]
                D += [(t, ANEIS, PULSO, cor, 0.4 + 0.6 * x)] * (x >= 0.25) + [(t, ESQ, ACENDE, outra, x), (t, DIR, ACENDE, outra, x)] * (x >= 0.5)
                if x >= 0.75:
                    D += [(t, CENTRO, ACENDE, cor, x), (t, GIRO, 0, 0, 0)] + [((t + float(bat[j + 1])) / 2, GIRO, 0, 0, 0)] * (k + 1 == k1)  # no ultimo compasso os aneis giram em dobro
            continue
        D.append((t0, FUNDO, CLARAO if queda else ACENDE, cor, 1.0 if queda else 0.35 + 0.4 * i))
        D += [(t0, VEL_E, 1 + round(i * (6 if queda else 3)), 0, 0), (t0, VEL_D, 1 + round(i * (6 if queda else 3)), 0, 0)]
        if queda:  # lasers dos dois lados, trocando de cor a cada compasso; aneis abrem e fecham a cada 4
            D += [(t0, ESQ, ACENDE, cor if k % 2 else outra, 0.8), (t0, DIR, ACENDE, outra if k % 2 else cor, 0.8)]
            if muda or k % 4 == 0:
                D.append((t0, ZOOM, 0, 0, 0))
            if muda:
                D += [(t0, e, CLARAO, 2, 1.0) for e in (FUNDO, CENTRO)]  # a queda entra com um clarao branco
        elif muda or pt[k - 1] == "pausa":
            D += [(t0, CENTRO, ACENDE, cor, 0.4), (t0, ESQ, APAGA, 0, 0), (t0, DIR, APAGA, 0, 0)]
            if p != "intro" and i >= 0.5:  # verso cheio: um par de lasers lentos, na outra cor
                D += [(t0, ESQ, ACENDE, outra, 0.5), (t0, DIR, ACENDE, outra, 0.5)]
        for c in range(a * CASAS, min(b * CASAS, len(g))):
            t, pos = float(g[c]), (c - a * CASAS) % CASAS
            peca = int(pc[c]) if pc is not None else (1 if pos == 0 and nivel[c] else 0)
            if peca in (1, 4) and pos % 2 == 0:  # bumbo (o prato de ataque quase sempre vem com ele): os aneis pulsam e, na queda, giram
                D += [(t, ANEIS, CLARAO if queda else PULSO, cor, 1.0 if queda else 0.5 + 0.5 * i)] + [(t, GIRO, 0, 0, 0)] * queda
            elif peca == 2 and queda:  # caixa: um lado dos lasers de cada vez
                D.append((t, (ESQ, DIR)[lado], CLARAO, outra, 1.0))
                lado ^= 1
            if peca == 4 or (pc is None and pos == 0 and c == a * CASAS and forca[c] >= acento):
                D.append((t, CENTRO, PULSO if not queda else CLARAO, 2, 1.0))  # acento: clarao branco
    D += [(float(bat[ic[-1]]), e, PULSO, 1, 0.6) for e in (FUNDO, CENTRO)] + [(float(bat[ic[-1]]), e, APAGA, 0, 0) for e in (ANEIS, ESQ, DIR)]  # o fim da musica some devagar
    D = [d for d in D if not any(e0 <= d[0] < e1 for e0, e1 in escuros)] + [(e0, e, APAGA, 0, 0) for e0, _ in escuros for e in range(5)]
    return sorted(D, key=lambda d: d[0])  # a ordem de quem empata fica: a deixa posta depois vale


def basicos(D, bt):
    """Deixas -> eventos basicos do mapa (os dos cenarios classicos). Duas deixas na mesma luz e na mesma batida: vale a ultima."""
    ev = {}
    for t, e, acao, cor, f in D:
        ev[(round(bt(t), 3), e)] = (acao if e > CENTRO or acao == APAGA else (5, 1, 9)[cor] + acao - 1, round(f, 2) if e <= CENTRO else 1)
    return [{"b": b, "et": e, "i": int(v), "f": f} for (b, e), (v, f) in sorted(ev.items())]


def ambiente(clima, marca):
    """O cenario de uma musica: um dos do clima dela, sempre o mesmo para a mesma musica (`marca` = o hash do audio)."""
    return AMBIENTE[clima][int(marca[:4], 16) % len(AMBIENTE[clima])]


def grupos(D, bt, amb):
    """Deixas -> (eventos de cor, eventos de rotacao) dos grupos de luzes do cenario `amb`, um dos de GRUPOS.

    Acender e um evento seco; o clarao estoura e volta ao brilho pedido em 1/4 de batida; o pulso estoura e some em pouco mais de meia batida (menos, se a
    proxima deixa da mesma luz vem antes). A cada giro os lasers abrem em leque e fecham, um lado espelhando o outro. Zoom e velocidade nao existem aqui.
    """
    tab, todos = GRUPOS[amb], {"f": 1, "p": 1, "t": 0, "r": 0, "c": 0, "n": 0, "s": 0, "l": 0, "d": 0}  # filtro: todas as luzes do grupo
    por, giros = {}, []
    for t, e, acao, cor, f in D:
        if e <= CENTRO:
            por.setdefault(e, {})[round(bt(t), 3)] = (acao, cor, f)  # duas deixas na mesma luz e na mesma batida: vale a ultima
        elif e == GIRO and round(bt(t), 3) not in giros:
            giros.append(round(bt(t), 3))
    cor_ev, rot_ev = [], []
    for e, deixas_ in por.items():
        bs = sorted(deixas_)
        for b, prox in zip(bs, bs[1:] + [bs[-1] + 9]):
            acao, cor, f = deixas_[b]
            um = lambda quando, como, brilho: {"b": round(quando, 3), "i": como, "c": cor, "s": round(brilho, 2), "f": 0}
            if acao == APAGA:
                passos = [{"b": 0, "i": 0, "c": 0, "s": 0, "f": 0}]
            elif acao == ACENDE or prox - b < 0.1:
                passos = [um(0, 0, f)]
            else:
                passos = [um(0, 0, 1.4 * f), um(min(0.25, 0.9 * (prox - b)), 1, f) if acao == CLARAO else um(min(0.6, 0.9 * (prox - b)), 1, 0)]
            cor_ev += [{"b": b, "g": g, "e": [{"f": todos, "w": 0, "d": 1, "r": 0, "t": 1, "b": 1, "i": 0, "e": passos}]} for g in tab[e]]
    for n, b in enumerate(giros):
        # do angulo em que estava ate o novo em meia batida: aberto (30 graus de uma luz a outra do grupo) nos giros pares, fechado nos impares
        passos = [{"b": 0, "p": 1, "e": 0, "l": 0, "r": 0, "o": 0}, {"b": 0.5, "p": 0, "e": 2, "l": 0, "r": 0 if n % 2 else 35, "o": 0}]
        rot_ev += [{"b": b, "g": g, "e": [{"f": todos, "w": 0, "d": 1, "s": 0 if n % 2 else 30, "t": 1, "b": 1, "i": 0, "a": 0, "r": lado, "l": passos}]} for lado in (0, 1) for g in tab[GIRO][lado]]
    return sorted(cor_ev, key=lambda x: (x["b"], x["g"])), sorted(rot_ev, key=lambda x: (x["b"], x["g"]))


def reforco(an, bt, pt=None):
    """Eventos de reforco de cor: o segundo par de cores entra em cada queda e sai no fim dela."""
    bat, ic, pt = an["batidas"], an["ini_comp"], partes(an) if pt is None else pt
    q = [p == "queda" for p in pt]
    return [{"b": round(bt(float(bat[ic[k]])), 3), "o": q[k]} for k in range(len(q)) if q[k] != (k > 0 and q[k - 1])]


def paleta(px):
    """Pixels RGB de 0 a 1, [n, 3] -> ((cor A, cor B), (A do reforco, B do reforco)) ou None.

    A e o tom que mais aparece na imagem; B e o segundo, se estiver a pelo menos 60 graus de A na roda de cores, senao e o tom oposto a A (a maioria
    das capas tem um tom so, e duas luzes da mesma cor nao servem). O par do reforco sao os dois tons seguintes, ou os do primeiro par girados 30 graus
    quando a capa nao tem mais tons. Sai tudo com brilho cheio e bastante saturacao, porque luz escura nao aparece.
    None = capa cinza (menos de 8% de pixels com cor): o mapa fica com as cores do jogo.
    """
    px = np.asarray(px, float)
    v, mn = px.max(1), px.min(1)
    sat = np.where(v > 0, (v - mn) / np.maximum(v, 1e-9), 0)
    c = (sat >= 0.3) & (v >= 0.25)
    if c.mean() < 0.08:
        return None
    r, g, b = px[c].T
    d = np.maximum(v[c] - mn[c], 1e-9)
    tom = np.where(v[c] == r, (g - b) / d % 6, np.where(v[c] == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
    N = 24  # fatias de 15 graus
    h = np.bincount((tom * N).astype(int) % N, weights=sat[c] * v[c], minlength=N)
    h = (np.roll(h, 1) + 2 * h + np.roll(h, -1)) / 4
    dist = lambda i: np.minimum(abs(np.arange(N) - i), N - abs(np.arange(N) - i))  # de cada fatia ate a fatia i, em fatias
    tem = lambda resto: resto.max() >= 0.04 * h.sum()  # um tom que quase nao aparece nao conta
    a = int(np.argmax(h))
    b = int(np.argmax(h * (dist(a) >= 4))) if tem(h * (dist(a) >= 4)) else (a + N // 2) % N
    # reforco: o terceiro e o quarto tons da capa (a 45 graus ou mais do primeiro par); o que faltar e um do primeiro par girado 30 graus
    resto = h * (dist(a) >= 3) * (dist(b) >= 3)
    a2 = int(np.argmax(resto)) if tem(resto) else (a + 2) % N
    resto = resto * (dist(a2) >= 4)
    b2 = int(np.argmax(resto)) if tem(resto) else max((a + 2) % N, (b + 2) % N, key=lambda i: dist(a2)[i])
    na_fatia = lambda i: sat[c][(tom * N).astype(int) % N == i]
    cor = lambda i: tuple(round(x, 3) for x in colorsys.hsv_to_rgb((i + 0.5) / N, float(np.clip(np.median(na_fatia(i)) if len(na_fatia(i)) else 1, 0.7, 1)), 1.0))
    return (cor(a), cor(b)), (cor(a2), cor(b2))


def cores(imagem):
    """A paleta (ver paleta) de um arquivo de imagem, ou None se nao der para ler."""
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(imagem), "-vf", "scale=48:48", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return paleta(np.frombuffer(r.stdout, np.uint8).reshape(-1, 3) / 255) if r.returncode == 0 and len(r.stdout) == 48 * 48 * 3 else None


def contraste(a, b):
    """Dois tons servem para sabre e nota? So se estiverem a 90 graus ou mais um do outro: com menos, na pressa, uma nota parece a outra."""
    d = abs(colorsys.rgb_to_hsv(*a)[0] - colorsys.rgb_to_hsv(*b)[0])
    return min(d, 1 - d) >= 0.25


def demo():
    rng = np.random.default_rng(0)
    cinza, verm, azul, verde = rng.random((300, 1)) * np.ones((1, 3)), [0.8, 0.1, 0.1] + rng.random((300, 3)) * 0.1, [0.1, 0.2, 0.9] + rng.random((200, 3)) * 0.1, [0.1, 0.6, 0.3] + rng.random((100, 3)) * 0.05
    assert paleta(cinza) is None and paleta(np.vstack([cinza, verm]))[0] == ((1.0, 0.259, 0.153), (0.0, 0.875, 1.0))  # cinza; e um tom so, que ganha o oposto
    (a, b), (a2, b2) = paleta(np.vstack([cinza, verm, azul, verde]))
    assert a[0] == 1 and a[2] < 0.3 and b[2] == 1 and b[0] < 0.3 and contraste(a, b), (a, b)  # vermelho na frente (aparece mais), depois azul; os dois de brilho cheio
    assert a2[1] == 1 and max(a2[0], a2[2]) < 0.6 and b2 not in (a, b), (a2, b2)  # o reforco comeca pelo verde, o terceiro tom
    assert not contraste((1, 0, 0), (1, 0.8, 0)) and contraste((1, 0, 0), (0, 0.4, 1))
    an_r = {"batidas": np.arange(21.0), "ini_comp": np.arange(0, 21, 4)}
    assert reforco(an_r, lambda t: t, ["verso", "queda", "queda", "verso", "queda"]) == [{"b": 4.0, "o": True}, {"b": 12.0, "o": False}, {"b": 16.0, "o": True}]
    # 4 compassos de 4 batidas, uma por segundo: verso, pausa, queda, queda. Bumbo na batida 1 de cada compasso, caixa na 3, prato de ataque abrindo a queda
    pc = np.zeros(65, int)
    pc[[0, 16, 32, 48]], pc[[8, 24, 40, 56]], pc[32] = 1, 2, 4
    an = {"batidas": np.arange(17.0), "ini_comp": np.arange(0, 17, 4), "intens": [0.5, 0.05, 0.9, 1.0], "grade": np.arange(65) / 4, "nivel": np.full(65, 2), "forca": np.ones(65)}
    D = deixas(an, ["verso", "pausa", "queda", "queda"], pc)
    em = lambda a, b: [d[1:4] for d in D if a <= d[0] < b]
    assert (ANEIS, PULSO, 1) in em(0, 1) and not any(e in (GIRO, ZOOM) for e, _, _ in em(0, 4)), em(0, 4)
    assert sorted(em(4, 8)) == [(e, APAGA, 0) for e in range(5)], em(4, 8)  # a pausa apaga tudo e nada acende dentro dela
    assert (CENTRO, CLARAO, 2) in em(8, 8.1) and (ZOOM, 0, 0) in em(8, 8.1) and [d[0] for d in D if d[1] == GIRO] == [8, 12], em(8, 9)  # os aneis giram no bumbo
    # verso, subida, queda, queda, com silencio na ultima batida da subida: o fundo sobe de brilho, as luzes entram uma a uma e a batida 7 fica no escuro
    an["nivel"] = np.where((np.arange(65) > 28) & (np.arange(65) < 32), 0, 2)
    D = deixas(an, ["verso", "subida", "queda", "queda"], pc)
    fundo = [d[4] for d in D if d[1] == FUNDO and 4 <= d[0] < 7]
    assert fundo == sorted(fundo) and fundo[0] == 0.2 and (ANEIS, PULSO, 0) in em(5, 5.1) and (ESQ, ACENDE, 1) not in em(5, 5.1) and (ESQ, ACENDE, 1) in em(6, 6.1), em(4, 7)
    assert sorted(em(7, 8)) == [(e, APAGA, 0) for e in range(5)] and (FUNDO, CLARAO, 2) in em(8, 8.1), em(7, 8.1)
    assert (ESQ, CLARAO, 1) in em(10, 10.1) and (DIR, CLARAO, 1) in em(14, 14.1), em(10, 15)
    ev = basicos(D, lambda t: t * 2)  # 120 BPM
    assert {"b": 8.0, "et": ANEIS, "i": 0, "f": 0} in ev and {"b": 16.0, "et": CENTRO, "i": 10, "f": 1.0} in ev, [e for e in ev if e["b"] in (8.0, 16.0)]
    assert len({(e["b"], e["et"]) for e in ev}) == len(ev) and [e["b"] for e in ev] == sorted(e["b"] for e in ev)
    # cenario novo: o pulso dos aneis da batida 0 vira estouro + sumir nos 2 grupos de aneis; o clarao do centro em 16 volta ao brilho pedido; 2 giros, 8 grupos de laser cada
    an["nivel"] = np.full(65, 2)
    cor_ev, rot_ev = grupos(deixas(an, ["verso", "pausa", "queda", "queda"], pc), lambda t: t * 2, "TheSecondEnvironment")
    pulso = [x for x in cor_ev if x["b"] == 0 and x["g"] in (0, 1)]
    assert len(pulso) == 2 and [(p["i"], p["c"], p["s"]) for p in pulso[0]["e"][0]["e"]] == [(0, 1, 1.05), (1, 1, 0)] and pulso[0]["e"][0]["e"][1]["b"] == 0.6, pulso
    assert [p["s"] for x in cor_ev if x["b"] == 16 and x["g"] == 4 for p in x["e"][0]["e"]] == [1.4, 1.0] and all(p["s"] == 0 for x in cor_ev if x["b"] == 8 for p in x["e"][0]["e"])
    assert len(rot_ev) == 16 and {x["e"][0]["l"][1]["r"] for x in rot_ev} == {35, 0} and {x["e"][0]["r"] for x in rot_ev if x["g"] in (7, 9, 11, 13)} == {1}, rot_ev[:2]
    assert ambiente("pesado", "00ff") == "RockMixtapeEnvironment" and ambiente("pesado", "00fe") == "GreenDayEnvironment" and all(v[1] in GRUPOS for v in AMBIENTE.values())
    print("luzes ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
