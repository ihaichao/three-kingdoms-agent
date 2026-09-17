import { Scene } from 'phaser';

export class Preloader extends Scene
{
    constructor ()
    {
        super('Preloader');
    }

    preload ()
    {
        this.load.setPath('assets');

        // General assets
        this.load.image('background', 'talking_philosophers.jpg');
        this.load.image('logo', 'logo.png');

        // Tilesets
        this.load.image("tuxmon-tiles", "tilesets/tuxmon-sample-32px-extruded.png");
        this.load.image("greece-tiles", "tilesets/ancient_greece_tileset.png");
        this.load.image("plant-tiles", "tilesets/plant.png");

        // Tilemap
        this.load.tilemapTiledJSON("map", "tilemaps/philoagents-town.json");

        // Character assets
        this.load.atlas("sophia", "characters/sophia/atlas.png", "characters/sophia/atlas.json");
        this.load.atlas("zhugeliang", "characters/socrates/atlas.png", "characters/socrates/atlas.json");
        this.load.atlas("liubei", "characters/plato/atlas.png", "characters/plato/atlas.json");
        this.load.atlas("caocao", "characters/aristotle/atlas.png", "characters/aristotle/atlas.json");
        this.load.atlas("simayi", "characters/descartes/atlas.png", "characters/descartes/atlas.json");
        this.load.atlas("sunquan", "characters/leibniz/atlas.png", "characters/leibniz/atlas.json");
        this.load.atlas("zhouyu", "characters/turing/atlas.png", "characters/turing/atlas.json");
    }

    create ()
    {
        this.scene.start('MainMenu');
    }
}
