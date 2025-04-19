import os
import json
import base64
from io import BytesIO
import requests
import logging
from datetime import datetime
from PyPDF2 import PdfReader
from pdf2image import convert_from_bytes
from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models.functions import Lower
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
# OpenAI Import
from openai import OpenAI

from apps.bills.tally.api.api_views import TallyVendor
from apps.teams.decorators import login_and_team_required
from apps.bills.tally.forms import (
    ExpenseBillForm, ExpenseAnalyzedBillForm, ExpenseAnalyzedProductForm, ExpenseProductFormSet
)
from apps.bills.tally.models import (
    TallyExpenseBill, TallyExpenseAnalyzedBill, TallyExpenseAnalyzedProduct
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)


# ✅ Expense Bills List
@login_and_team_required(login_url='account_login')
def expense_bills(request, team_slug):
    """
    Retrieves all expense bills for the current team and displays them in the expense main page.
    """
    bills = TallyExpenseBill.objects.filter(team=request.team).order_by('-created_at')
    context = {'bills': bills, 'heading': 'Expense Bills List'}
    return render(request, 'tally/expense/main.html', context)


# ✅ Create Expense Bill
@login_and_team_required(login_url='account_login')
def expense_bill_create(request, team_slug):
    """
    Handles vendor bill creation, including splitting PDFs for multiple invoices.
    """
    if request.method == 'POST':
        form = ExpenseBillForm(request.POST, request.FILES)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.team = request.team

            # Restrict PDF uploads for 'Single Invoice/File'
            if bill.fileType == 'Single Invoice/File' and bill.file.name.endswith('.pdf'):
                messages.error(request, 'PDF upload is not allowed for Single Invoice/File.')
                return redirect('tally:expense_bill_list', team_slug=team_slug)

            # Handle PDF splitting for 'Multiple Invoice/File'
            if bill.fileType == 'Multiple Invoice/File' and bill.file.name.endswith('.pdf'):
                try:
                    bill.file.seek(0)  # Ensure file is at the beginning
                    pdf_bytes = bill.file.read()  # Read the PDF once
                    pdf = PdfReader(BytesIO(pdf_bytes))
                    unique_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    for page_num in range(len(pdf.pages)):
                        # Convert each PDF page to an image
                        page_images = convert_from_bytes(pdf_bytes, first_page=page_num + 1, last_page=page_num + 1)

                        if page_images:
                            image_io = BytesIO()
                            page_images[0].save(image_io, format='JPEG')
                            image_io.seek(0)

                            # Create separate VendorBill for each page
                            TallyExpenseBill.objects.create(
                                billmunshiName=f"BM-Page-{page_num + 1}-{unique_id}",
                                file=ContentFile(image_io.read(), name=f"BM-Page-{page_num + 1}-{unique_id}.jpg"),
                                fileType=bill.fileType,
                                status=bill.status,
                                team=request.team
                            )

                    messages.success(request, 'Bill uploaded and split successfully!')
                    return redirect('tally:expense_bill_list', team_slug=team_slug)

                except Exception as e:
                    messages.error(request, f'Error processing PDF: {str(e)}')
                    return redirect('tally:expense_bill_list', team_slug=team_slug)

            # Save bill for non-PDF uploads
            bill.save()
            messages.success(request, 'Bill uploaded successfully!')
            return redirect('tally:expense_bill_list', team_slug=team_slug)
    else:
        form = ExpenseBillForm()

    return render(request, 'tally/expense/bill_upload.html', {'form': form, 'heading': 'Create Vendor Bill'})


# ✅ Delete Expense Bill
@login_and_team_required(login_url='account_login')
def expense_bill_delete(request, team_slug, bill_id):
    """
    Deletes an expense bill and removes its associated file from storage.
    """
    bill = get_object_or_404(TallyExpenseBill, id=bill_id)

    # Delete the file from storage if it exists
    if bill.file:
        file_path = os.path.join(settings.MEDIA_ROOT, str(bill.file))
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete the bill record from the database
    bill.delete()

    messages.success(request, 'Expense bill and associated file deleted successfully!')
    return redirect('tally:expense_bill_list', team_slug=team_slug)


# ✅ Draft Expense Bills
@login_and_team_required(login_url='account_login')
def expense_bill_drafts(request, team_slug):
    """
    Retrieves all draft expense bills for the current team.
    """
    draft_bills = TallyExpenseBill.objects.filter(team=request.team, status="Draft")
    context = {'draft_bills': draft_bills, 'heading': 'Draft Expense Bills'}
    return render(request, 'tally/expense/draft.html', context)


