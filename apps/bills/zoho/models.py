import re
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Max
from apps.teams.models import BaseTeamModel


##### Zoho Settings
class ZohoCredentials(BaseTeamModel):
    """
    Stores Zoho API credentials for each team.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    clientId = models.CharField(max_length=100)
    clientSecret = models.CharField(max_length=100)
    accessCode = models.CharField(max_length=200, default="Your Access Code")
    organisationId = models.CharField(max_length=100, default="Your organisationId")
    redirectUrl = models.CharField(max_length=200, default="Your Redirect URL")
    accessToken = models.CharField(max_length=200, null=True, blank=True)
    refreshToken = models.CharField(max_length=200, null=True, blank=True)
    onboarding_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Fixed typo: update_at -> updated_at

    def __str__(self):
        return self.team.name

    class Meta:
        verbose_name_plural = "Zoho Credentials"


##### Zoho Vendor
class ZohoVendor(BaseTeamModel):
    """
    Stores vendor details from Zoho.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    contactId = models.CharField(max_length=100, unique=True)
    companyName = models.CharField(max_length=100)
    gstNo = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.companyName

    class Meta:
        verbose_name_plural = "Zoho Vendors"


##### Zoho Chart of Accounts (COA)
class ZohoChartOfAccount(BaseTeamModel):
    """
    Stores Zoho's chart of accounts information.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    accountId = models.CharField(max_length=100, unique=True)
    accountName = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.accountName

    class Meta:
        verbose_name_plural = "Zoho Chart of Accounts"


##### Zoho Taxes
class ZohoTaxes(BaseTeamModel):
    """
    Stores tax-related information from Zoho.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    taxId = models.CharField(max_length=100, unique=True)
    taxName = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.taxName

    class Meta:
        verbose_name_plural = "Zoho Taxes"


