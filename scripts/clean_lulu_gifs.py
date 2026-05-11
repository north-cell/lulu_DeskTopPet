from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
GIF_DIR = ROOT / "assets" / "lulu_transparent_gifs"


def main() -> None:
    for path in sorted(GIF_DIR.glob("*.gif")):
        clean_gif(path)
        print(path.relative_to(ROOT))


def clean_gif(path: Path) -> None:
    with Image.open(path) as image:
        frames = [clean_frame(frame.convert("RGBA")) for frame in ImageSequence.Iterator(image)]
        durations = [frame.info.get("duration", image.info.get("duration", 90)) for frame in ImageSequence.Iterator(image)]
        loop = image.info.get("loop", 0)

    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop,
        disposal=2,
        transparency=0,
    )


def clean_frame(frame: Image.Image) -> Image.Image:
    arr = np.array(frame)
    height, width = arr.shape[:2]

    # The source GIFs have occasional gray/white residue between Lulu's feet.
    # Restrict cleanup to the lower center gap so hands, clothes, and face stay untouched.
    y0, y1 = int(height * 0.78), height
    x0, x1 = int(width * 0.36), int(width * 0.64)
    region = arr[y0:y1, x0:x1, :]
    r = region[:, :, 0].astype(np.int16)
    g = region[:, :, 1].astype(np.int16)
    b = region[:, :, 2].astype(np.int16)
    alpha = region[:, :, 3]

    saturation_span = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    warm_lulu = (r > 145) & (g > 70) & (b < 145) & ((r - b) > 40)
    gray_or_white_residue = (alpha > 0) & (saturation_span < 55) & ~warm_lulu
    pale_floor_residue = (alpha > 0) & (r > 160) & (g > 145) & (b > 135) & ~warm_lulu
    remove = gray_or_white_residue | pale_floor_residue

    region[remove, 3] = 0
    arr[y0:y1, x0:x1, :] = region
    return Image.fromarray(arr, "RGBA")


if __name__ == "__main__":
    main()
