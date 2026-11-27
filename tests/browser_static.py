"""Embed the actual shared assets in file-based Chrome regression fixtures."""
from pathlib import Path
import re


def inline_player_assets(html: str, static: Path) -> str:
    def stylesheet(match: re.Match[str]) -> str:
        asset = re.search(r'/static/([^"?]+)', match.group())
        return '<style>' + (static / asset.group(1)).read_text() + '</style>' if asset else match.group()

    def script(match: re.Match[str]) -> str:
        asset = re.search(r'/static/([^"?]+)', match.group())
        return '<script>' + (static / asset.group(1)).read_text() + '</script>' if asset else match.group()

    html = re.sub(r'<link rel="stylesheet"[^>]+>', stylesheet, html)
    return re.sub(r'<script src="[^"]+"[^>]*></script>', script, html)
