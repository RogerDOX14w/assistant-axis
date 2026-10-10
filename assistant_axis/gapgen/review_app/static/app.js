// The review page (coding_plan_review.md, section 3): plain JavaScript over the app's JSON API.
// State lives on the server (decisions.jsonl); this page only shows it and sends one action per button or key.
// Every action has a labelled button (the toolbar over the card, small buttons on each row; Roger 2026-10-10:
// "not a fan of having to learn keyboard shortcuts for a task I'll probably only be doing for less than a day");
// the keys stay as shortcuts, and both go through ACTIONS, so a button and its key never differ.
"use strict";

const ORDERS = ["cliques", "generator", "region"];
const PANES = ["members", "neighbours", "corpus", "opposed"];
const S = {
  order: null, queue: [], counts: null, card: null, qpos: -1,
  pane: "members", idx: { members: 0, neighbours: 0, corpus: 0, opposed: 0 },
  note: null, pinned: null, overlay: null,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function flash(msg, error) {
  const f = $("flash");
  f.textContent = msg || "";
  f.className = error ? "error" : "";
}

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `${r.status} ${r.statusText}`);
  return data;
}

// ------------------------------------------------------------------ loading

async function loadMeta() {
  const m = await api("/api/meta");
  $("batch").textContent = `review ${m.batch_id}`;
  document.title = `Review ${m.batch_id}`;
  S.order = S.order || m.default_order;
  if (!m.complete) flash("The graph is incomplete (a build stopped): resume the build before reviewing.", true);
}

async function loadQueue() {
  const q = await api(`/api/queue?order=${encodeURIComponent(S.order)}`);
  S.queue = q.items;
  S.counts = q.counts;
  renderCounts();
  renderQueue();
}

async function showGroup(card) {
  S.card = card;
  if (card) {
    S.idx = { members: Math.min(S.idx.members, Math.max(0, card.members.length - 1)), neighbours: 0, corpus: 0, opposed: 0 };
    const pos = S.queue.findIndex((it) => it.group === card.id || itemMatches(it, card));
    if (pos >= 0) S.qpos = pos;
  }
  renderCard();
  await loadQueue();
}

function itemMatches(it, card) {
  return it.source === card.source || (it.tier === "single" && card.members.length && card.members[0].key === it.members[0] && card.source === it.source);
}

async function act(body, okMsg) {
  try {
    const r = await api("/api/action", body);
    if (r.counts) S.counts = r.counts;
    if (r.group) {
      if (S.card && r.group.id !== S.card.id) S.idx.members = 0;
      await showGroup(r.group);
    } else {
      S.card = null;
      renderCard();
      await loadQueue();
    }
    if (okMsg !== null) flash(okMsg || describe(r.event));
    return r;
  } catch (e) {
    flash(e.message, true);
    return null;
  }
}

function describe(ev) {
  if (!ev) return "already open";
  const k = ev.key || (ev.keys || []).join(", ");
  switch (ev.action) {
    case "open": return `opened ${ev.group} (${ev.source}${ev.status === "proposed" ? ", proposed: Accept group takes it" : ""})`;
    case "accept": return `${ev.group} accepted as the working group`;
    case "drop": return `dropped ${k}`;
    case "merge_in": return `merged in ${k}`;
    case "nominate": return `nominated ${k}`;
    case "resolve": return `${ev.group} resolved: ${ev.resolution}${ev.nominated ? " " + ev.nominated : ""}`;
    case "start_antonym": return `antonym group ${ev.group} of ${ev.of}`;
    case "undo": return `undid decision ${ev.undoes}`;
    default: return ev.action;
  }
}

// ------------------------------------------------------------------ rendering

function renderCounts() {
  const c = S.counts;
  if (!c) return;
  $("order").textContent = `order: ${S.order} (o)`;
  $("counts").innerHTML =
    `<span>terms <b>${c.terms.handled}</b>/${c.terms.total} handled</span>` +
    `<span><span class="tier merged">M</span> <b>${c.merged.remaining}</b>/${c.merged.total} left</span>` +
    `<span><span class="tier proposed">P</span> <b>${c.proposed.remaining}</b>/${c.proposed.total} left</span>` +
    `<span><span class="tier single">S</span> <b>${c.single.remaining}</b>/${c.single.total} left</span>` +
    `<span class="muted">groups: ${c.groups_resolved} resolved, ${c.groups_open} open, ${c.groups_proposed_open} proposed</span>`;
}

