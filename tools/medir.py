r"""Mede os mapas que ja estao em saida\ (sem mapa humano): so o que da pra saber ouvindo a musica.

  .venv\Scripts\python tools\medir.py [pasta] [--dif ExpertPlus]

Pega, de cada musica, o zip da etapa mais nova (nome-v4.zip vence nome-v3.zip) e confere de novo com report.conferir, sem gravar nada.
Por dificuldade: notas por segundo; "cobertura" = ataques fortes que viraram nota; "precisao" = notas que caem num ataque forte (50 ms);
"corr" = correlacao entre a intensidade da musica e as notas por segundo em cada trecho de 4 compassos. No fim, a media por dificuldade
e quantos zips passaram em todas as conferencias. Compare antes e depois de cada mudanca no gerador.
"""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # a raiz do projeto, onde estao report.py e a pasta beatloom
from beatloom.audio import RAIZ
from report import conferir

DIFS = ("Easy", "Normal", "Hard", "Expert", "ExpertPlus")


def mais_novos(zips):
    """Um zip por musica: o de maior etapa (nome-v4 > nome-v3). Etiqueta depois da etapa (nome-v4-x) conta como outra musica."""
    por = {}
    for z in zips:
        m = re.fullmatch(r"(.+)-v(\d+)", z.stem)
        base, etapa = (m[1], int(m[2])) if m else (z.stem, 0)
        if base not in por or etapa > por[base][0]:
            por[base] = (etapa, z)
    return [z for _, z in sorted(por.values(), key=lambda v: v[1].name)]


def media(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else float("nan")


def main(args):
    so = args.pop(args.index("--dif") + 1) if "--dif" in args else None
    pasta = Path(args[0]) if args and args[0] != "--dif" else RAIZ / "saida"
    linhas, passou = {d: [] for d in DIFS}, []
    print(f"{'musica':44} {'dif':10} {'notas':>5} {'nps':>5} {'cobertura':>9} {'precisao':>8} {'corr':>5}")
    for zp in mais_novos(sorted(pasta.glob("*.zip"))):
        try:
            R = conferir(zp)
        except (SystemExit, Exception) as e:  # zip sem audio ou fora do formato nao derruba a medicao dos outros
            print(f"{zp.stem[:44]:44} pulado: {str(e)[:60]}")
            continue
        passou.append(R["passou"])
        if not R["passou"]:
            print(f"{zp.stem[:44]:44} NAO PASSOU em: " + ", ".join(f"{D['nome']} {m['id']}" for D in R["difs"] for m in D["metas"] if not m["ok"]))
        for D in R["difs"]:
            if not D["notas"] or (so and D["nome"] != so):
                continue
            v = (D["notas"], D["nps"], D["ataques_cobertura"], D["ataques_precisao"], D["correlacao"])
            linhas[D["nome"]].append(v)
            print(f"{zp.stem[:44]:44} {D['nome']:10} {v[0]:5d} {v[1]:5.2f} {v[2]:9.0%} {v[3]:8.0%} {'  -  ' if v[4] is None else format(v[4], '5.2f')}")
    print(f"\n{'MEDIA':44} {'dif':10} {'notas':>5} {'nps':>5} {'cobertura':>9} {'precisao':>8} {'corr':>5}   (n = musicas)")
    for d, L in linhas.items():
        if L:
            m = [media(c) for c in zip(*L)]
            print(f"{'':44} {d:10} {m[0]:5.0f} {m[1]:5.2f} {m[2]:9.0%} {m[3]:8.0%} {m[4]:5.2f}   n={len(L)}")
    print(f"\nzips que passaram em todas as conferencias: {sum(passou)} de {len(passou)}")


def demo():
    P = lambda *n: [Path(x) for x in n]
    assert mais_novos(P("a-v3.zip", "a-v4.zip", "b-v2.zip", "a-gerado-v4.zip")) == P("a-gerado-v4.zip", "a-v4.zip", "b-v2.zip")
    assert mais_novos(P("x-v10.zip", "x-v9.zip")) == P("x-v10.zip")
    assert media([1, None, 3]) == 2
    print("medir ok")


if __name__ == "__main__":
    sys.exit(demo() if sys.argv[1:] == ["--demo"] else main(sys.argv[1:]))
