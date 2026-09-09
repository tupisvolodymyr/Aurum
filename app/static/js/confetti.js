(() => {
  "use strict";

  // PixiJS-powered confetti burst, used by slots.js / wheel.js to celebrate
  // wins. Degrades to a silent no-op if the vendor bundle failed to load —
  // a decorative effect must never be able to break the actual game flow.
  if (typeof PIXI === "undefined") return;

  // Bright, varied palette — deliberately not limited to the site's
  // gold/black brand colors, since confetti reads as "celebration" precisely
  // because it breaks from the normal palette.
  const COLORS = [0xffd700, 0xff4d6d, 0x4dd0e1, 0x9b5de5, 0x00f5a0, 0xff8c42, 0xffffff, 0x5b8cff];

  let app = null;
  const particles = [];

  function ensureApp() {
    if (app) return app;

    const canvas = document.createElement("canvas");
    canvas.id = "confetti-canvas";
    document.body.appendChild(canvas);

    app = new PIXI.Application({
      view: canvas,
      resizeTo: window,
      backgroundAlpha: 0,
      antialias: true,
    });

    app.ticker.add((delta) => tick(delta));
    return app;
  }

  function makeParticle(x, y) {
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    const g = new PIXI.Graphics();
    g.beginFill(color);
    if (Math.random() < 0.5) {
      g.drawRect(-4, -6, 8, 12); // ribbon-shaped piece
    } else {
      g.drawCircle(0, 0, 4.5); // round piece
    }
    g.endFill();
    g.x = x;
    g.y = y;
    g.rotation = Math.random() * Math.PI * 2;

    return {
      sprite: g,
      vx: (Math.random() - 0.5) * 9,
      vy: -(Math.random() * 11 + 7),
      gravity: 0.3 + Math.random() * 0.15,
      rotationSpeed: (Math.random() - 0.5) * 0.35,
      wobble: Math.random() * Math.PI * 2,
      wobbleSpeed: 0.06 + Math.random() * 0.06,
      life: 0,
      maxLife: 85 + Math.random() * 55,
    };
  }

  function tick(delta) {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.vy += p.gravity * delta;
      p.wobble += p.wobbleSpeed * delta;
      p.sprite.x += (p.vx + Math.sin(p.wobble) * 1.6) * delta;
      p.sprite.y += p.vy * delta;
      p.sprite.rotation += p.rotationSpeed * delta;
      p.life += delta;

      const fadeStart = p.maxLife * 0.7;
      if (p.life > fadeStart) {
        p.sprite.alpha = Math.max(0, 1 - (p.life - fadeStart) / (p.maxLife - fadeStart));
      }

      if (p.life >= p.maxLife || p.sprite.y > window.innerHeight + 40) {
        app.stage.removeChild(p.sprite);
        p.sprite.destroy();
        particles.splice(i, 1);
      }
    }
  }

  // options: { x, y, count, spread } — x/y default to viewport center,
  // spread controls how wide the burst fans out horizontally.
  function confetti(options = {}) {
    const a = ensureApp();
    const count = options.count ?? 120;
    const originX = options.x ?? window.innerWidth / 2;
    const originY = options.y ?? window.innerHeight * 0.35;
    const spread = options.spread ?? window.innerWidth * 0.4;

    for (let i = 0; i < count; i++) {
      const x = originX + (Math.random() - 0.5) * spread;
      const y = originY + (Math.random() - 0.5) * 30;
      const particle = makeParticle(x, y);
      a.stage.addChild(particle.sprite);
      particles.push(particle);
    }
  }

  // Merge into the shared AURUM namespace rather than overwrite it — this
  // script can load before or after app.js depending on page, and both
  // sides guard the same way so load order never matters.
  window.AURUM = window.AURUM || {};
  window.AURUM.confetti = confetti;
})();
