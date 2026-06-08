/*
 * Princess — mobile client.
 *
 * Targets 390×844 portrait (iPhone 14). Shares all backend endpoints
 * and the WebSocket protocol with the desktop UI at `/`. Tap-only.
 *
 * Copyright 2026 Mike Huot
 * Licensed under the Apache License, Version 2.0.
 */

"use strict";

const state = {
  pid: null,
  code: null,
  isHost: false,
  socket: null,
  view: null,
  phase: null,
  selectedIndices: new Set(),
  setupSelected: new Set(),
  lastRoom: null,
};

const $ = (id) => document.getElementById(id);
const RANK_LABEL = { 11: "J", 12: "Q", 13: "K", 14: "A" };
const rankLabel = (r) => RANK_LABEL[r] || String(r);
const isRedSuit = (s) => s === "H" || s === "D";
const suitGlyph = (s) => ({ S: "♠", H: "♥", D: "♦", C: "♣" })[s] || s;

document.addEventListener("DOMContentLoaded", () => {
  $("m-create-btn").addEventListener("click", createRoom);
  $("m-join-btn").addEventListener("click", joinRoom);
  $("m-add-bot-btn").addEventListener("click", addBot);
  $("m-start-btn").addEventListener("click", startGame);
  $("m-solo-add-1").addEventListener("click", () => { $("m-solo-sheet").close(); mAddBotsThenStart(1); });
  $("m-solo-add-2").addEventListener("click", () => { $("m-solo-sheet").close(); mAddBotsThenStart(2); });
  $("m-solo-add-3").addEventListener("click", () => { $("m-solo-sheet").close(); mAddBotsThenStart(3); });
  $("m-solo-cancel").addEventListener("click", () => $("m-solo-sheet").close());
  $("m-lock-in-btn").addEventListener("click", lockInSetup);
  $("m-play-btn").addEventListener("click", playSelected);
  $("m-pickup-btn").addEventListener("click", pickupPile);
  $("m-rematch-btn").addEventListener("click", rematch);
  $("m-new-game-btn").addEventListener("click", () => (location.href = "/m"));
  $("m-quit-btn").addEventListener("click", openQuitSheet);
  $("m-rename-btn").addEventListener("click", openRenameSheet);
  $("m-rules-btn").addEventListener("click", openRulesSheet);
  $("m-setup-rules-btn").addEventListener("click", openRulesSheet);
  $("m-quit-sheet-cancel").addEventListener("click", () => $("m-quit-sheet").close());
  $("m-rules-sheet-cancel").addEventListener("click", () => $("m-rules-sheet").close());
  $("m-rename-cancel").addEventListener("click", () => $("m-rename-sheet").close());
  $("m-rename-submit").addEventListener("click", submitRename);
  $("m-game-room-code").addEventListener("click", copyRoomCode);

  const m = location.pathname.match(/^\/m\/([A-Z0-9]{4})$/i);
  if (m) $("m-code").value = m[1].toUpperCase();
});

// --- Networking helpers ----------------------------------------------------

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function showError(msg) {
  const el = $("m-lobby-error");
  el.textContent = msg;
  el.hidden = false;
  setTimeout(() => (el.hidden = true), 5000);
}

// --- Lobby flow ------------------------------------------------------------

async function createRoom() {
  const name = $("m-name").value.trim();
  if (!name) return showError("Enter your name first.");
  try {
    const r = await postJSON("/api/rooms", { name });
    state.code = r.code; state.pid = r.pid; state.isHost = true;
    enterRoom();
  } catch (e) { showError(e.message); }
}

async function joinRoom() {
  const name = $("m-name").value.trim();
  const code = $("m-code").value.trim().toUpperCase();
  if (!name) return showError("Enter your name first.");
  if (!code) return showError("Enter a 4-character room code.");
  try {
    const r = await postJSON(`/api/rooms/${code}/join`, { name });
    state.code = code; state.pid = r.pid; state.isHost = false;
    enterRoom();
  } catch (e) { showError(e.message); }
}

