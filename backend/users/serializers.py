from django.contrib.auth import authenticate, get_user_model
from djoser.serializers import TokenCreateSerializer as DjoserTCS
from rest_framework import serializers

from recipes.serializers import Base64ImageField

User = get_user_model()


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
    is_subscribed = serializers.SerializerMethodField()

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

    def get_is_subscribed(self, obj):
        request = self.context.get('request')

        if request is None or request.user.is_anonymous:
            return False

        return obj.followers.filter(
            user=request.user,
        ).exists()


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
            'is_subscribed',
        )

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
        )


class UserWithRecipesSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (  # type: ignore[assignment]
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        from recipes.serializers import RecipeMinifiedSerializer

        request = self.context.get('request')

        queryset = obj.recipes.all()

        limit = request.query_params.get('recipes_limit')

        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass

        return RecipeMinifiedSerializer(
            queryset,
            many=True,
            context=self.context,
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
