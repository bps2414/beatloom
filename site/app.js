// Pagina do Beatloom. As frases moram em site/i18n/<lingua>.json; o servidor so manda codigos e numeros, e aqui eles viram texto.
const $ = (id) => document.getElementById(id);
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const icone = (nome) => { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("class", "ic"); s.innerHTML = `<use href="#i-${nome}"/>`; return s; };
const enc = encodeURIComponent;
const NOMES = { Easy: "Easy", Normal: "Normal", Hard: "Hard", Expert: "Expert", ExpertPlus: "Expert+" };
const ITENS = ["ffmpeg", "node", "padroes", "visor", "adb"];

const T = {};
let lingua = navigator.language.startsWith("pt") ? "pt" : "en";  // ate o beatloom.json dizer outra coisa
let cfg = { difs: [], densidade: 1 }, quest = { mapas: {} }, estado = { mapas: [], trabalhos: [], visor: true };
let atual = null, mapa = null, dif = "Expert";

const t = (k, v = {}) => (T[lingua][k] ?? k).replace(/\{(\w+)\}/g, (_, n) => v[n] ?? "");
const num = (n, casas = 0) => new Intl.NumberFormat(lingua === "pt" ? "pt-BR" : "en", { minimumFractionDigits: casas, maximumFractionDigits: casas }).format(n);
const pct = (f, casas = 0) => num(f * 100, casas) + "%";
const tempo = (s) => Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
const mb = (n) => num(n / 2 ** 20) + " MB";

// erro do servidor: "codigo" ou "codigo|detalhe tecnico" (fim da saida do gerador, do yt-dlp ou do adb)
function lerErro(c) { const [k, ...r] = String(c || "").split("|"); return { msg: T[lingua]["erro_" + k] || t("erro_geral"), detalhe: r.join("|") }; }
class Erro extends Error { constructor(c) { const e = lerErro(c); super(e.msg); this.detalhe = e.detalhe; } }
const api = (url, corpo, cru) => fetch(url, corpo === undefined ? {} : {
  method: "POST", headers: { "X-Automapper": "1", ...(cru ? {} : { "Content-Type": "application/json" }) }, body: cru ? corpo : JSON.stringify(corpo),
}).then(async (r) => { const j = await r.json().catch(() => ({})); if (!r.ok) throw new Erro(j.erro); return j; });

function tecnico(txt) { const d = el("details"); d.append(el("summary", "", t("detalhe_tecnico")), el("pre", "", txt)); return d; }
function avisar(msg, ruim, detalhe, acao) {  // popover: fica por cima ate de um dialogo aberto. acao = { texto, fazer }: um botao no aviso (o Desfazer)
  const a = $("avisos"), d = el("div", "aviso" + (ruim ? " ruim" : ""), msg), sumir = () => { d.remove(); if (!a.children.length && a.matches(":popover-open")) a.hidePopover(); };  // o botao e o relogio podem chamar os dois
  if (acao) { const b = el("button", "quieto", acao.texto); b.type = "button"; b.onclick = () => { sumir(); acao.fazer(); }; d.append(b); }
  if (detalhe) d.append(tecnico(detalhe));
  a.append(d); if (a.matches(":popover-open")) a.hidePopover(); a.showPopover();
  setTimeout(sumir, acao ? 10000 : detalhe ? 20000 : 6000);
}
const falhou = (x) => avisar(x.message, true, x.detalhe);
function confirmar(pergunta, botao) {  // -> Promise<sim ou nao>
  const d = $("d-confirma"); $("cf-texto").textContent = t(pergunta); $("cf-sim").textContent = t(botao);
  d.returnValue = ""; d.showModal();
  return new Promise((ok) => { d.onclose = () => ok(d.returnValue === "sim"); });
}
for (const b of document.querySelectorAll("[data-fecha]")) b.onclick = () => b.closest("dialog").close();

