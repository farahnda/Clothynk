from django import template

register = template.Library()


@register.filter
def rupiah(value):
    """Format angka menjadi format Rupiah: Rp1.500.000"""
    try:
        value = int(value)
        return f"Rp{value:,}".replace(',', '.')
    except (ValueError, TypeError):
        return value


@register.filter
def percentage(value, decimals=1):
    """Format float menjadi persen: 0.756 → 75.6%"""
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (ValueError, TypeError):
        return value


@register.filter
def tier_badge(tier):
    """Mengembalikan class Bootstrap badge berdasarkan tier"""
    badges = {
        'bronze': 'badge-bronze',
        'silver': 'badge-silver',
        'gold': 'badge-gold',
        'platinum': 'badge-platinum',
    }
    return badges.get(tier, 'bg-secondary')
