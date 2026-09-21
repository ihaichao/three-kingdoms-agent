import { Game } from './scenes/Game';
import { MainMenu } from './scenes/MainMenu';
import { Preloader } from './scenes/Preloader';
import { PauseMenu } from './scenes/PauseMenu';

const config = {
    type: Phaser.AUTO,
    width: 1280,
    height: 720,
    parent: 'game-container',
    scale: {
        mode: Phaser.Scale.ENVELOP,
        autoCenter: Phaser.Scale.CENTER_BOTH
    },
    scene: [
        Preloader,
        MainMenu,
        Game,
        PauseMenu
    ],
    physics: {
        default: "arcade",
        arcade: {
            gravity: { y: 0 },
        },
    },
    render: {
        antialias: true,
        antialiasGL: true,
        roundPixels: true
    },
};

export default new Phaser.Game(config);