function renderQueue() {
  const ol = $("queue");
  ol.innerHTML = S.queue.map((it, i) => {
    const cls = [it.status, i === S.qpos ? "current" : ""].join(" ");
    const t = { merged: "M", proposed: "P", single: "S" }[it.tier];
    const h = it.handled ? ` <span class="muted small">${it.handled}/${it.size}</span>` : "";
    return `<li class="${cls}" data-i="${i}" title="${esc(it.id)} ${esc(it.generator)} ${esc(it.region)}">` +
      `<span class="tier ${it.tier}">${t}</span><span class="labels">${esc(it.labels.join(", "))}</span>${h}</li>`;
  }).join("");
  const cur = ol.querySelector("li.current");
  if (cur) cur.scrollIntoView({ block: "nearest" });
}

function link(entry) {
  if (!entry.href) return `<span>${esc(entry.label)}</span>`;
  return `<a href="${esc(entry.href)}" target="_blank" rel="noopener" title="${esc(entry.path)}">${esc(entry.label)}</a>` +
    `<span class="path">${esc(entry.path)}${entry.kind === "queue" ? ": " + esc(entry.key.split(":")[1]) : ""}</span>`;
}

function hl(pane, i) { return S.pane === pane && S.idx[pane] === i ? " hl" : ""; }

