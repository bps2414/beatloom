# Beatloom

Gerador de mapas de Beat Saber por regras, com site local. Público: qualquer pessoa no Windows, inclusive leiga. Ela baixa a release, dá dois cliques em `start.bat` e usa, sem instalar nada por fora.

## Trabalho em andamento

Há um redesenho combinado em quatro fatias. **Antes de qualquer coisa leia [docs/plan/README.md](docs/plan/README.md)**; ele diz o estado de cada fatia e aponta o documento de cada uma.

- "comece slice 2" (ou "fatia 2") quer dizer: leia `docs/plan/README.md` e `docs/plan/slice-2.md` e execute.
- Uma fatia por vez. Ao terminar uma, atualize o estado em `docs/plan/README.md`, pare e espere o dono aprovar antes da próxima.
- O dono pediu para não usar subagentes neste trabalho.
- Decisões já tomadas estão em `docs/plan/README.md`. Não as reabra; se uma parecer errada, diga e pergunte.

## Convenções do código

- Nomes de variáveis, funções, comentários e saída de terminal em português sem acento. Mantenha.
- Linhas longas e densas, comentário curto dizendo o porquê. Leia o arquivo antes de editar e imite o estilo.
- Servidor só com a biblioteca padrão do Python (`http.server`). Página em HTML, CSS e JS puros, sem etapa de build e sem framework.
- Nada de dependência nova para o que poucas linhas resolvem.
- Cada lógica não trivial deixa um teste mínimo executável no próprio arquivo: uma função `demo()` com `assert`, chamada por `--demo`.
- Toda frase que o usuário lê existe em pt-BR e em inglês, em `site/i18n/pt.json` e `en.json`. O servidor só devolve códigos e números.
- Mensagens de commit em português, uma linha descrevendo o que mudou, sem linhas de atribuição.

## Rodar e conferir

```
start.bat                                   Windows: instala o que falta e abre http://localhost:8777
.venv\Scripts\python app.py --sem-navegador  só o servidor
python generate.py --demo
python -m beatloom.preparo --demo
python -m beatloom.checks --demo
python tools/extract_patterns.py --demo
python report.py --demo
python tools/timing.py --demo               (tools/timing.py <audio> mede cada etapa da geração)
python tools/check_i18n.py                   frases: mesmas chaves nos dois idiomas, nenhuma faltando ou sobrando
```

Em Linux (sessão na nuvem) veja "Ambiente na nuvem" em [docs/plan/README.md](docs/plan/README.md): lá não existem os padrões, as músicas, os mapas gerados nem o Quest.

## Não fazer

- Não versionar `dados/`, `saida/`, `musicas/`, `bin/`, `arcviewer/`, `beatloom.json` (já estão no `.gitignore`). Mapas e músicas têm áudio protegido.
- Não embutir a biblioteca de padrões no repositório nem na release: ela deriva de mapas de outros mappers.
- Não hospedar o gerador como serviço público.
