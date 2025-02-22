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

from apps.teams.decorators import login_and_team_required
from apps.bills.zoho.forms import (
    ExpenseBillForm, ExpenseAnalyzedBillForm, ExpenseAnalyzedProductForm, ExpenseProductFormSet
)
from apps.bills.zoho.models import (
    ExpenseBill, ExpenseAnalyzedBill, ExpenseAnalyzedProduct, ZohoVendor,
    ZohoChartOfAccount, ZohoTaxes, ZohoCredentials
)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)


# ✅ Expense Bills List
@login_and_team_required(login_url='account_login')
def expense_bills(request, team_slug):
    """
    Retrieves all expense bills for the current team and displays them in the expense main page.
    """
    bills = ExpenseBill.objects.filter(team=request.team).order_by('-created_at')
    context = {'bills': bills, 'heading': 'Expense Bills List'}
    return render(request, 'zoho/expense/main.html', context)


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
                return redirect('zoho:expense_bill_list', team_slug=team_slug)

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
                            ExpenseBill.objects.create(
                                billmunshiName=f"BM-Page-{page_num + 1}-{unique_id}",
                                file=ContentFile(image_io.read(), name=f"BM-Page-{page_num + 1}-{unique_id}.jpg"),
                                fileType=bill.fileType,
                                status=bill.status,
                                team=request.team
                            )

                    messages.success(request, 'Bill uploaded and split successfully!')
                    return redirect('zoho:expense_bill_list', team_slug=team_slug)

                except Exception as e:
                    messages.error(request, f'Error processing PDF: {str(e)}')
                    return redirect('zoho:expense_bill_list', team_slug=team_slug)

            # Save bill for non-PDF uploads
            bill.save()
            messages.success(request, 'Bill uploaded successfully!')
            return redirect('zoho:expense_bill_list', team_slug=team_slug)
    else:
        form = ExpenseBillForm()

    return render(request, 'zoho/expense/bill_upload.html', {'form': form, 'heading': 'Create Vendor Bill'})


# ✅ Delete Expense Bill
@login_and_team_required(login_url='account_login')
def expense_bill_delete(request, team_slug, bill_id):
    """
    Deletes an expense bill and removes its associated file from storage.
    """
    bill = get_object_or_404(ExpenseBill, id=bill_id)

    # Delete the file from storage if it exists
    if bill.file:
        file_path = os.path.join(settings.MEDIA_ROOT, str(bill.file))
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete the bill record from the database
    bill.delete()

    messages.success(request, 'Expense bill and associated file deleted successfully!')
    return redirect('zoho:expense_bill_list', team_slug=team_slug)


# ✅ Draft Expense Bills
@login_and_team_required(login_url='account_login')
def expense_bill_drafts(request, team_slug):
    """
    Retrieves all draft expense bills for the current team.
    """
    draft_bills = ExpenseBill.objects.filter(team=request.team, status="Draft")
    context = {'draft_bills': draft_bills, 'heading': 'Draft Expense Bills'}
    return render(request, 'zoho/expense/draft.html', context)


# ✅ Analyzed Expense Bills
@login_and_team_required(login_url='account_login')
def expense_bill_analyzed(request, team_slug):
    """
    Retrieves all analyzed expense bills.
    """
    analyzed_bills = ExpenseBill.objects.filter(
        Q(team=request.team) & (Q(status="Analyzed") | Q(status="Verified"))
    )
    context = {'analyzed_bills': analyzed_bills, 'heading': 'Analyzed Expense Bills'}
    return render(request, 'zoho/expense/analyzed.html', context)


# ✅ Synced Expense Bills
@login_and_team_required(login_url='account_login')
def expense_bill_synced(request, team_slug):
    """
    Retrieves all synced expense bills.
    """
    synced_bills = ExpenseBill.objects.filter(team=request.team, status="Synced")
    context = {'synced_bills': synced_bills, 'heading': 'Synced Expense Bills'}
    return render(request, 'zoho/expense/synced.html', context)