function renderCard() {
  const c = S.card;
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("pane-focus", p.dataset.pane === S.pane));
  renderToolbar();
  if (!c) {
    $("card").innerHTML = `<p class="muted">Next group opens the next group in the queue; Find looks up a term; a click on the queue opens that group.</p>`;
    ["neighbours", "corpus", "opposed"].forEach((id) => { $(id).innerHTML = ""; });
    return;
  }
  const working = c.status === "open";                  // members can be nominated, neighbours merged in, resolved
  const shaping = working || c.status === "proposed";   // members can be excluded
  const status = `<span class="badge status-${c.status}">${c.status}${c.resolution ? ": " + esc(c.resolution) : ""}</span>`;
  let head = `<div class="card-head"><span class="gid">${esc(c.id)}</span>${status}` +
    `<span class="muted small">${esc(c.source)}${c.via ? " via " + esc(c.via) : ""}</span>` +
    (c.antonym_of ? `<span class="badge">antonym of ${esc(c.antonym_of)}</span>` : "") +
    (c.antonym_groups.length ? `<span class="badge">antonym group ${esc(c.antonym_groups.join(", "))}</span>` : "") + `</div>`;
  if (c.status === "proposed") head += `<div class="banner">Proposed group, not merged yet: <b>Accept group</b> takes it as it stands; <b>Exclude</b> a member first to split it.</div>`;
  if (c.status === "resolved") {
    const tgt = c.target ? " " + link(c.target) : "";
    head += `<div class="banner resolved">Resolved: ${esc(c.resolution)}${tgt}${c.nominated ? " (" + esc(labelOf(c, c.nominated)) + ")" : ""}` +
      `${c.note ? " · " + esc(c.note) : ""}.  <b>Next group</b> moves on; <b>Undo</b> takes the decision back.</div>`;
  }
  if (S.note) head += `<div class="banner">note for the next resolution: ${esc(S.note)}</div>`;
  const members = c.members.map((m, i) => {
    const cls = ["member", m.key === c.nominated ? "nominated" : "", m.handled_by && m.handled_by !== c.id ? "handled" : "", m.covered ? "covered" : ""].join(" ") + hl("members", i);
    const tags = (m.tags || []).map((t) => `<span class="chip">${esc(t)}</span>`).join("");
    const flags = (m.flags || []).map((f) => `<span class="badge flag">${esc(f)}</span>`).join("");
    const handled = m.handled_by && m.handled_by !== c.id ? `<span class="badge">handled by ${esc(m.handled_by)} (${esc(m.handled_resolution)})</span>` : "";
    const cov = m.covered_by ? `<span class="badge">covered by ${link(m.covered_by)}</span>` : "";
    const applied = m.applied ? `<span class="badge">registry: ${esc(m.applied)}${m.seed_queue_stem ? ", queued" : ""}</span>` : "";
    const groups = [...(m.merged || []), ...(m.proposed || [])].join(" ");
    const mine = !(m.handled_by && m.handled_by !== c.id);
    const btns = [
      working && mine && !m.covered && m.key !== c.nominated ? rowBtn("nominate", "Nominate", "n", "members", i, "make this the label promoted for the group (★)") : "",
      shaping && mine && c.members.length > 1 ? rowBtn("drop", "Exclude", "x", "members", i, "take this member out of the group") : "",
      rowBtn("details", "Details", "t", "members", i, "everything one edge away from this term"),
    ].join("");
    return `<li class="${cls}" data-pane="members" data-i="${i}"><span class="label">${esc(m.label)}</span>` +
      `<span class="row-btns">${btns}</span>` +
      `<span class="muted small"> ${esc(m.generator || "")} · ${esc(m.region || "")} · M3 ${esc(m.m3_decision || "")}` +
      `${groups ? " · " + esc(groups) : ""}</span>${tags}${flags}${handled}${cov}${applied}` +
      `<div class="gloss">${esc(m.gloss)}</div></li>`;
  }).join("");
  const others = c.neighbour_groups.length ? `<h2>Other groups sharing a member</h2><ol>` + c.neighbour_groups.map((g) =>
    `<li class="small"><span class="tier ${g.tier}">${g.tier === "merged" ? "M" : "P"}</span> ${esc(g.id)}: ${esc(g.labels.join(", "))} ` +
    `<span class="muted">(shares ${esc(g.shared.map((k) => labelOf(c, k)).join(", "))}; ${g.remaining} unhandled)</span></li>`).join("") + `</ol>` : "";
  $("card").innerHTML = head + `<h2 class="${S.pane === "members" ? "pane-focus" : ""}">Members <span class="muted small">★ marks the nominee, the label that is promoted</span></h2><ol>${members}</ol>${others}`;

  $("neighbours").innerHTML = c.neighbours.map((n, i) => {
    const h = n.handled_by ? ` <span class="badge">handled ${esc(n.handled_by)}</span>` : "";
    const grp = [...n.merged, ...n.proposed].join(" ");
    const many = n.merge_keys.length > 1 ? ` (${n.merge_keys.length})` : "";
    const btns = [
      working && !n.handled_by ? rowBtn("merge_in", `Merge in${many}`, "m", "neighbours", i,
        many ? `pull this neighbour and its merged group (${n.merge_keys.length} terms) into this group` : "pull this neighbour into this group") : "",
      rowBtn("details", "Details", "t", "neighbours", i, "everything one edge away from this term"),
    ].join("");
    return `<li class="entry${hl("neighbours", i)}" data-pane="neighbours" data-i="${i}"><span class="level l${n.level}">${n.level}</span> ` +
      `<b>${esc(n.label)}</b><span class="row-btns">${btns}</span> <span class="muted small">${fmt(n.cosine)} · ${esc(n.readings || n.relation)} · to ${esc(n.via_label)}${grp ? " · " + esc(grp) : ""}</span>${h}` +
      `<div class="gloss">${esc(n.gloss)}</div></li>`;
  }).join("") || `<li class="muted small">no candidate neighbour</li>`;

  const corpus = S.pinned ? [S.pinned, ...c.corpus.filter((t) => t.key !== S.pinned.key)] : c.corpus;
  S.corpusView = corpus;
  $("corpus").innerHTML = corpus.map((t, i) => {
    const cov = (t.covered || []).length ? `<div class="covered-list">covered by M3: ${t.covered.map((x) => esc(x.label) + " " + esc(x.reading) + (x.handled_by ? " (handled)" : "")).join(", ")}</div>` : "";
    const pin = t === S.pinned ? " pinned" : "";
    const btns = working ? rowBtn("merge_into", "Covered by this", "c", "corpus", i,
      "resolve the group as already covered by this corpus trait or queue entry (its labels go to the synonyms list)") : "";
    return `<li class="entry${pin}${hl("corpus", i)}" data-pane="corpus" data-i="${i}"><span class="level l${t.level || 0}">${t.level != null && t.level >= 0 ? t.level : ""}</span> ` +
      `${link(t)}<span class="row-btns">${btns}</span> <span class="muted small">${t.cosine != null ? fmt(t.cosine) + " · " : ""}${esc(t.reading || t.relation || "found")}${t.via_label ? " · from " + esc(t.via_label) : ""}</span>` +
      `<div class="gloss">${esc(t.gloss)}</div>${cov}</li>`;
  }).join("") || `<li class="muted small">no corpus trait read</li>`;

  $("opposed").innerHTML = c.opposed.map((o, i) => {
    const many = o.kind === "candidate" && o.antonym_keys && o.antonym_keys.length > 1 ? ` (${o.antonym_keys.length})` : "";
    const btns = c.status === "resolved" && o.kind === "candidate" && !o.handled_by
      ? rowBtn("antonym", `Start antonym group${many}`, "a", "opposed", i, "open a new group for this opposed candidate, linked as this group's antonym") : "";
    return `<li class="entry${hl("opposed", i)}" data-pane="opposed" data-i="${i}">` +
      (o.kind === "candidate" ? `<b>${esc(o.label)}</b>` : link(o)) + `<span class="row-btns">${btns}</span>` +
      ` <span class="muted small">${fmt(o.cosine)} · to ${esc(o.via_label)}</span>` +
      `${o.handled_by ? ` <span class="badge">handled ${esc(o.handled_by)}</span>` : ""}</li>`;
  }).join("") || `<li class="muted small">no opposed neighbour</li>`;
  const cur = document.querySelector(".hl");
  if (cur) cur.scrollIntoView({ block: "nearest" });
}

