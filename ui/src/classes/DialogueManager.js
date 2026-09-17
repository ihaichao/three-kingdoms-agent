import ApiService from '../services/ApiService';
import WebSocketApiService from '../services/WebSocketApiService';

class DialogueManager {
  constructor(scene) {
    // Core properties
    this.scene = scene;
    this.dialogueBox = null;
    this.activePhilosopher = null;

    // State management
    this.isTyping = false;
    this.isStreaming = false;
    this.currentMessage = '';
    this.streamingText = '';

    // Cursor properties
    this.cursorBlinkEvent = null;
    this.cursorVisible = true;

    // Connection management
    this.hasSetupListeners = false;
    this.disconnectTimeout = null;

    // Native DOM input for Chinese IME and standard text input support
    this.domInput = null;
    this.isComposing = false;
  }

  // === Initialization ===

  initialize(dialogueBox) {
    this.dialogueBox = dialogueBox;
    this.createDomInput();

    if (!this.hasSetupListeners) {
      this.setupKeyboardListeners();
      this.hasSetupListeners = true;
    }
  }

  createDomInput() {
    if (this.domInput) return;

    this.domInput = document.createElement('textarea');
    this.domInput.id = 'phaser-dialogue-input';
    this.domInput.style.position = 'fixed';
    this.domInput.style.zIndex = '10000';
    this.domInput.style.opacity = '0';
    this.domInput.style.pointerEvents = 'auto';
    this.domInput.style.resize = 'none';
    this.domInput.style.overflow = 'hidden';
    this.domInput.style.border = 'none';
    this.domInput.style.outline = 'none';
    this.domInput.style.background = 'transparent';
    this.domInput.style.display = 'none';
    this.domInput.style.padding = '0';
    this.domInput.style.margin = '0';
    this.domInput.autocomplete = 'off';
    this.domInput.autocorrect = 'off';
    this.domInput.autocapitalize = 'off';
    this.domInput.spellcheck = false;

    this.isComposing = false;

    this.domInput.addEventListener('compositionstart', () => {
      this.isComposing = true;
    });

    this.domInput.addEventListener('compositionupdate', () => {
      this.isComposing = true;
    });

    this.domInput.addEventListener('compositionend', () => {
      this.isComposing = false;
      this.currentMessage = this.domInput.value;
      this.updateDialogueText();
    });

    this.domInput.addEventListener('input', () => {
      this.currentMessage = this.domInput.value;
      this.updateDialogueText();
    });

    this.domInput.addEventListener('keydown', async (e) => {
      e.stopPropagation();

      if (e.key === 'Enter' && !e.shiftKey) {
        if (this.isComposing || e.keyCode === 229) {
          return;
        }
        e.preventDefault();
        await this.handleEnterKey();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        this.closeDialogue();
      }
    });

    this.domInput.addEventListener('keyup', (e) => e.stopPropagation());
    this.domInput.addEventListener('keypress', (e) => e.stopPropagation());

    document.body.appendChild(this.domInput);

    window.addEventListener('resize', () => {
      if (this.isTyping) {
        this.updateInputPosition();
      }
    });

    this.scene.input.on('pointerdown', () => {
      if (this.isTyping && this.domInput) {
        setTimeout(() => {
          if (this.isTyping && this.domInput) {
            this.domInput.focus();
          }
        }, 10);
      }
    });
  }

  updateInputPosition() {
    if (!this.domInput || !this.scene?.game?.canvas) return;
    const canvas = this.scene.game.canvas;
    const rect = canvas.getBoundingClientRect();
    const scaleX = rect.width / (this.scene.game.config.width || 1024);
    const scaleY = rect.height / (this.scene.game.config.height || 768);

    const x = rect.left + 120 * scaleX;
    const y = rect.top + 520 * scaleY;
    const width = 784 * scaleX;
    const height = 160 * scaleY;
    const fontSize = Math.max(14, Math.round(24 * scaleY));

    this.domInput.style.left = `${x}px`;
    this.domInput.style.top = `${y}px`;
    this.domInput.style.width = `${width}px`;
    this.domInput.style.height = `${height}px`;
    this.domInput.style.fontSize = `${fontSize}px`;
  }

  enableInput() {
    this.createDomInput();
    this.isTyping = true;
    this.domInput.value = this.currentMessage;
    this.domInput.style.display = 'block';
    this.updateInputPosition();
    this.domInput.focus();
    if (this.scene?.input?.keyboard) {
      this.scene.input.keyboard.enabled = false;
    }
  }

  disableInput() {
    if (!this.domInput) return;
    this.isTyping = false;
    this.domInput.blur();
    this.domInput.style.display = 'none';
    if (this.scene?.input?.keyboard) {
      this.scene.input.keyboard.enabled = true;
    }
  }

  setupKeyboardListeners() {
    this.scene.input.keyboard.on('keydown', async (event) => {
      if (!this.isTyping) {
        if (this.isStreaming && (event.key === 'Space' || event.key === ' ')) {
          this.skipStreaming();
        }
        return;
      }

      if (event.key === 'Escape') {
        this.closeDialogue();
      }
    });
  }

