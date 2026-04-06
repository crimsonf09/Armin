import { io, Socket } from "socket.io-client";
import "./style.css";

function readEnvUrl(key: "VITE_API_URL" | "VITE_SOCKET_URL", fallback: string): string {
  const v = import.meta.env[key];
  if (typeof v === "string" && v.trim() !== "") return v.trim();
  return fallback;
}

// Use absolute backend URL in production builds; in dev you can set VITE_API_URL=/api and rely on vite.config proxy.
const API_URL = readEnvUrl("VITE_API_URL", "http://localhost:8000/api");
const SOCKET_URL = readEnvUrl("VITE_SOCKET_URL", "http://localhost:8000");

type Conversation = { id: string; title: string };
type Message = { id: string; role: "user" | "assistant" | "system"; content: string; created_at: string };

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("App root not found");

let token = localStorage.getItem("token") ?? "";
let socket: Socket | null = null;
let activeConversationId = "";
let joinedConversationId = "";

app.innerHTML = `
<div class="layout">
  <aside class="sidebar">
    <h2>Chats</h2>
    <button id="newChatBtn">+ New chat</button>
    <div id="conversations"></div>
  </aside>
  <main class="main">
    <div class="auth">
      <input id="email" placeholder="email" />
      <input id="password" type="password" placeholder="password" />
      <button id="registerBtn">Register</button>
      <button id="loginBtn">Login</button>
      <span id="authState">${token ? "Signed in" : "Guest"}</span>
    </div>
    <div id="messages" class="messages"></div>
    <div class="composer">
      <input id="messageInput" placeholder="Type a message..." />
      <button id="sendBtn">Send</button>
    </div>
  </main>
</div>
`;

const conversationsEl = document.getElementById("conversations") as HTMLDivElement;
const messagesEl = document.getElementById("messages") as HTMLDivElement;

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

function connectSocket() {
  if (!token) return;
  if (socket) socket.disconnect();
  socket = io(SOCKET_URL, { auth: { token } });
  socket.on("message.created", (msg: Message) => {
    if (msg.role === "user" && msg.id) appendMessage(msg);
  });
  socket.on("agent.final", (msg: Message) => appendMessage(msg));
}

function appendMessage(msg: Message) {
  const row = document.createElement("div");
  row.className = `msg msg-${msg.role}`;
  row.textContent = `${msg.role}: ${msg.content}`;
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function selectConversation(conversationId: string) {
  activeConversationId = conversationId;
  messagesEl.innerHTML = "";
  const msgs = await api<Message[]>(`/conversations/${conversationId}/messages`);
  msgs.forEach(appendMessage);
  socket?.emit("conversation.join", { conversation_id: conversationId });
  joinedConversationId = conversationId;
}

async function loadConversations() {
  if (!token) return;
  const list = await api<Conversation[]>("/conversations");
  conversationsEl.innerHTML = "";
  list.forEach((c) => {
    const item = document.createElement("button");
    item.className = "conv";
    item.textContent = c.title;
    item.onclick = async () => selectConversation(c.id);
    conversationsEl.appendChild(item);
  });
}

async function auth(kind: "register" | "login") {
  const email = (document.getElementById("email") as HTMLInputElement).value;
  const password = (document.getElementById("password") as HTMLInputElement).value;
  const data = await api<{ access_token: string }>(`/auth/${kind}`, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  token = data.access_token;
  localStorage.setItem("token", token);
  (document.getElementById("authState") as HTMLSpanElement).textContent = "Signed in";
  connectSocket();
  await loadConversations();
}

(document.getElementById("registerBtn") as HTMLButtonElement).onclick = () => auth("register");
(document.getElementById("loginBtn") as HTMLButtonElement).onclick = () => auth("login");

(document.getElementById("newChatBtn") as HTMLButtonElement).onclick = async () => {
  const convo = await api<Conversation>("/conversations", {
    method: "POST",
    body: JSON.stringify({ title: `Chat ${new Date().toLocaleTimeString()}` }),
  });
  await loadConversations();
  await selectConversation(convo.id);
};

(document.getElementById("sendBtn") as HTMLButtonElement).onclick = async () => {
  if (!activeConversationId) return;
  const input = document.getElementById("messageInput") as HTMLInputElement;
  const content = input.value.trim();
  if (!content) return;
  input.value = "";
  if (joinedConversationId !== activeConversationId) {
    socket?.emit("conversation.join", { conversation_id: activeConversationId });
    joinedConversationId = activeConversationId;
  }
  // Optimistic render so user always sees what was sent.
  appendMessage({
    id: `local-${Date.now()}`,
    role: "user",
    content,
    created_at: new Date().toISOString(),
  });
  socket?.emit("message.send", { conversation_id: activeConversationId, content });
};

if (token) {
  connectSocket();
  loadConversations();
}