const fmt = (x) => (x == null ? "" : Number(x).toFixed(2));
function labelOf(card, key) {
  const m = card.members.find((x) => x.key === key);
  return m ? m.label : key;
}

// ------------------------------------------------------------------ actions

function current(pane) {
  const c = S.card;
  if (!c) return null;
  const list = { members: c.members, neighbours: c.neighbours, corpus: S.corpusView || c.corpus, opposed: c.opposed }[pane];
  return list && list.length ? list[Math.min(S.idx[pane], list.length - 1)] : null;
}

function needCard() {
  if (!S.card) { flash("no group open: Next group opens one", true); return false; }
  return true;
}

async function nextGroup() {
  await loadQueue();
  const n = S.queue.length;
  for (let step = 1; step <= n; step++) {
    const i = (S.qpos + step + n) % n;
    const it = S.queue[i];
    if (it.status !== "done" && (!S.card || it.group !== S.card.id)) {
      S.qpos = i;
      return act({ action: "open", source: it.source });
    }
  }
  flash("the queue is done: every term is handled");
  return null;
}

async function resolve(resolution) {
  if (!needCard()) return;
  const body = { action: "resolve", group: S.card.id, resolution };
  if (S.note) body.note = S.note;
  const r = await act(body);
  if (r) { S.note = null; S.pinned = null; renderCard(); }
}

async function onEnter() {
  if (!needCard()) return;
  if (S.card.status === "proposed") return act({ action: "accept", group: S.card.id });
  if (S.card.status === "resolved") return nextGroup();
  return resolve("promote");
}

async function startAntonym() {
  if (!needCard()) return;
  if (S.card.status !== "resolved") { flash("resolve this group first; then Start antonym group opens its antonym", true); return; }
  let o = S.pane === "opposed" ? current("opposed") : null;
  if (!o || o.kind !== "candidate") o = S.card.opposed.find((x) => x.kind === "candidate" && !x.handled_by);
  if (!o) { flash("no opposed term to start from: open the antonym's group with Find instead", true); return; }
  return act({ action: "start_antonym", of: S.card.id, keys: o.antonym_keys && o.antonym_keys.length ? o.antonym_keys : [o.key] });
}

async function mergeIntoCorpus() {
  if (!needCard()) return;
  const t = current("corpus");
  if (!t) { flash("no corpus trait to merge into: use Same as this on a row of the corpus list, or Find one", true); return; }
  return resolve(`merge_into:${t.key}`);
}

function editNote() {
  const t = window.prompt("Note saved with the next resolution (empty clears it)", S.note || "");
  if (t === null) return;                     // cancelled: keep the note as it was
  S.note = t.trim() || null;
  renderCard();
}

async function nextOrder() {
  S.order = ORDERS[(ORDERS.indexOf(S.order) + 1) % ORDERS.length];
  S.qpos = -1;
  await loadQueue();
  renderToolbar();
  flash(`queue order: ${S.order}`);
}

