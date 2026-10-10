"""Checagens de mapeamento em Python, portadas do bsmap (paridade) e do BeatSaber-MapCheck (o resto).

Uma nota aqui e uma tupla (t, x, y, c, d): tempo em SEGUNDOS, coluna 0-3, linha 0-2, cor 0/1, direcao 0-7.
O motor de golpes usa isto como barreira; o relatorio final confere a paridade de novo com o bsmap de verdade.
"""
import math

# angulo do corte no padrao do bsmap: 0 = para baixo, 90 = para a direita
ANG = {0: 180, 1: 0, 2: 270, 3: 90, 4: 225, 5: 135, 6: 315, 7: 45}
# rotacao do pulso exigida por cada direcao, por cor e por lado do golpe (f = ida/forehand, b = volta/backhand)
ROT = {0: {"f": [180, 0, -90, 90, -135, 135, -45, 45], "b": [0, 180, 90, -90, 45, -45, 135, -135]},
       1: {"f": [-180, 0, -90, 90, -135, 135, -45, 45], "b": [0, -180, 90, -90, 45, -45, 135, -135]}}
LIMITE = {0: (-155, 195), 1: (-195, 155)}
ESPELHO = {0: 0, 1: 1, 2: 3, 3: 2, 4: 5, 5: 4, 6: 7, 7: 6}  # a direcao vista no espelho (esquerda <-> direita)
IDA = {0: (1, 3, 6, 7), 1: (1, 2, 6, 7)}  # direcoes que so fazem sentido como golpe de ida
# maior velocidade da mesma mao entre duas notas seguidas (casas da grade por segundo): perto do 1% mais rapido dos mapas humanos.
# Sem este teto saiam trocas de posicao que o braco nao acompanha (dificuldade artificial).
VEL_MAO = {"Easy": 6, "Normal": 6, "Hard": 8, "Expert": 10, "ExpertPlus": 12}
SEM_CRUZAR = ("Easy", "Normal", "Hard")  # nestas o braco nunca cruza
VB = {"Easy": (0.025, 1.2), "Normal": (0.05, 1), "Hard": (0.08, 0.75), "Expert": (0.1, 0.625), "ExpertPlus": (0.1, 0.5)}
# quem GERA confere o bloqueio de visao com esta folga (s): o mapa gravado arredonda os tempos, e um intervalo exatamente no limite
# (0,5 s no Expert+) passava no motor e falhava na conferencia final
FOLGA_VB = 0.01
JANELA_FILA = 0.3  # preferencia "sem_fila": duas notas na mesma casa a menos disto (s) contam como uma escondendo a outra


def paridade_inicial(c, d):
    """Estado da mao ANTES da primeira nota, de modo que ela seja um golpe valido."""
    return "b" if d in IDA[c] else "f"


def paridade(estado, rot, c, d):
    """Um golpe da cor c na direcao d, vindo de (estado, rot). Devolve ('ok'|'aviso'|'erro', estado, rot)."""
    lado = "b" if estado == "f" else "f"
    r = ROT[c][lado][d]
    lo, hi = LIMITE[c]
    if abs(rot - r) > 180 or r < lo + 45 or r > hi - 45:
        return "erro", estado, ROT[c][estado][d]
    st = "aviso" if (r < lo + 90 or r > hi - 90 or abs(rot - r) > 90) else "ok"
    return st, lado, r


def conta_paridade(notas):
    """(erros, avisos) para notas com seta, um golpe por nota. Serve de espelho rapido do bsmap."""
    est, out = {}, {"erro": 0, "aviso": 0, "ok": 0}
    for t, x, y, c, d in sorted(notas):
        if c not in est:
            est[c] = (paridade_inicial(c, d), ROT[c]["b" if paridade_inicial(c, d) == "f" else "f"][d])
            est[c] = (("b" if est[c][0] == "f" else "f"), est[c][1])
            continue
        st, e, r = paridade(*est[c], c, d)
        out[st] += 1
        est[c] = (e, r)
    return out["erro"], out["aviso"]


