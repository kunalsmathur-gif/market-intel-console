"""Text matching shared by extract (does the model's quote appear in the feed item it was
given?) and verify (does it appear on the live article page?). Whitespace/case only — this
checks whether a quote is genuinely there, not whether it's paraphrased well.
"""

import html as html_module
import re

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def normalize_for_match(text: str) -> str:
    return " ".join(text.split()).lower()


def strip_html(markup: str) -> str:
    """A plain-text approximation of a page's body, good enough for a substring quote
    check — not a real HTML parser, so don't reuse this for anything that needs structure."""
    without_scripts = _SCRIPT_STYLE_RE.sub(" ", markup)
    without_tags = _TAG_RE.sub(" ", without_scripts)
    return html_module.unescape(without_tags)
