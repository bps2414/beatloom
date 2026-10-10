r"""Gera um mapa de Beat Saber (Easy, Normal, Hard, Expert e Expert+) a partir de um arquivo de audio.

  .venv\Scripts\python.exe generate.py <musica.mp3|ogg|wav> [--nome "Titulo"] [--artista "Nome"] [--capa imagem.jpg]
        [--difs Normal,Hard] [--densidade 0.8-1.3] [--album "Album"] [--ano 2024] [--link URL] [--etapa 1-4] [--tag texto]

Nome e artista: o que voce passar, senao as tags do arquivo, senao o nome do arquivo limpo ("Artista - Musica").
Capa: --capa, senao a imagem embutida no arquivo, senao uma capa generica. Sempre cortada em quadrado.

Sai em saida\<nome>-v<etapa>.zip (o site manda ao Quest), saida\<nome>-v<etapa>.relatorio.txt e .relatorio.json (o que o site mostra).
--etapa escolhe a versao do gerador (padrao 4, a mais completa):
  1 = notas no tempo + golpes do BeatKenja      2 = + intensidade por trecho, repeticoes, notas duplas nos sons fortes
  3 = + motor de golpes proprio (padroes humanos) 4 = + separacao de instrumentos (Demucs) e paredes
"""
import argparse, json, re, shutil, subprocess, sys, unicodedata, zipfile
from pathlib import Path

import numpy as np

from beatloom import checks, luzes
from beatloom.audio import CACHE, CASAS, RAIZ, analisar, bateria, clima, ffmpeg, partes, sustentados, voz

# tps = tempos de nota por segundo que a dificuldade mira (as duplas entram por cima disso)
# gap = menor intervalo entre dois tempos (s) | w4 = peso das casas de 1/4 de batida | duplas = fracao de tempos com nota dupla
# njs = velocidade das notas | salto = distancia de salto alvo (m) | piso = minimo de notas por segundo da dificuldade (wiki do BSMG)
# vazio = maior trecho sem nota (em batidas) que se aceita quando ha som marcante dentro | arcos = pode ter nota segurada
# NJS e densidade seguem os mapas humanos bem avaliados (dados/tipico.json): a densidade fica perto do quarto mais leve deles
DIFS = {
    # Easy: 188 mapas humanos tem mediana NJS 11, 1,64 nota/s, 99% dos tempos na batida ou meia batida e 8% de diagonais
    "Easy": dict(piso=0.82, rank=1, tps=1.25, gap=0.4, w4=0.0, duplas=0.04, njs=10, salto=23, vazio=6, arcos=False),
    # Normal: 274 mapas humanos tem mediana NJS 12, 97% dos tempos na batida ou meia batida e 17% de diagonais
    "Normal": dict(piso=1.05, rank=3, tps=1.8, gap=0.25, w4=0.0, duplas=0.05, njs=12, salto=25, vazio=4, arcos=False),
    "Hard": dict(piso=1.73, rank=5, tps=2.45, gap=0.16, w4=0.0, duplas=0.12, njs=14, salto=26, vazio=2, arcos=True),
    "Expert": dict(piso=2.42, rank=7, tps=3.3, gap=0.11, w4=0.55, duplas=0.18, njs=16, salto=24, vazio=2, arcos=True),
    "ExpertPlus": dict(piso=3.21, rank=9, tps=4.1, gap=0.075, w4=0.85, duplas=0.24, njs=18, salto=22, vazio=2, arcos=True),
}
INICIO, FIM = 2.0, 3.0  # folga sem notas no comeco e no fim (s)


# ---------------------------------------------------------------- peca 2: onde vai nota

