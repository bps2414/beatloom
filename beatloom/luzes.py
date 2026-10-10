"""Luzes: o que acende em cada momento da musica (deixas) e como isso vira evento do mapa.

Uma deixa e (segundo, luz, acao, cor, brilho). luz: 0 fundo, 1 aneis, 2 lasers da esquerda, 3 lasers da direita, 4 centro.
acao: 0 apaga, 1 acende, 2 clarao (estoura e fica aceso), 3 pulso (estoura e some). cor: 0 e 1 sao as duas cores do mapa, 2 e branco.
As outras deixas sao (segundo, GIRO ou ZOOM, 0, 0, 0) para os aneis e (segundo, VEL_E ou VEL_D, velocidade, 0, 0) para os lasers.
"""
import sys

import numpy as np

from beatloom.audio import CASAS, bateria, partes

FUNDO, ANEIS, ESQ, DIR, CENTRO, GIRO, ZOOM, VEL_E, VEL_D = 0, 1, 2, 3, 4, 8, 9, 12, 13
APAGA, ACENDE, CLARAO, PULSO = 0, 1, 2, 3
COR = {"intro": 1, "verso": 1, "subida": 0, "queda": 0}  # a cor de cada parte da musica; a pausa fica no escuro


def deixas(an, pt=None, pc=None):
    """A musica analisada -> as deixas, na ordem do tempo. `pt` (parte de cada compasso) e `pc` (peca da bateria de cada casa) so vem de fora no demo.

    Cada parte tem a sua cor e o seu jeito: introducao e verso com o fundo aceso e os aneis pulsando no bumbo, queda com tudo aceso, aneis girando
    e lasers batendo na caixa, pausa no escuro. Prato de ataque da um clarao branco no centro. Sem a bateria separada (modo rapido) o pulso vai na batida.
    """
    bat, ic, it = np.asarray(an["batidas"], float), [int(i) for i in an["ini_comp"]], np.asarray(an["intens"], float)
    g, nivel = np.asarray(an["grade"], float), np.asarray(an["nivel"])
    pt = partes(an) if pt is None else pt
    if pc is None and "nivel_drums" in an:
        pc = bateria(an)
    forca = np.maximum(an["forca"], an["forca_inst"].max(0)) if "forca_inst" in an else np.asarray(an["forca"], float)
    acento = float(np.percentile(forca[nivel == 2], 90)) if (nivel == 2).any() else 9e9
    lado, D = 0, [(0.0, FUNDO, ACENDE, 1, 0.3)]  # antes do primeiro compasso: so o fundo, baixinho
    for k, (a, b) in enumerate(zip(ic[:-1], ic[1:])):
        p, i, t0 = pt[k], float(it[k]), float(bat[a])
        muda = k == 0 or pt[k - 1] != p
        if p == "pausa":
            if muda:
                D += [(t0, e, APAGA, 0, 0) for e in range(5)]
            continue
        cor, queda = COR[p], p == "queda"
        outra = 1 - cor
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
            if queda and pos == 0:
                D.append((t, GIRO, 0, 0, 0))
            if peca in (1, 4) and pos % 2 == 0:  # bumbo (o prato de ataque quase sempre vem com ele): os aneis pulsam
                D.append((t, ANEIS, CLARAO if queda else PULSO, cor, 1.0 if queda else 0.5 + 0.5 * i))
            elif peca == 2 and queda:  # caixa: um lado dos lasers de cada vez
                D.append((t, (ESQ, DIR)[lado], CLARAO, outra, 1.0))
                lado ^= 1
            if peca == 4 or (pc is None and pos == 0 and c == a * CASAS and forca[c] >= acento):
                D.append((t, CENTRO, PULSO if not queda else CLARAO, 2, 1.0))  # acento: clarao branco
    D += [(float(bat[ic[-1]]), e, PULSO, 1, 0.6) for e in (FUNDO, CENTRO)] + [(float(bat[ic[-1]]), e, APAGA, 0, 0) for e in (ANEIS, ESQ, DIR)]  # o fim da musica some devagar
    return sorted(D, key=lambda d: d[0])  # a ordem de quem empata fica: a deixa posta depois vale


def basicos(D, bt):
    """Deixas -> eventos basicos do mapa (os dos cenarios classicos). Duas deixas na mesma luz e na mesma batida: vale a ultima."""
    ev = {}
    for t, e, acao, cor, f in D:
        ev[(round(bt(t), 3), e)] = (acao if e > CENTRO or acao == APAGA else (5, 1, 9)[cor] + acao - 1, round(f, 2) if e <= CENTRO else 1)
    return [{"b": b, "et": e, "i": int(v), "f": f} for (b, e), (v, f) in sorted(ev.items())]


def demo():
    # 4 compassos de 4 batidas, uma por segundo: verso, pausa, queda, queda. Bumbo na batida 1 de cada compasso, caixa na 3, prato de ataque abrindo a queda
    pc = np.zeros(65, int)
    pc[[0, 16, 32, 48]], pc[[8, 24, 40, 56]], pc[32] = 1, 2, 4
    an = {"batidas": np.arange(17.0), "ini_comp": np.arange(0, 17, 4), "intens": [0.5, 0.05, 0.9, 1.0], "grade": np.arange(65) / 4, "nivel": np.full(65, 2), "forca": np.ones(65)}
    D = deixas(an, ["verso", "pausa", "queda", "queda"], pc)
    em = lambda a, b: [d[1:4] for d in D if a <= d[0] < b]
    assert (ANEIS, PULSO, 1) in em(0, 1) and not any(e in (GIRO, ZOOM) for e, _, _ in em(0, 4)), em(0, 4)
    assert sorted(em(4, 8)) == [(e, APAGA, 0) for e in range(5)], em(4, 8)  # a pausa apaga tudo e nada acende dentro dela
    assert (CENTRO, CLARAO, 2) in em(8, 8.1) and (ZOOM, 0, 0) in em(8, 8.1) and sum(e == GIRO for e, _, _ in em(8, 16)) == 8, em(8, 9)
    assert (ESQ, CLARAO, 1) in em(10, 10.1) and (DIR, CLARAO, 1) in em(14, 14.1), em(10, 15)
    ev = basicos(D, lambda t: t * 2)  # 120 BPM
    assert {"b": 8.0, "et": ANEIS, "i": 0, "f": 0} in ev and {"b": 16.0, "et": CENTRO, "i": 10, "f": 1.0} in ev, [e for e in ev if e["b"] in (8.0, 16.0)]
    assert len({(e["b"], e["et"]) for e in ev}) == len(ev) and [e["b"] for e in ev] == sorted(e["b"] for e in ev)
    print("luzes ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