function enterRoom() {
  $("m-landing").hidden = true;
  $("m-room").hidden = false;
  $("m-room-code").textContent = state.code;
  $("m-host-controls").hidden = !state.isHost;
  history.replaceState({}, "", `/m/${state.code}`);
  openSocket();
}

function openSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${proto}://${location.host}/ws/${state.code}/${state.pid}`);
  state.socket.addEventListener("message", (e) => handleMessage(JSON.parse(e.data)));
  state.socket.addEventListener("close", () => {
    $("m-waiting").textContent = "Disconnected. Refresh to reconnect.";
  });
}

function handleMessage(msg) {
  if (msg.type === "lobby") renderLobby(msg.room);
  else if (msg.type === "state") renderGame(msg.view);
  else if (msg.type === "error") showError(msg.message);
}

async function addBot() {
  try { await postJSON(`/api/rooms/${state.code}/bot`, { host_pid: state.pid }); }
  catch (e) { showError(e.message); }
}

async function startGame() {
  if (state.lastRoom?.seats?.length === 1) {
    $("m-solo-sheet").showModal();
    return;
  }
  try { await postJSON(`/api/rooms/${state.code}/start`, { host_pid: state.pid }); }
  catch (e) { showError(e.message); }
}

async function mAddBotsThenStart(n) {
  for (let i = 0; i < n; i++) {
    try { await postJSON(`/api/rooms/${state.code}/bot`, { host_pid: state.pid }); }
    catch (e) { showError(e.message); return; }
  }
  try { await postJSON(`/api/rooms/${state.code}/start`, { host_pid: state.pid }); }
  catch (e) { showError(e.message); }
}

async function rematch() {
  try { await postJSON(`/api/rooms/${state.code}/rematch`, { host_pid: state.pid }); }
  catch (e) { showError(e.message); }
}

// --- Lobby render ----------------------------------------------------------

function renderLobby(room) {
  state.lastRoom = room;
  $("m-game").hidden = true;
  $("m-setup").hidden = true;
  $("m-game-over").hidden = true;
  $("m-room").hidden = false;
  const cfg = room.config || {};
  $("m-reverse-rank-readout").textContent = `Reverse rank: ${rankLabel(cfg.reverse_rank ?? 5)}`;
  const list = $("m-seat-list");
  list.innerHTML = "";
  room.seats.forEach((seat) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.textContent = seat.name;
    if (seat.is_bot) {
      const tag = document.createElement("span");
      tag.className = "m-badge bot";
      tag.textContent = "bot";
      name.appendChild(document.createTextNode(" "));
      name.appendChild(tag);
    }
    li.appendChild(name);
    const right = document.createElement("span");
    if (seat.pid === room.host_pid) right.appendChild(badge("host", "host"));
    if (!seat.is_bot && !seat.connected) right.appendChild(badge("offline", "offline"));
    li.appendChild(right);
    list.appendChild(li);
  });
  const pending = room.seats.length < 2;
  $("m-waiting").textContent = pending
    ? "Waiting for more players (or add a bot)…"
    : state.isHost
      ? "Ready when you are."
      : "Waiting for host to start…";
}

function badge(cls, text) {
  const s = document.createElement("span");
  s.className = "m-badge " + cls;
  s.textContent = text;
  return s;
}

// --- Top-level game render -------------------------------------------------

function renderGame(view) {
  // Reset setup selection on transition INTO setup (same trick as desktop).
  const wasPhase = state.phase;
  state.phase = view.phase;
  if (view.phase === "setup" && wasPhase !== "setup" && !view.you?.ready) {
    state.setupSelected.clear();
  }
  state.view = view;
  $("m-lobby").hidden = true;

  if (view.game_over) {
    $("m-game").hidden = true;
    $("m-setup").hidden = true;
    $("m-game-over").hidden = false;
    renderResults(view);
    return;
  }

  $("m-game-over").hidden = true;

  if (view.phase === "setup") {
    $("m-game").hidden = true;
    $("m-setup").hidden = false;
    renderSetup(view);
    return;
  }

  $("m-setup").hidden = true;
  $("m-game").hidden = false;
  renderOpponents(view);
  renderPile(view);
  renderTable(view);
  renderHand(view);
  renderStatus(view);
  refreshActionButtons(view);
  $("m-game-room-code").textContent = state.code;
  $("m-setup-room-code").textContent = state.code;
}