// Every action, by name: the toolbar's and the rows' buttons (data-act) and the keys all call these.  A row's
// button first makes its row the highlighted one (S.pane, S.idx), so the row actions work on "current".
const ACTIONS = {
  next: () => nextGroup(),
  accept: () => needCard() && act({ action: "accept", group: S.card.id }),
  promote: () => resolve("promote"),
  reject: () => resolve("reject"),
  park: () => resolve("park"),
  defer: () => resolve("defer"),
  merge_into: () => mergeIntoCorpus(),
  drop: () => { const m = current("members"); return needCard() && m && act({ action: "drop", group: S.card.id, key: m.key }); },
  nominate: () => { const m = current("members"); return needCard() && m && act({ action: "nominate", group: S.card.id, key: m.key }); },
  merge_in: () => {
    const nb = current("neighbours");
    return needCard() && nb && act({ action: "merge_in", group: S.card.id, keys: nb.merge_keys.length ? nb.merge_keys : [nb.key] });
  },
  antonym: () => startAntonym(),
  note: () => editNote(),
  undo: () => act({ action: "undo" }),
  find: () => openFind(),
  details: () => termView(),
  order: () => nextOrder(),
  help: () => help(),
};

// A button: data-act names its ACTIONS entry; a row's button carries its row (data-pane, data-i).  Its shortcut,
// when a letter, is the first occurrence of that letter in the text, bolded (Roger: "bold the keyboard shortcut in
// the text word"); a key that is no letter of the text (Space, Enter, /, ;, ?) is shown as a small hint after it.
function keyedLabel(text, key) {
  if (key && key.length === 1 && /[a-z]/i.test(key)) {
    // the letter at the start of a word if there is one ("Start antonym group"), else its first occurrence ("Exclude")
    const w = text.search(new RegExp(`\\b${key}`, "i"));
    const i = w >= 0 ? w : text.toLowerCase().indexOf(key.toLowerCase());
    if (i >= 0) return `${esc(text.slice(0, i))}<b class="kl">${esc(text[i])}</b>${esc(text.slice(i + 1))}`;
  }
  return esc(text) + (key ? `<span class="k">${esc(key)}</span>` : "");
}

function btn(action, text, key, opts = {}) {
  const cls = ["btn", opts.cls || ""].join(" ").trim();
  const row = opts.pane != null ? ` data-pane="${opts.pane}" data-i="${opts.i}"` : "";
  const tip = (opts.title || text) + (key ? ` (key: ${key})` : "");
  return `<button type="button" class="${cls}" data-act="${action}"${row} title="${esc(tip)}">${keyedLabel(text, key)}</button>`;
}
const rowBtn = (action, text, key, pane, i, title) => btn(action, text, key, { cls: "mini", pane, i, title });

// The toolbar over the card: what can be done to the open group now, then the always-there buttons.
function renderToolbar() {
  const c = S.card, b = [];
  if (!c || c.status === "resolved") {
    b.push(btn("next", "Next group", "Space", { cls: "primary", title: "open the next unhandled group in the queue" }));
    if (c && c.opposed.some((o) => o.kind === "candidate" && !o.handled_by))
      b.push(btn("antonym", "Start antonym group", "a", { title: "open a group for the first unhandled opposed candidate (or use the button on its row)" }));
  } else if (c.status === "proposed") {
    b.push(btn("accept", "Accept group", "g", { cls: "primary", title: "take the proposed group as it stands; Drop a member first to split it" }));
    b.push(btn("next", "Skip to next group", "Space"));
  } else {
    const nom = c.nominated ? labelOf(c, c.nominated) : null;
    b.push(btn("promote", nom ? `Promote "${nom}"` : "Promote", "Enter",
      { cls: "primary", title: "send the nominated member (★) to the seed queue when the decisions are applied" }));
    b.push(btn("reject", "Reject", "r", { cls: "danger", title: "not a trait worth adding" }),
      btn("park", "Park", "p", { title: "set aside for later; not rejected" }),
      btn("defer", "Defer", "d", { title: "decide later" }),
      btn("note", S.note ? "Edit note" : "Add note", ";", { title: "a note saved with the next resolution" }),
      btn("next", "Skip to next group", "Space"));
  }
  b.push(`<span class="sep"></span>`, btn("undo", "Undo", "u", { title: "undo the last decision" }),
    btn("find", "Find…", "/", { title: "find a term, a corpus trait or a queue entry" }),
    btn("order", `Order: ${S.order || ""}`, "o", { title: "the queue's order: cliques, generator, region" }),
    btn("help", "Keys", "?", { title: "the keyboard shortcuts (optional)" }));
  $("toolbar").innerHTML = b.join("");
}

