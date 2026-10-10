# Fatia 4: instalador pela CI, e link de playlist

Feita em 10/10/2026. O resumo do plano está no fim de [README.md](README.md).

## O que mudou

1. `installer\beatloom.iss` (Inno Setup 6): copia os arquivos do repositório para `%LOCALAPPDATA%\Beatloom`, sem administrador, cria atalho no menu Iniciar e (opcional) na área de trabalho apontando para `start.bat`, com ícone próprio (`installer\beatloom.ico`), em inglês e português. Não embute Python, torch nem padrões. O desinstalador pergunta se os mapas de `saida\` ficam e apaga o resto, inclusive o que o app baixou.
2. `.github\workflows\release.yml`: ao subir uma tag `v*`, um runner Windows monta o `beatloom-setup.exe` e publica a release, com as notas tiradas das mensagens de commit desde a tag anterior. O dono pediu para não montar no PC dele. Não há `CHANGELOG.md` no repositório: o changelog é o texto de cada release.
3. Link de playlist do YouTube: a prévia reconhece (`/api/previa` devolve `lista`), a página diz quantas faixas são e `POST /api/gerar` com `lista` cria um trabalho por faixa. `/api/estado` devolve a fila inteira; trabalho na fila ganhou o botão de dispensar; no meio de uma fila a página não abre sozinha cada mapa que termina, só o último. Link de vídeo com `&list=` continua sendo só o vídeo.

## Verificado

- Playlist pública de 182 faixas: prévia pelo servidor e pela página, fila criada, dispensar um item da fila. Link de vídeo com `&list=` devolve só o vídeo.
- `--demo` de sempre e `tools/check_i18n.py`.
- A execução da CI na primeira tag (veja a aba Actions).

## Não verificado

- **O instalador numa máquina Windows limpa** (o critério de aceite do plano): instalar, abrir pelo atalho, passar pelo preparo, gerar um mapa, desinstalar mantendo e não mantendo os mapas. Aqui não há Inno Setup nem máquina limpa; a CI só prova que o script compila.
- Uma playlist rodando até o fim (download e geração de cada faixa). Cada faixa segue o mesmo caminho de um link só, que não mudou.
- Faixa privada ou apagada no meio da playlist: deve virar um cartão de erro e a fila segue.

## Limites conhecidos

- O `.exe` não é assinado: o SmartScreen avisa (explicado nos READMEs).
- Uma playlist grande no modo completo leva horas (uns 1 a 3 minutos por música neste PC); o modo rápido é o indicado.
- A fila vive na memória: fechar o Beatloom perde o que ainda não rodou.