##### Zoho TDS/TCS
class ZohoTdsTcs(BaseTeamModel):
    """
    Stores TDS and TCS tax details.
    """
    TAX_CHOICES = (
        ('TCS', 'tcs_tax'),
        ('TDS', 'tds_tax'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    taxId = models.CharField(max_length=100, unique=True)
    taxName = models.CharField(max_length=100)
    taxPercentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)
    taxType = models.CharField(choices=TAX_CHOICES, max_length=10, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.taxName} ({self.taxPercentage}%)"

    class Meta:
        verbose_name_plural = "Zoho TDS and TCS Taxes"


##### Zoho Vendor Credits
class ZohoVendorCredits(BaseTeamModel):
    """
    Stores vendor credit details.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    vendor_id = models.CharField(max_length=100, null=True, blank=True)
    vendor_name = models.CharField(max_length=100, null=True, blank=True)
    vendor_credit_id = models.CharField(max_length=100, null=True, blank=True)
    vendor_credit_number = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.vendor_name

    class Meta:
        verbose_name_plural = "Zoho Vendor Credits"


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
class VendorBill(BaseTeamModel):
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
        verbose_name_plural = 'Vendor Bills'

    def __str__(self):
        return self.billmunshiName if self.billmunshiName else "Unnamed Bill"

    def save(self, *args, **kwargs):
        """
        Automatically generates a unique billmunshiName if not provided.
        """
        if not self.billmunshiName:
            highest_bill = VendorBill.objects.filter(billmunshiName__startswith='BM-ZV-').order_by(
                '-billmunshiName').first()
            if highest_bill:
                match = re.match(r'BM-ZV-(\d+)', highest_bill.billmunshiName)
                next_number = int(match.group(1)) + 1 if match else 1
            else:
                next_number = 1

            self.billmunshiName = f'BM-ZV-{next_number}'

        super().save(*args, **kwargs)


##### Vendor Analyzed Bill
class VendorAnalyzedBill(BaseTeamModel):
    """
    Stores analyzed vendor bill details.
    """
    TAX_CHOICES = (
        ('TCS', 'is_tcs_tax'),
        ('TDS', 'is_tds_tax'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    selectBill = models.ForeignKey(VendorBill, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(ZohoVendor, on_delete=models.CASCADE, null=True, blank=True)
    bill_no = models.CharField(max_length=50, null=True, blank=True)
    bill_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    cgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    tds_tcs_id = models.ForeignKey(ZohoTdsTcs, on_delete=models.CASCADE, null=True, blank=True)
    is_tax = models.CharField(choices=TAX_CHOICES, max_length=10, null=True, blank=True, default='TDS')
    note = models.TextField(null=True, blank=True, default="Enter Your Description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Analyzed Bills"

    def __str__(self):
        return self.selectBill.billmunshiName if self.selectBill else "Unnamed Bill"


##### Vendor Analyzed Product
class VendorAnalyzedProduct(BaseTeamModel):
    """
    Stores analyzed products from vendor bills.
    """
    ITC_ELIGIBILITY_CHOICES = (
        ('eligible', 'Eligible'),
        ('ineligible_section17', 'Ineligible Section17'),
        ('ineligible_others', 'Ineligible Others'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    vendor_bill_analyzed = models.ForeignKey(VendorAnalyzedBill, on_delete=models.CASCADE, related_name='products')
    item_name = models.CharField(max_length=100, null=True, blank=True)
    item_details = models.TextField(null=True, blank=True)
    chart_of_accounts = models.ForeignKey(ZohoChartOfAccount, on_delete=models.CASCADE, null=True, blank=True)
    taxes = models.ForeignKey(ZohoTaxes, on_delete=models.CASCADE, null=True, blank=True)
    reverse_charge_tax_id = models.BooleanField(default=False)
    itc_eligibility = models.CharField(choices=ITC_ELIGIBILITY_CHOICES, max_length=50, null=True, blank=True,
                                       default='eligible')
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Analyzed Bill Products"

    def __str__(self):
        return self.item_name if self.item_name else "Unnamed Product"


##### Expense Bill Upload
class ExpenseBill(BaseTeamModel):
    """
    Stores expense bill details.
    """
    BILL_STATUS = (
        ('Draft', 'Draft'),
        ('Analyzed', 'Analyzed'),
        ('Verified', 'Verified'),
        ('Synced', 'Synced'),
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
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Expense Bills"

    def __str__(self):
        return self.billmunshiName if self.billmunshiName else "Unnamed Expense Bill"

    def save(self, *args, **kwargs):
        """
        Automatically generates a unique billmunshiName if not provided.
        """
        if not self.billmunshiName:
            highest_bill = ExpenseBill.objects.filter(billmunshiName__startswith='BM-ZE-').order_by(
                '-billmunshiName').first()
            if highest_bill:
                match = re.match(r'BM-ZE-(\d+)', highest_bill.billmunshiName)
                next_number = int(match.group(1)) + 1 if match else 1
            else:
                next_number = 1

            self.billmunshiName = f'BM-ZE-{next_number}'

        super().save(*args, **kwargs)


##### Expense Analyzed Bill
class ExpenseAnalyzedBill(BaseTeamModel):
    """
    Stores analyzed expense bill details.
    """
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    selectBill = models.ForeignKey(ExpenseBill, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(ZohoVendor, on_delete=models.CASCADE, null=True, blank=True)
    bill_no = models.CharField(max_length=50, null=True, blank=True)
    bill_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    cgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    note = models.TextField(null=True, blank=True, default="Enter Your Description")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Expense Analyzed Bills"

    def __str__(self):
        return self.selectBill.billmunshiName if self.selectBill else "Unnamed Expense Bill"


##### Expense Analyzed Product
class ExpenseAnalyzedProduct(BaseTeamModel):
    """
    Stores analyzed products from expense bills.
    """
    EXPENSE_TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)
    expense_analyzed_bill = models.ForeignKey(ExpenseAnalyzedBill, on_delete=models.CASCADE, related_name='products')
    item_details = models.TextField(null=True, blank=True)
    chart_of_accounts = models.ForeignKey(ZohoChartOfAccount, on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(ZohoVendor, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    debit_or_credit = models.CharField(choices=EXPENSE_TYPE_CHOICES, max_length=10, null=True, blank=True,
                                       default='credit')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Expense Analyzed Bill Products"

    def __str__(self):
        return self.expense_analyzed_bill.selectBill.billmunshiName if self.expense_analyzed_bill else "Unnamed Expense Product"
