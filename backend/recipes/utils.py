import secrets

from .models import ShortLink


def generate_short_code():
    while True:
        short_code = secrets.token_urlsafe(4)

        if not ShortLink.objects.filter(
            short_code=short_code
        ).exists():
            return short_code
