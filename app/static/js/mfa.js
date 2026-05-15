document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('mfaForm');
    const codeInput = document.getElementById('mfaCode');
    const pemFileInput = document.getElementById('pemFile');
    const codeError = document.getElementById('mfaCodeError');
    const pemFileError = document.getElementById('pemFileError');
    const alertBox = document.getElementById('mfaError');
    const alertText = document.getElementById('mfaErrorText');
    const button = document.getElementById('mfaBtn');
    const config = window.MFA_CONFIG || {};

    const tabs = document.querySelectorAll('.mfa-tab');
    const methodPanels = document.querySelectorAll('.mfa-method-panel');

    tabs.forEach(function(tab) {
        tab.addEventListener('click', function() {
            var method = this.dataset.method;
            tabs.forEach(function(t) { t.classList.remove('is-active'); });
            methodPanels.forEach(function(p) { p.classList.remove('is-active'); });
            this.classList.add('is-active');
            var target = document.querySelector('[data-method-panel="' + method + '"]');
            if (target) target.classList.add('is-active');
            clearErrors();
        });
    });

    var dropzone = document.getElementById('pemDropzone');
    var dropzoneContent = document.getElementById('pemDropzoneContent');
    var dropzoneFile = document.getElementById('pemDropzoneFile');
    var pemFileName = document.getElementById('pemFileName');
    var pemClear = document.getElementById('pemClear');

    if (dropzone && pemFileInput) {
        ['dragenter', 'dragover'].forEach(function(event) {
            dropzone.addEventListener(event, function(e) {
                e.preventDefault();
                dropzone.classList.add('is-dragover');
            });
        });

        ['dragleave', 'drop'].forEach(function(event) {
            dropzone.addEventListener(event, function(e) {
                e.preventDefault();
                dropzone.classList.remove('is-dragover');
            });
        });

        dropzone.addEventListener('drop', function(e) {
            var files = e.dataTransfer.files;
            if (files.length > 0) {
                pemFileInput.files = files;
                showFileSelected(files[0].name);
            }
        });

        pemFileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                showFileSelected(this.files[0].name);
            }
        });

        if (pemClear) {
            pemClear.addEventListener('click', function(e) {
                e.stopPropagation();
                pemFileInput.value = '';
                hideFileSelected();
            });
        }
    }

    function showFileSelected(name) {
        if (dropzoneContent) dropzoneContent.hidden = true;
        if (dropzoneFile) dropzoneFile.hidden = false;
        if (pemFileName) pemFileName.textContent = name;
        if (dropzone) dropzone.classList.add('has-file');
    }

    function hideFileSelected() {
        if (dropzoneContent) dropzoneContent.hidden = false;
        if (dropzoneFile) dropzoneFile.hidden = true;
        if (pemFileName) pemFileName.textContent = '';
        if (dropzone) dropzone.classList.remove('has-file');
    }

    if (codeInput) {
        codeInput.addEventListener('input', clearErrors);
    }

    if (pemFileInput) {
        pemFileInput.addEventListener('change', clearErrors);
    }

    form.addEventListener('submit', async function(event) {
        event.preventDefault();

        const code = codeInput ? codeInput.value.trim() : '';
        const hasPemFile = Boolean(pemFileInput && pemFileInput.files && pemFileInput.files.length);
        if (!code && !hasPemFile) {
            if (codeInput) {
                codeInput.classList.add('input-error');
            }
            if (pemFileInput) {
                pemFileInput.classList.add('input-error');
            }
            if (codeError) {
                codeError.textContent = 'Ingresa un codigo o usa tu archivo PEM';
            }
            if (pemFileError) {
                pemFileError.textContent = 'Selecciona un archivo PEM';
            }
            return;
        }

        if (hasPemFile && !config.pemChallenge) {
            showError('No hay un reto PEM activo. Recarga la pagina e intenta de nuevo.');
            return;
        }

        let pemSignature = '';
        if (hasPemFile) {
            try {
                pemSignature = await signChallengeWithPem(pemFileInput.files[0], config.pemChallenge);
            } catch (error) {
                console.error('PEM signing error:', error);
                if (pemFileError) {
                    pemFileError.textContent = 'No se pudo usar el archivo PEM. Verifica que sea RSA PKCS#8 sin clave.';
                }
                if (pemFileInput) pemFileInput.classList.add('input-error');
                return;
            }
        }

        if (!code && !pemSignature) {
            if (codeInput) codeInput.classList.add('input-error');
            if (codeError) codeError.textContent = 'El codigo es requerido';
            return;
        }

        setLoading(true);

        try {
            const response = await fetch('/api/mfa/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    code,
                    pem_signature: pemSignature
                })
            });
            const data = await response.json();

            if (response.ok && data.success) {
                window.location.href = data.redirect || '/dashboard';
                return;
            }

            showError(data.message || 'Factor incorrecto.');
            setLoading(false);
        } catch (error) {
            console.error('MFA error:', error);
            showError('Error de conexion. Intenta de nuevo.');
            setLoading(false);
        }
    });

    function clearErrors() {
        if (codeInput) {
            codeInput.classList.remove('input-error');
        }
        if (pemFileInput) {
            pemFileInput.classList.remove('input-error');
        }
        if (codeError) {
            codeError.textContent = '';
        }
        if (pemFileError) {
            pemFileError.textContent = '';
        }
        alertBox.style.display = 'none';
        alertText.textContent = '';
    }

    function showError(message) {
        alertBox.style.display = 'flex';
        alertText.textContent = message;
    }

    async function signChallengeWithPem(file, challenge) {
        const pem = await file.text();
        const privateKey = await importPrivateKey(pem);
        const signature = await crypto.subtle.sign(
            { name: 'RSASSA-PKCS1-v1_5' },
            privateKey,
            new TextEncoder().encode(challenge)
        );
        return arrayBufferToBase64(signature);
    }

    async function importPrivateKey(pem) {
        const base64Body = pem
            .replace('-----BEGIN PRIVATE KEY-----', '')
            .replace('-----END PRIVATE KEY-----', '')
            .replace(/\s/g, '');

        if (!base64Body || pem.includes('BEGIN RSA PRIVATE KEY') || pem.includes('ENCRYPTED')) {
            throw new Error('Unsupported PEM format');
        }

        const binary = atob(base64Body);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) {
            bytes[index] = binary.charCodeAt(index);
        }

        return crypto.subtle.importKey(
            'pkcs8',
            bytes.buffer,
            {
                name: 'RSASSA-PKCS1-v1_5',
                hash: 'SHA-256'
            },
            false,
            ['sign']
        );
    }

    function arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let index = 0; index < bytes.byteLength; index += 1) {
            binary += String.fromCharCode(bytes[index]);
        }
        return btoa(binary);
    }

    function setLoading(isLoading) {
        const btnText = button.querySelector('.btn-text');
        const btnLoader = button.querySelector('.btn-loader');

        button.disabled = isLoading;
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnLoader.style.display = isLoading ? 'inline-block' : 'none';
    }
});
