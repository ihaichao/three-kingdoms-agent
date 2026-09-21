import { Scene } from 'phaser';
import ApiService from '../services/ApiService';

export class PauseMenu extends Scene {
    constructor() {
        super('PauseMenu');
    }

    create() {
        const overlay = this.add.graphics();
        overlay.fillStyle(0x000000, 0.7);
        overlay.fillRect(0, 0, this.cameras.main.width, this.cameras.main.height);

        const centerX = this.cameras.main.width / 2;
        const centerY = this.cameras.main.height / 2;

        const panel = this.add.graphics();
        // Deep ink background
        panel.fillStyle(0x0e111a, 0.95);
        panel.fillRoundedRect(centerX - 200, centerY - 160, 400, 320, 16);
        // Outer gold border
        panel.lineStyle(2, 0xd4af37, 1);
        panel.strokeRoundedRect(centerX - 200, centerY - 160, 400, 320, 16);
        // Inner bronze line
        panel.lineStyle(1, 0x856828, 0.6);
        panel.strokeRoundedRect(centerX - 194, centerY - 154, 388, 308, 12);

        this.add.text(centerX, centerY - 115, '游戏暂停', {
            fontSize: '28px',
            fontFamily: '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif',
            color: '#ffeed0',
            fontStyle: 'bold'
        }).setOrigin(0.5);

        const buttonY = centerY - 45;
        const buttonSpacing = 68;

        this.createButton(centerX, buttonY, '继续游戏', () => {
            this.resumeGame();
        });

        this.createButton(centerX, buttonY + buttonSpacing, '返回主界面', () => {
            this.returnToMainMenu();
        });

        this.createButton(centerX, buttonY + buttonSpacing * 2, '重置对话记忆', () => {
            this.resetGame();
        });

        this.input.keyboard.on('keydown-ESC', () => {
            this.resumeGame();
        });
    }

    createButton(x, y, text, callback) {
        const buttonWidth = 260;
        const buttonHeight = 48;
        const cornerRadius = 12;

        const shadow = this.add.graphics();
        shadow.fillStyle(0x000000, 0.5);
        shadow.fillRoundedRect(x - buttonWidth / 2 + 3, y - buttonHeight / 2 + 3, buttonWidth, buttonHeight, cornerRadius);

        const button = this.add.graphics();
        button.fillStyle(0x7a1818, 1);
        button.lineStyle(2, 0xd4af37, 1);
        button.fillRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
        button.strokeRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
        button.setInteractive(
            new Phaser.Geom.Rectangle(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight),
            Phaser.Geom.Rectangle.Contains
        );

        const buttonText = this.add.text(x, y, text, {
            fontSize: '20px',
            fontFamily: '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif',
            color: '#ffeed0',
            fontStyle: 'bold'
        }).setOrigin(0.5);

        button.on('pointerover', () => {
            button.clear();
            button.fillStyle(0x9a2424, 1);
            button.lineStyle(2, 0xffe066, 1);
            button.fillRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
            button.strokeRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
            buttonText.y -= 2;
        });

        button.on('pointerout', () => {
            button.clear();
            button.fillStyle(0x7a1818, 1);
            button.lineStyle(2, 0xd4af37, 1);
            button.fillRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
            button.strokeRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
            buttonText.y += 2;
        });

        button.on('pointerdown', callback);

        return { button, shadow, text: buttonText };
    }

    resumeGame() {
        this.scene.resume('Game');
        this.scene.stop();
    }

    returnToMainMenu() {
        this.scene.stop('Game');
        this.scene.start('MainMenu');
    }

    async resetGame() {
        try {
            await ApiService.resetMemory();

            this.scene.stop('Game');
            this.scene.start('Game');
            this.scene.stop();
        } catch (error) {
            console.error('Failed to reset game:', error);

            const centerX = this.cameras.main.width / 2;
            const centerY = this.cameras.main.height / 2 + 120;

            const errorText = this.add.text(centerX, centerY, '重置记忆失败，请稍后重试', {
                fontSize: '16px',
                fontFamily: '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif',
                color: '#FF6B6B'
            }).setOrigin(0.5);

            this.time.delayedCall(3000, () => {
                errorText.destroy();
            });
        }
    }
}
