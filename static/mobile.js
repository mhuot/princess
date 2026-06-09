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
  sortHand: true,
  // Play & burn animations: advance only on NEW last_actions entries.
  lastSeenActionIndex: -1,
  // One-shot celebrate gate keyed to the round-ending action index.
  celebratedRoundId: null,
  // Set while a `play` message is in flight so an incoming error toast can
  // be attributed to that play (and shake the selected cards).
  expectingPlayReply: false,
  // Connection-state machine for websocket-reconnect. "live" hides the
  // banner; "reconnecting" / "reconnected" / "lost" surface it.
  connState: "live",
  _reconnectAttempt: 0,
  _firstCloseTs: null,
  _reconnectTimer: null,
  _reconnectedFlashTimer: null,
  // Session scoreboard from the room-server, keyed by pid. Updated on every
  // `lobby` and `state` message.
  scoreboard: {},
};

let handEndObserver = null;

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
  $("m-sort-btn").addEventListener("click", toggleSort);

  const actionBar = document.querySelector("#m-game .m-action-bar");
  if (actionBar) {
    const barHeight = actionBar.getBoundingClientRect().height || 80;
    handEndObserver = new IntersectionObserver(
      (entries) => {
        const chip = $("m-hand-scroll-hint");
        const entry = entries[0];
        if (!entry || !chip) return;
        if (entry.isIntersecting) {
          chip.hidden = true;
          return;
        }
        const threshold = window.innerHeight - barHeight;
        let hiddenCount = 0;
        document.querySelectorAll("#m-hand-row .m-hand-card").forEach((c) => {
          if (c.getBoundingClientRect().top >= threshold) hiddenCount++;
        });
        chip.hidden = hiddenCount === 0;
        chip.textContent = `↓ ${hiddenCount} more`;
      },
      { rootMargin: `0px 0px -${barHeight + 12}px 0px` }
    );
  }

  $("m-hand-scroll-hint").addEventListener("click", () => {
    const sentinel = $("m-hand-end-sentinel");
    if (sentinel) sentinel.scrollIntoView({ block: "end", behavior: "smooth" });
  });
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
  $("m-share-btn-lobby").addEventListener("click", () => shareRoomLink("m-share-btn-lobby"));
  $("m-share-btn-game").addEventListener("click", () => shareRoomLink("m-share-btn-game"));
  document.getElementById("m-switch-to-desktop")?.addEventListener("click", () => {
    document.cookie = "princess_prefer_desktop=1; Path=/";
    location.href = "/";
  });

  $("m-focused-name").addEventListener("input", () => {
    $("m-focused-join-btn").disabled = !$("m-focused-name").value.trim();
  });
  $("m-focused-join-btn").addEventListener("click", focusedJoinSubmit);

  const m = location.pathname.match(/^\/m\/([A-Z0-9]{4})$/i);
  if (m) {
    $("m-code").value = m[1].toUpperCase();
    autoJoinFromUrl(m[1].toUpperCase());
  }
});

// --- Storage helpers -------------------------------------------------------

function savePreferredName(name) {
  try { localStorage.setItem("princess_name", name); } catch { /* best-effort */ }
}

function loadPreferredName() {
  try { return localStorage.getItem("princess_name") || ""; } catch { return ""; }
}

function saveSession(code, pid, name) {
  try {
    sessionStorage.setItem(
      "princess_session",
      JSON.stringify({ code, pid, name })
    );
  } catch { /* best-effort */ }
}

