document.addEventListener('DOMContentLoaded', function() {
    const navItems = document.querySelectorAll('.sec-nav-item');
    const panels = document.querySelectorAll('.sec-panel');

    navItems.forEach(function(item) {
        item.addEventListener('click', function() {
            const tab = this.dataset.tab;

            navItems.forEach(function(nav) { nav.classList.remove('is-active'); });
            panels.forEach(function(panel) { panel.classList.remove('is-active'); });

            this.classList.add('is-active');
            var target = document.querySelector('[data-panel="' + tab + '"]');
            if (target) target.classList.add('is-active');
        });
    });

    const generateButton = document.getElementById('generatePemKey');
    const publicKeyField = document.getElementById('publicKey');
    const alertBox = document.getElementById('pemGenerateAlert');

    if (!generateButton || !publicKeyField || !window.crypto || !window.crypto.subtle) {
        return;
    }

    generateButton.addEventListener('click', async function() {
        setBusy(true);
        showAlert('Generando llave RSA...', false);

        try {
            const keyPair = await crypto.subtle.generateKey(
                {
                    name: 'RSASSA-PKCS1-v1_5',
                    modulusLength: 2048,
                    publicExponent: new Uint8Array([1, 0, 1]),
                    hash: 'SHA-256'
                },
                true,
                ['sign', 'verify']
            );

            const publicKey = await crypto.subtle.exportKey('spki', keyPair.publicKey);
            const privateKey = await crypto.subtle.exportKey('pkcs8', keyPair.privateKey);
            publicKeyField.value = toPem(publicKey, 'PUBLIC KEY');
            downloadPrivateKey(toPem(privateKey, 'PRIVATE KEY'));
            showAlert('Archivo PEM generado. Registra la clave publica y conserva el archivo privado.', false);
        } catch (error) {
            console.error('PEM generation error:', error);
            showAlert('No se pudo generar la llave en este navegador.', true);
        } finally {
            setBusy(false);
        }
    });

    function toPem(buffer, label) {
        const base64 = arrayBufferToBase64(buffer);
        const lines = base64.match(/.{1,64}/g) || [];
        return [
            '-----BEGIN ' + label + '-----',
            ...lines,
            '-----END ' + label + '-----'
        ].join('\n');
    }

    function arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let index = 0; index < bytes.byteLength; index += 1) {
            binary += String.fromCharCode(bytes[index]);
        }
        return btoa(binary);
    }

    function downloadPrivateKey(pem) {
        const blob = new Blob([pem], { type: 'application/x-pem-file' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'ipguard-login-key.pem';
        document.body.appendChild(link);
        link.click();
        URL.revokeObjectURL(link.href);
        link.remove();
    }

    function showAlert(message, isError) {
        alertBox.hidden = false;
        alertBox.textContent = message;
        alertBox.classList.toggle('is-error', isError);
    }

    function setBusy(isBusy) {
        generateButton.disabled = isBusy;
        generateButton.classList.toggle('is-busy', isBusy);
    }
});
