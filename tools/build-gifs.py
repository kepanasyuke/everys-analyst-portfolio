"""Собирает GIF из кадров, снятых tools/record-demos.mjs."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

FRAMES = Path("assets/tmp")
OUT = Path("assets")
WIDTH = 900
DURATION = 180
COLORS = 128
SCENARIOS = ("demo-sale", "demo-return", "demo-reorder")


def frame_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("f*.png"))


def resized(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    return image.resize((WIDTH, round(image.height * WIDTH / image.width)), Image.LANCZOS)


def save_gif(images: list[Image.Image], name: str) -> int:
    return writing(quantized(images), name)


def quantized(images: list[Image.Image]) -> list[Image.Image]:
    return [image.quantize(colors=COLORS, method=Image.FASTOCTREE) for image in images]


def writing(frames: list[Image.Image], name: str) -> int:
    frames[0].save(OUT / f"{name}.gif", save_all=True, append_images=frames[1:], duration=DURATION, loop=0, optimize=True, disposal=2)
    return len(frames)


def build(name: str) -> int:
    return save_gif([resized(path) for path in frame_files(FRAMES / name)], name)


def main() -> int:
    for name in SCENARIOS:
        count = build(name)
        size = (OUT / f"{name}.gif").stat().st_size
        print(f"{name}: {count} кадров, {size / 1024:.0f} КБ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
