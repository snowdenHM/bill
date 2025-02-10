from django.contrib import admin

# Register your models here.

from .models import *

admin.site.register(ZohoVendor)
admin.site.register(ZohoChartOfAccount)
admin.site.register(ZohoCredentials)
admin.site.register(ZohoTaxes)
admin.site.register(ZohoTdsTcs)
admin.site.register(VendorBill)
admin.site.register(VendorAnalyzedBill)
admin.site.register(VendorAnalyzedProduct)
admin.site.register(ExpenseBill)
admin.site.register(ExpenseAnalyzedBill)
admin.site.register(ExpenseAnalyzedProduct)
