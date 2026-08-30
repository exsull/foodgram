from django.contrib.auth.models import AbstractUser
from django.db import models

from . import constants


class User(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        max_length=constants.EMAIL_MAX_LENGTH,
        unique=True,
    )
    first_name = models.CharField(
        'Имя',
        max_length=constants.FIRST_NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=constants.LAST_NAME_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/',
        default='',
        blank=True,
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
    )

    class Meta:
        ordering = ['username']
        verbose_name = 'пользователя'
        verbose_name_plural = 'пользователи'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь',
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Подписка на',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='unique_subscription',
            ),
            models.CheckConstraint(
                condition=~models.Q(following=models.F('user')),
                name='prevent_self_follow',
            ),
        ]
        verbose_name = 'подписку'
        verbose_name_plural = 'подписки'

    def __str__(self):
        return f'{self.user} -> {self.following}'
