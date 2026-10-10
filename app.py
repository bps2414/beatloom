r"""Interface web do automapper. Roda so neste PC.

  .venv\Scripts\python.exe app.py        -> abre http://localhost:8777 no navegador

Cole um link (YouTube etc., via yt-dlp) ou escolha um arquivo, gere o mapa, assista no ArcViewer (visualizador 3D embutido) e mande ao Quest.
"""
import json, mimetypes, re, shutil, subprocess, sys, threading, time, webbrowser, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from gerar import DIFS, dados_da_musica, fazer_capa, limpar_titulo

mimetypes.add_type('application/wasm', '.wasm')

RAIZ = Path(__file__).parent
SAIDA, MUSICAS = RAIZ / "saida", RAIZ / "musicas"
SYNC = RAIZ.parent / "quest-songs" / "sync.py"
PORTA = 8777
PY = sys.executable
ARC = RAIZ / "arcviewer"

trabalhos, fila = [], []  # um trabalho por vez: a analise usa o processador inteiro
trava = threading.Lock()


def dados_do_link(j):
    """Nome, artista, album, ano e capa a partir do que o yt-dlp sabe do link. Prefere a faixa/artista de verdade ao titulo do video."""
    m, a = limpar_titulo(j.get("title") or "")
    canal = re.sub(r"\s*-\s*Topic$", "", j.get("channel") or j.get("uploader") or "")
    artista = (j.get("artist") or j.get("creator") or "").split(",")[0].strip()
    ano = j.get("release_year") or (j.get("release_date") or j.get("upload_date") or "")[:4]
    d = {"nome": j.get("track") or m, "artista": artista or a or canal, "album": j.get("album"), "ano": str(ano or ""),
         "link": j.get("webpage_url"), "capa": j.get("thumbnail"), "dur": j.get("duration")}
    return {k: v for k, v in d.items() if v}


