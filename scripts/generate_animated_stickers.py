from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "assets" / "lulu_stickers"
OUTPUT_DIR = ROOT / "assets" / "lulu_animated_stickers"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source in sorted(SOURCE_DIR.glob("*.webp")):
        target = OUTPUT_DIR / f"{source.stem}.gif"
        make_bounce_gif(source, target)
        print(target.relative_to(ROOT))


def make_bounce_gif(source: Path, target: Path) -> None:
    image = first_frame(source)
    image.thumbnail((128, 128), Image.Resampling.LANCZOS)
    frames = []
    transforms = [
        (0, 0, 1.00, 0),
        (-4, -6, 1.04, -4),
        (0, -10, 1.07, 0),
        (4, -6, 1.04, 4),
        (0, 0, 1.00, 0),
        (0, 4, 0.97, 0),
    ]
    for x, y, scale, rotation in transforms:
        canvas = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        size = max(1, int(128 * scale))
        frame = image.resize((size, size), Image.Resampling.LANCZOS).rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
        left = (160 - frame.width) // 2 + x
        top = (160 - frame.height) // 2 + y
        canvas.alpha_composite(frame, (left, top))
        frames.append(canvas)
    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=0,
        disposal=2,
        transparency=0,
    )


def first_frame(path: Path) -> Image.Image:
    with Image.open(path) as image:
        frame = next(ImageSequence.Iterator(image)).convert("RGBA")
    return frame


if __name__ == "__main__":
    main()
