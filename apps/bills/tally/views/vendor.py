import os
import json
import base64
import datetime
import logging
import requests
from io import BytesIO
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
from apps.bills.tally.forms import (
    TallyVendorBillForm, TallyVendorAnalyzedBillForm, TallyVendorAnalyzedProductForm, TallyVendorProductFormSet
)
from apps.bills.tally.models import (ParentLedger, Ledger, TallyVendorBill, TallyVendorAnalyzedBill,
                                     TallyVendorAnalyzedProduct)

client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)


# ✅
@login_and_team_required(login_url='account_login')
def vendor_bills(request, team_slug):
    """
    Retrieves all vendor bills for the current team and displays them in the vendor main page.
    """
    bills = TallyVendorBill.objects.filter(team=request.team).order_by('-created_at')
    context = {'bills': bills, 'heading': 'Vendor Bills List'}
    return render(request, 'tally/vendor/main.html', context)


# ✅
@login_and_team_required(login_url='account_login')
def bill_create(request, team_slug):
    """
    Handles vendor bill creation, including splitting PDFs for multiple invoices.
    """
    if request.method == 'POST':
        form = TallyVendorBillForm(request.POST, request.FILES)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.team = request.team

            # Restrict PDF uploads for 'Single Invoice/File'
            if bill.fileType == 'Single Invoice/File' and bill.file.name.endswith('.pdf'):
                messages.error(request, 'PDF upload is not allowed for Single Invoice/File.')
                return redirect('tally:vendor_bill_list', team_slug=team_slug)

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
                            TallyVendorBill.objects.create(
                                billmunshiName=f"BM-Page-{page_num + 1}-{unique_id}",
                                file=ContentFile(image_io.read(), name=f"BM-Page-{page_num + 1}-{unique_id}.jpg"),
                                fileType=bill.fileType,
                                status=bill.status,
                                team=request.team
                            )

                    messages.success(request, 'Bill uploaded and split successfully!')
                    return redirect('tally:vendor_bill_list', team_slug=team_slug)

                except Exception as e:
                    messages.error(request, f'Error processing PDF: {str(e)}')
                    return redirect('tally:vendor_bill_list', team_slug=team_slug)

            # Save bill for non-PDF uploads
            bill.save()
            messages.success(request, 'Bill uploaded successfully!')
            return redirect('tally:vendor_bill_list', team_slug=team_slug)
    else:
        form = TallyVendorBillForm()
    return render(request, 'tally/vendor/bill_upload.html', {'form': form, 'heading': 'Create Vendor Bill'})


# ✅
@login_and_team_required(login_url='account_login')
def bill_delete(request, team_slug, bill_id):
    """
    Deletes a vendor bill and removes its associated file from storage.
    """
    bill = get_object_or_404(TallyVendorBill, id=bill_id)

    # Delete the file from storage if it exists
    if bill.file:
        file_path = os.path.join(settings.MEDIA_ROOT, str(bill.file))
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete the bill record from the database
    bill.delete()

    messages.success(request, 'Bill and associated file deleted successfully!')
    return redirect('tally:vendor_bill_list', team_slug=team_slug)


# ✅
@login_and_team_required(login_url='account_login')
def bill_drafts(request, team_slug):
    """
    Retrieves all draft vendor bills for the current team.
    """
    draft_bills = TallyVendorBill.objects.filter(team=request.team, status="Draft")
    context = {'draft_bills': draft_bills, 'heading': 'Draft Vendor Bills'}
    return render(request, 'tally/vendor/draft.html', context)


# ✅
@login_and_team_required(login_url='account_login')
def bill_analyzed(request, team_slug):
    """
    Retrieves all analyzed vendor bills.
    """
    analyzed_bills = TallyVendorBill.objects.filter(
        Q(team=request.team) & (Q(status="Analyzed") | Q(status="Verified"))
    )
    context = {'analyzed_bills': analyzed_bills, 'heading': 'Analyzed Vendor Bills'}
    return render(request, 'tally/vendor/analyzed.html', context)


# ✅
@login_and_team_required(login_url='account_login')
def bill_synced(request, team_slug):
    """
    Retrieves all synced vendor bills.
    """
    synced_bills = TallyVendorBill.objects.filter(team=request.team, status="Synced")
    context = {'synced_bills': synced_bills, 'heading': 'Synced Vendor Bills'}
    return render(request, 'tally/vendor/synced.html', context)