def aponta(a, b, tol):
    """A nota a aponta para a nota b, com tolerancia de angulo?"""
    pq = math.degrees(math.atan2(b[2] - a[2], b[1] - a[1])) + 90
    dif = abs((ANG[a[4]] - pq) % 360)
    return min(dif, 360 - dif) <= tol


def palma(a, b):
    """Duas notas de cores diferentes no mesmo instante que fazem as maos se baterem (MapCheck: handclap)."""
    if a[3] == b[3] or a[4] > 7 or b[4] > 7:
        return False
    dist = math.hypot(a[1] - b[1], a[2] - b[2])
    m = lambda tol: aponta(a, b, tol) and aponta(b, a, tol)
    n = lambda tol: not aponta(a, b, tol) and not aponta(b, a, tol)
    return ((dist <= 1 and m(45)) or (dist <= 1.5 and m(30)) or (dist <= 2 and m(15))
            or (dist <= 1 and n(134.999)) or (dist <= 1.5 and n(159.999)))


def palmas(notas):
    notas, out, ultimo = sorted(notas), [], -1
    for i, a in enumerate(notas):
        if a[0] < ultimo + 0.01:
            continue
        for b in notas[i + 1:]:
            if b[0] > a[0] + 0.01:
                break
            if palma(a, b):
                out.append(a[0]); ultimo = a[0]
    return out


def empilhadas(notas):
    """Duas notas no mesmo lugar ao mesmo tempo (MapCheck: stackedNote)."""
    notas, out, ultimo = sorted(notas), [], -1
    for i, a in enumerate(notas):
        if a[0] < ultimo + 0.01:
            continue
        for b in notas[i + 1:]:
            if b[0] > a[0] + 0.01:
                break
            if math.hypot(a[1] - b[1], a[2] - b[2]) <= 0.5:
                out.append(a[0]); ultimo = a[0]
    return out


def atravessadas(notas):
    """Dupla em que o sabre de uma mao passa pela nota da outra cor: a outra nota esta colada, na linha do corte
    (antes ou depois). Em mapa humano bem avaliado isso aparece em menos de 0,3 a cada mil notas."""
    notas, out = sorted(notas), []
    for i, a in enumerate(notas):
        for b in notas[i + 1:]:
            if b[0] > a[0] + 0.01:
                break
            if a[3] == b[3] or a[4] > 7 or b[4] > 7:
                continue
            dist = math.hypot(a[1] - b[1], a[2] - b[2])
            # ponta a ponta (um apontando para o outro pelo meio) ja e palma; aqui basta um dos cortes estar na linha
            if 0 < dist <= 1.5 and any(min(abs((ANG[p[4]] - math.degrees(math.atan2(q[2] - p[2], q[1] - p[1])) - 90) % 180),
                                           180 - abs((ANG[p[4]] - math.degrees(math.atan2(q[2] - p[2], q[1] - p[1])) - 90) % 180)) <= 25
                                       for p, q in ((a, b), (b, a))):
                out.append(a[0])
                break
    return out


def cruzadas(notas, janela=0.4):
    """Bracos cruzados: nota vermelha a direita da azul quando a outra mao bateu junto ou ha menos de `janela` segundos."""
    out, ult = [], {}
    for n in sorted(notas):
        o = ult.get(1 - n[3])
        if o and n[0] - o[0] <= janela and (n[1] > o[1] if n[3] == 0 else n[1] < o[1]):
            out.append(n[0])
        ult[n[3]] = n
    return out


def corridas(notas, limite):
    """Troca de posicao da mesma mao mais rapida que `limite` casas da grade por segundo."""
    out, ult = [], {}
    for n in sorted(notas):
        o = ult.get(n[3])
        if o and n[0] - o[0] > 0.02 and math.hypot(n[1] - o[1], n[2] - o[2]) > limite * (n[0] - o[0]) + 1e-6:
            out.append(n[0])
        ult[n[3]] = n
    return out


def meio_salto(njs, bpm, offset=0.0):
    """Meio salto em batidas (bsmap njs.js). Tempo de reacao = 60/bpm * isto."""
    h = 4.0
    while njs * (60 / bpm) * h > 17.999 and h > 1:
        h /= 2
    return max(h + offset, 0.25)