// ---------- controles repetidos: quantidade de notas e botoes de dificuldade
function dens(id) { const r = $(id); (r.oninput = () => { const v = +r.value; $(id + "-v").textContent = t(v < 0.98 ? "leve" : v > 1.02 ? "cheio" : "normal") + " ×" + num(v, 2); })(); }
function alternadores(id, marcadas, aoMudar) {
  const c = $(id); c.textContent = "";
  for (const d of Object.keys(NOMES)) {
    const b = el("button", "dif", NOMES[d]); b.type = "button"; b.dataset.n = d; b.setAttribute("aria-pressed", marcadas.includes(d));
    b.onclick = () => { b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true"); if (aoMudar) aoMudar(); }; c.append(b);
  }
}
const marcadasEm = (id) => [...$(id).querySelectorAll('[aria-pressed="true"]')].map((b) => b.dataset.n);

function traduzir() {
  document.documentElement.lang = lingua === "pt" ? "pt-BR" : "en";
  for (const e of document.querySelectorAll("[data-t]")) e.textContent = t(e.dataset.t);
  for (const e of document.querySelectorAll("[data-tp]")) { e.placeholder = t(e.dataset.tp); e.setAttribute("aria-label", t(e.dataset.tp)); }
  for (const e of document.querySelectorAll("[data-ta]")) e.setAttribute("aria-label", t(e.dataset.ta));
  $("lingua").textContent = lingua === "pt" ? "English" : "Português";
  for (const b of $("p-linguas").children) b.setAttribute("aria-pressed", b.dataset.l === lingua);
  for (const id of ["dens", "c-dens", "r-dens"]) dens(id);
  pintarArquivo(); pintarTrabalhos(); pintarLista(); pintarMapa(); pintarQuest(); resumo();
  if ($("painel").open) { botoes(); verPreparo(); verConfig(); }
}
function mudarLingua(l) { lingua = l; salvar({ lingua }); traduzir(); }
$("lingua").onclick = () => mudarLingua(lingua === "pt" ? "en" : "pt");
for (const b of $("p-linguas").children) b.onclick = () => mudarLingua(b.dataset.l);

// ---------- novo mapa
let arquivo = null, subido = null, extra = {}, miniatura = null, ultimoLink = "", lista = null, playlist = null;  // lista: as faixas quando o link e de playlist; playlist: o id e o nome dela
const erroNovo = (x) => { $("erro").textContent = x.message; $("erro").hidden = false; };
function pintarArquivo() { $("arq-nome").textContent = arquivo ? arquivo.name : t("solte"); $("arq-dica").textContent = t(arquivo ? "trocar_arq" : "solte_dica"); }
function previa(d, capa, info) {  // capa, nome e artista antes de gerar, para a pessoa corrigir
  extra = { album: d.album, ano: d.ano }; miniatura = capa; lista = d.lista || null; playlist = lista && d.id ? { id: d.id, nome: d.nome } : null;
  $("previa").hidden = false; $("jogo").parentElement.hidden = !playlist; $("jogo").checked = ls.ler("beatloom.jogo") === "1"; $("nome").parentElement.hidden = !!lista;  // playlist: nome e artista saem de cada video
  $("nome").value = d.nome || ""; $("artista").value = d.artista || "";
  $("p-capa").hidden = !capa; $("p-sem").hidden = !!capa; if (capa) $("p-capa").src = capa;
  $("p-info").textContent = lista ? t("lista_n", { n: lista.length, nome: d.nome }) : [d.album, d.ano, info, t("confira")].filter(Boolean).join(", ");
}
function semPrevia() { $("previa").hidden = true; $("nome").value = ""; $("artista").value = ""; extra = {}; miniatura = null; lista = playlist = null; $("jogo").parentElement.hidden = true; }
function resumo() {  // o que as opcoes fechadas dizem: as dificuldades marcadas, a quantidade de notas e o modo rapido
  const d = +$("dens").value;
  $("opc-resumo").textContent = [marcadasEm("escolha").map((n) => NOMES[n]).join(" "), d !== 1 && "×" + num(d, 2), $("rapido").checked && t("rapido")].filter(Boolean).join(" · ");
}
$("dens").addEventListener("input", resumo); $("rapido").onchange = resumo;
function abrirNovo() {
  if ($("d-novo").open) return;
  $("erro").hidden = true; alternadores("escolha", cfg.difs, resumo); $("dens").value = cfg.densidade; dens("dens"); $("rapido").checked = cfg.modo === "rapido"; $("sabres").checked = !!cfg.sabres_capa;
  $("opcoes").open = false; resumo();
  $("d-novo").showModal();
}
$("novo").onclick = abrirNovo;
$("vz-form").onsubmit = (e) => {  // o campo da tela vazia leva o link ao dialogo, que mostra a previa e as opcoes
  e.preventDefault(); const l = $("vz-link").value.trim(); abrirNovo();
  if (l) { $("link").value = l; verLink(); }
  $("vz-link").value = "";
};
async function verLink() {
  const link = $("link").value.trim();
  if (link === ultimoLink) return;
  ultimoLink = link; $("erro").hidden = true;
  if (!/^https?:\/\/\S+$/.test(link)) return semPrevia();
  arquivo = subido = null; pintarArquivo();
  $("previa").hidden = false; $("p-capa").hidden = true; $("p-sem").hidden = false; $("p-info").textContent = t("procurando");
  try { const d = await api("/api/previa", { link }); if ($("link").value.trim() === link) previa(d, d.capa, ""); }
  catch (x) { if ($("link").value.trim() === link) { semPrevia(); erroNovo(x); } }
}
$("link").onchange = verLink;
$("link").onpaste = () => setTimeout(verLink, 0);
async function pegarArquivo(f) {
  arquivo = f || null; subido = null; pintarArquivo();
  if (!arquivo) return semPrevia();
  $("link").value = ""; ultimoLink = ""; $("erro").hidden = true;
  try {
    subido = await api("/api/arquivo?nome=" + enc(arquivo.name), arquivo, true);
    const capa = "/api/capa?arquivo=" + enc(subido.base) + "&t=" + Date.now();
    const tem = (await fetch(capa)).ok;
    previa(subido, tem ? capa : null, t(tem ? "capa_arq" : "capa_gen"));
  } catch (x) { arquivo = null; pintarArquivo(); erroNovo(x); }
}
$("solta").onclick = () => $("arq").click();
$("arq").onchange = () => pegarArquivo($("arq").files[0]);
// soltar um arquivo em qualquer lugar da pagina abre o dialogo ja com ele
addEventListener("dragover", (e) => { e.preventDefault(); $("solta").classList.add("sobre"); });
addEventListener("dragleave", () => $("solta").classList.remove("sobre"));
addEventListener("drop", (e) => { e.preventDefault(); $("solta").classList.remove("sobre"); const f = e.dataTransfer.files[0]; if (f && !$("painel").open) { abrirNovo(); pegarArquivo(f); } });
$("form").onsubmit = async (e) => {
  e.preventDefault();
  $("erro").hidden = true; $("gerar").disabled = true;
  try {
    const link = $("link").value.trim(), difs = marcadasEm("escolha");
    if (!difs.length) throw new Error(t("sem_dif"));
    if (!link && arquivo && !subido) subido = await api("/api/arquivo?nome=" + enc(arquivo.name), arquivo, true);
    const comum = { difs, densidade: +$("dens").value, modo: $("rapido").checked ? "rapido" : "completo", sabres_capa: $("sabres").checked };
    if (link && lista) {  // um trabalho por faixa, na fila; o servidor pula as que ja tem mapa e refaz as que falharam na conferencia
      const r = await api("/api/gerar", { lista: lista.map((m) => ({ link: m.link, titulo: m.nome, capa: m.capa })), playlist: $("jogo").checked ? playlist : null, ...comum });
      if (playlist) ls.gravar("beatloom.jogo", $("jogo").checked ? "1" : "0");
      if (r.pulados || r.refeitos) avisar(t("lista_repetida", { novos: r.novos, pulados: r.pulados, refeitos: r.refeitos }));
    }
    else await api("/api/gerar", { link, arquivo: link ? null : subido && subido.arquivo, nome: $("nome").value, artista: $("artista").value, ...extra, capa: miniatura, ...comum });
    $("link").value = ""; ultimoLink = ""; $("arq").value = ""; arquivo = subido = null; semPrevia(); pintarArquivo();
    $("d-novo").close(); document.body.classList.remove("vendo"); atualizar();
  } catch (x) { erroNovo(x); }
  $("gerar").disabled = false;
};

// ---------- biblioteca: geracoes em andamento e mapas prontos
const vistos = new Set(), linhas = new Map(), marcados = new Set();
let primeira = true;
const ETAPAS = ["ouvindo", "golpes", "empacotando", "conferindo"];
function trilha(tr, passo, qual) {  // um trecho por etapa: as feitas cheias, a de agora enchendo (separacao em %, golpes por dificuldade) ou pulsando quando nao ha medida
  const nomes = tr.passos.includes("baixando") ? ["baixando", ...ETAPAS] : ETAPAS, agora = Math.max(nomes.indexOf(passo), 0), g = /\((\d+)\/(\d+)\)/.exec(qual || "");
  const p = tr.progresso != null ? tr.progresso : passo === "golpes" && g ? ((g[1] - 1) / g[2]) * 100 : null, c = el("div", "trilha"); c.setAttribute("aria-hidden", "true");
  nomes.forEach((_, i) => { const b = el("i", i < agora ? "feito" : i > agora ? "falta" : p == null ? "agora corre" : "agora"); if (i === agora && p != null) b.style.setProperty("--p", p + "%"); c.append(b); });
  return c;
}
let filaAberta = false;  // com muita coisa na fila, so as 2 primeiras aparecem: o resto nao empurra a lista de mapas para fora da tela
const NA_FILA = 2;
function pintarTrabalhos() {
  const vivos = estado.trabalhos.filter((tr) => tr.estado !== "pronto"), chave = JSON.stringify([vivos, lingua, estado.pausada, filaAberta]);
  if (chave === pintarTrabalhos.chave) return;  // so redesenha quando muda: nao rouba o foco do botao de dispensar
  pintarTrabalhos.chave = chave; $("trabalhos").textContent = "";
  const esperam = vivos.filter((tr) => tr.estado === "na fila").length;
  if (esperam || estado.pausada) {  // a fila: quantos esperam, pausar e esvaziar
    const barra = el("div", "barra"), p = el("button", "quieto", t(estado.pausada ? "continuar_fila" : "pausar")), v = el("button", "quieto", t("esvaziar"));
    p.type = v.type = "button"; v.hidden = !esperam;
    p.onclick = async () => { await api("/api/fila", { pausar: !estado.pausada }); atualizar(); };
    v.onclick = async () => { if (await confirmar("confirma_esvaziar", "esvaziar")) { await api("/api/trabalho/dispensar", { fila: true }); atualizar(); } };
    barra.append(el("span", "", t(estado.pausada ? "fila_pausada" : "fila_n", { n: esperam })), p, v); $("trabalhos").append(barra);
  }
  let vistos = 0;
  for (const tr of vivos) {
    if (tr.estado === "na fila" && ++vistos > NA_FILA && !filaAberta) continue;
    const ruim = tr.estado === "erro", c = el("div", "trabalho" + (ruim ? " ruim" : tr.estado === "rodando" ? " vivo" : " espera")), capa = tr.capa ? el("img", "capa") : el("div", "sem-capa");
    if (tr.capa) { capa.src = tr.capa; capa.alt = ""; }
    const [passo, qual] = (tr.passos.at(-1) || "comecando").split("|");  // "golpes|Hard (2/4)"
    const e = ruim ? lerErro(tr.erro) : null;
    const etapaDe = tr.progresso != null ? "separando" : passo;  // a separacao acontece dentro de "ouvindo" e tem barra propria
    const etapa = e ? e.msg : tr.estado === "na fila" ? t("fila") : t("passo_" + etapaDe) + (qual ? " " + qual.replace("ExpertPlus", "Expert+") : "") + (tr.progresso != null ? " " + tr.progresso + "%" : "");
    c.append(capa, el("b", "", tr.titulo), el("span", "etapa", etapa));
    if (tr.estado === "rodando") c.append(trilha(tr, passo, qual));
    if (ruim || tr.estado === "na fila") {
      const fim = el("div", "fim"), b = el("button", "quieto", t("dispensar")); b.type = "button";
      b.onclick = async () => { await api("/api/trabalho/dispensar", { id: tr.id }); atualizar(); };
      fim.append(e && e.detalhe ? tecnico(e.detalhe) : el("span"), b); c.append(fim);
    }
    $("trabalhos").append(c);
  }
  if (esperam > NA_FILA) {
    const b = el("button", "quieto mais-fila", t(filaAberta ? "fila_menos" : "fila_mostrar", { n: esperam - NA_FILA })); b.type = "button";
    b.onclick = () => { filaAberta = !filaAberta; pintarTrabalhos(); }; $("trabalhos").append(b);
  }
}
function pontosDe(m) {  // um ponto por dificuldade, na cor do botao dela
  const p = el("span", "pontos"); for (const d of m.difs) { const i = el("i"); i.dataset.n = d; i.title = NOMES[d] || d; p.append(i); }
  return p;
}
const ULTIMO = "beatloom.ultimo";  // o ultimo mapa aberto: o inicio oferece continuar dele
function pintarInicio() {  // a tela sem mapa aberto: o que ha na biblioteca e uma parede de capas para escolher
  const ms = estado.mapas; if (!ms.length) return;
  const volta = ms.find((m) => m.zip === ls.ler(ULTIMO)), cabeca = volta || ms[0], mostra = [cabeca, ...ms.filter((m) => m !== cabeca).slice(0, 11)];
  const total = ms.reduce((s, m) => s + (m.dur || 0), 0), ok = ms.filter((m) => m.ok === true).length, ruim = ms.filter((m) => m.ok === false).length, noq = quest.conectado ? ms.filter((m) => quest.mapas[m.zip] === "ok").length : 0;
  const chave = JSON.stringify([mostra.map((m) => [m.zip, m.v, m.ok, m.nome, m.artista, m.difs]), !!volta, ms.length, total, ok, ruim, noq, quest.conectado, lingua]);
  if (chave === pintarInicio.chave) return; pintarInicio.chave = chave;
  const h = Math.floor(total / 3600), min = Math.round((total % 3600) / 60), st = $("in-stats"); st.textContent = "";
  for (const [v, r, cls] of [[num(ms.length), "ini_mapas"], [h ? h + " h " + min + " min" : min + " min", "ini_tempo"], [num(ok), "ini_ok", "ok"], ruim && [num(ruim), "ini_falhou", "ruim"], quest.conectado && [num(noq), "ini_quest"]].filter(Boolean)) {
    const li = el("li", cls || ""), b = cls === "ruim" ? el("button") : li;  // o que falhou leva a lista para os que falharam
    if (cls === "ruim") { b.type = "button"; b.onclick = () => { ordem = $("ordem").value = "falhou"; ls.gravar("beatloom.ordem", ordem); pintarLista(); }; li.append(b); }
    b.append(el("b", "", v), el("span", "", t(r))); st.append(li);
  }
  const ul = $("parede"); ul.textContent = "";
  mostra.forEach((m, i) => {
    const li = el("li", i ? "" : "destaque"), b = el("button", "cartao"), img = el("img"), txt = el("span", "txt");
    b.type = "button"; b.onclick = () => abrir(m.zip); img.alt = ""; img.src = `/api/capa?zip=${enc(m.zip)}&v=${m.v}`;
    if (!i) txt.append(el("small", "rotulo", t(volta ? "ini_continuar" : "ini_recente")));
    txt.append(el("b", "", m.nome), el("span", "", m.artista), pontosDe(m)); if (m.ok === false) txt.append(el("span", "falha", t("tag_falhou")));
    b.append(img, txt); li.append(b); ul.append(li);
  });
  $("in-fundo").style.backgroundImage = `url("/api/capa?zip=${enc(cabeca.zip)}&v=${cabeca.v}")`;
}
let busca = "", ordem = "recentes", listadas = [];  // listadas: os mapas que a lista mostra neste momento (a busca esconde o resto)
const ls = { ler: (k) => { try { return localStorage.getItem(k); } catch { return null; } }, gravar: (k, v) => { try { localStorage.setItem(k, v); } catch { /* sem armazenamento: so nao lembra */ } } };
const sem = (x) => String(x).normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
const ORDENS = { nome: (a, b) => a.nome.localeCompare(b.nome, lingua), artista: (a, b) => a.artista.localeCompare(b.artista, lingua) || a.nome.localeCompare(b.nome, lingua), bpm: (a, b) => b.bpm - a.bpm, falhou: (a, b) => (a.ok === false ? 0 : 1) - (b.ok === false ? 0 : 1) };  // "recentes" e a ordem do servidor
if (ORDENS[ls.ler("beatloom.ordem")]) ordem = ls.ler("beatloom.ordem");
$("ordem").value = ordem;
$("busca").oninput = () => { busca = $("busca").value; pintarLista(); };
$("ordem").onchange = () => { ordem = $("ordem").value; ls.gravar("beatloom.ordem", ordem); pintarLista(); };
function pintarLista() {
  const ul = $("mapas"), q = sem(busca.trim());
  listadas = estado.mapas.filter((m) => !q || sem(m.nome + " " + m.artista).includes(q)); if (ORDENS[ordem]) listadas.sort(ORDENS[ordem]);
  for (const z of marcados) if (!listadas.some((m) => m.zip === z)) marcados.delete(z);  // o que a busca esconde sai da selecao: o lote so mexe no que se ve
  for (const [z, li] of linhas) if (!estado.mapas.some((m) => m.zip === z)) { li.remove(); linhas.delete(z); marcados.delete(z); }
  [...listadas, ...estado.mapas.filter((m) => !listadas.includes(m))].forEach((m, i) => {  // uma linha por zip, reaproveitada: refazer a lista roubaria o foco e faria as capas piscarem; as escondidas vao para o fim
    let li = linhas.get(m.zip);
    if (!li) {
      li = $("m-linha").content.firstElementChild.cloneNode(true); linhas.set(m.zip, li);
      li.querySelector(".abre").onclick = () => abrir(m.zip);
      li.zip = m.zip;
      li.querySelector(".marcar").onchange = (e) => { if (arrastou) { e.target.checked = marcados.has(m.zip); return; } marcados[e.target.checked ? "add" : "delete"](m.zip); pintarLote(); };  // depois de um arrasto o clique solto na caixa de origem nao desfaz o que o arrasto fez
    }
    if (ul.children[i] !== li) ul.insertBefore(li, ul.children[i] || null);
    li.hidden = !listadas.includes(m);
    const q = (s) => li.querySelector(s), capa = `/api/capa?zip=${enc(m.zip)}&v=${m.v}`, la = quest.mapas[m.zip];
    if (q(".capa").getAttribute("src") !== capa) q(".capa").src = capa;
    q(".n").textContent = m.nome; q(".a").textContent = m.artista; q(".bpm").textContent = num(m.bpm); q(".dur").textContent = m.dur ? tempo(m.dur) : "–";
    q(".bpm").title = "BPM"; q(".dur").title = t("duracao");
    q(".tags").textContent = "";
    q(".tags").append(pontosDe(m));
    if (/ v3/.test(m.sub)) q(".tags").append(el("span", "rapido", t("tag_rapido")));
    if (m.ok === false) q(".tags").append(el("span", "falha", t("tag_falhou")));
    if (la) q(".tags").append(el("span", la === "ok" ? "la" : "velho", t(la === "ok" ? "no_quest" : "q_velho")));
    q(".abre").setAttribute("aria-current", m.zip === atual);
    q(".marcar").checked = marcados.has(m.zip); q(".marcar").setAttribute("aria-label", t("marcar", { nome: m.nome }));
  });
  const nada = !estado.mapas.length && !estado.trabalhos.some((tr) => tr.estado !== "pronto");
  $("sem-mapas").hidden = estado.mapas.length > 0; $("sem-achado").hidden = !estado.mapas.length || listadas.length > 0; $("filtro").hidden = estado.mapas.length < 5; document.body.classList.toggle("sem-nada", nada);
  $("vz-titulo").textContent = t("titulo"); $("vz-sub").textContent = t("sub");
  pintarLote(); pintarInicio(); pintarPlaylists();
}
function pintarPlaylists() {  // as playlists que vao para o jogo: o nome marca os mapas dela (dai o lote manda ao Quest, refaz ou apaga), o .bplist baixa, o x esquece
  const ps = estado.playlists || [], chave = JSON.stringify([ps, lingua]);
  if (chave === pintarPlaylists.chave) return;  // so redesenha quando muda, para nao roubar o foco
  pintarPlaylists.chave = chave; $("playlists").textContent = "";
  for (const p of ps) {
    const c = el("div", "barra"), m = el("button", "quieto", `${p.nome} (${p.zips.length}/${p.total})`), a = el("a", "quieto", ".bplist"), x = el("button", "quieto", "×");
    m.type = x.type = "button"; m.title = t("pl_marcar"); a.href = "/api/bplist?id=" + enc(p.id); a.title = t("pl_baixar"); x.title = t("pl_tirar"); x.setAttribute("aria-label", t("pl_tirar"));
    m.onclick = () => { marcados.clear(); for (const z of p.zips) marcados.add(z); daLista = p.id; pintarLista(); };
    x.onclick = async () => { try { await api("/api/playlist/apagar", { id: p.id }); atualizar(); } catch (e) { falhou(e); } };
    c.append(m, a, x); $("playlists").append(c);
  }
}
let daLista = null;  // a playlist cujo nome foi clicado: enquanto so mapas dela estiverem marcados, o lote oferece tirar
function pintarLote() {
  const pl = (estado.playlists || []).find((p) => p.id === daLista);
  $("lote-tirar").hidden = !(pl && marcados.size && [...marcados].every((z) => pl.zips.includes(z)));
  const faltam = listadas.filter((m) => quest.mapas[m.zip] !== "ok");  // os que nao estao no Quest, ou estao numa versao antiga: so esses vao de fato
  $("barra-lista").hidden = !estado.mapas.length; $("q-novos").hidden = !quest.conectado || !listadas.length; $("q-novos").textContent = t(faltam.length ? "q_novos" : "q_em_dia", { n: faltam.length });
  $("q-novos").onclick = () => enviar(listadas.map((m) => m.zip), $("q-novos"));  // manda tudo da lista; o servidor pula o que ja esta igual no Quest
  $("marcar-todos").textContent = t(marcados.size === listadas.length ? "desmarcar_todos" : "marcar_todos"); $("lote-enviar").hidden = !quest.conectado;
  $("lote").hidden = !marcados.size; $("mapas").classList.toggle("marcando", marcados.size > 0);
  $("lote-n").textContent = t(marcados.size === 1 ? "lote_um" : "lote_varios", { n: marcados.size });
}
$("lote-tirar").onclick = async () => { try { await api("/api/playlist/mapas", { id: daLista, zips: [...marcados], tirar: true }); marcados.clear(); await atualizar(); } catch (x) { falhou(x); } };
$("lote-lista").onclick = () => {  // os marcados entram numa playlist que ja existe ou numa nova, que so precisa de um nome
  const s = $("pl-qual"); s.textContent = "";
  for (const p of estado.playlists || []) { const o = el("option", "", p.nome); o.value = p.id; s.append(o); }
  s.append(el("option", "", t("pl_nova"))); s.lastChild.value = "";
  (s.onchange = () => { $("pl-nome").hidden = !!s.value; $("pl-nome").required = !s.value; })();
  $("pl-nome").value = ""; $("d-lista").returnValue = ""; $("d-lista").showModal();
};
$("d-lista").onclose = async () => {
  if ($("d-lista").returnValue !== "sim") return;
  try {
    const r = await api("/api/playlist/mapas", { id: $("pl-qual").value || null, nome: $("pl-nome").value, zips: [...marcados] });
    avisar(t("pl_feito", { n: marcados.size, nome: r.nome })); marcados.clear(); await atualizar();
  } catch (x) { falhou(x); }
};
$("lote-limpar").onclick = () => { marcados.clear(); pintarLista(); };
$("marcar-todos").onclick = () => { if (marcados.size === listadas.length) marcados.clear(); else for (const m of listadas) marcados.add(m.zip); pintarLista(); };
// arrasto: apertar a caixa de uma linha e arrastar marca (ou desmarca, o contrario do que a caixa estava) todas as linhas por onde o mouse passa
let pincel = null, origem = null, arrastou = false;  // pincel = o que as linhas viram; origem = a linha do aperto; arrastou = o mouse saiu dela (entao o clique solto nao vale)
const pintar = (li) => { marcados[pincel ? "add" : "delete"](li.zip); li.querySelector(".marcar").checked = pincel; pintarLote(); };
$("mapas").onpointerdown = (e) => { if (e.button === 0 && e.pointerType === "mouse" && e.target.matches(".marcar")) { pincel = !e.target.checked; origem = e.target.closest(".linha"); arrastou = false; } };
$("mapas").onmousedown = (e) => { if (e.target.matches(".marcar")) e.preventDefault(); };  // sem isso o arrasto seleciona texto
$("mapas").onpointerover = (e) => {
  const li = e.target.closest(".linha"); if (pincel === null || !li || li === origem && !arrastou) return;
  if (!arrastou) { arrastou = true; pintar(origem); }
  pintar(li);
};
const soltou = () => { if (pincel !== null) { pincel = null; setTimeout(() => { arrastou = false; }); } };  // o clique vem logo depois do soltar: arrastou so zera depois dele
addEventListener("pointerup", soltou); addEventListener("pointercancel", soltou);
// teclado na lista: setas andam pelas linhas que aparecem, Espaco marca, Enter abre (e o proprio botao); / vai para a busca
$("mapas").onkeydown = (e) => {
  const b = e.target.closest(".abre"); if (!b) return;
  if (e.key === " ") { e.preventDefault(); b.closest(".linha").querySelector(".marcar").click(); return; }
  const bs = [...$("mapas").querySelectorAll(".linha:not([hidden]) .abre")], d = { ArrowDown: 1, ArrowUp: -1 }[e.key], v = bs[bs.indexOf(b) + d];
  if (d && v) { e.preventDefault(); v.focus(); }
};
$("mapas").onkeyup = (e) => { if (e.key === " " && e.target.closest(".abre")) e.preventDefault(); };  // o Firefox clica o botao ao soltar o Espaco
$("busca").onkeydown = (e) => { const v = $("mapas").querySelector(".linha:not([hidden]) .abre"); if (e.key === "ArrowDown" && v) { e.preventDefault(); v.focus(); } };
addEventListener("keydown", (e) => {
  if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) || document.querySelector("dialog[open]") || $("filtro").hidden) return;
  e.preventDefault(); $("busca").focus();
});
$("lote-regerar").onclick = async () => {  // refaz os marcados por inteiro com o gerador e os gostos de agora; entra na fila
  if (!await confirmar("confirma_regerar", "regerar_marcados")) return;
  try { await api("/api/regerar", { zips: [...marcados] }); marcados.clear(); pintarLista(); atualizar(); } catch (x) { falhou(x); }
};
$("refazer-todos").onclick = async () => {  // depois de uma melhoria do gerador: todos os mapas da lista entram na fila para serem refeitos por inteiro
  if (!await confirmar("confirma_refazer_todos", "refazer_todos")) return;
  try { await api("/api/regerar", { zips: listadas.map((m) => m.zip) }); atualizar(); } catch (x) { falhou(x); }
};
async function apagar(zips) {  // sem perguntar: vai para saida\lixeira e o aviso traz o Desfazer, que e mais rapido que confirmar toda vez
  const feitos = [];
  try { for (const zip of zips) { await api("/api/apagar", { zip }); feitos.push(zip); marcados.delete(zip); } } catch (x) { falhou(x); }
  await atualizar(); pintarLista();
  if (!feitos.length) return;
  avisar(t(feitos.length === 1 ? "apagado_um" : "apagado_varios", { n: feitos.length }), false, "", { texto: t("desfazer"), fazer: async () => {
    try { for (const zip of feitos) await api("/api/restaurar", { zip }); } catch (x) { falhou(x); }
    await atualizar(); if (feitos.length === 1) abrir(feitos[0]);
  } });
}
$("lote-apagar").onclick = () => apagar([...marcados]);
$("lote-enviar").onclick = () => enviar([...marcados], $("lote-enviar")).then(() => { marcados.clear(); pintarLista(); });
async function enviar(zips, botao, forcar = false) {  // um aviso por mapa que falhou, um com quantos foram e um com quantos ja estavam iguais (so o forcar manda esses)
  botao.disabled = true; avisar(t("mandando"));
  try {
    const res = await api("/api/quest", { zips, forcar }), r = res.resultados, bons = zips.filter((z) => z in r && !r[z]), igual = zips.filter((z) => !(z in r)).length, porcima = bons.filter((z) => res.situacao[z] === "velho").length;
    for (const z of zips) if (r[z]) { const e = lerErro(r[z]); avisar(t("q_falhou", { nome: (estado.mapas.find((m) => m.zip === z) || {}).nome || z }) + " " + e.msg, true, e.detalhe); }
    if (bons.length) avisar(t(bons.length === 1 ? "q_enviado" : "q_enviados", { n: bons.length }) + (porcima ? " " + t("q_por_cima", { n: porcima }) : ""));
    if (igual) avisar(t(bons.length ? "q_iguais" : "q_tudo_igual", { n: igual }));
    if (res.playlists) avisar(t("q_playlists", { n: res.playlists }));
  } catch (x) { falhou(x); }
  botao.disabled = false; await verQuest();
}
async function atualizar() {
  clearTimeout(atualizar.t);
  try { estado = await api("/api/estado"); } catch (x) { atualizar.t = setTimeout(atualizar, 6000); return; }
  for (const tr of estado.trabalhos) if (tr.estado === "pronto") { if (!primeira && !vistos.has(tr.id) && tr.zip && !estado.trabalhos.some((o) => ["na fila", "rodando"].includes(o.estado))) abrir(tr.zip); vistos.add(tr.id); }  // acabou agora: abre (no meio de uma fila nao, para nao tomar a tela a cada faixa)
  primeira = false;
  if (atual && !estado.mapas.some((m) => m.zip === atual)) fechar();  // o mapa aberto sumiu da pasta
  pintarTrabalhos(); pintarLista();
  if (mapa && $("visor").hidden === estado.visor) pintarMapa();  // o visualizador acabou de ser instalado
  atualizar.t = setTimeout(atualizar, estado.trabalhos.some((tr) => ["na fila", "rodando"].includes(tr.estado)) ? 1200 : 6000);
}

