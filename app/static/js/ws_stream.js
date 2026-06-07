/**
 * ws_stream.js — Modo WebSocket para cámaras remotas.
 *
 * El teléfono-cámara abre /camera-agent/<id> y envía frames por WebSocket
 * al servidor (agent_frame). El dashboard consulta /api/cameras/<id>/frame
 * cada ~120ms (mismo origen, sin CORS) y pinta el JPEG en el canvas.
 * La detección MediaPipe sigue corriendo en el servidor.
 */

(function () {
    'use strict';

    const POLL_MS      = 120;   // polling del frame al servidor (~8fps)
    const RENDER_MS    = 40;    // redraw del canvas (~25fps)
    const SEND_MS      = 150;   // envío al servidor para detección (~7fps)
    const JPEG_QUALITY = 0.72;

    function waitForSocketIO(cb, retries) {
        if (typeof io !== 'undefined') { cb(); return; }
        if (retries <= 0) { console.warn('[ws_stream] socket.io no disponible'); return; }
        setTimeout(() => waitForSocketIO(cb, retries - 1), 200);
    }

    waitForSocketIO(init, 25);

    function init() {
        const socket = io({ transports: ['websocket'], reconnectionDelay: 2000 });

        socket.on('connect', () => {
            console.log('[ws_stream] conectado', socket.id);
            document.querySelectorAll('.camera-card[data-remote="true"]').forEach(card => initCard(card, socket));
        });

        socket.on('disconnect', () => console.warn('[ws_stream] desconectado'));

        window.WS_STREAM = { initCard: (card) => initCard(card, socket) };
    }

    function initCard(card, socket) {
        if (card.dataset.wsInit === 'true') return;
        card.dataset.wsInit = 'true';

        const cameraId   = card.dataset.cameraId;
        const cameraName = card.querySelector('h3')?.textContent?.trim() || '';
        const chatId     = window.DASHBOARD_CONFIG?.chatId || '';
        const frameUrl   = `/api/cameras/${cameraId}/frame`;

        const canvas  = card.querySelector('.ws-canvas');
        const overlay = card.querySelector('.camera-stream-overlay');
        if (!canvas) return;

        const ctx          = canvas.getContext('2d');
        const offscreen    = document.createElement('canvas');
        const offscreenCtx = offscreen.getContext('2d', { willReadFrequently: true });

        canvas.width     = 640;
        canvas.height    = 480;
        offscreen.width  = 640;
        offscreen.height = 480;

        let currentBitmap  = null;
        let lastBbox       = null;
        let personDetected = false;
        let detectionOn    = card.dataset.detectionActive !== 'false';
        let alive          = true;
        let errorCount     = 0;
        let lastSendTime   = 0;
        let agentConnected = false;

        function showOverlay(msg) {
            if (!overlay) return;
            overlay.hidden = false;
            const span = overlay.querySelector('span');
            if (span) span.textContent = msg;
        }
        function hideOverlay() { if (overlay) overlay.hidden = true; }

        // ── Polling de frames desde el servidor ──────────────────────────────
        async function pollLoop() {
            while (alive) {
                const t0 = Date.now();
                try {
                    const resp = await fetch(frameUrl, { cache: 'no-store' });

                    if (resp.status === 204) {
                        // El agente aún no ha enviado ningún frame
                        if (!agentConnected) {
                            showOverlay('Esperando que el teléfono-cámara se conecte…');
                        }
                    } else if (!resp.ok) {
                        throw new Error('HTTP ' + resp.status);
                    } else {
                        const blob = await resp.blob();
                        const bmp  = await createImageBitmap(blob);

                        if (canvas.width !== bmp.width || canvas.height !== bmp.height) {
                            canvas.width     = bmp.width;
                            canvas.height    = bmp.height;
                            offscreen.width  = bmp.width;
                            offscreen.height = bmp.height;
                        }

                        currentBitmap  = bmp;
                        agentConnected = true;
                        errorCount     = 0;
                        hideOverlay();

                        // Enviar frame al servidor para detección (rate-limited)
                        const now = Date.now();
                        if (detectionOn && now - lastSendTime >= SEND_MS) {
                            lastSendTime = now;
                            offscreenCtx.drawImage(bmp, 0, 0, offscreen.width, offscreen.height);
                            offscreen.toBlob((frameBlob) => {
                                if (!frameBlob) return;
                                const reader = new FileReader();
                                reader.onloadend = () => socket.emit('frame', {
                                    image:       reader.result,
                                    camera_name: cameraName,
                                    chat_id:     chatId,
                                    camera_id:   cameraId,
                                });
                                reader.readAsDataURL(frameBlob);
                            }, 'image/jpeg', JPEG_QUALITY);
                        }
                    }
                } catch (err) {
                    errorCount++;
                    if (errorCount >= 4) {
                        showOverlay('Error al obtener frames del servidor.');
                    }
                }

                const elapsed = Date.now() - t0;
                await new Promise(r => setTimeout(r, Math.max(0, POLL_MS - elapsed)));
            }
        }

        // ── Render loop ───────────────────────────────────────────────────────
        function renderLoop() {
            if (!alive) return;
            if (currentBitmap) {
                ctx.drawImage(currentBitmap, 0, 0, canvas.width, canvas.height);
                if (personDetected && lastBbox) {
                    const [x1, y1, x2, y2] = lastBbox;
                    ctx.strokeStyle = '#00d68f';
                    ctx.lineWidth   = 3;
                    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                    ctx.fillStyle   = 'rgba(0,214,143,0.12)';
                    ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
                    ctx.fillStyle   = '#00d68f';
                    ctx.font        = 'bold 13px system-ui';
                    ctx.fillText('⚠ Persona', x1 + 4, y1 + 16);
                }
            }
            setTimeout(renderLoop, RENDER_MS);
        }

        // ── Resultado del servidor ────────────────────────────────────────────
        socket.on('result_' + cameraId, (data) => {
            personDetected = !!data.person;
            lastBbox       = data.bbox || null;
            const label    = card.querySelector('[data-role="detection-status-label"]');
            if (label) {
                label.textContent = personDetected
                    ? '⚠ Persona detectada'
                    : (detectionOn ? 'Detección activa' : 'Detección pausada');
            }
        });

        // ── Toggle detección ──────────────────────────────────────────────────
        const toggleBtn = card.querySelector('[data-action="toggle-detection"]');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                detectionOn = !detectionOn;
                card.dataset.detectionActive = detectionOn ? 'true' : 'false';
                socket.emit('toggle_detection', { active: detectionOn, camera_id: cameraId });
                const span = toggleBtn.querySelector('span');
                if (span) span.textContent = detectionOn ? 'Desactivar detección' : 'Activar detección';
                if (!detectionOn) { personDetected = false; lastBbox = null; }
            });
        }

        // ── Init servidor ─────────────────────────────────────────────────────
        socket.emit('init_camera', {
            camera_name:  cameraName,
            chat_id:      chatId,
            detection_on: detectionOn,
            camera_id:    cameraId,
        });

        pollLoop();
        renderLoop();
    }

})();
