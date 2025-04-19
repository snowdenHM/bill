import uuid
import re
from django.db import models
from apps.teams.models import BaseTeamModel


# Create your models here.
class ParentLedger(BaseTeamModel):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    parent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.parent}"


class Ledger(BaseTeamModel):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    master_id = models.CharField(max_length=255, blank=True, null=True)
    alter_id = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey(ParentLedger, on_delete=models.CASCADE)
    alias = models.CharField(max_length=255, blank=True, null=True)
    opening_balance = models.CharField(max_length=255, blank=True, null=True)
    gst_in = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = 'Ledger'
        verbose_name_plural = 'Ledgers'


class TallyConfig(BaseTeamModel):
    """
    Stores user-defined configuration for which ParentLedger should be used for IGST, CGST, SGST, and Vendors.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    igst_parent = models.ForeignKey(ParentLedger, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="igst_tally_config", verbose_name="IGST Parent Ledger")
    cgst_parent = models.ForeignKey(ParentLedger, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="cgst_tally_config", verbose_name="CGST Parent Ledger")
    sgst_parent = models.ForeignKey(ParentLedger, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="sgst_tally_config", verbose_name="SGST Parent Ledger")
    vendor_parent = models.ForeignKey(ParentLedger, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="vendor_tally_config", verbose_name="Vendor Parent Ledger")
    chart_of_accounts = models.ForeignKey(ParentLedger, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="coa_tally_config", verbose_name="COA Parent Ledger")
    chart_of_accounts_expense = models.ForeignKey(ParentLedger, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name="ex_coa_tally_config", verbose_name="EX COA Parent Ledger")

    class Meta:
        verbose_name_plural = "Tally Configurations"

    def __str__(self):
        return f"Tally Config for Team {self.team.name}"


##### File Validator
def validate_file_extension(value):
    """
    Validates the file extension for vendor bill uploads.
    """
    import os
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.pdf', '.png', '.jpeg', '.jpg']
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file extension.')


##### Vendor Bill Upload
class TallyVendorBill(BaseTeamModel):
    """
    Stores vendor bill details with an automated bill name generation.
    """
    BILL_STATUS = (
        ('Draft', 'Draft'),
        ('Analyzed', 'Analyzed'),
        ('Verified', 'Verified'),
        ('Synced', 'Synced')
    )

    BILL_TYPE = (
        ('Single Invoice/File', 'Single Invoice/File'),
        ('Multiple Invoice/File', 'Multiple Invoice/File'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    billmunshiName = models.CharField(max_length=100, null=True, blank=True)
    file = models.FileField(upload_to='bills/', validators=[validate_file_extension])
    fileType = models.CharField(choices=BILL_TYPE, max_length=100, null=True, blank=True, default="Single Invoice/File")
    analysed_data = models.JSONField(default=dict, null=True, blank=True)
    status = models.CharField(max_length=10, choices=BILL_STATUS, default='Draft', blank=True)
    process = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Fixed typo: update_at -> updated_at

    class Meta:
        verbose_name_plural = 'Tally Vendor Bills'

    def __str__(self):
        return self.billmunshiName if self.billmunshiName else "Unnamed Bill"

    def save(self, *args, **kwargs):
        """
        Automatically generates a unique billmunshiName if not provided.
        """
        if not self.billmunshiName:
            highest_bill = TallyVendorBill.objects.filter(billmunshiName__startswith='BM-TB-').order_by(
                '-billmunshiName').first()
            if highest_bill:
                match = re.match(r'BM-TB-(\d+)', highest_bill.billmunshiName)
                next_number = int(match.group(1)) + 1 if match else 1
            else:
                next_number = 1

            self.billmunshiName = f'BM-TB-{next_number}'

        super().save(*args, **kwargs)


##### Vendor Analyzed Bill
class TallyVendorAnalyzedBill(BaseTeamModel):
    """
    Stores analyzed vendor bill details.
    """
    TAX_CHOICES = (
        ('TCS', 'is_tcs_tax'),
        ('TDS', 'is_tds_tax'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    selectBill = models.ForeignKey(TallyVendorBill, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                               related_name="vendor_tally_vendor_analyzed_bills")
    bill_no = models.CharField(max_length=50, null=True, blank=True)
    bill_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    igst_taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="igst_tally_vendor_analyzed_bills")
    cgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    cgst_taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="cgst_tally_vendor_analyzed_bills")
    sgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    sgst_taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="sgst_tally_vendor_analyzed_bills")
    note = models.TextField(null=True, blank=True, default="Enter Your Description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Tally Vendor Analyzed Bills"

    def __str__(self):
        return self.selectBill.billmunshiName if self.selectBill else "Unnamed Bill"


##### Vendor Analyzed Product
class TallyVendorAnalyzedProduct(BaseTeamModel):
    """
    Stores analyzed products from vendor bills.
    """

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    vendor_bill_analyzed = models.ForeignKey(TallyVendorAnalyzedBill, on_delete=models.CASCADE, related_name='products')
    item_name = models.CharField(max_length=100, null=True, blank=True)
    item_details = models.TextField(null=True, blank=True)
    taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Tally Analyzed Bill Products"

    def __str__(self):
        return self.item_name if self.item_name else "Unnamed Product"


#### Expense Journal Bill
class TallyExpenseBill(BaseTeamModel):
    """
    Stores expense bill details with an automated bill name generation.
    """
    BILL_STATUS = (
        ('Draft', 'Draft'),
        ('Analyzed', 'Analyzed'),
        ('Verified', 'Verified'),
        ('Synced', 'Synced')
    )

    BILL_TYPE = (
        ('Single Invoice/File', 'Single Invoice/File'),
        ('Multiple Invoice/File', 'Multiple Invoice/File'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    billmunshiName = models.CharField(max_length=100, null=True, blank=True)
    file = models.FileField(upload_to='bills/', validators=[validate_file_extension])
    fileType = models.CharField(choices=BILL_TYPE, max_length=100, null=True, blank=True, default="Single Invoice/File")
    analysed_data = models.JSONField(default=dict, null=True, blank=True)
    status = models.CharField(max_length=10, choices=BILL_STATUS, default='Draft', blank=True)
    process = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Fixed typo: update_at -> updated_at

    class Meta:
        verbose_name_plural = 'Tally Expense Bills'

    def __str__(self):
        return self.billmunshiName if self.billmunshiName else "Unnamed Bill"

    def save(self, *args, **kwargs):
        """
        Automatically generates a unique billmunshiName if not provided.
        """
        if not self.billmunshiName:
            highest_bill = TallyExpenseBill.objects.filter(billmunshiName__startswith='BM-TB-').order_by(
                '-billmunshiName').first()
            if highest_bill:
                match = re.match(r'BM-TE-(\d+)', highest_bill.billmunshiName)
                next_number = int(match.group(1)) + 1 if match else 1
            else:
                next_number = 1

            self.billmunshiName = f'BM-TE-{next_number}'

        super().save(*args, **kwargs)


#### Expense Journal Analyzed Bill
class TallyExpenseAnalyzedBill(BaseTeamModel):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    selectBill = models.ForeignKey(TallyExpenseBill, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                               related_name="vendor_tally_expense_analyzed_bills")
    voucher = models.CharField(max_length=255, null=True, blank=True)
    bill_no = models.CharField(max_length=50, null=True, blank=True)
    bill_date = models.DateField(null=True, blank=True)
    total = models.CharField(max_length=50, null=True, blank=True, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    igst_taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="igst_tally_expense_analyzed_bills")
    cgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    cgst_taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="cgst_tally_expense_analyzed_bills")
    sgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    sgst_taxes = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="sgst_tally_expense_analyzed_bills")
    note = models.CharField(max_length=100, null=True, blank=True, default="Enter Your Description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Expense Analyzed Bill"

    def __str__(self):
        return self.selectBill.billmunshiName if self.selectBill else "Unnamed Bill"


#### Expense Journal Analyzed Product
class TallyExpenseAnalyzedProduct(BaseTeamModel):
    EXPENSE_TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    expense_bill = models.ForeignKey(TallyExpenseAnalyzedBill, related_name='products', on_delete=models.CASCADE)
    item_details = models.CharField(max_length=200, null=True, blank=True)
    chart_of_accounts = models.ForeignKey(Ledger, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.CharField(max_length=10, null=True, blank=True)
    debit_or_credit = models.CharField(choices=EXPENSE_TYPE_CHOICES, max_length=10, null=True, blank=True,
                                       default='credit')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Expense Analysed Bill Products"

    def __str__(self):
        return self.expense_bill.selectBill.billmunshiName