def ytdlp(*args):
    r = subprocess.run(["yt-dlp", "--no-playlist", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError("ytdlp|" + (r.stderr.strip().splitlines() or [""])[-1][:300])
    return r.stdout


def rodar(trab):
    def passo(txt):
        trab["passos"].append(txt)

    try:
        audio, d = trab.get("arquivo"), {}
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
        cmd = [PY, "-u", str(RAIZ / "gerar.py"), audio, "--etapa", "4", "--densidade", str(trab.get("densidade") or 1)]
        cmd += ["--difs", ",".join(trab["difs"])] if trab.get("difs") else []
        for k in ("nome", "artista", "album", "ano", "link", "capa"):
            cmd += [f"--{k}", str(d[k])] if d.get(k) else []
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
        rotulos = {"[1/4]": "ouvindo", "[2/4]": "golpes", "[3/4]": "empacotando", "[4/4]": "conferindo"}
        cauda = []
        for linha in p.stdout:
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
        if not trab.get("zip"):
            raise RuntimeError("gerador|" + " ".join(cauda)[-300:])
        trab["estado"] = "pronto"
    except Exception as e:
        trab["estado"], trab["erro"] = "erro", str(e)


def operario():
    while True:
        with trava:
            trab = fila.pop(0) if fila else None
        if trab is None:
            time.sleep(0.5)
            continue
        trab["estado"] = "rodando"
        rodar(trab)


def lista_de_mapas():
    out = []
    for zp in sorted(SAIDA.glob("*.zip"), key=lambda p: -p.stat().st_mtime):
        try:
            info = json.loads(zipfile.ZipFile(zp).read("Info.dat").decode("utf-8-sig"))
        except Exception:
            continue
        rel = zp.with_suffix(".relatorio.txt")
        txt = rel.read_text(encoding="utf-8") if rel.exists() else ""
        out.append({"zip": zp.name, "nome": info["_songName"], "sub": info.get("_songSubName", ""), "artista": info["_songAuthorName"],
                    "bpm": info["_beatsPerMinute"], "ok": "TODAS AS METAS OK" in txt, "conferido": bool(txt)})
    return out


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
    rel = zp.with_suffix(".relatorio.txt")
    return {"zip": zp.name, "nome": info["_songName"], "sub": info.get("_songSubName", ""), "artista": info["_songAuthorName"], "bpm": bpm,
            "difs": difs, "relatorio": rel.read_text(encoding="utf-8") if rel.exists() else "", **info.get("_customData", {}).get("_beatloom", {})}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def manda(self, corpo, tipo="application/json", cod=200, extra=()):
        if not isinstance(corpo, bytes):
            corpo = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(cod)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
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
                self.manda((RAIZ / "site" / "app.html").read_bytes(), "text/html; charset=utf-8")
            elif u.path == "/api/estado":
                self.manda({"trabalhos": trabalhos[-6:], "mapas": lista_de_mapas(), "quest": SYNC.exists(), "visor": (ARC / "index.html").exists(),
                            "difs": list(DIFS)})
            elif u.path == "/api/mapa":
                self.manda(mapa(q["zip"]))
            elif u.path == "/api/capa":  # capa de um mapa pronto (?zip=) ou de um arquivo de audio que acabou de subir (?arquivo=)
                if "zip" in q:
                    z = zipfile.ZipFile(SAIDA / Path(q["zip"]).name)
                    return self.manda(z.read(json.loads(z.read("Info.dat").decode("utf-8-sig"))["_coverImageFilename"]), "image/png")
                png = RAIZ / ".cache" / "previa.png"
                png.unlink(missing_ok=True)
                if not fazer_capa(MUSICAS / Path(q["arquivo"]).name, png):
                    raise FileNotFoundError
                self.manda(png.read_bytes(), "image/png")
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
            link, arq = (d.get("link") or "").strip(), d.get("arquivo")
            if link and not re.match(r"https?://\S+$", link):
                return self.manda({"erro": "link"}, cod=400)
            if not link and not (arq and Path(arq).parent == MUSICAS and Path(arq).exists()):
                return self.manda({"erro": "vazio"}, cod=400)
            trab = {"id": int(time.time() * 1000), "estado": "na fila", "passos": [], "titulo": (d.get("nome") or "").strip() or link or Path(arq).name,
                    "link": link or None, "arquivo": arq, **{k: str(d.get(k) or "").strip() or None for k in ("nome", "artista", "album", "ano")},
                    "difs": [x for x in DIFS if x in (d.get("difs") or DIFS)] or list(DIFS),
                    "densidade": min(max(float(d.get("densidade") or 1), 0.8), 1.3)}
            with trava:
                trabalhos.append(trab); fila.append(trab)
            return self.manda({"id": trab["id"]})
        if u.path == "/api/previa":  # dados e capa do link, antes de gerar (nao baixa o audio)
            link = (d.get("link") or "").strip()
            if not re.match(r"https?://\S+$", link):
                return self.manda({"erro": "link"}, cod=400)
            try:
                return self.manda(dados_do_link(json.loads(ytdlp("--skip-download", "--dump-single-json", "--", link))))
            except (RuntimeError, ValueError) as e:
                return self.manda({"erro": str(e) if str(e).startswith("ytdlp|") else "ytdlp"}, cod=400)
        zp = SAIDA / Path(d.get("zip") or "-").name
        if u.path in ("/api/quest", "/api/apagar", "/api/renomear") and not zp.is_file():
            return self.manda({"erro": "sem_mapa"}, cod=404)
        if u.path == "/api/apagar":  # nao apaga de verdade: vai para saida\lixeira, de onde da para trazer de volta
            (SAIDA / "lixeira").mkdir(exist_ok=True)
            for f in (zp, zp.with_suffix(".relatorio.txt")):
                if f.exists():
                    f.replace(SAIDA / "lixeira" / f.name)
            return self.manda({"ok": True})
        if u.path == "/api/renomear":
            renomear(zp, (d.get("nome") or "").strip(), (d.get("artista") or "").strip())
            return self.manda({"ok": True})
        if u.path == "/api/quest":  # so roda quando a pessoa clica no botao
            if not SYNC.exists():
                return self.manda({"erro": "sem_sync"}, cod=404)
            # o sync.py pula o zip se ja existe no Quest uma pasta com o mesmo nome: cada versao gerada vai com a hora no nome
            copia = RAIZ / ".cache" / "quest" / f"{zp.stem}-{time.strftime('%m%d-%H%M', time.localtime(zp.stat().st_mtime))}.zip"
            copia.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(zp, copia)
            r = subprocess.run([sys.executable, str(SYNC), str(copia)], capture_output=True, text=True, encoding="utf-8", errors="replace")
            return self.manda({"saida": (r.stdout + r.stderr).strip()[-600:], "ok": "ok      " in r.stdout})
        self.manda({"erro": "nao_existe"}, cod=404)


if __name__ == "__main__":
    SAIDA.mkdir(exist_ok=True)
    threading.Thread(target=operario, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    print(f"Beatloom aberto em http://localhost:{PORTA}  (Ctrl+C fecha)")
    if "--sem-navegador" not in sys.argv:
        webbrowser.open(f"http://localhost:{PORTA}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
