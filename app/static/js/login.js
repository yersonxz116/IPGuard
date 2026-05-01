/**
 * IPGuard - Login Page JavaScript
 * Maneja la validacion y envio del formulario de login
 */

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const togglePasswordBtn = document.getElementById('togglePassword');
    const loginBtn = document.getElementById('loginBtn');
    const loginError = document.getElementById('loginError');
    const errorText = document.getElementById('errorText');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');

    // Toggle password visibility
    togglePasswordBtn.addEventListener('click', function() {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;

        const icon = togglePasswordBtn.querySelector('i');
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    });

    // Clear error when typing
    usernameInput.addEventListener('input', function() {
        clearFieldError(usernameInput, usernameError);
        hideLoginError();
    });

    passwordInput.addEventListener('input', function() {
        clearFieldError(passwordInput, passwordError);
        hideLoginError();
    });

    // Form submission
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Validate fields
        let isValid = true;

        if (!usernameInput.value.trim()) {
            showFieldError(usernameInput, usernameError, 'El usuario o email es requerido');
            isValid = false;
        }

        if (!passwordInput.value.trim()) {
            showFieldError(passwordInput, passwordError, 'La contrasena es requerida');
            isValid = false;
        }

        if (!isValid) {
            return;
        }

        // Show loading state
        setLoadingState(true);

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: usernameInput.value.trim(),
                    password: passwordInput.value
                })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Login successful - redirect to dashboard
                window.location.href = data.redirect || '/dashboard';
            } else {
                // Login failed
                showLoginError(data.message || 'Credenciales incorrectas. Intenta de nuevo.');
                setLoadingState(false);
            }
        } catch (error) {
            console.error('Login error:', error);
            showLoginError('Error de conexion. Verifica tu red e intenta de nuevo.');
            setLoadingState(false);
        }
    });

    // Helper functions
    function showFieldError(input, errorElement, message) {
        input.classList.add('input-error');
        errorElement.textContent = message;
    }

    function clearFieldError(input, errorElement) {
        input.classList.remove('input-error');
        errorElement.textContent = '';
    }

    function showLoginError(message) {
        loginError.style.display = 'flex';
        errorText.textContent = message;
    }

    function hideLoginError() {
        loginError.style.display = 'none';
        errorText.textContent = '';
    }

    function setLoadingState(loading) {
        const btnText = loginBtn.querySelector('.btn-text');
        const btnLoader = loginBtn.querySelector('.btn-loader');

        loginBtn.disabled = loading;
        btnText.style.display = loading ? 'none' : 'inline';
        btnLoader.style.display = loading ? 'inline-block' : 'none';
    }

    // Add enter key support for password field
    passwordInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loginForm.dispatchEvent(new Event('submit'));
        }
    });
});
