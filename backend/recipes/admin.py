from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from users.models import User
from .constants import TABULAR_EXTRA, TABULAR_MIN
from .models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    ShortLink,
    Tag,
)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    min_num = TABULAR_MIN
    extra = TABULAR_EXTRA


class RecipeAuthorFilter(admin.SimpleListFilter):
    title = 'Автор'
    parameter_name = 'author'

    def lookups(self, request, model_admin):
        authors = User.objects.filter(
            recipes__isnull=False,
        ).distinct().order_by('username')

        return (
            (author.id, author.username)
            for author in authors
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(author_id=self.value())

        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'favorites_count',
        'cooking_time',
        'get_tags',
        'get_ingredients',
        'pub_date',
        'get_image_preview',
    )
    search_fields = (
        'name',
        'author__username',
        'tags__name',
    )
    list_filter = (
        'tags',
        'cooking_time',
        RecipeAuthorFilter,
    )
    readonly_fields = (
        'favorites_count',
    )
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('author')
            .prefetch_related('tags', 'recipe_ingredients__ingredient')
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
        return ', '.join(tag.name for tag in obj.tags.all())

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ', '.join(ing.name for ing in obj.ingredients.all())

    @admin.display(description='Картинка')
    def get_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; '
                'max-width: 50px; border-radius: 4px;" />',
                obj.image.url
            )
        return 'Нет картинки'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit',
        'recipe_count',
    )
    search_fields = (
        'name',
        'measurement_unit',
    )
    list_filter = (
        'measurement_unit',
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _recipe_count=Count('recipe_ingredients')
            )
        )

    @admin.display(
        description='Использовано в рецептах',
        ordering='_recipe_count',
    )
    def recipe_count(self, obj):
        return obj._recipe_count


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
