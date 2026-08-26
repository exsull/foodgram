from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.models import User as Usr

from .models import Subscription, User

# Скрываем стандартные Группы Django
if admin.site.is_registered(Group):
    admin.site.unregister(Group)

# Скрываем стандартных Пользователей Django (auth.User)
if admin.site.is_registered(Usr):
    admin.site.unregister(Usr)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_superuser',
        'last_login',
    )
    exclude = ('groups',)
    search_fields = (
        'email',
        'username',
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'following',
    )
