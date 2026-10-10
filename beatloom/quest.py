"""Manda mapas ao Quest por Wi-Fi (ADB). Quem guarda o IP e o beatloom.json; aqui so se fala com o aparelho."""
import re, shlex, shutil, subprocess, tempfile, zipfile
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
