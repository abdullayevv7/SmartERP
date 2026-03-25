"""
SmartERP URL Configuration.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

api_v1_urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("hr/", include("apps.hr.urls")),
    path("finance/", include("apps.finance.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("procurement/", include("apps.procurement.urls")),
    path("sales/", include("apps.sales.urls")),
    path("projects/", include("apps.projects.urls")),
]

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include(api_v1_urlpatterns)),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

# Debug toolbar
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Admin site customization
admin.site.site_header = "SmartERP Administration"
admin.site.site_title = "SmartERP Admin"
admin.site.index_title = "System Management"
