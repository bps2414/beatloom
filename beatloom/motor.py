"""Peca 3 - QUAL NOTA: motor de golpes proprio (etapas 3 e 4).

Anda pela musica batida a batida. Para cada janela de 4, 2 ou 1 batidas procura na biblioteca um padrao humano com o
MESMO ritmo, que encaixe no estado atual dos dois sabres (lado do golpe, rotacao do pulso, posicao) e passe pelas
checagens (paridade sem aviso, bloqueio de visao, palmas, notas empilhadas, velocidade do braco). Compasso repetido
tenta primeiro reusar o desenho do compasso original. Se nada servir, cai numa regra simples de sobe-desce.
"""
import math, pickle, random
from collections import Counter
from functools import lru_cache

import numpy as np

from beatloom import checks
from beatloom.audio import CASAS, INSTRUMENTOS, RAIZ

# menor intervalo entre dois golpes da MESMA mao (s): limita a velocidade do braco por dificuldade
MIN_MAO = {"Normal": 0.30, "Hard": 0.20, "Expert": 0.15, "ExpertPlus": 0.115}
from beatloom.checks import SEM_CRUZAR, VEL_MAO  # teto de velocidade da mao e dificuldades em que o braco nunca cruza (nas outras, cruzar perde pontos)
TENTATIVAS = 80
VIRA = {0: 1, 1: 0, 2: 2, 3: 3, 4: 6, 6: 4, 5: 7, 7: 5}  # inverte o corte na vertical


def variantes(pad):
    """O padrao como e, e depois com uma ou as duas maos invertidas na vertical (cima <-> baixo).

    Cada nota troca o lado do golpe da mao, entao metade das vezes o braco chega ao trecho repetido "do outro lado"
    e o desenho identico e impossivel. O invertido mantem ritmo, maos e colunas.
    """
    yield pad, False
    for maos in ((0,), (1,), (0, 1)):
        yield tuple((o, x, 2 - y if c in maos else y, c, VIRA[d] if c in maos else d) for o, x, y, c, d in pad), True


@lru_cache(None)
def biblioteca(dif):
    arq = RAIZ / "dados" / f"padroes_{dif}.pkl"
    if not arq.exists():
        raise SystemExit(f"Falta a biblioteca de padroes ({arq.name}). Rode ferramentas\\baixar_mapas.py e depois ferramentas\\extrair_padroes.py.")
    with open(arq, "rb") as f:
        return pickle.load(f)


class Maos:
    """Estado dos dois sabres: lado do ultimo golpe, rotacao do pulso, ultima nota e quando foi."""

    def __init__(self):
        self.est = {0: ("b", 0), 1: ("b", 0)}  # proximo golpe esperado: ida (para baixo)
        self.ult = {0: None, 1: None}          # (t, casa, x, y, d)

    def copia(self):
        m = Maos()
        m.est, m.ult = dict(self.est), dict(self.ult)
        return m

    def bate(self, t, casa, x, y, c, d, min_mao, vel_mao=99):
        """Aplica uma nota. Devolve False se quebra paridade (erro ou aviso) ou se o braco nao da tempo."""
        st, e, r = checks.paridade(*self.est[c], c, d)
        u = self.ult[c]
        if st != "ok" or (u and (t - u[0] < min_mao or math.hypot(x - u[2], y - u[3]) > vel_mao * (t - u[0]))):
            return False
        self.est[c], self.ult[c] = (e, r), (t, casa, x, y, d)
        return True