  // === Input Handling ===

  async handleEnterKey() {
    if (this.currentMessage.trim() !== '') {
      this.disableInput();
      this.dialogueBox.show('...', true);
      this.stopCursorBlink();

      if (this.activePhilosopher.defaultMessage) {
        await this.handleDefaultMessage();
      } else {
        await this.handleWebSocketMessage();
      }

      this.currentMessage = '';
      if (this.domInput) {
        this.domInput.value = '';
      }
    } else {
      this.restartTypingPrompt();
    }
  }

  // === Message Processing ===

  async handleDefaultMessage() {
    const apiResponse = this.activePhilosopher.defaultMessage;
    this.dialogueBox.show('', true);
    await this.streamText(apiResponse);
  }

  async handleWebSocketMessage() {
    this.dialogueBox.show('', true);
    this.isStreaming = true;
    this.streamingText = '';

    try {
      await this.processWebSocketMessage();
    } catch (error) {
      console.error('WebSocket error:', error);
      await this.fallbackToRegularApi();
    } finally {
      this.isTyping = false;
    }
  }

  async processWebSocketMessage() {
    await WebSocketApiService.connect();

    const callbacks = {
      onMessage: () => {
        this.finishStreaming();
      },
      onChunk: (chunk) => {
        this.streamingText += chunk;
        this.dialogueBox.show(this.streamingText, true);
      },
      onStreamingStart: () => {
        this.isStreaming = true;
      },
      onStreamingEnd: () => {
        this.finishStreaming();
      }
    };

    await WebSocketApiService.sendMessage(
      this.activePhilosopher,
      this.currentMessage,
      callbacks
    );

    while (this.isStreaming) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    this.currentMessage = '';
    WebSocketApiService.disconnect();
  }

  finishStreaming() {
    this.isStreaming = false;
    this.dialogueBox.show(this.streamingText, true);
  }

  async fallbackToRegularApi() {
    const apiResponse = await ApiService.sendMessage(
      this.activePhilosopher,
      this.currentMessage
    );
    await this.streamText(apiResponse);
  }

  // === UI Management ===

  updateDialogueText() {
    const displayText = this.currentMessage + (this.cursorVisible ? '|' : '');
    this.dialogueBox.show(displayText, true);
  }

  restartTypingPrompt() {
    this.currentMessage = '';
    this.dialogueBox.show('|', true);

    this.stopCursorBlink();
    this.cursorVisible = true;
    this.startCursorBlink();

    this.enableInput();
    this.updateDialogueText();
  }

  // === Cursor Management ===

  startCursorBlink() {
    this.cursorBlinkEvent = this.scene.time.addEvent({
      delay: 300,
      callback: () => {
        if (this.dialogueBox.isVisible() && this.isTyping) {
          this.cursorVisible = !this.cursorVisible;
          this.updateDialogueText();
        }
      },
      loop: true
    });
  }

  stopCursorBlink() {
    if (this.cursorBlinkEvent) {
      this.cursorBlinkEvent.remove();
      this.cursorBlinkEvent = null;
    }
  }

  // === Dialogue Flow Control ===

  startDialogue(philosopher) {
    this.cancelDisconnectTimeout();

    this.activePhilosopher = philosopher;
    this.currentMessage = '';

    this.dialogueBox.show('|', true);
    this.stopCursorBlink();

    this.cursorVisible = true;
    this.startCursorBlink();

    this.enableInput();
  }

  closeDialogue() {
    this.dialogueBox.hide();
    this.currentMessage = '';
    this.isStreaming = false;

    this.disableInput();
    if (this.domInput) {
      this.domInput.value = '';
    }

    this.stopCursorBlink();
    this.scheduleDisconnect();
  }

  isInDialogue() {
    return this.dialogueBox && this.dialogueBox.isVisible();
  }

  continueDialogue() {
    if (!this.dialogueBox.isVisible()) return;

    if (this.isStreaming) {
      this.skipStreaming();
    } else if (!this.isTyping) {
      this.restartTypingPrompt();
    }
  }

  // === Text Streaming ===

  async streamText(text, speed = 30) {
    this.isStreaming = true;
    let displayedText = '';

    this.stopCursorBlink();

    for (let i = 0; i < text.length; i++) {
      displayedText += text[i];
      this.dialogueBox.show(displayedText, true);

      await new Promise(resolve => setTimeout(resolve, speed));

      if (!this.isStreaming) break;
    }

    if (this.isStreaming) {
      this.dialogueBox.show(text, true);
    }

    this.isStreaming = false;
    return true;
  }

  skipStreaming() {
    this.isStreaming = false;
  }

  // === Connection Management ===

  cancelDisconnectTimeout() {
    if (this.disconnectTimeout) {
      clearTimeout(this.disconnectTimeout);
      this.disconnectTimeout = null;
    }
  }

  scheduleDisconnect() {
    this.cancelDisconnectTimeout();

    this.disconnectTimeout = setTimeout(() => {
      WebSocketApiService.disconnect();
    }, 5000);
  }
}

export default DialogueManager;