// --- Setup -----------------------------------------------------------------

function renderSetup(view) {
  $("m-setup-room-code").textContent = state.code;
  const grid = $("m-choose-grid");
  grid.innerHTML = "";
  const me = view.you;
  if (me.ready) {
    state.setupSelected.clear();
    grid.innerHTML = `<p class="m-muted">You're locked in. Waiting for others…</p>`;
  } else {
    me.choose.forEach((c, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "m-choose-card " + (isRedSuit(c.suit) ? "red" : "black");
      btn.textContent = `${rankLabel(c.rank)}${suitGlyph(c.suit)}`;
      const isSelected = state.setupSelected.has(idx);
      if (isSelected) btn.classList.add("selected");
      btn.setAttribute("aria-pressed", isSelected ? "true" : "false");
      if (isSpecialRank(c.rank, view)) btn.classList.add("special");
      btn.addEventListener("click", () => toggleSetupSelect(idx));
      grid.appendChild(btn);
    });
  }
  $("m-lock-in-btn").disabled = me.ready || state.setupSelected.size !== 3;
  const pending = view.players.filter((p) => !p.ready).map((p) => p.name);
  $("m-setup-status").textContent = pending.length
    ? `Waiting on: ${pending.join(", ")}`
    : "Everyone ready!";
}

function toggleSetupSelect(idx) {
  if (state.setupSelected.has(idx)) state.setupSelected.delete(idx);
  else if (state.setupSelected.size < 3) state.setupSelected.add(idx);
  else {
    const first = state.setupSelected.values().next().value;
    state.setupSelected.delete(first);
    state.setupSelected.add(idx);
  }
  renderSetup(state.view);
}

function lockInSetup() {
  if (state.setupSelected.size !== 3) return;
  sendAction({ type: "set_face_up", indices: [...state.setupSelected] });
}

// --- Opponents -------------------------------------------------------------

function renderOpponents(view) {
  const strip = $("m-opponents");
  strip.innerHTML = "";
  view.players.filter((p) => p.pid !== state.pid).forEach((p) => {
    const box = document.createElement("div");
    box.className = "m-opponent";
    if (p.pid === view.current_pid) box.classList.add("turn");
    if (p.finished) box.classList.add("finished");
    const name = document.createElement("div");
    name.className = "m-opp-name";
    name.textContent = p.name + (p.is_bot ? " (bot)" : "") + (p.finished ? " · out" : "");
    box.appendChild(name);
    const meta = document.createElement("div");
    meta.className = "m-opp-meta";
    meta.textContent = `hand ${p.hand_count} · down ${p.face_down_count}`;
    box.appendChild(meta);
    strip.appendChild(box);
  });
}

// --- Pile ------------------------------------------------------------------

function renderPile(view) {
  const pile = $("m-pile-card");
  pile.classList.remove("empty", "red", "black");
  if (view.pile_top) {
    pile.classList.add(isRedSuit(view.pile_top.suit) ? "red" : "black");
    pile.textContent = `${rankLabel(view.pile_top.rank)}${suitGlyph(view.pile_top.suit)}`;
  } else {
    pile.classList.add("empty");
    pile.textContent = "empty";
  }
  $("m-deck-count").textContent = String(view.deck_count);
  const rule = $("m-rule-indicator");
  const reverse = view.config?.reverse_rank ?? 5;
  const reverseLabel = rankLabel(reverse);
  if (view.under_reverse || view.under_seven) {
    rule.textContent = `UNDER ${reverseLabel}`;
    rule.classList.add("alert");
  } else {
    rule.textContent = view.pile_top ? "match or beat" : "anything";
    rule.classList.remove("alert");
  }
}

