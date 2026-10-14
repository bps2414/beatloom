r"""Mapas de prova do visual, para jogar no Quest e dizer o que funcionou (o que nao da para ver sem o jogo), e a previa do palco de um mapa.

  python tools\prova_visual.py                         grava em saida\ os mapas de prova: aparecem na lista do Beatloom, mande ao Quest por la
  python tools\prova_visual.py --previa <mapa.zip> [imagem.png]   desenha o palco do mapa (letreiro e colunas) visto do lugar do jogador
  python tools\prova_visual.py --demo

Cada mapa de prova sai do gerador de verdade, com o Chroma ligado, em cima da musica de mentira do tools\fixture.py. No jogo, o nome de cada
dificuldade diz o que ela testa, e o letreiro no fundo repete:
- "Prova logo Green Day" e "Prova logo Monstercat": cada dificuldade tenta esconder o nome da banda escrito no cenario com um palpite do nome
  da peca (o Chroma acha a peca pelo nome, e o jogo nao diz qual e). Anote qual dificuldade ficou sem o nome e se sumiu mais alguma coisa: o
  palpite certo vai para ESCONDE em beatloom\palco.py, e entao o cenario pode voltar ao sorteio do Chroma com o letreiro do artista por cima.
- "Prova neblina e carga": Easy normal; Normal e Hard com neblina mais fraca e mais forte; Expert e Expert+ com o letreiro repetido (uns 500 e
  uns 900 pecas), para achar quanto o Quest aguenta sem engasgar (palco.TETO, hoje 320).
"""
import json, subprocess, sys, zipfile
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
from beatloom import palco  # noqa: E402
from beatloom.luzes import LUZES  # noqa: E402

DIFS = ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"]
# palpites do nome da peca com o nome da banda: (rotulo no jogo, [(id, lookupMethod)]). Regex do .NET: (?i) ignora maiusculas
LOGO = r"(?i)logo"
PLACA = r"(?i)(text|sign|letter|title)"
NOME = r"(?i)(green ?day|monstercat)(?!environment)"
PALPITES = [("nada escondido", []), ("logo", [(LOGO, "Regex")]), ("texto ou placa", [(PLACA, "Regex")]), ("nome da banda", [(NOME, "Regex")]), ("os tres", [(LOGO, "Regex"), (PLACA, "Regex"), (NOME, "Regex")])]
NEBLINA = [None, 0.00001, 0.002, None, None]  # attenuation do BloomFogEnvironment em cada dificuldade
COPIAS = [0, 0, 0, 2, 4]  # letreiros a mais em cada dificuldade


def acende(d, amb, ids):
    """O letreiro da prova fica aceso, branco, a musica inteira; o centro do cenario passa a mirar so nas luzes dele."""
    for e in d["basicBeatmapEvents"]:
        if e["et"] == 4:
            e.setdefault("customData", {})["lightID"] = list(range(1, LUZES[amb][4] + 1))
    d["basicBeatmapEvents"].insert(0, {"b": 0, "et": 4, "i": 9, "f": 1, "customData": {"lightID": ids, "color": [1, 1, 1]}})


def preparar(d, amb, k, qual):
    """A dificuldade k da prova `qual` ("logo" ou "carga"). -> rotulo no jogo"""
    if qual == "logo":
        rotulo, esconde = PALPITES[k]
        pecas, ia, im = palco.letreiro(f"Prova {k + 1}", rotulo)
        extra = [{"id": i, "lookupMethod": m, "active": False} for i, m in esconde]
    else:
        rotulo = ["normal", "neblina fraca", "neblina forte", f"{COPIAS[3] + 1} letreiros", f"{COPIAS[4] + 1} letreiros"][k]
        pecas, ia, im = palco.letreiro(f"Prova {k + 1}", rotulo)
        n = len(pecas)
        for c in range(1, COPIAS[k] + 1):  # copias mais longe e mais alto, cada peca com um ID de luz proprio
            for j, q in enumerate(pecas[:n]):
                pecas.append({**q, "position": [q["position"][0], q["position"][1] + 9 * c, q["position"][2] + 12 * c],
                              "components": {"ILightWithId": {"type": 4, "lightID": palco.LETREIRO + 2000 * c + j}}})
        extra = [{"id": r"\]Environment$", "lookupMethod": "Regex", "components": {"BloomFogEnvironment": {"attenuation": NEBLINA[k]}}}] if NEBLINA[k] else []
    ids = [q["components"]["ILightWithId"]["lightID"] for q in pecas]
    d["customData"] = {"environment": extra + pecas, "materials": palco.MATERIAIS}
    acende(d, amb, ids)
    return f"{k + 1} {rotulo}"


def mapa(nome, amb, qual, saida, capa):
    """Gera o mapa de prova `nome` no cenario `amb` e prepara cada dificuldade. -> caminho do zip"""
    import fixture, generate
    from beatloom import engine
    egg = fixture.criar("Fixture", "pesado")
    if not (RAIZ / "dados" / "padroes_Easy.pkl").exists() or (RAIZ / "dados" / "padroes_Easy.pkl").stat().st_size == 0:
        engine.golpes = fixture.golpes_simples
    zp, _, _ = generate.gerar(egg, nome, "Beatloom", 4, "", saida, capa, None, 1.0, None, None, None, {"chroma"}, amb)
    tmp = zp.with_suffix(".tmp")
    with zipfile.ZipFile(zp) as z, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
        for b in info["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"]:
            d = json.loads(z.read(b["_beatmapFilename"]))
            rot = preparar(d, amb, DIFS.index(b["_difficulty"]), qual)
            b.setdefault("_customData", {}).update(_difficultyLabel=rot, _suggestions=["Chroma"])
            out.writestr(b["_beatmapFilename"], json.dumps(d, separators=(",", ":")))
        out.writestr("Info.dat", json.dumps(info, ensure_ascii=False, indent=2))
        for n in z.namelist():
            if n != "Info.dat" and not n.endswith("Standard.dat"):
                out.writestr(n, z.read(n))
    tmp.replace(zp)
    return zp


