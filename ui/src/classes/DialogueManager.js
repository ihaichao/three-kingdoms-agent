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
    const configWidth = this.scene.game.config.width || 1280;
    const configHeight = this.scene.game.config.height || 720;
    const scaleX = rect.width / configWidth;
    const scaleY = rect.height / configHeight;

    const boxX = (this.dialogueBox && typeof this.dialogueBox.textInputX === 'number')
      ? this.dialogueBox.textInputX
      : 280;
    const boxY = (this.dialogueBox && typeof this.dialogueBox.textInputY === 'number')
      ? this.dialogueBox.textInputY
      : 500;
    const boxWidth = (this.dialogueBox && typeof this.dialogueBox.textInputWidth === 'number')
      ? this.dialogueBox.textInputWidth
      : 800;
    const boxHeight = (this.dialogueBox && typeof this.dialogueBox.textInputHeight === 'number')
      ? this.dialogueBox.textInputHeight
      : 180;

    const x = rect.left + boxX * scaleX;
    const y = rect.top + boxY * scaleY;
    const width = Math.max(100, boxWidth * scaleX);
    const height = Math.max(50, boxHeight * scaleY);
    const fontSize = Math.max(24, Math.round(38 * scaleY));

    this.domInput.style.left = `${x}px`;
    this.domInput.style.top = `${y}px`;
    this.domInput.style.width = `${width}px`;
    this.domInput.style.height = `${height}px`;
    this.domInput.style.fontSize = `${fontSize}px`;
    this.domInput.style.lineHeight = '1.45';
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
      const charName = this.activePhilosopher?.name || '名将';
      this.disableInput();
      this.stopCursorBlink();
      this.dialogueBox.showLoading(charName);

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
    await new Promise(resolve => setTimeout(resolve, 600));
    this.dialogueBox.hideLoading();
    this.dialogueBox.show('', true);
    await this.streamText(apiResponse);
  }

  filterThinkingContent(text) {
    if (!text) return '';
    // 1. Remove completely closed <thinking>...</thinking>, <thought>...</thought>, <reasoning>...</reasoning>, <think>...</think>
    let clean = text.replace(/<(thinking|thought|reasoning|think)>[\s\S]*?<\/\1>/gi, '');
    // 2. Remove open/in-progress <thinking>... that hasn't closed yet
    clean = clean.replace(/<(thinking|thought|reasoning|think)>[\s\S]*$/gi, '');
    // 3. Remove trailing incomplete tags like "<think..." or "</think..."
    clean = clean.replace(/<\/?(?:thinking|thought|reasoning|think)?[^>]*$/gi, '');
    return clean.trimStart();
  }

  async handleWebSocketMessage() {
    const charName = this.activePhilosopher?.name || '名将';
    this.dialogueBox.showLoading(charName);
    this.isStreaming = true;
    this.streamingText = '';
    this.rawStreamedText = '';

    try {
      await this.processWebSocketMessage();
    } catch (error) {
      console.error('WebSocket error:', error);
      await this.fallbackToRegularApi();
    } finally {
      this.dialogueBox.hideLoading();
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
        this.rawStreamedText = (this.rawStreamedText || '') + chunk;
        const cleanText = this.filterThinkingContent(this.rawStreamedText);

        // Only hide loading and show text once the thinking tag has closed and actual dialogue begins!
        if (cleanText.length > 0) {
          if (this.dialogueBox.isLoading) {
            this.dialogueBox.hideLoading();
          }
          this.streamingText = cleanText;
          this.dialogueBox.show(this.streamingText, true);
        }
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
    this.dialogueBox.hideLoading();
    this.isStreaming = false;
    const cleanText = this.filterThinkingContent(this.rawStreamedText || this.streamingText);
    this.streamingText = cleanText || '（名将沉吟良久，未置可否）';
    this.dialogueBox.show(this.streamingText, true);
  }

  async fallbackToRegularApi() {
    const charName = this.activePhilosopher?.name || '名将';
    this.dialogueBox.showLoading(charName);
    try {
      const apiResponse = await ApiService.sendMessage(
        this.activePhilosopher,
        this.currentMessage
      );
      this.dialogueBox.hideLoading();
      const cleanResponse = this.filterThinkingContent(apiResponse);
      await this.streamText(cleanResponse);
    } catch (err) {
      this.dialogueBox.hideLoading();
      this.dialogueBox.show('（与名将对话连接中断，请稍后再试）', true);
    }
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

    if (this.dialogueBox && typeof this.dialogueBox.setCharacter === 'function') {
      this.dialogueBox.setCharacter(philosopher);
    }
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