// --- Your table (face-up + face-down) --------------------------------------

function renderTable(view) {
  const row = $("m-your-table");
  row.innerHTML = "";
  const meSeat = view.players.find((p) => p.pid === state.pid);
  if (!meSeat) return;
  const active = view.you.active_source;
  meSeat.face_up.forEach((c, idx) => {
    const el = makeMiniCard(c, view);
    if (active === "face_up" && view.you.your_turn) {
      el.classList.add("selectable");
      if (isLegalRank(c.rank, view)) el.classList.add("legal-hint");
      if (state.selectedIndices.has(idx) && active === "face_up") el.classList.add("selected");
      el.addEventListener("click", () => toggleSelect(idx, c.rank));
    }
    row.appendChild(el);
  });
  for (let i = 0; i < meSeat.face_down_count; i++) {
    const el = document.createElement("div");
    el.className = "m-mini-back";
    el.textContent = "♛";
    if (active === "face_down" && view.you.your_turn) {
      el.classList.add("selectable");
      el.addEventListener("click", () =>
        sendAction({ type: "play", source: "face_down", indices: [i] })
      );
    }
    row.appendChild(el);
  }
}

function makeMiniCard(c, view) {
  const el = document.createElement("div");
  el.className = "m-mini-card " + (isRedSuit(c.suit) ? "red" : "black");
  el.textContent = `${rankLabel(c.rank)}${suitGlyph(c.suit)}`;
  if (isSpecialRank(c.rank, view)) el.classList.add("special");
  return el;
}

// --- Fan-out hand ----------------------------------------------------------

function renderHand(view) {
  const fan = $("m-hand-fan");
  fan.innerHTML = "";
  const me = view.you;
  const cards = me.hand || [];
  if (!cards.length || me.active_source !== "hand") {
    fan.style.height = "0px";
    return;
  }
  fan.style.height = "140px";

  const n = cards.length;
  const maxAngle = Math.min(25, n <= 3 ? 8 * (n - 1) : 25);
  const arcRadius = 230;
  cards.forEach((c, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "m-hand-card " + (isRedSuit(c.suit) ? "red" : "black");
    btn.setAttribute("role", "listitem");
    btn.dataset.idx = String(idx);
    btn.innerHTML = `<span>${rankLabel(c.rank)}</span><span>${suitGlyph(c.suit)}</span>`;
    if (isSpecialRank(c.rank, view)) btn.classList.add("special");
    if (isLegalRank(c.rank, view) && me.your_turn) btn.classList.add("legal-hint");
    if (state.selectedIndices.has(idx) && me.active_source === "hand") btn.classList.add("selected");

    // Angle ranges symmetrically from -maxAngle to +maxAngle.
    let angle = 0;
    if (n > 1) {
      const t = idx / (n - 1);  // 0..1
      angle = -maxAngle + 2 * maxAngle * t;
    }
    // Lift cards: edges dip slightly so the arc is convex upward.
    const lift = arcRadius - Math.sqrt(arcRadius * arcRadius - Math.pow(arcRadius * Math.sin((angle * Math.PI) / 180), 2));
    const selectedBoost = state.selectedIndices.has(idx) ? -22 : 0;
    btn.style.transform = `translateY(${lift + selectedBoost}px) rotate(${angle}deg)`;
    btn.style.zIndex = String(idx);
    btn.addEventListener("click", () => toggleSelect(idx, c.rank));
    fan.appendChild(btn);
  });
}

