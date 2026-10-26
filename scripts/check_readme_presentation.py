#!/usr/bin/env python3
"""Check the README's publishing links, visual assets, and current-doc contracts.

Runs offline: does not fetch external image hosts, GitHub, or the Loon app.
The release version is read from build/release_spec.json so future releases
remain compatible with the existing README version-replacement workflow.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSET_DIR = ROOT / "docs/assets"

EVERGREEN_DOCS = (
    "docs/SETUP_GUIDE.md",
    "docs/LOON_APP_SETTINGS.md",
    "docs/DNS_PRIVACY.md",
    "docs/NETWORK_DIAGNOSTICS.md",
)

VISUALS = (
    "readme-hero-mobile-light.svg",
    "readme-hero-mobile-dark.svg",
    "readme-hero-wide-light.svg",
    "readme-hero-wide-dark.svg",
    "readme-cta-light.svg",
    "readme-cta-dark.svg",
)

FORBIDDEN_README = (
    "七项服务", "七项平台", "7 / 7", "服务访问检测", "解耦",
)


class LocalHTMLRefs(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.images_without_alt: int = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "img" and not attrs_dict.get("alt"):
            self.images_without_alt += 1
        for key in ("src", "href", "srcset"):
            value = attrs_dict.get(key)
            if value and key == "srcset":
                value = value.split(",")[0].strip().split()[0]
            if value:
                self.links.append(value)


def check() -> list[str]:
    errors: list[str] = []
    readme = README.read_text(encoding="utf-8")
    spec = json.loads((ROOT / "build/release_spec.json").read_text(encoding="utf-8"))
    version = spec["stable_release_version"]
    marker = "当前版本：**" + version + "**"
    if readme.count(marker) != 1:
        errors.append("README must contain exactly one current release marker: " + marker)

    for term in FORBIDDEN_README:
        if term in readme:
            errors.append("README contains unwanted copy: " + term)

    html = LocalHTMLRefs()
    html.feed(readme)
    if html.images_without_alt:
        errors.append("README contains images without alt text")

    links = html.links + re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", readme)
    links += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    for link in links:
        target = link.split("#", 1)[0].split("?", 1)[0]
        if not target.startswith("./"):
            continue
        file = (ROOT / target).resolve()
        if not file.is_relative_to(ROOT) or not file.is_file():
            errors.append("README local link not found: " + target)

    for filename in VISUALS:
        path = ASSET_DIR / filename
        if not path.is_file():
            errors.append("Missing visual asset: " + filename)
            continue
        try:
            root = ET.parse(path).getroot()
            if not root.tag.endswith("svg"):
                errors.append("Not SVG: " + filename)
                continue
            size = root.attrib.get("viewBox", "").split()
            if len(size) != 4:
                errors.append("Missing SVG viewBox: " + filename)
                continue
            width, height = float(size[2]), float(size[3])
            if filename.startswith("readme-hero-mobile") and width / height < 1.5:
                errors.append("Mobile banner is too tall: " + filename)
            if filename.startswith("readme-hero-wide") and width / height < 2.5:
                errors.append("Desktop banner is too tall: " + filename)
            if filename.startswith("readme-hero-mobile"):
                panel = [node for node in root.iter() if node.attrib.get("class") == "route-panel"]
                options = [node for node in root.iter() if node.attrib.get("class") == "route-option"]
                if len(panel) != 1 or len(options) != 3:
                    errors.append("Mobile route panel or option labels missing: " + filename)
                else:
                    box = panel[0]
                    box_right = float(box.attrib["x"]) + float(box.attrib["width"])
                    box_bottom = float(box.attrib["y"]) + float(box.attrib["height"])
                    for option in options:
                        right = float(option.attrib["x"]) + float(option.attrib["width"])
                        bottom = float(option.attrib["y"]) + float(option.attrib["height"])
                        if box_right - right < 16 or box_bottom - bottom < 6:
                            errors.append("Mobile route label outside safe panel area: " + filename)
                            break
        except (ET.ParseError, ValueError) as exc:
            errors.append("Invalid SVG " + filename + ": " + str(exc))

    for relative in EVERGREEN_DOCS:
        path = ROOT / relative
        content = path.read_text(encoding="utf-8")
        if re.search(r"\bv\d+\.\d+\.\d+\b", content):
            errors.append("Evergreen doc contains a fixed release version: " + relative)

    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print("ERROR:", error, file=sys.stderr)
        return 1
    print("README and evergreen docs: links, copy, release marker, and SVGs OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
