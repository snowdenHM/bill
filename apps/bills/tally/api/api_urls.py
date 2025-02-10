from django.urls import path

from apps.bills.tally.api import api_views

urlpatterns = [
    path('ledgers/', api_views.LedgerViewSet.as_view({'get': 'list', 'post': 'create'}), name='ledgers_api'),
    path('master/', api_views.MasterAPIView.as_view(), name='master_api'),
    path('expense/', api_views.TallyExpenseApi.as_view(), name='expense_api'),
    path('vendor/', api_views.TallyVendor.as_view(), name='vendor_api'),
]
