r"""Mede quanto tempo cada etapa da geracao leva, com o cache de analise desligado (pasta temporaria).

  .venv\Scripts\python.exe tools\timing.py <audio> [--etapa 3] [--threads N] [--difs Hard,Expert]

Os tempos sao "com tudo dentro": notas longas inclui as leituras de audio que ela faz, conferencia inclui o Node e a analise que ela repete.
"""
import sys, tempfile, time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # a raiz do projeto, onde estao generate.py e a pasta beatloom


def cronometrar(obj, nome, rotulo, soma):
    f = getattr(obj, nome)
    def g(*a, **k):
        t = time.perf_counter()
        try:
            return f(*a, **k)
        finally:
            soma[rotulo][0] += time.perf_counter() - t; soma[rotulo][1] += 1
    setattr(obj, nome, g)


def medir(audio, etapa=4, threads=None, difs=None):
    """-> ({rotulo: [segundos, chamadas]}, total em segundos)."""
    import librosa, beat_this.inference, generate, report
    from beatloom import audio as au, engine
    if threads:
        import torch
        torch.set_num_threads(threads)
    soma = defaultdict(lambda: [0.0, 0])
    for obj, nome, rotulo in ((au, "ffmpeg", "conversao (ffmpeg, na analise)"), (generate, "ffmpeg", "song.egg e capa (ffmpeg)"), 
                              (librosa, "load", "ler audio a 22 kHz (librosa.load)"), (au, "_ataques", "ataques"), (au, "_compassos", "compassos"), (au, "_separar", "separacao de instrumentos"),
                              (generate, "voz", "voz cantada (pYIN)"), (generate, "bateria", "pecas da bateria"), (generate, "partes", "partes da musica"),
                              (generate, "sustentados", "notas longas"),(engine, "golpes", "golpes (motor)"), (generate, "escolher_tempos", "escolha dos tempos"),
                              (report, "bsmap", "conferencia: Node (bsmap)"), (report, "conferir", "conferencia inteira")):
        cronometrar(obj, nome, rotulo, soma)
    F2B = beat_this.inference.File2Beats
    def batidas(*a, **k):  # o modelo e montado e chamado em seguida: conta os dois juntos
        t, f = time.perf_counter(), None
        def chamar(arq):
            r = F2B(*a, **k)(arq)
            soma["batidas (beat_this)"][0] += time.perf_counter() - t; soma["batidas (beat_this)"][1] += 1
            return r
        return chamar
    beat_this.inference.File2Beats = batidas
    with tempfile.TemporaryDirectory(dir=au.RAIZ / ".cache") as tmp:
        au.CACHE = Path(tmp)  # analise do zero; os modelos continuam vindo de .cache\torch e .cache\hf
        t = time.perf_counter()
        zp = generate.gerar(audio, "medir", etapa=etapa, saida=Path(tmp) / "saida", difs=difs)[0]
        soma["gerar inteiro (sem a conferencia)"] = [time.perf_counter() - t, 1]
        report.conferir(zp)
        return dict(soma), time.perf_counter() - t


def demo():
    class X:
        f = staticmethod(lambda v: v + 1)
    soma = defaultdict(lambda: [0.0, 0])
    cronometrar(X, "f", "x", soma)
    assert X.f(1) == 2 and X.f(2) == 3 and soma["x"][1] == 2 and soma["x"][0] >= 0
    print("medir ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a == ["--demo"]:
        sys.exit(demo())
    op = lambda n: a[a.index(n) + 1] if n in a else None
    soma, total = medir(a[0], int(op("--etapa") or 4), int(op("--threads") or 0), (op("--difs") or "").split(",") if op("--difs") else None)
    import torch
    print(f"\nTEMPOS  {Path(a[0]).name} | etapa {op('--etapa') or 4} | threads do torch {torch.get_num_threads()} | total {total:.1f} s")
    for k, (s, n) in sorted(soma.items(), key=lambda kv: -kv[1][0]):
        print(f"  {s:7.1f} s  {100 * s / total:5.1f}%  {k}" + (f" ({n}x)" if n > 1 else ""))
