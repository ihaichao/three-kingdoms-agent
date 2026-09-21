class DialogueBox {
    constructor(scene, config = {}) {
        this.scene = scene;
        this.awaitingInput = false;

        const cameraWidth = scene.cameras?.main?.width || scene.game?.config?.width || 1280;
        const cameraHeight = scene.cameras?.main?.height || scene.game?.config?.height || 720;

        const defaultWidth = Math.min(cameraWidth - 80, 1140);
        const defaultHeight = 220;
        const defaultX = Math.round((cameraWidth - defaultWidth) / 2);
        const defaultY = cameraHeight - defaultHeight - 30;

        const {
            x = defaultX,
            y = defaultY,
            width = defaultWidth,
            height = defaultHeight,
            depth = 30
        } = config;

        this.x = x;
        this.y = y;
        this.width = width;
        this.height = height;

        // Portrait layout
        const portraitSize = 176;
        const portraitPadding = 18;
        const portraitX = x + portraitPadding;
        const portraitY = y + Math.round((height - portraitSize) / 2);

        // Text layout (placed right of portrait)
        const textX = portraitX + portraitSize + 22;
        const textY = y + 22;
        const textWidth = (x + width) - textX - 26;
        const textHeight = height - 44;

        this.textInputX = textX;
        this.textInputY = textY;
        this.textInputWidth = textWidth;
        this.textInputHeight = textHeight;

        // 1. Main Background Graphics (Dark Ink Blue with Double Gold Borders)
        const bgGraphics = scene.add.graphics();
        // Deep ink background
        bgGraphics.fillStyle(0x0e111a, 0.92);
        bgGraphics.fillRoundedRect(x, y, width, height, 12);
        // Outer gold border
        bgGraphics.lineStyle(2, 0xd4af37, 1);
        bgGraphics.strokeRoundedRect(x, y, width, height, 12);
        // Inner subtle bronze border
        bgGraphics.lineStyle(1, 0x856828, 0.7);
        bgGraphics.strokeRoundedRect(x + 4, y + 4, width - 8, height - 8, 9);

        // 2. Character Name Tag (Classical Vermilion & Gold Plate)
        const nameplateWidth = 170;
        const nameplateHeight = 36;
        const nameplateX = portraitX;
        const nameplateY = y - 24;

        const nameplateGraphics = scene.add.graphics();
        nameplateGraphics.fillStyle(0x7a1818, 0.95);
        nameplateGraphics.fillRoundedRect(nameplateX, nameplateY, nameplateWidth, nameplateHeight, 6);
        nameplateGraphics.lineStyle(2, 0xd4af37, 1);
        nameplateGraphics.strokeRoundedRect(nameplateX, nameplateY, nameplateWidth, nameplateHeight, 6);

        this.nameText = scene.add.text(nameplateX + nameplateWidth / 2, nameplateY + nameplateHeight / 2, '三国名将', {
            font: 'bold 20px "PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif',
            fill: '#ffeed0'
        }).setOrigin(0.5);

        // 3. Portrait Image & Frame
        const portraitBg = scene.add.graphics();
        portraitBg.fillStyle(0x1a202c, 1);
        portraitBg.fillRect(portraitX, portraitY, portraitSize, portraitSize);

        this.portrait = scene.add.image(portraitX, portraitY, 'portrait-zhugeliang')
            .setOrigin(0, 0)
            .setDisplaySize(portraitSize, portraitSize);

        if (this.portrait.texture) {
            this.portrait.texture.setFilter(Phaser.Textures.FilterMode.LINEAR);
        }

        const portraitBorder = scene.add.graphics();
        portraitBorder.lineStyle(2, 0xd4af37, 1);
        portraitBorder.strokeRect(portraitX, portraitY, portraitSize, portraitSize);
        // Inner subtle border
        portraitBorder.lineStyle(1, 0x856828, 0.6);
        portraitBorder.strokeRect(portraitX + 2, portraitY + 2, portraitSize - 4, portraitSize - 4);

        this.text = scene.add.text(textX, textY, '', {
            font: '32px "PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif',
            fill: '#ffffff',
            lineSpacing: 12,
            wordWrap: { width: textWidth, useAdvancedWrap: true }
        });

        // 4b. Loading Effect (Classical Gold / Ink Thinking Animation - Subtitle removed)
        this.loadingContainer = scene.add.container(textX, textY + 6);
        this.isLoading = false;
        this.loadingTweens = [];

        this.loadingTitle = scene.add.text(0, 0, '正在沉吟思索中', {
            font: 'bold 12px "PingFang SC", "Microsoft YaHei", "SimHei", sans-serif',
            fill: '#ffd700'
        });

        this.loadingDots = [];
        for (let i = 0; i < 3; i++) {
            const dot = scene.add.circle(0, 0, 3, 0xd4af37, 1);
            this.loadingDots.push(dot);
        }

        this.loadingContainer.add([
            this.loadingTitle,
            ...this.loadingDots
        ]);
        this.loadingContainer.setVisible(false);

        // 5. Container grouping
        this.container = scene.add.container(0, 0, [
            bgGraphics,
            nameplateGraphics,
            this.nameText,
            portraitBg,
            this.portrait,
            portraitBorder,
            this.text,
            this.loadingContainer
        ]);
        this.container.setDepth(depth);
        this.container.setScrollFactor(0);
        this.hide();
    }

    setCharacter(character) {
        if (!character) return;

        // Set character name
        if (character.name) {
            this.nameText.setText(`【 ${character.name} 】`);
        }

        // Set character portrait texture
        const portraitKey = `portrait-${character.id}`;
        if (this.scene.textures.exists(portraitKey)) {
            this.portrait.setTexture(portraitKey);
            if (this.portrait.texture) {
                this.portrait.texture.setFilter(Phaser.Textures.FilterMode.LINEAR);
            }
            this.portrait.setVisible(true);
        }
    }

    showLoading(characterName = '名将') {
        this.isLoading = true;
        this.text.setText('');
        this.loadingTitle.setText(`【${characterName}】正在沉吟思索中`);

        // Dynamically adjust dots position according to character name length and center vertically
        const titleWidth = this.loadingTitle.width || 180;
        const centerY = Math.round((this.loadingTitle.height || 16) / 2);
        const dotsStartX = titleWidth + 10;
        this.loadingDots.forEach((dot, i) => {
            dot.setPosition(dotsStartX + i * 11, centerY);
            dot.setAlpha(0.35);
            dot.setScale(0.85);
        });

        // Stop any old tweens
        this.stopLoadingTweens();

        // Staggered bounce and glow animation on dots
        this.loadingDots.forEach((dot, i) => {
            const tween = this.scene.tweens.add({
                targets: dot,
                alpha: { from: 0.35, to: 1.0 },
                scale: { from: 0.85, to: 1.15 },
                y: centerY - 3,
                duration: 400,
                yoyo: true,
                repeat: -1,
                delay: i * 130,
                ease: 'Sine.easeInOut'
            });
            this.loadingTweens.push(tween);
        });

        this.loadingContainer.setVisible(true);
        this.container.setVisible(true);
        this.awaitingInput = true;
    }

    stopLoadingTweens() {
        if (this.loadingTweens && this.loadingTweens.length > 0) {
            this.loadingTweens.forEach(t => {
                try {
                    if (t && typeof t.stop === 'function') {
                        t.stop();
                    }
                } catch (e) {}
            });
            this.loadingTweens = [];
        }
    }

    hideLoading() {
        this.isLoading = false;
        this.stopLoadingTweens();
        if (this.loadingContainer) {
            this.loadingContainer.setVisible(false);
        }
    }

    show(message, awaitInput = false, character = null) {
        this.hideLoading();
        if (character) {
            this.setCharacter(character);
        }
        this.text.setText(message);
        this.container.setVisible(true);
        this.awaitingInput = awaitInput;
    }

    hide() {
        this.hideLoading();
        this.container.setVisible(false);
        this.awaitingInput = false;
    }

    isVisible() {
        return this.container.visible;
    }

    isAwaitingInput() {
        return this.awaitingInput;
    }
}

export default DialogueBox;