function loadSession() {
  try {
    const raw = sessionStorage.getItem("princess_session");
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function clearSession() {
  try { sessionStorage.removeItem("princess_session"); } catch { /* ignore */ }
}

// Reset the partially-seated mobile DOM so a re-entered autoJoinFromUrl()
// (tier 2 or tier 3 after a 4001 sentinel rejection) starts from a clean
// landing.
function resetSeatedUi() {
  $("m-room").hidden = true;
  $("m-game").hidden = true;
  $("m-landing").hidden = false;
}

async function joinRoomBy(code, name) {
  const r = await postJSON(`/api/rooms/${code}/join`, { name });
  state.code = code;
  state.pid = r.pid;
  state.isHost = false;
  savePreferredName(name);
  saveSession(code, r.pid, name);
  enterRoom();
}

async function autoJoinFromUrl(urlCode) {
  // Tier 1: session sentinel.
  const sentinel = loadSession();
  if (sentinel && sentinel.code === urlCode && sentinel.pid) {
    state.code = sentinel.code;
    state.pid = sentinel.pid;
    state.isHost = false;
    enterRoom();
    return;
  }

  // Tier 2: saved name.
  const savedName = loadPreferredName();
  if (savedName) {
    try {
      await joinRoomBy(urlCode, savedName);
      return;
    } catch (e) {
      showError(e.message);
      return;
    }
  }

  // Tier 3: focused view.
  $("m-focused-code").textContent = urlCode;
  $("m-focused-join-btn").textContent = `Join room ${urlCode}`;
  $("m-focused-join-btn").disabled = true;
  $("m-landing").hidden = true;
  $("m-focused-join").hidden = false;
  state._autoJoinCode = urlCode;
  $("m-focused-name").focus();
}

async function focusedJoinSubmit() {
  const name = $("m-focused-name").value.trim();
  if (!name || !state._autoJoinCode) return;
  try {
    await joinRoomBy(state._autoJoinCode, name);
  } catch (e) {
    $("m-focused-join").hidden = true;
    $("m-landing").hidden = false;
    $("m-code").value = state._autoJoinCode;
    $("m-name").value = name;
    showError(e.message);
  }
}

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
  // If the toast lands in response to a `play` message, shake the cards
  // that were selected at the moment of the click. The DOM `.selected`
  // class survives until the next render even though `state.selectedIndices`
  // was cleared on send.
  if (state.expectingPlayReply) {
    state.expectingPlayReply = false;
    document
      .querySelectorAll("#m-hand-row .selected")
      .forEach((cardEl) => flashClass(cardEl, "is-illegal", 200));
  }
}

// Add a class to `el`, then remove it on `animationend` (one-shot) with a
// setTimeout safety net. No-op if `el` is null. CSS owns timing/easing.
function flashClass(el, cls, durationMs) {
  if (!el) return;
  el.classList.add(cls);
  const cleanup = () => el.classList.remove(cls);
  el.addEventListener("animationend", cleanup, { once: true });
  setTimeout(cleanup, durationMs + 50);
}

// Map a `view.last_actions[newest]` entry onto the right element animation.
// Called only when a new entry has appeared since the previous render.
function dispatchActionAnimations(entry) {
  if (!entry) return;
  if (entry.burned) {
    flashClass($("m-pile-card"), "is-burning", 300);
  }
  if (entry.picked_up) {
    flashClass(document.querySelector(".m-pile-area"), "is-pickup", 280);
    if (entry.player_pid === state.pid) {
      flashClass($("m-hand-row"), "is-pickup", 280);
    }
  }
}

// --- Lobby flow ------------------------------------------------------------

async function createRoom() {
  const name = $("m-name").value.trim();
  if (!name) return showError("Enter your name first.");
  try {
    const r = await postJSON("/api/rooms", { name });
    state.code = r.code; state.pid = r.pid; state.isHost = true;
    savePreferredName(name);
    saveSession(r.code, r.pid, name);
    enterRoom();
  } catch (e) { showError(e.message); }
}

async function joinRoom() {
  const name = $("m-name").value.trim();
  const code = $("m-code").value.trim().toUpperCase();
  if (!name) return showError("Enter your name first.");
  if (!code) return showError("Enter a 4-character room code.");
  try {
    await joinRoomBy(code, name);
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

// --- websocket-reconnect: connection banner + backoff helpers -------------

const CONN_BANNER_TEXT = {
  live: "",
  reconnecting: "Reconnecting…",
  reconnected: "Reconnected",
  lost: "Disconnected — refresh to reconnect.",
};

function setConnState(label) {
  state.connState = label;
  const banner = $("m-conn-banner");
  if (banner) {
    banner.textContent = CONN_BANNER_TEXT[label] || "";
    banner.classList.remove("reconnecting", "reconnected", "lost");
    if (label !== "live") banner.classList.add(label);
    banner.hidden = label === "live";
  }
  const disableActions = label === "reconnecting" || label === "lost";
  const playBtn = $("m-play-btn");
  const pickupBtn = $("m-pickup-btn");
  if (disableActions) {
    if (playBtn) playBtn.disabled = true;
    if (pickupBtn) pickupBtn.disabled = true;
  } else {
    if (playBtn) playBtn.disabled = false;
    if (pickupBtn) pickupBtn.disabled = false;
  }
}

function scheduleReconnect() {
  const attempt = state._reconnectAttempt;
  const delayMs = Math.min(2 ** (attempt - 1), 16) * 1000;
  if (state._reconnectTimer) clearTimeout(state._reconnectTimer);
  setConnState("reconnecting");
  state._reconnectTimer = setTimeout(openSocket, delayMs);
}

function openSocket() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${proto}://${location.host}/ws/${state.code}/${state.pid}`);
  state._wsGotMessage = false;
  state.socket.addEventListener("message", (e) => {
    state._wsGotMessage = true;
    handleMessage(JSON.parse(e.data));
    if (state.connState === "reconnecting") {
      // First inbound message after a reopen — server has resynced us.
      if (state._reconnectTimer) {
        clearTimeout(state._reconnectTimer);
        state._reconnectTimer = null;
      }
      state._reconnectAttempt = 0;
      state._firstCloseTs = null;
      setConnState("reconnected");
      if (state._reconnectedFlashTimer) clearTimeout(state._reconnectedFlashTimer);
      state._reconnectedFlashTimer = setTimeout(() => {
        state._reconnectedFlashTimer = null;
        setConnState("live");
      }, 1500);
    }
  });
  state.socket.addEventListener("close", (event) => {
    console.info("ws close", { code: event.code, reason: event.reason });
    if (event.code === 4001) {
      // Permanent rejection (server signaled unknown_room or unknown_pid):
      // clear the dead sentinel, reset the seated DOM, and re-enter the
      // auto-join chain in-page. No location.reload().
      clearSession();
      resetSeatedUi();
      const m = location.pathname.match(/^\/m\/([A-Z0-9]{4})$/i);
      if (m) autoJoinFromUrl(m[1].toUpperCase());
      return;
    }
    if (!state._wsGotMessage) {
      // Never connected successfully — show the static disconnect notice.
      // The websocket-reconnect retry loop only engages once we've had at
      // least one inbound message (i.e. the seat was actually live).
      $("m-waiting").textContent = "Disconnected. Refresh to reconnect.";
      return;
    }
    // Mid-session drop: start (or continue) the exponential-backoff retry.
    if (state._firstCloseTs === null) state._firstCloseTs = Date.now();
    state._reconnectAttempt += 1;
    const elapsed = Date.now() - state._firstCloseTs;
    if (state._reconnectAttempt > 10 || elapsed > 90_000) {
      if (state._reconnectTimer) {
        clearTimeout(state._reconnectTimer);
        state._reconnectTimer = null;
      }
      setConnState("lost");
      return;
    }
    scheduleReconnect();
  });
}

function handleMessage(msg) {
  if (msg.type === "lobby") {
    if (msg.room && msg.room.scoreboard) state.scoreboard = msg.room.scoreboard;
    renderLobby(msg.room);
  } else if (msg.type === "state") {
    if (msg.scoreboard) state.scoreboard = msg.scoreboard;
    renderGame(msg.view);
  } else if (msg.type === "error") {
    showError(msg.message);
  }
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
  // Reset the per-round animation bookkeeping on phase-out-of-playing so
  // the next round's first action fires its animation correctly.
  if (wasPhase === "playing" && view.phase !== "playing") {
    state.lastSeenActionIndex = -1;
    state.celebratedRoundId = null;
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

  // Edge-detect a NEW last_actions entry; dispatch event-driven animations
  // only when the tail index has actually advanced since the previous render.
  const actions = Array.isArray(view.last_actions) ? view.last_actions : [];
  const newest = actions.length - 1;
  if (view.phase === "playing" && newest > state.lastSeenActionIndex) {
    dispatchActionAnimations(actions[newest]);
    state.lastSeenActionIndex = newest;
  }
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

// Append inline `· Princess N` / `· Last N` chips next to a name. Sourced
// from `state.scoreboard`; zero counters render nothing.
function appendScoreBadges(parent, pid) {
  const entry = state.scoreboard?.[pid];
  if (!entry) return;
  if (entry.princess_wins > 0) {
    const span = document.createElement("span");
    span.className = "m-score-badge";
    span.textContent = ` · Princess ${entry.princess_wins}`;
    parent.appendChild(span);
  }
  if (entry.last_places > 0) {
    const span = document.createElement("span");
    span.className = "m-score-badge";
    span.textContent = ` · Last ${entry.last_places}`;
    parent.appendChild(span);
  }
}

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
    appendScoreBadges(name, p.pid);
    box.appendChild(name);
    const faceUpRow = document.createElement("div");
    faceUpRow.className = "m-opp-face-up";
    (p.face_up || []).forEach((c) => {
      const el = document.createElement("span");
      el.className = "m-opp-mini-card " + (isRedSuit(c.suit) ? "red" : "black");
      el.textContent = `${rankLabel(c.rank)}${suitGlyph(c.suit)}`;
      if (isSpecialRank(c.rank, view)) el.classList.add("special");
      faceUpRow.appendChild(el);
    });
    box.appendChild(faceUpRow);
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
  $("m-discard-count").textContent = String(view.pile_size || 0);
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
  const toolbar = $("m-hand-toolbar");
  const wrap = $("m-hand-wrap");
  const row = $("m-hand-row");
  row.innerHTML = "";
  const me = view.you;
  const rawCards = me.hand || [];
  if (!rawCards.length || me.active_source !== "hand") {
    toolbar.hidden = true;
    wrap.hidden = true;
    $("m-hand-scroll-hint").hidden = true;
    return;
  }
  toolbar.hidden = false;
  wrap.hidden = false;
  // Re-render the hand-count slot from scratch so we can append the user's
  // session badges next to it (the wherever-the-user's-name-renders surface
  // on mobile).
  const countSlot = $("m-hand-count");
  countSlot.textContent = `${rawCards.length} card${rawCards.length === 1 ? "" : "s"}`;
  appendScoreBadges(countSlot, state.pid);

  // Build [{c, idx}] pairs so we can sort while preserving server-side indices.
  const items = rawCards.map((c, i) => ({ c, idx: i }));
  if (state.sortHand) {
    items.sort((a, b) => a.c.rank - b.c.rank || a.idx - b.idx);
  }

  items.forEach(({ c, idx }) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "m-hand-card " + (isRedSuit(c.suit) ? "red" : "black");
    btn.setAttribute("role", "listitem");
    btn.dataset.idx = String(idx);
    btn.innerHTML = `<span>${rankLabel(c.rank)}</span><span>${suitGlyph(c.suit)}</span>`;
    if (isSpecialRank(c.rank, view)) btn.classList.add("special");
    if (isLegalRank(c.rank, view) && me.your_turn) btn.classList.add("legal-hint");
    if (state.selectedIndices.has(idx) && me.active_source === "hand") btn.classList.add("selected");
    btn.addEventListener("click", () => toggleSelect(idx, c.rank));
    row.appendChild(btn);
  });

  const sentinel = document.createElement("span");
  sentinel.id = "m-hand-end-sentinel";
  sentinel.setAttribute("aria-hidden", "true");
  row.appendChild(sentinel);
  if (handEndObserver) {
    handEndObserver.disconnect();
    handEndObserver.observe(sentinel);
  }
}

function toggleSort() {
  state.sortHand = !state.sortHand;
  const btn = $("m-sort-btn");
  btn.setAttribute("aria-pressed", String(state.sortHand));
  btn.textContent = state.sortHand ? "Sort: rank" : "Sort: off";
  if (state.view) renderHand(state.view);
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
  // Mark the outbound play so an incoming error toast can shake the cards.
  state.expectingPlayReply = true;
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
  // Celebrate the winner-name once per round; subsequent re-renders of the
  // game-over panel (e.g., pre-rematch broadcasts) do not re-fire.
  const roundId = `${winnerPid || "noone"}:${Array.isArray(view.last_actions) ? view.last_actions.length : 0}`;
  if (winner && state.celebratedRoundId !== roundId) {
    flashClass($("m-winner-name"), "is-celebrating", 350);
    state.celebratedRoundId = roundId;
  }

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

  renderSessionRecord();

  $("m-rematch-btn").hidden = !state.isHost;
  $("m-rematch-note").hidden = state.isHost;
}

function renderSessionRecord() {
  const slot = $("m-session-record");
  if (!slot) return;
  const entry = state.scoreboard?.[state.pid];
  if (!entry || !entry.rounds_played) {
    slot.hidden = true;
    slot.textContent = "";
    return;
  }
  const parts = [`Princess ${entry.princess_wins}`];
  if (entry.last_places > 0) {
    parts.push(`Last place ${entry.last_places}`);
  }
  const rounds = entry.rounds_played;
  parts.push(`${rounds} round${rounds === 1 ? "" : "s"}`);
  slot.textContent = `Session record: ${parts.join(" · ")}`;
  slot.hidden = false;
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
  } catch (e) {
    showError(e.message);
    const inp = $("m-rename-input");
    inp.focus();
    inp.select();
  }
}

async function copyRoomCode() {
  if (!state.code) return;
  try { await navigator.clipboard.writeText(state.code); }
  catch { /* clipboard not available — silent */ }
}

async function shareRoomLink(buttonId) {
  if (!state.code) return;
  const url = `${location.origin}/m/${state.code}`;
  const payload = {
    title: "Princess Card Game",
    text: `Join my Princess room ${state.code}:`,
    url,
  };
  if (navigator.share) {
    try { await navigator.share(payload); return; }
    catch (e) { if (e.name === "AbortError") return; /* fall through */ }
  }
  try {
    await navigator.clipboard.writeText(url);
    if (buttonId) flashShareButton(buttonId);
  } catch { /* silent */ }
}

function flashShareButton(buttonId) {
  const btn = $(buttonId);
  if (!btn || btn.dataset.flashing === "1") return;
  btn.dataset.flashing = "1";
  const prev = btn.textContent;
  btn.textContent = "✓";
  setTimeout(() => {
    btn.textContent = prev;
    delete btn.dataset.flashing;
  }, 1500);
}

function sendAction(msg) {
  if (state.socket?.readyState === WebSocket.OPEN) {
    state.socket.send(JSON.stringify(msg));
  }
}
