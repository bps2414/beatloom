r"""O que o Beatloom precisa para funcionar: confere cada item e baixa o que faltar para dentro da pasta do projeto.

Nada e instalado no sistema: os programas vao para bin\, o visualizador para arcviewer\ e os padroes para dados\.
Os links sao os de Windows (o start.bat tambem e).

  .venv\Scripts\python.exe -m beatloom.preparo          -> mostra o estado de cada item
  .venv\Scripts\python.exe -m beatloom.preparo --demo
"""
import re, shutil, subprocess, sys, threading, urllib.request, zipfile
from pathlib import Path

from . import BIN, caminhos

RAIZ = BIN.parent
DADOS = RAIZ / "dados"
DIFS = ("Easy", "Normal", "Hard", "Expert", "ExpertPlus")
MAPAS = 1000  # quantos mapas humanos entram na biblioteca de padroes
ITENS = ("ffmpeg", "node", "padroes", "visor", "adb")
OBRIGATORIOS = ("ffmpeg", "node", "padroes")  # sem os outros dois so somem o visualizador 3D e o envio ao Quest
# cada zip e extraido sem a pasta de cima; "so" = guarda so estes arquivos, soltos na pasta
ZIPS = {
    "ffmpeg": dict(url="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip", pasta=BIN / "ffmpeg", so=("ffmpeg.exe", "ffprobe.exe")),
    "node": dict(url="https://nodejs.org/dist/v22.12.0/node-v22.12.0-win-x64.zip", pasta=BIN / "node"),
    "adb": dict(url="https://dl.google.com/android/repository/platform-tools-latest-windows.zip", pasta=BIN / "platform-tools"),
    "visor": dict(url="https://github.com/AllPoland/ArcViewer/archive/refs/heads/deploy.zip", pasta=RAIZ / "arcviewer"),  # GPL-3
}

andamento, rodando = {}, set()  # item -> {"feito", "total"} (bytes, ou mapas nos padroes) ou {"erro"}


def tem(item):
    if item == "ffmpeg":
        return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    if item == "node":  # o Node e mais a biblioteca bsmap, que confere o formato do mapa
        return bool(shutil.which("node")) and (RAIZ / "check" / "node_modules" / "bsmap").is_dir()
    if item == "adb":
        return bool(shutil.which("adb"))
    if item == "visor":
        return (RAIZ / "arcviewer" / "index.html").exists()
    return all((DADOS / f"padroes_{d}.pkl").exists() for d in DIFS)


def extrair(arq, pasta, so=None):
    pasta = Path(pasta).resolve()
    with zipfile.ZipFile(arq) as z:
        for info in z.infolist():
            partes = Path(info.filename).parts
            if info.is_dir() or len(partes) < 2 or (so and partes[-1] not in so):
                continue
            dest = (pasta / (partes[-1] if so else Path(*partes[1:]))).resolve()
            if pasta not in dest.parents:  # zip tentando escrever fora da pasta
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(info))


def baixar(item):
    z, arq = ZIPS[item], RAIZ / ".cache" / "baixar" / f"{item}.zip"
    arq.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(z["url"], headers={"User-Agent": "beatloom"}), timeout=60) as r, open(arq, "wb") as f:
        andamento[item] = {"feito": 0, "total": int(r.headers.get("Content-Length") or 0)}
        while bloco := r.read(1 << 18):
            f.write(bloco)
            andamento[item]["feito"] += len(bloco)
    extrair(arq, z["pasta"], z.get("so"))
    arq.unlink()
    caminhos()


def instalar_node():
    if not shutil.which("node"):
        baixar("node")
    andamento["node"] = {"feito": 0, "total": 0}
    r = subprocess.run([shutil.which("npm"), "ci", "--no-audit", "--no-fund"], cwd=RAIZ / "check", capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-300:])


def baixar_padroes():
    """Baixa so as notas dos mapas humanos (uma chamada por segundo, uns 20 minutos) e monta a biblioteca. Parou no meio: continua de onde estava."""
    andamento["padroes"] = {"feito": 0, "total": MAPAS}
    p = subprocess.Popen([sys.executable, "-u", str(RAIZ / "tools" / "download_maps.py"), str(MAPAS)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    cauda = ""
    for linha in p.stdout:
        cauda = linha.strip() or cauda
        m = re.search(r"\| (\d+) mapas", linha)
        if m:
            andamento["padroes"]["feito"] = int(m[1])
    if p.wait():
        raise RuntimeError(cauda[-300:])
    andamento["padroes"] = {"feito": 0, "total": 0}  # montar a biblioteca leva uns minutos e nao tem contagem
    r = subprocess.run([sys.executable, str(RAIZ / "tools" / "extract_patterns.py")], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[-300:])


def instalar(item):
    """Comeca a baixar um item em segundo plano; o andamento sai em estado()."""
    if item not in ITENS or item in rodando or tem(item):
        return

    def tarefa():
        try:
            {"padroes": baixar_padroes, "node": instalar_node}.get(item, lambda: baixar(item))()
            andamento.pop(item, None)
        except Exception as e:
            andamento[item] = {"erro": f"{type(e).__name__}: {e}"[:300]}
        rodando.discard(item)

    rodando.add(item)
    andamento[item] = {"feito": 0, "total": 0}
    threading.Thread(target=tarefa, daemon=True).start()


def estado():
    return {i: {"ok": tem(i), "obrigatorio": i in OBRIGATORIOS, "rodando": i in rodando, **andamento.get(i, {})} for i in ITENS}


def demo():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(tmp / "a.zip", "w") as z:
            for nome in ("topo/bin/ffmpeg.exe", "topo/bin/ffplay.exe", "topo/doc/leia.txt", "topo/../../fora.txt", "solto.txt"):
                z.writestr(nome, nome)
        extrair(tmp / "a.zip", tmp / "tudo")
        assert sorted(p.relative_to(tmp).as_posix() for p in tmp.rglob("*.*") if p.suffix != ".zip") == ["tudo/bin/ffmpeg.exe", "tudo/bin/ffplay.exe", "tudo/doc/leia.txt"]
        extrair(tmp / "a.zip", tmp / "so", so=("ffmpeg.exe",))
        assert [p.name for p in (tmp / "so").iterdir()] == ["ffmpeg.exe"]
    print("preparo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(demo())
    for nome, e in estado().items():
        print(f"{'ok   ' if e['ok'] else 'FALTA'} {nome}{'' if e['obrigatorio'] else ' (opcional)'}")
