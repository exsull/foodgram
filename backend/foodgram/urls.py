from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from django.conf import settings
from django.conf.urls.static import static

from api.views import ShortLinkRedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('djoser.urls.authtoken')),
    path(
        'api/docs/redoc/',
        TemplateView.as_view(
            template_name='redoc.html',
        ),
        name='redoc',
    ),
    path(
        'api/docs/redoc/openapi-schema.yml',
        TemplateView.as_view(
            template_name='openapi-schema.yml',
            content_type='text/yaml',
        ),
        name='openapi-schema',
    ),
    path('api/', include('api.urls')),
    path(
        's/<str:short_code>/',
        ShortLinkRedirectView.as_view(),
        name='short-link',
    ),
]

admin.site.site_header = 'Панель управления FoodGram'
admin.site.site_title = 'FoodGram'
admin.site.index_title = 'Управление проектом'

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