# ✅ Analyzed Expense Bills
@login_and_team_required(login_url='account_login')
def expense_bill_analyzed(request, team_slug):
    """
    Retrieves all analyzed expense bills.
    """
    analyzed_bills = TallyExpenseBill.objects.filter(
        Q(team=request.team) & (Q(status="Analyzed") | Q(status="Verified"))
    )
    context = {'analyzed_bills': analyzed_bills, 'heading': 'Analyzed Expense Bills'}
    return render(request, 'tally/expense/analyzed.html', context)


# ✅ Synced Expense Bills
@login_and_team_required(login_url='account_login')
def expense_bill_synced(request, team_slug):
    """
    Retrieves all synced expense bills.
    """
    synced_bills = TallyExpenseBill.objects.filter(team=request.team, status="Synced")
    context = {'synced_bills': synced_bills, 'heading': 'Synced Expense Bills'}
    return render(request, 'tally/expense/synced.html', context)


# ✅ View Bill
@login_and_team_required(login_url='account_login')
def view_bill(request, team_slug, bill_id):
    """
    Returns the bill image URL as a JSON response.
    """
    bill = get_object_or_404(TallyExpenseBill, id=bill_id)

    if bill.file:
        return JsonResponse({"image_url": bill.file.url})
    else:
        return JsonResponse({"error": "No bill image found"}, status=404)


# ✅Analyze & Process Expense Bill
@login_and_team_required(login_url='account_login')
def expense_bill_analysis_process(request, team_slug, bill_id):
    """
    Analyzes and processes a vendor bill using AI.
    """
    bill = get_object_or_404(TallyExpenseBill, id=bill_id)

    # Read the file and convert to Base64
    try:
        with open(bill.file.path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as error:
        logger.error(f"Error reading bill file: {error}")
        messages.warning(request, 'Error reading the bill file.')
        return redirect('tally:vendor_bill_list', team_slug=team_slug)

    # JSON Schema for AI extraction
    invoice_schema = {
        "$schema": "http://json-schema.org/draft/2020-12/schema",
        "title": "Invoice",
        "description": "A simple invoice format",
        "type": "object",
        "properties": {
            "invoiceNumber": {"type": "string"},
            "dateIssued": {"type": "string", "format": "date"},
            "dueDate": {"type": "string", "format": "date"},
            "from": {"type": "object", "properties": {"name": {"type": "string"}, "address": {"type": "string"}}},
            "to": {"type": "object", "properties": {"name": {"type": "string"}, "address": {"type": "string"}}},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "price": {"type": "number"}
                    }
                }
            },
            "total": {"type": "number"},
            "igst": {"type": "number"},
            "cgst": {"type": "number"},
            "sgst": {"type": "number"}
        }
    }

    # AI Processing Request
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": f"Extract invoice data in JSON format using this schema: {json.dumps(invoice_schema)}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }],
            max_tokens=1000
        )
        json_data = json.loads(response.choices[0].message.content)
    except Exception as error:
        logger.error(f"AI processing failed: {error}")
        messages.warning(request, 'AI processing failed.')
        return redirect('tally:vendor_bill_list', team_slug=team_slug)

    # Save extracted data to the bill object
    try:
        relevant_data = json_data if "properties" not in json_data else {
            "invoiceNumber": json_data["properties"]["invoiceNumber"]["const"],
            "dateIssued": json_data["properties"]["dateIssued"]["const"],
            "dueDate": json_data["properties"]["dueDate"]["const"],
            "from": json_data["properties"]["from"]["properties"],
            "to": json_data["properties"]["to"]["properties"],
            "items": [
                {
                    "description": item["description"]["const"],
                    "quantity": item["quantity"]["const"],
                    "price": item["price"]["const"]
                } for item in json_data["properties"]["items"]["items"]
            ],
            "total": json_data["properties"]["total"]["const"],
            "igst": json_data["properties"]["igst"]["const"],
            "cgst": json_data["properties"]["cgst"]["const"],
            "sgst": json_data["properties"]["sgst"]["const"],
        }

        bill.analysed_data = relevant_data
        bill.save(update_fields=['analysed_data'])
    except Exception as error:
        logger.error(f"Error saving bill data: {error}")
        messages.warning(request, 'Error saving Bill data.')
        return redirect('tally:expense_bill_list', team_slug=team_slug)

    # Extract required fields safely
    try:
        invoice_number = relevant_data.get('invoiceNumber', '').strip()
        date_issued = relevant_data.get('dateIssued', '')
        date_issued = datetime.strptime(date_issued, '%Y-%m-%d').date() if date_issued else None

        # Create ExpenseAnalyzedBill entry
        analyzed_bill = TallyExpenseAnalyzedBill.objects.create(
            selectBill=bill,
            voucher=invoice_number,
            bill_no=invoice_number,
            bill_date=date_issued,
            igst=str(float(relevant_data.get('igst', 0) or 0)),
            cgst=str(float(relevant_data.get('cgst', 0) or 0)),
            sgst=str(float(relevant_data.get('sgst', 0) or 0)),
            total=str(float(relevant_data.get('total', 0) or 0)),
            note="AI Analyzed Bill",
            team=request.team
        )

        # Bulk create ExpenseAnalyzedProduct entries
        product_instances = []
        for item in relevant_data.get('items', []):
            price = float(item.get('price', 0) or 0)
            quantity = float(item.get('quantity', 0) or 0)
            amount = price * quantity

            product_instances.append(
                TallyExpenseAnalyzedProduct(
                    expense_bill=analyzed_bill,
                    item_details=item.get('description', ''),
                    amount=str(amount),  # Convert to string
                    team=request.team
                )
            )

        TallyExpenseAnalyzedProduct.objects.bulk_create(product_instances)

        # Update bill status
        bill.status = "Analyzed"
        bill.process = True
        bill.save(update_fields=['status', 'process'])

        messages.success(request, 'Bill analyzed and processed successfully!')

    except (KeyError, ValueError) as e:
        logger.error(f"Data parsing error: {e}")
        messages.warning(request, f'Missing expected data: {e}')
        return redirect('tally:expense_bill_list', team_slug=team_slug)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        messages.warning(request, f'An error occurred: {e}')
        return redirect('tally:expense_bill_list', team_slug=team_slug)

    return redirect('tally:expense_bill_list', team_slug=team_slug)


