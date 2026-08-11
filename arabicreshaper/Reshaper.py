from unicodedata import lookup, combining, bidirectional, mirrored, name as chartype
from urllib.request import Request, urlopen
from itertools import takewhile
from pathlib import Path

_ARABIC_SHAPING_DATA = None
_DATA_DIR = Path(__file__).parent
_DATA_FILE = _DATA_DIR / "ArabicShaping.txt"
_UNICODE_URL = "https://www.unicode.org/Public/UCD/latest/ucd/ArabicShaping.txt"

def _load_arabic_shaping():
    global _ARABIC_SHAPING_DATA
    if _ARABIC_SHAPING_DATA:
        return _ARABIC_SHAPING_DATA

    if not _DATA_FILE.exists():
        _download_and_cache()

    data = {}
    with open(_DATA_FILE, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue

            fields = [x.strip() for x in line.split(";")]
            codepoint = int(fields[0], 16)
            joining_type = fields[2]

            data.setdefault(joining_type, "")
            data[joining_type] += chr(codepoint)

    _ARABIC_SHAPING_DATA = data
    return data


def _download_and_cache():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    req = Request(_UNICODE_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req) as response:
            content = response.read().decode()
    except Exception as e:
        raise RuntimeError(
            "ArabicShaping.txt not found locally and download failed."
        ) from e

    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def reshape(text: str, get_display: bool = False, width: int = 0, harakat: bool = True) -> str:
    has_diacritics = any(combining(ch) for ch in text)
    data = _load_arabic_shaping()

    if has_diacritics and not harakat:
        text = clear_diacritics(text)

    reshape_text = list(text)

    for i, letter in enumerate(text):
        if letter in data['D'] + data['R']:
            _k = 1 + sum(1 for _ in takewhile(lambda c: combining(c), (text[j] for j in range(i-1, -1, -1))))
            k_ = 1 + sum(1 for _ in takewhile(lambda c: combining(c), (text[j] for j in range(i+1, len(text)))))
            _letter, letter_ = [l for l in [text[i - _k] if i - _k >= 0 else None, text[i + k_] if i + k_ < len(text) else None]]

            Connect = 0
            if _letter and _letter in data['D'] + data['L'] + data['C']: Connect += 1
            if letter in data['D'] and letter_ and letter_ in data['D'] + data['R'] + data['C']: Connect += 2

            reshape_text[i] = chr(ord(isolated(letter)) + Connect)
    result = ''.join(reshape_text)

    if width:
        result = line_breaker(result, width)

    if get_display:
        result = _get_display(result)
        if has_diacritics and harakat:
            result = _fix_diacritics_display(result)

    return result


def line_breaker(text: str, width: int) -> str:
    lines, line = [], []
    length, break_at = 0, None

    for char in text:
        if char == ' ':
            break_at = len(line)

        line.append(char)
        length += not combining(char)

        if length > width:
            if break_at is None:
                lines.append(''.join(line[:-1]))
                line = line[-1:]
                length = 1
            else:
                lines.append(''.join(line[:break_at]))
                line = line[break_at + 1:]
                length = sum(not combining(c) for c in line)

            break_at = None

    if line:
        lines.append(''.join(line))

    return '\n'.join(lines)


def _get_display(text: str) -> str:
    if all(bidirectional(ch) in ('NSM', 'WS', 'AL') or bidirectional(ch) == "ON" and not mirrored(ch) for ch in text.replace("\n", "")):
        return '\n'.join(line[::-1] for line in text.split("\n"))

    try:
        from bidi.algorithm import get_display
    except ImportError:
        raise RuntimeError(
            "python-bidi is required for get_display=True.\n"
            "Install it with: pip install python-bidi"
        )
    return get_display(text)


def _fix_diacritics_display(text: str) -> str:
    result, pending = [], []
    for ch in text:
        if combining(ch):
            pending.insert(0, ch)
        else:
            result.append(ch)
            result.extend(pending)
            pending = []

    result.extend(pending)
    return ''.join(result)


def clear_diacritics(text: str) -> str:
    return ''.join(ch for ch in text if not combining(ch))


def isolated(letter: str) -> str:
    try:
        return lookup(chartype(letter) + " ISOLATED FORM")
    except (LookupError, ValueError, TypeError):
        return None