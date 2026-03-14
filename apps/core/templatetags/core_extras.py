from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permet d'accéder à un dict par clé dans un template."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}

@register.filter
def get_key(dictionary, key):
    """Accède à une clé d'un dict retourné par get_item."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0
