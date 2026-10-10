r"""Gera um mapa de Beat Saber (Easy, Normal, Hard, Expert e Expert+) a partir de um arquivo de audio.

  .venv\Scripts\python.exe generate.py <musica.mp3|ogg|wav> [--nome "Titulo"] [--artista "Nome"] [--capa imagem.jpg]
        [--difs Normal,Hard] [--densidade 0.8-1.3] [--album "Album"] [--ano 2024] [--link URL] [--etapa 1-4] [--tag texto]

Nome e artista: o que voce passar, senao as tags do arquivo, senao o nome do arquivo limpo ("Artista - Musica").
Capa: --capa, senao a imagem embutida no arquivo, senao uma capa generica. Sempre cortada em quadrado.

Sai em saida\<nome>-v<etapa>.zip (o site manda ao Quest) e saida\<nome>-v<etapa>.relatorio.txt.
--etapa escolhe a versao do gerador (padrao 4, a mais completa):
  1 = notas no tempo + golpes do BeatKenja      2 = + intensidade por trecho, repeticoes, notas duplas nos sons fortes
  3 = + motor de golpes proprio (padroes humanos) 4 = + separacao de instrumentos (Demucs) e paredes
"""
import argparse, json, re, shutil, subprocess, sys, unicodedata, zipfile
from pathlib import Path

import numpy as np

from beatloom import checks
from beatloom.audio import CACHE, CASAS, RAIZ, analisar, ffmpeg, sustentados

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
    prio = forca * metrico * np.where(nivel == 2, 1.0, 0.45)
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
    corte = np.sort(forca[aptas])[::-1][q - 1] if q > 0 else 9e9
    out = {int(i): 2 if (i in set(aptas.tolist()) and forca[i] >= corte) else 1 for i in casas}
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


def reservar_arcos(tempos, an):
    """Notas longas da musica viram nota segurada: dupla no comeco, dupla no fim e nada no meio. Mexe em `tempos`. -> [(casa_ini, casa_fim)]"""
    g, aceitos, livre = an["grade"], [], 0
    for s, e in sustentados(an):
        s, e = s - s % 2, min(e - e % 2, s - s % 2 + 4 * CASAS)  # comeco e fim na batida ou meia batida; no maximo 4 batidas
        if e - s < CASAS + 2 or s < livre or g[s] < INICIO or g[e] > an["dur"] - FIM:
            continue
        for i in range(s - s % CASAS, e - e % CASAS + CASAS):
            tempos.pop(i, None)
        tempos[s] = tempos[e] = 2
        aceitos.append((s, e))
        livre = e + 2 * CASAS
    return aceitos


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
    return len(checks.bloqueios_de_visao(notas, dif, reacao)) + len(checks.palmas(notas)) + len(checks.empilhadas(notas))


def esforco(notas, dif):
    """O que o conserto nao pode piorar ao mexer numa posicao: troca rapida demais para a mao, sabre atravessando nota, braco cruzado."""
    return (len(checks.corridas(notas, checks.VEL_MAO[dif])) + len(checks.atravessadas(notas))
            + (len(checks.cruzadas(notas)) if dif in checks.SEM_CRUZAR else 0))


def consertar(notas, dif, reacao):
    """Tira bloqueios de visao, palmas e notas empilhadas mexendo so na POSICAO (a paridade nao depende dela)."""
    notas = list(notas)
    for _ in range(3):
        if not defeitos(notas, dif, reacao):
            break
        for k, (t, x, y, c, d) in enumerate(notas):
            ruins = set(checks.bloqueios_de_visao(notas, dif, reacao)) | set(checks.palmas(notas)) | set(checks.empilhadas(notas))
            perto = [t2 for t2 in ruins if -reacao - 0.01 <= t - t2 <= 0.011]
            if not perto:
                continue
            base = defeitos(notas, dif, reacao)
            # tenta as casas da propria mao, das mais naturais para as menos
            lado = (0, 1) if c == 0 else (3, 2)
            for nx, ny in [(lado[1], 0), (lado[0], 0), (lado[0], 1), (lado[0], 2), (lado[1], 2)]:
                teste = notas[:k] + [(t, nx, ny, c, d)] + notas[k + 1:]
                if defeitos(teste, dif, reacao) < base and esforco(teste[max(k - 8, 0):k + 9], dif) <= esforco(notas[max(k - 8, 0):k + 9], dif):
                    notas = teste
                    break
    return notas


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