# ✅
@login_and_team_required(login_url='account_login')
def view_bill(request, team_slug, bill_id):
    """
    Returns the bill image URL as a JSON response.
    """
    bill = get_object_or_404(TallyVendorBill, id=bill_id)

    if bill.file:
        return JsonResponse({"image_url": bill.file.url})
    else:
        return JsonResponse({"error": "No bill image found"}, status=404)


# ✅
@login_and_team_required(login_url='account_login')
def bill_analysis_process(request, team_slug, bill_id):
    """
    Analyzes and processes a vendor bill using AI.
    """
    bill = get_object_or_404(TallyVendorBill, id=bill_id)

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
        return redirect('tally:vendor_bill_list', team_slug=team_slug)

    # Extract required fields safely
    try:
        invoice_number = relevant_data.get('invoiceNumber', '').strip()
        date_issued = relevant_data.get('dateIssued', '')
        company_name = relevant_data.get('from', {}).get('name', '').strip().lower()

        date_issued = datetime.strptime(date_issued, '%Y-%m-%d').date() if date_issued else None

        try:
            parent_ledger = ParentLedger.objects.get(parent="Sundry Creditors")
            vendor_list = Ledger.objects.filter(parent=parent_ledger, team=request.team)

            # Find the matching vendor in vendor_list (Case-Insensitive Exact Match)
            vendor = vendor_list.filter(name__iexact=company_name).first()
            if not vendor:
                vendor = vendor_list.filter(name__icontains=company_name).first()
        except ParentLedger.DoesNotExist:
            vendor = None

        # Determine GST Type
        igst_val = float(relevant_data.get('igst') or 0)
        cgst_val = float(relevant_data.get('cgst') or 0)
        sgst_val = float(relevant_data.get('sgst') or 0)

        if igst_val > 0:
            gst_type = "Inter-State"
        elif cgst_val > 0 or sgst_val > 0:
            gst_type = "Intra-State"
        else:
            gst_type = "Unknown"

        # Create VendorAnalyzedBill entry
        analyzed_bill = TallyVendorAnalyzedBill.objects.create(
            selectBill=bill,
            vendor=vendor,
            bill_no=invoice_number,
            bill_date=date_issued,
            igst=igst_val,
            cgst=cgst_val,
            sgst=sgst_val,
            total=relevant_data.get('total', 0),
            note="AI Analyzed Bill",
            team=request.team,
            gst_type=gst_type
        )

        # Bulk create VendorAnalyzedProduct entries
        product_instances = [
            TallyVendorAnalyzedProduct(
                vendor_bill_analyzed=analyzed_bill,
                item_details=item.get('description', ''),
                price=float(item.get('price', 0) or 0),
                quantity=int(item.get('quantity', 0) or 0),
                amount=float(item.get('price', 0) or 0) * int(item.get('quantity', 0) or 0),
                team=request.team
            ) for item in relevant_data.get('items', [])
        ]
        TallyVendorAnalyzedProduct.objects.bulk_create(product_instances)

        # Update bill status
        bill.status = "Analyzed"
        bill.process = True
        bill.save(update_fields=['status', 'process'])

        messages.success(request, 'Bill analyzed and processed successfully!')

    except (KeyError, ValueError) as e:
        logger.error(f"Data parsing error: {e}")
        messages.warning(request, f'Missing expected data: {e}')
        return redirect('tally:vendor_bill_list', team_slug=team_slug)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        messages.warning(request, f'An error occurred: {e}')
        return redirect('tally:vendor_bill_list', team_slug=team_slug)

    return redirect('tally:vendor_bill_analyzed', team_slug=team_slug)


