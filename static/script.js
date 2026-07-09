/**
 * Climate Decision — Weather Advisor Chatbot
 * Frontend interaction: send messages, load suggestions, auto-scroll.
 */

(function () {
  "use strict";

  // ─── DOM refs ────────────────────────────────────────────
  const form = document.getElementById("chatForm");
  const input = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const messages = document.getElementById("messagesContainer");
  const spinner = document.getElementById("spinnerOverlay");
  const suggestionsContainer = document.getElementById("suggestionsContainer");
  const menuBtn = document.getElementById("menuBtn");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const statusEl = document.getElementById("statusIndicator");

  // ─── State ───────────────────────────────────────────────
  let isLoading = false;

  function getCurrentPeriod(date = new Date()) {
    return date.getHours() < 12 ? "morning" : "night";
  }

  function getGreeting(date = new Date()) {
    return getCurrentPeriod(date) === "morning" ? "Good morning" : "Good evening";
  }

  function formatTimestamp(date = new Date()) {
    const locale = navigator.language || "en-US";
    return new Intl.DateTimeFormat(locale, {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }).format(date);
  }

  // ─── Welcome message ─────────────────────────────────────
  (function injectWelcome() {
    const div = document.createElement("div");
    div.className = "welcome-msg";
    div.innerHTML = `
      <div class="welcome-icon">🌤</div>
      <h3>${getGreeting()} 👋</h3>
      <p>
        Ask anything about the next 6 months' weather forecast.
        Click a suggestion below to get started, or type your own question.
      </p>
      <p class="welcome-meta">${formatTimestamp()}</p>
    `;
    messages.appendChild(div);
  })();

  // ─── Helpers ─────────────────────────────────────────────
  function scrollToBottom() {
    requestAnimationFrame(() => {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  function setLoading(loading) {
    isLoading = loading;
    sendBtn.disabled = loading;
    input.disabled = loading;
    if (loading) {
      spinner.classList.remove("hidden");
      statusEl.textContent = "● Thinking…";
    } else {
      spinner.classList.add("hidden");
      statusEl.textContent = "● Ready";
    }
  }

  function formatMessage(text) {
    let formatted = (text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br />");

    formatted = formatted.replace(/^(?:\s*[-*]\s+)/gm, "• ");
    return formatted;
  }

  function addMessage(text, role) {
    // Remove welcome message on first real message
    const welcome = messages.querySelector(".welcome-msg");
    if (welcome) welcome.remove();

    const div = document.createElement("div");
    div.className = `message ${role}`;

    const content = document.createElement("div");
    content.className = "message-content";
    content.innerHTML = formatMessage(text);

    const timestamp = document.createElement("div");
    timestamp.className = "message-timestamp";
    timestamp.textContent = formatTimestamp(new Date());

    div.appendChild(content);
    div.appendChild(timestamp);
    messages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function addTypingIndicator() {
    const div = document.createElement("div");
    div.className = "message ai typing-indicator";
    div.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;
    messages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function showError(msg) {
    addMessage(msg, "error");
  }

  // ─── Send message ────────────────────────────────────────
  async function sendMessage(text) {
    if (isLoading || !text.trim()) return;

    addMessage(text, "user");
    input.value = "";
    setLoading(true);

    const typing = addTypingIndicator();
    const aiMessage = addMessage("", "ai");

    try {
      const resp = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      typing.remove();

      if (!resp.ok) {
        const errText = await resp.text().catch(() => "");
        showError(errText || `Server error (${resp.status})`);
        return;
      }

      if (!resp.body) {
        aiMessage.innerHTML = formatMessage("No response received.");
        return;
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let result = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        result += chunk;
        aiMessage.innerHTML = formatMessage(result);
        scrollToBottom();
      }
    } catch (err) {
      typing.remove();
      aiMessage.innerHTML = formatMessage("Network error — could not reach the server.");
    } finally {
      setLoading(false);
      input.focus();
    }
  }

  // ─── Load suggestions ────────────────────────────────────
  async function loadSuggestions() {
    suggestionsContainer.innerHTML =
      '<div class="suggestion-chip loading">Loading suggestions…</div>';

    try {
      const resp = await fetch("/suggestions");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const data = await resp.json();
      const chips = data.suggestions || [];

      suggestionsContainer.innerHTML = "";
      chips.forEach((chipText) => {
        const chip = document.createElement("div");
        chip.className = "suggestion-chip";
        chip.textContent = chipText;
        chip.addEventListener("click", () => {
          sendMessage(chipText);
        });
        suggestionsContainer.appendChild(chip);
      });
    } catch {
      suggestionsContainer.innerHTML = `
        <div class="suggestion-chip">What does the forecast look like?</div>
        <div class="suggestion-chip">Give me agricultural advice</div>
        <div class="suggestion-chip">Best months for outdoor activities?</div>
        <div class="suggestion-chip">Energy planning recommendations</div>
      `;
    }
  }

  // ─── Event handlers ──────────────────────────────────────
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(input.value);
  });

  // Allow sending with Enter key
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event("submit"));
    }
  });

  // ─── Mobile sidebar toggle ───────────────────────────────
  menuBtn.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("visible");
  });

  overlay.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("visible");
  });

  // ─── Init ────────────────────────────────────────────────
  loadSuggestions();
  input.focus();
})();