# ✅ Verify Expense Bill
@login_and_team_required(login_url='account_login')
def expense_bill_verification_process(request, team_slug, bill_id):
    """
    Marks a bill as verified.
    """
    detailBill = get_object_or_404(TallyExpenseBill, id=bill_id)
    analysed_bill = get_object_or_404(TallyExpenseAnalyzedBill, selectBill=detailBill)
    analysed_products = TallyExpenseAnalyzedProduct.objects.filter(expense_bill=analysed_bill).all()

    if request.method == 'POST':
        bill_form = ExpenseAnalyzedBillForm(request.POST, instance=analysed_bill, team=request.team)  # ✅ Pass team
        formset = ExpenseProductFormSet(request.POST, queryset=analysed_products, team=request.team)  # ✅ Pass team

        if bill_form.is_valid() and formset.is_valid():
            analysed_bill = bill_form.save(commit=False)
            analysed_bill.selectBill = detailBill
            analysed_bill.team = request.team
            analysed_bill.save()

            for form in formset:
                if form.cleaned_data.get('item_details'):
                    formset_data = form.save(commit=False)
                    formset_data.expense_bill = analysed_bill  # ✅ Correct foreign key reference
                    formset_data.team = request.team
                    formset_data.save()
                elif form.instance.pk:  # If the form instance exists but has no valid data, delete it
                    form.instance.delete()

            detailBill.status = "Verified"
            detailBill.save()
            return redirect('tally:expense_bill_analyzed', team_slug=team_slug)
        else:
            print("Forms Error:", bill_form.errors)
            print("Formset Error:", formset.errors)
            messages.warning(request, 'Server Error! Contact Service Provider')
            return redirect('tally:expense_bill_analyzed', team_slug=team_slug)

    else:
        bill_form = ExpenseAnalyzedBillForm(instance=analysed_bill, team=request.team)
        formset = ExpenseProductFormSet(queryset=analysed_products, team=request.team)

    context = {
        'detailBill': detailBill,
        'bill_form': bill_form,
        'formset': formset,
        'analysed_products': analysed_products,
        "heading": "Bill Verification"
    }
    return render(request, 'tally/expense/verify_bill.html', context)