# ✅ View Bill
@login_and_team_required(login_url='account_login')
def view_bill(request, team_slug, bill_id):
    """
    Returns the bill image URL as a JSON response.
    """
    bill = get_object_or_404(ExpenseBill, id=bill_id)

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
    bill = get_object_or_404(ExpenseBill, id=bill_id)

    # Read the file and convert to Base64
    try:
        with open(bill.file.path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as error:
        logger.error(f"Error reading bill file: {error}")
        messages.warning(request, 'Error reading the bill file.')
        return redirect('zoho:vendor_bill_list', team_slug=team_slug)

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
        return redirect('zoho:vendor_bill_list', team_slug=team_slug)

    # Save extracted data to the bill object
    try:
        if "properties" in json_data:
            relevant_data = {
                "invoiceNumber": json_data["properties"]["invoiceNumber"]["const"],
                "dateIssued": json_data["properties"]["dateIssued"]["const"],
                "dueDate": json_data["properties"]["dueDate"]["const"],
                "from": json_data["properties"]["from"]["properties"],
                "to": json_data["properties"]["to"]["properties"],
                "items": [{"description": item["description"]["const"], "quantity": item["quantity"]["const"],
                           "price": item["price"]["const"]} for item in json_data["properties"]["items"]["items"]],
                "total": json_data["properties"]["total"]["const"],
                "igst": json_data["properties"]["igst"]["const"],
                "cgst": json_data["properties"]["cgst"]["const"],
                "sgst": json_data["properties"]["sgst"]["const"],
            }
        else:
            relevant_data = json_data
        bill.analysed_data = relevant_data
        bill.save(update_fields=['analysed_data'])
    except Exception as error:
        logger.error(f"Error saving bill data: {error}")
        messages.warning(request, 'Error saving Bill data.')
        return redirect('zoho:expense_bill_list', team_slug=team_slug)

    # Extract required fields safely
    try:
        invoice_number = relevant_data.get('invoiceNumber', '').strip()
        date_issued = relevant_data.get('dateIssued', '')
        company_name = relevant_data.get('from', {}).get('name', '').strip().lower()

        date_issued = datetime.strptime(date_issued, '%Y-%m-%d').date() if date_issued else None

        # Find vendor (case-insensitive search)
        vendor = ZohoVendor.objects.annotate(lower_name=Lower('companyName')).filter(
            lower_name=company_name).first()

        # Create ExpenseAnalyzedBill entry
        analyzed_bill = ExpenseAnalyzedBill.objects.create(
            selectBill=bill,
            vendor=vendor,
            bill_no=invoice_number,
            bill_date=date_issued,
            igst=relevant_data.get('igst', 0),
            cgst=relevant_data.get('cgst', 0),
            sgst=relevant_data.get('sgst', 0),
            total=relevant_data.get('total', 0),
            note="AI Analyzed Bill",
            team=request.team
        )

        # Bulk create ExpenseAnalyzedProduct entries
        product_instances = [
            ExpenseAnalyzedProduct(
                expense_analyzed_bill=analyzed_bill,
                item_details=item.get('description', ''),
                amount=item.get('price', 0) * item.get('quantity', 0),
                team=request.team
            ) for item in relevant_data.get('items', [])
        ]
        ExpenseAnalyzedProduct.objects.bulk_create(product_instances)

        # Update bill status
        bill.status = "Analyzed"
        bill.process = True
        bill.save(update_fields=['status', 'process'])

        messages.success(request, 'Bill analyzed and processed successfully!')

    except (KeyError, ValueError) as e:
        logger.error(f"Data parsing error: {e}")
        messages.warning(request, f'Missing expected data: {e}')
        return redirect('zoho:expense_bill_list', team_slug=team_slug)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        messages.warning(request, f'An error occurred: {e}')
        return redirect('zoho:expense_bill_list', team_slug=team_slug)

    return redirect('zoho:expense_bill_list', team_slug=team_slug)


# ✅Verify Expense Bill
@login_and_team_required(login_url='account_login')
def expense_bill_verification_process(request, team_slug, bill_id):
    """
    Marks a bill as verified.
    """
    detailBill = get_object_or_404(ExpenseBill, id=bill_id)
    analysed_bill = get_object_or_404(ExpenseAnalyzedBill, selectBill=detailBill)
    analysed_products = ExpenseAnalyzedProduct.objects.filter(expense_analyzed_bill=analysed_bill).all()
    if request.method == 'POST':
        bill_form = ExpenseAnalyzedBillForm(request.POST, instance=analysed_bill)
        formset = ExpenseProductFormSet(request.POST, queryset=analysed_products)
        if bill_form.is_valid() and formset.is_valid():
            analysed_bill = bill_form.save(commit=False)
            analysed_bill.selectBill = detailBill
            analysed_bill.team = request.team
            analysed_bill.save()
            for form in formset:
                # Check if the form has data in the required fields before saving
                if form.cleaned_data.get('item_details'):
                    formset_data = form.save(commit=False)
                    formset_data.expense_analyzed_bill = analysed_bill
                    formset_data.team = request.team
                    formset_data.save()
                else:
                    # If the form is empty or has default values, don't save it
                    if form.instance.pk:  # If it has an ID, it's already saved, so delete it
                        form.instance.delete()
            detailBill.status = "Verified"
            detailBill.save()
            return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)
        else:
            print("Forms Error:", bill_form.errors)
            print("Formset Error:", formset.errors)
            messages.warning(request, 'Server Error! Contact Service Provider')
            return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)
    else:
        bill_form = ExpenseAnalyzedBillForm(instance=analysed_bill)
        formset = ExpenseProductFormSet(queryset=analysed_products)
    context = {'detailBill': detailBill, 'bill_form': bill_form, 'formset': formset,
               'analysed_products': analysed_products, "heading": "Bill Verification"}
    return render(request, 'zoho/expense/verify_bill.html', context)


