document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');
    const chatStatus = document.getElementById('chatStatus');
    const sendButton = document.getElementById('sendButton');
    const clearChat = document.getElementById('clearChat');
    const modelStatus = document.getElementById('modelStatus');
    const quickPrompts = document.querySelectorAll('[data-prompt]');
    const { endpoint, model } = window.IA_CHAT_CONFIG;
    let history = [];

    messageInput.addEventListener('input', autoResize);
    clearChat.addEventListener('click', resetChat);
    quickPrompts.forEach((button) => {
        button.addEventListener('click', () => {
            messageInput.value = button.dataset.prompt;
            autoResize();
            messageInput.focus();
        });
    });

    chatForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const message = messageInput.value.trim();
        if (!message) {
            return;
        }

        appendMessage('user', 'Tú', message);
        history.push({ role: 'user', content: message });
        messageInput.value = '';
        autoResize();
        setLoading(true, `Consultando ${model}...`);

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                body: JSON.stringify({
                    message,
                    history: history.slice(0, -1)
                })
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'No fue posible completar la consulta');
            }

            history.push({ role: 'assistant', content: data.response });
            appendMessage('assistant', 'IA', data.response);
            setLoading(false, `${model} respondio en formato breve.`);
        } catch (error) {
            appendMessage('assistant', 'IA', `Error: ${error.message}`);
            history.push({ role: 'assistant', content: `Error: ${error.message}` });
            setLoading(false, 'Falló la consulta al modelo.');
        }
    });

    messageInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.requestSubmit();
        }
    });

    function appendMessage(role, label, content) {
        const article = document.createElement('article');
        article.className = `message message-${role}`;

        const badge = document.createElement('div');
        badge.className = 'message-badge';
        badge.textContent = role === 'user' ? 'TU' : 'IA';

        const body = document.createElement('div');
        body.className = 'message-body';

        const roleLabel = document.createElement('p');
        roleLabel.className = 'message-role';
        roleLabel.textContent = label;

        const paragraph = document.createElement('p');
        paragraph.textContent = content;

        body.appendChild(roleLabel);
        body.appendChild(paragraph);
        article.appendChild(badge);
        article.appendChild(body);
        chatMessages.appendChild(article);
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function resetChat() {
        history = [];
        chatMessages.innerHTML = `
            <article class="message message-assistant">
                <div class="message-badge">IA</div>
                <div class="message-body">
                    <p class="message-role">Asistente</p>
                    <p>Estoy usando ${model} para responder mas rapido. Mantendre cada respuesta en maximo dos frases.</p>
                </div>
            </article>
        `;
        chatStatus.textContent = 'Historial reiniciado. Puedes comenzar una consulta nueva.';
        modelStatus.textContent = 'Listo';
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function autoResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = `${Math.min(messageInput.scrollHeight, 220)}px`;
    }

    function setLoading(isLoading, statusText) {
        sendButton.disabled = isLoading;
        clearChat.disabled = isLoading;
        messageInput.disabled = isLoading;
        quickPrompts.forEach((button) => {
            button.disabled = isLoading;
        });
        chatStatus.textContent = statusText;
        modelStatus.textContent = isLoading ? 'Pensando' : 'Listo';
    }
});
