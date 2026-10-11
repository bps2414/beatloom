"""Manda mapas ao Quest por Wi-Fi (ADB). Quem guarda o IP e o beatloom.json; aqui so se fala com o aparelho."""
import base64, hashlib, json, re, shlex, shutil, socket, subprocess, sys, tempfile, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Beat Saber 1.40.8 (SongCore). Versoes antigas usavam .../Mods/SongLoader/CustomLevels
MODS = "/sdcard/ModData/com.beatgames.beatsaber/Mods"
DEST = MODS + "/SongCore/CustomLevels"
LISTAS = ("PlaylistCore", "PlaylistManager")  # o mod de playlists guarda os .bplist em <um destes>/Playlists; vale o que existir no Quest
PREFIXO = "beatloom-"  # cada mapa vira a pasta beatloom-<nome do zip>: da para saber o que e nosso e mandar de novo por cima


def adb(*args, espera=20):
    try:
        return subprocess.run(["adb", *args], capture_output=True, encoding="utf-8", errors="replace", timeout=espera)
    except (OSError, subprocess.TimeoutExpired) as e:  # sem adb, ou Quest que nao responde
        return subprocess.CompletedProcess(args, 1, "", str(e))


def conectado(ip):
    if not ip or not shutil.which("adb"):
        return False
    adb("connect", f"{ip}:5555", espera=6)
    return f"{ip}:5555\tdevice" in adb("devices", espera=6).stdout


def parear():
    """Com o cabo USB ligado: descobre o IP do Quest e liga o ADB por Wi-Fi. -> (ip, None) ou (None, codigo do erro)"""
    if not shutil.which("adb"):
        return None, "sem_adb"
    usb = dict(l.split("\t")[:2] for l in adb("devices").stdout.splitlines()[1:] if "\t" in l and ":" not in l.split("\t")[0])
    serie = next((s for s, e in usb.items() if e == "device"), None)
    if not serie:  # "unauthorized" = falta aceitar o aviso que aparece dentro do headset
        return None, "sem_permissao" if usb else "sem_cabo"
    m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", adb("-s", serie, "shell", "ip", "-f", "inet", "addr", "show", "wlan0").stdout)
    if not m:
        return None, "sem_wifi"
    adb("-s", serie, "tcpip", "5555")
    return m[1], None


def abertos(ips, porta=5555, espera=0.5):
    """Quais desses enderecos aceitam conexao na porta."""
    def tenta(ip):
        try:
            socket.create_connection((ip, porta), espera).close(); return ip
        except OSError:
            return None
    with ThreadPoolExecutor(64) as p:
        return [ip for ip in p.map(tenta, ips) if ip]


def procurar():
    """Sem cabo: varre a rede do PC atras de quem tem o ADB por Wi-Fi ligado e fica com o primeiro que conecta. So acha o Quest que ja foi ligado pelo cabo desde que reiniciou. -> (ip, None) ou (None, codigo do erro)"""
    if not shutil.which("adb"):
        return None, "sem_adb"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("192.0.2.1", 9)); meu = s.getsockname()[0]; s.close()  # nao manda nada: so pergunta ao sistema por qual placa sairia
    except OSError:
        return None, "sem_rede"
    base = meu.rsplit(".", 1)[0]  # ponytail: so a faixa /24 do PC; rede maior ou Quest em outra faixa pede o IP escrito a mao
    for ip in abertos([f"{base}.{i}" for i in range(1, 255) if f"{base}.{i}" != meu]):
        if conectado(ip):
            return ip, None
    return None, "nao_achou"


def no_quest(ip):
    """Nomes (sem .zip) dos mapas nossos que estao no Quest."""
    saida = adb("-s", f"{ip}:5555", "shell", "ls", DEST).stdout
    return {l.strip()[len(PREFIXO):] for l in saida.splitlines() if l.strip().startswith(PREFIXO)}


def fracao(du, total):
    """A saida de `du -sk` na pasta de destino diante do tamanho total que vai subir -> 0..1 (0 se nao deu para ler)."""
    m = re.match(r"\d+", du.strip())
    return min(int(m[0]) * 1024 / total, 1) if m and total else 0


