const FILL_MS = 1100;
const HOLD_MS = 200;
const FADE_MS = 200;

// Icons are decorative: all controls retain their text or accessible label.
window.addEventListener("load", () => {
  if (window.lucide) window.lucide.createIcons();
});

document.querySelectorAll("[data-password]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.getElementById(button.dataset.password);
    const showing = input.type === "password";
    input.type = showing ? "text" : "password";
    button.setAttribute("aria-pressed", String(showing));
    button.setAttribute("aria-label", showing ? button.dataset.hide : button.dataset.show);
    if (document.body.classList.contains("login-page")) {
      button.innerHTML = `<i data-lucide="${showing ? "eye-off" : "eye"}" aria-hidden="true"></i>`;
      if (window.lucide) window.lucide.createIcons();
    }
  });
});

// Login-only feedback. The form still submits to Django.
const loginForm = document.getElementById("login-form");
if (loginForm) {
  const seniorID = document.getElementById("senior-id");
  const idError = document.getElementById("id-error");
  const submit = loginForm.querySelector('[type="submit"]');
  const submitLabel = submit.querySelector("[data-submit-label]");
  const spinner = submit.querySelector(".login-spinner");

  seniorID.addEventListener("invalid", () => {
    idError.hidden = false;
    seniorID.setAttribute("aria-invalid", "true");
    seniorID.setCustomValidity("Limang numero ang kailangan.");
  });
  seniorID.addEventListener("input", () => {
    seniorID.setCustomValidity("");
    idError.hidden = /^[0-9]{5}$/.test(seniorID.value);
    seniorID.setAttribute("aria-invalid", String(!idError.hidden));
  });
  const password = document.getElementById("password");
  password.addEventListener("invalid", () => password.setCustomValidity("Ilagay ang inyong password."));
  password.addEventListener("input", () => {
    password.setCustomValidity("");
    password.removeAttribute("aria-invalid");
  });

  loginForm.addEventListener("submit", () => {
    submit.disabled = true;
    submit.setAttribute("aria-busy", "true");
    submitLabel.textContent = "Sandali lang po...";
    spinner.hidden = false;
  });
  window.addEventListener("pageshow", () => {
    submit.disabled = false;
    submit.removeAttribute("aria-busy");
    submitLabel.textContent = "PUMASOK";
    spinner.hidden = true;
  });
  const privacy = document.getElementById("login-privacy");
  document.getElementById("open-privacy").addEventListener("click", () => privacy.showModal());
  const help = document.getElementById("login-help");
  document.getElementById("open-login-help").addEventListener("click", () => help.showModal());
  document.getElementById("help-privacy").addEventListener("click", () => {
    help.close();
    privacy.showModal();
  });

  // Use the visible area when a phone keyboard covers part of the screen.
  if (window.visualViewport) {
    let fullHeight = window.innerHeight;
    const fitKeyboard = () => {
      if (document.activeElement.tagName !== "INPUT") fullHeight = window.innerHeight;
      const height = window.visualViewport.height;
      document.body.classList.toggle("keyboard-open", fullHeight - height > 120);
      document.body.style.setProperty("--login-visible-height", `${height}px`);
    };
    window.visualViewport.addEventListener("resize", fitKeyboard);
    window.addEventListener("resize", fitKeyboard);
  }
}

// The server owns the expiry time. Polling never renews an idle session.
if (document.body.dataset.session === "true") {
  const dialog = document.getElementById("idle-dialog");
  const countdown = document.getElementById("idle-countdown");
  const stayButton = document.getElementById("stay-signed-in");
  const csrf = document.querySelector('[name="csrfmiddlewaretoken"]').value;
  let deadline = Date.now() + Number(document.body.dataset.idle) * 1000;
  let lastTouch = 0;
  let busy = false;

  async function sessionRequest(renew = false) {
    if (busy) return;
    busy = true;
    try {
      const response = await fetch(renew ? "/session/touch/" : "/session/status/", {
        method: renew ? "POST" : "GET",
        headers: renew ? { "X-CSRFToken": csrf } : {},
        credentials: "same-origin",
        cache: "no-store",
      });
      if (response.status === 401 || response.status === 403) {
        window.location.replace("/login/?expired=1");
        return;
      }
      if (!response.ok) return;
      const data = await response.json();
      deadline = Date.now() + data.remaining * 1000;
      if (renew) {
        lastTouch = Date.now();
        if (dialog.open) dialog.close();
      }
    } catch {
      // A connection problem must not silently extend the countdown.
    } finally {
      busy = false;
    }
  }

  ["pointerdown", "keydown", "scroll"].forEach((eventName) => {
    document.addEventListener(eventName, (event) => {
      if (event.isTrusted && !dialog.open && Date.now() - lastTouch > 15000) sessionRequest(true);
    }, { passive: true });
  });
  stayButton.addEventListener("click", () => sessionRequest(true));
  dialog.addEventListener("cancel", (event) => event.preventDefault());
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) sessionRequest();
  });
  setInterval(() => sessionRequest(), 15000);
  setInterval(() => {
    const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    countdown.textContent = remaining;
    if (remaining <= 60 && !dialog.open) dialog.showModal();
    if (remaining === 0) sessionRequest();
  }, 1000);
  sessionRequest();
}

const loadingOverlay = document.getElementById("login-loading");
if (loadingOverlay) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fillDuration = reducedMotion ? 400 : FILL_MS;
  const holdDuration = reducedMotion ? 200 : HOLD_MS;
  loadingOverlay.style.setProperty("--loading-fill-ms", `${fillDuration}ms`);
  loadingOverlay.style.setProperty("--loading-fade-ms", `${FADE_MS}ms`);
  requestAnimationFrame(() => {
    loadingOverlay.classList.add("is-ready");
    window.setTimeout(() => loadingOverlay.classList.add("is-fading"), fillDuration + holdDuration);
    window.setTimeout(() => window.location.replace(loadingOverlay.dataset.destination), fillDuration + holdDuration + FADE_MS);
  });
}
