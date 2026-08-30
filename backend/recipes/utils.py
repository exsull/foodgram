import base64
import secrets
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import ShortLink


def generate_short_code(length=4):
    while True:
        short_code = secrets.token_urlsafe(length)

        if not ShortLink.objects.filter(
            short_code=short_code
        ).exists():
            return short_code


class Base64ImageField(serializers.ImageField):
    """Поле для преобразования base64-строки в изображение."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                header, encoded = data.split(';base64,', 1)
                extension = header.split('/')[-1]

                if extension == 'jpeg':
                    extension = 'jpg'

                decoded_file = base64.b64decode(encoded)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    'Некорректное изображение.'
                )

            data = ContentFile(
                decoded_file,
                name=f'{uuid.uuid4()}.{extension}',
            )

        return super().to_internal_value(data)


def format_shopping_list(ingredients):
    return '\n'.join(
        f'{item["ingredient__name"]} — '
        f'{item["amount"]:g} '
        f'{item["ingredient__measurement_unit"]}'
        for item in ingredients
    )
