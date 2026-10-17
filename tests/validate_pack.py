#!/usr/bin/env python3
"""Validate PKPack's Minecraft 26.3 data-pack structure and invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REGISTRY = Path(__file__).resolve().parent / "registry" / "26.3"
PACK_FORMAT = 121
EXPECTED_RECIPE_COUNT = 98
EXPECTED_TAG_COUNT = 9
EXPECTED_BLOCK_TAG_COUNT = 1
COLORS = (
    "white",
    "orange",
    "magenta",
    "light_blue",
    "yellow",
    "lime",
    "pink",
    "gray",
    "light_gray",
    "cyan",
    "purple",
    "blue",
    "brown",
    "green",
    "red",
    "black",
)
DYED_MATERIALS = (
    "concrete_powder",
    "glazed_terracotta",
    "stained_glass",
    "stained_glass_pane",
    "terracotta",
)
# Vanilla re-dyes these to any colour, so the pack must not duplicate them.
VANILLA_DYED_MATERIALS = ("bed", "wool")
RECIPE_TYPES = {
    "minecraft:crafting_shaped",
    "minecraft:crafting_shapeless",
    "minecraft:smelting",
    "minecraft:smithing_transform",
}
RESOURCE_LOCATION = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")


def load_registry(kind: str) -> set[str]:
    return set((REGISTRY / f"{kind}.txt").read_text(encoding="utf-8").split())


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.custom_tag_references: set[str] = set()
        self.items = load_registry("item")
        self.blocks = load_registry("block")

    def error(self, path: Path, message: str) -> None:
        self.errors.append(f"{path.relative_to(ROOT)}: {message}")

    def load_json(self, path: Path) -> Any | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.error(path, f"invalid JSON: {exc}")
            return None

        expected = json.dumps(data, indent=4) + "\n"
        if path.read_text(encoding="utf-8") != expected:
            self.error(path, "JSON is not canonically formatted")
        return data

    def validate_resource_location(self, path: Path, value: Any, field: str) -> bool:
        if not isinstance(value, str) or not RESOURCE_LOCATION.fullmatch(value):
            self.error(path, f"{field} must be a namespaced resource location")
            return False
        return True

    def validate_item(self, path: Path, value: Any, field: str) -> None:
        if self.validate_resource_location(path, value, field) and value not in self.items:
            self.error(path, f"{field} is not a Minecraft 26.3 item: {value}")

    def validate_ingredient(self, path: Path, ingredient: Any, field: str) -> None:
        if isinstance(ingredient, list):
            if not ingredient:
                self.error(path, f"{field} alternative list is empty")
            for index, alternative in enumerate(ingredient):
                if isinstance(alternative, str) and alternative.startswith("#"):
                    self.error(path, f"{field}[{index}] tags are not allowed in an alternatives list")
                else:
                    self.validate_item(path, alternative, f"{field}[{index}]")
            return

        if not isinstance(ingredient, str):
            self.error(path, f"{field} must be an item id, '#tag' or list of item ids")
            return

        if ingredient.startswith("#"):
            tag = ingredient[1:]
            if self.validate_resource_location(path, tag, field) and not tag.startswith("minecraft:"):
                self.custom_tag_references.add(tag)
        else:
            self.validate_item(path, ingredient, field)

    def validate_result(self, path: Path, result: Any) -> None:
        if not isinstance(result, dict):
            self.error(path, "result must use the item-stack object format")
            return

        self.validate_item(path, result.get("id"), "result.id")
        if "item" in result:
            self.error(path, "result.item is obsolete; use result.id")
        count = result.get("count", 1)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            self.error(path, "result.count must be a positive integer")

    def validate_recipe(self, path: Path, recipe: Any) -> None:
        if not isinstance(recipe, dict):
            self.error(path, "recipe root must be an object")
            return

        recipe_type = recipe.get("type")
        if recipe_type not in RECIPE_TYPES:
            self.error(path, f"unsupported or unnamespaced recipe type: {recipe_type!r}")
            return

        self.validate_result(path, recipe.get("result"))

        if recipe_type == "minecraft:crafting_shaped":
            pattern = recipe.get("pattern")
            key = recipe.get("key")
            if (
                not isinstance(pattern, list)
                or not 1 <= len(pattern) <= 3
                or not all(isinstance(row, str) for row in pattern)
                or not pattern
                or not 1 <= len(pattern[0]) <= 3
                or any(len(row) != len(pattern[0]) for row in pattern)
            ):
                self.error(path, "pattern must be a rectangular crafting-grid pattern")
                return
            if not isinstance(key, dict):
                self.error(path, "key must be an object")
                return

            used_symbols = set("".join(pattern)) - {" "}
            if used_symbols != set(key):
                self.error(path, "pattern symbols and key entries do not match")
            for symbol, ingredient in key.items():
                self.validate_ingredient(path, ingredient, f"key.{symbol}")

        elif recipe_type == "minecraft:crafting_shapeless":
            ingredients = recipe.get("ingredients")
            if not isinstance(ingredients, list) or not 1 <= len(ingredients) <= 9:
                self.error(path, "ingredients must contain between 1 and 9 entries")
                return
            for index, ingredient in enumerate(ingredients):
                self.validate_ingredient(path, ingredient, f"ingredients[{index}]")

        elif recipe_type == "minecraft:smithing_transform":
            self.validate_ingredient(path, recipe.get("base"), "base")
            for field in ("template", "addition"):
                if field in recipe:
                    self.validate_ingredient(path, recipe[field], field)

        else:
            self.validate_ingredient(path, recipe.get("ingredient"), "ingredient")
            cooking_time = recipe.get("cookingtime")
            if isinstance(cooking_time, bool) or not isinstance(cooking_time, int) or cooking_time < 1:
                self.error(path, "cookingtime must be a positive integer")
            experience = recipe.get("experience")
            if isinstance(experience, bool) or not isinstance(experience, (int, float)) or experience < 0:
                self.error(path, "experience must be a non-negative number")

    def validate_tag(self, path: Path, tag: Any, known: set[str], kind: str) -> list[Any]:
        if not isinstance(tag, dict) or not isinstance(tag.get("values"), list):
            self.error(path, f"{kind} tag must be an object with a values list")
            return []
        if tag.get("replace") is True:
            self.error(path, f"{kind} tag must extend, not replace, the existing tag")
        for index, value in enumerate(tag["values"]):
            field = f"values[{index}]"
            if isinstance(value, str) and value.startswith("#"):
                self.validate_resource_location(path, value[1:], field)
            elif self.validate_resource_location(path, value, field) and value not in known:
                self.error(path, f"{field} is not a Minecraft 26.3 {kind}: {value}")
        return tag["values"]

    def validate_dye_matrix(self, recipes: dict[Path, Any]) -> None:
        base = DATA / "universal_dyeing" / "recipe"
        for material in VANILLA_DYED_MATERIALS:
            for color in COLORS:
                path = base / f"{color}_{material}.json"
                if path.exists():
                    self.error(path, f"vanilla already re-dyes {material}; remove this recipe")

        for material in DYED_MATERIALS:
            all_items = {f"minecraft:{color}_{material}" for color in COLORS}
            for color in COLORS:
                path = base / f"{color}_{material}.json"
                recipe = recipes.get(path)
                if not isinstance(recipe, dict):
                    self.error(path, "missing universal dyeing recipe")
                    continue

                result = recipe.get("result")
                expected_result = f"minecraft:{color}_{material}"
                if not isinstance(result, dict) or result.get("id") != expected_result:
                    self.error(path, f"result must be {expected_result}")
                if not isinstance(result, dict) or result.get("count", 1) != 8:
                    self.error(path, "result count must be 8")

                if color in {"white", "blue", "brown", "black"}:
                    expected_dye = f"#universal_dyeing:dyes/{color}_dye"
                else:
                    expected_dye = f"minecraft:{color}_dye"

                if recipe.get("type") != "minecraft:crafting_shaped":
                    self.error(path, "block dyeing recipes must be shaped")
                if recipe.get("pattern") != ["###", "#O#", "###"]:
                    self.error(path, "block dyeing pattern must surround one dye with eight blocks")
                key = recipe.get("key")
                alternatives = key.get("#") if isinstance(key, dict) else None
                if not isinstance(key, dict) or key.get("O") != expected_dye:
                    self.error(path, "center ingredient must be the target dye")

                if not isinstance(alternatives, list):
                    self.error(path, "first ingredient must list source-color alternatives")
                    continue
                expected_items = all_items - {expected_result}
                if (
                    not all(isinstance(entry, str) for entry in alternatives)
                    or set(alternatives) != expected_items
                    or len(alternatives) != len(expected_items)
                ):
                    self.error(path, "source alternatives must contain each other color exactly once")

    def validate_climbable(self, values: list[Any]) -> None:
        path = DATA / "minecraft" / "tags" / "block" / "climbable.json"
        if "#minecraft:chains" not in values:
            self.error(path, "every chain block must be climbable (#minecraft:chains)")

    def run(self) -> int:
        metadata = self.load_json(ROOT / "pack.mcmeta")
        pack = metadata.get("pack") if isinstance(metadata, dict) else None
        if (
            not isinstance(pack, dict)
            or pack.get("min_format") != PACK_FORMAT
            or pack.get("max_format") != PACK_FORMAT
        ):
            self.error(ROOT / "pack.mcmeta", f"min_format and max_format must be {PACK_FORMAT}")

        for legacy_path in (
            *DATA.glob("*/recipes"),
            *DATA.glob("*/tags/items"),
            *DATA.glob("*/tags/blocks"),
        ):
            self.error(legacy_path, "legacy pre-1.21 directory name")

        recipe_paths = sorted(DATA.glob("*/recipe/**/*.json"))
        tag_paths = sorted(DATA.glob("*/tags/item/**/*.json"))
        block_tag_paths = sorted(DATA.glob("*/tags/block/**/*.json"))
        if len(recipe_paths) != EXPECTED_RECIPE_COUNT:
            self.error(DATA, f"expected {EXPECTED_RECIPE_COUNT} recipes, found {len(recipe_paths)}")
        if len(tag_paths) != EXPECTED_TAG_COUNT:
            self.error(DATA, f"expected {EXPECTED_TAG_COUNT} item tags, found {len(tag_paths)}")
        if len(block_tag_paths) != EXPECTED_BLOCK_TAG_COUNT:
            self.error(DATA, f"expected {EXPECTED_BLOCK_TAG_COUNT} block tags, found {len(block_tag_paths)}")

        recipes: dict[Path, Any] = {}
        for path in recipe_paths:
            recipe = self.load_json(path)
            recipes[path] = recipe
            self.validate_recipe(path, recipe)

        defined_tags: set[str] = set()
        for path in tag_paths:
            tag = self.load_json(path)
            self.validate_tag(path, tag, self.items, "item")
            namespace = path.parts[path.parts.index("data") + 1]
            tag_root = DATA / namespace / "tags" / "item"
            defined_tags.add(f"{namespace}:{path.relative_to(tag_root).with_suffix('').as_posix()}")

        climbable: list[Any] = []
        for path in block_tag_paths:
            values = self.validate_tag(path, self.load_json(path), self.blocks, "block")
            if path == DATA / "minecraft" / "tags" / "block" / "climbable.json":
                climbable = values
        self.validate_climbable(climbable)

        missing_tags = self.custom_tag_references - defined_tags
        for tag in sorted(missing_tags):
            self.errors.append(f"missing item tag definition: {tag}")
        unused_tags = defined_tags - self.custom_tag_references
        for tag in sorted(unused_tags):
            self.errors.append(f"unused item tag definition: {tag}")

        self.validate_dye_matrix(recipes)

        if self.errors:
            print("PKPack validation failed:", file=sys.stderr)
            for error in self.errors:
                print(f"  - {error}", file=sys.stderr)
            return 1

        print(
            f"PKPack validation passed: {len(recipe_paths)} recipes, "
            f"{len(tag_paths)} item tags, {len(block_tag_paths)} block tag, "
            f"pack format {PACK_FORMAT}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(Validator().run())
