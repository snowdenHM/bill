from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.teams.urls import team_urlpatterns as single_team_urls
from apps.web.urls import team_urlpatterns as web_team_urls
from apps.web.sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap(),
}

# Team URLs
team_urlpatterns = [
    path("", include(web_team_urls)),
    path("team/", include(single_team_urls)),
    path("bills/", include('apps.bills.urls')),
]

urlpatterns = [
                  # redirect Django admin login to main login page
                  path("admin/login/", RedirectView.as_view(pattern_name="account_login")),
                  path("admin/", admin.site.urls),
                  path("dashboard/", include("apps.dashboard.urls")),
                  path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
                  path("a/<slug:team_slug>/", include(team_urlpatterns)),
                  path("accounts/", include("allauth.urls")),
                  path("users/", include("apps.users.urls")),
                  path("teams/", include("apps.teams.urls")),
                  path("", include("apps.web.urls")),
                  path("support/", include("apps.support.urls")),
                  path("celery-progress/", include("celery_progress.urls")),
                  # API docs
                  path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
                  # Optional UI - you may wish to remove one of these depending on your preference
                  path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
                  # hijack urls for impersonation
                  path("hijack/", include("hijack.urls", namespace="hijack")),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.ENABLE_DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
