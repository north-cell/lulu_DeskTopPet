from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "assets" / "lulu_transparent_gifs"
RAW_DIR = ROOT / "assets" / "_qq_lulu_post_raw"
REPORT_PATH = OUTPUT_DIR / "qq_lulu_post_report.json"
POST_URL = "https://pd.qq.com/g/pd92538798/post/B_284d7a6886a60b001441152202225402930X60"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Referer": "https://pd.qq.com/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}

URL_RE = re.compile(r"https://channelr\.photo\.store\.qq\.com/psc\?[^\"'<>\\\s]+")


@dataclass
class SavedItem:
    file: str
    source_url: str
    width: int
    height: int
    frames: int
    content_type: str
    bytes: int


@dataclass
class SkippedItem:
    source_url: str
    reason: str


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    post_html = session.get(POST_URL, timeout=30).text
    image_urls = extract_image_urls(post_html)
    saved, skipped = [], []
    seen_hashes = existing_hashes()
    next_index = next_output_index()

    for url in image_urls:
        try:
            response = session.get(url, timeout=30)
            if response.status_code != 200 or len(response.content) < 10_000:
                skipped.append(SkippedItem(url, f"http {response.status_code}, {len(response.content)} bytes"))
                continue

            digest = hashlib.sha256(response.content).hexdigest()
            if digest in seen_hashes:
                skipped.append(SkippedItem(url, "duplicate bytes"))
                continue

            raw_path = RAW_DIR / f"{digest[:16]}.bin"
            raw_path.write_bytes(response.content)
            converted = convert_to_gif(raw_path, OUTPUT_DIR / f"qq_lulu_{next_index:02d}.gif")
            if not converted:
                skipped.append(SkippedItem(url, "not an animated image"))
                continue

            target, width, height, frames = converted
            seen_hashes.add(digest)
            saved.append(
                SavedItem(
                    file=target.name,
                    source_url=url,
                    width=width,
                    height=height,
                    frames=frames,
                    content_type=response.headers.get("content-type", ""),
                    bytes=target.stat().st_size,
                )
            )
            next_index += 1
            print(f"saved {target.name} {width}x{height} frames={frames}")
        except Exception as exc:  # noqa: BLE001 - keep the batch going.
            skipped.append(SkippedItem(url, exc.__class__.__name__))

    REPORT_PATH.write_text(
        json.dumps(
            {
                "post_url": POST_URL,
                "source_count": len(image_urls),
                "saved_count": len(saved),
                "saved": [asdict(item) for item in saved],
                "skipped": [asdict(item) for item in skipped],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"sources={len(image_urls)} saved={len(saved)} skipped={len(skipped)}")
    print(REPORT_PATH.relative_to(ROOT))


def extract_image_urls(post_html: str) -> list[str]:
    normalized = html.unescape(post_html).replace("\\/", "/").replace("\\u002F", "/")
    urls = []
    seen = set()
    for match in URL_RE.finditer(normalized):
        url = match.group(0).rstrip("\\")
        parsed = urlparse(url)
        # Keep the original /o= resource, not lower-quality /m= or /c= variants.
        if "/o=" not in parsed.query:
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def convert_to_gif(source: Path, target: Path) -> tuple[Path, int, int, int] | None:
    with Image.open(source) as image:
        width, height = image.size
        frame_count = getattr(image, "n_frames", 1)
        if frame_count < 2:
            return None
        frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(image)]
        durations = [
            frame.info.get("duration", image.info.get("duration", 90))
            for frame in ImageSequence.Iterator(image)
        ]
        loop = image.info.get("loop", 0)

    frames[0].save(
        target,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop,
        disposal=2,
        transparency=0,
    )
    return target, width, height, frame_count


def existing_hashes() -> set[str]:
    hashes = set()
    for path in OUTPUT_DIR.glob("*.gif"):
        hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    return hashes


def next_output_index() -> int:
    indexes = []
    for path in OUTPUT_DIR.glob("qq_lulu_*.gif"):
        match = re.search(r"(\d+)", path.stem)
        if match:
            indexes.append(int(match.group(1)))
    return max(indexes, default=0) + 1


if __name__ == "__main__":
    main()
