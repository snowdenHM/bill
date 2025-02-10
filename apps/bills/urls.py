from django.urls import path, include

urlpatterns = [
    path('zoho/', include('apps.bills.zoho.urls')),
    path('tally/', include('apps.bills.tally.urls')),
]