def refresh_zoho_access_token(currentToken):
    refresh_token = currentToken.refreshToken
    client_id = currentToken.clientId
    client_secret = currentToken.clientSecret
    url = f"https://accounts.zoho.in/oauth/v2/token?refresh_token={refresh_token}&client_id={client_id}&client_secret={client_secret}&grant_type=refresh_token"
    response = requests.post(url)
    if response.status_code == 200:
        new_access_token = response.json().get('access_token')
        currentToken.accessToken = new_access_token
        currentToken.save()
        return new_access_token
    else:
        return None


# 🚀 Sync Expense Bill with Zoho
@login_and_team_required(login_url='account_login')
def expense_bill_sync_process(request, team_slug, bill_id):
    """
    Marks an expense bill as synced with Zoho.
    """
    try:
        billSyncProcess = ExpenseAnalyzedBill.objects.get(selectBill=bill_id)
        zoho_products = billSyncProcess.products.all()

        vendorZohoId = ZohoVendor.objects.get(id=billSyncProcess.vendor_id)
        bill_date_str = billSyncProcess.bill_date.strftime('%Y-%m-%d')  # Convert date to yyyy-mm-dd string

        bill_data = {
            "reference_number": billSyncProcess.bill_no,
            "journal_date": bill_date_str,
            "notes": billSyncProcess.note,
            "line_items": []
        }

        for item in zoho_products:
            line_item = {
                "description": item.item_details,
                "account_id": str(ZohoChartOfAccount.objects.get(accountName=item.chart_of_accounts).accountId),
                "customer_id": str(ZohoVendor.objects.get(companyName=item.vendor).contactId),
                "amount": float(item.amount),
                "debit_or_credit": item.debit_or_credit
            }
            bill_data["line_items"].append(line_item)

        currentToken = ZohoCredentials.objects.get(team=request.team)
        url = f"https://www.zohoapis.in/books/v3/journals?organization_id={currentToken.organisationId}"
        payload = json.dumps(bill_data)
        headers = {
            'Authorization': f'Zoho-oauthtoken {currentToken.accessToken}',
        }
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 401:
            new_access_token = refresh_zoho_access_token(currentToken)
            if new_access_token:
                headers['Authorization'] = f'Zoho-oauthtoken {new_access_token}'
                response = requests.post(url, headers=headers, data=payload)

        if response.status_code == 201:
            billStatusUpdate = ExpenseBill.objects.get(id=bill_id)
            billStatusUpdate.status = "Synced"
            billStatusUpdate.save()
            messages.success(request, "Bill Synced Successfully")
            return redirect('zoho:expense_bill_synced', team_slug=team_slug)
        else:
            response_json = response.json()
            error_message = response_json.get("message", "Failed to send data to Zoho")
            messages.error(request, error_message)
            return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)

    except ExpenseAnalyzedBill.DoesNotExist:
        messages.error(request, "The specified bill does not exist.")
        return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)
    except ZohoVendor.DoesNotExist:
        messages.error(request, "Please select vendor against Accounts Payable item.")
        return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)
    except ZohoChartOfAccount.DoesNotExist:
        messages.error(request, "The specified chart of account does not exist.")
        return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)
    except ZohoCredentials.DoesNotExist:
        messages.error(request, "The Zoho credentials are not set.")
        return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect('zoho:expense_bill_analyzed', team_slug=team_slug)


# ✅View Synced Bill in detail
@login_and_team_required(login_url='account_login')
def expense_synced_bill_detail(request, team_slug, bill_id):
    detailBill = get_object_or_404(ExpenseBill, id=bill_id)
    analysed_bill = get_object_or_404(ExpenseAnalyzedBill, selectBill=detailBill)
    analysed_products = ExpenseAnalyzedProduct.objects.filter(expense_analyzed_bill=analysed_bill).all()
    bill_form = ExpenseAnalyzedBillForm(instance=analysed_bill)
    formset = ExpenseProductFormSet(queryset=ExpenseAnalyzedProduct.objects.filter(expense_analyzed_bill=analysed_bill))
    context = {'detailBill': detailBill, 'bill_form': bill_form, 'formset': formset,
               'analysed_products': analysed_products}
    return render(request, 'zoho/expense/synced_detail.html', context)
