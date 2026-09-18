// The stamp sound, the board's jolt, the mute toggle, and a keyboard shortcut (D26).
// Everything visual works without this file; it only adds sound and conveniences.
(() => {
  "use strict";

  // htmx does not swap 4xx answers by default. A 422 carries the filing form back
  // with a message and the user's text intact, so it should replace the form.
  htmx.config.responseHandling = [
    { code: "204", swap: false },
    { code: "[23]..", swap: true },
    { code: "422", swap: true },
    { code: "[45]..", swap: false, error: true },
  ];

  // A backstop for when no animation runs to its end (a background tab, say):
  // a little longer than the slam (480ms) and the finding's fade (600ms).
  const LANDED_MS = 800;
  const MUTE_KEY = "duck-council:muted";
  const stamp = new Audio("/static/sounds/stamp.mp3");
  stamp.preload = "auto";

  // Storage can be missing or throw (private windows, blocked site data).
  const remember = {
    get(key) { try { return window.localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { window.localStorage.setItem(key, value); } catch { /* ignore */ } },
  };
  let muted = remember.get(MUTE_KEY) === "1";

  // One clone per hit so overlapping stamps don't cut each other off, detuned a
  // little so thirteen of them don't sound mechanical. Sound never gates content:
  // if the browser refuses to play, the verdict has landed regardless.
  function hit(rate) {
    if (muted) return;
    try {
      const sound = stamp.cloneNode();
      sound.playbackRate = rate ?? 0.94 + Math.random() * 0.12;
      sound.volume = rate ? 1 : 0.85;
      sound.play().catch(() => {});
    } catch { /* no audio support */ }
  }

  function jolt(board) {
    board.classList.remove("jolt");
    void board.offsetWidth; // restart the animation
    board.classList.add("jolt");
  }

  function land(notice) {
    if (notice.dataset.landed) return;
    notice.dataset.landed = "1";
    stopLoader();
    const isFinding = notice.classList.contains("finding");
    // The sound comes once the notice is fully on the board (owner's call), not
    // part-way through the slam. Whichever comes first, the end of its own
    // animation or the backstop, and never both.
    let done = false;
    const thud = () => {
      if (done) return;
      done = true;
      hit(isFinding ? 0.72 : undefined); // the finding sounds lower: the gavel
      const board = notice.closest(".bench");
      if (board && !isFinding) jolt(board);
    };
    notice.addEventListener("animationend", (event) => {
      if (event.target === notice) thud();
    });
    window.setTimeout(thud, LANDED_MS);
  }

  // Notices arrive over the event stream and are swapped in by htmx. Watching the
  // page for new `.stamped` elements catches them however they got there.
  new MutationObserver((changes) => {
    for (const change of changes) {
      for (const node of change.addedNodes) {
        if (!(node instanceof HTMLElement)) continue;
        if (node.matches(".stamped")) land(node);
        node.querySelectorAll?.(".stamped").forEach(land);
      }
    }
  }).observe(document.documentElement, { childList: true, subtree: true });

  function showSound(button) {
    button.setAttribute("aria-pressed", String(muted));
    button.textContent = muted ? "Sound off" : "Sound on";
  }
  document.querySelectorAll("[data-sound-toggle]").forEach(showSound);
  document.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-sound-toggle]");
    if (!button) return;
    muted = !muted;
    remember.set(MUTE_KEY, muted ? "1" : "0");
    showSound(button);
  });

  // Commissioning a duck: its monogram previews the initials as the name is typed.
  document.addEventListener("input", (event) => {
    if (!event.target.matches?.("[data-monogram-from]")) return;
    const initials = event.target.value.split(/\s+/).filter((word) => /^[\p{L}\p{N}]/u.test(word))
      .slice(0, 2).map((word) => word[0].toUpperCase()).join("");
    document.querySelectorAll("[data-monogram]").forEach((mark) => { mark.textContent = initials || "?"; });
  });

  // ── The loading card while the ducks deliberate (D42) ────────────────────────
  // The server renders the card with every line it may show. We shuffle them, change
  // one a second, and fade the card once the first notice lands, but never before it
  // has been up for a moment, or a fast provider would make it flicker.
  const LINE_MS = 1000;
  const MIN_SHOWN_MS = 1000;
  let loader = null; // { el, timer, shownAt }

  function shuffled(lines) {
    const copy = [...lines];
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function startLoader(el) {
    if (loader?.el === el) return;
    stopLoader();
    let lines;
    try { lines = shuffled(JSON.parse(el.dataset.lines || "[]")); } catch { lines = []; }
    const shown = el.querySelector("[data-loader-line]");
    let next = 0;
    const timer = window.setInterval(() => {
      if (!shown || lines.length < 2) return;
      next = (next + 1) % lines.length;
      shown.classList.add("swapping");
      window.setTimeout(() => {
        shown.textContent = lines[next];
        shown.classList.remove("swapping");
      }, 200);
    }, LINE_MS);
    if (shown && lines.length) shown.textContent = lines[0];
    loader = { el, timer, shownAt: performance.now() };
  }

  function stopLoader() {
    if (!loader) return;
    const { el, timer, shownAt } = loader;
    loader = null;
    const wait = Math.max(0, MIN_SHOWN_MS - (performance.now() - shownAt));
    window.setTimeout(() => {
      window.clearInterval(timer);
      el.classList.add("gone");
      window.setTimeout(() => el.remove(), still() ? 0 : 450);
    }, wait);
  }

  // A hearing's board arrives by htmx swap; its loading card comes with it.
  new MutationObserver(() => {
    const el = document.querySelector("[data-loader]:not(.gone)");
    if (el && loader?.el !== el) startLoader(el);
  }).observe(document.body, { childList: true, subtree: true });
  const onLoad = document.querySelector("[data-loader]");
  if (onLoad) startLoader(onLoad);

  // ── Picking a notice up off the board (D40) ─────────────────────────────────
  // Every notice can be picked up: a copy lifts off the board into a dialog, full
  // size and unclipped. The motion is FLIP: measure the notice on the board (First)
  // and the copy in the middle of the screen (Last), transform the copy to sit on the
  // original (Invert), then animate the transform away (Play).
  const reader = document.getElementById("reader");
  const still = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let lifted = null; // { card, copy, button } while a notice is off the board

  function travel(from, to) {
    // The transform that makes a box at `to` look as if it were at `from`.
    const dx = from.left - to.left;
    const dy = from.top - to.top;
    return `translate(${dx}px, ${dy}px) scale(${from.width / to.width}, ${from.height / to.height})`;
  }

  function copyOf(card) {
    const copy = card.cloneNode(true);
    copy.removeAttribute("id");
    copy.querySelectorAll("[id]").forEach((part) => part.removeAttribute("id"));
    // Not `stamped`: the copy must not slam in, or ring the stamp again.
    copy.classList.remove("stamped", "pending");
    copy.classList.add("reader-card");
    delete copy.dataset.landed;
    copy.querySelectorAll("[data-reader-omit], [data-pick-up]").forEach((part) => part.remove());
    copy.querySelectorAll("[data-reader-only]").forEach((part) => { part.hidden = false; });
    const close = document.createElement("button");
    close.type = "button";
    close.className = "act reader-close";
    close.textContent = "Put it back";
    close.addEventListener("click", putBack);
    copy.append(close);
    return copy;
  }

  function liftOff(card, button) {
    if (!reader || lifted) return;
    const first = card.getBoundingClientRect();
    const copy = copyOf(card);
    reader.replaceChildren(copy);
    reader.showModal();
    const last = copy.getBoundingClientRect();
    card.classList.add("lifted"); // its spot stays empty while it is off the board
    lifted = { card, copy, button };
    if (!still()) {
      copy.animate(
        [{ transform: travel(first, last), opacity: 0.9 }, { transform: "none", opacity: 1 }],
        { duration: 380, easing: "cubic-bezier(.2, .72, .24, 1)" },
      );
    }
    copy.querySelector(".reader-close")?.focus();
  }

  async function putBack() {
    if (!lifted || lifted.leaving) return;
    lifted.leaving = true;
    const { card, copy, button } = lifted;
    reader.classList.add("closing");
    if (!still()) {
      const home = card.getBoundingClientRect(); // measured now: the page may have scrolled
      const flight = copy.animate(
        [{ transform: "none" }, { transform: travel(home, copy.getBoundingClientRect()) }],
        { duration: 300, easing: "cubic-bezier(.4, 0, .6, 1)", fill: "forwards" },
      );
      await flight.finished.catch(() => {});
    }
    reader.close();
    reader.classList.remove("closing");
    reader.replaceChildren();
    card.classList.remove("lifted");
    lifted = null;
    button?.focus();
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-pick-up]");
    if (!button) return;
    const card = button.closest(".row");
    if (card) liftOff(card, button);
  });
  if (reader) {
    // A click on the dimmed area around the notice lands on the dialog itself.
    reader.addEventListener("click", (event) => { if (event.target === reader) putBack(); });
    // Esc: animate back instead of vanishing.
    reader.addEventListener("cancel", (event) => { event.preventDefault(); putBack(); });
  }

  // Ctrl+Enter (Cmd+Enter on a Mac) files the case from either field.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
    const form = event.target.closest?.("form[data-filing]");
    if (!form) return;
    event.preventDefault();
    form.requestSubmit();
  });
})();
