r"""Confere as frases da pagina: os dois idiomas com as mesmas chaves, nenhuma chave usada que nao exista, nenhuma sobrando.

  python tools\check_i18n.py
"""
import json, re, sys
from pathlib import Path

SITE = Path(__file__).parent.parent / "site"
# chaves montadas na hora ("erro_" + codigo): a pagina nao as cita por inteiro, entao a lista fica aqui
MONTADAS = {"erro_": "geral recusado nao_existe sem_mapa grande tipo invalido link vazio ytdlp gerador ocupado sem_quest sem_adb sem_cabo sem_permissao sem_wifi adb",
            "passo_": "comecando baixando ouvindo golpes empacotando conferindo", "i_": "ffmpeg node padroes visor adb", "d_": "ffmpeg node padroes visor adb",
            "meta_": "esquema sem_notas paridade visao palmas empilhadas atravessadas grade folga_inicio folga_fim nps", "n_": "notas nps vel paredes arcos"}


def conferir():
    pt, en = (json.loads((SITE / "i18n" / f"{l}.json").read_text(encoding="utf-8")) for l in ("pt", "en"))
    fonte = "".join(p.read_text(encoding="utf-8") for p in [*SITE.glob("*.html"), *SITE.glob("*.js")])
    montadas = {p + c for p, cs in MONTADAS.items() for c in cs.split()}
    usadas = set(re.findall(r'data-t[pa]?="(\w+)"', fonte)) | montadas
    for args in re.findall(r"\bt\(((?:[^()]|\([^()]*\))*)\)", fonte):  # o que esta dentro de t(...): toda frase entre aspas e chave, menos a comparada com ===
        usadas |= set(re.findall(r'(?<!== )"([a-z][a-z0-9_]*[a-z0-9])"', args))
    citadas = set(re.findall(r'"(\w+)"', fonte)) | montadas  # chave passada por variavel (listas de [chave, valor]) aparece ao menos entre aspas
    erros = [f"so em pt: {k}" for k in pt.keys() - en.keys()] + [f"so em en: {k}" for k in en.keys() - pt.keys()]
    erros += [f"usada e nao existe: {k}" for k in sorted(usadas - pt.keys())] + [f"ninguem usa: {k}" for k in sorted(pt.keys() - citadas)]
    erros += [f"marcadores diferentes: {k}" for k in pt.keys() & en.keys() if set(re.findall(r"\{\w+\}", pt[k])) != set(re.findall(r"\{\w+\}", en[k]))]
    return erros


if __name__ == "__main__":
    erros = conferir()
    print("\n".join(erros) or "i18n ok")
    sys.exit(1 if erros else 0)
