/*
 * Hall of Princesses page logic.
 *
 * Copyright 2026 Mike Huot
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 */

(function () {
  "use strict";

  var currentSort = "wins";

  function el(id) {
    return document.getElementById(id);
  }

  function escapeText(value) {
    return String(value == null ? "" : value);
  }

  function formatWinRate(rate) {
    if (typeof rate !== "number" || !isFinite(rate)) return "—";
    return (rate * 100).toFixed(1) + "%";
  }

  function renderRows(entries) {
    var body = el("lb-body");
    body.replaceChildren();
    for (var i = 0; i < entries.length; i += 1) {
      var entry = entries[i];
      var tr = document.createElement("tr");

      var rankTd = document.createElement("td");
      rankTd.className = "lb-rank";
      rankTd.textContent = String(i + 1);
      tr.appendChild(rankTd);

      var nameTd = document.createElement("td");
      nameTd.className = "lb-player";
      nameTd.textContent = escapeText(entry.display_name);
      tr.appendChild(nameTd);

      var winsTd = document.createElement("td");
      winsTd.className = "lb-num";
      winsTd.textContent = String(entry.princess_wins);
      tr.appendChild(winsTd);

      var lastTd = document.createElement("td");
      lastTd.className = "lb-num";
      lastTd.textContent = String(entry.last_places);
      tr.appendChild(lastTd);

      var roundsTd = document.createElement("td");
      roundsTd.className = "lb-num";
      roundsTd.textContent = String(entry.rounds_played);
      tr.appendChild(roundsTd);

      var rateTd = document.createElement("td");
      rateTd.className = "lb-num";
      rateTd.textContent = formatWinRate(entry.win_rate);
      tr.appendChild(rateTd);

      body.appendChild(tr);
    }
  }

  function setStatus(text) {
    var status = el("lb-status");
    if (text) {
      status.textContent = text;
      status.hidden = false;
    } else {
      status.textContent = "";
      status.hidden = true;
    }
  }

  function showState(state) {
    el("lb-table").hidden = state !== "rows";
    el("lb-empty").hidden = state !== "empty";
    el("lb-error").hidden = state !== "error";
    if (state === "rows" || state === "empty") {
      setStatus("");
    }
  }

  function updateSortButtons() {
    var btns = document.querySelectorAll(".lb-sort-btn");
    for (var i = 0; i < btns.length; i += 1) {
      var pressed = btns[i].dataset.sort === currentSort;
      btns[i].setAttribute("aria-pressed", pressed ? "true" : "false");
    }
  }

  function fetchLeaderboard() {
    showState("loading");
    setStatus("Loading…");
    var url = "/api/leaderboard?sort=" + encodeURIComponent(currentSort) + "&limit=50";
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (resp) {
        if (!resp.ok) {
          throw new Error("HTTP " + resp.status);
        }
        return resp.json();
      })
      .then(function (data) {
        var entries = (data && data.entries) || [];
        if (entries.length === 0) {
          showState("empty");
          return;
        }
        renderRows(entries);
        showState("rows");
      })
      .catch(function () {
        showState("error");
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btns = document.querySelectorAll(".lb-sort-btn");
    for (var i = 0; i < btns.length; i += 1) {
      btns[i].addEventListener("click", function (evt) {
        var next = evt.currentTarget.dataset.sort;
        if (next && next !== currentSort) {
          currentSort = next;
          updateSortButtons();
          fetchLeaderboard();
        }
      });
    }
    var retry = el("lb-retry");
    if (retry) {
      retry.addEventListener("click", fetchLeaderboard);
    }
    updateSortButtons();
    fetchLeaderboard();
  });
})();