# ✅
@login_and_team_required(login_url='account_login')
def bill_verification_process(request, team_slug, bill_id):
    """
    Marks a bill as verified after validating product-level tax totals
    against bill-level taxes.
    """
    detailBill = get_object_or_404(TallyVendorBill, id=bill_id)
    analysed_bill = get_object_or_404(TallyVendorAnalyzedBill, selectBill=detailBill)
    analysed_products = TallyVendorAnalyzedProduct.objects.filter(vendor_bill_analyzed=analysed_bill).all()

    if request.method == 'POST':
        bill_form = TallyVendorAnalyzedBillForm(request.POST)

        # Update bill fields
        analysed_bill.vendor_id = request.POST.get('vendor')
        analysed_bill.note = request.POST.get('note')
        analysed_bill.bill_no = request.POST.get('bill_no')
        analysed_bill.bill_date = request.POST.get('bill_date')
        analysed_bill.cgst = float(request.POST.get('cgst') or 0)
        analysed_bill.sgst = float(request.POST.get('sgst') or 0)
        analysed_bill.igst = float(request.POST.get('igst') or 0)

        try:
            cgst_taxes_id = request.POST.get('cgst_taxes')
            if cgst_taxes_id:
                analysed_bill.cgst_taxes = Ledger.objects.get(id=cgst_taxes_id)
            else:
                analysed_bill.cgst_taxes = None
        except Ledger.DoesNotExist:
            analysed_bill.cgst_taxes = None

        try:
            sgst_taxes_id = request.POST.get('sgst_taxes')
            if sgst_taxes_id:
                analysed_bill.sgst_taxes = Ledger.objects.get(id=sgst_taxes_id)
            else:
                analysed_bill.sgst_taxes = None
        except Ledger.DoesNotExist:
            analysed_bill.sgst_taxes = None

        try:
            igst_taxes_id = request.POST.get('igst_taxes')
            if igst_taxes_id:
                analysed_bill.igst_taxes = Ledger.objects.get(id=igst_taxes_id)
            else:
                analysed_bill.igst_taxes = None
        except Ledger.DoesNotExist:
            analysed_bill.igst_taxes = None

        # Initialize product tax totals
        total_product_igst = 0
        total_product_cgst = 0
        total_product_sgst = 0

        # Update product data
        for index, product in enumerate(analysed_products):
            taxes_key = f"form-{index}-taxes"
            amount_key = f"form-{index}-amount"
            product_gst_key = f"form-{index}-product_gst"

            taxes_id = request.POST.get(taxes_key)
            amount_val = request.POST.get(amount_key)
            product_gst = request.POST.get(product_gst_key)

            if taxes_id:
                try:
                    product.taxes = Ledger.objects.get(id=taxes_id)
                except Ledger.DoesNotExist:
                    product.taxes = None

            if amount_val:
                try:
                    product.amount = float(amount_val)
                except ValueError:
                    product.amount = 0

            if product_gst:
                product.product_gst = product_gst
                product.igst = 0
                product.cgst = 0
                product.sgst = 0

                try:
                    gst_percent = float(product_gst.strip('%')) if "%" in product_gst else 0
                    gst_amount = (gst_percent / 100) * float(product.amount or 0)

                    if analysed_bill.gst_type == "Inter-State":
                        product.igst = round(gst_amount, 2)
                        total_product_igst += product.igst
                    elif analysed_bill.gst_type == "Intra-State":
                        product.cgst = round(gst_amount / 2, 2)
                        product.sgst = round(gst_amount / 2, 2)
                        total_product_cgst += product.cgst
                        total_product_sgst += product.sgst

                except Exception as e:
                    logger.warning(f"GST calculation failed for product {index}: {e}")

            product.team = request.team
            product.save()

        # ✅ Verify tax consistency
        verification_passed = True
        if analysed_bill.gst_type == "Inter-State":
            if round(total_product_igst, 2) != round(analysed_bill.igst, 2):
                verification_passed = False
                messages.warning(request,
                                 f"IGST mismatch: Sum of product IGST = {total_product_igst}, Bill IGST = {analysed_bill.igst}")
        elif analysed_bill.gst_type == "Intra-State":
            if round(total_product_cgst, 2) != round(analysed_bill.cgst, 2) or \
                    round(total_product_sgst, 2) != round(analysed_bill.sgst, 2):
                verification_passed = False
                messages.warning(request,
                                 f"CGST/SGST mismatch: Products CGST/SGST = {total_product_cgst}/{total_product_sgst}, Bill CGST/SGST = {analysed_bill.cgst}/{analysed_bill.sgst}")

        if not verification_passed:
            return redirect('tally:vendor_bill_analyzed', team_slug=team_slug)

        # ✅ Mark as verified
        analysed_bill.team = request.team
        analysed_bill.save()
        detailBill.status = "Verified"
        detailBill.save()

        messages.success(request, "Bill verified successfully.")
        return redirect('tally:vendor_bill_analyzed', team_slug=team_slug)

    else:
        bill_form = TallyVendorAnalyzedBillForm(instance=analysed_bill, team=request.team)
        formset = TallyVendorProductFormSet(
            queryset=analysed_products,
            team=request.team
        )

    context = {
        'detailBill': detailBill,
        'bill_form': bill_form,
        'formset': formset,
        'analysed_products': analysed_products,
        "heading": "Bill Verification"
    }

    return render(request, 'tally/vendor/verify_bill.html', context)


