from django import forms
from django.forms import modelformset_factory, Textarea
from apps.bills.tally.models import TallyVendorBill, TallyVendorAnalyzedProduct, TallyVendorAnalyzedBill, Ledger, \
    ParentLedger


class TallyVendorBillForm(forms.ModelForm):
    """
    Form for creating and updating Vendor Bills.
    """

    class Meta:
        model = TallyVendorBill
        fields = ['file', 'fileType']


class TallyVendorAnalyzedBillForm(forms.ModelForm):
    """
    Form for reviewing and verifying analyzed Vendor Bills.
    """

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        # Fetch ParentLedger for "Sundry Creditors"
        try:
            sundry_creditors = ParentLedger.objects.get(parent="Sundry Creditors", team=team)
            # Get all Ledgers under "Sundry Creditors"
            self.fields['vendor'].queryset = Ledger.objects.filter(parent=sundry_creditors)
        except ParentLedger.DoesNotExist:
            self.fields['vendor'].queryset = Ledger.objects.none()

    class Meta:
        model = TallyVendorAnalyzedBill
        fields = ['selectBill', 'vendor', 'bill_no', 'bill_date', 'total', 'igst', 'cgst', 'sgst', 'note']


class TallyVendorAnalyzedProductForm(forms.ModelForm):
    """
    Form for managing products in analyzed vendor bills.
    """
    item_details = forms.CharField(widget=Textarea(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        try:
            duties_taxes = ParentLedger.objects.get(parent="Duties & Taxes", team=team)
            self.fields['taxes'].queryset = Ledger.objects.filter(parent=duties_taxes)
        except ParentLedger.DoesNotExist:
            self.fields['taxes'].queryset = Ledger.objects.none()

    class Meta:
        model = TallyVendorAnalyzedProduct
        fields = ['item_name', 'item_details', 'taxes', 'price', 'quantity', 'amount']


# ✅
TallyVendorProductFormSet = modelformset_factory(
    TallyVendorAnalyzedProduct,
    form=TallyVendorAnalyzedProductForm,
    extra=0,
)
