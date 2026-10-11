# Plano do redesenho

Combinado com o dono em 10/10/2026. Objetivo: qualquer pessoa no Windows baixa a release, abre e usa, com uma interface bonita, em dois idiomas, e com a análise mais rápida.

## Estado

| Fatia | O que é | Estado | Documento |
|---|---|---|---|
| 1 | `start.bat`, tela de preparo, configuração, Quest por ADB | Feita em 10/10/2026 (commit `56172c6`). Pendências listadas no documento. | [slice-1.md](slice-1.md) |
| 2 | Redesenho da página, i18n em arquivos, relatório estruturado, lista estilo jogo | Feita em 10/10/2026 e aprovada pelo dono. | [slice-2-feito.md](slice-2-feito.md) (o plano: [slice-2.md](slice-2.md)) |
| 3 | Velocidade: medir, CUDA automático, modo rápido | Feita em 10/10/2026 e aprovada. Falta o dono decidir sobre o DirectML. | [slice-3-feito.md](slice-3-feito.md) (o plano: [slice-3.md](slice-3.md)) |
| 4 | Instalador `.exe` (Inno Setup) embrulhando o `start.bat`, montado e publicado pela CI | Feita em 10/10/2026, junto com link de playlist. **Instalador nunca testado numa máquina limpa.** | [slice-4-feito.md](slice-4-feito.md) |

Regra: uma fatia por vez. Ao terminar, atualize esta tabela, descreva o que foi verificado e o que não foi, e espere a aprovação do dono.

### Melhoria de UI/UX (depois das quatro fatias, a pedido do dono em 10/10/2026)

Sem redesenho: subir o nível do que existe, em três níveis, um por vez.

- **Nível 1 (feito, aguarda aprovação):** ações no topo da ficha (Quest ou Baixar em destaque, o resto no menu "⋯"), selo do veredito ao lado do título, aviso "Carregando o visualizador…" no lugar da caixa preta, apagar sem confirmar e com **Desfazer** (`POST /api/restaurar` traz da `saida\lixeira`), alvos de 40 px, e correção do nome e artista que não preenchiam na prévia do "Novo mapa" (um comentário engolia a linha em `app.js`). **Requer reiniciar o servidor** (endpoint novo). Verificado num servidor de teste com cópia de 3 mapas: abrir, menu, apagar, desfazer, 409 se já existe, selo rola até as conferências, 375 px sem rolagem lateral. **Não verificado:** com o Quest conectado (botão "Mandar ao Quest" em destaque), a barra de lote, e apagar vários.
- **Nível 2 (feito, aguarda aprovação):** busca (tecla `/`) e ordem na lista (aparecem com 5+ mapas; a ordem fica em `localStorage`; o lote só age no que a busca mostra), teclado na lista (setas, Espaço marca, Enter abre), "Novo mapa" em duas camadas (dificuldades, notas e modo rápido ficam em "Opções", com resumo ao fechar), cartão de geração em trilha de etapas no lugar da barra única, estado vazio com campo de link que leva ao diálogo, lista que encolhe de 372 para 290 px em larguras intermediárias. Só front-end, sem endpoint novo. Verificado num servidor de teste (9 mapas + 2 trabalhos falsos; e outro vazio): busca, ordem, teclado, trilha, campo da tela vazia, Opções com resumo, 980 px e 375 px sem rolagem lateral. **Não verificado:** a trilha com uma geração real do começo ao fim, e o inglês só passou pelo `check_i18n`, não pela vista.
- **Nível 3 (feito, aguarda aprovação):** transições curtas (a ficha ao trocar de mapa, o diálogo, o menu "⋯" e os avisos entram em vez de aparecer; `prefers-reduced-motion` desliga), um pontinho colorido por dificuldade em cada linha da lista (com o nome no `title`), e textos: "Regerar" virou "Refazer" em tudo (como o lote), "Trocar nome" virou "Renomear mapa", "Mandar os N que faltam ao Quest", duas mensagens de erro menos secas. Só front-end. Verificado: pontos com as cores certas, animações disparando na ficha, no diálogo e no menu, `check_i18n`. **Não verificado:** a aparência das animações a olho (só confirmei que rodam).
- **Início (depois do nível 3):** a tela sem mapa aberto deixou de ser só um título: "O que vamos jogar hoje?", números da biblioteca (mapas, minutos de música, conferências; o que falhou vira botão que ordena a lista por falhas; "no Quest" com o Quest conectado), e uma parede de capas com o último mapa aberto (`localStorage`, `beatloom.ultimo`) ou o mais recente em destaque, com um brilho borrado da capa ao fundo. A fila de geração mostra só as 2 primeiras que esperam (resto atrás de "Mostrar as outras N"), em linhas compactas, para não empurrar a lista de mapas para fora da tela. O botão "Seus mapas" e o logo voltam ao início (antes o botão só existia no celular). Captura nova em `docs/tela.jpg`. No celular o início não aparece (a lista já ocupa a tela). Verificado no servidor de teste com Edge headless e no painel do navegador; **não verificado:** com o Quest conectado e com mapas que falharam (os botões dos números).

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
| GPU | CUDA automático quando houver NVIDIA. Sem DirectML, **reaberta a pedido do dono na fatia 3 e ainda sem resposta dele** | A placa do dono é AMD RX 6600. Medido: o DirectML roda o Demucs com um remendo e ganha 1,3 a 1,5 vez só na separação (uns 20% do total), prendendo o torch em 2.4.1 com um pacote parado desde 2024. Números em [slice-3-feito.md](slice-3-feito.md) |
| Modo rápido | Opcional, completo por padrão, com aviso de perda de qualidade | Não piorar o mapa de quem não pediu |
| Fora de escopo | Terceiro idioma, tema claro, porta e pastas na config, Linux e Mac como alvo de usuário final | Ninguém pediu |