// ------------------------------------------------------------------ overlays: find, term view, help

function closeOverlay() { $("overlay").hidden = true; $("overlay").innerHTML = ""; S.overlay = null; }

function openFind() {
  const o = $("overlay");
  o.hidden = false;
  o.innerHTML = `<button type="button" class="btn mini close" data-close="1">Close</button>` +
    `<input id="find" placeholder="find a term, a corpus trait or a queue entry (click a result, or Enter)" autocomplete="off"><table id="found"></table>`;
  S.overlay = { kind: "find", results: [], i: 0 };
  const input = $("find");
  input.focus();
  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const r = await api(`/api/find?q=${encodeURIComponent(input.value)}`);
      S.overlay.results = r.results; S.overlay.i = 0;
      renderFound();
    }, 120);
  });
}

function renderFound() {
  const ov = S.overlay;
  $("found").innerHTML = ov.results.map((x, i) =>
    `<tr class="${i === ov.i ? "hl" : ""}" data-found="${i}"><td>${x.href ? link(x) : esc(x.label)}</td><td class="muted small">${esc(x.kind)}${x.handled_by ? " · handled " + esc(x.handled_by) : ""}</td></tr>`).join("");
}

async function chooseFound() {
  const x = S.overlay.results[S.overlay.i];
  if (!x) return;
  closeOverlay();
  if (x.kind === "candidate") return act({ action: "open", source: `term:${x.key}` });
  if (x.kind === "covered") {
    if (!needCard()) return;
    return act({ action: "merge_in", group: S.card.id, keys: [x.key] }, `pulled in ${x.label} (covered by M3; it passes in as a synonym note)`);
  }
  S.pinned = { key: x.key, kind: x.kind, label: x.label, path: x.path, href: x.href, gloss: null };
  S.pane = "corpus"; S.idx.corpus = 0;
  renderCard();
  flash(`${x.label} pinned at the top of the corpus list: c merges into it`);
}

async function termView() {
  const pane = S.pane === "corpus" ? "members" : S.pane;
  const x = current(pane);
  if (!x || x.kind === "corpus" || x.kind === "queue") return;
  try {
    const t = await api(`/api/term/${encodeURIComponent(x.key)}`);
    const o = $("overlay");
    o.hidden = false;
    S.overlay = { kind: "term" };
    o.innerHTML = `<button type="button" class="btn mini close" data-close="1">Close</button>` +
      `<h2>${esc(t.term.label)} <span class="muted small">${esc(t.term.key)} · ${esc(t.term.generator)} · M3 ${esc(t.term.m3_decision)} · groups ${esc([...t.merged, ...t.proposed, ...t.groups].join(" ") || "none")}</span></h2>` +
      `<p class="gloss">${esc(t.term.gloss)}</p><table>` + t.edges.map((e) =>
        `<tr><td>${e.kind === "candidate" ? esc(e.label) : link(e)}</td><td class="muted small">${esc(e.relation)}</td><td class="small">${fmt(e.cosine)}</td>` +
        `<td class="small">${esc(e.readings)}${e.strict ? " · 4-edge" : e.proposed_edge ? " · 3-edge" : ""}</td></tr>`).join("") + `</table>`;
  } catch (e) { flash(e.message, true); }
}

function help() {
  const o = $("overlay");
  o.hidden = false;
  S.overlay = { kind: "help" };
  const keys = [
    ["j / k", "next / previous in the focused list"], ["Tab / Shift-Tab", "focus members, neighbours, corpus, opposed"],
    ["g", "Accept group: take the proposed group (Enter too)"], ["x", "Exclude: take the highlighted member out (never the last)"],
    ["m", "Merge in: pull the highlighted neighbour in (with its merged group)"], ["n", "Nominate the highlighted member"],
    ["Enter", "Promote the nominee (or accept a proposed group; Next group once resolved)"],
    ["c", "Covered by this: resolve as covered by the highlighted corpus trait or queue entry"],
    ["p / r / d", "Park / Reject / Defer"], [";", "Add note: a note for the next resolution"],
    ["a", "Start antonym group from the highlighted (or first) opposed term"],
    ["u", "Undo the last decision"], ["/", "Find a term, corpus trait or queue entry"], ["t", "Details: everything one edge away"],
    ["Space or .", "Next group in the queue"], ["o", "Order: the next queue order"], ["Esc", "close"]];
  o.innerHTML = `<button type="button" class="btn mini close" data-close="1">Close</button>` +
    `<h2>Keys <span class="muted small">optional: every key is also a button, its letter in bold</span></h2>` +
    `<table>${keys.map(([k, v]) => `<tr><td><kbd>${esc(k)}</kbd></td><td>${esc(v)}</td></tr>`).join("")}</table>`;
}