def escolher_tempos(an, cfg, etapa):
    """-> {casa: 1 ou 2}: as casas da grade que ganham nota (2 = nota dupla)."""
    g, forca, nivel = an["grade"], an["forca"], an["nivel"]
    n = len(g)
    casa_s = float(np.median(np.diff(g)))
    gap = next(k for k in (1, 2, 4, 8) if k * casa_s >= cfg["gap"] or k == 8)
    pos = np.arange(n) % CASAS
    metrico = np.where(pos == 0, 1.0, np.where(pos == 2, 0.8, cfg["w4"]))
    if etapa >= 4 and "forca_inst" in an:  # ataque de qualquer instrumento separado tambem e candidato
        # medido na musica de referencia: os ataques da bateria isolada acertam mais que os da mixagem (92% contra 90%)
        # e cobrem mais; voz, melodia e baixo erram mais, entao entram so como candidatos fracos
        outros = np.max([an[f"nivel_{s}"] for s in ("bass", "other", "vocals")], axis=0) == 2
        nivel = np.where((nivel == 2) | (an["nivel_drums"] == 2), 2, np.where((nivel == 1) | outros, 1, 0))
        forca = np.maximum(forca, an["forca_inst"].max(0))
        # ... menos onde comeca uma silaba cantada (altura da voz, pYIN): essa conta como ataque forte
        sil = np.zeros(n, bool)
        sil[voz(an)["silaba"]] = True
        sil &= nivel < 2
        nivel = np.where(sil, 2, nivel)
    prio = forca * metrico * np.where(nivel == 2, 1.0, 0.45)
    if etapa >= 4 and "forca_inst" in an:
        prio = np.where(sil, prio * 0.7, prio)  # a silaba sem ataque forte fica entre o forte e o fraco: com peso cheio ela tirava nota da bateria
    cand = (nivel > 0) & (g >= INICIO) & (g <= an["dur"] - FIM) & (prio > 0)
    escolhido = np.zeros(n, bool)

    def guloso(casas, quantos):
        for i in sorted(casas, key=lambda i: -prio[i]):
            if quantos <= 0:
                break
            if cand[i] and not escolhido[max(0, i - gap + 1):i + gap].any():
                escolhido[i] = True
                quantos -= 1

    total = cfg["tps"] * (an["dur"] - INICIO - FIM)
    if etapa == 1:  # orcamento unico para a musica toda
        guloso(np.flatnonzero(cand), round(total))
    else:  # orcamento por compasso, proporcional a intensidade; compasso repetido copia o original
        ic = an["ini_comp"] * CASAS
        intens, rep = np.asarray(an["intens"]), an["rep"]
        fator = 0.45 + 1.1 * intens
        if etapa >= 3:  # a parte da musica pesa junto: a queda e o trecho mais cheio, a subida vem acelerando ate ela, a pausa e respiro de verdade
            pt = partes(an)
            fator = fator * np.array([{"queda": 1.1, "pausa": 0.0}.get(q, 1.0) for q in pt])
            for k in range(len(pt)):
                if pt[k] == "subida" and (k == 0 or pt[k - 1] != "subida"):
                    m = next((j for j in range(k, len(pt)) if pt[j] != "subida"), len(pt)) - k
                    fator[k:k + m] *= np.linspace(0.8, 1.2, m) if m > 1 else 1.0
            for k in np.flatnonzero(np.array(pt) == "pausa"):
                cand[ic[k]:ic[k + 1]] = False
        durs = np.array([g[min(b, n - 1)] - g[a] for a, b in zip(ic[:-1], ic[1:])])
        fator = fator * total / max(float(np.sum(fator * durs * cfg["tps"])), 1e-9)
        for k, (a, b) in enumerate(zip(ic[:-1], ic[1:])):
            r = int(rep[k])
            if r != k and ic[r + 1] - ic[r] == b - a and escolhido[ic[r]:ic[r + 1]].any():
                for off in np.flatnonzero(escolhido[ic[r]:ic[r + 1]]):
                    i = a + off
                    if (g[i] >= INICIO) and (g[i] <= an["dur"] - FIM) and not escolhido[max(0, i - gap + 1):i].any():
                        escolhido[i] = True
                # o compasso copiado pode ter ataques que o original nao tinha: completa ate o orcamento dele
                guloso(np.arange(a, min(b, n)), round(cfg["tps"] * durs[k] * fator[k]) - int(escolhido[a:b].sum()))
            else:
                casas = np.arange(a, min(b, n))
                tem = cand[casas].any()
                guloso(casas, max(1 if tem else 0, round(cfg["tps"] * durs[k] * fator[k])))
        # trecho vazio com som marcante dentro (3 ataques fortes ou mais): ganha a nota do ataque mais forte, ate nao sobrar nenhum
        marcante = cand & (nivel == 2) & (forca >= 0.35)
        limite = max(cfg["vazio"] * casa_s * CASAS, 1.0)
        while True:
            cs = np.concatenate([[np.searchsorted(g, INICIO) - gap], np.flatnonzero(escolhido), [np.searchsorted(g, an["dur"] - FIM) + gap]])
            novo = False
            for i, j in zip(cs[:-1], cs[1:]):
                dentro = np.arange(max(i + gap, 0), min(j - gap + 1, n))
                if len(dentro) and g[min(j, n - 1)] - g[max(i, 0)] >= limite and marcante[dentro].sum() >= 3:
                    escolhido[dentro[marcante[dentro]][np.argmax(prio[dentro[marcante[dentro]]])]] = novo = True
            if not novo:
                break
        # manha: quando a musica cresce de um compasso para o outro (entrada de refrao), a batida anterior fica livre (respiro)
        entradas = [int(ic[k]) for k in range(1, len(ic) - 1) if intens[k] >= 0.6 and intens[k] - intens[k - 1] >= 0.25]
        for a in entradas:
            escolhido[max(a - CASAS, 0):a] = False
            escolhido[a] = bool(cand[a]) or bool(escolhido[a])
    casas = np.flatnonzero(escolhido)
    # duplas: os ataques mais fortes em cima da batida, com espaco antes e depois
    sozinho = np.array([not escolhido[max(0, i - 1):i].any() and not escolhido[i + 1:i + 2].any() for i in casas])
    aptas = casas[(casas % CASAS == 0) & sozinho] if cfg["rank"] < 9 else casas[(casas % 2 == 0) & sozinho]
    # musica lenta tem poucos ataques: em vez de inventar nota onde nao ha som, sobe a fracao de duplas ate o piso de NPS
    frac = cfg["duplas"]
    while (len(casas) * (1 + frac)) / an["dur"] < cfg["piso"] * 1.06 and frac < 0.5:
        frac += 0.02
    q = min(len(aptas), int(len(casas) * frac))
    peso = forca + (bateria(an) == 4 if etapa >= 4 and "forca_inst" in an else 0)  # prato de ataque passa na frente: e o acento que pede as duas maos
    corte = np.sort(peso[aptas])[::-1][q - 1] if q > 0 else 9e9
    out = {int(i): 2 if (i in set(aptas.tolist()) and peso[i] >= corte) else 1 for i in casas}
    if etapa >= 2:  # mesmo som, mesmo peso: compasso repetido herda as duplas do original
        ic = an["ini_comp"] * CASAS
        for k, (a, b) in enumerate(zip(ic[:-1], ic[1:])):
            r = int(an["rep"][k])
            if r != k:
                for i in range(a, min(b, n)):
                    j = ic[r] + (i - a)
                    if i in out and j in out:
                        out[i] = out[j]
        for a in entradas:  # ... e a cabeca do trecho forte entra com nota dupla
            if a in out:
                out[a] = 2
    return out


