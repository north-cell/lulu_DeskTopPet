from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import numpy as np
import requests
from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
OUTPUT_DIR = ASSETS_DIR / "lulu_transparent_gifs"
RAW_ITEMS_PATH = ASSETS_DIR / "aigei_lulu_items.raw.txt"
COOKIE_PATH = ASSETS_DIR / "aigei_cookies.json"
REPORT_PATH = OUTPUT_DIR / "aigei_lulu_report.json"

MIN_SIZE = 300
MIN_FRAMES = 2
MIN_TRANSPARENT_RATIO = 0.01
MIN_SHARPNESS = 16.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    ),
    "Referer": "https://www.aigei.com/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


@dataclass
class SavedItem:
    file: str
    source_url: str
    title: str
    width: int
    height: int
    frames: int
    transparent_ratio: float
    sharpness: float
    bytes: int


@dataclass
class SkippedItem:
    source_url: str
    title: str
    reason: str


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    items = load_items()
    session = requests.Session()
    session.headers.update(HEADERS)
    load_browser_cookies(session)
    existing = existing_hashes()
    saved: list[SavedItem] = []
    skipped: list[SkippedItem] = []
    next_index = next_output_index()

    for item in items:
        title = title_from_text(item.get("text", ""))
        if not is_lulu_title(title):
            skipped.append(SkippedItem(item.get("img") or "", title, "not a lulu result"))
            continue
        source = source_url_for_item(session, item)
        if not source:
            skipped.append(SkippedItem("", title, "missing image url"))
            continue
        try:
            response = session.get(source, timeout=30)
            if response.status_code != 200 or len(response.content) < 15_000:
                skipped.append(SkippedItem(source, title, f"http {response.status_code}, {len(response.content)} bytes"))
                continue
            digest = hashlib.sha256(response.content).hexdigest()
            if digest in existing:
                skipped.append(SkippedItem(source, title, "duplicate"))
                continue

            target = OUTPUT_DIR / f"aigei_lulu_{next_index:02d}.gif"
            quality = save_if_clear_gif(response.content, target)
            if not quality:
                skipped.append(SkippedItem(source, title, "not clear transparent animated gif"))
                continue

            existing.add(digest)
            saved.append(
                SavedItem(
                    file=target.name,
                    source_url=source,
                    title=title,
                    width=quality["width"],
                    height=quality["height"],
                    frames=quality["frames"],
                    transparent_ratio=quality["transparent_ratio"],
                    sharpness=quality["sharpness"],
                    bytes=target.stat().st_size,
                )
            )
            print(f"saved {target.name} {quality['width']}x{quality['height']} frames={quality['frames']} {title}")
            next_index += 1
        except Exception as exc:  # noqa: BLE001 - keep batch downloads going.
            skipped.append(SkippedItem(source, title, exc.__class__.__name__))

    REPORT_PATH.write_text(
        json.dumps(
            {
                "source": "https://www.aigei.com/s?q=%E9%BB%84%E8%89%B2%E6%B0%B4%E8%B1%9A&type=gif_moving_graph",
                "item_count": len(items),
                "saved_count": len(saved),
                "saved": [asdict(item) for item in saved],
                "skipped": [asdict(item) for item in skipped],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"items={len(items)} saved={len(saved)} skipped={len(skipped)}")
    print(REPORT_PATH.relative_to(ROOT))


def load_items() -> list[dict]:
    raw = RAW_ITEMS_PATH.read_text(encoding="utf-8")
    if raw.startswith("result: "):
        raw = raw[len("result: ") :]
    return json.loads(raw)


def title_from_text(text: str) -> str:
    line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return re.sub(r"\s+", "", line)


def is_lulu_title(title: str) -> bool:
    return "水豚" in title and "噜噜" in title


def source_url_for_item(session: requests.Session, item: dict) -> str:
    detail_url = item.get("href") or ""
    if detail_url:
        try:
            response = session.get(detail_url, timeout=30)
            if response.status_code == 200:
                detail_source = extract_detail_preview(response.text)
                if detail_source:
                    return detail_source
        except requests.RequestException:
            pass
    return item.get("img") or ""


def extract_detail_preview(page_html: str) -> str:
    match = re.search(r"https://s1\.aigei\.com/prevfiles/[^\"'<>\s]+?\.gif\?[^\"'<>\s]+", page_html)
    if match:
        return match.group(0).replace("&amp;", "&")
    match = re.search(r"https://s1\.aigei\.com/src/img/gif/[^\"'<>\s]+?\.gif\?[^\"'<>\s]+", page_html)
    if match:
        return match.group(0).replace("&amp;", "&")
    return ""


def save_if_clear_gif(content: bytes, target: Path) -> dict[str, float | int] | None:
    tmp = target.with_suffix(".download")
    tmp.write_bytes(content)
    try:
        with Image.open(tmp) as image:
            width, height = image.size
            frame_count = getattr(image, "n_frames", 1)
            if width < MIN_SIZE or height < MIN_SIZE or frame_count < MIN_FRAMES:
                return None
            frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(image)]
            durations = [
                frame.info.get("duration", image.info.get("duration", 90))
                for frame in ImageSequence.Iterator(image)
            ]
            loop = image.info.get("loop", 0)

        transparent_ratio = alpha_ratio(frames[0])
        if transparent_ratio < MIN_TRANSPARENT_RATIO:
            return None
        sharpness = frame_sharpness(frames[0])
        if sharpness < MIN_SHARPNESS:
            return None

        frames[0].save(
            target,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=loop,
            disposal=2,
            transparency=0,
        )
        return {
            "width": width,
            "height": height,
            "frames": frame_count,
            "transparent_ratio": transparent_ratio,
            "sharpness": sharpness,
        }
    finally:
        if tmp.exists():
            tmp.unlink()


def alpha_ratio(frame: Image.Image) -> float:
    alpha = np.array(frame.getchannel("A"))
    return float((alpha < 12).sum() / alpha.size)


def frame_sharpness(frame: Image.Image) -> float:
    gray = frame.convert("L").resize((128, 128), Image.Resampling.LANCZOS)
    arr = np.array(gray, dtype=np.float32)
    return float(np.diff(arr, axis=1).var() + np.diff(arr, axis=0).var())


def existing_hashes() -> set[str]:
    hashes = set()
    for path in OUTPUT_DIR.glob("*.gif"):
        hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
    return hashes


def load_browser_cookies(session: requests.Session) -> None:
    if not COOKIE_PATH.exists():
        return
    cookies = json.loads(COOKIE_PATH.read_text(encoding="utf-8"))
    for cookie in cookies:
        domain = cookie.get("domain", "")
        if "aigei.com" not in domain:
            continue
        session.cookies.set(
            cookie.get("name", ""),
            cookie.get("value", ""),
            domain=domain,
            path=cookie.get("path", "/"),
        )


def next_output_index() -> int:
    indexes = []
    for path in OUTPUT_DIR.glob("aigei_lulu_*.gif"):
        match = re.search(r"(\d+)", path.stem)
        if match:
            indexes.append(int(match.group(1)))
    return max(indexes, default=0) + 1


if __name__ == "__main__":
    main()