// ---------- detalhe do mapa aberto
async function abrir(zip) {
  try { mapa = await api("/api/mapa?zip=" + enc(zip)); } catch (x) { return falhou(x); }
  if (atual !== zip) { const f = $("aberto"); f.classList.remove("troca"); void f.offsetWidth; f.classList.add("troca"); }  // fade curto ao trocar de mapa, nao a cada atualizacao
  atual = zip; ls.gravar(ULTIMO, zip); document.body.classList.add("vendo"); $("mais").open = false;
  if (!mapa.difs.some((d) => d.nome === dif)) dif = mapa.difs.some((d) => d.nome === "Expert") ? "Expert" : mapa.difs[0].nome;
  pintarMapa(); pintarLista();
  clearTimeout(abrir.t);
  if (mapa.conferindo) abrir.t = setTimeout(() => atual === zip && abrir(zip), 3000);  // mapa antigo sendo conferido agora: pergunta de novo
}
function fechar() {
  atual = mapa = null; document.body.classList.remove("vendo"); $("visor").removeAttribute("src"); $("visor").dataset.de = "";
  pintarMapa(); pintarLista();
}
$("voltar").onclick = fechar;  // volta ao inicio, no celular e no computador
document.querySelector(".marca").onclick = () => { if (atual) fechar(); };  // o logo tambem leva ao inicio
const falhas = (r) => (r ? r.metas.filter((m) => !m.ok).length + (r.esquema_ok && r.notas ? 0 : 1) : 0);
function valorMeta(m) {
  if (m.id === "esquema") return "";
  if (m.id === "paridade") return t("v_paridade", { erros: num(m.erros), avisos: num(m.avisos), golpes: num(m.golpes) });
  if (m.id === "grade") return pct(m.fracao, 1);
  if (m.id.startsWith("folga")) return t("v_seg", { n: num(m.s, 1) });
  if (m.id === "nps") return t("v_nps", { n: num(m.valor, 2), a: num(m.faixa[0], 2), b: num(m.faixa[1], 2) });
  return onde(m);
}
const onde = (v) => (v.n ? t("v_ex", { n: num(v.n), t: v.ex.map(tempo).join(", ") }) : "0");
function carregando() {  // ate o ArcViewer baixar e montar (ai ele mostra a barra dele) fica um aviso no lugar da caixa preta
  const c = $("carrega"), fim = () => { c.hidden = true; clearTimeout(carregando.limite); }; c.hidden = false;
  $("visor").onload = fim; clearTimeout(carregando.limite); carregando.limite = setTimeout(fim, 20000);  // se o load nunca vier, nao prende o aviso
}
function pintarMapa() {
  $("aberto").hidden = !mapa; $("vazio").hidden = !!mapa || estado.mapas.length > 0; $("inicio").hidden = $("in-fundo").hidden = !!mapa || !estado.mapas.length;
  if (!mapa) return;
  const R = mapa.relatorio, d = mapa.difs.find((x) => x.nome === dif), r = R && R.difs.find((x) => x.nome === dif);
  const capa = `/api/capa?zip=${enc(atual)}&v=${mapa.v}`;
  if ($("f-capa").getAttribute("src") !== capa) $("f-capa").src = capa;
  $("f-nome").textContent = mapa.nome; $("f-artista").textContent = mapa.artista;
  const info = $("f-info"); info.textContent = "";
  for (const x of [mapa.album, mapa.ano, num(mapa.bpm) + " BPM", R && tempo(R.dur), (mapa.mods || []).length && t("feito_com", { mods: mapa.mods.map((m) => t("mod_" + m)).join(", ") })]) if (x) info.append(el("span", "", x));
  if (/^https?:\/\//.test(mapa.link || "")) { const a = el("a", "", t("fonte")); a.href = mapa.link; a.target = "_blank"; a.rel = "noopener"; info.append(a); }

  // abas: so sao refeitas quando o mapa muda, para o foco do teclado ficar na aba clicada
  const chave = JSON.stringify([atual, mapa.difs.map((x) => x.nome), R && R.difs.map(falhas), lingua]);
  if (chave !== pintarMapa.chave) {
    pintarMapa.chave = chave; $("difs").textContent = "";
    for (const x of mapa.difs) {
      const b = el("button", "dif", NOMES[x.nome] || x.nome), ruim = falhas(R && R.difs.find((y) => y.nome === x.nome)) > 0;
      b.type = "button"; b.dataset.n = x.nome; b.classList.toggle("falha", ruim); if (ruim) b.setAttribute("aria-label", b.textContent + ", " + t("tag_falhou"));
      b.onclick = () => { dif = x.nome; pintarMapa(); }; $("difs").append(b);
    }
  }
  for (const b of $("difs").children) b.setAttribute("aria-pressed", b.dataset.n === dif);

  // copia local do ArcViewer; noProxy = le o zip direto deste PC, nada sobe para a internet. Trocar de dificuldade recarrega (uns segundos)
  const visor = `/arcviewer/?noProxy=true&difficulty=${dif}&url=` + enc(location.origin + "/zip/" + enc(atual)), de = visor + mapa.v;
  $("visor").hidden = $("dica").hidden = !estado.visor; $("sem-visor").hidden = estado.visor;
  if (estado.visor && $("visor").dataset.de !== de) { $("visor").dataset.de = de; $("visor").src = visor; $("fora").href = visor; carregando(); }

  const nums = $("numeros"); nums.textContent = "";
  for (const [k, v] of [["notas", num(d.notas)], ["nps", r && r.nps ? num(r.nps, 2) : "–"], ["vel", num(d.njs)], ["paredes", r && r.notas ? num(r.paredes) : "–"], ["arcos", num(d.arcos)]]) {
    const c = el("div"); c.append(el("dt", "", t("n_" + k)), el("dd", "", v)); nums.append(c);
  }

  const total = R ? R.difs.reduce((s, x) => s + falhas(x), 0) + (R.info_ok ? 0 : 1) : 0, ve = $("veredito"), sem = !R ? "sem" : total ? "nao" : "ok";
  ve.textContent = !R ? t(mapa.conferindo ? "v_conferindo" : "v_sem") : !total ? t("v_ok") : t(total === 1 ? "v_nao_um" : "v_nao_varios", { n: total });
  $("selo").className = "selo " + sem; $("selo-i").setAttribute("href", "#i-" + (sem === "ok" ? "ok" : sem === "nao" ? "nao" : "tempo"));  // o selo repete o veredito ao lado do titulo, onde ninguem precisa rolar
  const ul = $("metas"); ul.textContent = "";
  const linha = (ok, txt, v) => { const li = el("li", ok ? "" : "nao"); li.append(icone(ok ? "ok" : "nao"), el("span", "", txt), el("span", "v", v)); li.firstChild.setAttribute("role", "img"); li.firstChild.setAttribute("aria-label", t(ok ? "passou" : "nao_passou")); ul.append(li); };
  if (r && !r.esquema_ok) linha(false, t("meta_esquema"), r.erro || "");
  else if (r && !r.notas) linha(false, t("meta_sem_notas"), "");
  else if (r) for (const m of r.metas) linha(m.ok, t("meta_" + m.id), valorMeta(m));
  const tec = $("tecnico"); tec.textContent = ""; $("tec-caixa").hidden = !(r && r.notas);
  if (r && r.notas) {
    const g = r.gerador, D = r.direcoes;
    for (const [k, v] of [
      ["tec_bpm", num(R.bpm_detectado, 1) + " (" + t(R.bpm_fixo ? "bpm_fixo" : "bpm_variavel") + ")"], ["tec_tempos", num(r.tempos)], ["tec_duplas", num(r.duplas)], ["tec_luzes", num(r.luzes)],
      ["tec_cruzadas", onde(r.cruzadas)], ["tec_corridas", onde(r.corridas)], ["tec_pausa", t("v_seg", { n: num(r.maior_pausa, 1) })], ["tec_sobra", t("v_seg", { n: num(r.sobra_fim, 1) })],
      ["tec_salto", num(r.salto_m, 1) + " m"], ["tec_reacao", num(r.reacao_ms) + " ms"], ["tec_ataques_p", pct(r.ataques_precisao)], ["tec_ataques_c", pct(r.ataques_cobertura)],
      ["tec_direcoes", t("v_direcoes", { cima: D[0], baixo: D[1], esq: D[2], dir: D[3], diag: D[4] + D[5] + D[6] + D[7], ponto: D[8] })],
      ["tec_linhas", t("v_linhas", { baixo: r.linhas[0], meio: r.linhas[1], cima: r.linhas[2] })],
      ["tec_correlacao", r.correlacao == null ? "–" : num(r.correlacao, 2)],
      ["tec_janelas", g ? t("v_janelas", { a: g.padrao4, b: g.padrao2, c: g.padrao1, r: g.regra }) : null],
    ]) if (v != null) tec.append(el("dt", "", t(k)), el("dd", "", v));
  }

  const la = quest.mapas[atual];
  $("quest").hidden = !quest.conectado; $("quest").textContent = t(la === "ok" ? "q_de_novo" : la ? "q_atualizar" : "quest"); $("q-apagar").hidden = !la || !quest.conectado;
  $("baixar").href = "/api/zip?zip=" + enc(atual); $("baixar").className = quest.conectado ? "sec" : "acao";  // so uma acao em destaque: o Quest, ou o zip quando nao ha Quest
}
$("selo").onclick = () => $("conf").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
$("mais").onclick = (e) => { if (e.target.closest(".menu button")) $("mais").open = false; };
addEventListener("click", (e) => { if (!$("mais").contains(e.target)) $("mais").open = false; });
addEventListener("keydown", (e) => { if (e.key === "Escape") $("mais").open = false; });
$("quest").onclick = () => enviar([atual], $("quest"), true);  // o botao do mapa aberto e um pedido explicito: manda mesmo se ja estiver igual
$("q-apagar").onclick = async () => {
  if (!await confirmar("confirma_q_apagar", "q_apagar")) return;
  try { await api("/api/quest/apagar", { zip: atual }); avisar(t("q_apagado")); } catch (x) { falhou(x); }
  verQuest();
};
$("apagar").onclick = () => apagar([atual]);
$("renomear").onclick = () => { $("n-nome").value = mapa.nome; $("n-artista").value = mapa.artista; $("d-nome").returnValue = ""; $("d-nome").showModal(); };
$("d-nome").onclose = async () => {
  if ($("d-nome").returnValue !== "sim") return;
  try { await api("/api/renomear", { zip: atual, nome: $("n-nome").value, artista: $("n-artista").value }); await abrir(atual); await atualizar(); } catch (x) { falhou(x); }
};
$("regerar").onclick = () => {  // so a dificuldade que esta aberta; as outras ficam como estao
  $("r-titulo").textContent = t("regerar_titulo", { dif: NOMES[dif] }); $("r-dens").value = 1; dens("r-dens"); $("d-regerar").returnValue = ""; $("d-regerar").showModal();
};
$("d-regerar").onclose = async () => {
  if ($("d-regerar").returnValue !== "sim") return;
  const zip = atual, qual = dif; $("regerar").disabled = true; avisar(t("regerando", { dif: NOMES[qual] }));
  try { await api("/api/regerar", { zip, dif: qual, densidade: +$("r-dens").value }); avisar(t("regerado", { dif: NOMES[qual] })); if (atual === zip) await abrir(zip); atualizar(); } catch (x) { falhou(x); }
  $("regerar").disabled = false;
};
$("instalar-visor").onclick = async () => { try { await api("/api/preparo", { item: "visor" }); seguirVisor(); } catch (x) { falhou(x); } };
async function seguirVisor() {  // a barra do download fica ali mesmo, no lugar do visualizador
  const e = (await api("/api/preparo")).visor;
  $("instalar-visor").hidden = e.rodando; $("visor-andamento").hidden = !e.rodando;
  if (e.total) { $("visor-barra").max = e.total; $("visor-barra").value = e.feito; $("visor-quanto").textContent = mb(e.feito) + " / " + mb(e.total); }
  if (e.ok) return atualizar();
  if (e.rodando) return setTimeout(seguirVisor, 1000);
  if (e.erro) avisar(t("falhou"), true, e.erro);
}

// ---------- primeira vez e configuracao: o mesmo painel. passo 1 a 3 = primeira vez (uma parte por vez); 0 = tudo junto
let passo = 0;
const salvar = async (d) => { cfg = { ...cfg, ...(await api("/api/config", d)) }; };
async function verPreparo() {
  const p = await api("/api/preparo"), ul = $("itens");
  for (const i of ITENS) {  // uma linha por item, feita uma vez e depois so atualizada: o foco do teclado nao some durante um download
    let li = $("it-" + i);
    if (!li) {
      li = el("li"); li.id = "it-" + i;
      const s = el("span", "s"), b = el("button", "sec"); b.type = "button"; b.onclick = async () => { await api("/api/preparo", { item: i }); verPreparo(); };
      s.append(el("progress"), el("span"), b); li.append(el("b"), s, el("span", "d"), el("p", "erro")); ul.append(li);
    }
    const e = p[i], [n, s, d, x] = li.children, [barra, txt, b] = s.children, falta = !e.ok && !e.rodando;
    n.textContent = t("i_" + i) + (e.obrigatorio ? "" : " (" + t("opcional") + ")"); d.textContent = t("d_" + i);
    s.classList.toggle("ok", e.ok); barra.hidden = !e.rodando || e.ok; b.hidden = !falta; b.textContent = t("instalar");
    if (e.total) { barra.max = e.total; barra.value = e.feito; } else barra.removeAttribute("value");  // sem valor = tamanho desconhecido
    txt.textContent = e.ok ? t("instalado") : !e.rodando ? "" : i === "padroes" ? (e.total ? e.feito + " / " + e.total : t("montando")) : e.total ? mb(e.feito) + " / " + mb(e.total) : e.feito ? mb(e.feito) : t("trabalhando");
    x.hidden = !(e.erro && !e.ok); x.textContent = t("falhou") + " " + (e.erro || "");
  }
  const ativo = ITENS.some((i) => p[i].rodando);
  $("p-tudo").hidden = ativo || ITENS.every((i) => p[i].ok);
  verPreparo.falta = ITENS.some((i) => p[i].obrigatorio && !p[i].ok);
  botoes();
  clearTimeout(verPreparo.t);
  if ($("painel").open) verPreparo.t = setTimeout(verPreparo, ativo ? 1000 : 5000);
}
$("p-tudo").onclick = async () => { await api("/api/preparo", { item: "tudo" }); verPreparo(); };

function pintarQuest() {
  $("q-estado").textContent = t(quest.conectado ? "q_on" : quest.ip ? "q_off" : "q_configurar"); $("q-estado").classList.toggle("ok", !!quest.conectado);
  $("q-texto").textContent = t(!quest.adb ? "q_sem_adb" : quest.conectado ? "q_conectado" : quest.ip ? "q_nao_responde" : "q_sem_ip") + (quest.conectado ? " (" + quest.ip + ")" : "");
  $("q-parear").disabled = $("q-procurar").disabled = $("q-testar").disabled = !quest.adb;
  document.body.classList.toggle("com-quest", !!quest.conectado);
}
async function verQuest() {
  clearTimeout(verQuest.t); verQuest.t = setTimeout(verQuest, 15000);
  try { quest = await api("/api/quest"); } catch (x) { return; }
  if (document.activeElement !== $("q-ip")) $("q-ip").value = quest.ip;
  pintarQuest(); pintarLista(); pintarMapa();
}
async function comQuest(botao, pedido) {  // os dois botoes do Quest: trava, tenta, mostra o erro
  $("q-erro").hidden = true; botao.disabled = true;
  try { await pedido(); } catch (x) { $("q-erro").textContent = x.message; $("q-erro").hidden = false; }
  await verQuest();
}
$("q-parear").onclick = () => comQuest($("q-parear"), () => api("/api/quest/parear", {}));
$("q-procurar").onclick = () => comQuest($("q-procurar"), () => api("/api/quest/procurar", {}));
$("q-testar").onclick = () => comQuest($("q-testar"), async () => {
  const ip = $("q-ip").value.trim(); await salvar({ quest_ip: ip });
  if (cfg.quest_ip !== ip) throw new Error(t("ip_ruim"));
});

async function verConfig() {
  cfg = await api("/api/config");
  $("c-cache").textContent = t("cache_tam", { n: mb(cfg.cache) }); $("c-torch").textContent = t(cfg.placa ? "motor_placa" : "motor_cpu");
  $("c-dens").value = cfg.densidade; dens("c-dens"); $("c-rapido").checked = cfg.modo === "rapido";
  $("c-sem-topo").checked = !!cfg.sem_topo; $("c-sem-fila").checked = !!cfg.sem_fila; $("c-sabres").checked = !!cfg.sabres_capa; $("c-chroma").checked = !!cfg.chroma; $("c-noodle").checked = !!cfg.noodle;
  for (const b of $("c-cruzar").children) b.setAttribute("aria-pressed", b.dataset.v === cfg.cruzar);
  alternadores("c-difs", cfg.difs, () => (marcadasEm("c-difs").length ? salvar({ difs: marcadasEm("c-difs") }) : verConfig()));  // a ultima marcada nao sai
  pintarDiscord();
}
// avisos no Discord: o endereco do webhook nunca volta inteiro do servidor (cfg.discord_url e so o fim dele)
const DC = ["andamento", "pronto", "erro", "fim"], dcErro = (x) => { $("dc-erro").textContent = x ? x.message + (x.detalhe ? " (" + x.detalhe + ")" : "") : ""; $("dc-erro").hidden = !x; };
function pintarDiscord() {
  $("dc-texto").textContent = cfg.discord_url ? t("dc_ligado", { url: cfg.discord_url }) : t("dc_desligado");
  $("dc-remover").hidden = $("dc-testar").hidden = !cfg.discord_url;
  for (const ev of DC) $("dc-ev-" + ev).checked = (cfg.discord_eventos || []).includes(ev);
}
$("dc-salvar").onclick = async () => {
  dcErro();
  try { await salvar({ discord_url: $("dc-url").value.trim() }); $("dc-url").value = ""; } catch (x) { dcErro(x); }
  pintarDiscord();
};
$("dc-remover").onclick = async () => { dcErro(); await salvar({ discord_url: "" }); pintarDiscord(); };
for (const ev of DC) $("dc-ev-" + ev).onchange = () => salvar({ discord_eventos: DC.filter((e) => $("dc-ev-" + e).checked) });
$("dc-testar").onclick = async () => {
  const b = $("dc-testar"); b.disabled = true; dcErro();
  try { await api("/api/discord/teste", {}); avisar(t("dc_enviado")); } catch (x) { dcErro(x); }
  b.disabled = false;
};
$("c-dens").onchange = () => salvar({ densidade: +$("c-dens").value });
$("c-sem-topo").onchange = () => salvar({ sem_topo: $("c-sem-topo").checked });
$("c-sem-fila").onchange = () => salvar({ sem_fila: $("c-sem-fila").checked });
$("c-sabres").onchange = () => salvar({ sabres_capa: $("c-sabres").checked });
$("c-chroma").onchange = () => salvar({ chroma: $("c-chroma").checked });
$("c-noodle").onchange = () => salvar({ noodle: $("c-noodle").checked });
for (const b of $("c-cruzar").children) b.onclick = async () => { await salvar({ cruzar: b.dataset.v }); verConfig(); };
$("c-rapido").onchange = () => salvar({ modo: $("c-rapido").checked ? "rapido" : "completo" });
$("c-limpar").onclick = async () => {
  if (!await confirmar("confirma_limpar", "limpar")) return;
  try { await api("/api/cache", {}); } catch (x) { falhou(x); }
  verConfig();
};

function botoes() {
  const p = $("painel");
  if (passo) p.dataset.passo = passo; else delete p.dataset.passo;
  $("p-passo").textContent = passo ? t("passo", { n: passo }) : ""; $("p-passo").hidden = !passo;
  $("p-titulo").textContent = t(passo ? "bemvindo" : "config");
  $("p-voltar").hidden = passo < 2;
  $("p-seguir").textContent = t(!passo ? "fechar" : passo < 3 ? "continuar" : "concluir");
  $("p-seguir").disabled = passo === 2 && !!verPreparo.falta;  // sem os obrigatorios nao da para gerar
}
function abrirPainel(n) {
  passo = n;
  if (!$("painel").open) $("painel").showModal();
  botoes(); verPreparo(); verQuest(); verConfig();
}
$("config").onclick = () => abrirPainel(0);
$("q-estado").onclick = () => { abrirPainel(0); $("s-quest").scrollIntoView(); };
$("p-voltar").onclick = () => { passo--; botoes(); };
$("p-seguir").onclick = async () => {
  if (passo && passo < 3) { passo++; return botoes(); }
  if (passo) await salvar({ pronto: true });
  $("painel").close();
};
$("painel").oncancel = (e) => { if (passo) e.preventDefault(); };  // Esc nao pula a primeira vez

[T.pt, T.en, cfg] = await Promise.all(["/site/i18n/pt.json", "/site/i18n/en.json", "/api/config"].map((u) => api(u)));
lingua = cfg.lingua || lingua;
traduzir(); atualizar();
const p = await api("/api/preparo");
// primeira vez, ou sumiu algo sem o qual nao da para gerar (ai abre direto na lista de itens)
if (!cfg.pronto || ITENS.some((i) => p[i].obrigatorio && !p[i].ok)) abrirPainel(cfg.pronto ? 2 : 1);
else verQuest();
