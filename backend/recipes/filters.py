import django_filters
from django.db.models import Exists, OuterRef

from .models import Favorite, Recipe, ShoppingCart


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(
        field_name='author__id',
    )

    is_favorited = django_filters.NumberFilter(
        method='filter_is_favorited',
    )

    is_in_shopping_cart = django_filters.NumberFilter(
        method='filter_is_in_shopping_cart',
    )

    class Meta:
        model = Recipe
        fields = (
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        tags = self.request.query_params.getlist('tags')

        if tags:
            queryset = queryset.filter(
                tags__slug__in=tags,
            ).distinct()

        return queryset

    def filter_is_favorited(
        self,
        queryset,
        name,
        value,
    ):
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none() if value == 1 else queryset

        favorite_exists = Favorite.objects.filter(
            user=user,
            recipe=OuterRef('pk'),
        )

        if value == 1:
            return queryset.filter(
                Exists(favorite_exists),
            )

        if value == 0:
            return queryset.filter(
                ~Exists(favorite_exists),
            )

        return queryset

    def filter_is_in_shopping_cart(
        self,
        queryset,
        name,
        value,
    ):
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none() if value == 1 else queryset

        shopping_cart_exists = ShoppingCart.objects.filter(
            user=user,
            recipe=OuterRef('pk'),
        )

        if value == 1:
            return queryset.filter(
                Exists(shopping_cart_exists),
            )

        if value == 0:
            return queryset.filter(
                ~Exists(shopping_cart_exists),
            )

        return queryset
