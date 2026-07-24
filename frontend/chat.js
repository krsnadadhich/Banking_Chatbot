const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");

let sessionId = localStorage.getItem("session_id");

function addMessage(text, sender) {
  const el = document.createElement("div");
  el.className = `message ${sender}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function sendMessage(message) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  const data = await response.json();

  if (data.session_id) {
    sessionId = data.session_id;
    localStorage.setItem("session_id", sessionId);
  }

  addMessage(data.reply, "bot");
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;

  addMessage(message, "user");
  inputEl.value = "";
  sendMessage(message);
});

addMessage("Hi! I'm your banking assistant. Ask me about your balance, transactions, cards, loans, interest rates, or branches.", "bot");
