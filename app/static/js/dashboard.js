document.addEventListener('DOMContentLoaded', () => {
    const config = window.DASHBOARD_CONFIG || {};
    const cameraForm = document.getElementById('cameraForm');
    const cameraGrid = document.getElementById('cameraGrid');
    const cameraEmptyState = document.getElementById('cameraEmptyState');
    const cameraCount = document.getElementById('cameraCount');
    const activeCameraCount = document.getElementById('activeCameraCount');
    const cameraFormAlert = document.getElementById('cameraFormAlert');
    const cameraSubmitButton = document.getElementById('cameraSubmitButton');
    const refreshAllButton = document.getElementById('refreshAllButton');

    let cameras = Array.isArray(config.cameras) ? [...config.cameras] : [];
    let snapshotLoopHandle = null;

    attachCardEvents(cameraGrid);
    syncEmptyState();
    updateCounters();
    startSnapshotLoop();

    cameraForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const formData = new FormData(cameraForm);
        const payload = {
            name: (formData.get('name') || '').trim(),
            location: (formData.get('location') || '').trim(),
            stream_url: (formData.get('stream_url') || '').trim(),
            snapshot_url: (formData.get('snapshot_url') || '').trim()
        };

        if (!payload.name || !payload.stream_url) {
            showFormAlert('Completa al menos el nombre y la URL del stream.', true);
            return;
        }

        setFormLoading(true);
        showFormAlert('', false, true);

        try {
            const response = await fetch(config.createEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'No fue posible registrar la camara');
            }

            cameras.unshift(data.camera);
            cameraGrid.insertAdjacentHTML('afterbegin', createCameraCardMarkup(data.camera));
            attachCardEvents(cameraGrid);
            startSnapshotLoop();
            cameraForm.reset();
            showFormAlert(data.message || 'Camara agregada correctamente.', false);
            syncEmptyState();
            updateCounters();
        } catch (error) {
            showFormAlert(error.message, true);
        } finally {
            setFormLoading(false);
        }
    });

    refreshAllButton.addEventListener('click', () => {
        cameraGrid.querySelectorAll('.camera-card').forEach((card) => {
            refreshCameraStream(card);
        });
    });

    function attachCardEvents(root) {
        root.querySelectorAll('.camera-card').forEach((card) => {
            if (card.dataset.bound === 'true') {
                return;
            }

            card.dataset.bound = 'true';
            card.dataset.streamReady = 'false';
            const img = card.querySelector('.camera-stream');
            const overlay = card.querySelector('.camera-stream-overlay');
            const frame = card.querySelector('.camera-stream-frame');
            const previewMode = frame?.dataset.previewMode || 'snapshot';
            const toggleDetectionButton = card.querySelector('[data-action="toggle-detection"]');
            const refreshButton = card.querySelector('[data-action="refresh"]');
            const deleteButton = card.querySelector('[data-action="delete"]');

            syncDetectionUi(card);

            if (img && overlay) {
                if (previewMode === 'stream') {
                    overlay.hidden = true;
                }

                img.addEventListener('load', () => {
                    card.dataset.streamReady = 'true';
                    overlay.hidden = true;
                });

                img.addEventListener('error', () => {
                    const fallbackSrc = img.dataset.fallbackSrc || '';
                    const currentBaseUrl = (img.getAttribute('src') || '').split('?')[0];
                    const fallbackBaseUrl = fallbackSrc.split('?')[0];

                    if (fallbackSrc && fallbackBaseUrl && currentBaseUrl !== fallbackBaseUrl) {
                        card.dataset.streamReady = 'false';
                        overlay.hidden = true;
                        img.src = `${fallbackBaseUrl}?t=${Date.now()}`;
                        return;
                    }

                    if (previewMode === 'stream') {
                        overlay.hidden = true;
                        return;
                    }

                    overlay.hidden = false;
                });
            }

            if (refreshButton) {
                refreshButton.addEventListener('click', () => {
                    refreshCameraStream(card);
                });
            }

            if (toggleDetectionButton) {
                toggleDetectionButton.addEventListener('click', () => {
                    toggleCameraDetection(card);
                });
            }

            if (deleteButton) {
                deleteButton.addEventListener('click', async () => {
                    const cameraId = card.dataset.cameraId;
                    if (!cameraId) {
                        return;
                    }

                    const confirmDelete = window.confirm('Se eliminara esta camara del dashboard. Continuar?');
                    if (!confirmDelete) {
                        return;
                    }

                    card.classList.add('is-busy');

                    try {
                        const response = await fetch(`${config.deleteBaseEndpoint}/${cameraId}`, {
                            method: 'DELETE'
                        });
                        const data = await response.json();

                        if (!response.ok || !data.success) {
                            throw new Error(data.message || 'No fue posible eliminar la camara');
                        }

                        cameras = cameras.filter((camera) => String(camera.id) !== String(cameraId));
                        card.remove();
                        syncEmptyState();
                        updateCounters();
                        showFormAlert(data.message || 'Camara eliminada correctamente.', false);
                    } catch (error) {
                        card.classList.remove('is-busy');
                        showFormAlert(error.message, true);
                    }
                });
            }
        });
    }

    function refreshCameraStream(card) {
        const img = card.querySelector('.camera-stream');
        const overlay = card.querySelector('.camera-stream-overlay');
        const frame = card.querySelector('.camera-stream-frame');
        const previewMode = frame?.dataset.previewMode || 'snapshot';
        if (!img) {
            return;
        }

        const baseUrl = img.getAttribute('src').split('?')[0];
        overlay.hidden = true;
        if (previewMode === 'stream') {
            card.dataset.streamReady = 'false';
        }
        img.src = `${baseUrl}?t=${Date.now()}`;
    }

    function toggleCameraDetection(card) {
        const img = card.querySelector('.camera-stream');
        const overlay = card.querySelector('.camera-stream-overlay');
        const detectionAvailable = card.dataset.detectionAvailable === 'true';
        const detectionActive = card.dataset.detectionActive === 'true';
        if (!img || !detectionAvailable) {
            return;
        }

        const primarySrc = img.dataset.primarySrc || img.getAttribute('src');
        const fallbackSrc = img.dataset.fallbackSrc || img.getAttribute('src');
        const nextSrc = detectionActive ? fallbackSrc : primarySrc;

        card.dataset.detectionActive = detectionActive ? 'false' : 'true';
        card.dataset.streamReady = 'false';
        if (overlay) {
            overlay.hidden = true;
        }
        img.src = `${nextSrc.split('?')[0]}?t=${Date.now()}`;
        syncDetectionUi(card);
    }

    function syncDetectionUi(card) {
        const detectionAvailable = card.dataset.detectionAvailable === 'true';
        const detectionActive = card.dataset.detectionActive === 'true';
        const modeLabel = card.querySelector('[data-role="stream-mode-label"]');
        const statusLabel = card.querySelector('[data-role="detection-status-label"]');
        const toggleButton = card.querySelector('[data-action="toggle-detection"]');

        if (modeLabel) {
            modeLabel.textContent = detectionAvailable && detectionActive
                ? 'Stream con deteccion'
                : 'Stream normal';
        }

        if (statusLabel) {
            statusLabel.textContent = detectionAvailable && detectionActive
                ? 'Deteccion en PC activa'
                : (detectionAvailable ? 'Deteccion en PC desactivada' : 'Deteccion no disponible');
        }

        if (toggleButton) {
            toggleButton.disabled = !detectionAvailable;
            const buttonLabel = toggleButton.querySelector('span');
            if (buttonLabel) {
                buttonLabel.textContent = detectionAvailable
                    ? (detectionActive ? 'Desactivar deteccion' : 'Activar deteccion')
                    : 'Deteccion no disponible';
            }
        }
    }

    function createCameraCardMarkup(camera) {
        const location = escapeHtml(camera.location || 'Sin ubicacion registrada');
        const name = escapeHtml(camera.name);
        const streamUrl = escapeHtml(camera.stream_url);
        const snapshotUrl = escapeHtml(camera.snapshot_url || '');
        const previewUrl = escapeHtml(camera.detection_stream_url || camera.preview_url || streamUrl);
        const fallbackUrl = escapeHtml(camera.preview_url || streamUrl);
        const detectionAvailable = camera.detection_enabled === true;
        const streamModeLabel = camera.preview_mode === 'snapshot'
            ? 'Captura estatica'
            : (detectionAvailable ? 'Stream con deteccion' : 'Stream normal');
        const snapshotMeta = snapshotUrl
            ? '<span><i class="fas fa-camera"></i> Captura disponible</span>'
            : '<span><i class="fas fa-camera-slash"></i> Sin captura configurada</span>';
        const detectionMeta = camera.preview_mode === 'stream'
            ? `<span><i class="fas fa-person-rays"></i> <span data-role="detection-status-label">${detectionAvailable ? 'Deteccion en PC activa' : 'Deteccion no disponible'}</span></span>`
            : '<span><i class="fas fa-person-rays"></i> Deteccion reservada para stream</span>';
        const snapshotAction = snapshotUrl
            ? `
                <a href="${snapshotUrl}" class="ghost-button ghost-button--compact" target="_blank" rel="noreferrer">
                    <i class="fas fa-image"></i>
                    <span>Captura</span>
                </a>
            `
            : '';
        const detectionAction = camera.preview_mode === 'stream'
            ? `
                <button
                    type="button"
                    class="ghost-button ghost-button--compact"
                    data-action="toggle-detection"
                    ${detectionAvailable ? '' : 'disabled'}
                >
                    <i class="fas fa-person-rays"></i>
                    <span>${detectionAvailable ? 'Desactivar deteccion' : 'Deteccion no disponible'}</span>
                </button>
            `
            : '';

        return `
            <article
                class="camera-card"
                data-camera-id="${camera.id}"
                data-detection-available="${detectionAvailable ? 'true' : 'false'}"
                data-detection-active="${detectionAvailable ? 'true' : 'false'}"
            >
                <div class="camera-card-header">
                    <div>
                        <h3>${name}</h3>
                        <p>${location}</p>
                    </div>
                    <span class="camera-status">En vivo</span>
                </div>

                <div class="camera-stream-frame" data-preview-mode="${escapeHtml(camera.preview_mode || 'snapshot')}">
                    <img
                        class="camera-stream"
                        src="${previewUrl}"
                        data-primary-src="${previewUrl}"
                        data-fallback-src="${fallbackUrl}"
                        alt="Stream de ${name}"
                        loading="eager"
                        referrerpolicy="no-referrer"
                    >
                    <div class="camera-stream-overlay" hidden>
                        <i class="fas fa-plug-circle-xmark"></i>
                        <span>No se pudo cargar el stream. Revisa la IP y el endpoint.</span>
                    </div>
                </div>

                <div class="camera-card-meta">
                    <span><i class="fas fa-network-wired"></i> ${streamUrl}</span>
                    <span><i class="fas fa-arrows-rotate"></i> <span data-role="stream-mode-label">${streamModeLabel}</span></span>
                    ${detectionMeta}
                    ${snapshotMeta}
                </div>

                <div class="camera-card-actions">
                    ${detectionAction}
                    <button type="button" class="ghost-button ghost-button--compact" data-action="refresh">
                        <i class="fas fa-rotate"></i>
                        <span>Recargar</span>
                    </button>
                    <a href="${streamUrl}" class="ghost-button ghost-button--compact" target="_blank" rel="noreferrer">
                        <i class="fas fa-up-right-from-square"></i>
                        <span>Abrir stream</span>
                    </a>
                    ${snapshotAction}
                    <button type="button" class="danger-button danger-button--compact" data-action="delete">
                        <i class="fas fa-trash"></i>
                        <span>Eliminar</span>
                    </button>
                </div>
            </article>
        `;
    }

    function updateCounters() {
        cameraCount.textContent = String(cameras.length);
        activeCameraCount.textContent = String(cameras.length);
    }

    function startSnapshotLoop() {
        if (snapshotLoopHandle) {
            window.clearInterval(snapshotLoopHandle);
        }

        snapshotLoopHandle = window.setInterval(() => {
            cameraGrid.querySelectorAll('.camera-stream-frame[data-preview-mode="snapshot"]').forEach((frame) => {
                const img = frame.querySelector('.camera-stream');
                const overlay = frame.querySelector('.camera-stream-overlay');
                if (!img) {
                    return;
                }

                const baseUrl = img.getAttribute('src').split('?')[0];
                if (overlay) {
                    overlay.hidden = true;
                }
                img.src = `${baseUrl}?t=${Date.now()}`;
            });
        }, 700);
    }

    function syncEmptyState() {
        cameraEmptyState.classList.toggle('is-hidden', cameras.length > 0);
    }

    function setFormLoading(isLoading) {
        cameraSubmitButton.disabled = isLoading;
        cameraSubmitButton.classList.toggle('is-busy', isLoading);
    }

    function showFormAlert(message, isError, hide = false) {
        if (hide) {
            cameraFormAlert.hidden = true;
            cameraFormAlert.textContent = '';
            cameraFormAlert.classList.remove('is-error');
            return;
        }

        cameraFormAlert.hidden = false;
        cameraFormAlert.textContent = message;
        cameraFormAlert.classList.toggle('is-error', Boolean(isError));
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
});
