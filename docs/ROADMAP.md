# Roadmap

O que falta. O que já foi feito, com os números de cada mudança, está em [RESULTADOS.md](RESULTADOS.md); as decisões do redesenho estão em [plan/README.md](plan/README.md).

## Onde está

| Bloco | O que é | Estado |
|---|---|---|
| 1.0 | Medir "melhor" (`tools/medir.py`) | Feito o mínimo. Falta o conjunto com mapa humano, o teste cego e comparar com outros geradores |
| 1.1 | Detector: voz, bateria por peça, partes da música, força, BPM variável | Feito |
| 1.2 | Golpes mais humanos: contexto, variação, pilhas, braços cruzados, peso por qualidade | Feito |
| 1.3 | Mapa mais bonito: luzes, cores da capa, cenário, arcos, correntes, bombas, paredes, Chroma, Noodle Extensions | Feito, menos os itens 8, 9 e 11 |
| 1.4 | Pesquisar ferramentas de terceiros | Não começado |

Nas 18 músicas de teste todas as conferências passam. **Quase nada disso foi visto no jogo.** É o que mais falta, e só o dono consegue fazer.

## 1. Ver no jogo

Antes de qualquer item novo. Cada linha é uma coisa que passa na conferência mas ninguém viu:

- Correntes, bombas de reinício, paredes de desviar e de agachar.
- Luzes dos cenários novos (The Second, Rock Mixtape, Weave), que são o maior risco: se um sair apagado, tirar ele de `AMBIENTE` em `beatloom/luzes.py` devolve as músicas ao cenário clássico.
- Cores da capa nas luzes e, com a chave ligada, nos sabres e notas.
- Eventos de BPM em música de andamento variável (a grade no jogo e no ArcViewer).
- Chroma: cor nos eventos de transição. Noodle Extensions: a posição das barras, se 120 paredes pesam no Quest.
- Torre (uma por mapa no Expert e no Expert+) e refrão espelhado: se incomodam ou se o refrão continua reconhecível.

## 2. Gerador: o que falta

- **Medir contra gente (1.0).** Conjunto fixo de umas 10 músicas com mapa humano bem avaliado, teste cego do dono (`tools/blind_test.py`) e as mesmas músicas no Beat Sage e no TopMapper.
- **Um Sabre, Sem Setas, 360 e 90 graus (1.3 item 8).** Sem Setas é o mais barato. Só se o dono jogar esses modos.
- **Velocidade por trecho (1.3 item 9).**
- **Escolher o que vai no mapa (1.3 item 11).** No diálogo de mapa novo: modos de jogo e chaves para bombas, paredes, luzes. Só aparece o que o gerador já sabe fazer.
- **Chroma, o que ficou de fora.** Acender luzes uma a uma, cor por nota, mexer no cenário. Só depois de ver o Chroma atual no jogo.
- **Ficha do mapa.** Mostrar arcos, correntes, bombas e paredes, as cores do mapa, o conjunto Lawless e o resultado da conferência dele.

### 1.4 Ferramentas de terceiros a aproveitar

