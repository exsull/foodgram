import base64
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers

from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)


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


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug',
        )
        read_only_fields = (
            'id',
        )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit',
        )
        read_only_fields = (
            'id',
        )


class IngredientAmountSerializer(serializers.Serializer):
    """Ингредиент при создании/изменении рецепта."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
    )
    amount = serializers.IntegerField(
        min_value=1,
    )


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Ингредиент при получении рецепта."""

    id = serializers.IntegerField(
        source='ingredient.id',
        read_only=True,
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True,
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True,
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )
        read_only_fields = (
            'id',
        )


class RecipeSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    image = Base64ImageField()

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )

    ingredients = IngredientAmountSerializer(
        many=True,
        write_only=True,
    )

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        read_only_fields = (
            'id',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def get_author(self, obj):
        from users.serializers import UserSerializer

        return UserSerializer(
            obj.author,
            context=self.context,
        ).data

    def get_is_favorited(self, obj):
        return getattr(
            obj,
            'user_is_favorited',
            False,
        )

    def get_is_in_shopping_cart(self, obj):
        return getattr(
            obj,
            'user_is_in_shopping_cart',
            False,
        )

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Рецепт должен содержать хотя бы один ингредиент.'
            )

        ingredient_ids = [
            item['id'].pk
            for item in ingredients
        ]

        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                'Рецепт должен содержать хотя бы один тег.'
            )

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                'Теги не должны повторяться.'
            )

        return tags

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )

        recipe.tags.set(tags)

        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount'],
            )
            for item in ingredients
        )

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'ingredients' not in validated_data:
            raise serializers.ValidationError({
                'ingredients': 'Обязательное поле.',
            })

        if 'tags' not in validated_data:
            raise serializers.ValidationError({
                'tags': 'Обязательное поле.',
            })

        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')

        instance = super().update(
            instance,
            validated_data,
        )

        instance.tags.set(tags)

        instance.recipe_ingredients.all().delete()

        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=instance,
                ingredient=item['id'],
                amount=item['amount'],
            )
            for item in ingredients
        )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['ingredients'] = (
            IngredientInRecipeSerializer(
                instance.recipe_ingredients.all(),
                many=True,
            ).data
        )

        representation['tags'] = TagSerializer(
            instance.tags.all(),
            many=True,
        ).data

        return representation
