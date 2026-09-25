from django.conf import settings
from django.urls import include, path
from django.views.static import serve

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls


def serve_media(request, path):
    # MEDIA_ROOT is changed by the tests, so look it up on each request
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("media/<path:path>", serve_media),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("", include(wagtail_urls)),
]