- [BeatSaber-JSMap](https://github.com/KivalEvan/BeatSaber-JSMap) (o pacote `bsmap`) já é usado em `check\` para validar o formato, e as regras de paridade e de mapa em `beatloom/checks.py` foram portadas dele e do BeatSaber-MapCheck. Falta aproveitar: as outras checagens do MapCheck que ainda não foram portadas, e a conversão de formato (gravar em v4).
- Estimadores de dificuldade da comunidade (estrelas do BeatLeader e do ScoreSaber) para calibrar se o nosso Expert+ é mesmo um Expert+.
- **Pesquisar o que mais existe** (pedido do dono), antes de escrever do zero cada item dos blocos 1.1 a 1.3 ([RESULTADOS.md](RESULTADOS.md)). Candidatos a avaliar, nenhum ainda testado aqui: reconhecimento de partes da música (all-in-one, MSAF), transcrição de melodia e voz (basic-pitch, CREPE), separação de bateria por peça, outros geradores para comparar e aprender (Beat Sage, de 2020, rede neural, código fechado; TopMapper, que também faz luzes; InfernoSaber e DeepSaber, a confirmar; o Mapperatorinator é do osu! e só serve de ideia), conferência de paridade (JoshaParity), geradores de luzes (Lightmap do ChroMapper, Lolighter) e as ferramentas de script de mapa (ReMapper, Heck). Para cada um anotar: licença, peso da instalação, se roda sem GPU, e o ganho no conjunto do item 1.0.

### Pedidos prontos

Um por sessão, para colar como está.

```text
Execute os itens 9 e 11 do bloco 1.3 (docs/RESULTADOS.md), um por vez. No item 11 só aparece na tela o que o gerador já sabe fazer. A cada item: confira que o mapa passa na conferência e faça commit. No fim, atualize o roadmap, push.
```

```text
Roadmap 1.4: pesquise as ferramentas de terceiros da lista e diga quais valem a pena e para qual item. Sem código, só atualize o roadmap, commit e push.
```

```text
Roadmap, uso no dia a dia, item 8 (versões de um mapa): confira primeiro como o envio ao Quest nomeia a pasta e se o jogo mantém a pontuação quando o mapa muda, depois faça. Atualize o roadmap, commit e push ao final.
```

```text
Roadmap, uso no dia a dia, item 9, o que falta (contar os mapas atrás da versão atual, só as luzes, mapa travado): faça um por vez, com commit a cada um. Atualize o roadmap, commit e push ao final.
```

```text
Roadmap, medir contra gente: os zips do Beat Sage e do TopMapper estão em <pasta>. Passe pela conferência e pelo tools/medir.py ao lado dos nossos das mesmas músicas e me mostre a tabela. Sem mudar o gerador. Atualize o roadmap, commit e push.
```

Para proteger as músicas que já ficaram boas, acrescente a qualquer pedido: "Estas músicas ficaram perfeitas: <nomes>. Se o mapa delas mudar muito, me mostre antes de manter."

## 3. Pendências do que já foi feito

- Instalador nunca testado numa máquina limpa (instalar, atalho, preparo, gerar, desinstalar).
- Caderno do Colab/Kaggle nunca rodou de verdade; é também o primeiro teste do caminho da placa NVIDIA.
- Botões novos da página (fila, refazer os mapas, refazer todos os mapas, marcar todos, mandar os que faltam) não foram vistos num navegador por quem os escreveu.
- Decisões do dono em aberto: DirectML na RX 6600, 300 ou 1000 mapas na biblioteca, apagar `dados\mapas` depois de montar.
- Nunca conferido: envio real ao Quest em lote, telas da primeira vez no visual novo.

## 4. Uso no dia a dia

1. **Página e servidor de versões diferentes.** Aconteceu: a página nova falando com o servidor antigo. A página deve perceber e pedir para reabrir o Beatloom.
2. **Aviso de versão nova**, com o link da release.
3. **Playlist no jogo.** Gravar um `.bplist` com os mapas gerados para eles aparecerem agrupados no Quest.
4. **Fila.** Cancelar a música que está rodando, reordenar.
5. **Preferências por mapa**, além das gerais; e uma versão mais branda da linha de cima (só proibir corte para baixo lá).
6. **Quest.** Apagar vários de uma vez.
7. Mostrar na ficha do mapa com quais preferências ele foi feito.
8. **Versões de um mapa** (pedido do dono). Refazer um mapa e mandar ao Quest deve trocar a música que já está lá, não criar outra na lista do jogo: mesma pasta e mesmo nome no óculos a cada envio. No computador, cada versão anterior fica guardada (numerada, com data e com o que mudou: modo, preferências, versão do Beatloom), e a ficha do mapa deixa voltar a uma delas ou apagar as antigas. A conferir antes de fazer: como o envio nomeia a pasta hoje e se o jogo mantém a pontuação quando o conteúdo do mapa muda.
9. **Atualizar os mapas antigos de uma vez** (pedido do dono: não ter que regerar música por música a cada melhoria do gerador). **Primeira parte feita em 10/10/2026.**
   - Feito: "Refazer os mapas" (os marcados) e "Refazer todos os mapas" fazem o mapa de novo por inteiro com o gerador de agora, pela fila: notas, arcos, correntes, bombas, paredes, luzes, cenário, cores da capa, eventos de BPM e o Info.dat. Ficam o nome, o artista, o álbum, o ano, o link, a capa, o modo, a densidade e as dificuldades que o mapa tinha, e o arquivo continua com o mesmo nome. A versão anterior (zip e relatórios) vai para `saida\versoes` com a data e a hora; nada é apagado de lá.
   - O que o caminho antigo ("Refazer as notas") deixava para trás: mapa antigo sem a origem da capa anotada nunca ganhava as cores da capa; os campos do Info.dat fora da dificuldade (BPM, início da prévia) ficavam os de antes, e o BPM podia divergir do das notas se a análise fosse refeita; os números do gerador no relatório se perdiam; ninguém conferia se a análise guardada ainda servia; a versão anterior era perdida. Notas, luzes, cenário, eventos de BPM e cores da dificuldade já eram trocados.
   - Feito: a análise guardada tem número de versão (`VERSAO` em `beatloom/audio.py`). Se ele não bate, a música é ouvida de novo reaproveitando os instrumentos já separados, e as camadas de cima (voz, bateria, partes, clima, notas seguradas) são refeitas. As 25 análises que estavam guardadas foram refeitas e comparadas: iguais às do código de agora, então nenhuma precisa ser ouvida de novo hoje. Quem mudar a análise sobe o número.
   - Tempo por música, medido na máquina do dono: uns 10 segundos com a análise guardada; 25 segundos numa música de 1:43 quando a análise venceu mas os instrumentos separados estão guardados (uns 8 segundos a mais a cada 100 segundos de música); 3 minutos e 40 segundos numa música de 3:54 sem nada guardado (a separação dos instrumentos é 71% disso), o mesmo que gerar do zero.
   - Capa: a capa de verdade é sempre levada ao gerador; a genérica do Beatloom é reconhecida pelas cores e trocada pela genérica de agora.
   - Não conferido: os dois botões num navegador (o servidor foi exercitado por HTTP numa pasta à parte, com fila de 2 mapas).
   - Falta, lista: mostrar quantos mapas estão atrás da versão atual e oferecer "Atualizar os N mapas antigos" (hoje o botão refaz todos).
   - Falta, só as luzes: quando a melhoria for só de luzes ou cores, refazer só elas e deixar as notas como estão. Protege o mapa que já ficou bom de jogar.
   - Falta, mapa "travado": marcar um mapa de que se gosta para as atualizações em lote não tocarem nas notas dele.
   - Falta, com o item 8: ver, voltar e apagar as versões guardadas pela ficha do mapa. A densidade escolhida ao refazer uma dificuldade sozinha não é lembrada (vale a do mapa).

## 5. Projeto

- Rodar os `--demo` e o `tools/check_i18n.py` na CI a cada push.
- Notas de release agrupadas (novidades, correções) em vez da lista crua de commits.
- Assinar o instalador, para o SmartScreen não assustar. Custa um certificado.

## Fora do roadmap

O que as decisões em [plan/README.md](plan/README.md) deixam de fora: hospedar como serviço, embutir a biblioteca de padrões, terceiro idioma, tema claro, Linux e Mac como alvo de usuário final.
