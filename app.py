r"""Interface web do automapper. Roda so neste PC.

  .venv\Scripts\python.exe app.py        -> abre http://localhost:8777 no navegador

Cole um link (YouTube etc., via yt-dlp) ou escolha um arquivo, gere o mapa, assista no ArcViewer (visualizador 3D embutido) e mande ao Quest.
"""
import json, mimetypes, re, subprocess, sys, threading, time, webbrowser, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

mimetypes.add_type('application/wasm', '.wasm')

RAIZ = Path(__file__).parent
SAIDA, MUSICAS = RAIZ / "saida", RAIZ / "musicas"
SYNC = RAIZ.parent / "quest-songs" / "sync.py"
PORTA = 8777
PY = sys.executable
ARC = RAIZ / "arcviewer"

trabalhos, fila = [], []  # um trabalho por vez: a analise usa o processador inteiro
trava = threading.Lock()


def limpar_titulo(t):
    """'Artista - Musica (Official Video)' -> (musica, artista)."""
    t = re.sub(r"\s*[\(\[][^\)\]]*(official|video|audio|lyric|visuali[sz]er|hd|4k|mv)[^\)\]]*[\)\]]", "", t, flags=re.I).strip()
    if " - " in t:
        a, m = t.split(" - ", 1)
        return m.strip(), a.strip()
    return t, None


def rodar(trab):
    def passo(txt):
        trab["passos"].append(txt)

    try:
        audio, nome, artista = trab.get("arquivo"), trab.get("nome"), trab.get("artista")
        if trab.get("link"):
            passo("baixando")
            MUSICAS.mkdir(exist_ok=True)
            r = subprocess.run(
                ["yt-dlp", "--no-playlist", "-x", "--audio-format", "mp3", "--audio-quality", "0", "--restrict-filenames",
                 "-o", str(MUSICAS / "%(title)s.%(ext)s"), "--print", "after_move:%(filepath)s\t%(title)s\t%(artist,uploader)s\t%(track)s",
                 "--", trab["link"]], capture_output=True, text=True, encoding="utf-8", errors="replace")
            linha = next((l for l in r.stdout.splitlines() if "\t" in l), None)
            if r.returncode or not linha:
                raise RuntimeError("ytdlp|" + (r.stderr.strip().splitlines() or [""])[-1][:300])
            audio, titulo, art, faixa = linha.split("\t")
            m, a = limpar_titulo(titulo)
            nome = nome or (faixa if faixa and faixa != "NA" else m)
            artista = artista or a or (art if art != "NA" else None)
        trab["titulo"] = nome or Path(audio).stem
        cmd = [PY, "-u", str(RAIZ / "gerar.py"), audio, "--etapa", "4"]
        cmd += ["--nome", nome] if nome else []
        cmd += ["--artista", artista] if artista else []
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
        rotulos = {"[1/4]": "ouvindo", "[2/4]": "golpes", "[3/4]": "empacotando", "[4/4]": "conferindo"}
        cauda = []
        for linha in p.stdout:
            cauda = (cauda + [linha.rstrip()])[-6:]
            for k, v in rotulos.items():
                if linha.startswith(k) and (not trab["passos"] or trab["passos"][-1] != v):
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
            k = 60 / bpm
            difs.append({"nome": b["_difficulty"], "njs": b["_noteJumpMovementSpeed"],
                         "notas": [[round(n["_time"] * k, 4), n["_lineIndex"], n["_lineLayer"], n["_type"], n["_cutDirection"]] for n in d.get("_notes", [])],
                         "paredes": [[round(o["_time"] * k, 3), round(o["_duration"] * k, 3), o["_lineIndex"], o["_width"], o["_type"]] for o in d.get("_obstacles", [])]})
    rel = zp.with_suffix(".relatorio.txt")
    return {"zip": zp.name, "nome": info["_songName"], "sub": info.get("_songSubName", ""), "artista": info["_songAuthorName"], "bpm": bpm,
            "audio": info["_songFilename"], "difs": difs, "relatorio": rel.read_text(encoding="utf-8") if rel.exists() else ""}


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
                self.manda((RAIZ / "app.html").read_bytes(), "text/html; charset=utf-8")
            elif u.path == "/api/estado":
                self.manda({"trabalhos": trabalhos[-6:], "mapas": lista_de_mapas(), "quest": SYNC.exists(), "visor": (ARC / "index.html").exists()})
            elif u.path == "/api/mapa":
                self.manda(mapa(q["zip"]))
            elif u.path == "/api/audio":
                z = zipfile.ZipFile(SAIDA / Path(q["zip"]).name)
                info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
                self.manda(z.read(info["_songFilename"]), "audio/ogg")
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
            return self.manda({"arquivo": str(MUSICAS / nome)})
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
            trab = {"id": int(time.time() * 1000), "estado": "na fila", "passos": [], "titulo": link or Path(arq).name,
                    "link": link or None, "arquivo": arq, "nome": (d.get("nome") or "").strip() or None, "artista": (d.get("artista") or "").strip() or None}
            with trava:
                trabalhos.append(trab); fila.append(trab)
            return self.manda({"id": trab["id"]})
        if u.path == "/api/quest":  # so roda quando a pessoa clica no botao
            zp = SAIDA / Path(d.get("zip", "")).name
            if not zp.exists() or not SYNC.exists():
                return self.manda({"erro": "sem_sync"}, cod=404)
            r = subprocess.run([sys.executable, str(SYNC), str(zp)], capture_output=True, text=True, encoding="utf-8", errors="replace")
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
