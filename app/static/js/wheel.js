(() => {
  "use strict";

  const form = document.getElementById("wheel-form");
  if (!form) return; // not on the wheel page

  const spinButton = document.getElementById("wheel-spin-button");
  const betInput = document.getElementById("bet");
  const messageEl = document.getElementById("wheel-message");
  const stageEl = document.getElementById("wheel-stage");
  const discEl = document.getElementById("wheel-disc");
  const pointerMountEl = document.getElementById("wheel-pointer-mount");
  const chosenInput = document.getElementById("chosen-multiplier");
  const pickerButtons = Array.from(document.querySelectorAll(".multiplier-choice"));

  // ---------------------------------------------------------------------
  // Force-square guarantee — CSS already sizes #wheel-stage with
  // `aspect-ratio: 1/1`, which should be sufficient on its own, but a
  // player reported the disc still reading as non-circular after that was
  // in place. Rather than keep guessing which browser/zoom/OS combination
  // is computing `aspect-ratio` differently, this removes the dependency
  // on it entirely for the one property that matters most: every time the
  // stage's rendered width changes (on load, and on every resize — the
  // site is desktop-only with no breakpoints, but the *window* can still
  // be resized), read that width in real pixels and set the height to
  // match it exactly via inline style. Inline style wins the cascade over
  // the stylesheet's aspect-ratio, so this is a hard guarantee independent
  // of aspect-ratio support/quirks, not just a backup.
  // ---------------------------------------------------------------------
  function forceSquareStage() {
    if (!stageEl) return;
    const width = stageEl.getBoundingClientRect().width;
    if (width > 0) stageEl.style.height = `${width}px`;
  }
  forceSquareStage();
  window.addEventListener("resize", forceSquareStage);

  // ---------------------------------------------------------------------
  // Configuration — every tunable constant lives here so the wheel can be
  // rebalanced or retimed later without hunting through the file.
  // ---------------------------------------------------------------------
  const CONFIG = {
    BIG_WIN_MULTIPLIER: 20, // x20 and above get the celebration toast + bigger confetti burst
    SPIN_DURATION_MS: 7000, // total spin time (spec target: 4000-7000ms)
    EXTRA_SPINS_MIN: 5, // minimum full rotations before landing, for drama
    EXTRA_SPINS_RANGE: 2, // + a random 0..N-1 more full rotations
    PEG_COUNT: 24, // must match the <circle class="peg"> count in wheel_machine.html
    // Softened from the original 140ms/20deg/8deg/0.1 set — those read as a
    // sharp, jarring twitch (fast snap + hard spring overshoot) rather than
    // a smooth mechanical vibration. Longer duration + smaller angle/scale
    // + gentler overshoot keeps the "the pointer is physically reacting to
    // each peg" feeling without the jolt.
    POINTER_IMPACT_DURATION_MS: 190,
    POINTER_IMPACT_ANGLE_DEG: 13, // how far the pointer kicks back on impact
    POINTER_OVERSHOOT_ANGLE_DEG: 4, // spring overshoot past neutral before settling
    POINTER_IMPACT_TRANSLATE_PX: 3.5, // small physical "push" alongside the rotation
    POINTER_IMPACT_SCALE: 0.06, // extra scale-punch at peak impact (1 ± this)
  };

  // Must match app/games/wheel.py's SEGMENTS exactly — same order, same
  // angle boundaries (angle 0 = top, clockwise). Colors live entirely in
  // the SVG gradients in wheel_machine.html (one gradient per multiplier),
  // not duplicated here.
  const SEGMENTS = [
    { multiplier: 100, start: 0, end: 3 },
    { multiplier: 50, start: 3, end: 9 },
    { multiplier: 20, start: 9, end: 26 },
    { multiplier: 10, start: 26, end: 60 },
    { multiplier: 5, start: 60, end: 94 },
    { multiplier: 5, start: 94, end: 128 },
    { multiplier: 2, start: 128, end: 347 },
    { multiplier: 25, start: 347, end: 360 },
  ];

  const PEG_SPACING_DEG = 360 / CONFIG.PEG_COUNT;

  // ---------------------------------------------------------------------
  // Winning-sector angle
  // ---------------------------------------------------------------------
  // Set by angleForMultiplier each spin — the SEGMENTS index actually
  // targeted (there are two x5 wedges, picked at random), so the win
  // effect can highlight the *exact* sector the wheel lands on rather
  // than every sector sharing that multiplier. SEGMENTS' order matches
  // the <path class="sector" data-index="N"> elements 1:1.
  let lastSegmentIndex = -1;

  function angleForMultiplier(multiplier) {
    // A multiplier can land on more than one segment (x5 appears twice) —
    // pick one of its wedges at random each spin.
    const candidateIndexes = SEGMENTS.reduce((acc, s, i) => {
      if (s.multiplier === multiplier) acc.push(i);
      return acc;
    }, []);
    const segmentIndex = candidateIndexes[Math.floor(Math.random() * candidateIndexes.length)];
    lastSegmentIndex = segmentIndex;
    const segment = SEGMENTS[segmentIndex];
    const mid = (segment.start + segment.end) / 2;
    const halfWidth = (segment.end - segment.start) / 2;
    const margin = halfWidth * 0.2; // stay clear of the divider lines
    const usable = Math.max(halfWidth - margin, 0);
    return mid + (Math.random() * 2 - 1) * usable;
  }

  // ---------------------------------------------------------------------
  // Win / loss embellishments
  // ---------------------------------------------------------------------
  function highlightWinningSector() {
    document.querySelectorAll(".sector.is-winner").forEach((el) => el.classList.remove("is-winner"));
    if (lastSegmentIndex < 0) return;
    const el = document.querySelector(`.sector[data-index="${lastSegmentIndex}"]`);
    el?.classList.add("is-winner");
  }

  function clearWinningSector() {
    document.querySelectorAll(".sector.is-winner").forEach((el) => el.classList.remove("is-winner"));
  }

  // Small burst of golden sparkle/star particles from the wheel's hub,
  // layered on top of the confetti burst — cheap DOM+CSS animation (no
  // canvas), auto-removed once each sparkle's animation finishes so this
  // never accumulates nodes across repeated spins.
  function spawnSparkles(count) {
    if (!stageEl) return;
    for (let i = 0; i < count; i++) {
      const sparkle = document.createElement("span");
      sparkle.className = "wheel-sparkle";
      const angle = Math.random() * 360;
      const distance = 38 + Math.random() * 46; // % of stage radius
      const size = 4 + Math.random() * 6;
      sparkle.style.setProperty("--sparkle-angle", `${angle}deg`);
      sparkle.style.setProperty("--sparkle-distance", `${distance}%`);
      sparkle.style.width = `${size}px`;
      sparkle.style.height = `${size}px`;
      sparkle.style.animationDelay = `${Math.random() * 250}ms`;
      stageEl.appendChild(sparkle);
      sparkle.addEventListener("animationend", () => sparkle.remove(), { once: true });
    }
  }

  // ---------------------------------------------------------------------
  // Spin motion profile: quick spin-up, sustained cruise, long progressive
  // deceleration — a real mechanical wheel's velocity curve, not a single
  // easing function. Returns fraction-of-total-rotation for a given
  // fraction-of-total-time (both in [0, 1]).
  // ---------------------------------------------------------------------
  // Three phases (quick spin-up, sustained cruise, long progressive
  // slowdown) sharing ONE continuous velocity curve — not just three
  // functions glued together at matching *positions*. The original version
  // matched position at each phase boundary but not velocity: cruise ran
  // at a constant speed, and the moment the decel phase (easeOutQuint)
  // took over, its own velocity at its very start was ~4x the cruise
  // speed — a real, measurable jump, not just a perception issue, and
  // exactly what read as a jerk/jolt right as the wheel was supposed to
  // start slowing down. The fix: derive the accel distance AND the decel
  // curve's shape FROM the cruise velocity, so position *and* velocity
  // both stay continuous at both phase boundaries (a proper C1-continuous
  // curve) — nothing to visually "snap" anywhere along the whole spin.
  const ACCEL_END_T = 0.1; // time fraction where the fast spin-up ends
  const CRUISE_END_T = 0.55; // time fraction where the high-speed cruise ends
  const CRUISE_VELOCITY = 1.2; // progress-fraction per time-fraction during cruise
  // Accel distance is *derived*, not chosen: a quadratic ease-in
  // (local^2) has velocity 2*D/t1 at its end — setting D this way is the
  // only value that makes that end velocity land exactly on
  // CRUISE_VELOCITY, so accel flows into cruise with zero velocity jump.
  const ACCEL_DIST = (CRUISE_VELOCITY * ACCEL_END_T) / 2;
  const CRUISE_DIST = CRUISE_VELOCITY * (CRUISE_END_T - ACCEL_END_T);
  const DECEL_DIST = 1 - ACCEL_DIST - CRUISE_DIST;
  const DECEL_DURATION = 1 - CRUISE_END_T;
  // Normalized starting slope the decel cubic must have (in its own local
  // 0..1 parametrization) so its velocity at local=0 also equals
  // CRUISE_VELOCITY — the cruise->decel half of the same continuity fix.
  const DECEL_K = (CRUISE_VELOCITY * DECEL_DURATION) / DECEL_DIST;

  function spinProgress(t) {
    if (t <= ACCEL_END_T) {
      const local = t / ACCEL_END_T;
      return ACCEL_DIST * (local * local); // ease-in, ends at velocity = CRUISE_VELOCITY
    }
    if (t <= CRUISE_END_T) {
      const local = (t - ACCEL_END_T) / (CRUISE_END_T - ACCEL_END_T);
      return ACCEL_DIST + CRUISE_DIST * local; // constant velocity = CRUISE_VELOCITY
    }
    // Cubic Hermite curve on local ∈ [0, 1] with f(0)=0, f(1)=1,
    // f'(0)=DECEL_K (matches incoming cruise velocity), f'(1)=0 (eases
    // all the way to a true stop, no lingering creep at the very end).
    const local = (t - CRUISE_END_T) / DECEL_DURATION;
    const k = DECEL_K;
    const eased = k * local + (3 - 2 * k) * local * local + (k - 2) * local * local * local;
    return ACCEL_DIST + CRUISE_DIST + DECEL_DIST * eased;
  }

  // ---------------------------------------------------------------------
  // Pointer physics — a small spring-like "click" every time a peg passes
  // underneath the fixed pointer. Cancels and restarts on every new impact
  // so rapid peg-crossings during the fast cruise phase don't queue up and
  // lag behind the actual wheel position.
  // ---------------------------------------------------------------------
  let pointerAnimation = null;

  function triggerPointerImpact(intensity) {
    if (!pointerMountEl) return;
    if (pointerAnimation) pointerAnimation.cancel();

    const impactAngle = -(CONFIG.POINTER_IMPACT_ANGLE_DEG * intensity);
    const overshootAngle = CONFIG.POINTER_OVERSHOOT_ANGLE_DEG * intensity;
    const pushY = CONFIG.POINTER_IMPACT_TRANSLATE_PX * intensity;
    const punchScale = 1 + CONFIG.POINTER_IMPACT_SCALE * intensity;
    const settleScale = 1 - CONFIG.POINTER_IMPACT_SCALE * 0.3 * intensity;

    // Every keyframe re-includes translateX(-50%) — that's the pointer's
    // fixed horizontal centering (see .wheel-pointer-mount in style.css);
    // WAAPI replaces the whole transform each frame, so it has to be
    // repeated here rather than left to the stylesheet. The little
    // scale punch/rebound on top of the rotation+push is what sells the
    // "physically struck" feeling instead of reading as a plain wiggle.
    pointerAnimation = pointerMountEl.animate(
      [
        { transform: "translateX(-50%) rotate(0deg) translateY(0px) scale(1)", offset: 0 },
        {
          transform: `translateX(-50%) rotate(${impactAngle}deg) translateY(${pushY}px) scale(${punchScale})`,
          offset: 0.28,
        },
        {
          transform: `translateX(-50%) rotate(${overshootAngle}deg) translateY(-${pushY * 0.4}px) scale(${settleScale})`,
          offset: 0.62,
        },
        { transform: "translateX(-50%) rotate(0deg) translateY(0px) scale(1)", offset: 1 },
      ],
      {
        duration: CONFIG.POINTER_IMPACT_DURATION_MS,
        easing: "cubic-bezier(0.33, 1.15, 0.5, 1)", // gentle spring overshoot, no hard snap
      }
    );
  }

  let lastPegIndex = 0;

  function checkPegCrossing(currentRotationDeg, spinT) {
    const pegIndex = Math.floor(currentRotationDeg / PEG_SPACING_DEG);
    if (pegIndex === lastPegIndex) return;
    lastPegIndex = pegIndex;
    // Impacts read as more noticeable as the wheel slows down, matching
    // how a real peg strike would feel more distinct at low speed. Starts
    // softer than before (0.4 vs the old 0.7 floor) — during the fast
    // cruise phase, pegs cross in rapid succession, and starting each of
    // those dozens of impacts at high intensity is what made the spin
    // read as a constant jittery buzz rather than smooth motion.
    const intensity = 0.4 + 0.6 * spinT;
    triggerPointerImpact(intensity);
    if (spinT > 0.75) spawnSparkles(1); // tiny spark per late-spin peg strike
  }

  // ---------------------------------------------------------------------
  // Multiplier picker
  // ---------------------------------------------------------------------
  pickerButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      pickerButtons.forEach((b) => b.classList.remove("is-selected"));
      btn.classList.add("is-selected");
      chosenInput.value = btn.dataset.multiplier;
    });
  });

  // ---------------------------------------------------------------------
  // Spin
  // ---------------------------------------------------------------------
  let currentRotation = 0; // degrees, unwrapped (keeps accumulating across spins)

  function spinWheelTo(landedMultiplier) {
    return new Promise((resolve) => {
      const targetAngle = angleForMultiplier(landedMultiplier);
      const desiredMod = (360 - targetAngle + 360) % 360;
      const currentMod = ((currentRotation % 360) + 360) % 360;
      let delta = desiredMod - currentMod;
      if (delta <= 0) delta += 360;

      const extraSpins = CONFIG.EXTRA_SPINS_MIN + Math.floor(Math.random() * CONFIG.EXTRA_SPINS_RANGE);
      const finalRotation = currentRotation + extraSpins * 360 + delta;
      const startRotation = currentRotation;
      currentRotation = finalRotation;
      lastPegIndex = Math.floor(startRotation / PEG_SPACING_DEG);

      const startTime = performance.now();
      let settled = false;

      // Bright, energetic look while the wheel is actually moving — the
      // light rays speed way up and glow harder, and the rim pulses. Both
      // driven purely by this one class (see .wheel-stage.is-spinning in
      // style.css) so the effect always starts/stops exactly in sync with
      // the real spin instead of being timed separately and risking drift.
      stageEl?.classList.add("is-spinning");

      function frame(now) {
        const t = Math.min((now - startTime) / CONFIG.SPIN_DURATION_MS, 1);
        const eased = spinProgress(t);
        const deg = startRotation + (finalRotation - startRotation) * eased;
        discEl.style.transform = `rotate(${deg}deg)`;
        checkPegCrossing(deg, t);
        if (t < 1) {
          requestAnimationFrame(frame);
        } else {
          settle();
        }
      }

      const settle = () => {
        // Guard against running twice: both the rAF completion and the
        // fallback timer below can each call this.
        if (settled) return;
        settled = true;
        stageEl?.classList.remove("is-spinning");
        resolve();
      };

      requestAnimationFrame(frame);

      // Safety net: browsers fully suspend rAF callbacks while the tab is
      // backgrounded — e.g. the player alt-tabs mid-spin. Without this, the
      // spin controls would stay disabled forever until they come back. A
      // plain timer fires close to on-time regardless, and always unlocks
      // the UI.
      setTimeout(settle, CONFIG.SPIN_DURATION_MS + 200);
    });
  }

  function resetMessage() {
    messageEl.textContent = "";
    messageEl.className = "wheel-message";
    stageEl?.classList.remove("is-winning", "is-losing");
    clearWinningSector();
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
    spinButton.textContent = "Spinning…";

    try {
      const resp = await fetch("/games/golden-wheel/spin", { method: "POST", body: formData });
      const data = await resp.json();

      if (!resp.ok) {
        messageEl.textContent = data.error || "Something went wrong. Please try again.";
        messageEl.classList.add("is-error");
        if (typeof data.balance === "number") window.AURUM.flashBalance(`${data.balance} ₴`);
        return;
      }

      await spinWheelTo(data.landed_multiplier);

      if (data.winnings > 0) {
        const isBigWin = data.landed_multiplier >= CONFIG.BIG_WIN_MULTIPLIER;
        messageEl.innerHTML =
          `<span class="wheel-result-kicker">Winning Result</span>` +
          `<span class="wheel-result-value">x${data.landed_multiplier}</span>` +
          `<span class="wheel-result-sub">+${data.winnings} ₴</span>`;
        messageEl.classList.add(isBigWin ? "is-big-win" : "is-win");
        stageEl?.classList.add("is-winning");
        highlightWinningSector();
        spawnSparkles(isBigWin ? 18 : 9);

        // Small burst from the wheel on any win, a bigger full-width one
        // for a big win — keeps small wins feeling alive without the
        // celebration overload a full-size burst every time would cause.
        const originY = discEl.getBoundingClientRect().top + discEl.offsetHeight / 2;
        if (isBigWin) {
          window.AURUM.showToast(`Big win! +${data.winnings} ₴`);
          window.AURUM.confetti?.({ count: 260, spread: window.innerWidth * 0.75, y: originY });
        } else {
          window.AURUM.confetti?.({ count: 70, spread: window.innerWidth * 0.28, y: originY });
        }
      } else {
        messageEl.innerHTML =
          `<span class="wheel-result-kicker">Result</span>` +
          `<span class="wheel-result-value wheel-result-value--lose">x${data.landed_multiplier}</span>` +
          `<span class="wheel-result-sub">Better luck next time</span>`;
        messageEl.classList.add("is-lose");
        stageEl?.classList.add("is-losing");
        setTimeout(() => stageEl?.classList.remove("is-losing"), 900);
      }

      window.AURUM.flashBalance(`${data.balance} ₴`);
    } catch {
      messageEl.textContent = "Couldn't connect to the server.";
      messageEl.classList.add("is-error");
    } finally {
      setControlsDisabled(false);
      spinButton.textContent = originalLabel;
    }
  });
})();