## Perguntas em aberto (são do dono)

1. **300 ou 1000 mapas na biblioteca.** Medido em três músicas: com 300 todas as conferências passam e o número de notas é o mesmo, mas o gerador usa menos trechos de 4 batidas e mais de 1 batida, principalmente em música rápida (Joseph, Expert+: trechos de 1 batida 89 → 167). Hoje está 1000 (`MAPAS` em `beatloom/preparo.py`). O dono ainda não escolheu.
2. **Apagar `dados\mapas` depois de montar a biblioteca.** São 2,4 GB que só servem para montar os `.pkl`. Na máquina do dono esse conjunto é usado para pesquisa, então não foi automatizado. Se for feito, precisa de uma condição que proteja quem já tinha os dados.
3. **RX 6600 pelo DirectML.** Adotar por uns 20% a menos no tempo total, tentar o caminho ONNX (não testado, projeto à parte) ou deixar como está. Detalhes em [slice-3-feito.md](slice-3-feito.md).

Fora das quatro fatias, a pedido do dono: link de playlist do YouTube (feito junto com a fatia 4) e `colab/beatloom.ipynb`, um caderno do Google Colab que gera em lote na GPU deles e guarda os zips e a biblioteca de padrões no Drive de quem roda. O mesmo caderno roda no Kaggle (lá guarda em `/kaggle/working/Beatloom` e lê a biblioteca de um Dataset anexado). **O caderno nunca rodou no Colab nem no Kaggle**: só a célula de geração foi ensaiada aqui, com o gerador trocado por um falso. Ele reaproveita `app.ytdlp` e `app.rodar`; ao mudar essas duas funções, lembre dele. Não contraria "só app local": cada pessoa roda na própria conta, não há serviço hospedado.

Depois das fatias, a pedido do dono (10/10/2026): preferências de quem joga (`sem_topo`, `sem_fila` em `beatloom.json`, `--prefs` no `generate.py`, aplicadas como barreira no motor), fila que pausa, esvazia e é guardada em `.cache\fila.json`, "Refazer as notas" de vários mapas pela fila (`POST /api/regerar` com `zips`), "Marcar todos" e "Mandar ao Quest os N que faltam". Corrigido também o bloqueio de visão que passava no motor e falhava na conferência por arredondamento no limite do intervalo (`FOLGA_VB` em `beatloom/checks.py`). Medido em duas músicas: com as duas preferências o Expert+ perde até 3% das notas e os braços cruzados dobram (26 → 52 e 27 → 69); todas as conferências passam. **Os botões novos da página não foram vistos num navegador**, só o servidor foi testado.