function toggleSelect(idx, rank) {
  const view = state.view;
  if (!view) return;
  const me = view.you;
  if (!me.your_turn) return;
  // Reset selection if switching to a different rank.
  const cards = currentSourceCards(view);
  const existing = [...state.selectedIndices].map((i) => cards[i]?.rank);
  if (existing.length && existing[0] !== rank) state.selectedIndices.clear();
  if (state.selectedIndices.has(idx)) state.selectedIndices.delete(idx);
  else state.selectedIndices.add(idx);
  renderGame(view);
}

function currentSourceCards(view) {
  const src = view.you.active_source;
  if (src === "hand") return view.you.hand;
  const meSeat = view.players.find((p) => p.pid === state.pid);
  if (src === "face_up") return meSeat?.face_up || [];
  return [];
}

function playSelected() {
  const view = state.view;
  if (!view?.you?.your_turn) return;
  const source = view.you.active_source;
  if (!source || source === "face_down") return;
  const indices = [...state.selectedIndices].sort((a, b) => a - b);
  if (!indices.length) return;
  sendAction({ type: "play", source, indices });
  state.selectedIndices.clear();
}

function pickupPile() {
  sendAction({ type: "pickup" });
}

function refreshActionButtons(view) {
  const yourTurn = view?.you?.your_turn;
  $("m-play-btn").disabled = !(yourTurn && state.selectedIndices.size > 0);
  $("m-pickup-btn").disabled = !(yourTurn && view.pile_size > 0);
}

// --- Status ticker ---------------------------------------------------------

function renderStatus(view) {
  const slot = $("m-status-line");
  const entries = Array.isArray(view.last_actions) ? view.last_actions : [];
  if (!entries.length) {
    slot.textContent = view.last_action || "";
    return;
  }
  const entry = entries[entries.length - 1];
  let text = entry.text || "";
  if (entry.burned) text += " 🔥";
  if (entry.picked_up) text += " ↑";
  const me = view.you;
  if (!view.game_over) {
    text += me.your_turn ? " — Your turn." : ` — ${currentName(view)}'s turn.`;
  }
  slot.textContent = text;
}

function currentName(view) {
  const p = view.players.find((pl) => pl.pid === view.current_pid);
  return p ? p.name : "someone";
}

// --- End-of-round panel ----------------------------------------------------

function renderResults(view) {
  const ol = $("m-results");
  ol.innerHTML = "";
  const winnerPid = view.finished_order[0];
  const winner = winnerPid ? view.players.find((p) => p.pid === winnerPid) : null;
  const youWon = winnerPid === state.pid;
  $("m-winner-name").textContent = winner ? `${winner.name} won the round!` : "Round over!";
  $("m-winner-subtitle").textContent = youWon
    ? "👑 That's you. Take a bow, Princess."
    : winner
      ? "Better luck next round."
      : "";

  const finalSlot = $("m-winner-final-action");
  const entries = view.last_actions || [];
  const finalEntry = entries.length ? entries[entries.length - 1] : null;
  if (finalEntry?.text) {
    let text = finalEntry.text;
    if (finalEntry.burned) text += " 🔥";
    if (finalEntry.picked_up) text += " ↑";
    if (finalEntry.finished_pid) {
      const p = view.players.find((pl) => pl.pid === finalEntry.finished_pid);
      if (p) text += ` 👑 ${p.name}`;
    }
    finalSlot.textContent = text;
  } else {
    finalSlot.textContent = "";
  }

  view.finished_order.forEach((pid, i) => {
    const p = view.players.find((pl) => pl.pid === pid);
    if (!p) return;
    const li = document.createElement("li");
    const isFirst = i === 0;
    const isLast = i === view.finished_order.length - 1;
    const left = document.createElement("span");
    left.textContent = `${i + 1}. ${p.name}`;
    const right = document.createElement("span");
    right.textContent = isFirst ? "👑 Princess" : isLast ? "last place" : "";
    li.appendChild(left);
    li.appendChild(right);
    if (isFirst) li.classList.add("princess");
    if (isLast) li.classList.add("last-place");
    ol.appendChild(li);
  });

  $("m-rematch-btn").hidden = !state.isHost;
  $("m-rematch-note").hidden = state.isHost;
}