def empurrar(serie, origem, destino, total, andamento, espera=300):
    """adb push; o adb sem terminal nao conta o andamento, entao de segundo em segundo se pergunta ao Quest quanto ja chegou e se chama andamento(0..1)."""
    try:
        p = subprocess.Popen(["adb", "-s", serie, "push", origem, destino], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    except OSError as e:
        return subprocess.CompletedProcess([], 1, "", str(e))
    t0 = time.time()
    while True:
        try:
            out, err = p.communicate(timeout=1)
            return subprocess.CompletedProcess(p.args, p.returncode, out, err)
        except subprocess.TimeoutExpired:
            if time.time() - t0 > espera:
                p.kill(); out, err = p.communicate()
                return subprocess.CompletedProcess(p.args, 1, out, err or "timeout")
            if andamento:
                andamento(min(fracao(adb("-s", serie, "shell", "du", "-sk", destino, espera=5).stdout, total), 0.99))


def enviar(ip, zp, andamento=None):
    """Sobe com nome temporario e troca no fim: envio cortado no meio nao deixa mapa pela metade. -> None ou o erro"""
    serie, alvo, part = f"{ip}:5555", shlex.quote(f"{DEST}/{PREFIXO}{Path(zp).stem}"), shlex.quote(f"{DEST}/.part")
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(zp).extractall(Path(tmp) / "mapa")
        adb("-s", serie, "shell", f"mkdir -p {shlex.quote(DEST)} && rm -rf {part}")
        r = empurrar(serie, str(Path(tmp) / "mapa"), f"{DEST}/.part", sum(f.stat().st_size for f in (Path(tmp) / "mapa").rglob("*") if f.is_file()), andamento)
        if r.returncode == 0:
            r = adb("-s", serie, "shell", f"rm -rf {alvo} && mv {part} {alvo}")
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:] or "adb"


def apagar(ip, nome):
    r = adb("-s", f"{ip}:5555", "shell", f"rm -rf {shlex.quote(f'{DEST}/{PREFIXO}{nome}')}")
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:] or "adb"


def impressao(zp):
    """O codigo com que o jogo conhece o mapa: SHA-1 do Info.dat seguido dos arquivos de dificuldade, na ordem em que o Info.dat os cita. -> (codigo, Info.dat)"""
    with zipfile.ZipFile(zp) as z:
        cru = z.read("Info.dat"); info = json.loads(cru.decode("utf-8-sig"))
        return hashlib.sha1(cru + b"".join(z.read(b["_beatmapFilename"]) for s in info["_difficultyBeatmapSets"] for b in s["_difficultyBeatmaps"])).hexdigest().upper(), info


def bplist(nome, zips):
    """O texto de um .bplist (o formato dos mods de playlist) com esses mapas, na ordem; a capa e a do primeiro."""
    musicas, capa = [], ""
    for zp in zips:
        h, info = impressao(zp)
        musicas.append({"hash": h, "levelid": "custom_level_" + h, "songName": info["_songName"]})
        if not capa:
            capa = "data:image/png;base64," + base64.b64encode(zipfile.ZipFile(zp).read(info["_coverImageFilename"])).decode()
    return json.dumps({"playlistTitle": nome, "playlistAuthor": "Beatloom", "image": capa, "songs": musicas}, ensure_ascii=False)


def enviar_lista(ip, arquivo, texto):
    """Poe um .bplist na pasta do mod de playlists. -> None ou o erro"""
    serie = f"{ip}:5555"
    tem = adb("-s", serie, "shell", "ls", MODS).stdout.split()
    pasta = f"{MODS}/{next((m for m in LISTAS if m in tem), LISTAS[0])}/Playlists"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / arquivo).write_text(texto, encoding="utf-8")
        adb("-s", serie, "shell", f"mkdir -p {shlex.quote(pasta)}")
        r = adb("-s", serie, "push", str(Path(tmp) / arquivo), f"{pasta}/{arquivo}", espera=60)
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:] or "adb"


def demo():
    with tempfile.TemporaryDirectory() as tmp:  # a impressao segue a ordem do Info.dat, nao a do zip
        zp, info = Path(tmp) / "m.zip", json.dumps({"_songName": "X", "_coverImageFilename": "c.png", "_difficultyBeatmapSets": [{"_difficultyBeatmaps": [{"_beatmapFilename": "a.dat"}, {"_beatmapFilename": "b.dat"}]}]}).encode()
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("b.dat", "B"); z.writestr("a.dat", "A"); z.writestr("Info.dat", info); z.writestr("c.png", b"png")
        h = hashlib.sha1(info + b"AB").hexdigest().upper()
        assert impressao(zp)[0] == h
        j = json.loads(bplist("Lista", [zp]))
        assert j["songs"] == [{"hash": h, "levelid": "custom_level_" + h, "songName": "X"}] and j["image"].endswith(base64.b64encode(b"png").decode())
    assert fracao("512\t/x/.part\n", 2048 * 1024) == 0.25 and fracao("9999\t/x", 1024) == 1 and fracao("du: No such file", 1024) == 0 and fracao("5", 0) == 0
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen()
    assert abertos(["127.0.0.1", "127.0.0.2"], s.getsockname()[1]) == ["127.0.0.1"]
    s.close()
    print("demo ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