# 🚀 Sync Expense Bill with tally
@login_and_team_required(login_url='account_login')
def expense_bill_sync_process(request, team_slug, bill_id):
    """
    Syncs an expense bill with Tally.
    """
    try:
        # Fetch the bill details
        billSyncProcess = get_object_or_404(TallyExpenseAnalyzedBill, selectBill=bill_id)
        tally_products = billSyncProcess.products.all()  # ✅ Using related_name='products'

        # Fetch vendor details (Handle missing vendor scenario)
        vendor_ledger = billSyncProcess.vendor
        vendor_details = {
            "name": vendor_ledger.name if vendor_ledger else "No Vendor",
            "company": vendor_ledger.company if vendor_ledger else "No Company",
            "gst_in": vendor_ledger.gst_in if vendor_ledger else "No GST",
        }

        # Construct the payload
        bill_data = {
            "bill_id": str(billSyncProcess.id),
            "bill_details": {
                "reference_number": billSyncProcess.bill_no or "N/A",
                "bill_date": billSyncProcess.bill_date.strftime('%Y-%m-%d') if billSyncProcess.bill_date else None,
                "voucher": billSyncProcess.voucher or "N/A",
                "total_amount": float(billSyncProcess.total) if billSyncProcess.total else 0.0,
                "company_id": team_slug,
            },
            "vendor": vendor_details,
            "taxes": {
                "igst": {
                    "amount": float(billSyncProcess.igst) if billSyncProcess.igst else 0.0,
                    "ledger": str(billSyncProcess.igst_taxes) if billSyncProcess.igst_taxes else "No Tax Ledger",
                    "debit_or_credit": "debit"
                },
                "cgst": {
                    "amount": float(billSyncProcess.cgst) if billSyncProcess.cgst else 0.0,
                    "ledger": str(billSyncProcess.cgst_taxes) if billSyncProcess.cgst_taxes else "No Tax Ledger",
                    "debit_or_credit": "debit"
                },
                "sgst": {
                    "amount": float(billSyncProcess.sgst) if billSyncProcess.sgst else 0.0,
                    "ledger": str(billSyncProcess.sgst_taxes) if billSyncProcess.sgst_taxes else "No Tax Ledger",
                    "debit_or_credit": "debit"
                }
            },
            "notes": billSyncProcess.note or "No Notes",
            "line_items": [
                {
                    "item_details": item.item_details or "N/A",
                    "chart_of_accounts": str(item.chart_of_accounts.name) if item.chart_of_accounts else "No Chart",
                    "amount": float(item.amount) if item.amount else 0.0,
                    "debit_or_credit": item.debit_or_credit or "credit",
                }
                for item in tally_products
            ]
        }

        # Debugging - Print the JSON payload before sending it
        print(json.dumps(bill_data, indent=2))

        # API URL for syncing data
        api_url = f'{settings.SERVER_URL}/org/{team_slug}/bills/tally/api/v1/expense/'

        # Send the POST request to Tally API
        response = requests.post(api_url, json=bill_data)

        if response.status_code == 200:
            # Update bill status to "Synced"
            billStatusUpdate = get_object_or_404(TallyExpenseBill, id=bill_id)
            billStatusUpdate.status = "Synced"
            billStatusUpdate.save()

            messages.success(request, "Expense Bill synced successfully with Tally.")
            return redirect('tally:expense_bill_synced', team_slug=team_slug)
        else:
            response_json = response.json()
            error_message = response_json.get("message", "Failed to send data to Tally")
            messages.error(request, error_message)
            return redirect('tally:expense_bill_analyzed', team_slug=team_slug)

    except TallyExpenseAnalyzedBill.DoesNotExist:
        messages.error(request, "The specified bill does not exist.")
        return redirect('tally:expense_bill_analyzed', team_slug=team_slug)
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect('tally:expense_bill_analyzed', team_slug=team_slug)


# ✅View Synced Bill in detail
@login_and_team_required(login_url='account_login')
def expense_synced_bill_detail(request, team_slug, bill_id):
    detailBill = get_object_or_404(TallyExpenseBill, id=bill_id)
    analysed_bill = get_object_or_404(TallyExpenseAnalyzedBill, selectBill=detailBill)
    analysed_products = TallyExpenseAnalyzedProduct.objects.filter(expense_bill=analysed_bill).all()
    bill_form = ExpenseAnalyzedBillForm(instance=analysed_bill, team=request.team)
    formset = ExpenseProductFormSet(queryset=analysed_products, team=request.team)
    context = {'detailBill': detailBill, 'bill_form': bill_form, 'formset': formset,
               'analysed_products': analysed_products, "heading": "Bill Synced"}
    return render(request, 'tally/expense/synced_detail.html', context)