// ------------------------------------------------------------------ keys

function move(delta) {
  const c = S.card;
  if (!c) return;
  const n = { members: c.members.length, neighbours: c.neighbours.length, corpus: (S.corpusView || c.corpus).length, opposed: c.opposed.length }[S.pane];
  if (!n) return;
  S.idx[S.pane] = (S.idx[S.pane] + delta + n) % n;
  renderCard();
}

document.addEventListener("keydown", async (ev) => {
  if (S.overlay && S.overlay.kind === "find") {
    if (ev.key === "Escape") { closeOverlay(); return; }
    if (ev.key === "ArrowDown") { S.overlay.i = Math.min(S.overlay.i + 1, S.overlay.results.length - 1); renderFound(); ev.preventDefault(); return; }
    if (ev.key === "ArrowUp") { S.overlay.i = Math.max(S.overlay.i - 1, 0); renderFound(); ev.preventDefault(); return; }
    if (ev.key === "Enter") { ev.preventDefault(); await chooseFound(); }
    return;
  }
  if (S.overlay) { if (ev.key === "Escape" || ev.key === "?") closeOverlay(); return; }
  if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
  const k = ev.key;
  const handled = true;
  switch (k) {
    case "j": case "ArrowDown": move(1); break;
    case "k": case "ArrowUp": move(-1); break;
    case "Tab": {
      const i = PANES.indexOf(S.pane);
      S.pane = PANES[(i + (ev.shiftKey ? -1 : 1) + PANES.length) % PANES.length];
      renderCard(); break;
    }
    case "g": await ACTIONS.accept(); break;
    case "Enter": await onEnter(); break;
    case "x": await ACTIONS.drop(); break;
    case "n": await ACTIONS.nominate(); break;
    case "m": await ACTIONS.merge_in(); break;
    case "c": await ACTIONS.merge_into(); break;
    case "p": await ACTIONS.park(); break;
    case "r": await ACTIONS.reject(); break;
    case "d": await ACTIONS.defer(); break;
    case ";": ACTIONS.note(); break;
    case "a": await ACTIONS.antonym(); break;
    case "u": await ACTIONS.undo(); break;
    case "/": ACTIONS.find(); break;
    case "t": await ACTIONS.details(); break;
    case " ": case ".": await ACTIONS.next(); break;
    case "o": await ACTIONS.order(); break;
    case "?": ACTIONS.help(); break;
    case "Escape": S.pinned = null; renderCard(); break;
    default: return;
  }
  if (handled) ev.preventDefault();
});

// a click on a button never moves the keyboard focus to it (a focused button would also take Space and Enter)
document.addEventListener("mousedown", (ev) => { if (ev.target.closest("button.btn")) ev.preventDefault(); });

// clicks: a button runs its action (a row's button on its row); Close shuts an overlay; a Find result is chosen;
// a queue item opens it; a list row takes the highlight
document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (b) {
    if (b.dataset.pane) { S.pane = b.dataset.pane; S.idx[S.pane] = Number(b.dataset.i); }
    const f = ACTIONS[b.dataset.act];
    if (f) await f();
    return;
  }
  if (ev.target.closest("[data-close]")) { closeOverlay(); return; }
  if (ev.target.closest("a")) return;
  const fr = ev.target.closest("[data-found]");
  if (fr && S.overlay && S.overlay.kind === "find") { S.overlay.i = Number(fr.dataset.found); await chooseFound(); return; }
  const q = ev.target.closest("#queue li");
  if (q) { S.qpos = Number(q.dataset.i); await act({ action: "open", source: S.queue[S.qpos].source }); return; }
  const row = ev.target.closest("[data-pane][data-i]");
  if (row) { S.pane = row.dataset.pane; S.idx[S.pane] = Number(row.dataset.i); renderCard(); }
});

(async function init() {
  try {
    await loadMeta();
    await loadQueue();
    flash("Next group opens the first group. Every action is a button; the bold letter in a button is its optional key.");
  } catch (e) { flash(e.message, true); }
})();
