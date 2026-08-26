(() => {
  "use strict";

  const form = document.getElementById("wheel-form");
  if (!form) return; // not on the wheel page

  const spinButton = document.getElementById("wheel-spin-button");
  const betInput = document.getElementById("bet");
  const messageEl = document.getElementById("wheel-message");
  const stageEl = document.getElementById("wheel-stage");
  const discEl = document.getElementById("wheel-disc");
  const chosenInput = document.getElementById("chosen-multiplier");
  const pickerButtons = Array.from(document.querySelectorAll(".multiplier-choice"));

  const BIG_WIN_MULTIPLIER = 20; // x20 and x40 get the celebration

  // Must match app/games/wheel.py SEGMENTS exactly (angle 0 = top, clockwise).
  const SEGMENTS = [
    { multiplier: 2, start: 0, end: 150 },
    { multiplier: 3, start: 150, end: 250 },
    { multiplier: 5, start: 250, end: 310 },
    { multiplier: 10, start: 310, end: 340 },
    { multiplier: 20, start: 340, end: 353.3333 },
    { multiplier: 40, start: 353.3333, end: 360 },
  ];

  let currentRotation = 0;

  pickerButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      pickerButtons.forEach((b) => b.classList.remove("is-selected"));
      btn.classList.add("is-selected");
      chosenInput.value = btn.dataset.multiplier;
    });
  });

  function angleForMultiplier(multiplier) {
    const segment = SEGMENTS.find((s) => s.multiplier === multiplier);
    const mid = (segment.start + segment.end) / 2;
    const halfWidth = (segment.end - segment.start) / 2;
    const margin = halfWidth * 0.25; // stay clear of the wedge boundary lines
    const usable = Math.max(halfWidth - margin, 0);
    return mid + (Math.random() * 2 - 1) * usable;
  }

  function spinWheelTo(landedMultiplier) {
    return new Promise((resolve) => {
      const targetAngle = angleForMultiplier(landedMultiplier);
      const desiredMod = (360 - targetAngle + 360) % 360;
      const currentMod = ((currentRotation % 360) + 360) % 360;
      let delta = desiredMod - currentMod;
      if (delta <= 0) delta += 360;

      const extraSpins = 5 + Math.floor(Math.random() * 2); // 5-6 full turns for drama
      const finalRotation = currentRotation + extraSpins * 360 + delta;
      const startRotation = currentRotation;
      currentRotation = finalRotation;

      const DURATION = 3200;
      const anim = discEl.animate(
        [{ transform: `rotate(${startRotation}deg)` }, { transform: `rotate(${finalRotation}deg)` }],
        { duration: DURATION, easing: "cubic-bezier(0.13, 0.6, 0.15, 1)", fill: "forwards" }
      );

      let settled = false;
      const settle = () => {
        // Guard with ?. — a DOM/selector slip here must never keep this
        // promise from resolving, or the whole spin flow hangs forever.
        // Also guard against running twice: both anim.finished and the
        // fallback timer below can each call this.
        if (settled) return;
        settled = true;
        stageEl?.classList.add("is-landing");
        setTimeout(() => stageEl?.classList.remove("is-landing"), 250);
        resolve();
      };
      anim.finished.then(settle).catch(settle);

      // Safety net: browsers fully suspend the Web Animations timeline
      // (and therefore anim.finished) while the tab is backgrounded — e.g.
      // the player alt-tabs mid-spin. Without this, the spin controls would
      // stay disabled forever until they come back and the animation
      // catches up. A plain timer isn't tied to the animation timeline, so
      // it fires close to on-time regardless, and always unlocks the UI.
      setTimeout(settle, DURATION + 200);
    });
  }

  function resetMessage() {
    messageEl.textContent = "";
    messageEl.className = "wheel-message";
  }

  function setControlsDisabled(disabled) {
    spinButton.disabled = disabled;
    betInput.disabled = disabled;
    pickerButtons.forEach((b) => (b.disabled = disabled));
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (spinButton.disabled) return;

    // Snapshot the form data before disabling anything — disabled form
    // fields are excluded from FormData per the HTML spec.
    const formData = new FormData(form);

    setControlsDisabled(true);
    resetMessage();
    const originalLabel = spinButton.textContent;
    spinButton.textContent = "Крутиться…";

    try {
      const resp = await fetch("/games/golden-wheel/spin", { method: "POST", body: formData });
      const data = await resp.json();

      if (!resp.ok) {
        messageEl.textContent = data.error || "Щось пішло не так. Спробуй ще раз.";
        messageEl.classList.add("is-error");
        if (typeof data.balance === "number") window.AURUM.flashBalance(`${data.balance} ₴`);
        return;
      }

      await spinWheelTo(data.landed_multiplier);

      if (data.winnings > 0) {
        const isBigWin = data.landed_multiplier >= BIG_WIN_MULTIPLIER;
        messageEl.textContent = `Випало x${data.landed_multiplier}! Виграш: +${data.winnings} ₴`;
        messageEl.classList.add(isBigWin ? "is-big-win" : "is-win");
        if (isBigWin) window.AURUM.showToast(`Великий виграш! +${data.winnings} ₴`);
      } else {
        messageEl.textContent = `Випало x${data.landed_multiplier}. Не пощастило цього разу.`;
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
