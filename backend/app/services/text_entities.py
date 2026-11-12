"""Protect opaque identifiers before language-specific text transformations."""
import re

ENTITY_PATTERN = re.compile(
    r'(?P<literal><\s*ID\s*\d+\s*>)|'
    r'(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})|'
    r"(?P<url>\b(?:(?:https?://|ftp://|www\.)[^\s<>\"']+|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:/[^\s<>\"']*)?))|"
    r'(?P<number>[+\-\u2212]?(?:\d+(?:[-/.,:\\+]\d+)+|[.,]\d+|\d{4,})%?|[+\-\u2212]\d+%?|\d+%)|'
    r'(?P<handle>[@#][\w]+)', re.IGNORECASE)


def map_unprotected(text, transform):
    """Apply a script conversion only outside URLs, emails and identifiers."""
    result=[]; offset=0
    for match in ENTITY_PATTERN.finditer(text):
        if match.start()>offset: result.append(transform(text[offset:match.start()]))
        result.append(match.group(0)); offset=match.end()
    if offset<len(text): result.append(transform(text[offset:]))
    return ''.join(result)
