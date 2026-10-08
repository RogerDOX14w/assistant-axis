// The review page (coding_plan_review.md, section 3): plain JavaScript over the app's JSON API, keyboard first.
// State lives on the server (decisions.jsonl); this page only shows it and sends one action per key.
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
    case "open": return `opened ${ev.group} (${ev.source}${ev.status === "proposed" ? ", proposed: g accepts" : ""})`;
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
  if (!c) {
    $("card").innerHTML = `<p class="muted">Space opens the next group in the queue; / finds a term.</p>`;
    ["neighbours", "corpus", "opposed"].forEach((id) => { $(id).innerHTML = ""; });
    return;
  }
  const status = `<span class="badge status-${c.status}">${c.status}${c.resolution ? ": " + esc(c.resolution) : ""}</span>`;
  let head = `<div class="card-head"><span class="gid">${esc(c.id)}</span>${status}` +
    `<span class="muted small">${esc(c.source)}${c.via ? " via " + esc(c.via) : ""}</span>` +
    (c.antonym_of ? `<span class="badge">antonym of ${esc(c.antonym_of)}</span>` : "") +
    (c.antonym_groups.length ? `<span class="badge">antonym group ${esc(c.antonym_groups.join(", "))}</span>` : "") + `</div>`;
  if (c.status === "proposed") head += `<div class="banner">Proposed group, not merged: <kbd>g</kbd> or <kbd>Enter</kbd> accepts it; <kbd>x</kbd> drops a member first.</div>`;
  if (c.status === "resolved") {
    const tgt = c.target ? " " + link(c.target) : "";
    head += `<div class="banner resolved">Resolved: ${esc(c.resolution)}${tgt}${c.nominated ? " (" + esc(labelOf(c, c.nominated)) + ")" : ""}` +
      `${c.note ? " · " + esc(c.note) : ""}. <kbd>a</kbd> starts the antonym group, <kbd>Space</kbd> the next group, <kbd>u</kbd> undoes.</div>`;
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
    return `<li class="${cls}" data-pane="members" data-i="${i}"><span class="label">${esc(m.label)}</span>` +
      `<span class="muted small"> ${esc(m.generator || "")} · ${esc(m.region || "")} · M3 ${esc(m.m3_decision || "")}` +
      `${groups ? " · " + esc(groups) : ""}</span>${tags}${flags}${handled}${cov}${applied}` +
      `<div class="gloss">${esc(m.gloss)}</div></li>`;
  }).join("");
  const others = c.neighbour_groups.length ? `<h2>Other groups sharing a member</h2><ol>` + c.neighbour_groups.map((g) =>
    `<li class="small"><span class="tier ${g.tier}">${g.tier === "merged" ? "M" : "P"}</span> ${esc(g.id)}: ${esc(g.labels.join(", "))} ` +
    `<span class="muted">(shares ${esc(g.shared.map((k) => labelOf(c, k)).join(", "))}; ${g.remaining} unhandled)</span></li>`).join("") + `</ol>` : "";
  $("card").innerHTML = head + `<h2 class="${S.pane === "members" ? "pane-focus" : ""}">Members <span class="muted small">j/k · n nominates · x drops · Enter promotes</span></h2><ol>${members}</ol>${others}`;

  $("neighbours").innerHTML = c.neighbours.map((n, i) => {
    const merge = n.merge_keys.length > 1 ? ` <span class="muted small">m merges ${n.merge_keys.length}</span>` : "";
    const h = n.handled_by ? ` <span class="badge">handled ${esc(n.handled_by)}</span>` : "";
    const grp = [...n.merged, ...n.proposed].join(" ");
    return `<li class="entry${hl("neighbours", i)}" data-pane="neighbours" data-i="${i}"><span class="level l${n.level}">${n.level}</span> ` +
      `<b>${esc(n.label)}</b> <span class="muted small">${fmt(n.cosine)} · ${esc(n.readings || n.relation)} · to ${esc(n.via_label)}${grp ? " · " + esc(grp) : ""}</span>${merge}${h}` +
      `<div class="gloss">${esc(n.gloss)}</div></li>`;
  }).join("") || `<li class="muted small">no candidate neighbour</li>`;

  const corpus = S.pinned ? [S.pinned, ...c.corpus.filter((t) => t.key !== S.pinned.key)] : c.corpus;
  S.corpusView = corpus;
  $("corpus").innerHTML = corpus.map((t, i) => {
    const cov = (t.covered || []).length ? `<div class="covered-list">covered by M3: ${t.covered.map((x) => esc(x.label) + " " + esc(x.reading) + (x.handled_by ? " (handled)" : "")).join(", ")}</div>` : "";
    const pin = t === S.pinned ? " pinned" : "";
    return `<li class="entry${pin}${hl("corpus", i)}" data-pane="corpus" data-i="${i}"><span class="level l${t.level || 0}">${t.level != null && t.level >= 0 ? t.level : ""}</span> ` +
      `${link(t)} <span class="muted small">${t.cosine != null ? fmt(t.cosine) + " · " : ""}${esc(t.reading || t.relation || "found")}${t.via_label ? " · from " + esc(t.via_label) : ""}</span>` +
      `<div class="gloss">${esc(t.gloss)}</div>${cov}</li>`;
  }).join("") || `<li class="muted small">no corpus trait read</li>`;

  $("opposed").innerHTML = c.opposed.map((o, i) =>
    `<li class="entry${hl("opposed", i)}" data-pane="opposed" data-i="${i}">` +
    (o.kind === "candidate" ? `<b>${esc(o.label)}</b>` : link(o)) +
    ` <span class="muted small">${fmt(o.cosine)} · to ${esc(o.via_label)}${o.kind === "candidate" && o.antonym_keys && o.antonym_keys.length > 1 ? " · a takes " + o.antonym_keys.length : ""}</span>` +
    `${o.handled_by ? ` <span class="badge">handled ${esc(o.handled_by)}</span>` : ""}</li>`).join("") || `<li class="muted small">no opposed neighbour</li>`;
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
  if (!S.card) { flash("no group open: Space opens the next one", true); return false; }
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
  if (S.card.status !== "resolved") { flash("resolve this group first; a starts its antonym group", true); return; }
  let o = S.pane === "opposed" ? current("opposed") : null;
  if (!o || o.kind !== "candidate") o = S.card.opposed.find((x) => x.kind === "candidate" && !x.handled_by);
  if (!o) { flash("no opposed term to start from: open the antonym's group with / instead", true); return; }
  return act({ action: "start_antonym", of: S.card.id, keys: o.antonym_keys && o.antonym_keys.length ? o.antonym_keys : [o.key] });
}