def reservar_arcos(tempos, an, minimo=0):
    """Notas longas da musica viram nota segurada: dupla no comeco, dupla no fim e nada no meio. Mexe em `tempos`. -> [(casa_ini, casa_fim)]

    Das mais longas para as mais curtas, com 2 batidas de folga entre uma e outra, no maximo uma a cada 20 s de musica (cantor de
    nota longa enchia o mapa de arcos) e so enquanto sobrarem `minimo` notas no mapa (a segurada apaga as notas das batidas que
    ocupa; em musica lenta isso derrubava o mapa abaixo do piso da dificuldade)."""
    g, aceitos = an["grade"], []
    for s, e in sorted(sustentados(an), key=lambda v: v[0] - v[1]):
        s, e = s - s % 2, min(e - e % 2, s - s % 2 + 4 * CASAS)  # comeco e fim na batida ou meia batida; no maximo 4 batidas
        if len(aceitos) >= an["dur"] / 20 or e - s < CASAS + 2 or g[s] < INICIO or g[e] > an["dur"] - FIM or any(s < z + 2 * CASAS and a < e + 2 * CASAS for a, z in aceitos):
            continue
        dentro = [i for i in range(s - s % CASAS, e - e % CASAS + CASAS) if i in tempos]
        if sum(tempos.values()) - sum(tempos[i] for i in dentro) + 4 < minimo:
            continue
        for i in dentro:
            del tempos[i]
        tempos[s] = tempos[e] = 2
        aceitos.append((s, e))
    return sorted(aceitos)


# ---------------------------------------------------------------- peca 3 (etapas 1 e 2): golpes do BeatKenja

def golpes_beatkenja(tempos, bpm, grade, nome):
    """Manda os tempos pro BeatKenja (modo linear) e devolve notas (t_s, x, y, cor, dir)."""
    ent, sai = CACHE / f"bk_in_{nome}.dat", CACHE / f"bk_out_{nome}.dat"
    notas = []
    for i, q in sorted(tempos.items()):
        b = round(float(grade[i]) * bpm / 60, 4)
        notas += [{"_time": b, "_lineIndex": 1 + c, "_lineLayer": 0, "_type": c, "_cutDirection": 1} for c in range(q)]
    ent.write_text(json.dumps({"_version": "2.0.0", "_notes": notas, "_obstacles": [], "_events": []}))
    sai.unlink(missing_ok=True)
    r = subprocess.run(["java", "-jar", "BeatKenja.jar", "--input", ent, "--output", sai, "--mode", "linear"],
                       cwd=RAIZ / "beatkenja", capture_output=True, text=True)
    if not sai.exists():
        sys.exit("BeatKenja falhou: " + (r.stdout + r.stderr)[-400:])
    return sorted((n["_time"] * 60 / bpm, n["_lineIndex"], n["_lineLayer"], n["_type"], n["_cutDirection"])
                  for n in json.loads(sai.read_text())["_notes"] if n["_type"] in (0, 1))


def defeitos(notas, dif, reacao):
    return len(checks.bloqueios_de_visao(notas, dif, reacao, checks.FOLGA_VB)) + len(checks.palmas(notas)) + len(checks.empilhadas(notas))


def esforco(notas, dif, prefs=()):
    """O que o conserto nao pode piorar ao mexer numa posicao: troca rapida demais para a mao, sabre atravessando nota, braco cruzado."""
    return (len(checks.corridas(notas, checks.VEL_MAO[dif])) + len(checks.atravessadas(notas))
            + (len(checks.cruzadas(notas)) if checks.teto_cruzadas(dif, prefs) is not None else 0))


def consertar(notas, dif, reacao, prefs=()):
    """Tira bloqueios de visao, palmas e notas empilhadas mexendo so na POSICAO (a paridade nao depende dela)."""
    notas, topo = list(notas), 1 if "sem_topo" in prefs else 2
    for _ in range(3):
        if not defeitos(notas, dif, reacao):
            break
        for k, (t, x, y, c, d) in enumerate(notas):
            ruins = set(checks.bloqueios_de_visao(notas, dif, reacao, checks.FOLGA_VB)) | set(checks.palmas(notas)) | set(checks.empilhadas(notas))
            perto = [t2 for t2 in ruins if -reacao - 0.01 <= t - t2 <= 0.011]
            if not perto:
                continue
            base = defeitos(notas, dif, reacao)
            # tenta as casas da propria mao, das mais naturais para as menos
            lado = (0, 1) if c == 0 else (3, 2)
            for nx, ny in [(lado[1], 0), (lado[0], 0), (lado[0], 1), (lado[0], 2), (lado[1], 2)][:5 if topo == 2 else 3]:
                teste = notas[:k] + [(t, nx, ny, c, d)] + notas[k + 1:]
                if defeitos(teste, dif, reacao) < base and esforco(teste[max(k - 8, 0):k + 9], dif, prefs) <= esforco(notas[max(k - 8, 0):k + 9], dif, prefs):
                    notas = teste
                    break
    return notas


