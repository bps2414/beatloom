r"""Baixa mapas humanos bem avaliados do BeatSaver e guarda SO os arquivos de dificuldade.

  .venv\Scripts\python.exe tools\download_maps.py [quantos=1000]

Filtro: nota >= 85%, >= 50 votos, de 2022 em diante, sem IA, modo Standard, de Easy a Expert+,
sem Noodle/Mapping Extensions e com zero erro de paridade. O zip e lido na memoria; o audio nunca vai pro disco.
Uma chamada por segundo. Pode interromper e rodar de novo: continua de onde parou.
"""
import io, json, sys, time, urllib.parse, urllib.request, zipfile
from pathlib import Path

UA = "beatloom/0.1 (+https://github.com/bps2414/beatloom; biblioteca de padroes para uso pessoal)"
API = "https://api.beatsaver.com/search/text/{}?" + urllib.parse.urlencode(
    {"minRating": 0.85, "minVotes": 50, "from": "2022-01-01T00:00:00Z", "sortOrder": "Rating", "pageSize": 20})
DIFFS = {"Easy": 80, "Normal": 80, "Hard": 150, "Expert": 150, "ExpertPlus": 150}  # dificuldade -> minimo de notas
OUT = Path(__file__).parent.parent / "dados"
MAPAS, META, ESTADO = OUT / "mapas", OUT / "meta.jsonl", OUT / "estado.json"


def get(url):
    time.sleep(1.0)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def bons(m):
    """Dificuldades aproveitaveis de um mapa (lista vazia = pular o mapa)."""
    if m.get("automapper") or m.get("declaredAi", "None") != "None":
        return []
    return [d for d in m["versions"][-1]["diffs"]
            if d["characteristic"] == "Standard" and d["difficulty"] in DIFFS and not d["ne"] and not d["me"]
            and d["paritySummary"]["errors"] == 0 and d["notes"] >= DIFFS[d["difficulty"]]]


def main(alvo):
    MAPAS.mkdir(parents=True, exist_ok=True)
    est = json.loads(ESTADO.read_text()) if ESTADO.exists() else {"pagina": 0, "feitos": 0}
    while est["feitos"] < alvo and est["pagina"] < 557:
        docs = json.loads(get(API.format(est["pagina"])))["docs"]
        if not docs:
            break
        for m in docs:
            diffs, pasta = bons(m), MAPAS / m["id"]
            if not diffs or all((pasta / f"{d['difficulty']}.dat").exists() for d in diffs):  # ja tem tudo deste mapa
                continue
            try:
                z = zipfile.ZipFile(io.BytesIO(get(m["versions"][-1]["downloadURL"])))
                nomes = {n.lower(): n for n in z.namelist()}
                info = json.loads(z.read(nomes["info.dat"]).decode("utf-8-sig"))
                arqs = {b["_difficulty"]: b["_beatmapFilename"] for s in info["_difficultyBeatmapSets"]
                        if s["_beatmapCharacteristicName"] == "Standard" for b in s["_difficultyBeatmaps"]}
                pasta.mkdir(exist_ok=True)
                for d in diffs:
                    (pasta / f"{d['difficulty']}.dat").write_bytes(z.read(nomes[arqs[d["difficulty"]].lower()]))
            except Exception as e:  # Info.dat v4, zip quebrado, queda de rede: pula o mapa
                print(f"pulei {m['id']}: {type(e).__name__} {e}", flush=True)
                continue
            with META.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"id": m["id"], "bpm": m["metadata"]["bpm"], "nota": m["stats"]["score"],
                                    "ranked": m.get("ranked") or m.get("blRanked"),
                                    "diffs": {d["difficulty"]: {k: d[k] for k in ("nps", "njs", "offset", "notes")} for d in diffs}}) + "\n")
            est["feitos"] += 1
            if est["feitos"] >= alvo:
                break
        else:
            est["pagina"] += 1
        ESTADO.write_text(json.dumps(est))
        print(f"pagina {est['pagina']} | {est['feitos']} mapas", flush=True)
    print("FIM", est, flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
