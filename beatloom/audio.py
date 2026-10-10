"""Peca 1 - OUVIR: batida, ataques, intensidade por compasso, compassos repetidos e (opcional) instrumentos.

Tudo em segundos. A grade tem 4 "casas" por batida (1/4 de batida). O resultado fica em cache por conteudo do arquivo.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).parent.parent  # a pasta do projeto
CACHE = RAIZ / ".cache"
# o C: quase nao tem espaco: todo cache vai pro F:
os.environ.setdefault("TORCH_HOME", str(CACHE / "torch"))
os.environ.setdefault("HF_HOME", str(CACHE / "hf"))
os.environ.setdefault("UV_CACHE_DIR", str(CACHE / "uv"))
os.environ.setdefault("NUMBA_CACHE_DIR", str(CACHE / "numba"))

import numpy as np

SR, HOP = 22050, 64
CASAS = 4  # casas por batida
INSTRUMENTOS = ("drums", "bass", "other", "vocals")


def ffmpeg(*args):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"ffmpeg falhou: {r.stderr.strip()[:500]}")


def _grade_de_batidas(beats, dur):
    """Limpa as batidas do beat_this -> (batidas cobrindo a musica toda, bpm, bpm_fixo?)."""
    beats = np.asarray(beats, float)
    p = float(np.median(np.diff(beats)))
    # buraco de uma batida perdida: preenche pelo meio
    cheio = [beats[0]]
    for b in beats[1:]:
        n = int(round((b - cheio[-1]) / p))
        cheio.extend(cheio[-1] + (b - cheio[-1]) * k / n for k in range(1, n)) if 1 < n <= 4 else None
        cheio.append(b)
    beats = np.array(cheio)
    idx = np.arange(len(beats))
    fixo = False
    if np.max(np.abs(np.diff(beats) - p)) < 0.4 * p:  # sem saltos: da pra testar BPM fixo
        per, a = np.polyfit(idx, beats, 1)
        bpm = 60 / per
        if abs(bpm - round(bpm)) < 0.05:  # tenta o BPM redondo; so aceita se a grade continuar colada
            per2 = 60 / round(bpm)
            a2 = float(np.mean(beats - per2 * idx))
            if np.max(np.abs(beats - (a2 + per2 * idx))) < 0.025:
                per, a = per2, a2
        if np.max(np.abs(beats - (a + per * idx))) < 0.035:
            fixo, beats, p = True, a + per * idx, per
    if not fixo and len(beats) >= 9:
        # andamento que oscila (banda tocando): segue a oscilacao, mas tira o tremor de 20 ms do detector
        from scipy.signal import savgol_filter
        beats = savgol_filter(beats, 9, 1)
    # estende ate cobrir [0, dur] com o periodo local
    p0, p1 = (p, p) if fixo else (float(np.median(np.diff(beats[:8]))), float(np.median(np.diff(beats[-8:]))))
    antes = beats[0] - p0 * np.arange(int(beats[0] / p0), 0, -1)
    depois = beats[-1] + p1 * np.arange(1, int((dur - beats[-1]) / p1) + 1)
    return np.concatenate([antes, beats, depois]), round(60 / p, 3), fixo, len(antes)


def _ataques(y, grade, sens):
    """Forca do ataque em cada casa e nivel do pico (2 = deteccao normal, 1 = so na sensivel, 0 = nada)."""
    import librosa
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    tenv = librosa.frames_to_time(np.arange(len(env)), sr=SR, hop_length=HOP)
    meia = np.minimum(np.diff(grade, append=grade[-1] + 1).clip(0.02) / 2, 0.045)
    i0, i1 = np.searchsorted(tenv, grade - meia), np.searchsorted(tenv, grade + meia)
    forca = np.array([env[a:max(b, a + 1)].max() if a < len(env) else 0.0 for a, b in zip(i0, i1)])
    forca = forca / (np.percentile(forca, 95) + 1e-9)
    nivel = np.zeros(len(grade), int)
    for lvl, delta in ((1, sens), (2, 0.07)):
        on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="time", backtrack=False, delta=delta)
        j = np.clip(np.searchsorted(grade, on), 1, len(grade) - 1)
        j = np.where(np.abs(grade[j - 1] - on) < np.abs(grade[j] - on), j - 1, j)
        nivel[j[np.abs(grade[j] - on) <= 0.06]] = lvl
    return forca, nivel, env


def _compassos(y, batidas, ini_comp, forca):
    """Intensidade (0..1) de cada compasso e 'de quem ele e repeticao' (indice do primeiro compasso igual)."""
    import librosa
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
    croma = librosa.feature.chroma_stft(y=y, sr=SR, hop_length=HOP)
    fr = lambda t: int(np.clip(t * SR / HOP, 0, len(rms) - 1))
    feats, energia = [], []
    for a, b in zip(ini_comp[:-1], ini_comp[1:]):
        f0, f1 = fr(batidas[a]), max(fr(batidas[b]), fr(batidas[a]) + 1)
        energia.append(float(np.sqrt(np.mean(rms[f0:f1] ** 2))))
        cortes = np.linspace(f0, f1, 5).astype(int)  # croma em 4 pedacos do compasso
        c = np.concatenate([croma[:, i:max(j, i + 1)].mean(1) for i, j in zip(cortes[:-1], cortes[1:])])
        r = forca[a * CASAS:b * CASAS]
        r = np.interp(np.linspace(0, 1, 16), np.linspace(0, 1, len(r)), r)
        feats.append(np.concatenate([c / (np.linalg.norm(c) + 1e-9), r / (np.linalg.norm(r) + 1e-9), [0]]))
    energia = np.array(energia)
    lo, hi = np.percentile(energia, 5), np.percentile(energia, 95)
    intens = np.clip((energia - lo) / (hi - lo + 1e-9), 0, 1)
    F = np.array(feats)
    F[:, -1] = intens  # compasso calmo nao e repeticao de compasso forte
    sim = (F[:, :-1] @ F[:, :-1].T) / 2 - np.abs(F[:, -1:] - F[:, -1:].T)
    R = sim > 0.9
    n = len(F)
    rep = list(range(n))
    for j in range(n):
        for i in range(j):
            # so vale se o vizinho tambem repete (diagonal na matriz de semelhanca)
            if R[i, j] and ((i > 0 and R[i - 1, j - 1]) or (j + 1 < n and R[i + 1, j + 1])):
                rep[j] = rep[i]
                break
    return [round(float(v), 3) for v in intens], rep


def dispositivo():
    """Placa NVIDIA quando o torch instalado sabe usa-la (o start.bat escolhe esse torch sozinho); senao o processador."""
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def na_placa(f):
    """f(dispositivo). Se a placa falhar no meio (o comum e faltar memoria), refaz no processador em vez de perder a geracao."""
    dev = dispositivo()
    try:
        return f(dev)
    except RuntimeError as e:
        if dev == "cpu":
            raise
        print(f"      a placa de video falhou ({str(e)[:80]}); refazendo no processador", flush=True)
        return f("cpu")


def _separar(wav, pasta):
    """Demucs (htdemucs) -> um wav por instrumento. E a parte demorada; fica em cache."""
    if not all((pasta / f"{s}.wav").exists() for s in INSTRUMENTOS):
        import torch, soundfile as sf
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        modelo = get_model("htdemucs").eval()
        x, sr = sf.read(wav, dtype="float32", always_2d=True)
        x = torch.from_numpy(x.T)
        ref = x.mean(0)
        media, desvio = ref.mean(), ref.std() + 1e-9
        x = (x - media) / desvio
        # o site le "[sep] N" para a barra: N = quanto da musica ja passou, contado nos pedacos que o Demucs comeca
        def andou(d):
            if d["state"] == "start":
                print(f"[sep] {100 * (d['model_idx_in_bag'] + d['segment_offset'] / x.shape[-1]) / d['models']:.0f}", flush=True)
        with torch.no_grad():
            out = na_placa(lambda dev: apply_model(modelo, x[None], device=dev, split=True, overlap=0.1, progress=False, callback=andou)[0].cpu())
        print("[sep] fim", flush=True)
        pasta.mkdir(parents=True, exist_ok=True)
        for nome, s in zip(modelo.sources, out):
            sf.write(pasta / f"{nome}.wav", (s.mean(0) * desvio).numpy(), sr)
    return {s: pasta / f"{s}.wav" for s in INSTRUMENTOS}


def analisar(caminho, instrumentos=False):
    """Analisa um arquivo de audio. Devolve dict com arrays numpy (ver chaves no fim)."""
    caminho = Path(caminho)
    h = hashlib.sha1(caminho.read_bytes()).hexdigest()[:16]
    pasta = CACHE / "analise" / h
    pasta.mkdir(parents=True, exist_ok=True)
    wav = pasta / "audio.wav"
    if not wav.exists():
        ffmpeg("-i", caminho, "-ac", "2", "-ar", "44100", wav)
    arq = pasta / ("analise_inst.json" if instrumentos else "analise.json")
    if not instrumentos and not arq.exists() and (pasta / "analise_inst.json").exists():
        arq = pasta / "analise_inst.json"  # a analise com instrumentos tem tudo o que a sem tem: a conferencia nao precisa ouvir a musica de novo
    if arq.exists():
        return {k: np.array(v) if isinstance(v, list) else v for k, v in json.loads(arq.read_text()).items()}

    import librosa
    y, _ = librosa.load(wav, sr=SR, mono=True)
    dur = len(y) / SR
    bruto = pasta / "batidas.json"
    if not bruto.exists():
        from beat_this.inference import File2Beats
        b, d = na_placa(lambda dev: File2Beats(checkpoint_path="final0", device=dev, dbn=False)(str(wav)))
        bruto.write_text(json.dumps({"b": [float(v) for v in b], "d": [float(v) for v in d]}))
    bd = json.loads(bruto.read_text())
    if len(bd["b"]) < 8:
        sys.exit("Nao achei batida nesta musica (menos de 8 batidas detectadas).")
    batidas, bpm, fixo, desloc = _grade_de_batidas(bd["b"], dur)
    di = np.array([int(np.argmin(np.abs(batidas - d))) for d in bd["d"]])
    if len(di) > 2 and int(np.bincount(np.diff(di)).argmax()) == 2 and bpm < 100:
        # compasso de 2 batidas lentas = o detector pegou meio-tempo; dobra para o compasso virar 4
        batidas = np.interp(np.arange(len(batidas) * 2 - 1) / 2, np.arange(len(batidas)), batidas)
        bpm = round(bpm * 2, 3)
    # compassos: tamanho e fase mais comuns entre os inicios de compasso detectados
    di = np.array([int(np.argmin(np.abs(batidas - d))) for d in bd["d"]])
    tam = int(np.bincount(np.diff(di)).argmax()) if len(di) > 2 else 4
    tam = tam if 2 <= tam <= 8 else 4
    fase = int(np.bincount(di % tam).argmax()) if len(di) else 0
    ini_comp = np.arange(fase, len(batidas), tam)
    fazer_grade = lambda b: np.interp(np.arange((len(b) - 1) * CASAS + 1) / CASAS, np.arange(len(b)), b)
    # o beat_this anda em passos de 20 ms e sai atrasado; acerta a fase pela mediana dos ataques (passo de 3 ms)
    on = librosa.onset.onset_detect(y=y, sr=SR, hop_length=HOP, units="time", backtrack=False)
    g0 = fazer_grade(batidas)
    desvio = on - g0[np.clip(np.searchsorted(g0, on), 1, len(g0) - 1)]
    desvio = np.where(np.abs(desvio) < np.abs(desvio + np.diff(g0).mean()), desvio, desvio + np.diff(g0).mean())
    fase_ms = float(np.median(desvio[np.abs(desvio) < 0.04])) if np.any(np.abs(desvio) < 0.04) else 0.0
    batidas = batidas + fase_ms
    grade = fazer_grade(batidas)
    forca, nivel, _ = _ataques(y, grade, 0.03)
    intens, rep = _compassos(y, batidas, ini_comp, forca)
    res = {"hash": h, "dur": dur, "bpm": bpm, "bpm_fixo": bool(fixo), "ajuste_fase_ms": round(fase_ms * 1000, 1), "batidas_por_compasso": tam,
           "batidas": batidas, "ini_comp": ini_comp, "grade": grade, "forca": forca, "nivel": nivel,
           "intens": intens, "rep": rep}
    if instrumentos:
        f_inst = []
        for nome, w in _separar(wav, pasta / "stems").items():
            ys, _ = librosa.load(w, sr=SR, mono=True)
            f, n, _ = _ataques(ys, grade, 0.05)
            # a forca de cada instrumento na escala da musica inteira: instrumento baixinho nao vira protagonista
            escala = float(np.sqrt(np.mean(ys ** 2)) / (np.sqrt(np.mean(y ** 2)) + 1e-9))
            f_inst.append(f * min(1.0, escala * 2))
            res[f"nivel_{nome}"] = n
        res["forca_inst"] = np.array(f_inst)  # [instrumento, casa], na ordem de INSTRUMENTOS
    arq.write_text(json.dumps({k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in res.items()}))
    return res


def sustentados(an):
    """Notas longas de voz ou melodia (o "ahhh" segurado) -> [(casa_ini, casa_fim)]. Precisa dos instrumentos separados.

    Vale quando ha um ataque forte do instrumento, o volume dele se mantem por pelo menos 1,5 batida (e 0,7 s),
    nao entra outro ataque forte no meio e a nota (altura) fica a mesma.
    """
    pasta = CACHE / "analise" / an["hash"]
    arq = pasta / "sustentados.json"
    if arq.exists():
        return [tuple(v) for v in json.loads(arq.read_text())]
    import librosa
    g, out = np.asarray(an["grade"]), []
    n = len(g) - 1
    for nome in ("vocals", "other"):
        w = pasta / "stems" / f"{nome}.wav"
        if not w.exists() or f"nivel_{nome}" not in an:
            continue
        y, _ = librosa.load(w, sr=SR, mono=True)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        nota = librosa.feature.chroma_stft(y=y, sr=SR, hop_length=512).argmax(0)
        fr = np.clip((g * SR / 512).astype(int), 0, len(rms) - 1)
        vol = np.array([rms[a:max(b, a + 1)].mean() for a, b in zip(fr[:-1], fr[1:])])
        alto, niv = np.percentile(vol, 75), an[f"nivel_{nome}"]
        i = 0
        while i < n:
            j = i + 1
            if niv[i] == 2 and vol[i] >= alto:
                while j < n and niv[j] < 2 and vol[j] >= 0.5 * vol[i]:
                    j += 1
                tom = nota[fr[i]:fr[j]]
                if (j - i >= CASAS * 1.5 and g[j] - g[i] >= 0.7 and len(tom) and np.mean(tom == np.bincount(tom).argmax()) >= 0.7
                        and not any(a < j and i < b for a, b in out)):
                    out.append((i, j))
            i = j
    out.sort()
    arq.write_text(json.dumps(out))
    return out


if __name__ == "__main__":
    a = analisar(sys.argv[1], "--inst" in sys.argv)
    print(f"dur {a['dur']:.1f}s | BPM {a['bpm']} ({'fixo' if a['bpm_fixo'] else 'variavel'}) | {len(a['batidas'])} batidas | "
          f"compasso de {a['batidas_por_compasso']} | picos fortes {int((a['nivel'] == 2).sum())}, fracos {int((a['nivel'] == 1).sum())}")
    print("repeticao:", " ".join(str(r) for r in a["rep"]))
    print("intensidade:", " ".join(f"{v:.1f}" for v in a["intens"]))