PASSO = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0), 4: (-1, 1), 5: (1, 1), 6: (-1, -1), 7: (1, -1)}  # para onde o corte anda (coluna, linha)
# pilhas a cada mil notas. Nos mapas humanos da biblioteca a mediana e 6 (Hard), 16 (Expert) e 30 (Expert+) e o quarto mais leve 0, 3 e 11;
# torre (tres notas) quase nao existe neles: 0,1 a 0,2 a cada mil notas. Easy e Normal ficam sem.
PILHAS = {"Hard": 3, "Expert": 8, "ExpertPlus": 15}


def empilhar(notas, peso, dif, reacao, prefs=(), presas=()):
    """Pilha em acento: nos ataques mais fortes a nota ganha outra da mesma cor na casa vizinha, na linha do corte, e um golpe so passa pelas duas.

    peso(t) = forca do ataque no instante t; presas = {(t, cor)} das notas que nao podem ganhar par (pontas de nota segurada).
    Do acento mais forte para o mais fraco, ate a cota da dificuldade, com 2 s entre uma pilha e outra. So onde a mao tem 0,25 s livres antes e
    depois e a nota a mais nao cria defeito nem esforco. Dupla ganha pilha nas duas maos ou em nenhuma. No Expert e no Expert+, a primeira
    pilha de corte reto para cima ou para baixo que tiver a coluna livre vira torre: uma por mapa. -> (notas, pilhas, torres)"""
    notas, topo, fila = sorted(notas), 1 if "sem_topo" in prefs else 2, "sem_fila" in prefs
    cota, feitas, torres, onde = round(PILHAS.get(dif, 0) * len(notas) / 1000), 0, 0, []
    ruim = lambda ns: (defeitos(ns, dif, reacao), esforco(ns, dif, prefs), len(checks.enfileiradas(ns)) if fila else 0)
    por_t = {}
    for n in notas:
        por_t.setdefault(n[0], []).append(n)
    for t in sorted(por_t, key=lambda t: -peso(t)):
        grupo = por_t[t]
        if feitas + len(grupo) > cota:
            break
        perto = [m for m in notas if abs(m[0] - t) <= reacao + 1]
        if (any(abs(t - u) < 2 for u in onde) or len({n[3] for n in grupo}) < len(grupo) or any((t, n[3]) in presas for n in grupo)
                or any(m[3] == n[3] and 0 < abs(m[0] - t) < 0.25 for m in perto for n in grupo)):
            continue
        teste, base = perto, ruim(perto)
        cabe = lambda ns: all(a <= b for a, b in zip(ruim(ns), base))
        for n in grupo:
            dx, dy = PASSO[n[4]]
            for x, y in ((n[1] - dx, n[2] - dy), (n[1] + dx, n[2] + dy)):  # primeiro atras da nota (o sabre chega nela antes), depois na frente
                if 0 <= x <= 3 and 0 <= y <= topo and cabe(novo := sorted(teste + [(t, x, y, n[3], n[4])])):
                    teste = novo
                    break
            else:
                teste = None
                break
        if teste is None:
            continue
        if not torres and len(grupo) == 1 and dif in ("Expert", "ExpertPlus") and grupo[0][4] in (0, 1) and topo == 2:
            livre = ({0, 1, 2} - {m[2] for m in teste if m[0] == t and m[3] == grupo[0][3]}).pop()
            if cabe(novo := sorted(teste + [(t, grupo[0][1], livre, grupo[0][3], grupo[0][4])])):
                teste, torres = novo, 1
        notas = sorted([m for m in notas if abs(m[0] - t) > reacao + 1] + teste)
        feitas += len(grupo); onde.append(t)
    return notas, feitas - torres, torres


def repetir_golpes(notas, an, dif, reacao):
    """Etapa 2: compasso repetido recebe o mesmo desenho do original, quando isso nao cria erro. -> (notas, iguais, repetidos)"""
    g, ic = an["grade"], an["ini_comp"] * CASAS
    lim = [float(g[min(i, len(g) - 1)]) - 0.01 for i in ic]
    nota = lambda ns: (checks.conta_paridade(ns), defeitos(ns, dif, reacao))
    iguais = repetidos = 0
    for k in range(len(lim) - 1):
        r = int(an["rep"][k])
        if r == k:
            continue
        orig = [n for n in notas if lim[r] <= n[0] < lim[r + 1]]
        aqui = [n for n in notas if lim[k] <= n[0] < lim[k + 1]]
        if not orig or not aqui:
            continue
        repetidos += 1
        desl = lim[k] - lim[r]
        copia = [(round(t + desl, 4), x, y, c, d) for t, x, y, c, d in orig]
        if sorted(round(n[0], 2) for n in copia) != sorted(round(n[0], 2) for n in aqui):
            continue
        teste = sorted([n for n in notas if not lim[k] <= n[0] < lim[k + 1]] + copia)
        (e0, a0), d0 = nota(notas)
        (e1, a1), d1 = nota(teste)
        if e1 <= e0 and a1 <= a0 and d1 <= d0:
            notas, iguais = teste, iguais + 1
    return notas, iguais, repetidos


# ---------------------------------------------------------------- luzes e paredes