def luzes(an, bpm):
    """Luzes simples: nunca fica escuro, pisca na batida e muda de cor conforme a intensidade do compasso."""
    bat, ic, intens = an["batidas"], an["ini_comp"], an["intens"]
    ev = [(0.0, t, 1) for t in (0, 1, 4)]  # liga azul no comeco
    for k, (a, b) in enumerate(zip(ic[:-1], ic[1:])):
        forte = intens[k] >= 0.6
        cor = 4 if (forte and k % 2 == 0) else 0  # +4 = vermelho
        t0 = float(bat[a])
        ev += [(t0, 8, 0), (t0, 4, (2 if forte else 3) + cor), (t0, 0, 3 + cor)]
        ev += [(t0, 12, 1 + round(intens[k] * 5)), (t0, 13, 1 + round(intens[k] * 5))]
        ev += [(t0, 2, (1 if forte else 0) + (cor if forte else 0)), (t0, 3, (1 if forte else 0) + (cor if forte else 0))]
        for j in range(a, b):
            if intens[k] >= 0.25:
                ev.append((float(bat[j]), 1, 3 + (4 if (j - a) % 2 else 0)))
            if forte and (j - a) % 2 == 1:
                ev.append((float(bat[j]), 9, 0))
    return [{"b": round(t * bpm / 60, 3), "et": ty, "i": v, "f": 1} for t, ty, v in sorted(ev) if t >= 0]


def paredes(notas, an, bpm, arcos=()):
    """Paredes laterais decorativas nas pausas de 1,6 s ou mais. Ficam na coluna da ponta e nao pedem movimento."""
    ts = sorted({n[0] for n in notas})
    segurando = {round(a[0], 4) for a in arcos}  # durante uma nota segurada a mao esta ocupada: sem parede
    out, lado = [], 0
    for a, b in zip(ts[:-1], ts[1:]):
        if b - a >= 1.6 and round(a, 4) not in segurando:
            ini, fim = a + 0.4, b - 0.6
            for x in (0, 3) if b - a >= 4.0 else ((0, 3)[lado],):
                out.append({"b": round(ini * bpm / 60, 3), "x": x, "y": 0, "d": round((fim - ini) * bpm / 60, 3), "w": 1, "h": 5})
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


