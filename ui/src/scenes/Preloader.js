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
        this.load.image('background', 'three_kingdoms_courtyard.jpg');
        this.load.image('logo', 'logo.png');

        // Tilesets
        this.load.image("tuxmon-tiles", "tilesets/tuxmon-sample-32px-extruded.png");
        this.load.image("greece-tiles", "tilesets/ancient_greece_tileset.png");
        this.load.image("plant-tiles", "tilesets/plant.png");

        // Tilemap
        this.load.tilemapTiledJSON("map", "tilemaps/philoagents-town.json");

        // Character assets (Three Kingdoms Remastered)
        this.load.atlas("sophia", "characters/tk_hero/atlas.png", "characters/tk_hero/atlas.json");
        this.load.atlas("zhugeliang", "characters/tk_zhugeliang/atlas.png", "characters/tk_zhugeliang/atlas.json");
        this.load.atlas("liubei", "characters/tk_liubei/atlas.png", "characters/tk_liubei/atlas.json");
        this.load.atlas("caocao", "characters/tk_caocao/atlas.png", "characters/tk_caocao/atlas.json");
        this.load.atlas("simayi", "characters/tk_simayi/atlas.png", "characters/tk_simayi/atlas.json");
        this.load.atlas("sunquan", "characters/tk_sunquan/atlas.png", "characters/tk_sunquan/atlas.json");
        this.load.atlas("zhouyu", "characters/tk_zhouyu/atlas.png", "characters/tk_zhouyu/atlas.json");

        // Character portraits
        this.load.image("portrait-zhugeliang", "portraits/zhugeliang.jpg");
        this.load.image("portrait-liubei", "portraits/liubei.jpg");
        this.load.image("portrait-caocao", "portraits/caocao.jpg");
        this.load.image("portrait-simayi", "portraits/simayi.jpg");
        this.load.image("portrait-sunquan", "portraits/sunquan.jpg");
        this.load.image("portrait-zhouyu", "portraits/zhouyu.jpg");
    }

    create ()
    {
        this.scene.start('MainMenu');
    }
}