Playlist no jogo (a pedido do dono, 10/10/2026): com um link de playlist, a caixa "Criar também a playlist no jogo" manda `playlist: {id, nome}` em `POST /api/gerar`, que anota as faixas em `saida\playlists.json`. O `.bplist` nunca é guardado: `quest.bplist` monta na hora com os mapas que existem (o código de cada mapa é o SHA-1 do Info.dat mais as dificuldades, e muda quando o mapa é refeito). `POST /api/quest` manda junto as playlists, cada uma só com os mapas dela que estão no Quest; `GET /api/bplist?id=` baixa; `POST /api/playlist/apagar` esquece. Na lista, cada playlist é uma linha: o nome marca os mapas dela. `POST /api/playlist/mapas` (`id` ou `nome` para uma nova, `zips`, `tirar`) põe mapas à mão (`extras`, pelo nome do zip, depois das faixas) ou tira; pela página, "Adicionar à playlist" e "Tirar da playlist" na barra dos marcados. Verificado num servidor de teste com 4 mapas reais: anotar, `/api/estado`, baixar o `.bplist`, marcar pela linha, esquecer. **Não verificado:** nada no Quest (estava desligado): a pasta do mod (`PlaylistCore` ou `PlaylistManager`, a que existir em `Mods`; não achei fonte que confirme) e se o jogo casa os códigos; e a caixa no diálogo com um link de playlist de verdade.

Avisos no Discord (a pedido do dono, 10/10/2026): `beatloom/discord.py`, `discord_url` e `discord_eventos` em `beatloom.json` (a página só vê o fim do endereço), frases `dc_*` em `site/i18n`. Uma mensagem de andamento editada a cada música (fila com 3+), cartão por mapa pronto, erro e resumo final; `POST /api/discord/teste`. Também `start-bandeja.bat` (`tools/bandeja.ps1`). Verificado: `--demo` (limites do Discord, pt/en, servidor falso com 429), fila falsa no `operario`, página, bandeja numa porta de teste, e o teste real no webhook do dono. **Não verificado:** a aparência final de cada cartão no Discord além do teste, o ícone na bandeja a olho, `start.bat bandeja` de ponta a ponta.

Envio ao Quest em segundo plano (a pedido do dono, 10/10/2026): `POST /api/quest` volta na hora e o `enviador` (thread em `app.py`) esvazia a fila, um mapa por vez, e depois manda as playlists; a fila vai em `/api/estado` (`envio`). `POST /api/quest/limpar` fecha o resultado ou, com `cancelar`, tira o que ainda espera. `quest.enviar` aceita `andamento(0..1)`: o `adb push` sem terminal não conta, então de segundo em segundo se pergunta ao Quest o `du -sk` da pasta `.part`. Na página: cartão no alto da lista (barra geral, mapa de agora com %, falhas com detalhe, Cancelar/Fechar), tag e barra fina na linha de cada mapa, um aviso-resumo no fim. O card dos marcados ganhou hierarquia (Quest cheio; playlist e refazer em contorno; cancelar e apagar só texto). Verificado num servidor de teste com `quest.enviar` falso (4 mapas, um falhando). **Não verificado:** com o Quest de verdade, em particular se `du -sk` responde direito no Android (se não responder a barra de cada mapa fica parada em 0 e o geral continua andando).

O que vem depois está em [../ROADMAP.md](../ROADMAP.md).

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

`app.py` importa `generate`, que importa `numpy`; `torch`, `demucs` e `beat_this` só são importados quando uma análise roda. `/api/config` devolve `placa` falso quando o torch não está instalado.

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
beatloom/audio.py    análise: batidas (beat_this), ataques (librosa), instrumentos (Demucs), voz cantada (pYIN), peças da bateria, partes da música, clima, cache
beatloom/engine.py   escolha dos golpes a partir da biblioteca de padrões
beatloom/luzes.py    luzes (deixas, eventos básicos e grupos de luzes), cores da capa e cenário por clima
beatloom/mods.py     mods opcionais, por último sobre o mapa pronto: cores do Chroma nas luzes e o conjunto a mais do Noodle Extensions
beatloom/checks.py   regras de jogabilidade (paridade, bloqueio de visão, palmas...)
beatloom/preparo.py  o que falta instalar e os downloads da primeira vez
beatloom/quest.py    ADB: parear, listar, enviar, apagar
site/app.html        a marcação da página; app.css o visual; app.js o comportamento
site/i18n/           as frases: pt.json e en.json (tools/check_i18n.py confere)
site/fonts/          Bricolage Grotesque e Instrument Sans (OFL)
installer/           beatloom.iss (Inno Setup) e o ícone; .github/workflows/release.yml monta e publica ao subir uma tag v*
colab/               beatloom.ipynb: geração em lote no Google Colab ou no Kaggle
check/               validador de formato com a biblioteca bsmap (Node)
tools/               biblioteca de padrões, teste cego, lote, medição de tempo (timing.py)
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
