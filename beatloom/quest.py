"""Manda mapas ao Quest por Wi-Fi (ADB). Quem guarda o IP e o beatloom.json; aqui so se fala com o aparelho."""
import re, shlex, shutil, socket, subprocess, sys, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Beat Saber 1.40.8 (SongCore). Versoes antigas usavam .../Mods/SongLoader/CustomLevels
DEST = "/sdcard/ModData/com.beatgames.beatsaber/Mods/SongCore/CustomLevels"
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


def enviar(ip, zp):
    """Sobe com nome temporario e troca no fim: envio cortado no meio nao deixa mapa pela metade. -> None ou o erro"""
    serie, alvo, part = f"{ip}:5555", shlex.quote(f"{DEST}/{PREFIXO}{Path(zp).stem}"), shlex.quote(f"{DEST}/.part")
    with tempfile.TemporaryDirectory() as tmp:
        zipfile.ZipFile(zp).extractall(Path(tmp) / "mapa")
        adb("-s", serie, "shell", f"mkdir -p {shlex.quote(DEST)} && rm -rf {part}")
        r = adb("-s", serie, "push", str(Path(tmp) / "mapa"), f"{DEST}/.part", espera=300)
        if r.returncode == 0:
            r = adb("-s", serie, "shell", f"rm -rf {alvo} && mv {part} {alvo}")
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:] or "adb"


def apagar(ip, nome):
    r = adb("-s", f"{ip}:5555", "shell", f"rm -rf {shlex.quote(f'{DEST}/{PREFIXO}{nome}')}")
    return None if r.returncode == 0 else (r.stderr or r.stdout).strip()[-300:] or "adb"


def demo():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); s.listen()
    assert abertos(["127.0.0.1", "127.0.0.2"], s.getsockname()[1]) == ["127.0.0.1"]
    s.close()
    print("demo ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
