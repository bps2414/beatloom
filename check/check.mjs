// Valida um arquivo de dificuldade com a biblioteca bsmap e conta erros de paridade.
// O laco de paridade e o mesmo do BeatSaber-MapCheck (src/ts/checks/notes/parity.ts), preset padrao.
//   node check.mjs <bpm> <duracao_s> <arquivo.dat> [mais arquivos...]
//   node check.mjs --json <bpm> <duracao_s> <arquivo.dat> ...   (saida para o relatorio.py, com as notas)
import { readFileSync } from 'node:fs';
import { loadDifficulty, loadInfo, TimeProcessor } from 'bsmap';
import { Parity } from 'bsmap/extensions/parity';
import * as swing from 'bsmap/extensions/swing';

const args = process.argv.slice(2);
const asJson = args[0] === '--json' && args.shift();
const [bpm, seconds, ...files] = args;
const results = [];
for (const file of files) {
   let diff;
   if (/info\.dat$/i.test(file)) { // o Info.dat so passa pelo validador de esquema
      try {
         loadInfo(JSON.parse(readFileSync(file, 'utf8').replace(/^﻿/, '')));
         results.push({ file, ok: true });
      } catch (e) {
         results.push({ file, ok: false, erro: e.message });
      }
      if (!asJson) console.log(`${file}\n  ${results.at(-1).ok ? 'esquema ok' : 'ESQUEMA INVALIDO: ' + results.at(-1).erro}`);
      continue;
   }
   try {
      diff = loadDifficulty(JSON.parse(readFileSync(file, 'utf8').replace(/^﻿/, ''))); // lanca erro se o esquema for invalido
   } catch (e) {
      results.push({ file, ok: false, erro: e.message });
      if (!asJson) console.log(`${file}\n  ESQUEMA INVALIDO: ${e.message}`);
      continue;
   }
   const tp = new TimeProcessor(+bpm);
   const notes = diff.difficulty.colorNotes, bombs = diff.difficulty.bombNotes;
   const all = [...notes.map((d) => ({ bomb: false, d })), ...bombs.map((d) => ({ bomb: true, d }))]
      .sort((a, b) => a.d.time - b.d.time);
   const par = [0, 1].map((c) => new Parity(notes, bombs, c, 90, 45, 90));
   const last = {}, cur = [[], []], bombCtx = [[], []], lastBombCtx = [[], []];
   const out = { warning: 0, error: 0 }, onde = [];
   let swings = 0;
   for (const { bomb, d } of all) {
      if (bomb) { bombCtx[0].push(d); bombCtx[1].push(d); continue; }
      const c = d.color;
      if (last[c] && swing.next(d, last[c], tp, cur[c])) {
         swings++;
         const st = par[c].check(cur[c], lastBombCtx[c]);
         if (st in out) out[st]++;
         if (st === 'error') onde.push(cur[c][0].time);
         par[c].next(cur[c], lastBombCtx[c]);
         lastBombCtx[c] = bombCtx[c]; bombCtx[c] = []; cur[c] = [];
      }
      last[c] = d; cur[c].push(d);
   }
   const d = diff.difficulty;
   results.push({
      file, ok: true, golpes: swings, erros: out.error, avisos: out.warning, onde,
      notas: notes.map((n) => [n.time, n.posX, n.posY, n.color, n.direction]),
      bombas: bombs.map((n) => [n.time, n.posX, n.posY]),
      paredes: d.obstacles.map((o) => [o.time, o.duration, o.posX, o.posY, o.width, o.height]),
      eventos: diff.lightshow?.basicEvents?.length ?? d.basicEvents?.length ?? 0, arcos: d.arcs.length, correntes: d.chains.length,
   });
   const pct = (n) => (100 * n / Math.max(swings, 1)).toFixed(1);
   if (!asJson) console.log(`${file}\n  esquema ok | notas ${notes.length} | bombas ${bombs.length} | paredes ${d.obstacles.length}` +
      ` | NPS ${(notes.length / +seconds).toFixed(2)} | golpes ${swings}` +
      ` | paridade: ${out.error} erros (${pct(out.error)}%), ${out.warning} avisos (${pct(out.warning)}%)`);
}
if (asJson) console.log(JSON.stringify(results));
