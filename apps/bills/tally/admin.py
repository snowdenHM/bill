from django.contrib import admin
from apps.bills.tally.models import ParentLedger, Ledger, TallyVendorBill, TallyVendorAnalyzedProduct, \
    TallyVendorAnalyzedBill

# Register your models here.


admin.site.register(ParentLedger)
admin.site.register(Ledger)
admin.site.register(TallyVendorBill)
admin.site.register(TallyVendorAnalyzedProduct)
admin.site.register(TallyVendorAnalyzedBill)