def gerar(audio, nome=None, artista=None, etapa=4, tag="", saida=None, capa=None, difs=None, densidade=1.0, album=None, ano=None, link=None):
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

    ev = luzes(an, bpm)
    mapas, resumo = [], [f"capa {origem_capa} | densidade x{densidade:g}"]
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
            pedidos = reservar_arcos(tempos, an) if etapa >= 4 and cfg["arcos"] else []
            notas, extra, seg = engine.golpes(tempos, an, dif, reacao, etapa, cfg["njs"], pedidos)
            notas = consertar(notas, dif, reacao)  # rede de seguranca: sobra rara do motor (so muda posicao)
            # arco = (nota da cabeca, nota da cauda); procura as duas depois do conserto, que pode ter mudado a posicao
            achar = lambda t, c: next(n for n in notas if abs(n[0] - t) < 0.001 and n[3] == c)
            arcos = [(achar(t0, c), achar(t1, c)) for t0, t1, c in seg]
            extra += f" | notas seguradas: {len(arcos)}" + (" (em " + ", ".join(sorted({f'{a[0]:.1f}s' for a, _ in arcos}, key=lambda s: float(s[:-1]))) + ")" if arcos else "")
        par = paredes(notas, an, bpm, [a for a, _ in arcos]) if etapa >= 4 else []
        arq = f"{dif}Standard.dat"
        bt = lambda t: round(t * bpm / 60, 4)
        (pasta / arq).write_text(json.dumps({
            "version": "3.2.0", "bpmEvents": [], "rotationEvents": [],
            "colorNotes": [{"b": bt(t), "x": x, "y": y, "c": c, "d": d, "a": 0} for t, x, y, c, d in sorted(notas)],
            "bombNotes": [], "obstacles": par,
            # arco (nota segurada): sai da nota da cabeca e chega na nota da cauda, as duas da mesma cor
            "sliders": [{"c": a[3], "b": bt(a[0]), "x": a[1], "y": a[2], "d": a[4], "mu": 1, "tb": bt(z[0]), "tx": z[1], "ty": z[2], "tc": z[4], "tmu": 1, "m": 0}
                        for a, z in arcos],
            "burstSliders": [], "waypoints": [], "basicBeatmapEvents": ev, "colorBoostBeatmapEvents": [],
            "lightColorEventBoxGroups": [], "lightRotationEventBoxGroups": [], "lightTranslationEventBoxGroups": [],
            "basicEventTypesWithKeywords": {"d": []}, "useNormalEventsAsCompatibleEvents": False}))
        mapas.append({"_difficulty": dif, "_difficultyRank": cfg["rank"], "_beatmapFilename": arq,
                      "_noteJumpMovementSpeed": cfg["njs"], "_noteJumpStartBeatOffset": off})
        resumo.append(f"{dif}: {len(notas)} notas{extra}")

    # previa: comeca no trecho de 4 compassos mais intenso
    ic, it = an["ini_comp"], np.asarray(an["intens"])
    k = int(np.argmax([it[i:i + 4].mean() for i in range(max(1, len(it) - 4))]))
    info = {
        "_version": "2.0.0", "_songName": nome, "_songSubName": f"auto v{etapa}{(' ' + tag) if tag else ''}", "_songAuthorName": artista,
        "_levelAuthorName": "automapper", "_beatsPerMinute": bpm, "_songTimeOffset": 0, "_shuffle": 0, "_shufflePeriod": 0.5,
        "_previewStartTime": round(float(an["batidas"][ic[k]]), 2), "_previewDuration": 10,
        "_songFilename": "song.egg", "_coverImageFilename": "cover.png",
        "_environmentName": "DefaultEnvironment", "_allDirectionsEnvironmentName": "GlassDesertEnvironment",
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
    return zp, resumo


def demo():
    assert limpar_titulo("Falling_In_Reverse_-_Joseph_feat._Corey_Taylor_and_Serj_Tankian") == ("Joseph", "Falling In Reverse")
    assert limpar_titulo("beabadoobee_-_Take_A_Bite_Official_Video") == ("Take A Bite", "beabadoobee")
    assert limpar_titulo('Falling In Reverse - "Joseph" (feat. Corey Taylor) [Official Music Video]') == ("Joseph", "Falling In Reverse")
    assert limpar_titulo("Sk8er_Boi") == ("Sk8er Boi", None)
    assert limpar_titulo("Artista – Musica (Lyric Video)") == ("Musica", "Artista")
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
    ap.add_argument("--saida"); ap.add_argument("--humano", help="pasta de um mapa humano da mesma musica, para comparar os tempos")
    a = ap.parse_args()
    zp, resumo = gerar(a.audio, a.nome, a.artista, a.etapa, a.tag, a.saida, a.capa, a.difs and a.difs.split(","), min(max(a.densidade, 0.5), 1.6),
                       a.album, a.ano, a.link)
    from report import relatorio
    txt, ok = relatorio(zp, a.humano)
    txt += "\n\nGERADOR (etapa %d)\n  " % a.etapa + "\n  ".join(resumo)
    zp.with_suffix(".relatorio.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nMapa: {zp}\nRelatorio: {zp.with_suffix('.relatorio.txt')}")
    sys.exit(0 if ok else 1)
