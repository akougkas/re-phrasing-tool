class ChatUI {
    constructor() {
        // Initialize DOM elements
        this.chatContainer = document.querySelector('.chat-container');
        this.form = document.querySelector('#chat-form');
        this.input = document.querySelector('#user-input');
        this.submitButton = this.form?.querySelector('button[type="submit"]');
        this.charCount = document.querySelector('.char-count');
        this.validationError = document.querySelector('.validation-error');
        this.loadingSpinner = document.querySelector('#loading');
        
        // Get CSRF token from the form
        this.csrfToken = this.form?.querySelector('input[name="csrf_token"]')?.value;
        
        if (!this.csrfToken) {
            console.error('CSRF token not found');
            return;
        }
        
        // Initialize state
        this.messageHistory = [];
        this.controller = null;
        this.isProcessing = false;
        
        // Validation settings
        this.validation = {
            minLength: 2,
            maxLength: 1000,
            disallowedChars: new Set(['<', '>', '{', '}', '[', ']']),
            requestTimes: [],
            maxRequests: 10,
            windowSeconds: 60
        };
        
        // Check required elements
        if (!this.form || !this.input || !this.submitButton) {
            console.error('Required elements not found');
            return;
        }

        // Initialize the UI
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadPersistedState();
        this.maintainFocus();
        this.updateCharCount();
        
        // Setup state persistence
        window.addEventListener('beforeunload', () => this.persistState());
        
        // Hide loading spinner on init
        if (this.loadingSpinner) {
            this.loadingSpinner.style.display = 'none';
        }
    }

    maintainFocus() {
        this.input.focus();
        this.input.addEventListener('blur', () => {
            if (!this.isProcessing && !window.getSelection().toString()) {
                setTimeout(() => this.input.focus(), 100);
            }
        });
    }

    updateCharCount() {
        if (this.charCount) {
            const remaining = this.validation.maxLength - (this.input.value?.length || 0);
            this.charCount.textContent = `${remaining} characters remaining`;
        }
    }

    showError(message) {
        if (this.validationError) {
            this.validationError.textContent = message;
            this.validationError.style.display = 'block';
        }
    }

    hideError() {
        if (this.validationError) {
            this.validationError.style.display = 'none';
        }
    }

    validateLength(text) {
        if (text.length < this.validation.minLength) {
            throw new Error(`Input must be at least ${this.validation.minLength} characters long`);
        }
        if (text.length > this.validation.maxLength) {
            throw new Error(`Input cannot exceed ${this.validation.maxLength} characters`);
        }
        return true;
    }

    validateCharacters(text) {
        const foundDangerous = [...text].filter(c => this.validation.disallowedChars.has(c));
        if (foundDangerous.length > 0) {
            throw new Error('Input contains invalid characters');
        }
        return true;
    }

    validateRateLimit() {
        const currentTime = Date.now() / 1000;
        this.validation.requestTimes = this.validation.requestTimes.filter(
            time => currentTime - time < this.validation.windowSeconds
        );
        
        if (this.validation.requestTimes.length >= this.validation.maxRequests) {
            const retryAfter = Math.ceil(
                this.validation.requestTimes[0] + 
                this.validation.windowSeconds - 
                currentTime
            );
            throw new Error(`Rate limit exceeded. Please try again in ${retryAfter} seconds.`);
        }
        
        return true;
    }

    validateInput() {
        const text = this.input.value.trim();
        try {
            this.validateLength(text);
            this.validateCharacters(text);
            this.validateRateLimit();
            this.hideError();
            this.submitButton.disabled = false;
            return true;
        } catch (error) {
            this.showError(error.message);
            this.submitButton.disabled = true;
            return false;
        }
    }

    setLoadingState(loading) {
        this.isProcessing = loading;
        this.input.disabled = loading;
        this.submitButton.disabled = loading;
        
        if (this.loadingSpinner) {
            this.loadingSpinner.style.display = loading ? 'flex' : 'none';
        }
        
        if (!loading) {
            this.input.focus();
            this.updateCharCount();
        }
    }

    addMessage(content, type, persist = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.textContent = content;
        messageDiv.setAttribute('role', 'article');
        this.chatContainer.appendChild(messageDiv);
        
        // Trigger animation
        requestAnimationFrame(() => messageDiv.classList.add('show'));
        
        // Scroll into view
        messageDiv.scrollIntoView({ behavior: 'smooth' });

        if (persist) {
            this.messageHistory.push({
                content,
                type,
                timestamp: new Date().toISOString()
            });
            this.persistState();
        }

        return messageDiv;
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        if (this.isProcessing) return;
        
        const text = this.input.value.trim();
        
        try {
            if (!this.validateInput()) return;
            
            this.setLoadingState(true);
            this.addMessage(text, 'user');
            this.input.value = '';
            
            // Record request time for rate limiting
            this.validation.requestTimes.push(Date.now() / 1000);

            if (this.controller) {
                this.controller.abort();
            }
            this.controller = new AbortController();

            const response = await fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.csrfToken
                },
                body: JSON.stringify({ text }),
                signal: this.controller.signal
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Network response was not ok');
            }

            const messageDiv = this.addMessage('', 'assistant', false);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                if (chunk.trim()) {
                    assistantMessage += chunk;
                    messageDiv.textContent = assistantMessage;
                    messageDiv.scrollIntoView({ behavior: 'smooth' });
                }
            }

            if (assistantMessage) {
                this.messageHistory.push({
                    content: assistantMessage,
                    type: 'assistant',
                    timestamp: new Date().toISOString()
                });
                this.persistState();
            }

        } catch (error) {
            console.error('Error:', error);
            this.addMessage(error.message || 'Sorry, there was an error processing your request. Please try again.', 'assistant');
        } finally {
            this.setLoadingState(false);
            this.controller = null;
        }
    }

    loadPersistedState() {
        try {
            const state = localStorage.getItem('chatState');
            if (state) {
                const { messages } = JSON.parse(state);
                messages.forEach(msg => this.addMessage(msg.content, msg.type, false));
            }
        } catch (error) {
            console.error('Error loading persisted state:', error);
            localStorage.removeItem('chatState');
        }
    }

    persistState() {
        try {
            const state = {
                messages: this.messageHistory,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem('chatState', JSON.stringify(state));
        } catch (error) {
            console.error('Error persisting state:', error);
        }
    }

    setupEventListeners() {
        this.input.addEventListener('input', () => {
            this.updateCharCount();
            this.validateInput();
        });

        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
    }
}

// Initialize chat UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.chatUI = new ChatUI();
});
