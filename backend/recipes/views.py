from collections import defaultdict

from django.conf import settings
from django.db.models import Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import RecipeFilter
from .models import Favorite, Ingredient, Recipe, ShoppingCart, ShortLink, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import IngredientSerializer, RecipeSerializer, TagSerializer
from .utils import generate_short_code
from foodgram.pagination import LimitPageNumberPagination


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (IsAuthorOrReadOnly,)

    def get_queryset(self):
        queryset = (
            Recipe.objects
            .select_related('author')
            .prefetch_related(
                'tags',
                'recipe_ingredients__ingredient',
            ).order_by('-id')
        )

        user = self.request.user

        # Избранное.
        if user.is_authenticated:
            queryset = queryset.annotate(
                user_is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk'),
                    )
                ),
                user_is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk'),
                    )
                ),
            )

        return queryset

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()

        if request.method == 'POST':
            favorite, created = Favorite.objects.get_or_create(
                user=request.user,
                recipe=recipe,
            )

            if not created:
                return Response(
                    {
                        'errors': (
                            'Рецепт уже находится в избранном.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                self._get_minified_recipe(recipe),
                status=status.HTTP_201_CREATED,
            )

        deleted, _ = Favorite.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()

        if not deleted:
            return Response(
                {
                    'errors': (
                        'Рецепта нет в избранном.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()

        if request.method == 'POST':
            shopping_cart, created = (
                ShoppingCart.objects.get_or_create(
                    user=request.user,
                    recipe=recipe,
                )
            )

            if not created:
                return Response(
                    {
                        'errors': (
                            'Рецепт уже находится '
                            'в списке покупок.'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                self._get_minified_recipe(recipe),
                status=status.HTTP_201_CREATED,
            )

        deleted, _ = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()

        if not deleted:
            return Response(
                {
                    'errors': (
                        'Рецепта нет в списке покупок.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    def _get_minified_recipe(self, recipe):
        from .serializers import RecipeMinifiedSerializer

        return RecipeMinifiedSerializer(
            recipe,
            context={'request': self.request},
        ).data

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        shopping_cart = (
            ShoppingCart.objects
            .filter(user=request.user)
            .select_related('recipe')
            .prefetch_related(
                'recipe__recipe_ingredients__ingredient',
            )
        )

        ingredients = defaultdict(float)

        for item in shopping_cart:
            for recipe_ingredient in item.recipe.recipe_ingredients.all():
                ingredient = recipe_ingredient.ingredient

                ingredients[
                    (
                        ingredient.name,
                        ingredient.measurement_unit,
                    )
                ] += recipe_ingredient.amount

        shopping_list = [
            f'{name} — {amount:g} {measurement_unit}'
            for (
                name,
                measurement_unit,
            ), amount in sorted(
                ingredients.items(),
                key=lambda item: item[0][0].lower(),
            )
        ]

        response = HttpResponse(
            '\n'.join(shopping_list),
            content_type='text/plain; charset=utf-8',
        )

        response[
            'Content-Disposition'
        ] = 'attachment; filename="shopping_cart.txt"'

        return response

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()

        short_link, created = ShortLink.objects.get_or_create(
            recipe=recipe,
        )

        if created:
            short_link.short_code = generate_short_code()
            short_link.save(
                update_fields=('short_code',)
            )

        short_url = request.build_absolute_uri(
            reverse(
                'short-link',
                kwargs={
                    'short_code': short_link.short_code,
                },
            )
        )

        return Response(
            {
                'short-link': short_url,
            }
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        name = self.request.query_params.get('name')

        if name:
            queryset = queryset.filter(
                name__istartswith=name,
            )

        return queryset


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer


class ShortLinkRedirectView(View):
    def get(self, request, short_code):
        short_link = get_object_or_404(
            ShortLink.objects.select_related('recipe'),
            short_code=short_code,
        )

        return redirect(
            f'{settings.FRONTEND_URL}/recipes/{short_link.recipe.id}/'
        )
