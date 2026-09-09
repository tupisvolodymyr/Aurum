(() => {
  "use strict";

  const csrfToken = () => document.querySelector('meta[name="csrf-token"]')?.content || "";

  // ---------- Balance flash ----------
  // Visibly pulses the header balance whenever it changes (spin, deposit,
  // withdraw) — including a break-even push where the number itself
  // doesn't move, so the action still reads as "processed".
  function flashBalance(newText) {
    const el = document.getElementById("balance");
    if (!el) return;
    if (newText !== undefined) el.textContent = newText;
    el.classList.remove("is-flashing");
    void el.offsetWidth; // force reflow so the animation can restart
    el.classList.add("is-flashing");
  }

  // ---------- Toasts ----------
  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("is-visible"));
    setTimeout(() => {
      toast.classList.remove("is-visible");
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  // ---------- Auth modal ----------
  const modal = document.getElementById("auth-modal");
  const loginLink = document.getElementById("modal-login-link");
  const signupLink = document.getElementById("modal-signup-link");

  function openAuthModal(nextHref) {
    if (!modal) return;
    const next = nextHref ? `?next=${encodeURIComponent(nextHref)}` : "";
    if (loginLink) loginLink.href = `/login${next}`;
    if (signupLink) signupLink.href = `/register${next}`;
    modal.hidden = false;
    modal.classList.add("is-open");
    document.body.classList.add("modal-open");
  }

  function closeAuthModal() {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.hidden = true;
    document.body.classList.remove("modal-open");
  }

  document.getElementById("modal-close")?.addEventListener("click", closeAuthModal);
  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeAuthModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal?.classList.contains("is-open")) closeAuthModal();
  });

  // ---------- Play buttons & favorites (delegated) ----------
  document.addEventListener("click", (e) => {
    const playBtn = e.target.closest("[data-play]");
    if (playBtn) {
      const isActive = playBtn.dataset.active === "true";
      if (!isActive) {
        e.preventDefault();
        showToast("Coming soon — this game is being prepared.");
        return;
      }
      if (!window.CASINO?.isAuthenticated) {
        e.preventDefault();
        openAuthModal(playBtn.dataset.href || playBtn.getAttribute("href"));
      }
      // Otherwise let the real <a href="/games/{slug}"> navigate normally —
      // the game page itself is the colorful "arcade" presentation now,
      // not a modal/iframe layered over the lobby.
      return;
    }

    const favBtn = e.target.closest("[data-favorite]");
    if (favBtn) {
      e.preventDefault();
      if (!window.CASINO?.isAuthenticated) {
        openAuthModal("/");
        return;
      }
      toggleFavorite(favBtn);
    }
  });

  async function toggleFavorite(button) {
    const slug = button.dataset.slug;
    button.disabled = true;
    try {
      const resp = await fetch(`/games/${slug}/favorite`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken() },
      });
      if (resp.status === 401) {
        openAuthModal("/");
        return;
      }
      if (!resp.ok) throw new Error("request failed");
      const data = await resp.json();
      button.classList.toggle("is-active", data.favorited);
      showToast(data.favorited ? "Added to favorites" : "Removed from favorites");
    } catch {
      showToast("Something went wrong — please try again.", "error");
    } finally {
      button.disabled = false;
    }
  }

  // ---------- Mobile nav ----------
  const navToggle = document.getElementById("nav-toggle");
  const mainNav = document.getElementById("main-nav");
  navToggle?.addEventListener("click", () => {
    const open = mainNav.classList.toggle("is-open");
    navToggle.classList.toggle("is-open", open);
    navToggle.setAttribute("aria-expanded", String(open));
  });

  // ---------- Category filter tabs + search ----------
  const grid = document.getElementById("game-grid");
  const tabs = document.getElementById("category-tabs");
  const search = document.getElementById("game-search");
  const emptyState = document.getElementById("empty-state");
  const TABLE_GAME_CATEGORIES = new Set(["roulette", "blackjack", "poker"]);

  function cardMatchesTab(card, tab) {
    if (tab === "all") return true;
    if (tab === "new") return card.dataset.new === "true";
    if (tab === "popular") return card.dataset.popular === "true";
    if (tab === "table_games") return TABLE_GAME_CATEGORIES.has(card.dataset.category);
    return card.dataset.category === tab;
  }

  function applyFilters() {
    if (!grid) return;
    const activeTab = tabs?.querySelector(".tab.is-active")?.dataset.tab || "all";
    const query = (search?.value || "").trim().toLowerCase();
    const cards = Array.from(grid.querySelectorAll(".game-card"));

    let visibleCount = 0;
    for (const card of cards) {
      const matchesTab = cardMatchesTab(card, activeTab);
      const matchesQuery = !query || card.dataset.title.includes(query);
      const visible = matchesTab && matchesQuery;
      card.hidden = !visible;
      if (visible) visibleCount += 1;
    }

    if (emptyState) emptyState.hidden = visibleCount > 0;
  }

  function setActiveTab(tab) {
    if (!tabs) return;
    tabs.querySelectorAll(".tab").forEach((btn) => btn.classList.toggle("is-active", btn.dataset.tab === tab));
    grid?.classList.add("is-filtering");
    setTimeout(() => grid?.classList.remove("is-filtering"), 220);
    applyFilters();
  }

  tabs?.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (btn) setActiveTab(btn.dataset.tab);
  });

  let searchDebounce;
  search?.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(applyFilters, 150);
  });

  // Header nav links with data-filter jump into the lobby and pre-select a tab.
  document.querySelectorAll("#main-nav a[data-filter]").forEach((link) => {
    link.addEventListener("click", (e) => {
      const tab = link.dataset.filter;
      if (window.location.pathname === "/") {
        e.preventDefault();
        setActiveTab(tab);
        document.getElementById("lobby")?.scrollIntoView({ behavior: "smooth" });
        mainNav?.classList.remove("is-open");
      } else {
        sessionStorage.setItem("pendingFilter", tab);
      }
    });
  });

  const pendingFilter = sessionStorage.getItem("pendingFilter");
  if (pendingFilter && tabs) {
    sessionStorage.removeItem("pendingFilter");
    setActiveTab(pendingFilter);
  }

  applyFilters();

  // Small shared API surface for page-specific scripts (e.g. slots.js,
  // confetti.js) — merge rather than overwrite, since confetti.js may run
  // before or after this file depending on the page and shouldn't have its
  // window.AURUM.confetti entry clobbered (or vice versa).
  window.AURUM = Object.assign(window.AURUM || {}, { csrfToken, showToast, flashBalance, openAuthModal });
})();