// --- Legality / specials ---------------------------------------------------

function isLegalRank(rank, view) {
  const reverse = view.config?.reverse_rank ?? 5;
  if (rank === 2 || rank === 10 || rank === reverse) return true;
  const top = view.pile_top;
  if (!top) return true;
  if (view.under_reverse || view.under_seven) return rank < reverse;
  return rank >= top.rank;
}

function isSpecialRank(rank, view) {
  const reverse = view?.config?.reverse_rank ?? 5;
  return rank === 2 || rank === 10 || rank === reverse;
}

// --- Sheets (quit, rules, rename) -----------------------------------------

function openQuitSheet() {
  const sheet = $("m-quit-sheet");
  const actions = $("m-quit-sheet-actions");
  actions.innerHTML = "";
  const inGame = state.view && !state.view.game_over;
  const isHost = state.isHost;
  const add = (label, cls, fn) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    if (cls) b.classList.add(cls);
    b.addEventListener("click", async () => { sheet.close(); try { await fn(); } catch (e) { showError(e.message); } });
    actions.appendChild(b);
  };
  if (inGame && !isHost) {
    add("Take over with a bot", "takeover", takeoverWithBot);
    add("Leave room", "danger", leaveAndGoHome);
  } else if (inGame && isHost) {
    add("End the round now", "takeover", endRoundNow);
    add("Abort the game", "danger", abortGame);
  } else if (!isHost) {
    add("Leave room", "danger", leaveAndGoHome);
  } else {
    add("Abort the game", "danger", abortGame);
  }
  sheet.showModal();
}

async function takeoverWithBot() {
  await postJSON(`/api/rooms/${state.code}/leave`, { pid: state.pid, convert_to_bot: true });
  if (state.socket) state.socket.close();
  location.href = "/m";
}

async function leaveAndGoHome() {
  await postJSON(`/api/rooms/${state.code}/leave`, { pid: state.pid, convert_to_bot: false });
  if (state.socket) state.socket.close();
  location.href = "/m";
}

async function endRoundNow() {
  await postJSON(`/api/rooms/${state.code}/end_round`, { host_pid: state.pid });
}

async function abortGame() {
  await postJSON(`/api/rooms/${state.code}/abort`, { host_pid: state.pid });
}

function openRulesSheet() {
  const list = $("m-rules-sheet-list");
  list.innerHTML = "";
  const reverse = state.view?.config?.reverse_rank ?? 5;
  const reverseLabel = rankLabel(reverse);
  const items = [
    `<strong>2</strong> — Wild reset. Always legal; next player can play anything.`,
    `<strong>10</strong> — Burn. Always legal; clears the pile; you play again.`,
    `<strong>${reverseLabel}</strong> — Reverse (wild). Always legal; next play must be UNDER ${reverseLabel}.`,
    `Four of a kind in a row on the pile burns it.`,
    `Can't play? Pick up the pile.`,
  ];
  items.forEach((html) => {
    const li = document.createElement("li");
    li.innerHTML = html;
    list.appendChild(li);
  });
  $("m-rules-sheet").showModal();
}

function openRenameSheet() {
  const me = state.view?.players?.find((p) => p.pid === state.pid);
  $("m-rename-input").value = me?.name || "";
  $("m-rename-sheet").showModal();
}

async function submitRename() {
  const value = $("m-rename-input").value.trim();
  if (!value) return;
  try {
    await postJSON(`/api/rooms/${state.code}/rename`, { pid: state.pid, new_name: value });
    $("m-rename-sheet").close();
  } catch (e) { showError(e.message); }
}

async function copyRoomCode() {
  if (!state.code) return;
  try { await navigator.clipboard.writeText(state.code); }
  catch { /* clipboard not available — silent */ }
}

function sendAction(msg) {
  if (state.socket?.readyState === WebSocket.OPEN) {
    state.socket.send(JSON.stringify(msg));
  }
}
