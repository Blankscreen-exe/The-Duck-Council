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

  const IMPACT_MS = 170; // when, inside the 480ms slam, the notice reads as landing
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
    const isFinding = notice.classList.contains("finding");
    window.setTimeout(() => {
      hit(isFinding ? 0.72 : undefined); // the finding sounds lower: the gavel
      const board = notice.closest(".bench");
      if (board && !isFinding) jolt(board);
    }, IMPACT_MS);
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

  // Ctrl+Enter (Cmd+Enter on a Mac) files the case from either field.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
    const form = event.target.closest?.("form[data-filing]");
    if (!form) return;
    event.preventDefault();
    form.requestSubmit();
  });
})();