async function mergeIntoCorpus() {
  if (!needCard()) return;
  const t = current("corpus");
  if (!t) { flash("no corpus trait to merge into: highlight one (Tab to the corpus list) or find one with /", true); return; }
  return resolve(`merge_into:${t.key}`);
}

// ------------------------------------------------------------------ overlays: find, term view, help

function closeOverlay() { $("overlay").hidden = true; $("overlay").innerHTML = ""; S.overlay = null; }

function openFind() {
  const o = $("overlay");
  o.hidden = false;
  o.innerHTML = `<input id="find" placeholder="find a term, a corpus trait or a queue entry (Enter opens, Esc closes)" autocomplete="off"><table id="found"></table>`;
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
    `<tr class="${i === ov.i ? "hl" : ""}"><td>${x.href ? link(x) : esc(x.label)}</td><td class="muted small">${esc(x.kind)}${x.handled_by ? " · handled " + esc(x.handled_by) : ""}</td></tr>`).join("");
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
    o.innerHTML = `<h2>${esc(t.term.label)} <span class="muted small">${esc(t.term.key)} · ${esc(t.term.generator)} · M3 ${esc(t.term.m3_decision)} · groups ${esc([...t.merged, ...t.proposed, ...t.groups].join(" ") || "none")}</span></h2>` +
      `<p class="gloss">${esc(t.term.gloss)}</p><table>` + t.edges.map((e) =>
        `<tr><td>${e.kind === "candidate" ? esc(e.label) : link(e)}</td><td class="muted small">${esc(e.relation)}</td><td class="small">${fmt(e.cosine)}</td>` +
        `<td class="small">${esc(e.readings)}${e.strict ? " · 4-edge" : e.proposed_edge ? " · 3-edge" : ""}</td></tr>`).join("") + `</table><p class="muted small">Esc closes</p>`;
  } catch (e) { flash(e.message, true); }
}

