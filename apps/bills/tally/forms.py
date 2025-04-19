from django import forms
from django.forms import modelformset_factory, Textarea
from django.forms import BaseModelFormSet
from apps.bills.tally.models import TallyVendorBill, TallyVendorAnalyzedProduct, TallyVendorAnalyzedBill, Ledger, \
    ParentLedger, TallyExpenseBill, TallyExpenseAnalyzedBill, TallyExpenseAnalyzedProduct, TallyConfig


class TallyVendorBillForm(forms.ModelForm):
    """
    Form for creating and updating Vendor Bills.
    """

    class Meta:
        model = TallyVendorBill
        fields = ['file', 'fileType']


class TallyVendorAnalyzedBillForm(forms.ModelForm):
    """
    Form for reviewing and verifying analyzed Vendor Bills using dynamic TallyConfig.
    """

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

        # Fetch TallyConfig for the given team
        try:
            tally_config = TallyConfig.objects.get(team=team)
            # Dynamically assign querysets based on the selected ParentLedgers
            self.fields['vendor'].queryset = Ledger.objects.filter(parent=tally_config.vendor_parent)
            self.fields['igst_taxes'].queryset = Ledger.objects.filter(parent=tally_config.igst_parent)
            self.fields['cgst_taxes'].queryset = Ledger.objects.filter(parent=tally_config.cgst_parent)
            self.fields['sgst_taxes'].queryset = Ledger.objects.filter(parent=tally_config.sgst_parent)
        except TallyConfig.DoesNotExist:
            self.fields['vendor'].queryset = Ledger.objects.none()
            self.fields['igst_taxes'].queryset = Ledger.objects.none()
            self.fields['cgst_taxes'].queryset = Ledger.objects.none()
            self.fields['sgst_taxes'].queryset = Ledger.objects.none()

    class Meta:
        model = TallyVendorAnalyzedBill
        fields = [
            'selectBill', 'vendor', 'bill_no', 'bill_date', 'total',
            'igst', 'igst_taxes', 'cgst', 'cgst_taxes', 'sgst', 'sgst_taxes', 'note'
        ]


class TallyVendorAnalyzedProductForm(forms.ModelForm):
    """
    Form for managing products in analyzed vendor bills.
    """

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        try:
            tally_config = TallyConfig.objects.get(team=team)
            # Dynamically assign querysets based on the selected ParentLedgers
            self.fields['taxes'].queryset = Ledger.objects.filter(parent=tally_config.chart_of_accounts)
        except ParentLedger.DoesNotExist:
            self.fields['taxes'].queryset = Ledger.objects.none()

    class Meta:
        model = TallyVendorAnalyzedProduct
        fields = ['item_name', 'item_details', 'taxes', 'price', 'quantity', 'amount']


# ✅
class BaseTallyVendorProductFormSet(BaseModelFormSet):
    """
    Custom formset to pass 'team' parameter to each form.
    """

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs.update({'team': self.team})
        return kwargs


TallyVendorProductFormSet = forms.modelformset_factory(
    TallyVendorAnalyzedProduct,
    form=TallyVendorAnalyzedProductForm,
    formset=BaseTallyVendorProductFormSet,
    extra=0,
)


class ExpenseBillForm(forms.ModelForm):
    """
    Form for creating and updating Expense Bills.
    """

    class Meta:
        model = TallyExpenseBill
        fields = ['file', 'fileType']


class ExpenseAnalyzedBillForm(forms.ModelForm):
    """
    Form for reviewing and verifying analyzed Expense Bills using dynamic TallyConfig.
    """

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

        # Fetch TallyConfig for the given team
        try:
            tally_config = TallyConfig.objects.get(team=team)

            # Dynamically assign querysets based on the selected ParentLedgers
            self.fields['vendor'].queryset = Ledger.objects.filter(parent=tally_config.vendor_parent)
            self.fields['igst_taxes'].queryset = Ledger.objects.filter(parent=tally_config.igst_parent)
            self.fields['cgst_taxes'].queryset = Ledger.objects.filter(parent=tally_config.cgst_parent)
            self.fields['sgst_taxes'].queryset = Ledger.objects.filter(parent=tally_config.sgst_parent)

        except TallyConfig.DoesNotExist:
            self.fields['vendor'].queryset = Ledger.objects.none()
            self.fields['igst_taxes'].queryset = Ledger.objects.none()
            self.fields['cgst_taxes'].queryset = Ledger.objects.none()
            self.fields['sgst_taxes'].queryset = Ledger.objects.none()

    class Meta:
        model = TallyExpenseAnalyzedBill
        fields = [
            'selectBill', 'vendor', 'voucher', 'bill_no', 'bill_date', 'total',
            'igst', 'cgst', 'sgst', 'note', 'igst_taxes', 'cgst_taxes', 'sgst_taxes'
        ]


class ExpenseAnalyzedProductForm(forms.ModelForm):
    """
    Form for managing products in analyzed expense bills.
    """
    item_details = forms.CharField(widget=Textarea(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        try:
            tally_config = TallyConfig.objects.get(team=team)
            # Dynamically assign querysets based on the selected ParentLedgers
            self.fields['chart_of_accounts'].queryset = Ledger.objects.filter(
                parent=tally_config.chart_of_accounts_expense)
        except ParentLedger.DoesNotExist:
            self.fields['chart_of_accounts'].queryset = Ledger.objects.none()

    class Meta:
        model = TallyExpenseAnalyzedProduct
        fields = ['item_details', 'chart_of_accounts', 'amount', 'debit_or_credit']


# ✅
class BaseTallyExpenseProductFormSet(BaseModelFormSet):
    """
    Custom formset to pass 'team' parameter to each form.
    """

    def __init__(self, *args, **kwargs):
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs.update({'team': self.team})
        return kwargs


ExpenseProductFormSet = forms.modelformset_factory(
    TallyExpenseAnalyzedProduct,
    form=ExpenseAnalyzedProductForm,
    formset=BaseTallyExpenseProductFormSet,
    extra=0,
)
