r"""Interface web do Beatloom. Roda so neste PC.

  start.bat                               -> instala o que faltar e abre o site (duplo clique)
  .venv\Scripts\python.exe app.py        -> abre http://localhost:8777 no navegador

Cole um link (YouTube etc., via yt-dlp) ou escolha um arquivo, gere o mapa, assista no ArcViewer (visualizador 3D embutido) e mande ao Quest.
Na primeira vez a pagina confere o que falta (ffmpeg, Node, padroes...) e baixa para dentro da pasta do projeto: beatloom\preparo.py.
"""
import importlib.metadata, json, mimetypes, os, re, shutil, subprocess, sys, tempfile, threading, time, webbrowser, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from beatloom import discord, mods, preparo, quest
from generate import DIFS, dados_da_musica, fazer_capa, limpar_titulo

mimetypes.add_type('application/wasm', '.wasm')

RAIZ = Path(__file__).parent
SAIDA, MUSICAS = RAIZ / "saida", RAIZ / "musicas"
PORTA = int(os.environ.get("BEATLOOM_PORTA", 8777))  # so os testes mudam
PY = sys.executable
ARC = RAIZ / "arcviewer"
CONFIG = RAIZ / "beatloom.json"  # escolhas de quem usa; nao vai para o repositorio
ENVIADOS = SAIDA / "quest.json"  # {zip: data do arquivo quando foi mandado}: mapa refeito depois disso precisa ir de novo
DESCARTAVEL = ("analise", "regerar", "quest", "tmp_egg", "baixar")  # pastas de .cache que podem sumir (os modelos ficam)

trabalhos, fila = [], []  # um trabalho por vez: a analise usa o processador inteiro
conferindo, lidos = {}, {}  # zip -> data do arquivo quando a conferencia comecou; zip -> (datas, linha da lista)
SITE = RAIZ / "site"
TIPOS = {".css": "text/css", ".js": "text/javascript", ".json": "application/json", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}
trava = threading.Lock()
pausada = [False]  # fila pausada: a musica que esta rodando termina e a proxima espera
FILA = RAIZ / ".cache" / "fila.json"
LISTAS = SAIDA / "playlists.json"  # {id: {nome, videos: [codigo de cada faixa, na ordem], extras: [zips postos a mao]}}: as playlists que a pessoa quis ver no jogo


def dados_do_link(j):
    """Nome, artista, album, ano e capa a partir do que o yt-dlp sabe do link. Prefere a faixa/artista de verdade ao titulo do video."""
    m, a = limpar_titulo(j.get("title") or "")
    canal = re.sub(r"\s*-\s*Topic$", "", j.get("channel") or j.get("uploader") or "")
    artista = (j.get("artist") or j.get("creator") or "").split(",")[0].strip()
    ano = j.get("release_year") or (j.get("release_date") or j.get("upload_date") or "")[:4]
    d = {"nome": j.get("track") or m, "artista": artista or a or canal, "album": j.get("album"), "ano": str(ano or ""),
         "link": j.get("webpage_url"), "capa": j.get("thumbnail"), "dur": j.get("duration")}
    return {k: v for k, v in d.items() if v}


