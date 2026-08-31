from django.db.models import Exists, OuterRef
from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter

from recipes.models import Favorite, Recipe, ShoppingCart, Tag


class IngredientSearchFilter(SearchFilter):
    search_param = 'name'


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(
        method='filter_is_favorited',
    )

    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart',
    )

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )

    class Meta:
        model = Recipe
        fields = (
            'author',
            'is_favorited',
            'is_in_shopping_cart',
            'tags',
        )

    def filter_is_favorited(
        self,
        queryset,
        name,
        value,
    ):
        if value is None:
            return queryset

        user = self.request.user

        if not user.is_authenticated:
            return queryset.none() if value else queryset

        favorite_exists = Favorite.objects.filter(
            user=user,
            recipe=OuterRef('pk'),
        )

        if value:
            return queryset.filter(
                Exists(favorite_exists),
            )

        return queryset.filter(
            ~Exists(favorite_exists),
        )

    def filter_is_in_shopping_cart(
        self,
        queryset,
        name,
        value,
    ):
        if value is None:
            return queryset

        user = self.request.user

        if not user.is_authenticated:
            return queryset.none() if value else queryset

        shopping_cart_exists = ShoppingCart.objects.filter(
            user=user,
            recipe=OuterRef('pk'),
        )

        if value:
            return queryset.filter(
                Exists(shopping_cart_exists),
            )

        return queryset.filter(
            ~Exists(shopping_cart_exists),
        )