def relogio(an, bpm, tol=0.010):
    """-> (eventos de BPM do mapa, funcao segundos -> batida do mapa).

    Com BPM fixo nao ha evento e a batida e t * bpm / 60. Senao o mapa ganha um evento de BPM a cada trecho em que o andamento
    muda: o trecho vai de um inicio de compasso a outro e cresce enquanto os compassos do meio ficarem a ate `tol` segundos da
    reta. Sem isso o jogo e os editores desenham a grade de um BPM so, que em musica tocada por banda foge varios segundos.
    """
    if an["bpm_fixo"]:
        return [], lambda t: t * bpm / 60
    bat, ic = np.asarray(an["batidas"], float), [int(i) for i in an["ini_comp"]]
    f0 = bat[0] / (bat[1] - bat[0])  # a batida 0 do mapa e o segundo 0; a primeira batida detectada cai nesta fracao
    pts = [(i + f0, float(bat[i])) for i in sorted({*ic, len(bat) - 1}) if bat[i] > 0.001]
    B, T, ev, k = [0.0], [0.0], [], 0
    while k < len(pts):
        j = k  # o trecho mais longo a partir de (B, T) que ainda passa perto de todos os compassos do meio
        while j + 1 < len(pts) and all(abs(T[-1] + (b - B[-1]) * (pts[j + 1][1] - T[-1]) / (pts[j + 1][0] - B[-1]) - t) <= tol for b, t in pts[k:j + 1]):
            j += 1
        m = round(60 * (pts[j][0] - B[-1]) / (pts[j][1] - T[-1]), 3)
        ev.append({"b": round(B[-1], 4), "m": m})
        T.append(T[-1] + (pts[j][0] - B[-1]) * 60 / m)  # o tempo que o jogo vai calcular com o BPM arredondado, para o erro nao acumular
        B.append(pts[j][0])
        k = j + 1
    B.append(B[-1] + 1000 * ev[-1]["m"] / 60); T.append(T[-1] + 1000)  # depois do ultimo compasso segue o ultimo BPM
    return ev, lambda t: float(np.interp(t, T, B))


def paredes(notas, an, bt, arcos=()):
    """Paredes laterais decorativas nas pausas de 1,6 s ou mais. Ficam na coluna da ponta e nao pedem movimento."""
    ts = sorted({n[0] for n in notas})
    segurando = {round(a[0], 4) for a in arcos}  # durante uma nota segurada a mao esta ocupada: sem parede
    out, lado = [], 0
    for a, b in zip(ts[:-1], ts[1:]):
        if b - a >= 1.6 and round(a, 4) not in segurando:
            ini, fim = a + 0.4, b - 0.6
            for x in (0, 3) if b - a >= 4.0 else ((0, 3)[lado],):
                out.append({"b": round(bt(ini), 3), "x": x, "y": 0, "d": round(bt(fim) - bt(ini), 3), "w": 1, "h": 5})
            lado ^= 1
    return out


# ---------------------------------------------------------------- peca 4: empacotar

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "musica"


def limpar_titulo(t):
    """'Artista - Musica (feat. Fulano) [Official Video]' ou o nome do arquivo com _ -> (musica, artista ou None)."""
    t = re.sub(r"[_\s]+", " ", t).strip()
    lixo = r"official|oficial|video|v[ií]deo|audio|[aá]udio|lyrics?|letra|legendado|visuali[sz]er|clipe|hd|hq|4k|mv|remaster(ed)?"
    t = re.sub(rf"\s*[\(\[][^\)\]]*\b({lixo})\b[^\)\]]*[\)\]]", "", t, flags=re.I)
    t = re.sub(rf"(\s+({lixo}))+$", "", t, flags=re.I)  # sem parenteses (nome de arquivo do yt-dlp)
    t = re.sub(r"\s*[\(\[]?\s*\b(feat|ft|featuring)\b\.?\s.*$", "", t, flags=re.I)  # convidados nao fazem parte do nome
    partes = re.split(r"\s+[-–—|]\s+", t.strip(), maxsplit=1)
    limpo = lambda s: s.strip(" \"'“”‘’-–—|")
    return (limpo(partes[1]), limpo(partes[0])) if len(partes) == 2 and limpo(partes[1]) else (limpo(t), None)


