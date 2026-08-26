from django.contrib import admin
from django.db.models import Count

from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    ShortLink,
    Tag,
)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'favorites_count',
        'get_tags',
    )
    search_fields = (
        'name',
        'author__username',
    )
    list_filter = (
        'tags',
    )
    readonly_fields = (
        'favorites_count',
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('author')
            .prefetch_related('tags')
            .annotate(
                _favorites_count=Count('favorites'),
            )
        )

    @admin.display(
        description='Добавили в избранное',
        ordering='_favorites_count',
    )
    def favorites_count(self, obj):
        return obj._favorites_count

    @admin.display(description='Тэги')
    def get_tags(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
    )
    search_fields = (
        'name',
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
    )
    search_fields = (
        'name',
    )


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = (
        'recipe',
        'ingredient',
        'amount',
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'recipe',
    )


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = (
        'recipe',
        'short_code',
    )
    search_fields = (
        'short_code',
        'recipe__name',
    )
