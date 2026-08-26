(() => {
  "use strict";

  const form = document.getElementById("slot-form");
  if (!form) return; // not on the slots page

  const spinButton = document.getElementById("spin-button");
  const betInput = document.getElementById("bet");
  const messageEl = document.getElementById("slot-message");
  const reelsContainer = document.getElementById("slot-reels");
  const machineEl = document.getElementById("slot-machine");
  const windows = Array.from(reelsContainer.querySelectorAll(".reel-window"));

  // Must match the backend's Symbol enum values in app/games/slots.py —
  // only used for the decorative "spinning" blur, never the real outcome.
  const ALL_SYMBOLS = ["🍒", "🍋", "🍊", "🔔", "⭐", "💎", "7️⃣"];
  const SYMBOL_SIZE = 80; // px, must match .reel-symbol height in CSS
  const BIG_WIN_MULTIPLIER = 25; // Bell tier and above gets the celebration

  // Staggered per-reel timing: first reel lands soonest, last reel lasts
  // longest — the classic "clunk, clunk, clunk" build-up.
  const REEL_TIMING = [
    { delay: 0, duration: 900 },
    { delay: 150, duration: 1050 },
    { delay: 300, duration: 1200 },
  ];

  function buildStrip(finalSymbol) {
    const strip = document.createElement("div");
    strip.className = "reel-strip";

    const spinCount = 18 + Math.floor(Math.random() * 6);
    for (let i = 0; i < spinCount; i++) {
      const el = document.createElement("div");
      el.className = "reel-symbol";
      el.textContent = ALL_SYMBOLS[Math.floor(Math.random() * ALL_SYMBOLS.length)];
      strip.appendChild(el);
    }

    const finalEl = document.createElement("div");
    finalEl.className = "reel-symbol";
    finalEl.textContent = finalSymbol;
    strip.appendChild(finalEl);

    return strip;
  }

  function spinReel(windowEl, finalSymbol, delay, duration) {
    return new Promise((resolve) => {
      setTimeout(() => {
        windowEl.innerHTML = "";
        const strip = buildStrip(finalSymbol);
        windowEl.appendChild(strip);

        const finalOffset = -(strip.children.length - 1) * SYMBOL_SIZE;
        const anim = strip.animate(
          [
            { transform: "translateY(0)", filter: "blur(0px)", offset: 0 },
            { transform: `translateY(${finalOffset * 0.55}px)`, filter: "blur(5px)", offset: 0.45 },
            { transform: `translateY(${finalOffset * 0.9}px)`, filter: "blur(2px)", offset: 0.82 },
            { transform: `translateY(${finalOffset}px)`, filter: "blur(0px)", offset: 1 },
          ],
          { duration, easing: "cubic-bezier(0.12, 0.8, 0.25, 1)", fill: "forwards" }
        );

        let settled = false;
        const settle = () => {
          // Guard against running twice: both anim.finished and the
          // fallback timer below can each call this.
          if (settled) return;
          settled = true;
          windowEl.classList.add("is-landing");
          setTimeout(() => windowEl.classList.remove("is-landing"), 300);
          resolve();
        };
        anim.finished.then(settle).catch(settle);

        // Safety net: browsers fully suspend the Web Animations timeline
        // (and therefore anim.finished) while the tab is backgrounded — e.g.
        // the player alt-tabs mid-spin. Without this, the spin controls
        // would stay disabled forever until they come back. A plain timer
        // isn't tied to the animation timeline, so it fires close to
        // on-time regardless, and always unlocks the UI.
        setTimeout(settle, duration + 200);
      }, delay);
    });
  }

  function playSpinAnimation(reels) {
    return Promise.all(windows.map((el, i) => spinReel(el, reels[i], REEL_TIMING[i].delay, REEL_TIMING[i].duration)));
  }

  function resetMessage() {
    messageEl.textContent = "";
    messageEl.className = "slot-message";
    reelsContainer.classList.remove("is-win");
    machineEl.classList.remove("is-celebrating");
  }

  function setControlsDisabled(disabled) {
    spinButton.disabled = disabled;
    betInput.disabled = disabled;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (spinButton.disabled) return;

    // Snapshot the form data before disabling anything — disabled form
    // fields are excluded from FormData per the HTML spec, so building this
    // after setControlsDisabled(true) would silently drop "bet".
    const formData = new FormData(form);

    setControlsDisabled(true);
    resetMessage();
    const originalLabel = spinButton.textContent;
    spinButton.textContent = "Крутиться…";

    try {
      const resp = await fetch("/games/slots/spin", { method: "POST", body: formData });
      const data = await resp.json();

      if (!resp.ok) {
        messageEl.textContent = data.error || "Щось пішло не так. Спробуй ще раз.";
        messageEl.classList.add("is-error");
        if (typeof data.balance === "number") window.AURUM.flashBalance(`${data.balance} ₴`);
        return;
      }

      await playSpinAnimation(data.reels);

      if (data.winnings > 0) {
        const isBigWin = data.multiplier >= BIG_WIN_MULTIPLIER;
        reelsContainer.classList.add("is-win");
        messageEl.textContent = `Виграш: +${data.winnings} ₴ (x${data.multiplier})`;
        messageEl.classList.add(isBigWin ? "is-big-win" : "is-win");
        if (isBigWin) {
          machineEl.classList.add("is-celebrating");
          window.AURUM.showToast(`Великий виграш! +${data.winnings} ₴`);
        }
      } else {
        messageEl.textContent = "Не пощастило. Спробуй ще раз!";
        messageEl.classList.add("is-lose");
      }

      window.AURUM.flashBalance(`${data.balance} ₴`);
    } catch {
      messageEl.textContent = "Не вдалося з'єднатися з сервером.";
      messageEl.classList.add("is-error");
    } finally {
      setControlsDisabled(false);
      spinButton.textContent = originalLabel;
    }
  });
})();
