from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from djoser.views import UserViewSet as DjoserUserViewSet

from .models import Subscription
from .serializers import (
    AvatarSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)
from foodgram.pagination import LimitPageNumberPagination

User = get_user_model()


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
        if self.action == 'subscriptions':
            return UserWithRecipesSerializer

        return super().get_serializer_class()

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, id=None):
        author = self.get_object()

        if request.method == 'POST':
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

            serializer = UserWithRecipesSerializer(
                author,
                context={'request': request},
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

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
        )

        page = self.paginate_queryset(subscriptions)

        if page is not None:
            serializer = UserWithRecipesSerializer(
                page,
                many=True,
                context={'request': request},
            )
            return self.get_paginated_response(serializer.data)

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
        request.user.save(update_fields=('avatar',))

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
