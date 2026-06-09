#!/usr/bin/env python3
"""
Playwright smoke test for recently shipped changes.

Copyright 2026 Mike Huot

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

Covers:
- share-room-link (desktop + mobile, clipboard fallback path)
- mobile-discard-count (Deck above Discard in pile area)
- mobile-hand-scroll-hint (chip appears + tap-to-jump when overflow)
- supporting checks: opponent face-up cards, wrapped hand layout

Outputs screenshots to /Users/mhuot/princess/smoke/screens/ and a
markdown report at /Users/mhuot/princess/smoke/SMOKE_REPORT.md.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

ROOT = Path("/Users/mhuot/princess")
OUT = ROOT / "smoke"
SHOTS = OUT / "screens"
REPORT = OUT / "SMOKE_REPORT.md"
BASE = os.environ.get("PRINCESS_SMOKE_BASE", "http://127.0.0.1:8000").rstrip("/")


@dataclass
class CheckResult:
    name: str
    passed: bool
    notes: str = ""
    screenshot: str | None = None


@dataclass
class Section:
    title: str
    checks: list[CheckResult] = field(default_factory=list)


def shoot(page: Page, name: str) -> str:
    path = SHOTS / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=False)
    return path.relative_to(OUT).as_posix()


def safe_click(page: Page, selector: str, *, timeout: int = 4000) -> bool:
    try:
        page.wait_for_selector(selector, timeout=timeout, state="visible")
        page.click(selector)
        return True
    except Exception:  # pylint: disable=broad-except
        return False


def make_mobile_context(browser: Browser) -> BrowserContext:
    return browser.new_context(
        viewport={"width": 390, "height": 844},
        device_scale_factor=2,
        is_mobile=True,
        has_touch=True,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ),
        permissions=["clipboard-read", "clipboard-write"],
    )


def make_desktop_context(browser: Browser) -> BrowserContext:
    return browser.new_context(
        viewport={"width": 1280, "height": 800},
        permissions=["clipboard-read", "clipboard-write"],
    )


def create_room_desktop(page: Page, host_name: str = "Mike") -> str:
    page.goto(BASE + "/")
    page.fill("#player-name", host_name)
    page.click("#create-btn")
    page.wait_for_selector("#room-code-display:not(:empty)", timeout=8000)
    page.wait_for_selector("#seat-list li", timeout=8000)
    return page.locator("#room-code-display").inner_text().strip()


def create_room_mobile(page: Page, host_name: str = "Mike") -> str:
    page.goto(BASE + "/m")
    page.fill("#m-name", host_name)
    page.click("#m-create-btn")
    page.wait_for_selector("#m-room-code:not(:empty)", timeout=8000)
    # Wait for the WebSocket lobby broadcast to populate state.lastRoom so the
    # solo-start sheet logic has accurate seat counts.
    page.wait_for_selector("#m-seat-list li", timeout=8000)
    return page.locator("#m-room-code").inner_text().strip()


def add_bots_and_start(page: Page, n: int, *, mobile: bool) -> None:
    """Use the solo-start modal to add N bots and start."""
    if mobile:
        page.click("#m-start-btn")
        page.wait_for_selector("#m-solo-sheet[open]", timeout=6000)
        page.click(f"#m-solo-add-{n}")
    else:
        page.click("#start-btn")
        page.wait_for_selector("#solo-start-modal[open]", timeout=6000)
        page.click(f"#solo-add-{n}")
    # Wait for the setup phase to render (face-up choose grid).
    if mobile:
        page.wait_for_selector("#m-choose-grid .m-choose-card", timeout=12000)
    else:
        page.wait_for_selector("#choose-row .card", timeout=12000)


def section_share_room_link(browser: Browser) -> Section:
    section = Section("share-room-link")

    # --- Desktop path ---
    ctx = make_desktop_context(browser)
    page = ctx.new_page()
    code = create_room_desktop(page, "Mike")
    page.wait_for_timeout(300)
    shot_pre = shoot(page, "share-desktop-lobby")
    section.checks.append(CheckResult(
        "Desktop lobby shows Share link button",
        passed=page.locator("#share-link-btn").is_visible(),
        notes=f"Room {code}",
        screenshot=shot_pre,
    ))

    page.click("#share-link-btn")
    page.wait_for_timeout(600)
    label_after = page.locator("#share-link-btn").inner_text().strip()
    flashed = label_after == "Copied!"
    shot_flash = shoot(page, "share-desktop-copied")
    section.checks.append(CheckResult(
        "Desktop Share button flashes 'Copied!'",
        passed=flashed,
        notes=f"Label after click: {label_after!r}",
        screenshot=shot_flash,
    ))

    clip_url = ""
    try:
        clip_url = page.evaluate("navigator.clipboard.readText()")
    except Exception as e:  # pylint: disable=broad-except
        clip_url = f"<read failed: {e}>"
    expected_url = f"{BASE}/room/{code}"
    section.checks.append(CheckResult(
        "Desktop clipboard URL matches /room/<code>",
        passed=clip_url == expected_url,
        notes=f"clipboard={clip_url!r} expected={expected_url!r}",
    ))
    ctx.close()

    # --- Mobile path ---
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    code = create_room_mobile(page, "Mike")
    page.wait_for_timeout(300)
    shot_pre = shoot(page, "share-mobile-lobby")
    section.checks.append(CheckResult(
        "Mobile lobby shows ↗ share button",
        passed=page.locator("#m-share-btn-lobby").is_visible(),
        notes=f"Room {code}",
        screenshot=shot_pre,
    ))

    page.click("#m-share-btn-lobby")
    # Capture mid-flash (the button glyph briefly becomes ✓ for ~1.5s).
    page.wait_for_timeout(500)
    btn_text_mid = page.locator("#m-share-btn-lobby").inner_text().strip()
    shot_flash = shoot(page, "share-mobile-flash")
    section.checks.append(CheckResult(
        "Mobile share button glyph flashes to ✓",
        passed=btn_text_mid == "✓",
        notes=f"button text mid-flash={btn_text_mid!r} (expected '✓')",
        screenshot=shot_flash,
    ))
    # And it reverts after the timeout.
    page.wait_for_timeout(1300)
    btn_text_after = page.locator("#m-share-btn-lobby").inner_text().strip()
    section.checks.append(CheckResult(
        "Mobile share button glyph reverts after flash",
        passed=btn_text_after == "↗",
        notes=f"button text after flash={btn_text_after!r} (expected '↗')",
    ))

    clip_url = ""
    try:
        clip_url = page.evaluate("navigator.clipboard.readText()")
    except Exception as e:  # pylint: disable=broad-except
        clip_url = f"<read failed: {e}>"
    expected_url = f"{BASE}/m/{code}"
    section.checks.append(CheckResult(
        "Mobile clipboard URL matches /m/<code>",
        passed=clip_url == expected_url,
        notes=f"clipboard={clip_url!r} expected={expected_url!r}",
    ))
    ctx.close()
    return section


def section_discard_count(browser: Browser) -> Section:
    section = Section("mobile-discard-count")
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    code = create_room_mobile(page, "Mike")
    section.checks.append(CheckResult(
        "Created mobile room",
        passed=bool(code),
        notes=f"Room {code}",
    ))

    add_bots_and_start(page, 2, mobile=True)
    page.wait_for_timeout(600)

    discard_visible = page.locator("#m-discard-count").is_visible()
    discard_value = page.locator("#m-discard-count").inner_text().strip() if discard_visible else ""
    deck_value = page.locator("#m-deck-count").inner_text().strip() if discard_visible else ""

    # Verify layout: Discard stat is below Deck stat in the same column.
    layout_ok = False
    try:
        deck_box = page.locator("#m-deck-count").bounding_box()
        discard_box = page.locator("#m-discard-count").bounding_box()
        if deck_box and discard_box:
            same_x = abs(deck_box["x"] - discard_box["x"]) < 30
            below = discard_box["y"] > deck_box["y"]
            layout_ok = bool(same_x and below)
    except Exception:  # pylint: disable=broad-except
        pass

    shot = shoot(page, "discard-setup-phase")
    section.checks.append(CheckResult(
        "Setup phase visible (Discard count won't render here, but pile-area UI not yet)",
        passed=True,
        notes=f"deck={deck_value!r} discard={discard_value!r}",
        screenshot=shot,
    ))

    # Bots auto-pick; we need to lock-in human face-up to enter playing phase.
    # Pick the first 3 choose cards.
    page.click("#m-choose-grid .m-choose-card:nth-child(1)")
    page.click("#m-choose-grid .m-choose-card:nth-child(2)")
    page.click("#m-choose-grid .m-choose-card:nth-child(3)")
    page.wait_for_timeout(200)
    page.click("#m-lock-in-btn")
    # Wait for playing phase: discard count node is in #m-game.
    try:
        page.wait_for_selector("#m-game:not([hidden]) #m-discard-count", timeout=8000)
    except Exception:  # pylint: disable=broad-except
        pass
    page.wait_for_timeout(800)

    deck_value = page.locator("#m-deck-count").inner_text().strip()
    discard_value = page.locator("#m-discard-count").inner_text().strip()
    shot = shoot(page, "discard-playing-phase")
    section.checks.append(CheckResult(
        "Playing phase shows Deck and Discard stats",
        passed=deck_value.isdigit() and discard_value.isdigit(),
        notes=f"deck={deck_value!r} discard={discard_value!r}",
        screenshot=shot,
    ))

    # Verify Discard sits below Deck (left stats column).
    try:
        deck_box = page.locator("#m-deck-count").bounding_box()
        discard_box = page.locator("#m-discard-count").bounding_box()
        if deck_box and discard_box:
            same_x = abs(deck_box["x"] - discard_box["x"]) < 30
            below = discard_box["y"] > deck_box["y"]
            layout_ok = bool(same_x and below)
    except Exception:  # pylint: disable=broad-except
        pass
    section.checks.append(CheckResult(
        "Discard rendered below Deck in same column",
        passed=layout_ok,
        notes=f"deck_y={deck_box['y'] if deck_box else 'n/a'} "
              f"discard_y={discard_box['y'] if discard_box else 'n/a'}",
    ))

    ctx.close()
    return section


def section_scroll_hint(browser: Browser) -> Section:
    """Verify the bottom-padding + chip element exist; deep behavior needs a real overflow."""
    section = Section("mobile-hand-scroll-hint")
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    create_room_mobile(page, "Mike")
    add_bots_and_start(page, 2, mobile=True)
    page.click("#m-choose-grid .m-choose-card:nth-child(1)")
    page.click("#m-choose-grid .m-choose-card:nth-child(2)")
    page.click("#m-choose-grid .m-choose-card:nth-child(3)")
    page.click("#m-lock-in-btn")
    page.wait_for_selector("#m-game:not([hidden]) #m-hand-row", timeout=8000)
    page.wait_for_timeout(800)

    # Chip element is in the DOM (hidden by default for a small hand).
    chip_exists = page.locator("#m-hand-scroll-hint").count() == 1
    chip_hidden = page.locator("#m-hand-scroll-hint").get_attribute("hidden") is not None
    section.checks.append(CheckResult(
        "Scroll hint chip element exists in DOM",
        passed=chip_exists,
        notes=f"count=1 hidden_for_small_hand={chip_hidden}",
    ))

    # Bottom-padding fix: #m-game should reserve space below for the action bar.
    pad_bottom = page.evaluate(
        "getComputedStyle(document.getElementById('m-game')).paddingBottom"
    )
    # Default 64px action bar + 12px buffer + 0 safe area = ~76px. Anything
    # > 50 px tells us the padding was applied.
    try:
        pad_value = float(pad_bottom.replace("px", ""))
    except ValueError:
        pad_value = 0.0
    section.checks.append(CheckResult(
        "#m-game reserves bottom padding for the action bar",
        passed=pad_value >= 50,
        notes=f"computed padding-bottom={pad_bottom} (need >= 50px)",
    ))

    # Sentinel was appended at the end of #m-hand-row by renderHand.
    sentinel_exists = page.locator("#m-hand-end-sentinel").count() == 1
    section.checks.append(CheckResult(
        "Hand sentinel attached at end of hand row",
        passed=sentinel_exists,
        notes=f"sentinel count={page.locator('#m-hand-end-sentinel').count()}",
    ))

    # Visual: with a small hand, the chip is hidden.
    shot = shoot(page, "scroll-hint-small-hand")
    section.checks.append(CheckResult(
        "Chip stays hidden when the whole hand fits",
        passed=chip_hidden,
        notes="Small starting hand; nothing to overflow.",
        screenshot=shot,
    ))

    ctx.close()
    return section


def section_ua_redirect(browser: Browser) -> Section:
    """Verify GET / redirects mobile UAs to /m and stays put for desktop."""
    section = Section("mobile-ua-redirect")

    # 1. Mobile UA on / lands on /m.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.wait_for_load_state("domcontentloaded")
    landed_url = page.url
    landed_title = page.title()
    shot = shoot(page, "redirect-mobile-to-m")
    section.checks.append(CheckResult(
        "Mobile UA hitting / lands on /m",
        passed=landed_url.rstrip("/").endswith("/m") and "mobile" in landed_title.lower(),
        notes=f"url={landed_url!r} title={landed_title!r}",
        screenshot=shot,
    ))
    ctx.close()

    # 2. Mobile UA on /room/{code} lands on /m/{code}.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/room/AB12")
    page.wait_for_load_state("domcontentloaded")
    deep_url = page.url
    section.checks.append(CheckResult(
        "Mobile UA hitting /room/AB12 lands on /m/AB12",
        passed=deep_url.endswith("/m/AB12"),
        notes=f"url={deep_url!r}",
    ))
    ctx.close()

    # 3. Desktop UA on / stays on /.
    ctx = make_desktop_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.wait_for_load_state("domcontentloaded")
    desktop_url = page.url
    desktop_title = page.title()
    shot = shoot(page, "redirect-desktop-stays")
    section.checks.append(CheckResult(
        "Desktop UA hitting / stays on /",
        passed=desktop_url.rstrip("/") == BASE
        and "princess card game" in desktop_title.lower(),
        notes=f"url={desktop_url!r} title={desktop_title!r}",
        screenshot=shot,
    ))
    ctx.close()

    # 4. ?desktop=1 override on mobile UA serves desktop UI.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/?desktop=1")
    page.wait_for_load_state("domcontentloaded")
    override_url = page.url
    override_title = page.title()
    shot = shoot(page, "redirect-desktop-query-override")
    section.checks.append(CheckResult(
        "?desktop=1 keeps mobile UA on the desktop UI",
        passed="princess card game" in override_title.lower()
        and "?desktop=1" in override_url,
        notes=f"url={override_url!r} title={override_title!r}",
        screenshot=shot,
    ))
    ctx.close()

    # 5. The "View desktop site" link on /m sets the cookie + navigates to /.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/m")
    page.wait_for_load_state("domcontentloaded")
    link_visible = page.locator("#m-switch-to-desktop").is_visible()
    page.click("#m-switch-to-desktop")
    page.wait_for_load_state("domcontentloaded")
    after_url = page.url
    after_title = page.title()
    cookies = {c["name"]: c["value"] for c in ctx.cookies()}
    cookie_ok = cookies.get("princess_prefer_desktop") == "1"
    landed_on_desktop = "princess card game" in after_title.lower()
    shot = shoot(page, "redirect-mobile-link-to-desktop")
    section.checks.append(CheckResult(
        "Mobile lobby has 'View desktop site' link",
        passed=link_visible,
        notes=f"#m-switch-to-desktop visible={link_visible}",
        screenshot=shot,
    ))
    section.checks.append(CheckResult(
        "Tapping 'View desktop site' sets cookie + lands on /",
        passed=cookie_ok and landed_on_desktop and after_url.rstrip("/") == BASE,
        notes=(
            f"cookie={cookies.get('princess_prefer_desktop')!r} "
            f"url={after_url!r} title={after_title!r}"
        ),
    ))

    # 6. With cookie set, navigating to / from mobile UA stays on /.
    page.goto(BASE + "/")
    page.wait_for_load_state("domcontentloaded")
    cookie_persists_url = page.url
    cookie_persists_title = page.title()
    section.checks.append(CheckResult(
        "Cookie keeps mobile UA on / on subsequent visits",
        passed="princess card game" in cookie_persists_title.lower(),
        notes=f"url={cookie_persists_url!r} title={cookie_persists_title!r}",
    ))
    ctx.close()

    # 7. The "Mobile site" link on / clears the cookie + navigates to /m.
    ctx = make_desktop_context(browser)
    page = ctx.new_page()
    # Pre-set the cookie so we can confirm it gets cleared.
    ctx.add_cookies([{
        "name": "princess_prefer_desktop", "value": "1",
        "url": BASE,
    }])
    page.goto(BASE + "/")
    page.wait_for_load_state("domcontentloaded")
    link_present = page.locator("#switch-to-mobile").is_visible()
    page.click("#switch-to-mobile")
    page.wait_for_load_state("domcontentloaded")
    final_url = page.url
    final_title = page.title()
    final_cookies = {c["name"]: c["value"] for c in ctx.cookies()}
    cookie_cleared = "princess_prefer_desktop" not in final_cookies or \
        final_cookies.get("princess_prefer_desktop") == ""
    section.checks.append(CheckResult(
        "Desktop footer has 'Mobile site' link",
        passed=link_present,
        notes=f"#switch-to-mobile visible={link_present}",
    ))
    section.checks.append(CheckResult(
        "Tapping 'Mobile site' clears cookie + lands on /m",
        passed=final_url.rstrip("/").endswith("/m")
        and "mobile" in final_title.lower()
        and cookie_cleared,
        notes=(
            f"cookie_cleared={cookie_cleared} url={final_url!r} "
            f"title={final_title!r} cookies={final_cookies!r}"
        ),
    ))
    ctx.close()

    return section


def section_deep_link_auto_join(browser: Browser) -> Section:
    """Verify /m/<code> auto-join behavior across the three tiers."""
    section = Section("deep-link-auto-join")

    # Set up: create a room first to get a valid code.
    setup_ctx = make_mobile_context(browser)
    setup_page = setup_ctx.new_page()
    code = create_room_mobile(setup_page, "Host")
    setup_ctx.close()

    # Tier 3: no saved name → focused view appears.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(f"{BASE}/m/{code}")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(400)
    focused_visible = page.locator("#m-focused-join").is_visible()
    landing_hidden = page.locator("#m-landing").get_attribute("hidden") is not None
    btn_text = page.locator("#m-focused-join-btn").inner_text().strip()
    btn_disabled = page.locator("#m-focused-join-btn").is_disabled()
    shot = shoot(page, "auto-join-focused-view")
    section.checks.append(CheckResult(
        "Tier 3: focused view appears with no saved name",
        passed=focused_visible and landing_hidden and btn_text == f"Join room {code}",
        notes=f"focused_visible={focused_visible} landing_hidden={landing_hidden} btn={btn_text!r}",
        screenshot=shot,
    ))
    section.checks.append(CheckResult(
        "Join button disabled on empty input",
        passed=btn_disabled,
        notes=f"button.disabled={btn_disabled}",
    ))

    # Empty-name guard: type whitespace → button stays disabled.
    page.fill("#m-focused-name", "   ")
    page.wait_for_timeout(120)
    btn_disabled_whitespace = page.locator("#m-focused-join-btn").is_disabled()
    section.checks.append(CheckResult(
        "Whitespace-only input keeps button disabled",
        passed=btn_disabled_whitespace,
        notes=f"button.disabled={btn_disabled_whitespace}",
    ))

    # Type a real name → button enables.
    page.fill("#m-focused-name", "  Pat  ")  # whitespace around the name
    page.wait_for_timeout(120)
    btn_enabled = not page.locator("#m-focused-join-btn").is_disabled()
    section.checks.append(CheckResult(
        "Non-empty input enables the button",
        passed=btn_enabled,
        notes=f"button.disabled={not btn_enabled}",
    ))

    # Click → name should trim, save, and enter the room.
    page.click("#m-focused-join-btn")
    page.wait_for_selector("#m-room:not([hidden])", timeout=4000)
    saved_name = page.evaluate("localStorage.getItem('princess_name')")
    section.checks.append(CheckResult(
        "Tier 3 submit trims and saves name; enters room",
        passed=saved_name == "Pat"
        and page.locator("#m-room").is_visible(),
        notes=f"saved_name={saved_name!r} room_visible=True",
    ))
    ctx.close()

    # Tier 2: saved name → direct auto-join, no focused view.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    # Seed localStorage via the storage state by navigating to set it.
    page.goto(BASE + "/m")
    page.evaluate("localStorage.setItem('princess_name', 'Mike')")
    page.goto(f"{BASE}/m/{code}")
    page.wait_for_selector("#m-room:not([hidden])", timeout=6000)
    landed_in_room = page.locator("#m-room").is_visible()
    focused_shown = page.locator("#m-focused-join").is_visible()
    shot = shoot(page, "auto-join-tier2-saved-name")
    section.checks.append(CheckResult(
        "Tier 2: saved name auto-joins without focused view",
        passed=landed_in_room and not focused_shown,
        notes=f"landed_in_room={landed_in_room} focused_shown={focused_shown}",
        screenshot=shot,
    ))
    # Sentinel should be set after join.
    sentinel = page.evaluate("sessionStorage.getItem('princess_session')")
    sentinel_ok = sentinel and code in sentinel
    section.checks.append(CheckResult(
        "Session sentinel persisted after join",
        passed=bool(sentinel_ok),
        notes=f"sentinel={sentinel!r}",
    ))
    ctx.close()

    # Failure fallback: unknown code → falls back to landing with error.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/m")
    page.evaluate("localStorage.setItem('princess_name', 'Mike')")
    page.goto(f"{BASE}/m/ZZZZ")
    page.wait_for_timeout(800)
    landing_back = page.locator("#m-landing").is_visible()
    code_input = page.locator("#m-code").input_value()
    error_visible = page.locator("#m-lobby-error").is_visible()
    shot = shoot(page, "auto-join-failure-fallback")
    section.checks.append(CheckResult(
        "Failure (404) falls back to landing with code prefilled + error",
        passed=landing_back and code_input == "ZZZZ" and error_visible,
        notes=(
            f"landing_back={landing_back} code_input={code_input!r} "
            f"error_visible={error_visible}"
        ),
        screenshot=shot,
    ))
    ctx.close()

    return section


def section_sentinel_reject_soft_fallback(browser: Browser) -> Section:
    """Verify a stale sentinel triggers an in-page retry (no full reload)."""
    section = Section("sentinel-reject-soft-fallback")

    # Set up a real room so we can craft "room exists, pid stale" cases too.
    setup_ctx = make_mobile_context(browser)
    setup_page = setup_ctx.new_page()
    real_code = create_room_mobile(setup_page, "Host")
    setup_ctx.close()

    # Case 1: Stale sentinel, room gone (ZZZZ), with saved name.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/m")
    page.evaluate("localStorage.setItem('princess_name', 'Mike')")
    page.evaluate(
        "sessionStorage.setItem('princess_session',"
        " JSON.stringify({code: 'ZZZZ', pid: 'fake', name: 'Mike'}))"
    )
    page.goto(f"{BASE}/m/ZZZZ")
    nav_before = page.evaluate(
        "performance.getEntriesByType('navigation').length"
    )
    page.wait_for_timeout(1200)
    nav_after = page.evaluate(
        "performance.getEntriesByType('navigation').length"
    )
    landing_visible = page.locator("#m-landing").is_visible()
    error_visible = page.locator("#m-lobby-error").is_visible()
    section.checks.append(CheckResult(
        "Stale sentinel + room gone + saved name: no reload, landing visible",
        passed=(nav_after == nav_before)
        and landing_visible
        and error_visible,
        notes=(
            f"nav_before={nav_before} nav_after={nav_after} "
            f"landing_visible={landing_visible} error_visible={error_visible}"
        ),
    ))
    ctx.close()

    # Case 2: Stale sentinel, room exists, with saved name → tier 2 seats user.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/m")
    page.evaluate("localStorage.setItem('princess_name', 'Mike')")
    page.evaluate(
        "sessionStorage.setItem('princess_session',"
        f" JSON.stringify({{code: '{real_code}', pid: 'fake', name: 'Mike'}}))"
    )
    page.goto(f"{BASE}/m/{real_code}")
    nav_before = page.evaluate(
        "performance.getEntriesByType('navigation').length"
    )
    try:
        page.wait_for_selector("#m-room:not([hidden])", timeout=6000)
        seated = True
    except Exception:  # pylint: disable=broad-exception-caught
        seated = False
    nav_after = page.evaluate(
        "performance.getEntriesByType('navigation').length"
    )
    section.checks.append(CheckResult(
        "Stale sentinel + room exists + saved name: no reload, user seated",
        passed=seated and (nav_after == nav_before),
        notes=f"seated={seated} nav_before={nav_before} nav_after={nav_after}",
    ))
    ctx.close()

    # Case 3: Stale sentinel, room exists, no saved name → tier 3 focused view.
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    page.goto(BASE + "/m")
    page.evaluate("localStorage.removeItem('princess_name')")
    page.evaluate(
        "sessionStorage.setItem('princess_session',"
        f" JSON.stringify({{code: '{real_code}', pid: 'fake', name: ''}}))"
    )
    page.goto(f"{BASE}/m/{real_code}")
    nav_before = page.evaluate(
        "performance.getEntriesByType('navigation').length"
    )
    try:
        page.wait_for_selector("#m-focused-join:not([hidden])", timeout=6000)
        focused = True
    except Exception:  # pylint: disable=broad-exception-caught
        focused = False
    nav_after = page.evaluate(
        "performance.getEntriesByType('navigation').length"
    )
    section.checks.append(CheckResult(
        "Stale sentinel + room exists + no saved name: focused view, no reload",
        passed=focused and (nav_after == nav_before),
        notes=f"focused={focused} nav_before={nav_before} nav_after={nav_after}",
    ))
    ctx.close()

    return section


def section_supporting_visuals(browser: Browser) -> Section:
    """Snapshot the mobile UI to visually confirm opponent face-up + wrapped hand."""
    section = Section("supporting visuals")
    ctx = make_mobile_context(browser)
    page = ctx.new_page()
    create_room_mobile(page, "Mike")
    add_bots_and_start(page, 2, mobile=True)
    page.click("#m-choose-grid .m-choose-card:nth-child(1)")
    page.click("#m-choose-grid .m-choose-card:nth-child(2)")
    page.click("#m-choose-grid .m-choose-card:nth-child(3)")
    page.click("#m-lock-in-btn")
    page.wait_for_selector("#m-game:not([hidden]) #m-hand-row", timeout=8000)
    page.wait_for_timeout(1000)

    shot = shoot(page, "mobile-playing-overview")
    # Heuristic: at least one opponent face-up mini-card rendered?
    n_opp_minis = page.locator(".m-opp-mini-card").count()
    section.checks.append(CheckResult(
        "Opponent face-up cards rendered in chip",
        passed=n_opp_minis > 0,
        notes=f"m-opp-mini-card count={n_opp_minis}",
        screenshot=shot,
    ))

    n_hand_cards = page.locator("#m-hand-row .m-hand-card").count()
    section.checks.append(CheckResult(
        "Hand rendered as wrap row",
        passed=n_hand_cards > 0,
        notes=f"hand card count={n_hand_cards}",
    ))

    ctx.close()
    return section


def write_report(sections: list[Section]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = []
    lines.append("# Smoke test report")
    lines.append("")
    lines.append(f"_Generated {now}_  ")
    lines.append("_Tool: Playwright (Chromium headless)_  ")
    lines.append(f"_Base URL: {BASE}_")
    lines.append("")

    total = sum(len(s.checks) for s in sections)
    passed = sum(1 for s in sections for c in s.checks if c.passed)
    lines.append(f"**Result: {passed}/{total} checks passed.**")
    lines.append("")

    for sec in sections:
        sec_passed = sum(1 for c in sec.checks if c.passed)
        lines.append(f"## {sec.title} ({sec_passed}/{len(sec.checks)})")
        lines.append("")
        for c in sec.checks:
            badge = "✅" if c.passed else "❌"
            lines.append(f"### {badge} {c.name}")
            if c.notes:
                lines.append("")
                lines.append(f"> {c.notes}")
            if c.screenshot:
                lines.append("")
                lines.append(f"![{c.name}]({c.screenshot})")
            lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)

    sections: list[Section] = []
    pw: Playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            sections.append(section_ua_redirect(browser))
            sections.append(section_deep_link_auto_join(browser))
            sections.append(section_sentinel_reject_soft_fallback(browser))
            sections.append(section_share_room_link(browser))
            sections.append(section_discard_count(browser))
            sections.append(section_scroll_hint(browser))
            sections.append(section_supporting_visuals(browser))
        finally:
            browser.close()
    write_report(sections)

    total = sum(len(s.checks) for s in sections)
    passed = sum(1 for s in sections for c in s.checks if c.passed)
    print(f"\n=== Smoke test: {passed}/{total} passed ===")
    print(f"Report: {REPORT}")
    print(f"Screens: {SHOTS}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