def previa(zp, png, dif=None):
    """Desenha o palco do mapa (as pecas do Chroma) visto do lugar do jogador, numa tela de 90 graus, com a pista de notas. -> deu certo?"""
    with zipfile.ZipFile(zp) as z:
        info = json.loads(z.read("Info.dat").decode("utf-8-sig"))
        bs = info["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"]
        b = next((x for x in bs if x["_difficulty"] == dif), bs[-1])
        d = json.loads(z.read(b["_beatmapFilename"]))
        cd = b.get("_customData", {})
    pecas = [p for p in d.get("customData", {}).get("environment", []) if "geometry" in p]
    if not pecas:
        return False
    cor = lambda k, pad: tuple(round(255 * cd[k][c]) for c in "rgb") if k in cd else pad
    tons = {"beatloom_letreiro": cor("_envColorLeft", (255, 60, 60)), "beatloom_coluna": cor("_envColorRight", (60, 120, 255))}
    W, H = 1280, 720
    img = np.zeros((H, W, 3), np.uint8)
    img[:] = (8, 8, 18)
    f, olho = (W / 2) / np.tan(np.radians(45)), (0.0, 1.7, 0.0)
    for z_ in np.linspace(1.5, 40, 600):  # as bordas da pista
        for x in (-1.2, 1.2):
            u, v = int(W / 2 + f * x / z_), int(H / 2 + f * olho[1] / z_)
            if 0 <= u < W and 0 <= v < H:
                img[v, u] = (90, 90, 110)
    for p in sorted(pecas, key=lambda p: -p["position"][2]):
        (x, y, z_), (sx, sy, sz) = p["position"], p["scale"]
        zf = z_ - sz / 2 - olho[2]
        if zf <= 0.5:
            continue
        x0, x1 = W / 2 + f * (x - sx / 2) / zf, W / 2 + f * (x + sx / 2) / zf
        y0, y1 = H / 2 - f * (y + sy / 2 - olho[1]) / zf, H / 2 - f * (y - sy / 2 - olho[1]) / zf
        img[int(np.clip(y0, 0, H)):int(np.clip(np.ceil(y1), 0, H)), int(np.clip(x0, 0, W)):int(np.clip(np.ceil(x1), 0, W))] = tons.get(p["geometry"].get("material"), (200, 200, 200))
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-i", "-", "-frames:v", "1", str(png)], input=img.tobytes())
    return r.returncode == 0


def demo():
    d = {"basicBeatmapEvents": [{"b": 1, "et": 4, "i": 1, "f": 1}, {"b": 1, "et": 1, "i": 1, "f": 1}]}
    assert preparar(d, "GreenDayEnvironment", 4, "logo") == "5 os tres" and [p["id"] for p in d["customData"]["environment"][:3]] == [LOGO, PLACA, NOME]
    assert d["basicBeatmapEvents"][0]["customData"]["color"] == [1, 1, 1] and d["basicBeatmapEvents"][1]["customData"]["lightID"] == [1, 2, 3]
    d = {"basicBeatmapEvents": []}
    preparar(d, "TriangleEnvironment", 4, "carga")
    ids = [p["components"]["ILightWithId"]["lightID"] for p in d["customData"]["environment"]]
    assert len(ids) == len(set(ids)) > 400 and d["basicBeatmapEvents"][0]["customData"]["lightID"] == ids  # 5 letreiros, IDs sem repetir, todos acesos
    d = {"basicBeatmapEvents": []}
    preparar(d, "TriangleEnvironment", 2, "carga")
    assert d["customData"]["environment"][0]["components"] == {"BloomFogEnvironment": {"attenuation": 0.002}}
    import re
    assert re.search(NOME, "GreenDayEnvironment.[0]Environment.[3]GreenDayLogo", re.I) and not re.search(NOME[4:], "greendayenvironment.[0]environment")
    print("prova ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--demo"]:
        sys.exit(demo())
    if a[:1] == ["--previa"]:
        png = Path(a[2] if len(a) > 2 else Path(a[1]).with_suffix(".palco.png"))
        print(png if previa(a[1], png) else "esse mapa nao tem palco (feito sem o Chroma, ou no palco da banda)")
        sys.exit(0)
    saida = RAIZ / "saida"
    capa = RAIZ / ".cache" / "prova_capa.png"
    capa.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "gradients=s=512x512:c0=0xff2a1a:c1=0x1a4dff:c2=0xffd21a:n=3", "-frames:v", "1", str(capa)], check=True)
    for nome, amb, qual in (("Prova logo Green Day", "GreenDayEnvironment", "logo"), ("Prova logo Monstercat", "MonstercatEnvironment", "logo"), ("Prova neblina e carga", "TriangleEnvironment", "carga")):
        print(f"{nome}: {mapa(nome, amb, qual, saida, capa)}")