def enfileiradas(notas, janela=JANELA_FILA):
    """Duas notas seguidas na mesma casa, de qualquer cor: a da frente esconde a de tras."""
    notas, out = sorted(notas), []
    for i, a in enumerate(notas):
        for b in notas[i + 1:]:
            if b[0] > a[0] + janela:
                break
            if (a[1], a[2]) == (b[1], b[2]) and b[0] - a[0] > 0.011:
                out.append(b[0])
    return out


def bloqueios_de_visao(notas, dificuldade, hjd_s, folga=0.0):
    """Nota no centro da grade (linha do meio) seguida de nota atras dela, do mesmo lado (MapCheck: visionBlock)."""
    tmin, tmax = VB.get(dificuldade, VB["ExpertPlus"])
    tmin, tmax = tmin - folga, min(hjd_s, tmax) + folga
    out, midl, midr = [], None, None
    for n in sorted(notas):
        t, x, y = n[0], n[1], n[2]
        if midl is not None:
            if tmin <= t - midl <= tmax:
                if x < 2:
                    out.append(t)
            elif t - midl > tmax:
                midl = None
        if midr is not None:
            if tmin <= t - midr <= tmax:
                if x > 1:
                    out.append(t)
            elif t - midr > tmax:
                midr = None
        if y == 1 and x == 1:
            midl = t
        if y == 1 and x == 2:
            midr = t
    return out


def demo():
    # sobe-desce alternado e valido; dois cortes para baixo seguidos e erro
    assert conta_paridade([(0, 1, 0, 0, 1), (1, 1, 2, 0, 0), (2, 1, 0, 0, 1)]) == (0, 0)
    assert conta_paridade([(0, 1, 0, 0, 1), (1, 1, 0, 0, 1)])[0] == 1
    # vermelho apontando pra direita colado no azul apontando pra esquerda: palma
    assert palma((0, 1, 0, 0, 3), (0, 2, 0, 1, 2))
    assert not palma((0, 1, 0, 0, 1), (0, 2, 0, 1, 1))
    assert empilhadas([(0, 1, 0, 0, 1), (0, 1, 0, 1, 1)]) == [0]
    # vermelha subindo para a esquerda em (0,1) vem de (1,0), onde esta a azul: o sabre passa por ela
    assert atravessadas([(0, 0, 1, 0, 4), (0, 1, 0, 1, 6)]) == [0]
    assert not atravessadas([(0, 1, 0, 0, 1), (0, 2, 0, 1, 1)])  # dupla para baixo lado a lado
    assert cruzadas([(0, 2, 0, 0, 1), (0, 1, 0, 1, 1)]) == [0] and not cruzadas([(0, 1, 0, 0, 1), (0, 2, 0, 1, 1)])
    assert corridas([(0, 0, 0, 0, 1), (0.2, 3, 2, 0, 0)], 10) == [0.2] and not corridas([(0, 0, 0, 0, 1), (0.5, 3, 2, 0, 0)], 10)
    assert bloqueios_de_visao([(0, 1, 1, 0, 1), (0.3, 0, 0, 0, 0)], "Expert", 0.5) == [0.3]
    # no limite de 0,5 s do Expert+ o arredondamento decide; com a folga de quem gera, pega dos dois lados
    assert not bloqueios_de_visao([(0, 2, 1, 1, 7), (0.5000001, 3, 1, 0, 3)], "ExpertPlus", 1) and bloqueios_de_visao([(0, 2, 1, 1, 7), (0.5000001, 3, 1, 0, 3)], "ExpertPlus", 1, FOLGA_VB)
    assert enfileiradas([(0, 1, 0, 0, 1), (0.2, 1, 0, 1, 1)]) == [0.2] and not enfileiradas([(0, 1, 0, 0, 1), (0.2, 2, 0, 1, 1), (0.5, 1, 0, 0, 0)])
    assert abs(meio_salto(16, 120) - 2) < 1e-9
    print("checks ok")


if __name__ == "__main__":
    demo()
