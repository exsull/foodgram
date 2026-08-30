from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.models import User as Usr
from django.utils.html import format_html

from .models import Subscription, User

# Скрываем стандартные Группы Django
if admin.site.is_registered(Group):
    admin.site.unregister(Group)

# Скрываем стандартных Пользователей Django (auth.User)
if admin.site.is_registered(Usr):
    admin.site.unregister(Usr)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_superuser',
        'last_login',
        'get_avatar_preview',
    )
    search_fields = (
        'email',
        'username',
    )
    fieldsets = (
        (None, {
                'fields': (
                    'username',
                    'password',
                ),
            }),
        ('Личная информация', {
                'fields': (
                    'first_name',
                    'last_name',
                    'email',
                    'avatar',
                ),
            }),
        ('Права доступа', {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                ),
            }),
        ('Важные даты', {
                "fields": (
                    'last_login',
                    'date_joined',
                ),
            }),
    )

    @admin.display(description='Аватар')
    def get_avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="max-height: 50px; '
                'max-width: 50px; border-radius: 4px;" />',
                obj.avatar.url
            )
        return 'Нет аватара'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'following',
    )
