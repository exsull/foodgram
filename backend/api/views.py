from django.conf import settings
from django.db.models import Count, Exists, OuterRef, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from foodgram.pagination import LimitPageNumberPagination
from recipes.filters import IngredientSearchFilter, RecipeFilter
from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    ShortLink,
    Tag,
)
from recipes.permissions import IsAuthorOrReadOnly
from recipes.utils import (
    format_shopping_list,
    generate_short_code,
)
from users.models import Subscription, User
from .serializers import (
    AvatarSerializer,
    IngredientSerializer,
    RecipeMinifiedSerializer,
    RecipeSerializer,
    TagSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer
    pagination_class = LimitPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (
        IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )

    def get_queryset(self):
        queryset = (
            Recipe.objects
            .select_related('author')
            .prefetch_related(
                'tags',
                'recipe_ingredients__ingredient',
            )
        )

        user = self.request.user

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

    def _add_to_relation(
        self,
        request,
        recipe,
        model,
        error_message,
    ):
        _, created = model.objects.get_or_create(
            user=request.user,
            recipe=recipe,
        )

        if not created:
            return Response(
                {'errors': error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            self._get_minified_recipe(recipe),
            status=status.HTTP_201_CREATED,
        )

    def _remove_from_relation(
        self,
        request,
        recipe,
        model,
        error_message,
    ):
        deleted, _ = model.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()

        if not deleted:
            return Response(
                {'errors': error_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()

        return self._add_to_relation(
            request,
            recipe,
            Favorite,
            'Рецепт уже находится в избранном.',
        )

    @favorite.mapping.delete
    def favorite_delete(self, request, pk=None):
        recipe = self.get_object()

        return self._remove_from_relation(
            request,
            recipe,
            Favorite,
            'Рецепта нет в избранном.',
        )

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()

        return self._add_to_relation(
            request,
            recipe,
            ShoppingCart,
            'Рецепт уже находится в списке покупок.',
        )

    @shopping_cart.mapping.delete
    def shopping_cart_delete(self, request, pk=None):
        recipe = self.get_object()

        return self._remove_from_relation(
            request,
            recipe,
            ShoppingCart,
            'Рецепта нет в списке покупок.',
        )

    def _get_minified_recipe(self, recipe):
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
        ingredients = (
            RecipeIngredient.objects
            .filter(
                recipe__shopping_cart__user=request.user,
            )
            .values(
                'ingredient__name',
                'ingredient__measurement_unit',
            )
            .annotate(
                amount=Sum('amount'),
            )
            .order_by('ingredient__name')
        )

        response = HttpResponse(
            format_shopping_list(ingredients),
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

        short_link, _ = ShortLink.objects.get_or_create(
            recipe=recipe,
            defaults={
                'short_code': generate_short_code(),
            },
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
    filter_backends = (IngredientSearchFilter,)
    search_fields = ('^name',)


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


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = LimitPageNumberPagination
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def get_permissions(self):
        if self.action in (
            'list',
            'retrieve',
        ):
            return (IsAuthenticatedOrReadOnly(),)

        if self.action == 'me':
            return (IsAuthenticated(),)

        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in (
            'subscriptions',
            'subscribe',
        ):
            return UserWithRecipesSerializer

        return super().get_serializer_class()

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id=None):
        author = self.get_object()

        if request.user == author:
            return Response(
                {'errors': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription, created = Subscription.objects.get_or_create(
            user=request.user,
            following=author,
        )

        if not created:
            return Response(
                {'errors': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        author = User.objects.annotate(
            recipes_count=Count('recipes'),
        ).get(
            pk=author.pk,
        )

        serializer = UserWithRecipesSerializer(
            author,
            context={'request': request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        author = self.get_object()

        deleted, _ = Subscription.objects.filter(
            user=request.user,
            following=author,
        ).delete()

        if not deleted:
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        subscriptions = User.objects.filter(
            followers__user=request.user,
        ).annotate(
            recipes_count=Count('recipes'),
        )

        page = self.paginate_queryset(subscriptions)

        if page is not None:
            serializer = UserWithRecipesSerializer(
                page,
                many=True,
                context={'request': request},
            )
            return self.get_paginated_response(
                serializer.data,
            )

        serializer = UserWithRecipesSerializer(
            subscriptions,
            many=True,
            context={'request': request},
        )

        return Response(serializer.data)

    @action(
        detail=False,
        methods=('put', 'delete'),
        url_path='me/avatar',
        permission_classes=(IsAuthenticated,),
    )
    def avatar(self, request):
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                request.user,
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        request.user.avatar.delete(save=False)
        request.user.avatar = None
        request.user.save(
            update_fields=('avatar',),
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