function help() {
  const o = $("overlay");
  o.hidden = false;
  S.overlay = { kind: "help" };
  const keys = [
    ["j / k", "next / previous in the focused list"], ["Tab / Shift-Tab", "focus members, neighbours, corpus, opposed"],
    ["g", "accept the proposed group (Enter too)"], ["x", "drop the highlighted member (never the last)"],
    ["m", "merge in the highlighted neighbour (with its merged group)"], ["n", "nominate the highlighted member"],
    ["Enter", "resolve: promote the nominee (or accept a proposed group; next group once resolved)"],
    ["c", "resolve: merge into the highlighted corpus trait or queue entry"], ["p / r / d", "resolve: park / reject / defer"],
    [";", "a note for the next resolution"], ["a", "start the antonym group from the highlighted (or first) opposed term"],
    ["u", "undo the last decision"], ["/", "find a term, corpus trait or queue entry"], ["t", "the term view (everything one edge away)"],
    ["Space or .", "the next group in the queue"], ["o", "the next queue order"], ["Esc", "close"]];
  o.innerHTML = `<h2>Keys</h2><table>${keys.map(([k, v]) => `<tr><td><kbd>${esc(k)}</kbd></td><td>${esc(v)}</td></tr>`).join("")}</table>`;
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
    case "g": if (needCard()) await act({ action: "accept", group: S.card.id }); break;
    case "Enter": await onEnter(); break;
    case "x": { const m = current("members"); if (needCard() && m) await act({ action: "drop", group: S.card.id, key: m.key }); break; }
    case "n": { const m = current("members"); if (needCard() && m) await act({ action: "nominate", group: S.card.id, key: m.key }); break; }
    case "m": {
      const nb = current("neighbours");
      if (needCard() && nb) await act({ action: "merge_in", group: S.card.id, keys: nb.merge_keys.length ? nb.merge_keys : [nb.key] });
      break;
    }
    case "c": await mergeIntoCorpus(); break;
    case "p": await resolve("park"); break;
    case "r": await resolve("reject"); break;
    case "d": await resolve("defer"); break;
    case ";": { const t = window.prompt("Note for the next resolution", S.note || ""); S.note = t ? t.trim() : null; renderCard(); break; }
    case "a": await startAntonym(); break;
    case "u": await act({ action: "undo" }); break;
    case "/": openFind(); break;
    case "t": await termView(); break;
    case " ": case ".": await nextGroup(); break;
    case "o": S.order = ORDERS[(ORDERS.indexOf(S.order) + 1) % ORDERS.length]; S.qpos = -1; await loadQueue(); flash(`queue order: ${S.order}`); break;
    case "?": help(); break;
    case "Escape": S.pinned = null; renderCard(); break;
    default: return;
  }
  if (handled) ev.preventDefault();
});

// clicks: a queue item opens it; a list row takes the highlight
document.addEventListener("click", async (ev) => {
  if (ev.target.closest("a")) return;
  const q = ev.target.closest("#queue li");
  if (q) { S.qpos = Number(q.dataset.i); await act({ action: "open", source: S.queue[S.qpos].source }); return; }
  const row = ev.target.closest("[data-pane][data-i]");
  if (row) { S.pane = row.dataset.pane; S.idx[S.pane] = Number(row.dataset.i); renderCard(); }
});

(async function init() {
  try {
    await loadMeta();
    await loadQueue();
    flash("Space opens the next group; ? lists the keys.");
  } catch (e) { flash(e.message, true); }
})();