def tags(audio):
    """Tags do arquivo (titulo, artista, album, ano), so as que existirem."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(audio)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        j = json.loads(r.stdout)
        t = {k.lower(): v for s in j.get("streams", []) for k, v in s.get("tags", {}).items()}  # ogg guarda as tags na faixa
        t.update({k.lower(): v for k, v in j["format"].get("tags", {}).items()})
    except Exception:
        t = {}
    ano = re.search(r"\d{4}", t.get("date") or t.get("year") or "")
    d = {"nome": t.get("title"), "artista": t.get("artist") or t.get("album_artist"), "album": t.get("album"), "ano": ano and ano[0], "link": t.get("purl")}
    return {k: v.strip() for k, v in d.items() if v and v.strip()}


def dados_da_musica(audio):
    """O que da para saber da musica sem perguntar: tags do arquivo e, na falta, o nome do arquivo limpo."""
    d = tags(audio)
    # o yt-dlp grava o titulo inteiro do video na tag ("Artista - Musica (Official Video)"): limpa do mesmo jeito que o nome do arquivo
    m, a = limpar_titulo(d.get("nome") or Path(audio).stem)
    # ... e ai o "artista" da tag e o canal que subiu o video (da para saber pela tag do link): vale o que vem antes do traco
    if a and not d.get("link") and d.get("artista", a).lower() != a.lower():
        m, a = f"{a} - {m}", None  # arquivo de musica de verdade: a tag de artista manda e o traco faz parte do nome
    d["nome"] = m
    if a:
        d["artista"] = a
    return d


def fazer_capa(origem, destino):
    """Primeira imagem de `origem` (foto ou capa embutida no audio), cortada no centro em quadrado. -> deu certo?"""
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(origem), "-an", "-frames:v", "1",
                        "-vf", "crop='min(iw,ih)':'min(iw,ih)',scale=512:512", str(destino)], capture_output=True)
    return r.returncode == 0 and Path(destino).exists()


def salto_offset(njs, bpm, alvo):
    """Offset que deixa a distancia de salto perto do alvo (m)."""
    h = checks.meio_salto(njs, bpm)
    return round(max(alvo / (2 * njs * 60 / bpm), 0.25) - h, 2)


def gerar(audio, nome=None, artista=None, etapa=4, tag="", saida=None, capa=None, difs=None, densidade=1.0, album=None, ano=None, link=None, prefs=(), ambiente=None):
    audio = Path(audio)
    if not audio.exists():
        sys.exit(f"Arquivo nao encontrado: {audio}")
    if capa and not Path(capa).exists():
        sys.exit(f"Capa nao encontrada: {capa}")
    difs = [d for d in DIFS if d in difs] if difs else list(DIFS)
    if not difs:
        sys.exit("Nenhuma dificuldade valida. Use: " + ", ".join(DIFS))
    d = dados_da_musica(audio)
    nome, artista = nome or d["nome"], artista or d.get("artista") or "Desconhecido"
    extra_info = {k: v for k, v in (("album", album or d.get("album")), ("ano", ano or d.get("ano")), ("link", link or d.get("link"))) if v}
    saida = Path(saida or RAIZ / "saida")
    base = f"{slug(nome)}-v{etapa}{('-' + slug(tag)) if tag else ''}"
    pasta = saida / base
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True)

    # o jogo toca o song.egg; a analise roda nele, para o mapa e o audio nunca sairem de sincronia
    egg = pasta / "song.egg"
    # bitexact: a mesma musica da sempre o mesmo song.egg, entao a analise (a parte demorada) sai do cache na segunda vez
    if audio.suffix.lower() == ".egg":  # ja e o audio de um mapa (regerar uma dificuldade): copia igual, para a analise sair do cache
        shutil.copyfile(audio, egg)
    else:
        ffmpeg("-i", audio, "-vn", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", "-c:a", "libvorbis", "-q:a", "6", "-ar", "44100", "-f", "ogg", egg)
    arq_capa = pasta / "cover.png"
    origem_capa = "escolhida" if capa and fazer_capa(capa, arq_capa) else "do arquivo de audio" if fazer_capa(audio, arq_capa) else "generica"
    if origem_capa == "generica":
        ffmpeg("-f", "lavfi", "-i", "gradients=s=512x512:c0=0x1e3a8a:c1=0xdb2777:x0=0:y0=0:x1=512:y1=512", "-frames:v", "1", arq_capa)

    print(f"[1/4] ouvindo a musica{' e separando instrumentos (demora alguns minutos)' if etapa >= 4 else ''}...", flush=True)
    an = analisar(egg, instrumentos=etapa >= 4)
    bpm = float(an["bpm"])
    bpm = int(bpm) if bpm == int(bpm) else bpm
    print(f"      {an['dur']:.0f} s | BPM {bpm} ({'fixo' if an['bpm_fixo'] else 'variavel'}) | compasso de {an['batidas_por_compasso']} batidas", flush=True)
    if an["dur"] < 20:
        sys.exit("Musica curta demais (menos de 20 s).")

    bpm_ev, bt_ = relogio(an, bpm)
    casa_de = {round(float(t), 4): i for i, t in enumerate(an["grade"])}
    it_casa = np.asarray(an["intens"])[np.clip(np.searchsorted(an["ini_comp"] * CASAS, np.arange(len(an["grade"])), "right") - 1, 0, len(an["intens"]) - 1)]  # intensidade do compasso de cada casa
    bt = lambda t: round(bt_(t), 4)
    ev, boost = luzes.basicos(luzes.deixas(an), bt), luzes.reforco(an, bt)
    ambiente = ambiente or luzes.AMBIENTE[clima(an)]  # o cenario segue o clima da musica, a nao ser que venha escolhido (refazer uma dificuldade so)
    # cores da capa: as luzes sempre; sabres e notas so se a pessoa pediu e os dois tons forem bem diferentes. O SongCore le isto do _customData de cada dificuldade
    pal = luzes.cores(arq_capa) if origem_capa != "generica" else None
    rgb = lambda c: dict(zip("rgb", c))
    cores_mapa = {}
    if pal:
        cores_mapa = {"_envColorLeft": rgb(pal[0][0]), "_envColorRight": rgb(pal[0][1]), "_envColorLeftBoost": rgb(pal[1][0]), "_envColorRightBoost": rgb(pal[1][1])}
        if "sabres_capa" in prefs and luzes.contraste(*pal[0]):
            cores_mapa.update(_colorLeft=rgb(pal[0][0]), _colorRight=rgb(pal[0][1]))
    hexa = [["#%02x%02x%02x" % tuple(round(x * 255) for x in c) for c in par] for par in pal or ()]
    mapas, resumo = [], [f"capa {origem_capa} | densidade x{densidade:g} | cores " + (" ".join(hexa[0]) + ", na queda " + " ".join(hexa[1]) + (" (sabres tambem)" if "_colorLeft" in cores_mapa else "") if pal else "do jogo") + f" | cenario {ambiente.removesuffix('Environment')} (musica de clima {clima(an)})"]
    ger = {"etapa": etapa, "capa": origem_capa.split()[-1], "densidade": densidade, "prefs": sorted(prefs), "cores": hexa, "sabres": "_colorLeft" in cores_mapa, "clima": clima(an), "ambiente": ambiente, "difs": {}}  # o mesmo resumo em numeros, para o .relatorio.json
    for dif in difs:
        cfg = dict(DIFS[dif], tps=DIFS[dif]["tps"] * densidade)
        print(f"[2/4] {dif}: escolhendo os tempos e os golpes...", flush=True)
        off = salto_offset(cfg["njs"], bpm, cfg["salto"])
        reacao = 60 / bpm * checks.meio_salto(cfg["njs"], bpm, off)
        tempos = escolher_tempos(an, cfg, etapa)
        extra, arcos = "", []
        if etapa <= 2:
            notas = consertar(golpes_beatkenja(tempos, bpm, an["grade"], dif), dif, reacao)
            if etapa == 2:
                notas, ig, rp = repetir_golpes(notas, an, dif, reacao)
                extra = f" | compassos repetidos com desenho identico: {ig}/{rp}"
        else:
            from beatloom import engine
            pedidos = reservar_arcos(tempos, an, cfg["piso"] * 1.06 * an["dur"]) if etapa >= 4 and cfg["arcos"] else []
            notas, extra, seg, ger["difs"][dif] = engine.golpes(tempos, an, dif, reacao, etapa, cfg["njs"], pedidos, prefs)
            notas = consertar(notas, dif, reacao, prefs)  # rede de seguranca: sobra rara do motor (so muda posicao)
            if etapa >= 4:  # vocabulario: pilha (e uma torre) nos acentos; o prato de ataque passa na frente, como nas duplas
                fz = np.maximum(an["forca"], an["forca_inst"].max(0)) + (bateria(an) == 4) if "forca_inst" in an else an["forca"]
                fz = fz * it_casa  # acento de trecho calmo vale menos: e nele que a mao esta livre, e as pilhas iam todas parar la
                notas, np_, nt = empilhar(notas, lambda t: fz[casa_de[round(t, 4)]], dif, reacao, prefs, {(t, c) for a, z, c in seg for t in (a, z)})
                ger["difs"][dif].update(pilhas=np_, torres=nt)
                extra += f" | pilhas em acento: {np_}" + (f" e {nt} torre" if nt else "")
            # arco = (nota da cabeca, nota da cauda); procura as duas depois do conserto, que pode ter mudado a posicao
            achar = lambda t, c: next(n for n in notas if abs(n[0] - t) < 0.001 and n[3] == c)
            arcos = [(achar(t0, c), achar(t1, c)) for t0, t1, c in seg]
            extra += f" | notas seguradas: {len(arcos)}" + (" (em " + ", ".join(sorted({f'{a[0]:.1f}s' for a, _ in arcos}, key=lambda s: float(s[:-1]))) + ")" if arcos else "")
        par = paredes(notas, an, bt, [a for a, _ in arcos]) if etapa >= 4 else []
        arq = f"{dif}Standard.dat"
        (pasta / arq).write_text(json.dumps({
            "version": "3.2.0", "bpmEvents": bpm_ev, "rotationEvents": [],
            "colorNotes": [{"b": bt(t), "x": x, "y": y, "c": c, "d": d, "a": 0} for t, x, y, c, d in sorted(notas)],
            "bombNotes": [], "obstacles": par,
            # arco (nota segurada): sai da nota da cabeca e chega na nota da cauda, as duas da mesma cor
            "sliders": [{"c": a[3], "b": bt(a[0]), "x": a[1], "y": a[2], "d": a[4], "mu": 1, "tb": bt(z[0]), "tx": z[1], "ty": z[2], "tc": z[4], "tmu": 1, "m": 0}
                        for a, z in arcos],
            "burstSliders": [], "waypoints": [], "basicBeatmapEvents": ev, "colorBoostBeatmapEvents": boost,
            "lightColorEventBoxGroups": [], "lightRotationEventBoxGroups": [], "lightTranslationEventBoxGroups": [],
            "basicEventTypesWithKeywords": {"d": []}, "useNormalEventsAsCompatibleEvents": False}))
        mapas.append({"_difficulty": dif, "_difficultyRank": cfg["rank"], "_beatmapFilename": arq,
                      "_noteJumpMovementSpeed": cfg["njs"], "_noteJumpStartBeatOffset": off, **({"_customData": cores_mapa} if cores_mapa else {})})
        resumo.append(f"{dif}: {len(notas)} notas{extra}")

    # previa: comeca no trecho de 4 compassos mais intenso
    ic, it = an["ini_comp"], np.asarray(an["intens"])
    k = int(np.argmax([it[i:i + 4].mean() for i in range(max(1, len(it) - 4))]))
    info = {
        "_version": "2.0.0", "_songName": nome, "_songSubName": f"auto v{etapa}{(' ' + tag) if tag else ''}", "_songAuthorName": artista,
        "_levelAuthorName": "automapper", "_beatsPerMinute": bpm, "_songTimeOffset": 0, "_shuffle": 0, "_shufflePeriod": 0.5,
        "_previewStartTime": round(float(an["batidas"][ic[k]]), 2), "_previewDuration": 10,
        "_songFilename": "song.egg", "_coverImageFilename": "cover.png",
        "_environmentName": ambiente, "_allDirectionsEnvironmentName": "GlassDesertEnvironment",
        "_difficultyBeatmapSets": [{"_beatmapCharacteristicName": "Standard", "_difficultyBeatmaps": mapas}]}
    if extra_info:  # o Info.dat nao tem campo proprio para album, ano e link: vao no _customData, que o jogo ignora e o site le
        info["_customData"] = {"_beatloom": extra_info}
    (pasta / "Info.dat").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[3/4] empacotando...", flush=True)
    zp = saida / f"{base}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pasta.iterdir()):
            z.write(f, f.name)
    shutil.rmtree(pasta)
    print("[4/4] conferindo...", flush=True)
    return zp, resumo, ger


def demo():
    assert limpar_titulo("Falling_In_Reverse_-_Joseph_feat._Corey_Taylor_and_Serj_Tankian") == ("Joseph", "Falling In Reverse")
    assert limpar_titulo("beabadoobee_-_Take_A_Bite_Official_Video") == ("Take A Bite", "beabadoobee")
    assert limpar_titulo('Falling In Reverse - "Joseph" (feat. Corey Taylor) [Official Music Video]') == ("Joseph", "Falling In Reverse")
    assert limpar_titulo("Sk8er_Boi") == ("Sk8er Boi", None)
    assert limpar_titulo("Artista – Musica (Lyric Video)") == ("Musica", "Artista")
    # andamento que muda no meio: 8 batidas a 120 e depois 8 a 100, compasso de 4. A ida (nosso relogio) e a volta (a conta do jogo) batem
    bat = np.concatenate([0.25 + 0.5 * np.arange(9), 4.25 + 0.6 * np.arange(1, 9)])
    ev, bt = relogio({"bpm_fixo": False, "batidas": bat, "ini_comp": np.arange(0, 17, 4)}, 120)
    assert [e["m"] for e in ev] == [120, 100] and ev[1]["b"] == 8.5, ev
    volta = lambda b: sum((min(b, z["b"]) - a["b"]) * 60 / a["m"] for a, z in zip(ev, ev[1:] + [{"b": 9e9}]) if b > a["b"])
    assert all(abs(volta(bt(t)) - t) < 0.001 for t in (0.25, 3.0, 4.25, 6.65, 9.05)), [volta(bt(t)) for t in (0.25, 4.25, 9.05)]
    assert relogio({"bpm_fixo": True}, 120)[1](2.0) == 4 and relogio({"bpm_fixo": True}, 120)[0] == []
    # 200 notas, uma por segundo, vermelha desce embaixo e sobe em cima; a do segundo 50 e a mais forte, depois a do 100. Expert: cota de 2 pilhas, a primeira vira torre
    ns = [(float(t), 1, 0 if t % 2 == 0 else 2, 0, 1 if t % 2 == 0 else 0) for t in range(200)]
    com, p, tr = empilhar(ns, lambda t: {50: 9, 100: 8}.get(t, 0), "Expert", 0.5)
    assert (p, tr) == (1, 1) and [n[1:] for n in com if n[0] == 50] == [(1, 0, 0, 1), (1, 1, 0, 1), (1, 2, 0, 1)] and [n[1:] for n in com if n[0] == 100] == [(1, 0, 0, 1), (1, 1, 0, 1)], (p, tr)
    assert empilhar(ns, lambda t: t, "Normal", 0.5) == (ns, 0, 0) and sum(n[0] == 50 for n in empilhar(ns, lambda t: -abs(t - 50), "Expert", 0.5, presas={(50.0, 0)})[0]) == 1
    print("gerar ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--demo"]:
        sys.exit(demo())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--nome"); ap.add_argument("--artista"); ap.add_argument("--tag", default="")
    ap.add_argument("--capa", help="imagem para a capa (jpg, png...); e cortada em quadrado")
    ap.add_argument("--difs", help="dificuldades separadas por virgula, ex.: Normal,Hard (padrao: todas)")
    ap.add_argument("--densidade", type=float, default=1.0, help="multiplica a quantidade de notas (0.8 = mais leve, 1.3 = mais cheio)")
    ap.add_argument("--album"); ap.add_argument("--ano"); ap.add_argument("--link", help="de onde a musica veio")
    ap.add_argument("--etapa", type=int, default=4, choices=(1, 2, 3, 4))
    ap.add_argument("--prefs", default="", help="gostos de quem joga, separados por virgula: sem_topo (nada na linha de cima), sem_fila (nada logo atras de outra nota na mesma casa), cruzar_nunca ou cruzar_livre (bracos cruzados; sem nenhum dos dois, pouco), sabres_capa (sabres e notas com as cores da capa)")
    ap.add_argument("--ambiente", help="cenario do jogo (ex.: BigMirrorEnvironment); sem isto, o do clima da musica")
    ap.add_argument("--saida"); ap.add_argument("--humano", help="pasta de um mapa humano da mesma musica, para comparar os tempos")
    a = ap.parse_args()
    zp, resumo, ger = gerar(a.audio, a.nome, a.artista, a.etapa, a.tag, a.saida, a.capa, a.difs and a.difs.split(","), min(max(a.densidade, 0.5), 1.6),
                       a.album, a.ano, a.link, {p for p in a.prefs.split(",") if p in ("sem_topo", "sem_fila", "cruzar_nunca", "cruzar_livre", "sabres_capa")}, a.ambiente)
    import report
    R = report.conferir(zp, a.humano)
    for D in R["difs"]:
        D["gerador"] = ger["difs"].get(D["nome"])
    R["gerador"] = {k: v for k, v in ger.items() if k != "difs"}
    report.gravar_json(zp, R)
    txt, ok = report.texto(R), R["passou"]
    txt += "\n\nGERADOR (etapa %d)\n  " % a.etapa + "\n  ".join(resumo)
    zp.with_suffix(".relatorio.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nMapa: {zp}\nRelatorio: {zp.with_suffix('.relatorio.txt')}")
    sys.exit(0 if ok else 1)
