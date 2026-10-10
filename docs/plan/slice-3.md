# Fatia 3: velocidade da análise (a fazer, depois da fatia 2 aprovada)

Leia antes: [README.md](README.md). O código envolvido está quase todo em `beatloom/audio.py`.

## Objetivo

A geração de um mapa novo leva minutos. Encurtar essa espera sem piorar o mapa de quem não pediu, e dar a quem quer pressa uma opção rápida e honesta sobre o que perde.

## Fatos

- A placa do dono é uma AMD RX 6600 e o processador um Ryzen 5 5500 (6 núcleos), 16 GB de RAM. CUDA só existe para NVIDIA; na máquina dele o ganho vem de CPU e do modo rápido.
- O `start.bat` já instala o torch com CUDA quando há NVIDIA (`uv pip install --torch-backend auto`). O código ainda pede `device="cpu"` em dois lugares, então hoje a GPU não é usada nem por quem tem.
- DirectML foi descartado (prende o torch numa versão antiga e provavelmente não roda o Demucs por causa das operações com números complexos). Não reabrir sem pedido.
- A análise fica em cache por conteúdo do áudio (`.cache/analise/<hash>/`): só a primeira geração de cada música é lenta. Regerar uma dificuldade já é rápido.

## Passo 1: medir antes de mexer

Sem medida, nada de otimização. Crie `tools/profile.py` que roda a análise completa de um áudio com o cache desligado (pasta temporária) e imprime o tempo de cada etapa:

| Etapa | Onde |
|---|---|
| Conversão para wav | `analisar()`, chamada do ffmpeg |
| Batidas | `File2Beats(...)` do beat_this |
| Ataques e compassos da mixagem | `_ataques`, `_compassos`, `librosa.load` |
| Separação de instrumentos | `_separar` (Demucs `htdemucs`) |
| Ataques por instrumento | laço sobre as quatro faixas em `analisar()` |
| Notas longas | `sustentados()` |
| Escolha de tempos e golpes, por dificuldade | `generate.gerar()` |
| Conferência | `report.relatorio()` (inclui o Node) |

Rode em duas ou três músicas de durações diferentes, na máquina do dono, e registre a tabela em `slice-3-feito.md`. A suspeita é que a separação seja quase todo o tempo; confirme.

## Passo 2: usar a GPU quando houver

- Uma função em `beatloom/audio.py` que devolve `"cuda"` se `torch.cuda.is_available()` e `"cpu"` senão. Passe o resultado para `File2Beats(device=...)` e para `apply_model(device=...)`; no Demucs o tensor de entrada e o modelo vão para o dispositivo e a saída volta para a CPU antes de gravar.
- Se a GPU falhar no meio (memória insuficiente é o caso comum), refaça na CPU e avise na saída. Não deixe a geração morrer por isso.
- A configuração mostra o dispositivo em uso ("GPU NVIDIA" ou "processador") no lugar da versão crua do torch.
- O resultado na GPU pode diferir do da CPU em casas decimais, e o cache guarda o que foi calculado primeiro. Isso é aceitável; registre no documento final.
- Ninguém envolvido tem NVIDIA. Deixe o caminho escrito e diga claramente no relatório que não foi testado em GPU, a menos que alguém teste.

## Passo 3: modo rápido

- "Rápido" = gerar com `--etapa 3`: sem separação de instrumentos. O usuário perde: as notas fortes seguindo a bateria, as notas seguradas (arcos) e as paredes. A página precisa dizer isso em uma frase, nos dois idiomas, perto do controle.
- Onde aparece: uma chave no diálogo de novo mapa e o padrão na configuração (`beatloom.json`, chave `modo`: `"completo"` ou `"rapido"`, padrão `"completo"`). `gravar_config()` valida.
- `POST /api/gerar` aceita `modo`; `app.rodar()` passa `--etapa 3` ou `4`. O nome do arquivo já leva a etapa (`-v3.zip`), então os dois modos da mesma música não se sobrescrevem; a lista mostra qual é qual (o subtítulo do mapa já diz `auto v3`).
- Regerar uma dificuldade usa a etapa do próprio mapa. Hoje `/api/regerar` sempre gera na etapa 4 e procura `regerar-v4.zip`: corrija para ler a etapa do mapa.
- Meça e mostre o ganho real ("uns 30 segundos em vez de 4 minutos", com os números medidos, não com esses).

## Passo 4: ajustes de CPU, guiados pela medição

Só faça o que a medição justificar. Cada ajuste precisa de um antes e depois em tempo e de uma prova de que o mapa não mudou (compare os arquivos `.dat` gerados) ou, se mudar, de quanto.

Candidatos, em ordem de suspeita:

1. **Threads do torch.** Confira `torch.get_num_threads()` na máquina; teste `torch.set_num_threads()` com o número de núcleos físicos.
2. **Carregar o áudio uma vez.** `analisar()`, `_ataques` por instrumento e `sustentados()` chamam `librosa.load` com reamostragem para 22050 Hz várias vezes. Reamostrar é lento; veja quanto pesa.
3. **Parâmetros do Demucs** (`split`, `overlap=0.1`, `segment`). Mudam o resultado da separação, logo os mapas. Só mexa se o ganho for grande, e trate como mudança de qualidade: compare os relatórios das músicas de referência antes e depois.
4. **Modelo menor.** Trocar `htdemucs` por outro modelo muda a qualidade da separação. Mesma regra do item 3.
5. **Conferência.** `report.relatorio()` roda `analisar()` de novo (sem instrumentos) e chama o Node. Veja se vale reaproveitar a análise que acabou de ser feita.

O que não vale: paralelizar gerações (a análise já usa o processador inteiro), reduzir a qualidade por padrão.

## Critérios de aceite

- Tabela de tempos por etapa, antes e depois, em pelo menos duas músicas, na máquina do dono.
- Modo completo: mapas idênticos aos de antes, ou diferença descrita e aprovada pelo dono.
- Modo rápido funcionando de ponta a ponta pela página, com o aviso do que se perde, nos dois idiomas.
- Em máquina sem GPU nada muda de comportamento além do tempo.
- `--demo` de todos os arquivos passa; o teste de i18n passa com as chaves novas.
- READMEs e `docs/ARCHITECTURE*` atualizados; estado em [README.md](README.md); `slice-3-feito.md` com o que foi verificado e o que não foi (GPU incluída).

## Armadilhas

- A chave do cache é o hash do `song.egg`, que é gerado com `-fflags +bitexact` para a mesma música dar sempre o mesmo arquivo. Não quebre isso.
- `analise.json` (sem instrumentos) e `analise_inst.json` (com) são caches separados. O modo rápido usa o primeiro.
- `.cache/torch` e `.cache/hf` guardam os modelos baixados; ficam fora do "apagar análises guardadas".
- Medir com o cache quente não mede nada: use pasta temporária ou um áudio novo.
