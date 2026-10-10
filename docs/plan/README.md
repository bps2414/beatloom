# Plano do redesenho

Combinado com o dono em 10/10/2026. Objetivo: qualquer pessoa no Windows baixa a release, abre e usa, com uma interface bonita, em dois idiomas, e com a análise mais rápida.

## Estado

| Fatia | O que é | Estado | Documento |
|---|---|---|---|
| 1 | `start.bat`, tela de preparo, configuração, Quest por ADB | Feita em 10/10/2026 (commit `56172c6`). Pendências listadas no documento. | [slice-1.md](slice-1.md) |
| 2 | Redesenho da página, i18n em arquivos, relatório estruturado, lista estilo jogo | Feita em 10/10/2026. **Esperando a aprovação do dono.** | [slice-2-feito.md](slice-2-feito.md) (o plano: [slice-2.md](slice-2.md)) |
| 3 | Velocidade: medir, CUDA automático, modo rápido | **A fazer. É a próxima**, depois da 2 aprovada | [slice-3.md](slice-3.md) |
| 4 | Instalador `.exe` (Inno Setup) embrulhando o `start.bat` | A fazer, por último | Resumo no fim deste arquivo |

Regra: uma fatia por vez. Ao terminar, atualize esta tabela, descreva o que foi verificado e o que não foi, e espere a aprovação do dono.

## Decisões tomadas (não reabrir)

