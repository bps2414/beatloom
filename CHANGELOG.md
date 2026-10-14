# Mudanças

O que mudou em cada versão, para quem usa. A seção de uma versão vira o texto da release dela; a lista completa dos commits vai junto, recolhida. Os números medidos de cada mudança do gerador estão em [docs/RESULTADOS.md](docs/RESULTADOS.md).

## Próxima versão

## v1.3.0

Mapas feitos antes desta versão não mudam sozinhos: use "Novo visual em todos" (só o visual, as notas ficam como estão) ou "Refazer todos os mapas".

### Visual dos mapas

- **Sem nome de banda no fundo.** Os cenários sorteados pelo clima da música não têm mais nome de banda ou gravadora escrito (antes uma música pesada podia cair no palco do Green Day, com "GREEN DAY" no fundo). Música da própria banda vai para o palco dela: Green Day, Linkin Park, BTS, Imagine Dragons, Panic! at the Disco, Timbaland, Skrillex, Billie Eilish, K/DA.
- **Letreiro do artista** (com "Tenho Chroma"). O artista grande e a música embaixo, em letras de luz no fundo do cenário: acendem letra por letra na entrada, carregam na subida, piscam com a bateria e com a voz, um clarão branco corre por elas na queda. E colunas de luz dos dois lados, que acendem com os lasers.
- **Chroma luz por luz.** Os anéis enchem na subida e, na queda, acendem com as quatro cores da capa espalhadas a cada bumbo; os lasers acendem um terço de cada vez na caixa; paredes na cor da parte da música.
- **Mais luz sem mod.** A subida acende em transição contínua, os cenários novos ganham luz correndo em onda, a pausa respira em vez de ficar no escuro e, no verso, o centro dá um clarão a cada nota cantada longa.
- **Lawless animado** (com "Tenho Noodle Extensions"). O letreiro sobe do horizonte, pula a cada queda e sobe para o céu no fim; as colunas pulam no ritmo; as notas surgem do nada e, na entrada da queda, caem de cima.
- **Refazer só as luzes.** Na ficha (menu "⋯"), nos marcados e em "Novo visual em todos": cenário, luzes, cores e mods de agora, com as notas exatamente como estão. Renomear um mapa com letreiro refaz o visual dele sozinho.

Nada disso foi visto no jogo ainda. `tools\prova_visual.py` grava mapas de prova para conferir no Quest.

### Outras mudanças

- **Envio ao Quest em segundo plano.** "Mandar ao Quest" volta na hora: os mapas vão um de cada vez, com um cartão no alto da lista (barra geral, o mapa de agora com a porcentagem, falhas com o detalhe, Cancelar) e uma barra fina na linha de cada mapa. As playlists vão no fim.
- **Servidor Linux.** O Beatloom roda como serviço num servidor Linux de casa, e a porta não fica mais presa por um minuto depois de reiniciar.

## v1.2.0

- **Selecionar arrastando.** Aperte a caixa de uma música e arraste: o trecho até onde o mouse está fica marcado (ou desmarcado, se a primeira estava marcada). Voltar com o mouse, sem soltar, desfaz.
- **Envio ao Quest sem repetir.** "Mandar tudo ao Quest" compara cada mapa com o que já está no aparelho: o novo é enviado, o que foi refeito ou renomeado depois do último envio é trocado e o que está na mesma versão é pulado. O aviso diz quantos de cada.
- **Avisos no Discord.** Em Configuração, cole o endereço de um webhook e o Beatloom avisa no canal: uma mensagem única de andamento da fila (barra, música atual, etapa), um cartão por mapa pronto com a capa, os erros e o resumo final. Nas duas línguas, e o botão "Enviar teste" mostra como fica. O endereço fica só no seu computador.
- **Bandeja do Windows.** `start-bandeja.bat` (ou `start.bat bandeja`) abre o Beatloom minimizado, com um ícone perto do relógio: duplo clique abre a página, "Sair" encerra.
- **Playlist no jogo.** Ao colar um link de playlist, "Criar também a playlist no jogo" faz os mapas aparecerem agrupados no Beat Saber (precisa de um mod de playlists no Quest). A playlist vai junto a cada envio ao Quest e também pode ser baixada como `.bplist`. Mapas marcados na lista entram numa playlist que já existe ou numa nova, mesmo sem link do YouTube.

## v1.1.0

O gerador passou a ouvir mais da música e a usar mais do que o jogo oferece. Mapas feitos na 1.0.0 não mudam sozinhos: use "Refazer todos os mapas" para trazê-los ao gerador novo.

### O mapa

- **Voz.** Sílaba cantada vira nota, a melodia puxa a linha e o sentido do corte, nota longa vira nota segurada.
- **Bateria por peça.** Bumbo embaixo, caixa no meio, prato forte vira dupla.
- **Partes da música.** Introdução, verso, subida, queda e pausa: a queda sai mais cheia, a subida acelera até ela, a pausa fica sem nota.
- **Golpes mais humanos.** A escolha ensaia 8 batidas à frente, o refrão volta espelhado ou com um acento a mais, e os acentos fortes ganham pilhas.
- **Mais vocabulário.** Correntes nos ataques secos, arcos seguindo a voz, bombas de reinício na volta dos respiros, paredes de desviar e de agachar.
- **BPM variável.** O mapa ganha eventos de BPM e a grade acompanha a música.

### Luzes e cores

- As luzes seguem as partes da música e a bateria: escuro na pausa, a subida acende aos poucos, apagão antes da queda.
- Luzes com as cores da capa. Sabres e notas também, por uma chave.
- O cenário do jogo é escolhido pelo clima da música (calmo, pesado, eletrônico), incluindo cenários novos.

### Página

- **Seu jeito de jogar**, na Configuração: sem notas na linha de cima, sem nota escondida atrás de outra, quanto os braços podem cruzar.
- **Mods opcionais**: "Tenho Chroma" (paleta da capa nas luzes) e "Tenho Noodle Extensions" (um conjunto de dificuldades à parte, com efeitos leves).
- **Refazer os mapas**: os marcados ou todos, com o gerador e as preferências de agora. A versão anterior fica em `saida\versoes`.
- **Fila** que pausa, esvazia e sobrevive a fechar o Beatloom. Colar a mesma playlist de novo só faz o que falta.
- **Lista**: marcar vários mapas pela capa para refazer, apagar ou mandar ao Quest; "Mandar ao Quest os N que faltam".
- Procurar o Quest na rede sem cabo, para quem já ligou o modo sem fio.

### Outros

- Caderno para gerar em lote no Google Colab ou no Kaggle.
- Corrigido: um bloqueio de visão no limite do intervalo escapava do gerador e reprovava na conferência.

### Ainda não visto no jogo

Correntes, bombas, paredes de desviar, as luzes dos cenários novos e os efeitos do Chroma e do Noodle Extensions passam na conferência de formato, mas ainda não foram conferidos dentro do jogo. O instalador também não foi testado numa máquina limpa.

## v1.0.0

Primeira versão: instalador e `start.bat` que baixam tudo sozinhos, página nova em português e inglês, visualizador 3D, envio ao Quest por Wi-Fi, modo rápido, placa NVIDIA usada automaticamente e link de playlist.
