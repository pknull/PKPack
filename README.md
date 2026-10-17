# PKPack

A Minecraft data pack that adds "missing" crafting recipes for quality-of-life improvements.

## Features

### Universal Dyeing
Re-dye supported colored blocks to any other color:
- Concrete powder
- Stained glass and glass panes
- Terracotta and glazed terracotta

Wool and beds are left to vanilla, which re-dyes them to any color.

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

### Smithing Recipes
- **Gilded Blackstone**: Blackstone + gold ingot at a smithing table, no template

### Climbable Blocks
Every chain block (`#minecraft:chains`) and bamboo can be climbed like a ladder.

## Installation

1. Download or clone this repository
2. Place `pack.mcmeta` and `data/` in a `PKPack` folder inside your world's `datapacks` folder,
   or build a zip with `git archive --format=zip -o PKPack.zip HEAD pack.mcmeta data`:
   - **Singleplayer**: `.minecraft/saves/<world>/datapacks/`
   - **Server**: `<server>/world/datapacks/`
3. Run `/reload` in-game or restart the world

## Compatibility

- **Minecraft Java Edition**: 26.3 (tested on a 26.3 Fabric server)
- **Data Pack Format**: 121 (`min_format`/`max_format`)

The last 1.21.1 release (pack format 48) is commit `8449846`.

## Recipe Count

- 98 recipes across 10 namespaces
- 9 item tag files for ingredient alternatives
- 1 block tag (`minecraft:climbable`)

## Validation

Run the repository's structural and recipe-invariant checks before packaging. Item and block
ids are checked against the 26.3 registry lists in `tests/registry/26.3/`:

```bash
python3 tests/validate_pack.py
```

## License

[MIT License](LICENSE)
