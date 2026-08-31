from django.contrib.auth import authenticate
from django.db import transaction
from djoser.serializers import TokenCreateSerializer as DjoserTCS
from rest_framework import serializers

from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)
from recipes.utils import Base64ImageField
from users.models import User


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


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор для получения рецепта."""

    author = serializers.SerializerMethodField()

    tags = TagSerializer(
        many=True,
        read_only=True,
    )

    ingredients = IngredientInRecipeSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True,
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

    def get_author(self, obj):
        return UserSerializer(
            obj.author,
            context=self.context,
        ).data


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и изменения рецепта."""

    image = Base64ImageField()

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )

    ingredients = IngredientAmountSerializer(
        many=True,
        write_only=True,
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        read_only_fields = (
            'id',
            'author',
        )

    def validate_image(self, image):
        if not image:
            raise serializers.ValidationError(
                'Изображение обязательно.'
            )
        return image

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

    def _set_tags_and_ingredients(
        self,
        recipe,
        tags=None,
        ingredients=None,
    ):
        if tags is not None:
            recipe.tags.set(tags)

        if ingredients is not None:
            recipe.recipe_ingredients.all().delete()

            RecipeIngredient.objects.bulk_create(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=item['id'],
                    amount=item['amount'],
                )
                for item in ingredients
            )

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')

        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )

        self._set_tags_and_ingredients(
            recipe,
            tags=tags,
            ingredients=ingredients,
        )

        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop(
            'ingredients',
            None,
        )
        tags = validated_data.pop(
            'tags',
            None,
        )

        instance = super().update(
            instance,
            validated_data,
        )

        self._set_tags_and_ingredients(
            instance,
            tags=tags,
            ingredients=ingredients,
        )

        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context=self.context,
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class TokenCreateSerializer(DjoserTCS):
    email = serializers.EmailField(
        required=True,
    )
    password = serializers.CharField(
        required=True,
    )

    class Meta:
        model = User
        fields = (
            'email',
            'password',
        )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email is None:
            raise serializers.ValidationError({
                'email': 'Обязательное поле.'
            })

        if password is None:
            raise serializers.ValidationError({
                'password': 'Обязательное поле.'
            })

        self.user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password,
        )

        if not self.user:
            raise serializers.ValidationError(
                'Неверный email или пароль.'
            )

        if not self.user.is_active:
            raise serializers.ValidationError(
                'Пользователь неактивен.'
            )

        return attrs


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        read_only_fields = (
            'id',
            'is_subscribed',
        )


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
    )

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        read_only_fields = (
            'id',
        )

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
        )


class RecipesLimitSerializer(serializers.Serializer):
    recipes_limit = serializers.IntegerField(
        min_value=1,
        required=False,
    )


class UserWithRecipesSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (  # type: ignore[assignment]
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')

        queryset = obj.recipes.all()

        params_serializer = RecipesLimitSerializer(
            data=request.query_params,
        )
        params_serializer.is_valid(raise_exception=True)

        limit = params_serializer.validated_data.get(
            'recipes_limit',
        )

        if limit is not None:
            queryset = queryset[:limit]

        return RecipeMinifiedSerializer(
            queryset,
            many=True,
            context=self.context,
        ).data
