from django.urls import path, include

from apps.bills.tally.views import settings, vendor

app_name = 'tally'

urlpatterns = [
    ################# Vendor Bills ################
    # Vendor Bills Management
    path('vendor/main/', vendor.vendor_bills, name='vendor_bill_list'),
    path('vendor/bills/create/', vendor.bill_create, name='vendor_bill_create'),
    path('vendor/bills/<str:bill_id>/delete/', vendor.bill_delete, name='vendor_bill_delete'),
    # Vendor Bills Categories
    path('vendor/bills/draft/', vendor.bill_drafts, name='vendor_bill_drafts'),  # Draft Bills
    path('vendor/bills/analyzed/', vendor.bill_analyzed, name='vendor_bill_analyzed'),  # Analyzed Bills
    path('vendor/bills/synced/', vendor.bill_synced, name='vendor_bill_synced'),  # Synced Bills
    # Vendor Actions
    path('vendor/bills/<str:bill_id>/analyze/', vendor.bill_analysis_process, name='vendor_bill_analysis_process'),
    path('vendor/bills/<str:bill_id>/verification/', vendor.bill_verification_process,
         name='vendor_bill_verification_process'),
    path('vendor/bills/<str:bill_id>/sync/', vendor.bill_sync_process,
         name='vendor_bill_sync_process'),
    path('vendor/bill/<str:bill_id>/view/', vendor.view_bill, name='view_vendor_bill'),
    # Sync Bill Detail Page
    path('vendor/bills/sync/<str:bill_id>/detail/', vendor.synced_bill_detail, name='vendor_bills_sync_detail'),

    ################ Expense Journals ###################

    # Tally API
    path('api/v1/', include('apps.bills.tally.api.api_urls')),
    # Tally Settings URLs
    path('ledgers/', settings.ledger, name='tally_ledgers'),
    # Utility URLs
    path('vendor/fetch/', settings.fetchVendorGst, name='tally_fetch_vendor_gst'),  # Get Vendor GST
]
