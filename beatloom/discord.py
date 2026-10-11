r"""Avisos no Discord por webhook: andamento da fila, mapa pronto, erro e resumo final.

As frases moram em site\i18n\pt.json e en.json (chaves dc_*), como as da pagina. A mensagem e montada aqui (montar) e enviada
por uma thread propria, uma por vez e na ordem, para nunca atrasar a geracao. A mensagem de andamento e uma so: nasce com a fila e
e editada a cada musica (sem encher o canal, e longe do limite de envios do Discord); o resumo final reaproveita a mesma mensagem.

  python -m beatloom.discord --demo
"""
import json, queue, re, sys, threading, time, urllib.error, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path

URL = re.compile(r"https://(?:(?:ptb|canary)\.)?(?:discord|discordapp)\.com/api/webhooks/(\d+)/([\w-]+)")  # so o Discord: o Beatloom nao manda dados para outro endereco
EVENTOS = ("andamento", "pronto", "erro", "fim")
I18N = Path(__file__).parent.parent / "site" / "i18n"
COR = {"ok": 0x3DDC97, "azul": 0x2F8FFF, "alerta": 0xFFB020, "erro": 0xFF3355}  # as cores da pagina
BOLA = {"Easy": "🟢", "Normal": "🔵", "Hard": "🟠", "Expert": "🔴", "ExpertPlus": "🟣"}  # as cores das dificuldades no jogo
_frases = {}


def tr(lingua, k, **v):
    if lingua not in ("pt", "en"):
        lingua = "pt"
    if lingua not in _frases:
        _frases[lingua] = json.loads((I18N / f"{lingua}.json").read_text(encoding="utf-8"))
    return re.sub(r"\{(\w+)\}", lambda m: str(v.get(m[1], "")), _frases[lingua].get(k, k))


def mascara(url):
    """O endereco do webhook e um segredo: a pagina so ve o fim dele."""
    m = URL.fullmatch(url or "")
    return f"discord.com/…{m[1][-4:]}/•••{m[2][-4:]}" if m else ""


