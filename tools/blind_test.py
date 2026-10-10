r"""Teste cego: recebe dois zips da MESMA musica e devolve "Musica - A" e "Musica - B" sem dizer qual e qual.

  .venv\Scripts\python.exe tools\blind_test.py <mapa1.zip> <mapa2.zip> [--nome "Musica"]

Sorteia quem e A e quem e B, iguala nome, autor, capa e cenario, e grava em saida\cego\:
  <musica>-<codigo>-A.zip, <musica>-<codigo>-B.zip   -> mande os dois pro Quest com o sync.py
  gabarito-<codigo>.txt                                -> NAO abra antes de jogar e dar as notas
O <codigo> muda a cada rodada, porque o sync.py pula nomes de pasta que ja existem no Quest.
"""
import io, json, random, secrets, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # a raiz do projeto, onde estao generate.py e a pasta beatloom
from beatloom.audio import RAIZ, ffmpeg
from generate import slug


def reempacotar(origem, destino, nome, letra, capa):
    z = zipfile.ZipFile(origem)
    info_n = next(n for n in z.namelist() if n.lower().endswith("info.dat") and "bpm" not in n.lower())
    raiz = info_n[:len(info_n) - len("info.dat")]
    info = json.loads(z.read(info_n).decode("utf-8-sig"))
    if "_difficultyBeatmapSets" not in info:
        sys.exit(f"{origem}: Info.dat nao e v2; nao sei igualar este formato.")
    info.update({"_songName": f"{nome} - {letra}", "_songSubName": "", "_levelAuthorName": "teste cego",
                 "_coverImageFilename": "cover.png", "_environmentName": "DefaultEnvironment"})
    info.pop("_customData", None)
    for s in info["_difficultyBeatmapSets"]:
        for b in s["_difficultyBeatmaps"]:
            b.pop("_customData", None)  # rotulos de dificuldade entregariam o autor
    antiga = None
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as out:
        out.writestr("Info.dat", json.dumps(info, ensure_ascii=False, indent=2))
        out.write(capa, "cover.png")
        for n in z.namelist():
            base = n[len(raiz):]
            if n.startswith(raiz) and base and "/" not in base and base.lower() not in ("info.dat", "cover.png") \
                    and not base.lower().endswith((".png", ".jpg", ".jpeg")):
                out.writestr(base, z.read(n))


def main(args):
    nome = args[args.index("--nome") + 1] if "--nome" in args else None
    zips = [Path(a) for a in args if a.lower().endswith(".zip")]
    if len(zips) != 2:
        sys.exit(__doc__)
    if not nome:
        z = zipfile.ZipFile(zips[0])
        nome = json.loads(z.read(next(n for n in z.namelist() if n.lower().endswith("info.dat"))).decode("utf-8-sig"))["_songName"]
    saida = RAIZ / "saida" / "cego"
    saida.mkdir(parents=True, exist_ok=True)
    cod = secrets.token_hex(2)
    capa = saida / "capa-neutra.png"
    if not capa.exists():
        ffmpeg("-f", "lavfi", "-i", "color=c=0x444444:s=256x256", "-frames:v", "1", capa)
    ordem = zips[:]
    random.SystemRandom().shuffle(ordem)
    for letra, zp in zip("AB", ordem):
        reempacotar(zp, saida / f"{slug(nome)}-{cod}-{letra}.zip", nome, letra, capa)
    (saida / f"gabarito-{cod}.txt").write_text("\n".join(f"{l} = {z.name}" for l, z in zip("AB", ordem)) + "\n", encoding="utf-8")
    print(f"Pronto: {saida}\\{slug(nome)}-{cod}-A.zip e -B.zip. O gabarito esta em gabarito-{cod}.txt (nao abra antes de jogar).")
    print("Formulario para cada um: nota 1-10 | as notas caiam na musica? | movimento desconfortavel (onde)? | trecho vazio ou cheio demais (onde)? | terminou?")


if __name__ == "__main__":
    main(sys.argv[1:])
