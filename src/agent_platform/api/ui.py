"""Single-page web chat UI for the Smart Grocery Platform.

Served directly by FastAPI with zero extra Python dependencies. Connects
to the /chat/stream SSE endpoint, renders Markdown, visualizes tool calls
and query results, and handles conversational multi-turn history.
"""

from __future__ import annotations

CHAT_UI_HTML = """<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-900 text-slate-100">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Smart Grocery Platform — Analyst Chat</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    code, pre { font-family: 'JetBrains Mono', monospace; }
    .prose pre { background: #0f172a; padding: 0.75rem 1rem; border-radius: 0.5rem; overflow-x: auto; }
    .prose code { color: #38bdf8; font-size: 0.875em; }
    .prose table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.875rem; }
    .prose th, .prose td { padding: 0.5rem 0.75rem; border: 1px solid #334155; text-align: left; }
    .prose th { background: #1e293b; font-weight: 600; }
    .prose tr:nth-child(even) { background: #0f172a80; }
    .prose p { margin-bottom: 0.75rem; line-height: 1.6; }
    .prose p:last-child { margin-bottom: 0; }
    .prose ul, .prose ol { margin-left: 1.5rem; margin-bottom: 0.75rem; }
    .prose ul { list-style-type: disc; }
    .prose ol { list-style-type: decimal; }
    .prose strong { color: #f8fafc; font-weight: 600; }
    .prose blockquote { border-left: 3px solid #38bdf8; padding-left: 1rem; font-style: italic; color: #94a3b8; margin: 0.75rem 0; }
    .pulse-dot { animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
  </style>
</head>
<body class="h-full flex flex-col bg-slate-950 text-slate-100 overflow-hidden">

  <!-- Header -->
  <header class="flex-none border-b border-slate-800 bg-slate-900/80 backdrop-blur px-4 sm:px-6 py-3 flex items-center justify-between">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-lg">
        🛒
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <h1 class="font-semibold text-slate-100 text-sm sm:text-base leading-tight">Smart Grocery Platform</h1>
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800/40">
            Chat Service
          </span>
        </div>
        <p class="text-xs text-slate-400">Shufersal · Rami Levy · Victory analytical intelligence</p>
      </div>
    </div>
    <div class="flex items-center space-x-2 sm:space-x-3 text-xs">
      <button id="btn-new-chat" class="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1">
        <span>↺</span>
        <span class="hidden sm:inline">New Thread</span>
      </button>
      <a href="/docs" target="_blank" class="px-3 py-1.5 rounded-md bg-slate-800/60 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition flex items-center space-x-1">
        <span>Swagger Docs</span>
        <span class="text-slate-500">↗</span>
      </a>
      <a href="/health" target="_blank" class="hidden sm:inline-flex px-2.5 py-1.5 rounded-md bg-slate-800/60 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition">
        Health
      </a>
    </div>
  </header>

  <!-- Main Chat Area -->
  <main class="flex-1 flex flex-col min-h-0 max-w-4xl w-full mx-auto p-4 sm:p-6">
    <!-- Messages Scroll Container -->
    <div id="messages-container" class="flex-1 overflow-y-auto space-y-5 pr-1 pb-4">
      
      <!-- Welcome Empty State -->
      <div id="empty-state" class="h-full flex flex-col items-center justify-center text-center p-6 space-y-6">
        <div class="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-3xl">
          📊
        </div>
        <div class="max-w-md space-y-2">
          <h2 class="text-lg font-semibold text-slate-100">Grocery Price Intelligence</h2>
          <p class="text-sm text-slate-400 leading-relaxed">
            Ask questions in English or Hebrew. Answers are grounded in read-only SQL over the verified 3-chain database (14,816 comparable products).
          </p>
        </div>
        <div class="w-full max-w-lg space-y-2 text-left">
          <div class="text-xs font-medium text-slate-400 uppercase tracking-wider px-1">Suggested inquiries</div>
          <div class="grid grid-cols-1 gap-2">
            <button class="prompt-chip p-3 rounded-lg bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 text-left transition flex items-start justify-between group">
              <span class="text-xs sm:text-sm text-slate-200">Which supermarket is cheapest most often?</span>
              <span class="text-xs text-emerald-400 opacity-0 group-hover:opacity-100 transition ml-2">Ask →</span>
            </button>
            <button class="prompt-chip p-3 rounded-lg bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 text-left transition flex items-start justify-between group">
              <span class="text-xs sm:text-sm text-slate-200">Where is 3% milk cheapest? (איפה הכי זול חלב 3%)</span>
              <span class="text-xs text-emerald-400 opacity-0 group-hover:opacity-100 transition ml-2">Ask →</span>
            </button>
            <button class="prompt-chip p-3 rounded-lg bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 text-left transition flex items-start justify-between group">
              <span class="text-xs sm:text-sm text-slate-200">Show database overview and number of comparable products</span>
              <span class="text-xs text-emerald-400 opacity-0 group-hover:opacity-100 transition ml-2">Ask →</span>
            </button>
          </div>
        </div>
      </div>

    </div>

    <!-- Active Conversation Badge -->
    <div id="thread-badge" class="flex-none hidden py-1.5 px-2 text-xs text-slate-400 flex items-center justify-between border-t border-slate-800/50">
      <div class="flex items-center space-x-1.5 truncate">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        <span class="truncate">Thread: <span id="conversation-id-label" class="font-mono text-slate-300"></span></span>
      </div>
      <button id="btn-inspect-context" class="text-slate-400 hover:text-slate-200 underline text-xs">Inspect context</button>
    </div>

    <!-- Input Form -->
    <div class="flex-none pt-2">
      <form id="chat-form" class="relative bg-slate-900 border border-slate-800 focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/50 rounded-xl shadow-lg transition">
        <textarea
          id="message-input"
          rows="1"
          dir="auto"
          placeholder="Ask a question about grocery prices across chains..."
          class="w-full bg-transparent px-4 py-3.5 pr-24 text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none max-h-36"
        ></textarea>
        <div class="absolute right-2 bottom-2.5 flex items-center space-x-1.5">
          <button
            type="submit"
            id="send-button"
            class="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white font-medium text-xs transition flex items-center space-x-1"
          >
            <span id="send-btn-text">Send</span>
            <span>↑</span>
          </button>
        </div>
      </form>
      <div class="mt-2 text-center text-[11px] text-slate-400 flex items-center justify-center space-x-3">
        <span>Read-only remote SQL</span>
        <span>•</span>
        <span>Deterministic tie handling</span>
        <span>•</span>
        <span>Skills playbooks</span>
      </div>
    </div>
  </main>

  <script>
    let currentConversationId = null;
    let isStreaming = false;

    const messagesContainer = document.getElementById('messages-container');
    const emptyState = document.getElementById('empty-state');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const sendBtnText = document.getElementById('send-btn-text');
    const threadBadge = document.getElementById('thread-badge');
    const conversationIdLabel = document.getElementById('conversation-id-label');
    const btnNewChat = document.getElementById('btn-new-chat');
    const btnInspectContext = document.getElementById('btn-inspect-context');

    // Auto-grow textarea
    messageInput.addEventListener('input', () => {
      messageInput.style.height = 'auto';
      messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + 'px';
    });

    messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    });

    // Preset prompts
    document.querySelectorAll('.prompt-chip').forEach(button => {
      button.addEventListener('click', () => {
        const text = button.querySelector('span').innerText;
        messageInput.value = text;
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
      });
    });

    // Reset thread
    btnNewChat.addEventListener('click', () => {
      currentConversationId = null;
      messagesContainer.innerHTML = '';
      messagesContainer.appendChild(emptyState);
      emptyState.style.display = 'flex';
      threadBadge.classList.add('hidden');
      messageInput.value = '';
      messageInput.focus();
    });

    // Inspect stored wire messages
    btnInspectContext.addEventListener('click', async () => {
      if (!currentConversationId) return;
      window.open(`/conversations/${currentConversationId}/context`, '_blank');
    });

    function setStreamingState(streaming) {
      isStreaming = streaming;
      sendButton.disabled = streaming;
      sendBtnText.innerText = streaming ? 'Streaming...' : 'Send';
      if (!streaming) {
        messageInput.focus();
      }
    }

    function createMessageBubble(role) {
      if (emptyState.parentNode) {
        emptyState.style.display = 'none';
      }

      const wrapper = document.createElement('div');
      wrapper.className = `flex flex-col ${role === 'user' ? 'items-end' : 'items-start'} space-y-1.5`;

      const header = document.createElement('div');
      header.className = 'text-[11px] font-medium text-slate-400 px-1';
      header.innerText = role === 'user' ? 'You' : 'Analyst Assistant';
      wrapper.appendChild(header);

      const bubble = document.createElement('div');
      bubble.dir = 'auto';
      if (role === 'user') {
        bubble.className = 'max-w-[85%] bg-slate-800 text-slate-100 border border-slate-700/80 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm';
      } else {
        bubble.className = 'max-w-full w-full bg-slate-900 text-slate-100 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-sm prose prose-invert';
      }
      wrapper.appendChild(bubble);
      messagesContainer.appendChild(wrapper);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      return { wrapper, bubble };
    }

    function createToolCallCard(toolName, args) {
      const card = document.createElement('div');
      card.className = 'my-2 rounded-lg border border-slate-800 bg-slate-950/60 p-2.5 text-xs font-mono text-slate-300';
      
      const titleRow = document.createElement('div');
      titleRow.className = 'flex items-center justify-between text-slate-400 cursor-pointer';
      titleRow.innerHTML = `
        <div class="flex items-center space-x-2">
          <span class="w-2 h-2 rounded-full bg-amber-400 pulse-dot"></span>
          <span class="font-semibold text-amber-300">Tool: ${toolName}</span>
        </div>
        <span class="text-[10px] text-slate-500 toggle-label">▼ details</span>
      `;

      const body = document.createElement('div');
      body.className = 'mt-2 space-y-1 text-[11px] border-t border-slate-800/80 pt-2';
      body.innerHTML = `<div class="text-slate-500">Arguments:</div><pre class="bg-slate-900 p-1.5 rounded overflow-x-auto text-amber-200">${escapeHtml(args)}</pre><div class="tool-result-box text-slate-400 italic">Executing query...</div>`;

      titleRow.addEventListener('click', () => {
        body.classList.toggle('hidden');
      });

      card.appendChild(titleRow);
      card.appendChild(body);
      return card;
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const message = messageInput.value.trim();
      if (!message || isStreaming) return;

      // Render user message
      const { bubble: userBubble } = createMessageBubble('user');
      userBubble.innerText = message;
      messageInput.value = '';
      messageInput.style.height = 'auto';

      // Render assistant container
      const { bubble: assistantBubble, wrapper: assistantWrapper } = createMessageBubble('assistant');
      setStreamingState(true);

      // Tool call tracking element
      const toolsContainer = document.createElement('div');
      toolsContainer.className = 'space-y-2 mb-2';
      assistantBubble.appendChild(toolsContainer);

      const contentBox = document.createElement('div');
      contentBox.className = 'prose prose-invert max-w-none';
      assistantBubble.appendChild(contentBox);

      const footerBox = document.createElement('div');
      footerBox.className = 'mt-3 text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/60 pt-2 hidden';
      assistantBubble.appendChild(footerBox);

      let accumulatedText = '';
      const toolCards = {};

      try {
        const response = await fetch('/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: message,
            conversation_id: currentConversationId,
          }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({ message: response.statusText }));
          throw new Error(errData.message || `HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop(); // keep incomplete tail

          let currentEvent = null;

          for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith('data:') && currentEvent) {
              const rawData = line.slice(5).trim();
              if (!rawData) continue;

              try {
                const payload = JSON.parse(rawData);
                handleStreamEvent(currentEvent, payload);
              } catch (parseErr) {
                console.warn('Could not parse SSE JSON', rawData, parseErr);
              }
              currentEvent = null;
            }
          }
        }
      } catch (err) {
        renderErrorBox(assistantBubble, err.message);
      } finally {
        setStreamingState(false);
      }

      function handleStreamEvent(type, payload) {
        if (type === 'status') {
          if (payload.conversation_id) {
            currentConversationId = payload.conversation_id;
            conversationIdLabel.innerText = currentConversationId.slice(0, 8) + '...';
            threadBadge.classList.remove('hidden');
          }
        } else if (type === 'tool_call') {
          const card = createToolCallCard(payload.tool_name, payload.arguments);
          toolCards[payload.tool_call_id] = card;
          toolsContainer.appendChild(card);
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else if (type === 'tool_result') {
          const card = toolCards[payload.tool_call_id];
          if (card) {
            const dot = card.querySelector('.pulse-dot');
            if (dot) {
              dot.classList.remove('pulse-dot', 'bg-amber-400');
              dot.classList.add('bg-emerald-400');
            }
            const resultBox = card.querySelector('.tool-result-box');
            if (resultBox) {
              resultBox.className = 'tool-result-box text-slate-300';
              resultBox.innerHTML = `<div class="text-slate-500 mt-1">Returned:</div><pre class="bg-slate-900 p-1.5 rounded overflow-x-auto text-emerald-300">${escapeHtml(payload.result)}</pre>`;
            }
          }
        } else if (type === 'text_delta') {
          accumulatedText += payload.delta;
          contentBox.innerHTML = marked.parse(accumulatedText);
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else if (type === 'usage') {
          footerBox.classList.remove('hidden');
          footerBox.innerHTML = `
            <span>Tokens: ${payload.total_tokens.toLocaleString()} (${payload.input_tokens} in / ${payload.output_tokens} out)</span>
            <span>Requests: ${payload.requests} · Tool calls: ${payload.tool_calls}</span>
          `;
        } else if (type === 'error') {
          renderErrorBox(assistantBubble, payload.error?.message || 'Run error occurred', payload.error?.code);
        } else if (type === 'completed') {
          if (payload.text && !accumulatedText) {
            contentBox.innerHTML = marked.parse(payload.text);
          }
        }
      }

      function renderErrorBox(container, message, code) {
        const errBox = document.createElement('div');
        errBox.className = 'my-2 rounded-lg bg-red-950/50 border border-red-800/60 p-3 text-xs text-red-200';
        errBox.innerHTML = `
          <div class="font-semibold text-red-400 flex items-center space-x-1.5 mb-1">
            <span>⚠ Error${code ? ` (${code})` : ''}</span>
          </div>
          <div class="leading-relaxed">${escapeHtml(message)}</div>
        `;
        container.appendChild(errBox);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    });
  </script>
</body>
</html>
"""