def corta(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def esc(s, n=100):
    """Nome de musica vem de fora (YouTube): sem markdown solto e sem @everyone."""
    return corta(re.sub(r"([\\*_`~|>])", r"\\\1", str(s or "")).replace("@", "@​"), n)


def mmss(s):
    s = int(s or 0)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def barra(f, n=14):
    k = round(min(max(f, 0), 1) * n)
    return "▰" * k + "▱" * (n - k)


def campo(nome, valor, lado=False):
    return {"name": corta(nome, 256), "value": corta(valor, 1024) or "-", "inline": lado}


def etapa(T, passo, prog):
    """A mesma frase da pagina: "golpes|Hard (2/4)" vira "Escolhendo as notas e os golpes de Hard (2/4)"."""
    k, _, qual = (passo or "comecando").partition("|")
    return T("passo_" + ("separando" if prog is not None else k)) + (" " + qual.replace("ExpertPlus", "Expert+") if qual else "") + (f" {prog}%" if prog is not None else "")


def montar(ev, d, lg="pt"):
    """-> o JSON do webhook. ev: pronto | teste | erro | andamento | fim. `d` e o que o app.py sabe; sem nada do Discord aqui."""
    T = lambda k, **v: tr(lg, k, **v)
    e = {"footer": {"text": "Beatloom"}, "timestamp": datetime.now(timezone.utc).isoformat()}
    if ev in ("pronto", "teste"):
        ok = d.get("ok")
        e.update(author={"name": T("dc_teste_a" if ev == "teste" else "dc_pronto_a")}, title=esc(d["nome"], 200), color=COR["alerta" if ok is False else "ok"],
                 description=(T("dc_teste_d") + "\n\n" if ev == "teste" else "") + T("dc_de", artista=esc(d["artista"], 120)))
        e["fields"] = [campo(T("dc_bpm"), f"{d['bpm']:g}" if d.get("bpm") else "-", True), campo(T("dc_dur"), mmss(d.get("dur")), True)]
        if d.get("tempo"):
            e["fields"].append(campo(T("dc_tempo"), mmss(d["tempo"]), True))
        e["fields"].append(campo(T("dc_difs"), "   ".join(f"{BOLA.get(x, '⚪')} {x.replace('ExpertPlus', 'Expert+')}" for x in d.get("difs") or [])))
        if ok is not None:
            e["fields"].append(campo(T("dc_conf"), T("dc_conf_ok" if ok else "dc_conf_ruim")))
        if d.get("capa_arq"):
            e["thumbnail"] = {"url": "attachment://" + d["capa_arq"]}
    elif ev == "erro":
        code, _, det = str(d.get("erro") or "").partition("|")
        msg = T("erro_" + code)
        if msg == "erro_" + code:  # codigo que a pagina nao conhece: a frase geral, e o texto inteiro como detalhe
            msg, det = T("erro_geral"), str(d.get("erro") or "")
        e.update(author={"name": T("dc_erro_a")}, title=esc(d["titulo"], 200), color=COR["erro"], description=msg + (f"\n```\n{corta(det.replace('```', chr(39) * 3), 900)}\n```" if det.strip() else ""))
        e["fields"] = [campo(T("dc_erro_dica_t"), T("dc_erro_dica"))]
        if d.get("capa", "").startswith("https://"):
            e["thumbnail"] = {"url": d["capa"]}
    elif ev == "andamento":
        fe, tot = d["feitos"], max(d["total"], 1)
        e.update(author={"name": T("dc_and_a")}, title=T("dc_and_t", feitos=len(fe), total=tot), color=COR["azul"],
                 description=f"`{barra(len(fe) / tot)}`  **{round(100 * len(fe) / tot)}%**")
        if d.get("atual"):
            a = d["atual"]
            e["fields"] = [campo(T("dc_agora"), f"**{esc(a['titulo'], 150)}**\n{etapa(T, a.get('passo'), a.get('progresso'))}")]
            if a.get("capa", "").startswith("https://"):
                e["thumbnail"] = {"url": a["capa"]}
        e.setdefault("fields", []).extend(lista_de(T, fe, 6, "dc_prontos") + [campo(T("dc_faltam"), str(max(tot - len(fe) - (1 if d.get("atual") else 0), 0)), True), campo(T("dc_decorrido"), mmss(d.get("seg")), True)])
    elif ev == "fim":
        fe = d["feitos"]
        bons, ruins = [x for x in fe if x["ok"]], [x for x in fe if not x["ok"]]
        linhas = [f"{'✅' if x['ok'] else '❌'} **{esc(x['titulo'], 70)}**" + (f" · {esc(x['artista'], 50)}" if x.get("artista") else "") for x in fe]
        texto, i = "", 0
        while i < len(linhas) and len(texto) + len(linhas[i]) < 3600:  # a descricao aceita 4096; o resto vira "e mais N"
            texto += linhas[i] + "\n"; i += 1
        if i < len(linhas):
            texto += T("dc_mais", n=len(linhas) - i)
        e.update(author={"name": T("dc_fim_a")}, title=T("dc_fim_ok", n=len(bons)) if not ruins else T("dc_fim_ruim", n=len(bons), e=len(ruins)), color=COR["alerta" if ruins else "ok"], description=texto.strip(),
                 fields=[campo(T("dc_total"), mmss(d.get("seg")), True), campo(T("dc_media"), mmss(d.get("seg", 0) / max(len(fe), 1)), True)])
    return {"embeds": [e], "allowed_mentions": {"parse": []}}  # sem marcar ninguem, venha o que vier no nome da musica


def lista_de(T, feitos, n, chave):
    if not feitos:
        return []
    ult = [f"✅ {esc(x['titulo'], 60)}" if x["ok"] else f"❌ {esc(x['titulo'], 60)}" for x in feitos[-n:]]
    return [campo(T(chave), "\n".join(ult) + (("\n" + T("dc_antes", n=len(feitos) - n)) if len(feitos) > n else ""))]


def enviar(url, payload, capa=None, editar=None):
    """-> (id da mensagem, None) ou (None, codigo do erro). Com `capa` (bytes) vai como anexo e o embed a mostra; `editar` = id de uma mensagem do mesmo webhook."""
    if capa:
        b, nome = uuid.uuid4().hex, "capa.png" if capa[:4] == b"\x89PNG" else "capa.jpg"
        cab = lambda extra: f'--{b}\r\nContent-Disposition: form-data; {extra}\r\n'.encode()
        corpo = cab('name="payload_json"') + b"Content-Type: application/json\r\n\r\n" + json.dumps(payload).encode() + b"\r\n" + cab(f'name="files[0]"; filename="{nome}"') + b"\r\n" + capa + f"\r\n--{b}--\r\n".encode()
        tipo = "multipart/form-data; boundary=" + b
    else:
        corpo, tipo = json.dumps(payload).encode(), "application/json"
    base = url.split("?")[0]
    alvo = f"{base}/messages/{editar}" if editar else base + "?wait=true"
    for tentativa in (0, 1):
        pedido = urllib.request.Request(alvo, corpo, {"Content-Type": tipo, "User-Agent": "DiscordBot (https://github.com/bps2414/beatloom, 1)"}, method="PATCH" if editar else "POST")  # o User-Agent padrao do urllib e barrado
        try:
            with urllib.request.urlopen(pedido, timeout=15) as r:
                return json.loads(r.read() or b"{}").get("id"), None
        except urllib.error.HTTPError as x:
            if x.code == 429 and not tentativa:  # limite de envios: espera o que o Discord pediu e tenta uma vez mais
                try:
                    time.sleep(min(float(json.loads(x.read() or b"{}").get("retry_after", 1)), 10))
                except ValueError:
                    time.sleep(1)
                continue
            return None, str(x.code)
        except (OSError, ValueError):
            return None, "rede"
    return None, "429"


_fila, _msg, _trava = queue.Queue(), [None, None], threading.Lock()  # _msg = [webhook, id] da mensagem de andamento que esta sendo editada
_viva = []


def _trabalha():
    while True:
        url, modo, payload, capa = _fila.get()
        try:
            if modo == "novo":
                erro = enviar(url, payload, capa)[1]
            else:  # andamento e fim: edita a mensagem da fila; se ainda nao ha (ou foi apagada) cria
                alvo = _msg[1] if _msg[0] == url else None
                id, erro = enviar(url, payload, editar=alvo) if alvo else (None, "404")
                if erro == "404":
                    id, erro = enviar(url, payload)
                _msg[:] = [url, None if modo == "fim" else (id or alvo)]
            if erro:
                print(f"[discord] nao enviou ({erro})")  # nunca o endereco: ele e segredo
        except Exception as x:
            print(f"[discord] nao enviou ({type(x).__name__})")
        _fila.task_done()


def avisar(url, ev, d, lg="pt", capa=None):
    """Entra na fila de envio e volta na hora. `capa` = bytes da imagem (so mensagens novas: pronto)."""
    with _trava:
        if not _viva:
            _viva.append(threading.Thread(target=_trabalha, daemon=True)); _viva[0].start()
    if capa:
        d = {**d, "capa_arq": "capa.png" if capa[:4] == b"\x89PNG" else "capa.jpg"}
    _fila.put((url, ev if ev in ("andamento", "fim") else "novo", montar(ev, d, lg), capa if ev in ("pronto", "teste") else None))


def teste(url, lg="pt"):
    """O botao "Enviar teste": manda um cartao de exemplo e espera a resposta. -> None se foi, senao o codigo do erro."""
    return enviar(url, montar("teste", {"nome": "Beatloom", "artista": "Test", "bpm": 128, "dur": 195, "tempo": 312, "ok": True, "difs": ["Normal", "Hard", "Expert", "ExpertPlus"]}, lg))[1]


def demo():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    ok = "https://discord.com/api/webhooks/123456789/AbC-dEf_123"
    assert URL.fullmatch(ok) and mascara(ok).endswith("•••_123") and "AbC" not in mascara(ok)
    for ruim in ("http://discord.com/api/webhooks/1/a", "https://discord.com.evil.com/api/webhooks/1/a", "https://evil.com/api/webhooks/1/a", ok + "/x", ""):
        assert not URL.fullmatch(ruim), ruim
    assert barra(0.5, 4) == "▰▰▱▱" and mmss(75) == "1:15" and mmss(3725) == "1:02:05"
    feitos = [{"titulo": f"Musica *{i}* @everyone " + "x" * 90, "artista": "A" * 80, "ok": i % 7 != 0, "erro": None} for i in range(80)]
    pronto = {"nome": "Ache", "artista": "Not For Radio", "bpm": 63.83, "dur": 113.7, "tempo": 400, "ok": True, "difs": ["Normal", "Hard", "Expert", "ExpertPlus"], "capa_arq": "capa.png"}
    casos = {"pronto": pronto, "teste": pronto, "erro": {"titulo": "X" * 300, "erro": "gerador|" + "linha ``` longa " * 80, "capa": "https://i.ytimg.com/a.jpg"}, "erro2": {"titulo": "X", "erro": "[WinError 2] algo"},
             "andamento": {"feitos": feitos[:5], "total": 12, "seg": 700, "atual": {"titulo": "Ache", "passo": "golpes|Hard (2/4)", "progresso": None, "capa": "https://i.ytimg.com/a.jpg"}},
             "fim": {"feitos": feitos, "seg": 99999}}
    for lg in ("pt", "en"):
        for nome, d in casos.items():
            p = montar(nome.rstrip("2"), d, lg)
            e, total = p["embeds"][0], 0
            assert p["allowed_mentions"] == {"parse": []} and "@everyone" not in json.dumps(p), nome
            assert "dc_" not in json.dumps(p) and not re.search(r"\b(erro|passo)_\w+", json.dumps(p)), (lg, nome, "falta frase")  # chave sem frase aparece como o proprio codigo
            assert len(e.get("title", "")) <= 256 and len(e.get("description", "")) <= 4096 and len(e.get("fields", [])) <= 25, nome
            total += len(e.get("title", "")) + len(e.get("description", "")) + len(e["footer"]["text"]) + len(e.get("author", {}).get("name", ""))
            for f in e.get("fields", []):
                assert len(f["name"]) <= 256 and len(f["value"]) <= 1024, nome
                total += len(f["name"]) + len(f["value"])
            assert total <= 6000, (nome, total)
    assert "Starting" in json.dumps(montar("andamento", {"feitos": [], "total": 3, "atual": {"titulo": "A", "passo": None}}, "en"))
    assert "63.83" in json.dumps(montar("pronto", pronto, "pt"))
    vistos = []

    class S(BaseHTTPRequestHandler):
        def do_POST(self): self.resp()
        def do_PATCH(self): self.resp()

        def resp(self):
            corpo = self.rfile.read(int(self.headers["Content-Length"]))
            vistos.append((self.command, self.path, self.headers["Content-Type"].split(";")[0], corpo, self.headers["User-Agent"]))
            if "limite" in self.path and len([v for v in vistos if "limite" in v[1]]) == 1:
                self.send_response(429); self.end_headers(); self.wfile.write(b'{"retry_after": 0.01}'); return
            self.send_response(200); self.end_headers(); self.wfile.write(b'{"id": "42"}')

        def log_message(self, *a): pass

    srv = HTTPServer(("127.0.0.1", 0), S)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}/api/webhooks/1/tok"
    assert enviar(base, {"a": 1}) == ("42", None) and vistos[-1][:3] == ("POST", "/api/webhooks/1/tok?wait=true", "application/json") and vistos[-1][4].startswith("DiscordBot")
    assert enviar(base, {"a": 1}, editar="42") == ("42", None) and vistos[-1][:2] == ("PATCH", "/api/webhooks/1/tok/messages/42")
    assert enviar(base, {"a": 1}, capa=b"\x89PNGxyz")[0] == "42" and vistos[-1][2] == "multipart/form-data" and b"payload_json" in vistos[-1][3] and b"\x89PNGxyz" in vistos[-1][3] and b"capa.png" in vistos[-1][3]
    assert enviar(base.replace("tok", "limite"), {"a": 1}) == ("42", None) and len([v for v in vistos if v[1].endswith("limite?wait=true")]) == 2  # 429 e uma segunda tentativa
    assert enviar("http://127.0.0.1:1/x", {})[1] == "rede"
    vistos.clear()
    avisar(base, "andamento", casos["andamento"]); avisar(base, "andamento", casos["andamento"]); avisar(base, "fim", casos["fim"]); avisar(base, "andamento", casos["andamento"]); avisar(base, "pronto", pronto, capa=b"\xff\xd8jpg")
    _fila.join()
    assert [v[0] for v in vistos] == ["POST", "PATCH", "PATCH", "POST", "POST"] and vistos[2][1].endswith("/messages/42") and b"capa.jpg" in vistos[4][3], [v[:2] for v in vistos]  # o resumo fecha a mensagem; o proximo andamento abre outra
    assert teste(base.replace("tok", "t")) is None
    srv.shutdown()
    print("demo ok")


if __name__ == "__main__" and "--demo" in sys.argv:
    demo()
