# Fatia 3: velocidade da análise (feita, com uma decisão em aberto)

Feita em 10/10/2026, na máquina do dono (Ryzen 5 5500, 6 núcleos, RX 6600, torch 2.14.1 de CPU). O plano está em [slice-3.md](slice-3.md).

## O que mudou

1. `tools/timing.py` mede cada etapa da geração com o cache de análise desligado. (O plano chamava de `tools/profile.py`; esse nome esconderia o módulo `profile` do Python, que o torch importa.)
2. Modo rápido: uma chave no diálogo de novo mapa e o padrão na configuração (`beatloom.json`, chave `modo`: `completo` ou `rapido`). `POST /api/gerar` aceita `modo`; rápido gera com `--etapa 3`, sem separar instrumentos. O mapa sai como `<nome>-v3.zip` e leva a marca "modo rápido" na lista.
3. Regerar uma dificuldade usa a etapa do próprio mapa (lida de `_songSubName`); antes era sempre a 4.
4. A conferência não ouve mais a música de novo: `analisar()` sem instrumentos reaproveita `analise_inst.json` quando ele existe. As chaves comuns dos dois arquivos são iguais (conferido nas 14 músicas do cache).
5. Placa NVIDIA: `beatloom/audio.py` ganhou `dispositivo()` (`cuda` se o torch instalado tem, senão `cpu`) e `na_placa(f)`, que refaz no processador se a placa falhar. As batidas (beat_this) e a separação (Demucs) passam por ela.
6. A configuração diz "A análise usa o processador" ou "…a placa de vídeo NVIDIA" no lugar da versão do torch (`/api/config`: `placa`, tirado do nome da versão instalada, sem importar o torch no servidor).
7. A etapa "ouvindo" mostra "Separando os instrumentos 37%" enquanto a barra anda.

## Medições

Tempo total de gerar e conferir as cinco dificuldades, análise fora do cache.

| Música | Modo | Antes | Depois | Separação de instrumentos |
|---|---|---|---|---|
| Koro Disco (1:43) | completo | 77,5 s | 62,2 s | 57,0 s → 43,6 s |
| Joseph (4:17) | completo | 148,0 s | 171,7 s | 105,7 s → 129,6 s |
| Koro Disco (1:43) | rápido | 12,3 s | | não tem |
| Joseph (4:17) | rápido | | 24,7 s | não tem |

Leitura honesta: a separação é de 70 a 75% do tempo e **varia uns 20% de uma rodada para outra na mesma máquina** (uma música ficou mais rápida e a outra mais lenta, sem que o código da separação tenha mudado). O único ganho de código no modo completo é a conferência: de 4,4 s para 1,3 s (Koro) e de 10,8 s para 0,8 s (Joseph), que some dentro desse ruído. O ganho grande é o modo rápido, umas 6 vezes.

O resto do tempo, na Joseph: batidas 8 a 12 s, ataques 10 s (cinco vezes: a música e os quatro instrumentos), compassos 9 s, golpes 2 s, todo o resto abaixo de 2 s.

### Ajustes de CPU testados e não adotados

- **Threads do torch.** Já usa 6 (os núcleos físicos). Com 12 a separação da Koro levou 44,5 s contra 38,9 a 42,4 s com 6. Fica como está.
- **Juntar pedaços num lote.** Um pedaço de 7,8 s leva 2,25 s sozinho e 2,5 a 2,8 s por pedaço em lotes de 4 e 8. Pior.
- **Parâmetros e modelo do Demucs** não foram mexidos: mudam as faixas separadas e, com elas, os mapas.
- **Ler o áudio uma vez** (`librosa.load`): 1,4 s no total. Não vale a mudança.

## RX 6600 (AMD) pelo DirectML: testado, não adotado, decisão do dono

O dono pediu para reabrir. Testado num ambiente separado (`torch-directml` 0.2.5, que obriga torch 2.4.1), com a separação da Koro Disco:

| Onde | Tempo |
|---|---|
| RX 6600 pelo DirectML | 26,6 s e 31,0 s (duas rodadas) |
| Processador, mesmo torch 2.4.1 | 37,5 s e 39,6 s |
| Processador, torch 2.14.1 (o de hoje) | 38,9 s a 44,5 s |

- Funciona, com um remendo: o DirectML não tem números complexos, então três métodos do modelo (`_spec`, `_mask`, `_ispec`) precisam rodar no processador. Sem isso o processo cai.
- O resultado é o mesmo da CPU (diferença máxima de 0,00003 com a mesma semente).
- O ganho é de 1,3 a 1,5 vez só na separação, ou uns 20% no tempo total. Lote maior não ajuda (1,5 a 1,8 s por pedaço na placa contra 2,2 a 2,8 s no processador).
- O custo: o `torch-directml` não recebe versão nova desde setembro de 2024 e prende o torch em 2.4.1; o `start.bat` teria de detectar placa AMD e instalar outro conjunto de pacotes; o remendo mexe por dentro do Demucs; o beat_this não foi testado com esse torch.

Recomendação: não adotar por 20%. Se o dono quiser mesmo assim, é um dia de trabalho com esses riscos. Um caminho que pode render mais (não testado): exportar o modelo para ONNX e rodar com `onnxruntime-directml`, que é mantido; é um projeto à parte.

## Verificado

- Modo rápido de ponta a ponta pelo servidor: gerou `-v3.zip` em 6 s (trecho de 45 s), conferências aprovadas, e regerar uma dificuldade desse mapa funcionou na etapa 3.
- A chave "Modo rápido" e a frase do que se perde aparecem no diálogo e na configuração, nos dois idiomas; a configuração mostra "A análise usa o processador".
- Geração no modo completo depois das mudanças, com todas as conferências (as duas medições acima).
- `--demo` de `generate.py`, `report.py`, `beatloom.preparo`, `beatloom.checks`, `tools/extract_patterns.py`, `tools/timing.py`, e `tools/check_i18n.py`.

## Não verificado

- **O caminho da placa NVIDIA.** Ninguém envolvido tem uma. O código está escrito (`dispositivo()`, `na_placa()`), mas nunca rodou em `cuda`, nem a volta para o processador quando a placa falha.
- Mapas idênticos antes e depois numa geração do zero: não dá para comparar, porque o Demucs sorteia um deslocamento a cada rodada e as faixas separadas mudam um pouco de uma vez para outra (isso já era assim; o cache esconde). Com a análise no cache nada do que mudou toca as notas.

## Pendências

1. Decidir sobre o DirectML (acima).
2. Pedidos novos do dono, fora desta fatia: aceitar link de playlist do YouTube; um caderno do Google Colab para gerar em lote na GPU deles (o caminho `cuda` desta fatia serve; o YouTube costuma bloquear download vindo de datacenter, então talvez precise subir os arquivos).
