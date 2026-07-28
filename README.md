# PKPack

A Minecraft data pack that adds "missing" crafting recipes for quality-of-life improvements.

## Features

### Universal Dyeing
Re-dye supported colored blocks to any other color:
- Wool, beds, concrete powder
- Stained glass and glass panes
- Terracotta and glazed terracotta

Stained glass, glass panes, and terracotta can also be stripped back to their
uncolored variants.

### Material Conversions
- **Cobblestone to Gravel**: 1 cobblestone → 2 gravel
- **Gravel to Sand**: 1 gravel → 2 sand
- **Sand + Water to Clay**: Combine sand and a water bucket to craft clay

> **Note:** Material multiplication (1:2 ratios) is intentional for gameplay balance.

### Coral Blocks
Craft coral blocks from coral items (tube, brain, bubble, fire, horn).

### Sandstone Dyeing
Convert regular sandstone variants to red sandstone variants using red dye.

### Uncraftable Items
- **Nether Wart Block**: Reverse-craft back into 9 nether wart
- **Enchanted Golden Apple**: Classic "Notch apple" recipe (8 gold blocks + golden apple)

### Smelting Recipes
- **Rotten Flesh to Leather**: Smelt rotten flesh in a furnace to get leather

## Installation

1. Download or clone this repository
2. Place the `PKPack` folder into your Minecraft world's `datapacks` folder:
   - **Singleplayer**: `.minecraft/saves/<world>/datapacks/`
   - **Server**: `<server>/world/datapacks/`
3. Run `/reload` in-game or restart the world

## Compatibility

- **Minecraft Java Edition**: 1.21–1.21.1 (tested on 1.21.1)
- **Data Pack Format**: 48

## Recipe Count

- 129 recipes across 9 namespaces
- 9 item tag files for ingredient alternatives

## Validation

Run the repository's structural and recipe-invariant checks before packaging:

```bash
python3 tests/validate_pack.py
```

## License

[MIT License](LICENSE)
