#!/usr/bin/env python3
"""Prepare LoonKit's six new strategy icons from verified Apple App Store listings."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "icons" / "v20261025r1"
APPS = {
    "GitHub": (1477376905, "github"),
    "ChatGPT": (6448311069, "openai"),
    "Gemini": (6477489729, "google"),
    "Claude": (6473753684, "anthropic"),
    "Speedtest": (300704847, "ookla"),
    "Cloudflare": (1423538627, "cloudflare"),
}
CANVAS = 512

def download(url: str, *, max_bytes: int = 8_000_000) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "LoonKit-Icon-Builder/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError("unexpected HTTP status")
        data = response.read(max_bytes + 1)
    if not data or len(data) > max_bytes:
        raise ValueError("invalid artwork response")
    return data

def lookup(app_id: int, seller_hint: str) -> tuple[dict, str]:
    endpoint = "https://itunes.apple.com/lookup?id=" + str(app_id) + "&country=us&entity=software"
    record = json.loads(download(endpoint, max_bytes=2_000_000))
    results = [x for x in record.get("results", []) if x.get("trackId") == app_id and x.get("kind") == "software"]
    if len(results) != 1:
        raise ValueError("App Store lookup returned an unexpected app ID: " + str(app_id))
    app = results[0]
    sellers = " ".join(str(app.get(x, "")) for x in ("artistName", "sellerName")).lower()
    if seller_hint not in sellers:
        raise ValueError("App Store seller does not match: " + str(app_id))
    artwork = app.get("artworkUrl512") or app.get("artworkUrl100")
    if not isinstance(artwork, str):
        raise ValueError("app artwork URL absent")
    parsed = urllib.parse.urlparse(artwork)
    if parsed.scheme != "https" or not re.fullmatch(r"(?:is\d+-ssl|is\d+|a\d+)\.mzstatic\.com", parsed.hostname or ""):
        raise ValueError("unexpected App Store artwork host")
    # Apple's image service accepts the requested 512x512 icon size.
    artwork = re.sub(r"/\d+x\d+(?:bb|wa)(?=\.)", "/512x512bb", artwork)
    return app, artwork

def normalize(payload: bytes) -> tuple[bytes, dict]:
    original = Image.open(io.BytesIO(payload))
    original.load()
    if original.width < 100 or original.height < 100 or original.width > 8192 or original.height > 8192:
        raise ValueError("unusable artwork dimensions")
    image = original.convert("RGBA")
    alpha = image.getchannel("A")
    # Cropping only known transparent margins avoids losing real artwork/highlight detail.
    bounding = alpha.point(lambda value: 255 if value >= 15 else 0).getbbox()
    crop = (0, 0, image.width, image.height)
    if bounding:
        left, top, right, bottom = bounding
        xpad = round(image.width * 0.01)
        ypad = round(image.height * 0.01)
        inner = (max(0,left-xpad), max(0,top-ypad), min(image.width,right+xpad), min(image.height,bottom+ypad))
        if inner[0] > image.width*0.035 or inner[1] > image.height*0.035 or inner[2] < image.width*0.965 or inner[3] < image.height*0.965:
            crop = inner
            image = image.crop(crop)
    if image.width != image.height:
        image = ImageOps.fit(image, (CANVAS, CANVAS), method=Image.Resampling.LANCZOS, centering=(0.5,0.5))
    else:
        image = image.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)
    # Rounded iOS-style mask, with anti-aliasing, consistent for all new icon assets.
    supersample = 4
    side = CANVAS * supersample
    mask = Image.new("L", (side,side))
    drawer = ImageDraw.Draw(mask)
    drawer.rounded_rectangle((0,0,side-1,side-1), radius=round(side*0.217), fill=255)
    mask = mask.resize((CANVAS,CANVAS), Image.Resampling.LANCZOS)
    a = image.getchannel("A")
    import PIL.ImageChops
    image.putalpha(PIL.ImageChops.multiply(a, mask))
    result = io.BytesIO()
    image.save(result, format="PNG", optimize=True, compress_level=9)
    return result.getvalue(), {"original_dimensions":[original.width,original.height],"crop_box":list(crop),"output_dimensions":[CANVAS,CANVAS],"mode":"RGBA"}

def build() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version":1,"source":"Apple App Store iTunes lookup by verified application ID","icons":{}}
    for strategy, (app_id, seller) in APPS.items():
        app, url = lookup(app_id, seller)
        result, details = normalize(download(url))
        path = OUTPUT / (strategy + ".png")
        path.write_bytes(result)
        manifest["icons"][strategy] = {
            "app_store_id": app_id,
            "app_store_url": app.get("trackViewUrl", "https://apps.apple.com/us/app/id"+str(app_id)),
            "publisher": app.get("artistName"),
            "artwork_url": url,
            "sha256": hashlib.sha256(result).hexdigest(),
            **details,
        }
    (OUTPUT/"sources.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

def check() -> None:
    record = json.loads((OUTPUT/"sources.json").read_text(encoding="utf-8"))
    if set(record["icons"]) != set(APPS):
        raise ValueError("wrong icon set")
    for name, data in record["icons"].items():
        img = OUTPUT/(name+".png")
        contents = img.read_bytes()
        if hashlib.sha256(contents).hexdigest() != data["sha256"]:
            raise ValueError("icon checksum changed: " + name)
        with Image.open(io.BytesIO(contents)) as v:
            if v.size != (512,512) or v.mode != "RGBA":
                raise ValueError("wrong normalized format: " + name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        print(json.dumps({"icon_names":list(build()["icons"]),"format":"512x512 RGBA PNG"},ensure_ascii=False))
