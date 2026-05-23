from unicodedata import lookup, combining, bidirectional, name as chartype
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


def reshape(text: str, harakat: bool = True, get_display: bool = False) -> str:
    data = _load_arabic_shaping()

    if not harakat:
        text = clear_movements(text)

    reshape_text = list(text)

    for i, letter in enumerate(text):
        if letter in data['D'] + data['R']:
            _k = 1 + sum(1 for _ in takewhile(lambda c: combining(c), (text[j] for j in range(i-1, -1, -1))))
            k_ = 1 + sum(1 for _ in takewhile(lambda c: combining(c), (text[j] for j in range(i+1, len(text)))))
            _letter, letter_ = [l for l in [text[i - _k] if i > 0 else None, text[i + k_] if i + k_ < len(text) else None]]

            Connect = 0
            if _letter and _letter in data['D'] + data['L'] + data['C']: Connect += 1
            if letter in data['D'] and letter_ and letter_ in data['D'] + data['R'] + data['C']: Connect += 2
            
            reshape_text[i] = chr(ord(isolated(letter)) + Connect)
    result = "".join(reshape_text)

    if get_display:
        result = _get_display(result)

    return result


def _get_display(text: str) -> str:
    if all(bidirectional(letter) in ('NSM', 'WS', 'ON', 'AL') for letter in text):
        return text[::-1]
    
    try:
        from bidi.algorithm import get_display
    except ImportError:
        raise RuntimeError(
            "python-bidi is required for get_display=True.\n"
            "Install it with: pip install python-bidi"
        )
    return get_display(text)


def clear_movements(text: str) -> str:
    return "".join(letter for letter in text if not combining(letter))


def isolated(l):
    try:
        return lookup(chartype(l) + " ISOLATED FORM")
    except (LookupError, ValueError, TypeError):
        return None