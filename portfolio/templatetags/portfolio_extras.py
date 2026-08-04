import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_ACCENT_RE = re.compile(r'\*\*(.+?)\*\*')
_ACCENT_CLASSES = ['text-accent-orange', 'text-accent-purple']
_PAREN_RE = re.compile(r'\(([^)]+)\)\s*$')


@register.filter
def accentize(text):
    """Render **word** spans in admin-entered copy as alternating orange/purple
    accent spans, so which words get hero-heading emphasis stays admin-editable
    instead of hardcoded in the template."""
    if not text:
        return ''
    parts = []
    last_end = 0
    for i, m in enumerate(_ACCENT_RE.finditer(text)):
        parts.append(escape(text[last_end:m.start()]))
        cls = _ACCENT_CLASSES[i % len(_ACCENT_CLASSES)]
        parts.append(f'<span class="{cls}">{escape(m.group(1))}</span>')
        last_end = m.end()
    parts.append(escape(text[last_end:]))
    return mark_safe(''.join(parts))


@register.filter
def cert_badge(name):
    """Short badge label for a certification card — the bracketed code if the
    name ends with one (e.g. "AWS Certified AI Practitioner (AIF-C01)" ->
    "AIF-C01"), otherwise initials of its first few significant words."""
    if not name:
        return ''
    m = _PAREN_RE.search(name)
    if m:
        return m.group(1)[:8]
    words = [w for w in re.split(r'\s+', name) if w]
    letters = ''.join(w[0] for w in words[:3]).upper()
    return letters or name[:3].upper()


@register.filter
def icon_slug(value):
    """CoreExpertise.Icon value ('AI_DELIVERY') -> sprite id suffix ('ai-delivery')."""
    return str(value).lower().replace('_', '-')