# ✅
@login_and_team_required(login_url='account_login')
def bill_sync_process(request, team_slug, bill_id):
    """
    Marks a bill as synced with Tally.
    """
    try:
        analysed_bill = get_object_or_404(TallyVendorAnalyzedBill, selectBill=bill_id)
        analysed_bill_products = analysed_bill.products.all()

        # Fetch vendor ledger details
        vendor_ledger = Ledger.objects.filter(id=analysed_bill.vendor_id).first()

        # Convert bill date to string format (yyyy-mm-dd)
        bill_date_str = analysed_bill.bill_date.strftime('%Y-%m-%d') if analysed_bill.bill_date else None

        # Build the payload
        bill_data = {
            "vendor": {
                "master_id": vendor_ledger.master_id if vendor_ledger else "No Ledger",
                "name": vendor_ledger.name if vendor_ledger else "No Ledger",
                "gst_in": vendor_ledger.gst_in if vendor_ledger else "No Ledger",
                "company": vendor_ledger.company if vendor_ledger else "No Ledger",
            },
            "bill_details": {
                "bill_number": analysed_bill.bill_no,
                "date": bill_date_str,
                "total_amount": float(analysed_bill.total),
                "company_id": team_slug,
            },
            "taxes": {
                "igst": {
                    "amount": float(analysed_bill.igst),
                    "ledger": str(analysed_bill.igst_taxes) if analysed_bill.igst_taxes else "No Tax Ledger",
                },
                "cgst": {
                    "amount": float(analysed_bill.cgst),
                    "ledger": str(analysed_bill.cgst_taxes) if analysed_bill.cgst_taxes else "No Tax Ledger",
                },
                "sgst": {
                    "amount": float(analysed_bill.sgst),
                    "ledger": str(analysed_bill.sgst_taxes) if analysed_bill.sgst_taxes else "No Tax Ledger",
                }
            },
            "line_items": [
                {
                    "item_name": item.item_name,
                    "item_details": item.item_details,
                    "tax_ledger": str(item.taxes) if item.taxes else "No Tax Ledger",
                    "price": float(item.price),
                    "quantity": int(item.quantity),
                    "amount": float(item.amount),
                    "gst": item.product_gst,
                    "igst": float(item.igst or 0),
                    "cgst": float(item.cgst or 0),
                    "sgst": float(item.sgst or 0),
                }
                for item in analysed_bill_products
            ],
        }
        print(json.dumps(bill_data, indent=4))
        # API endpoint
        api_url = f'{settings.SERVER_URL}/org/{team_slug}/bills/tally/api/v1/vendor/'

        # Send POST request
        response = requests.post(api_url, json=bill_data)

        if response.status_code == 200:
            # Mark the bill as "Synced"
            TallyVendorBill.objects.filter(id=bill_id).update(status="Synced")
            messages.success(request, "Bill synced successfully with Tally.")
            return redirect('tally:vendor_bill_synced', team_slug=team_slug)
        else:
            response_json = response.json()
            error_message = response_json.get("message", "Failed to send data to Tally")
            messages.error(request, error_message)
            return redirect('tally:vendor_bill_analyzed', team_slug=team_slug)

    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect('tally:vendor_bill_analyzed', team_slug=team_slug)


# ✅
@login_and_team_required(login_url='account_login')
def synced_bill_detail(request, team_slug, bill_id):
    detailBill = get_object_or_404(TallyVendorBill, id=bill_id)
    analysed_bill = get_object_or_404(TallyVendorAnalyzedBill, selectBill=detailBill)
    analysed_products = TallyVendorAnalyzedProduct.objects.filter(vendor_bill_analyzed=analysed_bill).all()
    bill_form = TallyVendorAnalyzedBillForm(instance=analysed_bill, team=request.team)
    formset = TallyVendorProductFormSet(queryset=analysed_products, team=request.team)
    context = {'detailBill': detailBill, 'bill_form': bill_form, 'formset': formset,
               'analysed_products': analysed_products, "heading": "Bill Synced"}
    return render(request, 'tally/vendor/synced_detail.html', context)
