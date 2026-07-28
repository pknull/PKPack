#!/usr/bin/env python3
"""Validate PKPack's Minecraft 1.21.1 data-pack structure and invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PACK_FORMAT = 48
EXPECTED_RECIPE_COUNT = 129
EXPECTED_TAG_COUNT = 9
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
    "bed",
    "concrete_powder",
    "glazed_terracotta",
    "stained_glass",
    "stained_glass_pane",
    "terracotta",
    "wool",
)
RECIPE_TYPES = {
    "minecraft:crafting_shaped",
    "minecraft:crafting_shapeless",
    "minecraft:smelting",
}
RESOURCE_LOCATION = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.custom_tag_references: set[str] = set()

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

    def validate_resource_location(self, path: Path, value: Any, field: str) -> None:
        if not isinstance(value, str) or not RESOURCE_LOCATION.fullmatch(value):
            self.error(path, f"{field} must be a namespaced resource location")

    def validate_ingredient(self, path: Path, ingredient: Any, field: str) -> None:
        if isinstance(ingredient, list):
            if not ingredient:
                self.error(path, f"{field} alternative list is empty")
            for index, alternative in enumerate(ingredient):
                self.validate_ingredient(path, alternative, f"{field}[{index}]")
            return

        if not isinstance(ingredient, dict):
            self.error(path, f"{field} must be an ingredient object or alternatives list")
            return

        keys = set(ingredient)
        if keys not in ({"item"}, {"tag"}):
            self.error(path, f"{field} must contain exactly one of 'item' or 'tag'")
            return

        key = next(iter(keys))
        value = ingredient[key]
        self.validate_resource_location(path, value, f"{field}.{key}")
        if key == "tag" and isinstance(value, str) and not value.startswith("minecraft:"):
            self.custom_tag_references.add(value)

    def validate_result(self, path: Path, result: Any) -> None:
        if not isinstance(result, dict):
            self.error(path, "result must use the Minecraft 1.21 item-stack object format")
            return

        self.validate_resource_location(path, result.get("id"), "result.id")
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

        else:
            self.validate_ingredient(path, recipe.get("ingredient"), "ingredient")
            cooking_time = recipe.get("cookingtime")
            if isinstance(cooking_time, bool) or not isinstance(cooking_time, int) or cooking_time < 1:
                self.error(path, "cookingtime must be a positive integer")
            experience = recipe.get("experience")
            if isinstance(experience, bool) or not isinstance(experience, (int, float)) or experience < 0:
                self.error(path, "experience must be a non-negative number")

    def validate_tag(self, path: Path, tag: Any) -> None:
        if not isinstance(tag, dict) or not isinstance(tag.get("values"), list):
            self.error(path, "item tag must be an object with a values list")
            return
        for index, value in enumerate(tag["values"]):
            self.validate_resource_location(path, value, f"values[{index}]")

    def validate_dye_matrix(self, recipes: dict[Path, Any]) -> None:
        base = DATA / "universal_dyeing" / "recipe"
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
                expected_count = 1 if material in {"bed", "wool"} else 8
                if not isinstance(result, dict) or result.get("count", 1) != expected_count:
                    self.error(path, f"result count must be {expected_count}")

                if color in {"white", "blue", "brown", "black"}:
                    expected_dye = {"tag": f"universal_dyeing:dyes/{color}_dye"}
                else:
                    expected_dye = {"item": f"minecraft:{color}_dye"}

                if material in {"bed", "wool"}:
                    if recipe.get("type") != "minecraft:crafting_shapeless":
                        self.error(path, "bed and wool dyeing recipes must be shapeless")
                    ingredients = recipe.get("ingredients")
                    alternatives = (
                        ingredients[0] if isinstance(ingredients, list) and ingredients else None
                    )
                    expected_dye_count = 3 if material == "bed" else 1
                    if (
                        not isinstance(ingredients, list)
                        or ingredients[1:] != [expected_dye] * expected_dye_count
                    ):
                        self.error(path, f"dye ingredients must contain {expected_dye_count} target dye(s)")
                else:
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
                actual_items = {
                    entry.get("item")
                    for entry in alternatives
                    if isinstance(entry, dict) and set(entry) == {"item"}
                }
                expected_items = all_items - {expected_result}
                if actual_items != expected_items or len(alternatives) != len(expected_items):
                    self.error(path, "source alternatives must contain each other color exactly once")

    def run(self) -> int:
        metadata = self.load_json(ROOT / "pack.mcmeta")
        pack = metadata.get("pack") if isinstance(metadata, dict) else None
        if not isinstance(pack, dict) or pack.get("pack_format") != PACK_FORMAT:
            self.error(ROOT / "pack.mcmeta", f"pack_format must be {PACK_FORMAT}")

        for legacy_path in (*DATA.glob("*/recipes"), *DATA.glob("*/tags/items")):
            self.error(legacy_path, "legacy pre-1.21 directory name")

        recipe_paths = sorted(DATA.glob("*/recipe/**/*.json"))
        tag_paths = sorted(DATA.glob("*/tags/item/**/*.json"))
        if len(recipe_paths) != EXPECTED_RECIPE_COUNT:
            self.error(DATA, f"expected {EXPECTED_RECIPE_COUNT} recipes, found {len(recipe_paths)}")
        if len(tag_paths) != EXPECTED_TAG_COUNT:
            self.error(DATA, f"expected {EXPECTED_TAG_COUNT} item tags, found {len(tag_paths)}")

        recipes: dict[Path, Any] = {}
        for path in recipe_paths:
            recipe = self.load_json(path)
            recipes[path] = recipe
            self.validate_recipe(path, recipe)

        defined_tags: set[str] = set()
        for path in tag_paths:
            tag = self.load_json(path)
            self.validate_tag(path, tag)
            namespace = path.parts[path.parts.index("data") + 1]
            tag_root = DATA / namespace / "tags" / "item"
            defined_tags.add(f"{namespace}:{path.relative_to(tag_root).with_suffix('').as_posix()}")

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
            f"{len(tag_paths)} item tags, pack format {PACK_FORMAT}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(Validator().run())