def config():
    padrao = {"lingua": None, "quest_ip": "", "difs": list(DIFS), "densidade": 1.0, "modo": "completo", "sem_topo": False, "sem_fila": False, "cruzar": "pouco", "sabres_capa": False, "chroma": False, "noodle": False, "pronto": False,
              "discord_url": "", "discord_eventos": list(discord.EVENTOS), "discord_minimo": 3}
    try:
        return {**padrao, **json.loads(CONFIG.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return padrao


def gravar_config(d):
    """Guarda so o que veio em `d` e e valido; o resto fica como estava."""
    c = config()
    if d.get("lingua") in ("pt", "en"):
        c["lingua"] = d["lingua"]
    if "quest_ip" in d and re.fullmatch(r"(\d{1,3}(\.\d{1,3}){3})?", str(d["quest_ip"]).strip()):
        c["quest_ip"] = str(d["quest_ip"]).strip()
    if isinstance(d.get("difs"), list) and any(x in DIFS for x in d["difs"]):
        c["difs"] = [x for x in DIFS if x in d["difs"]]
    if isinstance(d.get("densidade"), (int, float)):
        c["densidade"] = min(max(float(d["densidade"]), 0.8), 1.3)
    if d.get("modo") in ("completo", "rapido"):
        c["modo"] = d["modo"]
    if d.get("cruzar") in ("nunca", "pouco", "livre"):
        c["cruzar"] = d["cruzar"]
    if "discord_url" in d and (not d["discord_url"] or discord.URL.fullmatch(str(d["discord_url"]).strip())):  # vazio desliga; o resto e barrado antes, em POST /api/config
        c["discord_url"] = str(d["discord_url"]).strip()
    if isinstance(d.get("discord_eventos"), list):
        c["discord_eventos"] = [x for x in discord.EVENTOS if x in d["discord_eventos"]]
    for k in ("pronto", "sem_topo", "sem_fila", "sabres_capa", "chroma", "noodle"):
        if isinstance(d.get(k), bool):
            c[k] = d[k]
    CONFIG.write_text(json.dumps(c, indent=1), encoding="utf-8")
    return c


def config_publica():
    """O que a pagina pode ver: o endereco do webhook e um segredo, so o fim dele sai daqui."""
    c = config()
    return {**c, "discord_url": discord.mascara(c["discord_url"])}


def prefs(sabres=None):
    """Os gostos de quem joga, do jeito que o generate.py recebe em --prefs. `sabres` = o que a pessoa marcou no dialogo de mapa novo; sem isso vale a Configuracao."""
    c = config()
    c["sabres_capa"] = c.get("sabres_capa") if sabres is None else sabres
    return ",".join([k for k in ("sem_topo", "sem_fila", "sabres_capa", "chroma", "noodle") if c.get(k)] + [f"cruzar_{c['cruzar']}"] * (c.get("cruzar") in ("nunca", "livre")))  # "pouco" e o padrao do gerador


def guardar_fila():
    """A fila sobrevive a fechar o Beatloom: o que nao acabou volta na proxima vez (a musica que estava rodando recomeca)."""
    FILA.parent.mkdir(exist_ok=True)
    FILA.write_text(json.dumps([t for t in trabalhos if t["estado"] in ("na fila", "rodando")]), encoding="utf-8")


def ler_fila():
    try:
        pend = [t for t in json.loads(FILA.read_text(encoding="utf-8")) if isinstance(t, dict) and "id" in t]
    except (OSError, ValueError):
        return
    for t in pend:
        t.update(estado="na fila", passos=[], progresso=None)
    trabalhos.extend(pend); fila.extend(pend)


def capa_generica(png):
    """A capa e a generica do gerador (degrade de azul a rosa)? Mapa antigo nao anota de onde a capa veio, entao so olhando para ela:
    encolhida para 2 x 2 pontos, os quatro caem na reta entre as duas cores do degrade (o de agora e o das versoes antigas, que era outro desenho)."""
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(png), "-vf", "scale=2:2", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    a, b = (0x1e, 0x3a, 0x8a), (0xdb, 0x27, 0x77)
    def longe(p):  # distancia do ponto ao segmento a-b, no cubo de cores
        f = min(max(sum((p[i] - a[i]) * (b[i] - a[i]) for i in range(3)) / sum((b[i] - a[i]) ** 2 for i in range(3)), 0), 1)
        return sum((p[i] - a[i] - f * (b[i] - a[i])) ** 2 for i in range(3)) ** 0.5
    return len(r.stdout) == 12 and all(longe(r.stdout[k:k + 3]) <= 24 for k in (0, 3, 6, 9))


def egg_do_mapa(zp, onde):
    """Poe o audio e a capa do mapa em .cache\\regerar\\<onde>. Devolve (pasta, etapa em que o mapa foi feito, dificuldades que ele tem, argumento --capa do gerador, cenario do mapa, Info.dat)."""
    tmp = RAIZ / ".cache" / "regerar" / onde
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    with zipfile.ZipFile(zp) as z:
        info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
        (tmp / "song.egg").write_bytes(z.read(info["_songFilename"]))
        (tmp / "cover.png").write_bytes(z.read(info["_coverImageFilename"]))
    # a capa da musica volta ao gerador (e a mesma, e dela saem as cores do mapa); a generica nao, para o mapa nao ganhar as cores do degrade
    origem = ((ler_relatorio(zp) or {}).get("gerador") or {}).get("capa")
    capa = [] if origem == "generica" or origem is None and capa_generica(tmp / "cover.png") else ["--capa", str(tmp / "cover.png")]
    etapa = (re.search(r"auto v([1-4])", info.get("_songSubName", "")) or ["", "4"])[1]  # o mapa refeito sai no mesmo modo (completo ou rapido)
    difs = [b["_difficulty"] for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == "Standard" for b in s["_difficultyBeatmaps"]]
    return tmp, etapa, [x for x in DIFS if x in difs], capa, info.get("_environmentName") or "DefaultEnvironment", info


def guardar_versao(zp):
    """Antes de um mapa ser refeito, o zip e os relatorios de agora vao para saida\\versoes, com a data e a hora no nome. Nada e apagado de la."""
    (SAIDA / "versoes").mkdir(exist_ok=True)
    quando = time.strftime("%Y-%m-%d %H%M%S")
    for f in (zp, zp.with_suffix(".relatorio.txt"), zp.with_suffix(".relatorio.json")):
        if f.exists():
            f.replace(SAIDA / "versoes" / f"{zp.stem} {quando}{f.name[len(zp.stem):]}")


def enviados():
    try:
        return json.loads(ENVIADOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def situacao(z, la, env):
    """Um zip diante do Quest: "novo" (nao esta la), "velho" (esta, mas o zip mudou depois do envio: vai por cima) ou "igual" (mesma versao: pula)."""
    return "novo" if z.stem not in la else "igual" if env.get(z.name) == z.stat().st_mtime else "velho"


def estado_quest():
    """-> tem adb?, ip, conectado? e, por zip, "ok" (a versao de agora esta no Quest) ou "velho" (o mapa mudou depois do envio)."""
    ip = config()["quest_ip"]
    on = quest.conectado(ip)
    la, env = quest.no_quest(ip) if on else set(), enviados()
    return {"adb": preparo.tem("adb"), "ip": ip, "conectado": on,
            "mapas": {z.name: "ok" if situacao(z, la, env) == "igual" else "velho" for z in SAIDA.glob("*.zip") if z.stem in la}}


envio = {"itens": [], "ativo": False, "playlists": 0, "lote": 0}  # a fila de envio ao Quest, um item por mapa ("espera", "enviando", "ok", "igual", "erro"); a pagina a le em /api/estado


def enviador():
    """Esvazia envio["itens"] um mapa por vez (o adb nao ganha nada em paralelo), depois manda as playlists; quem chegar no meio entra na mesma fila."""
    while True:
        ip, env = config()["quest_ip"], enviados()
        while True:
            with trava:
                it = next((i for i in envio["itens"] if i["estado"] == "espera"), None)
                if it:
                    it["estado"] = "enviando"
            if not it:
                break
            z = SAIDA / it["zip"]
            try:
                it["sit"] = situacao(z, quest.no_quest(ip), env)
                if it["sit"] == "igual" and not it["forcar"]:
                    it["estado"] = "igual"; continue  # mesma versao ja esta no Quest: nao e mandada
                it["erro"] = quest.enviar(ip, z, lambda f: it.update(pct=int(f * 100))) or ""
                if not it["erro"]:
                    env[z.name] = z.stat().st_mtime
                    ENVIADOS.write_text(json.dumps(env), encoding="utf-8")
                else:
                    it["erro"] = "adb|" + it["erro"]
            except Exception as e:  # um mapa que quebra nao derruba a fila
                it["erro"] = "adb|" + str(e)[-300:]
            it["pct"], it["estado"] = 100, "erro" if it["erro"] else "ok"
        try:
            ls = listas()  # as playlists vao junto, cada uma com os mapas dela que estao no Quest (o codigo do mapa muda quando ele e refeito)
            la, mapas = quest.no_quest(ip) if ls else set(), lista_de_mapas() if ls else []
            for k, p in ls.items():
                zs = [SAIDA / z for z in mapas_da_lista(p, mapas) if z[:-4] in la]
                envio["playlists"] += bool(zs) and not quest.enviar_lista(ip, arquivo_da_lista(k), quest.bplist(p["nome"], zs))
        except Exception:
            pass  # playlist nao e o mapa: a pagina so deixa de contar
        with trava:
            if not any(i["estado"] == "espera" for i in envio["itens"]):
                envio["ativo"] = False
                return


def capa_do_zip(zp):
    z = zipfile.ZipFile(zp)
    return z.read(json.loads(z.read("Info.dat").decode("utf-8-sig"))["_coverImageFilename"])


def ytdlp(*args):
    r = subprocess.run([PY, "-m", "yt_dlp", "--no-playlist", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError("ytdlp|" + (r.stderr.strip().splitlines() or [""])[-1][:300])
    return r.stdout


def rodar(trab):
    def passo(txt):
        trab["passos"].append(txt)
        aviso_andamento(trab)

    try:
        audio, d, refaz = trab.get("arquivo"), {}, trab.get("regerar")
        if refaz:  # refaz o mapa inteiro (notas, luzes, cenario, cores, eventos de BPM) com o gerador e os gostos de agora, como se fosse novo:
            # so ficam o audio, a capa, o nome, o artista, o album, o ano, o link, o modo, a densidade e as dificuldades. O audio sai do zip, entao a
            # analise sai do cache se ainda servir (beatloom.audio.VERSAO); senao a musica e ouvida de novo
            zp = SAIDA / refaz
            ger = (ler_relatorio(zp) or {}).get("gerador") or {}
            tmp, etapa, difs, capa, _, info = egg_do_mapa(zp, "fila")
            trab["difs"] = difs
            dados = {"nome": info["_songName"], "artista": info["_songAuthorName"], "tag": (re.search(r"auto v[1-4] (.+)", info.get("_songSubName", "")) or ["", ""])[1],
                     **info.get("_customData", {}).get("_beatloom", {})}
            cmd = [PY, "-u", str(RAIZ / "generate.py"), str(tmp / "song.egg"), "--etapa", etapa, "--densidade", str(ger.get("densidade") or 1), "--difs", ",".join(difs),
                   "--saida", str(tmp), "--prefs", prefs(), *capa, *[f"--{k}={dados[k]}" for k in ("nome", "artista", "tag", "album", "ano", "link") if dados.get(k)]]
        else:
            if trab.get("link"):
                passo("baixando")
                MUSICAS.mkdir(exist_ok=True)
                # a miniatura do video vem junto para virar a capa; o --print devolve, depois do download, o caminho do arquivo e os dados da faixa
                j = json.loads(ytdlp("-x", "--audio-format", "mp3", "--audio-quality", "0", "--restrict-filenames", "--write-thumbnail",
                                     "--convert-thumbnails", "jpg", "-o", str(MUSICAS / "%(title)s.%(ext)s"), "--print",
                                     "after_move:%(.{filepath,title,track,artist,creator,album,release_year,release_date,upload_date,webpage_url,thumbnail,channel,uploader,duration})j",
                                     "--", trab["link"]).splitlines()[-1])
                audio = str(Path(j["filepath"]))
                d = dados_do_link(j)
                capa = Path(audio).with_suffix(".jpg")
                d["capa"] = str(capa) if capa.exists() else None
            d = {**d, **{k: trab[k] for k in ("nome", "artista", "album", "ano") if trab.get(k)}}  # o que a pessoa escreveu vale mais
            trab["titulo"] = d.get("nome") or Path(audio).stem
            cmd = [PY, "-u", str(RAIZ / "generate.py"), audio, "--etapa", str(trab.get("etapa") or 4), "--densidade", str(trab.get("densidade") or 1)]
            cmd += ["--difs", ",".join(trab["difs"])] if trab.get("difs") else []
            cmd += ["--prefs", prefs(trab.get("sabres_capa"))]
            for k in ("nome", "artista", "album", "ano", "link", "capa"):
                cmd += [f"--{k}", str(d[k])] if d.get(k) else []
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
        rotulos = {"[1/4]": "ouvindo", "[2/4]": "golpes", "[3/4]": "empacotando", "[4/4]": "conferindo"}
        cauda = []
        for linha in p.stdout:
            if linha.startswith("[sep] "):  # andamento da separacao de instrumentos, em %; fora dela a barra nao tem numero
                trab["progresso"] = int(linha[6:]) if linha[6:].strip().isdigit() else None
                continue
            cauda = (cauda + [linha.rstrip()])[-6:]
            for k, v in rotulos.items():
                if linha.startswith(k):
                    if k == "[2/4]":  # "golpes|Hard (2/4)": qual dificuldade esta sendo feita
                        v += f"|{linha.split()[1].rstrip(':')} ({1 + sum(x.startswith('golpes') for x in trab['passos'])}/{len(trab.get('difs') or DIFS)})"
                    if not trab["passos"] or trab["passos"][-1] != v:
                        passo(v)
            if linha.startswith("Mapa: "):
                trab["zip"] = Path(linha[6:].strip()).name
        p.wait()
        if refaz:
            novo = tmp / (trab.pop("zip", None) or "-")
            if not novo.is_file():
                raise RuntimeError("gerador|" + " ".join(cauda)[-300:])
            guardar_versao(zp)
            for f in (novo, novo.with_suffix(".relatorio.txt"), novo.with_suffix(".relatorio.json")):  # o mapa novo entra com o nome de arquivo do antigo
                if f.exists():
                    dest = zp.with_name(zp.stem + f.name[len(novo.stem):])
                    dest.write_bytes(f.read_bytes().replace(novo.name.encode(), zp.name.encode()) if f.suffix != ".zip" else f.read_bytes())  # os relatorios dizem o nome do zip
            trab["zip"] = zp.name
        elif not trab.get("zip"):
            raise RuntimeError("gerador|" + " ".join(cauda)[-300:])
        trab["estado"] = "pronto"
    except Exception as e:
        trab["estado"], trab["erro"] = "erro", str(e)


lote = {"t0": None, "tj": 0, "feitos": [], "ult": 0}  # a fila de agora, para os avisos do Discord: abre quando o operario sai da folga e fecha quando a fila esvazia


def avisar(ev, d, capa=None):
    c = config()
    if c["discord_url"] and ev in c["discord_eventos"]:
        discord.avisar(c["discord_url"], ev, d, c["lingua"] or "pt", capa)


def aviso_andamento(trab, forca=False):
    """A mensagem unica da fila: na troca de musica e, no maximo a cada 20 s, na troca de etapa. So quando a fila tem `discord_minimo` mapas ou mais."""
    try:
        with trava:
            total = len(lote["feitos"]) + 1 + len(fila)
        if total < config()["discord_minimo"] or (not forca and time.time() - lote["ult"] < 20):
            return
        lote["ult"] = time.time()
        avisar("andamento", {"feitos": list(lote["feitos"]), "total": total, "seg": time.time() - lote["t0"],
                             "atual": {"titulo": trab.get("titulo"), "capa": trab.get("capa") or "", "passo": (trab["passos"] or [None])[-1], "progresso": trab.get("progresso")}})
    except Exception as x:  # aviso nunca derruba a geracao
        print("[discord]", type(x).__name__)


def aviso_comecou(trab):
    if lote["t0"] is None:
        lote.update(t0=time.time(), feitos=[])
    lote["tj"] = time.time()
    aviso_andamento(trab, True)


def aviso_acabou(trab):
    try:
        ok = trab["estado"] == "pronto"
        m = next((m for m in lista_de_mapas() if m["zip"] == trab.get("zip")), None) if ok else None
        lote["feitos"].append({"titulo": m["nome"] if m else trab.get("titulo"), "artista": m["artista"] if m else None, "ok": ok})
        if m:
            try:
                capa = capa_do_zip(SAIDA / m["zip"])
            except (KeyError, OSError, zipfile.BadZipFile):
                capa = None
            avisar("pronto", {"nome": m["nome"], "artista": m["artista"], "bpm": m["bpm"], "dur": m["dur"], "ok": m["ok"], "difs": m["difs"], "tempo": time.time() - lote["tj"]}, capa)
        elif not ok:
            avisar("erro", {"titulo": trab.get("titulo"), "erro": trab.get("erro"), "capa": trab.get("capa") or ""})
        with trava:
            vazia = not fila
        if vazia:  # a fila acabou: o resumo so vale a pena se foram varias
            if len(lote["feitos"]) >= config()["discord_minimo"]:
                avisar("fim", {"feitos": lote["feitos"], "seg": time.time() - lote["t0"]})
            lote.update(t0=None, feitos=[])
    except Exception as x:
        print("[discord]", type(x).__name__)


def operario():
    while True:
        with trava:
            trab = fila.pop(0) if fila and not pausada[0] else None
            if trab:
                trab["estado"] = "rodando"  # dentro da trava: quem dispensa da fila nao pega um trabalho que ja saiu dela
        if trab is None:
            time.sleep(0.5)
            continue
        aviso_comecou(trab)
        rodar(trab)
        with trava:
            guardar_fila()
        aviso_acabou(trab)


def ler_relatorio(zp):
    try:
        return json.loads(zp.with_suffix(".relatorio.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lista_de_mapas():
    """Roda a cada poucos segundos: so reabre o zip e o relatorio de quem mudou."""
    out = []
    for zp in sorted(SAIDA.glob("*.zip"), key=lambda p: -p.stat().st_mtime):
        rel = zp.with_suffix(".relatorio.json")
        datas = (zp.stat().st_mtime, rel.stat().st_mtime if rel.exists() else 0)
        if lidos.get(zp.name, (0,))[0] != datas:
            try:
                info = json.loads(zipfile.ZipFile(zp).read("Info.dat").decode("utf-8-sig"))
            except Exception:
                continue
            r = ler_relatorio(zp) or {}
            lidos[zp.name] = (datas, {"zip": zp.name, "nome": info["_songName"], "sub": info.get("_songSubName", ""), "artista": info["_songAuthorName"],
                                      "bpm": info["_beatsPerMinute"], "ok": r.get("passou"), "link": info.get("_customData", {}).get("_beatloom", {}).get("link"), "dur": r.get("dur"), "v": int(datas[0]),
                                      "difs": [b["_difficulty"] for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == "Standard" for b in s["_difficultyBeatmaps"]]})
        out.append(lidos[zp.name][1])
    return out


def video(link):
    """O que identifica a musica de um link: o codigo do video (o mesmo video chega como music.youtube, www.youtube ou youtu.be), senao o link inteiro."""
    m = re.search(r"(?:[?&]v=|youtu\.be/)([\w-]{11})", link or "")
    return m[1] if m else (link or "").strip()


def arquivo_da_lista(k):
    return "beatloom-" + re.sub(r"[^\w-]", "_", k) + ".bplist"


def listas():
    try:
        return json.loads(LISTAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def mapas_da_lista(p, mapas):
    """Os zips que existem para as faixas de uma playlist, na ordem dela (de cada faixa, o mapa mais novo), e depois os que a pessoa pos a mao."""
    por = {}
    for m in mapas:
        if m.get("link"):
            por.setdefault(video(m["link"]), m["zip"])
    tem = {m["zip"] for m in mapas}
    return list(dict.fromkeys([por[v] for v in p["videos"] if v in por] + [z for z in p.get("extras", []) if z in tem]))


def mexer_na_lista(p, zips, mapas, tirar=False):
    """Poe mapas numa playlist ou tira dela. Tirar um mapa que veio do YouTube tira a faixa dele, senao ele voltaria sozinho."""
    if tirar:
        fora = {video(m["link"]) for m in mapas if m["zip"] in zips and m.get("link")}
        p["videos"], p["extras"] = [v for v in p["videos"] if v not in fora], [z for z in p.get("extras", []) if z not in zips]
    else:
        ja = mapas_da_lista(p, mapas)
        p["extras"] = p.get("extras", []) + [m["zip"] for m in reversed(mapas) if m["zip"] in zips and m["zip"] not in ja]  # reversed: na ordem em que foram feitos


def demo():
    global SAIDA, ENVIADOS, config
    a, b, c = "https://youtu.be/aaaaaaaaaaa", "https://www.youtube.com/watch?v=bbbbbbbbbbb", None
    mapas = [{"zip": "c.zip", "link": c}, {"zip": "b2.zip", "link": b}, {"zip": "b.zip", "link": b}, {"zip": "a.zip", "link": a}]  # do mais novo ao mais velho, como lista_de_mapas
    p = {"nome": "P", "videos": ["bbbbbbbbbbb", "xxxxxxxxxxx", "aaaaaaaaaaa"]}
    assert mapas_da_lista(p, mapas) == ["b2.zip", "a.zip"]  # a ordem e a da playlist; faixa sem mapa fica de fora; vale o mapa mais novo
    mexer_na_lista(p, ["c.zip", "a.zip", "sumiu.zip"], mapas)
    assert p["extras"] == ["c.zip"] and mapas_da_lista(p, mapas) == ["b2.zip", "a.zip", "c.zip"]
    mexer_na_lista(p, ["a.zip", "c.zip"], mapas, tirar=True)
    assert mapas_da_lista(p, mapas) == ["b2.zip"] and len(p["videos"]) == 2
    with tempfile.TemporaryDirectory() as tmp:  # situacao: novo, igual ao enviado, ou refeito depois do envio
        z = Path(tmp) / "m.zip"; z.write_bytes(b"x"); mt = z.stat().st_mtime
        assert situacao(z, set(), {}) == "novo" and situacao(z, {"m"}, {"m.zip": mt}) == "igual"
        assert situacao(z, {"m"}, {"m.zip": mt - 5}) == "velho" and situacao(z, {"m"}, {}) == "velho"
    with tempfile.TemporaryDirectory() as tmp:  # o enviador com um Quest de mentira: o igual pula, o novo sobe com andamento, o que falha nao derruba a fila
        SAIDA, ENVIADOS, config = Path(tmp), Path(tmp) / "quest.json", lambda: {"quest_ip": "1.2.3.4"}
        for n in "abc":
            (SAIDA / f"{n}.zip").write_bytes(b"x")
        ENVIADOS.write_text(json.dumps({"a.zip": (SAIDA / "a.zip").stat().st_mtime}), encoding="utf-8")
        def sobe(ip, z, andamento):
            andamento(0.5); assert envio["itens"][1]["pct"] == 50 or z.name != "b.zip"
            return "quebrou" if z.name == "c.zip" else None
        quest.no_quest, quest.enviar = lambda ip: {"a"}, sobe
        envio.update(itens=[{"zip": f"{n}.zip", "estado": "espera", "pct": 0, "sit": "", "erro": "", "forcar": False} for n in "abc"], ativo=True)
        enviador()
        assert [(i["estado"], i["erro"]) for i in envio["itens"]] == [("igual", ""), ("ok", ""), ("erro", "adb|quebrou")] and not envio["ativo"]
        assert "b.zip" in enviados() and "c.zip" not in enviados()
    print("demo ok")


def conferir(zp):
    """Mapa de antes do .relatorio.json: confere em segundo plano, uma vez por versao do zip. -> esta conferindo agora?"""
    def faz():
        subprocess.run([PY, str(RAIZ / "report.py"), str(zp), "--so-json"], capture_output=True, cwd=RAIZ)
        conferindo[zp.name] = (data, False)
    data = zp.stat().st_mtime
    with trava:
        if conferindo.get(zp.name, (0,))[0] != data:
            conferindo[zp.name] = (data, True)
            threading.Thread(target=faz, daemon=True).start()
    return conferindo[zp.name][1]


def renomear(zp, nome, artista):
    """Troca nome e artista dentro do Info.dat do zip (o arquivo zip continua com o mesmo nome)."""
    novo = zp.with_suffix(".tmp")
    with zipfile.ZipFile(zp) as z, zipfile.ZipFile(novo, "w", zipfile.ZIP_DEFLATED) as out:
        for n in z.namelist():
            dado = z.read(n)
            if n == "Info.dat":
                info = json.loads(dado.decode("utf-8-sig"))
                info["_songName"], info["_songAuthorName"] = nome or info["_songName"], artista or info["_songAuthorName"]
                dado = json.dumps(info, ensure_ascii=False, indent=2).encode()
            out.writestr(n, dado)
    novo.replace(zp)


def trocar_dificuldade(zp, novo, dif):
    """Poe no zip `zp` a dificuldade `dif` que esta no zip `novo`, sem mexer nas outras."""
    with zipfile.ZipFile(novo) as z:
        ninfo = json.loads(z.read("Info.dat").decode("utf-8-sig"))
        entrada = next(b for b in ninfo["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"] if b["_difficulty"] == dif)
        notas = z.read(entrada["_beatmapFilename"])
    tmp = zp.with_suffix(".tmp")
    with zipfile.ZipFile(zp) as z, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
        mapas = next(s for s in info["_difficultyBeatmapSets"] if s["_beatmapCharacteristicName"] == "Standard")
        fora = {b["_beatmapFilename"] for b in mapas["_difficultyBeatmaps"] if b["_difficulty"] == dif} | {"Info.dat", entrada["_beatmapFilename"]}
        mapas["_difficultyBeatmaps"] = sorted([b for b in mapas["_difficultyBeatmaps"] if b["_difficulty"] != dif] + [entrada], key=lambda b: b["_difficultyRank"])
        out.writestr("Info.dat", json.dumps(info, ensure_ascii=False, indent=2))
        out.writestr(entrada["_beatmapFilename"], notas)
        for n in z.namelist():
            if n not in fora:
                out.writestr(n, z.read(n))
    tmp.replace(zp)


def mapa(nome_zip):
    zp = SAIDA / Path(nome_zip).name
    z = zipfile.ZipFile(zp)
    info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
    bpm, difs = info["_beatsPerMinute"], []
    for s in info["_difficultyBeatmapSets"]:
        if s["_beatmapCharacteristicName"] != "Standard":
            continue
        for b in s["_difficultyBeatmaps"]:
            d = json.loads(z.read(b["_beatmapFilename"]).decode("utf-8-sig"))
            difs.append({"nome": b["_difficulty"], "njs": b["_noteJumpMovementSpeed"],  # mapa antigo (v2) ou novo (v3)
                         "notas": len(d.get("colorNotes", d.get("_notes", []))), "arcos": len(d.get("sliders", []))})
    rel = ler_relatorio(zp)
    return {"zip": zp.name, "nome": info["_songName"], "sub": info.get("_songSubName", ""), "artista": info["_songAuthorName"], "bpm": bpm, "v": int(zp.stat().st_mtime),
            "difs": difs, "mods": mods.do_mapa(info), "relatorio": rel, "conferindo": not rel and conferir(zp), **info.get("_customData", {}).get("_beatloom", {})}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def manda(self, corpo, tipo="application/json", cod=200, extra=(), guarda=False):
        if not isinstance(corpo, bytes):
            corpo = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(cod)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "max-age=31536000, immutable" if guarda else "no-store")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(corpo)

    def local(self):
        """So atende o proprio PC: barra outro site tentando falar com este servidor pelo navegador."""
        ok = self.headers.get("Host", "") in (f"localhost:{PORTA}", f"127.0.0.1:{PORTA}")
        if self.command == "POST":
            ok = ok and self.headers.get("X-Automapper") == "1"
        if not ok:
            self.manda({"erro": "recusado"}, cod=403)
        return ok

    def do_GET(self):
        if not self.local():
            return
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                self.manda((SITE / "app.html").read_bytes(), "text/html; charset=utf-8")
            elif u.path.startswith("/site/"):  # css, js, frases e fontes da pagina
                arq = (SITE / unquote(u.path[6:])).resolve()
                if SITE not in arq.parents or arq.suffix not in TIPOS or not arq.is_file():
                    return self.manda({"erro": "nao_existe"}, cod=404)
                self.manda(arq.read_bytes(), TIPOS[arq.suffix] + ("; charset=utf-8" if arq.suffix in (".css", ".js", ".json") else ""), guarda=arq.suffix == ".woff2")
            elif u.path == "/api/estado":
                vivos = [t for t in trabalhos if t["estado"] in ("na fila", "rodando")]  # a fila inteira (uma playlist enche) e os ultimos que acabaram
                mapas = lista_de_mapas()
                self.manda({"trabalhos": vivos + [t for t in trabalhos if t not in vivos][-6:], "mapas": mapas, "playlists": [{"id": k, "nome": p["nome"], "zips": mapas_da_lista(p, mapas), "total": len(p["videos"]) + len(p.get("extras", []))} for k, p in listas().items()], "visor": (ARC / "index.html").exists(), "difs": list(DIFS), "pausada": pausada[0], "envio": envio})
            elif u.path == "/api/preparo":
                self.manda(preparo.estado())
            elif u.path == "/api/config":
                cache = sum(f.stat().st_size for p in DESCARTAVEL for f in (RAIZ / ".cache" / p).rglob("*") if f.is_file())
                self.manda({**config_publica(), "cache": cache, "placa": "+cu" in next((d.version for d in importlib.metadata.distributions(name="torch")), "")})  # torch com CUDA = analise na placa NVIDIA
            elif u.path == "/api/quest":
                self.manda(estado_quest())
            elif u.path == "/api/mapa":
                self.manda(mapa(q["zip"]))
            elif u.path == "/api/capa":  # capa de um mapa pronto (?zip=) ou de um arquivo de audio que acabou de subir (?arquivo=)
                if "zip" in q:
                    return self.manda(capa_do_zip(SAIDA / Path(q["zip"]).name), "image/png", guarda="v" in q)  # com a data na URL a capa pode ficar guardada
                png = RAIZ / ".cache" / "previa.png"
                png.unlink(missing_ok=True)
                if not fazer_capa(MUSICAS / Path(q["arquivo"]).name, png):
                    raise FileNotFoundError
                self.manda(png.read_bytes(), "image/png")
            elif u.path == "/api/bplist":  # a playlist com os mapas que ja existem, para quem poe o arquivo no jogo a mao
                p = listas()[q["id"]]
                self.manda(quest.bplist(p["nome"], [SAIDA / z for z in mapas_da_lista(p, lista_de_mapas())]).encode(), extra=[("Content-Disposition", f'attachment; filename="{arquivo_da_lista(q["id"])}"')])
            elif u.path == "/api/zip":
                nome = Path(q["zip"]).name
                self.manda((SAIDA / nome).read_bytes(), "application/zip", extra=[("Content-Disposition", f'attachment; filename="{nome}"')])
            elif u.path.startswith("/zip/"):  # o ArcViewer le o zip daqui
                self.manda((SAIDA / Path(unquote(u.path)).name).read_bytes(), "application/zip")
            elif u.path.startswith("/arcviewer/"):  # copia local do ArcViewer (GPL-3, github.com/AllPoland/ArcViewer)
                arq = (ARC / unquote(u.path[11:] or "index.html")).resolve()
                if ARC not in arq.parents:
                    return self.manda({"erro": "nao_existe"}, cod=404)
                extra = [("Content-Encoding", e) for x, e in ((".br", "br"), (".gz", "gzip")) if arq.suffix == x]
                base = arq.with_suffix("") if extra else arq
                self.manda(arq.read_bytes(), mimetypes.guess_type(base.name)[0] or "application/octet-stream", extra=extra)
            else:
                self.manda({"erro": "nao_existe"}, cod=404)
        except (KeyError, FileNotFoundError, zipfile.BadZipFile):
            self.manda({"erro": "sem_mapa"}, cod=404)

    def do_POST(self):
        if not self.local():
            return
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        n = int(self.headers.get("Content-Length", 0))
        if n > 300 * 2**20:
            return self.manda({"erro": "grande"}, cod=413)
        corpo = self.rfile.read(n)
        if u.path == "/api/arquivo":  # corpo = bytes do audio; ?nome=musica.mp3
            nome = re.sub(r"[^\w.\- ]", "_", Path(q.get("nome", "musica.mp3")).name)
            if Path(nome).suffix.lower() not in (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus", ".egg"):
                return self.manda({"erro": "tipo"}, cod=400)
            MUSICAS.mkdir(exist_ok=True)
            (MUSICAS / nome).write_bytes(corpo)
            return self.manda({"arquivo": str(MUSICAS / nome), "base": nome, **dados_da_musica(MUSICAS / nome)})
        try:
            d = json.loads(corpo or b"{}")
        except ValueError:
            return self.manda({"erro": "invalido"}, cod=400)
        if u.path == "/api/gerar":
            # playlist: "lista" traz as faixas ({link, titulo, capa}); cada uma vira um trabalho com as mesmas dificuldades, densidade e modo
            pedidos, novos = [{**d, "arquivo": None, "nome": None, "artista": None, "album": None, "ano": None, **m} for m in d["lista"] if isinstance(m, dict)] if isinstance(d.get("lista"), list) else [d], []
            # playlist repetida: faixa que ja tem mapa no mesmo modo e pulada, ou tem as notas refeitas se a conferencia dele falhou; a que ja espera na fila tambem e pulada
            varios, pulados, refeitos, pl = isinstance(d.get("lista"), list), 0, 0, d.get("playlist")
            feitos = {(video(m["link"]), m["sub"][-1:]): m for m in reversed(lista_de_mapas()) if m.get("link")} if varios else {}
            with trava:
                esperando = {(video(t["link"]), str(t.get("etapa"))) for t in trabalhos if t.get("link") and t["estado"] in ("na fila", "rodando")} | {t["regerar"] for t in fila if t.get("regerar")}
            for i, d in enumerate(pedidos):
                link, arq = str(d.get("link") or "").strip(), d.get("arquivo")
                if link and not re.match(r"https?://\S+$", link):
                    return self.manda({"erro": "link"}, cod=400)
                if not link and not (arq and Path(arq).parent == MUSICAS and Path(arq).exists()):
                    return self.manda({"erro": "vazio"}, cod=400)
                qual = (video(link), "3" if (d.get("modo") or config()["modo"]) == "rapido" else "4")
                m = feitos.get(qual)
                if varios and (qual in esperando or m and (m["ok"] is not False or m["zip"] in esperando)):
                    pulados += 1; continue
                esperando.add(qual)
                if m:
                    refeitos += 1; esperando.add(m["zip"])
                    novos.append({"id": int(time.time() * 1000) + i, "estado": "na fila", "passos": [], "progresso": None, "regerar": m["zip"], "titulo": m["nome"], "capa": "/api/capa?zip=" + quote(m["zip"])}); continue
                capa = d.get("capa") if re.fullmatch(r"https?://\S+|/api/capa\?\S+", str(d.get("capa"))) else None  # a miniatura da previa, so para o cartao da fila
                novos.append({"id": int(time.time() * 1000) + i, "estado": "na fila", "passos": [], "progresso": None, "capa": capa, "titulo": str(d.get("nome") or d.get("titulo") or "").strip() or link or Path(arq).name,
                              "link": link or None, "arquivo": arq, **{k: str(d.get(k) or "").strip() or None for k in ("nome", "artista", "album", "ano")},
                              "difs": [x for x in DIFS if x in (d.get("difs") or DIFS)] or list(DIFS),
                              "densidade": min(max(float(d.get("densidade") or 1), 0.8), 1.3), "sabres_capa": d["sabres_capa"] if isinstance(d.get("sabres_capa"), bool) else None,
                              "etapa": 3 if (d.get("modo") or config()["modo"]) == "rapido" else 4})  # rapido = sem separar instrumentos (etapa 3 do gerador)
            if not novos and not pulados:
                return self.manda({"erro": "vazio"}, cod=400)
            if varios and isinstance(pl, dict) and pl.get("id"):  # "criar a playlist no jogo": so anota as faixas; o .bplist e montado na hora, com os mapas que existirem
                ls = listas()
                ls[str(pl["id"])[:80]] = {"nome": str(pl.get("nome") or pl["id"])[:120], "videos": list(dict.fromkeys(video(str(m.get("link") or "")) for m in pedidos))}
                LISTAS.write_text(json.dumps(ls, ensure_ascii=False, indent=1), encoding="utf-8")
            with trava:
                trabalhos.extend(novos); fila.extend(novos); guardar_fila()
            return self.manda({"id": novos[0]["id"] if novos else None, "novos": len(novos) - refeitos, "pulados": pulados, "refeitos": refeitos})
        if u.path == "/api/trabalho/dispensar":  # tira da lista um trabalho que acabou (pronto ou com erro) ou que ainda esta na fila; "fila" = todos os que esperam
            with trava:
                sai = (lambda t: t["estado"] == "na fila") if d.get("fila") else (lambda t: t["id"] == d.get("id") and t["estado"] != "rodando")
                fila[:] = [t for t in fila if not sai(t)]
                trabalhos[:] = [t for t in trabalhos if not sai(t)]
                guardar_fila()
            return self.manda({"ok": True})
        if u.path == "/api/playlist/mapas":  # poe mapas numa playlist ("id") ou numa nova ("nome"), ou tira ("tirar")
            ls, k = listas(), str(d.get("id") or "")
            if k not in ls:
                if d.get("id") or not str(d.get("nome") or "").strip():
                    return self.manda({"erro": "invalido"}, cod=400)
                k = f"bl-{int(time.time() * 1000)}"
                ls[k] = {"nome": str(d["nome"]).strip()[:120], "videos": []}
            mexer_na_lista(ls[k], [str(z) for z in d.get("zips") or []], lista_de_mapas(), bool(d.get("tirar")))
            LISTAS.write_text(json.dumps(ls, ensure_ascii=False, indent=1), encoding="utf-8")
            return self.manda({"id": k, "nome": ls[k]["nome"]})
        if u.path == "/api/playlist/apagar":  # esquece a playlist; os mapas ficam
            ls = listas()
            if ls.pop(d.get("id"), None):
                LISTAS.write_text(json.dumps(ls, ensure_ascii=False, indent=1), encoding="utf-8")
            return self.manda({"ok": True})
        if u.path == "/api/fila":  # pausar ou continuar
            pausada[0] = bool(d.get("pausar"))
            return self.manda({"pausada": pausada[0]})
        if u.path == "/api/regerar" and isinstance(d.get("zips"), list):  # refaz varios mapas inteiros: um trabalho na fila para cada
            nomes = {m["zip"]: m["nome"] for m in lista_de_mapas()}
            novos = [{"id": int(time.time() * 1000) + i, "estado": "na fila", "passos": [], "progresso": None, "regerar": z, "titulo": nomes[z], "capa": "/api/capa?zip=" + quote(z)}
                     for i, z in enumerate(d["zips"]) if z in nomes]
            with trava:
                trabalhos.extend(novos); fila.extend(novos); guardar_fila()
            return self.manda({"n": len(novos)})
        if u.path == "/api/previa":  # dados e capa do link, antes de gerar (nao baixa o audio)
            link = (d.get("link") or "").strip()
            if not re.match(r"https?://\S+$", link):
                return self.manda({"erro": "link"}, cod=400)
            try:
                j = json.loads(ytdlp("--skip-download", "--flat-playlist", "--dump-single-json", "--", link))
                if j.get("_type") == "playlist":  # link so de playlist: a pagina pede um mapa por faixa (video com &list= continua sendo so o video, pelo --no-playlist)
                    itens = [{"link": e["url"], "nome": e.get("title") or e["url"], "capa": (e.get("thumbnails") or [{}])[-1].get("url"), "dur": e.get("duration")} for e in j.get("entries") or [] if e and e.get("url")]
                    return self.manda({"nome": j.get("title"), "id": j.get("id"), "capa": itens[0]["capa"], "lista": itens}) if itens else self.manda({"erro": "ytdlp"}, cod=400)
                return self.manda(dados_do_link(j))
            except (RuntimeError, ValueError) as e:
                return self.manda({"erro": str(e) if str(e).startswith("ytdlp|") else "ytdlp"}, cod=400)
        if u.path == "/api/preparo":  # baixa um item que falta, ou todos ("tudo"); o andamento sai no GET
            for item in preparo.ITENS if d.get("item") == "tudo" else [d.get("item")]:
                preparo.instalar(item)
            return self.manda(preparo.estado())
        if u.path == "/api/config":
            if d.get("discord_url") and not discord.URL.fullmatch(str(d["discord_url"]).strip()):
                return self.manda({"erro": "discord_url"}, cod=400)
            gravar_config(d)
            return self.manda(config_publica())
        if u.path == "/api/discord/teste":  # com o botao "Enviar teste": um cartao de exemplo, e a resposta diz se o Discord aceitou
            c = config()
            if not c["discord_url"]:
                return self.manda({"erro": "sem_discord"}, cod=400)
            erro = discord.teste(c["discord_url"], c["lingua"] or "pt")
            return self.manda({"erro": "discord|" + erro}, cod=502) if erro else self.manda({"ok": True})
        if u.path == "/api/cache":  # apaga as analises guardadas: a proxima geracao de cada musica volta a demorar
            if any(t["estado"] in ("na fila", "rodando") for t in trabalhos):
                return self.manda({"erro": "ocupado"}, cod=409)
            for p in DESCARTAVEL:
                shutil.rmtree(RAIZ / ".cache" / p, ignore_errors=True)
            return self.manda({"ok": True})
        if u.path in ("/api/quest/parear", "/api/quest/procurar"):  # com o cabo USB ligado, ou varrendo a rede atras do Quest que ja esta com o Wi-Fi ligado
            ip, erro = quest.parear() if u.path.endswith("parear") else quest.procurar()
            if erro:
                return self.manda({"erro": erro}, cod=400)
            gravar_config({"quest_ip": ip})
            time.sleep(2)  # o Quest leva um instante para voltar a responder depois de ligar o Wi-Fi
            return self.manda(estado_quest())
        if u.path == "/api/quest":  # so roda quando a pessoa clica no botao; "zips" = varios de uma vez; "forcar" manda tambem o que ja esta igual no Quest. Volta na hora: o envio roda no enviador e a pagina acompanha por /api/estado
            if not quest.conectado(config()["quest_ip"]):
                return self.manda({"erro": "sem_quest"}, cod=400)
            with trava:
                if not envio["ativo"]:  # lote novo: o resultado do anterior sai
                    envio.update(itens=[], playlists=0, lote=envio["lote"] + 1, ativo=True); inicia = True
                else:
                    inicia = False
                for nome in d.get("zips") or [d.get("zip")]:
                    z = SAIDA / Path(nome or "-").name
                    if any(i["zip"] == z.name and i["estado"] in ("espera", "enviando") for i in envio["itens"]):
                        continue  # ja esta na fila
                    envio["itens"] = [i for i in envio["itens"] if i["zip"] != z.name]
                    envio["itens"].append({"zip": z.name, "estado": "espera" if z.is_file() else "erro", "pct": 0, "sit": "", "erro": "" if z.is_file() else "sem_mapa", "forcar": bool(d.get("forcar"))})
            if inicia:
                threading.Thread(target=enviador, daemon=True).start()
            return self.manda({"ok": True})
        if u.path == "/api/quest/limpar":  # o X do painel (tira o resultado) ou "cancelar" (tira tambem o que ainda espera; o que esta subindo termina)
            with trava:
                envio["itens"] = [i for i in envio["itens"] if i["estado"] == "enviando" or i["estado"] == "espera" and not d.get("cancelar")]
            return self.manda({"ok": True})
        zp = SAIDA / Path(d.get("zip") or "-").name
        if u.path == "/api/restaurar":  # o Desfazer do apagar: traz da lixeira de volta, a menos que ja exista um mapa com esse nome
            if not (SAIDA / "lixeira" / zp.name).is_file():
                return self.manda({"erro": "sem_mapa"}, cod=404)
            if zp.exists():
                return self.manda({"erro": "invalido"}, cod=409)
            for f in (zp, zp.with_suffix(".relatorio.txt"), zp.with_suffix(".relatorio.json")):
                if (SAIDA / "lixeira" / f.name).exists():
                    (SAIDA / "lixeira" / f.name).replace(f)
            return self.manda({"ok": True})
        if u.path in ("/api/quest/apagar", "/api/apagar", "/api/renomear", "/api/regerar") and not zp.is_file():
            return self.manda({"erro": "sem_mapa"}, cod=404)
        if u.path == "/api/apagar":  # nao apaga de verdade: vai para saida\lixeira, de onde da para trazer de volta
            (SAIDA / "lixeira").mkdir(exist_ok=True)
            for f in (zp, zp.with_suffix(".relatorio.txt"), zp.with_suffix(".relatorio.json")):
                if f.exists():
                    f.replace(SAIDA / "lixeira" / f.name)
            return self.manda({"ok": True})
        if u.path == "/api/regerar":  # refaz uma dificuldade de um mapa pronto (outra quantidade de notas), sem mexer nas outras
            if d.get("dif") not in DIFS:
                return self.manda({"erro": "invalido"}, cod=400)
            tmp, etapa, _, capa, amb, _ = egg_do_mapa(zp, "um")  # o audio sai do proprio mapa, entao a analise ja esta no cache; o cenario fica o do mapa, para as luzes desta dificuldade servirem nele
            novo = tmp / f"regerar-v{etapa}.zip"
            dens = min(max(float(d.get("densidade") or 1), 0.8), 1.3)
            r = subprocess.run([PY, str(RAIZ / "generate.py"), str(tmp / "song.egg"), "--difs", d["dif"], "--densidade", str(dens), "--etapa", etapa, "--nome", "regerar", "--saida", str(tmp), "--prefs", prefs(), "--ambiente", amb, *capa],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
            if not novo.exists():
                return self.manda({"erro": "gerador|" + (r.stdout + r.stderr)[-300:]}, cod=500)
            trocar_dificuldade(zp, novo, d["dif"])
            mods.conjunto(zp, novo, [d["dif"]])  # a mesma dificuldade no conjunto do Noodle Extensions: entra, troca ou sai
            subprocess.run([PY, str(RAIZ / "report.py"), str(zp)], capture_output=True, cwd=RAIZ)  # relatorio do mapa inteiro, de novo
            return self.manda({"ok": True})
        if u.path == "/api/renomear":
            renomear(zp, (d.get("nome") or "").strip(), (d.get("artista") or "").strip())
            return self.manda({"ok": True})
        if u.path == "/api/quest/apagar":  # tira o mapa do Quest; o zip daqui fica
            erro = quest.apagar(config()["quest_ip"], zp.stem)
            return self.manda({"erro": "adb|" + erro}, cod=500) if erro else self.manda({"ok": True})
        self.manda({"erro": "nao_existe"}, cod=404)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(demo())
    SAIDA.mkdir(exist_ok=True)
    ler_fila()
    threading.Thread(target=operario, daemon=True).start()
    ThreadingHTTPServer.allow_reuse_address = os.name != "nt"  # no Windows, reusar o endereco deixaria dois servidores na mesma porta; no Linux, sem reusar, a porta fica presa por um minuto depois de fechar
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    except OSError:  # a porta esta ocupada: o Beatloom ja esta aberto em outra janela
        sys.exit(webbrowser.open(f"http://localhost:{PORTA}") and 0)
    print(f"Beatloom aberto em http://localhost:{PORTA}  (Ctrl+C fecha)")
    if "--sem-navegador" not in sys.argv:
        webbrowser.open(f"http://localhost:{PORTA}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
