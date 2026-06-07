/*
 * Princess Card Game — client.
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
  selectedSource: null,
  selectedIndices: new Set(),
  view: null,
  sortHand: false,
  setupSelected: new Set(),
  seatWasHuman: new Set(),
};

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  $("create-btn").addEventListener("click", createRoom);
  $("join-btn").addEventListener("click", joinRoom);
  $("add-bot-btn").addEventListener("click", addBot);
  $("start-btn").addEventListener("click", startGame);
  $("play-btn").addEventListener("click", playSelected);
  $("pickup-btn").addEventListener("click", pickup);
  $("sort-hand-btn").addEventListener("click", toggleSortHand);
  $("lock-in-btn").addEventListener("click", lockInSetup);
  $("cfg-reverse-rank").addEventListener("change", saveConfig);
  $("rematch-btn").addEventListener("click", playRematch);
  $("new-game-btn").addEventListener("click", () => location.reload());
  $("quit-btn").addEventListener("click", quitGame);
  $("rename-btn").addEventListener("click", promptRenameForGame);
  $("quit-dialog-cancel").addEventListener("click", () => $("quit-dialog").close());
  $("quit-dialog").addEventListener("close", () => {});

  const urlCode = (location.pathname.match(/^\/room\/([A-Z0-9]{4})$/i) || [])[1];
  if (urlCode) {
    $("room-code").value = urlCode.toUpperCase();
  }
});

function showError(elId, msg) {
  const el = $(elId);
  el.textContent = msg;
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 5000);
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || res.statusText);
  }
  return data;
}

async function createRoom() {
  const name = $("player-name").value.trim();
  if (!name) return showError("lobby-error", "Enter your name first.");
  try {
    const { code, pid } = await postJSON("/api/rooms", { name });
    state.code = code;
    state.pid = pid;
    state.isHost = true;
    enterRoom();
  } catch (e) { showError("lobby-error", e.message); }
}

async function joinRoom() {
  const name = $("player-name").value.trim();
  const code = $("room-code").value.trim().toUpperCase();
  if (!name) return showError("lobby-error", "Enter your name first.");
  if (!code) return showError("lobby-error", "Enter a 4-character room code.");
  try {
    const { pid } = await postJSON(`/api/rooms/${code}/join`, { name });
    state.code = code;
    state.pid = pid;
    state.isHost = false;
    enterRoom();
  } catch (e) { showError("lobby-error", e.message); }
}

function enterRoom() {
  $("lobby").hidden = true;
  $("room-view").hidden = false;
  $("room-code-display").textContent = state.code;
  $("host-controls").hidden = !state.isHost;
  history.replaceState({}, "", `/room/${state.code}`);
  openSocket();
}

function openSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${proto}://${location.host}/ws/${state.code}/${state.pid}`);
  state.socket.addEventListener("message", (e) => handleMessage(JSON.parse(e.data)));
  state.socket.addEventListener("close", () => {
    $("waiting-message").textContent = "Disconnected. Refresh to reconnect.";
  });
}

function handleMessage(msg) {
  if (msg.type === "lobby") {
    renderLobby(msg.room);
  } else if (msg.type === "state") {
    renderGame(msg.view);
  } else if (msg.type === "error") {
    showError("action-error", msg.message);
  }
}

function trackSeatHumanity(seats) {
  // Anyone seen as a human (is_bot:false) in this round is remembered. Once
  // they flip to a bot, the rendered tag becomes "(now a bot)" until the round
  // ends (and we reset the set on game_over).
  seats.forEach((seat) => {
    if (!seat.is_bot) state.seatWasHuman.add(seat.pid);
  });
}

function botTagFor(seat) {
  if (!seat.is_bot) return null;
  return state.seatWasHuman.has(seat.pid) ? "now a bot" : "bot";
}

function appendNameWithTag(parent, name, seat) {
  parent.appendChild(document.createTextNode(name));
  const tag = botTagFor(seat);
  if (tag) {
    const span = document.createElement("span");
    span.className = "bot-tag" + (tag === "now a bot" ? " now" : "");
    span.textContent = ` (${tag})`;
    parent.appendChild(span);
  }
}

function renderLobby(room) {
  $("game-view").hidden = true;
  $("room-view").hidden = false;
  renderConfigPanel(room);
  trackSeatHumanity(room.seats);
  const list = $("seat-list");
  list.innerHTML = "";
  room.seats.forEach((seat) => {
    const li = document.createElement("li");
    const left = document.createElement("span");
    left.className = "seat-name-cell";
    appendNameWithTag(left, seat.name, seat);
    li.appendChild(left);
    const right = document.createElement("span");
    right.className = "seat-controls";
    if (seat.pid === room.host_pid) {
      right.appendChild(badge("host", "host"));
    }
    if (!seat.is_bot && !seat.connected) {
      right.appendChild(badge("offline", "offline"));
    }
    if (seat.pid === state.pid) {
      const renameBtn = document.createElement("button");
      renameBtn.type = "button";
      renameBtn.className = "seat-action";
      renameBtn.textContent = "Rename";
      renameBtn.addEventListener("click", () => beginRenameInline(li, left, seat.name));
      right.appendChild(renameBtn);
    }
    if (seat.is_bot && state.isHost) {
      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "seat-action danger";
      removeBtn.textContent = "Remove";
      removeBtn.addEventListener("click", () => removeBot(seat.pid));
      right.appendChild(removeBtn);
    }
    li.appendChild(right);
    list.appendChild(li);
  });
  const tooFew = room.seats.length < 2;
  $("waiting-message").textContent = tooFew
    ? "Waiting for more players (or add a bot)…"
    : state.isHost
      ? "Ready when you are."
      : "Waiting for host to start…";
}

function badge(cls, text) {
  const span = document.createElement("span");
  span.className = `badge ${cls}`;
  span.textContent = text;
  return span;
}

function renderConfigPanel(room) {
  const cfg = room.config || {};
  const rankSelect = $("cfg-reverse-rank");
  if (rankSelect) {
    rankSelect.value = String(cfg.reverse_rank ?? 5);
    rankSelect.disabled = !state.isHost;
  }
  $("config-readonly-note").hidden = state.isHost;
}

async function saveConfig() {
  if (!state.isHost) return;
  const config = {
    reverse_rank: parseInt($("cfg-reverse-rank").value, 10),
  };
  try {
    await postJSON(`/api/rooms/${state.code}/config`, {
      host_pid: state.pid,
      config,
    });
  } catch (e) { showError("lobby-error", e.message); }
}

async function removeBot(botPid) {
  try {
    await postJSON(`/api/rooms/${state.code}/remove_bot`, {
      host_pid: state.pid,
      bot_pid: botPid,
    });
  } catch (e) { showError("lobby-error", e.message); }
}

async function renameSelf(newName) {
  const trimmed = (newName || "").trim();
  if (!trimmed) return;
  if (trimmed.length > 20) {
    showError("lobby-error", "Name must be 20 characters or fewer.");
    return;
  }
  try {
    await postJSON(`/api/rooms/${state.code}/rename`, {
      pid: state.pid,
      new_name: trimmed,
    });
  } catch (e) { showError("lobby-error", e.message); }
}

function beginRenameInline(li, nameCell, currentName) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = currentName;
  input.maxLength = 20;
  input.className = "rename-input";
  input.setAttribute("aria-label", "New name");
  let settled = false;
  const cancel = () => {
    if (settled) return;
    settled = true;
    input.replaceWith(nameCell);
  };
  const submit = () => {
    if (settled) return;
    settled = true;
    const value = input.value.trim();
    input.replaceWith(nameCell);
    if (value && value !== currentName) renameSelf(value);
  };
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); submit(); }
    if (e.key === "Escape") { e.preventDefault(); cancel(); }
  });
  input.addEventListener("blur", submit);
  nameCell.replaceWith(input);
  input.focus();
  input.select();
}

function promptRenameForGame() {
  const current = (state.view?.players || []).find((p) => p.pid === state.pid)?.name || "";
  const next = window.prompt("New name?", current);
  if (next == null) return;
  renameSelf(next);
}

async function addBot() {
  try {
    await postJSON(`/api/rooms/${state.code}/bot`, { host_pid: state.pid });
  } catch (e) { showError("lobby-error", e.message); }
}

async function startGame() {
  try {
    await postJSON(`/api/rooms/${state.code}/start`, { host_pid: state.pid });
  } catch (e) { showError("lobby-error", e.message); }
}

function renderGame(view) {
  state.view = view;
  $("room-view").hidden = true;
  $("game-view").hidden = false;

  if (view.game_over) {
    state.seatWasHuman = new Set();  // reset for next round
    // Hide the play surface, show only the winner panel.
    $("opponents").hidden = true;
    document.querySelector(".pile-area").hidden = true;
    document.querySelector(".legend").hidden = true;
    $("status-stack").hidden = true;
    $("setup-area").hidden = true;
    $("you-area").hidden = true;
    $("game-over").hidden = false;
    renderResults(view);
    return;
  }

  $("opponents").hidden = false;
  document.querySelector(".pile-area").hidden = false;
  document.querySelector(".legend").hidden = false;
  $("status-stack").hidden = false;
  $("game-over").hidden = true;

  renderOpponents(view);
  renderPile(view);
  renderLegend(view);
  renderStatus(view);

  if (view.phase === "setup") {
    $("setup-area").hidden = false;
    $("you-area").hidden = true;
    renderSetup(view);
  } else {
    $("setup-area").hidden = true;
    $("you-area").hidden = false;
    renderYou(view);
  }
}

function renderLegend(view) {
  const list = $("legend-list");
  if (!list) return;
  const cfg = view.config || {};
  const reverse = reverseRankOf(view);
  const reverseLabel = rankLabel(reverse);
  const items = [
    { rank: "2", title: "Wild reset", body: "Always legal; next player can play anything." },
    {
      rank: reverseLabel,
      title: "Reverse (wild)",
      body: `Always legal; the next card must be UNDER ${reverseLabel}.`,
    },
    { rank: "10", title: "Burn", body: "Always legal; clears the pile; you play again." },
    { rank: "4×", title: "Four of a kind", body: "Four same-rank cards in a row on the pile burns it." },
    { rank: "", title: "Can't play?", body: "Pick up the pile — the turn passes." },
  ];
  list.innerHTML = "";
  for (const it of items) {
    const li = document.createElement("li");
    if (it.rank) {
      const tag = document.createElement("span");
      tag.className = "legend-rank";
      tag.textContent = it.rank;
      li.appendChild(tag);
    }
    const strong = document.createElement("strong");
    strong.textContent = it.title;
    li.appendChild(strong);
    li.appendChild(document.createTextNode(" — " + it.body));
    list.appendChild(li);
  }
}

function renderSetup(view) {
  const me = view.you;
  const down = $("setup-down-row");
  down.innerHTML = "";
  const meSeat = view.players.find((p) => p.pid === state.pid);
  for (let i = 0; i < meSeat.face_down_count; i++) {
    const el = document.createElement("div");
    el.className = "card back";
    el.textContent = "♛";
    down.appendChild(el);
  }
  const row = $("choose-row");
  row.innerHTML = "";
  if (me.ready) {
    state.setupSelected.clear();
    row.appendChild(textLineEl(`You're locked in. Waiting for others…`));
  } else {
    me.choose.forEach((c, idx) => {
      const el = makeFaceCard(c);
      el.setAttribute("role", "listitem");
      if (state.setupSelected.has(idx)) el.classList.add("selected");
      el.addEventListener("click", () => toggleSetupSelect(idx));
      row.appendChild(el);
    });
  }
  $("lock-in-btn").disabled = me.ready || state.setupSelected.size !== 3;
  const pending = view.players.filter((p) => !p.ready).map((p) => p.name);
  $("setup-status").textContent = pending.length
    ? `Waiting on: ${pending.join(", ")}`
    : "Everyone ready!";
}

function textLineEl(text) {
  const p = document.createElement("p");
  p.className = "muted";
  p.textContent = text;
  return p;
}

function toggleSetupSelect(idx) {
  if (state.setupSelected.has(idx)) {
    state.setupSelected.delete(idx);
  } else if (state.setupSelected.size < 3) {
    state.setupSelected.add(idx);
  } else {
    // Replace oldest selection.
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

function toggleSortHand() {
  state.sortHand = !state.sortHand;
  $("sort-hand-btn").setAttribute("aria-pressed", String(state.sortHand));
  if (state.view) renderYou(state.view);
}

function renderOpponents(view) {
  // Mirror lobby-side bookkeeping for cross-render bot-tag continuity.
  // Opponent entries don't include `is_bot` directly, so reach into the
  // matching room seat carried in the lobby broadcast (cached on state.view).
  const opponentSeats = view.players.map((p) => ({
    pid: p.pid,
    is_bot: !!p.is_bot,
  }));
  trackSeatHumanity(opponentSeats);
  const container = $("opponents");
  container.innerHTML = "";
  view.players
    .filter((p) => p.pid !== state.pid)
    .forEach((p) => {
      const box = document.createElement("div");
      box.className = "opponent";
      if (p.pid === view.current_pid) box.classList.add("turn");
      if (p.finished) box.classList.add("finished");
      const h = document.createElement("h4");
      appendNameWithTag(h, p.name + (p.finished ? " (out)" : ""), { pid: p.pid, is_bot: p.is_bot });
      box.appendChild(h);
      box.appendChild(textLine(`Hand: ${p.hand_count}`));
      box.appendChild(textLine(`Face-down: ${p.face_down_count}`));

      const row = document.createElement("div");
      row.className = "mini-row";
      p.face_up.forEach((c) => row.appendChild(miniCard(c)));
      for (let i = 0; i < p.face_down_count; i++) row.appendChild(miniBack());
      box.appendChild(row);
      container.appendChild(box);
    });
}

function textLine(text) {
  const p = document.createElement("p");
  p.className = "opp-line";
  p.textContent = text;
  return p;
}

function miniCard(c) {
  const el = document.createElement("div");
  el.className = "mini-card";
  el.textContent = c.label.replace(/[SHDC]$/, "");
  el.style.color = isRedSuit(c.suit) ? "#a3002b" : "#11111b";
  const special = specialCardInfo(c.rank, state.view);
  el.title = special ? `${c.label}\n${special}` : c.label;
  if (special) el.classList.add("special");
  return el;
}

function miniBack() {
  const el = document.createElement("div");
  el.className = "mini-back";
  el.textContent = "♛";
  return el;
}

function renderPile(view) {
  const pile = $("pile-card");
  pile.classList.remove("empty", "red", "black");
  if (view.pile_top) {
    pile.textContent = "";
    pile.appendChild(makeCardFace(view.pile_top));
    pile.classList.add(isRedSuit(view.pile_top.suit) ? "red" : "black");
    const special = specialCardInfo(view.pile_top.rank, view);
    pile.title = special
      ? `${view.pile_top.label}\n${special}`
      : view.pile_top.label;
  } else {
    pile.textContent = "empty";
    pile.classList.add("empty");
    pile.title = "Pile is empty — play anything";
  }
  $("pile-size").textContent = `${view.pile_size} card${view.pile_size === 1 ? "" : "s"}`;
  $("deck-count").textContent = view.deck_count;
  const rule = $("rule-indicator");
  const reverse = reverseRankOf(view);
  const reverseLabel = rankLabel(reverse);
  if (view.under_reverse || view.under_seven) {
    rule.textContent = `play UNDER ${reverseLabel} (or another ${reverseLabel})`;
    rule.classList.add("alert");
  } else {
    rule.textContent = view.pile_top ? "match or beat" : "anything";
    rule.classList.remove("alert");
  }
}

function makeCardFace(c) {
  const wrap = document.createElement("div");
  wrap.style.display = "flex";
  wrap.style.flexDirection = "column";
  wrap.style.alignItems = "center";
  const r = document.createElement("div");
  r.textContent = c.label.replace(/[SHDC]$/, "");
  const s = document.createElement("div");
  s.style.fontSize = "0.9rem";
  s.textContent = suitGlyph(c.suit);
  wrap.appendChild(r);
  wrap.appendChild(s);
  return wrap;
}

function suitGlyph(suit) {
  return { S: "♠", H: "♥", D: "♦", C: "♣" }[suit] || suit;
}

function isRedSuit(suit) {
  return suit === "H" || suit === "D";
}

function renderYou(view) {
  const me = view.you;
  const activeSource = me.active_source;
  state.selectedSource = activeSource;
  // Clear selection on state change.
  state.selectedIndices.clear();

  $("source-label").textContent = activeSource
    ? `Playing from: ${activeSource.replace("_", "-")}` + (me.your_turn ? " — your turn" : "")
    : "You're out of cards.";

  renderHand(me, view);
  renderYourTable(view);

  const handEmpty = me.hand.length === 0;
  $("hand").hidden = handEmpty;
  $("hand-toolbar").hidden = handEmpty;
  $("hand-heading").hidden = handEmpty;

  refreshActionButtons(view);
}

function renderHand(me, view) {
  const row = $("hand");
  row.innerHTML = "";
  const pairs = me.hand.map((c, idx) => ({ card: c, idx }));
  if (state.sortHand) {
    pairs.sort((a, b) => a.card.rank - b.card.rank || a.card.suit.localeCompare(b.card.suit));
  }
  pairs.forEach(({ card, idx }) => {
    row.appendChild(buildSelectableCard(card, idx, view, "hand"));
  });
}

function renderYourTable(view) {
  const row = $("your-table");
  row.innerHTML = "";
  const meSeat = view.players.find((p) => p.pid === state.pid);
  if (!meSeat) return;
  const active = view.you.active_source;
  const faceUpActive = active === "face_up";
  const faceDownActive = active === "face_down";

  meSeat.face_up.forEach((c, idx) => {
    const el = miniCard(c);
    el.dataset.idx = String(idx);
    el.classList.add("face-up-slot");
    if (faceUpActive && view.you.your_turn) {
      el.classList.add("selectable");
      if (isLegalRank(c.rank, view)) el.classList.add("legal-hint");
      if (state.selectedIndices.has(idx) && active === "face_up") el.classList.add("selected");
      el.addEventListener("click", () => toggleSelect(idx, c.rank));
    } else {
      el.classList.add("disabled");
    }
    row.appendChild(el);
  });

  for (let i = 0; i < meSeat.face_down_count; i++) {
    const el = document.createElement("div");
    el.className = "mini-back face-down-slot";
    el.textContent = "♛";
    el.setAttribute("role", "listitem");
    el.setAttribute("aria-label", `Face-down card ${i + 1}`);
    el.title = "Face-down — play blind when your face-up cards are gone";
    if (faceDownActive && view.you.your_turn) {
      el.classList.add("selectable");
      el.addEventListener("click", () =>
        sendAction({ type: "play", source: "face_down", indices: [i] })
      );
    } else {
      el.classList.add("disabled");
    }
    row.appendChild(el);
  }
}

function buildSelectableCard(card, idx, view, sourceName) {
  const el = makeFaceCard(card);
  el.setAttribute("role", "listitem");
  el.dataset.idx = String(idx);
  if (state.selectedIndices.has(idx) && view.you.active_source === sourceName) {
    el.classList.add("selected");
  }
  const yourTurn = view.you.your_turn;
  const legal = isLegalRank(card.rank, view);
  if (legal && yourTurn && view.you.active_source === sourceName) {
    el.classList.add("legal-hint");
  }
  if (!yourTurn || view.you.active_source !== sourceName) {
    el.classList.add("disabled");
    return el;
  }
  el.addEventListener("click", () => toggleSelect(idx, card.rank));
  return el;
}

function isLegalRank(rank, view) {
  const reverse = reverseRankOf(view);
  // Three wilds: 2, 10, and the reverse rank are always legal.
  if (rank === 2 || rank === 10 || rank === reverse) return true;
  const top = view.pile_top;
  if (!top) return true;
  const reverseActive = view.under_reverse ?? view.under_seven ?? (top.rank === reverse);
  if (reverseActive) return rank < reverse;
  return rank >= top.rank;
}

function makeFaceCard(c) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `card ${isRedSuit(c.suit) ? "red" : "black"}`;
  const special = specialCardInfo(c.rank, state.view);
  const aria = special ? `${c.label} card — ${special}` : `${c.label} card`;
  btn.setAttribute("aria-label", aria);
  btn.title = special ? `${c.label}\n${special}` : c.label;
  btn.appendChild(makeCardFace(c));
  if (special) btn.classList.add("special");
  return btn;
}

const RANK_LABEL = { 11: "J", 12: "Q", 13: "K", 14: "A" };

function rankLabel(rank) {
  return RANK_LABEL[rank] || String(rank);
}

function reverseRankOf(view) {
  return view?.config?.reverse_rank ?? 5;
}

function specialCardInfo(rank, view) {
  if (rank === 2) return "Wild reset — always legal; next player can play anything.";
  if (rank === 10) return "Burn — always legal; clears the pile; you play again.";
  if (rank === reverseRankOf(view)) {
    return `Wild + Reverse — always legal; next play must be UNDER ${rankLabel(rank)}.`;
  }
  return null;
}

function toggleSelect(idx, rank) {
  // Selecting must keep all selected cards the same rank.
  const sources = currentSourceCards();
  const existing = [...state.selectedIndices].map((i) => sources[i].rank);
  if (state.selectedIndices.has(idx)) {
    state.selectedIndices.delete(idx);
  } else {
    if (existing.length && existing[0] !== rank) {
      state.selectedIndices.clear();
    }
    state.selectedIndices.add(idx);
  }
  paintSelection();
  refreshActionButtons(state.view);
}

function currentSourceCards() {
  const view = state.view;
  if (!view) return [];
  const source = view.you.active_source;
  if (source === "hand") return view.you.hand;
  const me = view.players.find((p) => p.pid === state.pid);
  if (source === "face_up") return me.face_up;
  return [];
}

function paintSelection() {
  const source = state.view?.you?.active_source;
  if (!source) return;
  const row = source === "hand" ? $("hand") : source === "face_up" ? $("your-table") : null;
  if (!row) return;
  [...row.children].forEach((el) => {
    if (source === "face_up" && !el.classList.contains("face-up-slot")) return;
    const idx = Number(el.dataset.idx);
    if (Number.isNaN(idx)) return;
    el.classList.toggle("selected", state.selectedIndices.has(idx));
  });
}

function refreshActionButtons(view) {
  const yourTurn = view?.you?.your_turn;
  const hasSelection = state.selectedIndices.size > 0;
  $("play-btn").disabled = !(yourTurn && hasSelection);
  $("pickup-btn").disabled = !(yourTurn && view.pile_size > 0);
}

function playSelected() {
  if (!state.view?.you?.your_turn) return;
  const source = state.view.you.active_source;
  if (!source || source === "face_down") return;
  const indices = [...state.selectedIndices].sort((a, b) => a - b);
  if (!indices.length) return;
  sendAction({ type: "play", source, indices });
  state.selectedIndices.clear();
}

function pickup() {
  sendAction({ type: "pickup" });
}

function sendAction(msg) {
  if (state.socket?.readyState === WebSocket.OPEN) {
    state.socket.send(JSON.stringify(msg));
  }
}

function renderStatus(view) {
  const stack = $("status-stack");
  stack.innerHTML = "";
  // Prefer the new structured list; fall back to the legacy single string.
  let entries = Array.isArray(view.last_actions) ? view.last_actions.slice() : null;
  if (!entries) {
    const text = view.last_action || "";
    entries = text ? [{ text }] : [];
  }
  if (!entries.length) return;

  const me = view.you;
  let suffix = "";
  if (!view.game_over) {
    suffix = me.your_turn ? " — Your turn." : ` — ${currentName(view)}'s turn.`;
  }

  entries.forEach((entry, idx) => {
    const isNewest = idx === entries.length - 1;
    const el = document.createElement("p");
    el.className = "status-entry" + (isNewest ? " newest" : " dim");
    if (entry.burned) el.classList.add("burned");
    if (entry.picked_up) el.classList.add("picked-up");
    if (entry.finished_pid) el.classList.add("finished");
    let text = entry.text || "";
    if (entry.burned) text += " 🔥";
    if (entry.picked_up) text += " ↑";
    if (entry.finished_pid) {
      const p = view.players.find((pl) => pl.pid === entry.finished_pid);
      if (p) text += ` 👑 ${p.name}`;
    }
    if (isNewest) {
      el.textContent = text + suffix;
      el.setAttribute("aria-live", "polite");
    } else {
      el.textContent = text;
      el.setAttribute("aria-hidden", "true");
    }
    stack.appendChild(el);
  });
}

function currentName(view) {
  const p = view.players.find((pl) => pl.pid === view.current_pid);
  return p ? p.name : "someone";
}

function renderResults(view) {
  const ol = $("results");
  ol.innerHTML = "";
  const winnerPid = view.finished_order[0];
  const winner = winnerPid ? view.players.find((p) => p.pid === winnerPid) : null;
  const youWon = winnerPid === state.pid;
  $("winner-name").textContent = winner
    ? `${winner.name} won the round!`
    : "Round over!";
  $("winner-subtitle").textContent = youWon
    ? "👑 That's you. Take a bow, Princess."
    : winner
      ? "Better luck next round."
      : "";
  view.finished_order.forEach((pid, i) => {
    const p = view.players.find((pl) => pl.pid === pid);
    if (!p) return;
    const li = document.createElement("li");
    const isLast = i === view.finished_order.length - 1;
    const isFirst = i === 0;
    const place = document.createElement("span");
    place.textContent = `${i + 1}. ${p.name}`;
    const tag = document.createElement("span");
    tag.textContent = isFirst ? "👑 Princess" : isLast ? "last place" : "";
    li.appendChild(place);
    li.appendChild(tag);
    if (isFirst) li.classList.add("princess");
    if (isLast) li.classList.add("last-place");
    ol.appendChild(li);
  });
  $("rematch-btn").hidden = !state.isHost;
  $("rematch-note").hidden = state.isHost;
}

async function playRematch() {
  try {
    await postJSON(`/api/rooms/${state.code}/rematch`, { host_pid: state.pid });
  } catch (e) { showError("action-error", e.message); }
}

function quitGame() {
  const dialog = $("quit-dialog");
  const actions = $("quit-dialog-actions");
  actions.innerHTML = "";
  const isHost = state.isHost;
  // "In a game" = the room has a game and it's not finished. Includes the
  // setup phase, since a seat that quits mid-setup still needs to either be
  // converted to a bot (so the deal can finish) or removed entirely.
  const inGame = state.view && !state.view.game_over;
  $("quit-dialog-body").textContent = inGame
    ? "The round is live. Pick what should happen to your seat."
    : "Leave this room?";

  const addAction = (label, klass, handler) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    if (klass) btn.classList.add(klass);
    btn.addEventListener("click", async () => {
      dialog.close();
      try { await handler(); }
      catch (e) { showError("action-error", e.message); }
    });
    actions.appendChild(btn);
  };

  if (inGame && !isHost) {
    addAction("Take over with a bot (continue the round)", "takeover", takeoverWithBot);
    addAction("Leave room", "danger", leaveAndGoHome);
  } else if (inGame && isHost) {
    addAction("End the round now", "takeover", endRoundNow);
    addAction("Abort the game (back to lobby)", "danger", abortGame);
  } else if (!isHost) {
    addAction("Leave room", "danger", leaveAndGoHome);
  } else {
    addAction("Abort the game (back to lobby)", "danger", abortGame);
  }

  dialog.showModal();
  if (actions.firstChild) actions.firstChild.focus();
}

async function takeoverWithBot() {
  await postJSON(`/api/rooms/${state.code}/leave`, {
    pid: state.pid,
    convert_to_bot: true,
  });
  if (state.socket) state.socket.close();
  location.href = "/";
}

async function leaveAndGoHome() {
  await postJSON(`/api/rooms/${state.code}/leave`, {
    pid: state.pid,
    convert_to_bot: false,
  });
  if (state.socket) state.socket.close();
  location.href = "/";
}

async function endRoundNow() {
  await postJSON(`/api/rooms/${state.code}/end_round`, { host_pid: state.pid });
}

async function abortGame() {
  await postJSON(`/api/rooms/${state.code}/abort`, { host_pid: state.pid });
}
