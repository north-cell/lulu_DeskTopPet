from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "lulu_source" / "lulu_13.webp"
OUT = ROOT / "assets" / "lulu_character"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = extract_lulu(SOURCE)
    base.save(OUT / "base.png")
    make_frames(base)
    print((OUT / "base.png").resolve())


def extract_lulu(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    arr = np.array(image)
    r, g, b, _ = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

    # Lulu is a contiguous yellow/orange character with a warm snout.
    warm = (r > 145) & (g > 75) & (b < 145) & ((r.astype(int) - b.astype(int)) > 45) & ((g.astype(int) - b.astype(int)) > 35)
    yellow = (r > 170) & (g > 135) & (b < 130)
    orange = (r > 175) & (g > 80) & (g < 170) & (b < 105)
    mask = warm | yellow | orange
    mask &= lulu_shape_mask(image.size)

    component = component_from_seed(mask, seed=(int(image.height * 0.55), int(image.width * 0.58)))
    component = close_mask(component, radius=4)
    component = fill_holes(component)

    alpha = Image.fromarray((component.astype(np.uint8) * 255), "L")
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))
    cutout = Image.new("RGBA", image.size, (0, 0, 0, 0))
    cutout.alpha_composite(image)
    cutout.putalpha(alpha)
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError("Could not extract Lulu character")
    cutout = cutout.crop(expand_bbox(bbox, image.size, 18))
    cutout = trim_transparent(cutout)
    cutout.thumbnail((260, 260), Image.Resampling.LANCZOS)
    return cutout


def component_from_seed(mask: np.ndarray, seed: tuple[int, int]) -> np.ndarray:
    height, width = mask.shape
    sy, sx = nearest_mask_point(mask, seed)
    result = np.zeros(mask.shape, dtype=bool)
    queue: deque[tuple[int, int]] = deque([(sy, sx)])
    result[sy, sx] = True
    while queue:
        cy, cx = queue.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not result[ny, nx]:
                result[ny, nx] = True
                queue.append((ny, nx))
    return result


def nearest_mask_point(mask: np.ndarray, seed: tuple[int, int]) -> tuple[int, int]:
    height, width = mask.shape
    sy, sx = seed
    sy = max(0, min(height - 1, sy))
    sx = max(0, min(width - 1, sx))
    if mask[sy, sx]:
        return sy, sx
    for radius in range(1, max(width, height)):
        y0, y1 = max(0, sy - radius), min(height - 1, sy + radius)
        x0, x1 = max(0, sx - radius), min(width - 1, sx + radius)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if mask[y, x]:
                    return y, x
    raise RuntimeError("No Lulu-colored seed point found")


def largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    best: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            points: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            while queue:
                cy, cx = queue.popleft()
                points.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))
            if len(points) > len(best):
                best = points
    result = np.zeros(mask.shape, dtype=bool)
    for y, x in best:
        result[y, x] = True
    return result


def lulu_shape_mask(size: tuple[int, int]) -> np.ndarray:
    width, height = size
    sx = width / 512
    sy = height / 512
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)

    def box(x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int, int]:
        return round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy)

    draw.ellipse(box(112, 78, 466, 334), fill=255)     # head and snout
    draw.ellipse(box(228, 27, 309, 108), fill=255)     # top knot
    draw.ellipse(box(87, 117, 176, 205), fill=255)     # left ear
    draw.ellipse(box(389, 123, 468, 211), fill=255)    # right ear
    draw.rounded_rectangle(box(146, 260, 405, 459), radius=round(56 * sx), fill=255)
    draw.ellipse(box(116, 278, 194, 435), fill=255)    # left arm
    draw.ellipse(box(362, 272, 449, 429), fill=255)    # right arm
    draw.ellipse(box(169, 402, 251, 500), fill=255)    # left leg
    draw.ellipse(box(306, 405, 392, 500), fill=255)    # right leg
    return np.array(mask) > 0


def close_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    image = Image.fromarray((mask.astype(np.uint8) * 255), "L")
    image = image.filter(ImageFilter.MaxFilter(radius * 2 + 1))
    image = image.filter(ImageFilter.MinFilter(radius * 2 + 1))
    return np.array(image) > 0


def fill_holes(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    outside = np.zeros(mask.shape, dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        for y in (0, height - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if not mask[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    while queue:
        cy, cx = queue.popleft()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < height and 0 <= nx < width and not mask[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                queue.append((ny, nx))
    return mask | ~outside


def expand_bbox(bbox: tuple[int, int, int, int], size: tuple[int, int], pad: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    width, height = size
    return max(0, left - pad), max(0, top - pad), min(width, right + pad), min(height, bottom + pad)


def trim_transparent(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    return image.crop(bbox) if bbox else image


def make_frames(base: Image.Image) -> None:
    specs = {
        "idle": [(1.00, 1.00, 0, 0, 0), (1.01, 0.99, 0, 1, 0), (1.00, 1.00, 0, 0, 0), (0.99, 1.01, 0, -1, 0)],
        "walk": [(1.00, 1.00, -3, 0, -3), (1.03, 0.98, 0, -4, 2), (1.00, 1.00, 3, 0, 3), (0.98, 1.02, 0, 2, -2)],
        "run": [(1.06, 0.94, -7, -2, -8), (0.98, 1.05, 0, -8, 5), (1.06, 0.94, 7, -2, 8), (0.98, 1.05, 0, 1, -5)],
        "sleep": [(1.04, 0.88, 0, 16, 0), (1.05, 0.86, 0, 17, 0), (1.04, 0.88, 0, 16, 0), (1.03, 0.89, 0, 15, 0)],
        "dragged": [(0.98, 1.04, 0, -14, -8), (0.98, 1.04, 0, -14, 8)],
        "falling": [(1.00, 1.00, 0, -4, -8), (1.00, 1.00, 0, 0, 8)],
        "roll": [(0.96, 0.96, 0, 0, angle) for angle in (0, 45, 90, 135, 180, 225, 270, 315)],
    }
    for name, frames in specs.items():
        for idx, spec in enumerate(frames):
            frame = transform(base, *spec)
            frame.save(OUT / f"{name}_{idx:02d}.png")


def transform(base: Image.Image, scale_x: float, scale_y: float, offset_x: int, offset_y: int, rotation: float) -> Image.Image:
    canvas = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    resized = base.resize((max(1, int(base.width * scale_x)), max(1, int(base.height * scale_y))), Image.Resampling.LANCZOS)
    if rotation:
        resized = resized.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
    x = (canvas.width - resized.width) // 2 + offset_x
    y = canvas.height - resized.height - 18 + offset_y
    canvas.alpha_composite(resized, (x, y))
    canvas = trim_transparent(canvas)
    canvas.thumbnail((260, 260), Image.Resampling.LANCZOS)
    return canvas


if __name__ == "__main__":
    main()
