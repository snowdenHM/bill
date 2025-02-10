from django import forms
from django.forms import modelformset_factory, Textarea
from apps.bills.zoho.models import (
    VendorBill, VendorAnalyzedBill, VendorAnalyzedProduct, ExpenseBill,
    ExpenseAnalyzedBill, ExpenseAnalyzedProduct
)


class VendorBillForm(forms.ModelForm):
    """
    Form for creating and updating Vendor Bills.
    """
    class Meta:
        model = VendorBill
        fields = ['file', 'fileType']


class VendorAnalyzedBillForm(forms.ModelForm):
    """
    Form for reviewing and verifying analyzed Vendor Bills.
    """
    class Meta:
        model = VendorAnalyzedBill
        fields = ['selectBill', 'vendor', 'bill_no', 'bill_date', 'total', 'igst', 'cgst', 'sgst', 'is_tax',
                  'tds_tcs_id', 'note']


class VendorAnalyzedProductForm(forms.ModelForm):
    """
    Form for managing products in analyzed vendor bills.
    """
    item_details = forms.CharField(widget=Textarea(attrs={'class': 'form-control'}))

    class Meta:
        model = VendorAnalyzedProduct
        fields = ['item_name', 'item_details', 'chart_of_accounts', 'taxes', 'rate', 'quantity', 'amount',
                  'reverse_charge_tax_id', 'itc_eligibility']


# ✅
VendorProductFormSet = modelformset_factory(
    VendorAnalyzedProduct,
    form=VendorAnalyzedProductForm,
    extra=0,
)



class ExpenseBillForm(forms.ModelForm):
    """
    Form for creating and updating Expense Bills.
    """
    class Meta:
        model = ExpenseBill
        fields = ['file', 'fileType']


class ExpenseAnalyzedBillForm(forms.ModelForm):
    """
    Form for reviewing and verifying analyzed Expense Bills.
    """
    class Meta:
        model = ExpenseAnalyzedBill
        fields = ['selectBill', 'vendor', 'bill_no', 'bill_date', 'total', 'igst', 'cgst', 'sgst', 'note']


class ExpenseAnalyzedProductForm(forms.ModelForm):
    """
    Form for managing products in analyzed expense bills.
    """
    item_details = forms.CharField(widget=Textarea(attrs={'class': 'form-control'}))

    class Meta:
        model = ExpenseAnalyzedProduct
        fields = ['item_details', 'chart_of_accounts', 'amount', 'vendor', 'debit_or_credit']


# ✅ Fixed: Explicitly added `fields` to avoid ImproperlyConfigured error
ExpenseProductFormSet = modelformset_factory(
    ExpenseAnalyzedProduct,
    form=ExpenseAnalyzedProductForm,
    extra=1,  # Allow for at least one additional empty form
    can_delete=True  # Allow forms to be marked for deletion
)
