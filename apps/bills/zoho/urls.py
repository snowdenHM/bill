from django.urls import path

from apps.bills.zoho.views import vendor, settings, expense

app_name = 'zoho'

urlpatterns = [
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

    # Expense Bills Management
    path('expense/main/', expense.expense_bills, name='expense_bill_list'),
    path('expense/bills/create/', expense.expense_bill_create, name='expense_bill_create'),
    path('expense/bills/<str:bill_id>/delete/', expense.expense_bill_delete, name='expense_bill_delete'),
    path('expense/bill/<str:bill_id>/view/', expense.view_bill, name='view_expense_bill'),
    # Expense Bills Categories
    path('expense/bills/draft/', expense.expense_bill_drafts, name='expense_bill_drafts'),  # Draft Bills
    path('expense/bills/analyzed/', expense.expense_bill_analyzed, name='expense_bill_analyzed'),  # Analyzed Bills
    path('expense/bills/synced/', expense.expense_bill_synced, name='expense_bill_synced'),  # Synced Bills

    # Expense Bill Actions
    path('expense/bills/<str:bill_id>/analyze/', expense.expense_bill_analysis_process,
         name='expense_bill_analysis_process'),
    path('expense/bills/<str:bill_id>/verification/', expense.expense_bill_verification_process,
         name='expense_bill_verification_process'),
    path('expense/bills/<str:bill_id>/sync/', expense.expense_bill_sync_process, name='expense_bill_sync_process'),
    # Expense Sync Bill Detail Page
    path('expense/bills/sync/<str:bill_id>/detail/', expense.expense_synced_bill_detail,
         name='expense_bills_sync_detail'),

    # Settings of Zoho
    path('credentials/', settings.credentials, name='credentials'),
    path('vendors/', settings.vendor, name='vendors'),
    path('chartOfaccounts/', settings.chart_of_account, name='chartOfAccount'),
    path('taxes/', settings.taxes, name='taxes'),
    path('tds_tcs/taxes/', settings.tds_tcs_tax, name='tds_tcs_tax'),

    # Utiliy for zoho data
    path('generate_token/', settings.generate_token, name='generate_token'),
    path('fetchTax/', settings.fetchTaxes, name='fetchTax'),  # Tax Utility Function
    path('fetchCoa/', settings.fetchChartAccount, name='fetchChartAccount'),  # COA Utility Function
    path('fetch_vendor/', settings.fetchVendor, name='fetch_vendor'),
    path('vendor/fetch/', settings.fetchVendorGst, name='fetchVendorGst'),  # Get Vendor GST
    path('tds_tcs/fetch/', settings.fetch_tds_tcs_tax, name='fetch_tds_tcs_tax'),  # TDS/TCS Utility Function
    path('fetch_tax_data/', settings.fetch_tax_data, name='fetch_tax_data'),  # TDS/TCS Analysis Bill Function
]
