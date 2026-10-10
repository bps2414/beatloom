r"""Gera varias musicas de uma vez e resume os relatorios, para comparar antes e depois de uma mudanca.

  .venv\Scripts\python.exe ferramentas\lote.py <lista.txt> <pasta de saida>

Cada linha da lista: arquivo de audio | nome | artista | pasta do mapa humano (opcional)
"""
import re, subprocess, sys
from pathlib import Path

lista, saida = Path(sys.argv[1]), sys.argv[2]
for linha in lista.read_text(encoding="utf-8-sig").splitlines():
    if not linha.strip():
        continue
    arq, nome, art, *hum = [p.strip() for p in linha.split("|")]
    cmd = [sys.executable, str(Path(__file__).parent.parent / "gerar.py"), arq, "--nome", nome, "--artista", art, "--saida", saida] + (["--humano", hum[0]] if hum and hum[0] else [])
    txt = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    print(f"\n{nome}: " + (re.search(r"RESULTADO: .*", txt) or ["GERADOR FALHOU " + txt[-300:]])[0])
    for bloco in txt.split("\n== ")[1:]:
        g = lambda p: (re.search(p, bloco) or ["", "-"])[1]
        print(f"  {bloco.split()[0]:11s} notas {g(r'notas (\d+) em'):>5s} | NPS {g(r'NPS na faixa [^:]*: ([\d.]+)'):>5s} | atravessadas {g(r'outra nota = 0: (\d+)')} | cruzados {g(r'cruzados (\d+)')} | rapidas {g(r'para a mao (\d+)')} | arcos {g(r'\(arcos\) (\d+)')}"
              f" | precisao {g(r'precisao (\d+%) \(nossos')} cobertura {g(r'cobertura (\d+%)')}" + "".join(" | FALHOU " + f for f in re.findall(r"\[FALHOU\] ([^:]*)", bloco)))
