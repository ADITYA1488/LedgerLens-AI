const chatToggle = document.getElementById("chat-toggle");
const chatPanel = document.getElementById("chat-panel");
const chatClose = document.getElementById("chat-close");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

chatToggle.addEventListener("click", () => {
    chatPanel.classList.remove("chat-hidden");
    chatToggle.style.display = "none";
});

chatClose.addEventListener("click", () => {
    chatPanel.classList.add("chat-hidden");
    chatToggle.style.display = "block";
});

function addMessage(text, type) {
    const message = document.createElement("div");
    message.className = type === "user" ? "user-message" : "bot-message";
    message.textContent = text;
    chatMessages.appendChild(message);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendMessage() {
    const message = chatInput.value.trim();

    if (!message) return;

    addMessage(message, "user");
    chatInput.value = "";
    chatSend.disabled = true;

    const loading = document.createElement("div");
    loading.className = "bot-message";
    loading.textContent = "Analyzing financial data...";
    chatMessages.appendChild(loading);

    try {
        const response = await fetch("http://127.0.0.1:8001/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                entity: "LOG"
            })
        });

        const data = await response.json();
        loading.remove();

        if (!response.ok) {
            throw new Error(data.detail || "Request failed");
        }

        addMessage(data.reply, "bot");
    } catch (error) {
        loading.remove();
        addMessage("Unable to connect to LedgerLens AI. Please ensure the AI backend is running.", "bot");
        console.error(error);
    } finally {
        chatSend.disabled = false;
        chatInput.focus();
    }
}

chatSend.addEventListener("click", sendMessage);

chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") sendMessage();
});