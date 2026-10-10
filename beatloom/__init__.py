"""Miolo do Beatloom: ouvir a musica (audio), escolher os golpes (motor) e conferir (checks)."""
import os
from pathlib import Path

BIN = Path(__file__).parent.parent / "bin"  # programas que o proprio Beatloom baixa (ffmpeg, node, adb): ver preparo.py


def caminhos():
    """Poe os programas de bin\\ no fim do PATH: quem ja tem um instalado no sistema continua usando o seu."""
    atuais = os.environ.get("PATH", "").split(os.pathsep)
    novos = [str(p) for p in (BIN / "ffmpeg", BIN / "node", BIN / "platform-tools") if p.is_dir() and str(p) not in atuais]
    os.environ["PATH"] = os.pathsep.join(atuais + novos)


caminhos()