| Assunto | Decisão | Motivo |
|---|---|---|
| Público | Terceiros no Windows, inclusive leigos | O dono quer que qualquer pessoa use |
| Como abrir | `start.bat` de dois cliques, que baixa o uv, o Python e os pacotes para a pasta do projeto | Executável com torch teria uns 2 GB e é frágil |
| Dependências | A página baixa tudo para dentro da pasta (`bin\`, `arcviewer\`, `dados\`), com barra. Nada de mandar o usuário instalar programa | O dono pediu "sem depender de baixar nada externo" |
| Biblioteca de padrões | Baixada no preparo (1000 mapas, uns 20 min). Não vai na release | Deriva do trabalho de outros mappers |
| Hospedagem | Só app local. Sem site hospedado, sem página de apresentação | Custo de processamento; yt-dlp num servidor público tem risco de direito autoral e o YouTube bloqueia datacenter; o Quest só é alcançável na rede local |
| Quest | ADB dentro do repositório, com pareamento por cabo, indicador, marca de enviado, apagar e envio de vários | Antes dependia de um script fora do repositório |
| Config | `beatloom.json` na raiz, fora do git | `config.json` na raiz é do BeatKenja |
| Tecnologia da página | HTML, CSS e JS puros, sem build, fontes embutidas (sem Google Fonts) | Servidor é biblioteca padrão; precisa funcionar sem internet |
| Visual | Escuro, tipo palco, vermelho e azul dos sabres como destaque. Sem tema claro | O visualizador 3D é escuro |
| Estrutura da tela | Biblioteca à esquerda, detalhe com visualizador à direita, "Novo mapa" em painel, config no topo | Escolhido pelo dono entre três esboços |
| Lista estilo jogo | A própria lista "Seus mapas" é desenhada como a lista de músicas do Beat Saber. Não é tela separada. Inspirada, sem copiar fonte nem logotipo do jogo | Tela só de enfeite não teria função |
| i18n | pt-BR e inglês, em arquivos separados. O servidor devolve códigos e números; o relatório vira dados e a página escreve no idioma | Hoje o relatório só existe em português |
| Progresso | Etapas nomeadas com barra real na separação de instrumentos. Sem tempo estimado | Estimativa erra e irrita |
| Aprovação visual | Fazer direto, sem protótipo; o dono ajusta no produto funcionando | Escolha do dono |
| GPU | CUDA automático quando houver NVIDIA. Sem DirectML | A placa do dono é AMD RX 6600; DirectML prende o torch em versão antiga e provavelmente não roda o Demucs |
| Modo rápido | Opcional, completo por padrão, com aviso de perda de qualidade | Não piorar o mapa de quem não pediu |
| Fora de escopo | Terceiro idioma, tema claro, porta e pastas na config, Linux e Mac como alvo de usuário final | Ninguém pediu |

## Perguntas em aberto (são do dono)

1. **300 ou 1000 mapas na biblioteca.** Medido em três músicas: com 300 todas as conferências passam e o número de notas é o mesmo, mas o gerador usa menos trechos de 4 batidas e mais de 1 batida, principalmente em música rápida (Joseph, Expert+: trechos de 1 batida 89 → 167). Hoje está 1000 (`MAPAS` em `beatloom/preparo.py`). O dono ainda não escolheu.
2. **Apagar `dados\mapas` depois de montar a biblioteca.** São 2,4 GB que só servem para montar os `.pkl`. Na máquina do dono esse conjunto é usado para pesquisa, então não foi automatizado. Se for feito, precisa de uma condição que proteja quem já tinha os dados.

## Ambiente na nuvem (Linux, repositório recém-clonado)

O que **não existe** num clone: `dados/` (padrões), `saida/` (mapas), `musicas/`, `arcviewer/`, `bin/`, `.venv/`, `beatloom.json`, Quest. Consequências:

- A geração de verdade não roda sem a biblioteca de padrões (`dados/padroes_<dif>.pkl`). Baixá-la leva uns 20 minutos, 2,4 GB e depende de acesso de rede a `api.beatsaver.com`. Para a fatia 2 isso não é necessário.
- O `start.bat` e os downloads de `beatloom/preparo.py` são de Windows. No Linux, `ffmpeg`, `ffprobe` e `node` do sistema já satisfazem a tela de preparo.

Preparação mínima para trabalhar na página (fatia 2):

```
python3.12 -m venv .venv
.venv/bin/pip install numpy scipy soundfile librosa yt-dlp
sudo apt-get install -y ffmpeg nodejs npm   # se faltarem
(cd check && npm ci)
.venv/bin/python app.py --sem-navegador      # http://localhost:8777
```

`app.py` importa `generate`, que importa `numpy`; `torch`, `demucs` e `beat_this` só são importados quando uma análise roda. `/api/config` devolve a versão do torch vazia quando o pacote não está instalado.

A tela de preparo trava no passo 2 enquanto faltar item obrigatório. `preparo.tem("padroes")` só confere se os cinco arquivos existem, então para trabalhar na interface basta criar arquivos vazios (ficam fora do git):

```
mkdir -p dados && for d in Easy Normal Hard Expert ExpertPlus; do : > dados/padroes_$d.pkl; done
```

Mapas para a página mostrar: `tools/fixture.py` (mapa de mentira com áudio sintético, especificado em [slice-2.md](slice-2.md), passo 0) não foi criado, porque a fatia 2 foi feita na máquina do dono, que tem mapas de verdade. Crie-o se for trabalhar na nuvem.

O que só o dono consegue testar, na máquina dele (Windows, RX 6600, Quest): geração real de ponta a ponta, `start.bat`, downloads reais do preparo, envio ao Quest, visualizador ArcViewer com mapa real. Liste isso no relatório final de cada fatia como "não verificado aqui".

## Mapa do repositório

```
start.bat            instala o que falta (uv, Python, pacotes) e abre a página
app.py               servidor HTTP local, todas as rotas /api
generate.py          gera um mapa (CLI); app.py o chama como subprocesso
report.py            confere um mapa e escreve o relatório
beatloom/audio.py    análise: batidas (beat_this), ataques (librosa), instrumentos (Demucs), cache
beatloom/engine.py   escolha dos golpes a partir da biblioteca de padrões
beatloom/checks.py   regras de jogabilidade (paridade, bloqueio de visão, palmas...)
beatloom/preparo.py  o que falta instalar e os downloads da primeira vez
beatloom/quest.py    ADB: parear, listar, enviar, apagar
site/app.html        a marcação da página; app.css o visual; app.js o comportamento
site/i18n/           as frases: pt.json e en.json (tools/check_i18n.py confere)
site/fonts/          Bricolage Grotesque e Instrument Sans (OFL)
check/               validador de formato com a biblioteca bsmap (Node)
tools/               biblioteca de padrões, teste cego, lote
docs/ARCHITECTURE*   como o gerador funciona
```

## Fatia 4: instalador `.exe` (resumo)

Depende de a fatia 1 estar estável no uso real.

- Inno Setup. O instalador copia os arquivos do repositório para `%LOCALAPPDATA%\Beatloom` (pasta gravável sem administrador, porque o app baixa coisas para dentro dela) e cria atalho no menu Iniciar e na área de trabalho apontando para `start.bat`, com ícone próprio.
- Não embute Python, torch nem padrões: quem baixa é o `start.bat` e a tela de preparo, como hoje.
- O desinstalador apaga a pasta inteira depois de perguntar se os mapas em `saida\` devem ficar.
- O `.exe` não é assinado; o Windows SmartScreen vai avisar. Documentar isso no README com a captura do aviso e manter o zip como alternativa.
- O script `.iss` fica em `installer\beatloom.iss`, com um comando no README para compilar. Compilar exige Windows.
- Critério de aceite: numa máquina Windows sem Python, instalar, abrir pelo atalho, passar pelo preparo e gerar um mapa.