def golpes(tempos, an, dif, reacao, etapa, njs=16, arcos=()):
    """tempos = {casa: 1|2}; arcos = [(casa_ini, casa_fim)] das notas seguradas pedidas.
    Devolve (notas [(t_s, x, y, cor, dir)], texto de resumo, seguradas [(t_ini, t_fim, cor)])."""
    lib, grade = biblioteca(dif), an["grade"]
    rng = random.Random(f"{an['hash']}-{dif}")
    min_mao, vel_mao = MIN_MAO[dif], VEL_MAO[dif]
    intens = [float(v) for v in an["intens"]]
    usos = Counter()  # quantas vezes cada desenho ja saiu: repetir sempre o mesmo cansa
    tam = int(an["batidas_por_compasso"])
    ini_comp = [int(v) for v in an["ini_comp"]]
    comp_de = {b: k for k, (a, z) in enumerate(zip(ini_comp[:-1], ini_comp[1:])) for b in range(a, z)}
    rep = [int(v) for v in an["rep"]]
    # etapa 4: cada casa sabe se o ataque e de bateria/baixo (grave, embaixo) ou de voz/melodia (em cima)
    alto = None
    if etapa >= 4 and "forca_inst" in an:
        f = np.asarray(an["forca_inst"])
        ritmo, melodia = f[[INSTRUMENTOS.index("drums"), INSTRUMENTOS.index("bass")]].max(0), f[[INSTRUMENTOS.index("other"), INSTRUMENTOS.index("vocals")]].max(0)
        alto = melodia > ritmo * 1.15

    maos_atual, notas_todas = [Maos()], []
    usado = {}  # (compasso, posicao no compasso, L) -> padrao usado, para repetir nos compassos iguais
    stats = {"padrao4": 0, "padrao2": 0, "padrao1": 0, "regra": 0, "rep_tentou": 0, "rep_igual": 0, "rep_inv": 0, "descartadas": 0}

    colado = max(1.425 / njs, 0.12)  # cores diferentes na mesma casa precisam deste intervalo (MapCheck: hitboxInline)

    def tentar(padrao, casa0, maos=None, notas=None):
        """Tenta colar o padrao a partir da casa0. Devolve (novas_notas, novas_maos) ou None."""
        maos, notas = maos or maos_atual[0], notas if notas is not None else notas_todas
        m, novas = maos.copia(), []
        for off, x, y, c, d in padrao:
            casa = casa0 + off
            t = float(grade[casa])
            if not m.bate(t, casa, x, y, c, d, min_mao, vel_mao):
                return None
            novas.append((t, x, y, c, d))
        cauda = [n for n in notas[-12:] if n[0] >= novas[0][0] - reacao - 0.05]
        junto = cauda + novas
        if (checks.bloqueios_de_visao(junto, dif, reacao) or checks.palmas(junto) or checks.empilhadas(junto) or checks.atravessadas(novas)):
            return None
        if dif in SEM_CRUZAR and any(t >= novas[0][0] for t in checks.cruzadas(junto)):
            return None
        for i, a in enumerate(junto):
            for z in junto[max(i + 1, len(cauda)):]:
                if a[3] != z[3] and (a[1], a[2]) == (z[1], z[2]) and 0.011 < z[0] - a[0] < colado:
                    return None
        return novas, m

    def original(b):
        """Se a janela que comeca na batida b esta num compasso repetido, devolve (L, casa0, mascara, padrao) do original."""
        k = comp_de.get(b)
        if k is None or rep[k] == k:
            return None
        pos = b - ini_comp[k]
        for L in (4, 2, 1):
            o = usado.get((rep[k], pos, L))
            if o is not None:
                masc = "".join(str(tempos.get(b * CASAS + i, 0)) for i in range(L * CASAS))
                return (L, b * CASAS, masc, o[1]) if o[0] == masc else None
        return None

    def pontos(pad, pre, casa0):
        maos = maos_atual[0]
        """Quanto o padrao combina com a situacao: braco vindo do mesmo lugar que no mapa humano, e altura por instrumento."""
        p = 0.0
        for c in (0, 1):
            u = maos.ult[c]
            if pre[c] is None or u is None:
                continue
            if u[4] == pre[c][2]:
                p += 1 + (2 if (u[2], u[3]) == (pre[c][0], pre[c][1]) else 0)
            gap = casa0 + next((n[0] for n in pad if n[3] == c), 0) - u[1]
            if gap < min(pre[c][3], 3):
                p -= 3  # no mapa humano o braco tinha mais tempo para chegar aqui
        if alto is not None:
            for off, x, y, c, d in pad:
                p += 0.6 if (y >= 1) == bool(alto[casa0 + off]) else -0.3
        # manha: trecho forte pede desenho aberto (linhas de cima, pontas, diagonais); trecho calmo pede sobe-desce simples embaixo
        it = intens[min(comp_de.get(casa0 // CASAS, 0), len(intens) - 1)]
        for off, x, y, c, d in pad:
            aberto = y >= 1 or x in (0, 3) or d >= 4
            p += (0.3 if aberto else -0.1) if it >= 0.6 else (0.3 if not aberto else -0.2) if it <= 0.3 else 0
            if dif == "Normal" and d >= 4:
                p -= 0.6  # Normal: golpe simples, pouca diagonal
        p -= 0.35 * min(usos[pad], 6)
        if dif not in SEM_CRUZAR:
            p -= 1.5 * len(checks.cruzadas([(float(grade[casa0 + o]), x, y, c, d) for o, x, y, c, d in pad]))
        return p

    def regra(casas_da_batida):
        """Ultimo recurso: sobe-desce reto, uma mao por vez, cada mao no seu lado."""
        for casa in casas_da_batida:
            q, t = tempos[casa], float(grade[casa])
            maos = maos_atual[0]
            ordem = sorted((0, 1), key=lambda c: maos.ult[c][0] if maos.ult[c] else -1)
            postas = 0
            for c in ordem:
                if postas >= q:
                    break
                desce = maos.est[c][0] == "b"
                for d, y in ((1, 0), (6 if c == 0 else 7, 0)) if desce else ((0, 2), (4 if c == 0 else 5, 2), (0, 0)):
                    x = (1 if y == 0 else 0) if c == 0 else (2 if y == 0 else 3)
                    r = tentar([(0, x, y, c, d)], casa)
                    if r:
                        notas_todas.extend(r[0]); maos_atual[0] = maos = r[1]
                        postas += 1
                        break
            stats["descartadas"] += q - postas
        stats["regra"] += 1

    # nota segurada: as duas maos cortam juntas no comeco, o arco liga cada uma a nota do fim, cortada no sentido contrario.
    # O desenho preferido sobe de baixo para cima no meio e termina descendo nas pontas; se o braco estiver do outro lado, o inverso.
    ini_arco = {s // CASAS: (s, e) for s, e in arcos}
    fim_arco, seguradas = {}, []  # batida do fim -> (casa do fim, t do comeco, maos que seguram)
    reservada = set(ini_arco) | {e // CASAS for _, e in arcos}

    def cabeca(c, sobe):
        return (0, 1 + c, 0 if sobe else 2, c, 0 if sobe else 1)

    def comecar_arco(s, e):
        maos = maos_atual[0]
        sobe = {c: maos.est[c][0] == "f" for c in (0, 1)}
        for cores in ((0, 1), (0,), (1,)):
            if r := tentar([cabeca(c, sobe[c]) for c in cores], s):
                notas_todas.extend(r[0]); maos_atual[0] = r[1]
                fim_arco[e // CASAS] = (e, float(grade[s]), {c: sobe[c] for c in cores})
                return True
        return False

    def terminar_arco(e, t0, quem):
        for c, sobe in quem.items():
            ponta, meio = (0, 1) if c == 0 else (3, 2)
            for x, y in ((ponta, 1), (ponta, 0 if sobe else 2), (meio, 0 if sobe else 2), (ponta, 2 if sobe else 0)):
                if r := tentar([(0, x, y, c, 1 if sobe else 0)], e):
                    notas_todas.extend(r[0]); maos_atual[0] = r[1]
                    seguradas.append((t0, float(grade[e]), c))
                    break
            else:
                stats["descartadas"] += 1

    n_bat = (len(grade) - 1) // CASAS
    b = 0
    while b < n_bat:
        if b in fim_arco:
            terminar_arco(*fim_arco.pop(b))
            b += 1
            continue
        if b in ini_arco and comecar_arco(*ini_arco[b]):
            b += 1
            continue
        if not any((b * CASAS + i) in tempos for i in range(CASAS)):
            b += 1
            continue
        k = comp_de.get(b)
        pos = (b - ini_comp[k]) if k is not None else 0
        feito = False
        o = original(b)  # compasso repetido: primeiro o mesmo padrao do original
        if o is None and k is not None and rep[k] != k and any((rep[k], pos, L) in usado for L in (4, 2, 1)):
            stats["rep_tentou"] += 1  # o ritmo saiu diferente do original
        if o is not None and any(x in reservada for x in range(b + 1, b + o[0])):
            o = None
        if o is not None:
            stats["rep_tentou"] += 1
            for v, invertido in variantes(o[3]):
                if r := tentar(v, o[1]):
                    notas_todas.extend(r[0]); maos_atual[0] = r[1]
                    usado[(k, pos, o[0])] = (o[2], o[3])
                    stats["rep_inv" if invertido else "rep_igual"] += 1; stats[f"padrao{o[0]}"] += 1
                    b += o[0]
                    break
            else:
                o = None
            if o is not None:
                continue
        for L in (4, 2, 1):
            if pos % L or pos + L > tam or (b + L) > n_bat or any(x in reservada for x in range(b + 1, b + L)):
                continue
            casa0 = b * CASAS
            masc = "".join(str(tempos.get(casa0 + i, 0)) for i in range(L * CASAS))
            lista = lib[L].get(masc)
            if not lista:
                continue
            amostra = rng.sample(lista, min(TENTATIVAS, len(lista))) if len(lista) > TENTATIVAS else list(lista)
            melhor = None
            for pad, pre, freq in amostra:
                r = tentar(pad, casa0)
                if r:
                    p = pontos(pad, pre, casa0) + min(freq, 8) * 0.15 + rng.random() * 0.5
                    # antecipacao: vale muito deixar os bracos prontos para o desenho repetido que vem a seguir
                    nb = next((x for x in range(b + L, min(b + L + 8, n_bat)) if any((x * CASAS + i) in tempos for i in range(CASAS))), None)
                    prox = original(nb) if nb is not None else None
                    if prox and tentar(prox[3], prox[1], r[1], notas_todas + r[0]):
                        p += 20
                    elif prox and any(tentar(v, prox[1], r[1], notas_todas + r[0]) for v, _ in variantes(prox[3])):
                        p += 10
                    if melhor is None or p > melhor[0]:
                        melhor = (p, pad, r)
            if melhor:
                _, pad, r = melhor
                usos[pad] += 1
                notas_todas.extend(r[0]); maos_atual[0] = r[1]
                usado[(k, pos, L)] = (masc, pad)
                stats[f"padrao{L}"] += 1
                b += L; feito = True
                break
        if not feito:
            regra([b * CASAS + i for i in range(CASAS) if (b * CASAS + i) in tempos])
            b += 1
    tot = stats["padrao4"] + stats["padrao2"] + stats["padrao1"] + stats["regra"]
    resumo = (f" | janelas: {stats['padrao4']} de 4 batidas, {stats['padrao2']} de 2, {stats['padrao1']} de 1, {stats['regra']} por regra simples"
              f" ({stats['descartadas']} notas descartadas) | janelas de compasso repetido: {stats['rep_tentou']}, das quais {stats['rep_igual']} com desenho identico e {stats['rep_inv']} com o mesmo desenho invertido na vertical")
    if alto is not None and notas_todas:
        casa_de = {round(float(t), 4): i for i, t in enumerate(grade)}
        mel = [n[2] >= 1 for n in notas_todas if alto[casa_de[round(n[0], 4)]]]
        rit = [n[2] >= 1 for n in notas_todas if not alto[casa_de[round(n[0], 4)]]]
        resumo += (f" | notas fora da linha de baixo: {np.mean(mel) if mel else 0:.0%} das {len(mel)} em ataques de voz/melodia"
                   f" contra {np.mean(rit) if rit else 0:.0%} das {len(rit)} em ataques de bateria/baixo")
    return sorted(notas_todas), resumo, seguradas
