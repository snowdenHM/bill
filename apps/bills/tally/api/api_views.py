from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.bills.tally.api.serializers import LedgerSerializer, InvoiceIDSerializer
# Project Imports
from apps.bills.tally.models import *


class LedgerViewSet(viewsets.ModelViewSet):
    queryset = Ledger.objects.all()
    serializer_class = LedgerSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # Print the full request URL
        full_url = request.build_absolute_uri()
        print(f"Full Request URL: {full_url}")

        print("Incoming Data:", request.data)
        ledger_data = request.data.get("LEDGER", [])

        if not ledger_data:
            return Response({'message': 'No Ledger Data Provided'}, status=status.HTTP_400_BAD_REQUEST)

        ledger_instances = []
        response_data = []

        try:
            with transaction.atomic():
                for ledger_entry in ledger_data:
                    parent_name = ledger_entry.get('Parent', '').strip()

                    # Fetch or create ParentLedger
                    parent_ledger, _ = ParentLedger.objects.get_or_create(parent=parent_name)

                    # Prepare Ledger instance
                    ledger_instance = Ledger(
                        master_id=ledger_entry.get('Master_Id'),
                        alter_id=ledger_entry.get('Alter_Id'),
                        name=ledger_entry.get('Name'),
                        parent=parent_ledger,
                        alias=ledger_entry.get('ALIAS'),
                        opening_balance=ledger_entry.get('OpeningBalance', '0'),
                        gst_in=ledger_entry.get('GSTIN'),
                        company=ledger_entry.get('Company'),
                    )
                    ledger_instances.append(ledger_instance)

                # Bulk create ledgers for performance
                created_ledgers = Ledger.objects.bulk_create(ledger_instances)

                # Prepare response data
                for ledger_instance in created_ledgers:
                    response_data.append({
                        'id': ledger_instance.id,
                        'master_id': ledger_instance.master_id,
                        'alter_id': ledger_instance.alter_id,
                        'name': ledger_instance.name,
                        'parent': ledger_instance.parent.parent,
                        'alias': ledger_instance.alias,
                        'opening_balance': ledger_instance.opening_balance,
                        'gst_in': ledger_instance.gst_in,
                        'company': ledger_instance.company
                    })

            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MasterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("Incoming Data:", request.data)
        return Response({'message': 'Incoming Data Received'}, status=status.HTTP_200_OK)


class TallyExpenseApi(APIView):
    """
    API View that handles both POST (to receive payload) and GET (to retrieve all synced data with products) requests.
    """
    permission_classes = [AllowAny]

    def get(self, request, team_slug, *args, **kwargs):
        try:
            # Filter TallyExpense instances where the associated TallyExpenseBill status is 'Synced'
            expenses = TallyExpense.objects.filter(selectBill__status='Synced', team__slug=team_slug)
            data = []
            for expense in expenses:
                # Ensure selectBill is available and has status 'Synced'
                if not expense.selectBill:
                    print(f"Missing selectBill for expense ID {expense.id}")
                    continue
                # Fetch related products for each TallyExpense
                products = expense.products.all()
                products_data = [{
                    "id": product.id,
                    "item_details": product.item_details,
                    "amount": product.amount,
                    "debit_or_credit": product.debit_or_credit,
                    "created_at": product.created_at
                } for product in products]
                # Add expense details with associated products
                data.append({
                    "id": expense.id,
                    "voucher": expense.voucher,
                    "voucher_number": expense.voucher_number,
                    "bill_no": expense.bill_no,
                    "bill_date": expense.bill_date,
                    "total": expense.total,
                    "company": expense.company,
                    "note": expense.note,
                    "created_at": expense.created_at,
                    "products": products_data
                })
            response_payload = {
                "data": data
            }
            return Response(response_payload, status=status.HTTP_200_OK)

        except AttributeError as e:
            # Print specific error for debugging
            print(f"AttributeError: {e}")
            return Response({"error": "An attribute error occurred. Please check your data structure."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            # Catch-all for other errors
            print(f"Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, team_slug, *args, **kwargs):
        try:
            payload = request.data
            print(f"Received Payload for team '{team_slug}':", payload)

            if not payload.get("voucher") or not payload.get("voucher_number"):
                return Response({"message": "Missing required fields: voucher or voucher_number"},
                                status=status.HTTP_400_BAD_REQUEST)

            print(f"Team Slug: {team_slug}")
            return Response({"message": "Payload received successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error occurred: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TallyVendor(APIView):
    """
    API View that handles both POST (to receive payload) and GET (to retrieve all synced data with products) requests.
    """
    permission_classes = [AllowAny]

    def get(self, request, team_slug, *args, **kwargs):
        try:
            # Filter invoices where the associated TallyVendorBill status is 'Synced'
            vendors = Invoice.objects.filter(selectBill__status='Synced', selectBill__team__slug=team_slug)
            data = []
            for vendor in vendors:
                # Ensure selectBill is available and has status 'Synced'
                if not vendor.selectBill:
                    print(f"Missing selectBill for vendor ID {vendor.id}")
                    continue
                # Fetch related product transactions for each Invoice
                transactions = vendor.transactions.all()
                transactions_data = [{
                    "id": transaction.id,
                    "item_name": transaction.item_name,
                    "item_details": transaction.item_details,
                    "price": transaction.price,
                    "quantity": transaction.quantity,
                    "amount": transaction.amount,
                } for transaction in transactions]
                # Add vendor details with associated products
                data.append({
                    "id": vendor.id,
                    "bill_no": vendor.bill_no,
                    "bill_date": vendor.bill_date,
                    "total": vendor.total,
                    "igst": vendor.igst,
                    "cgst": vendor.cgst,
                    "sgst": vendor.sgst,
                    "vendor_company": vendor.vendor.company,
                    "vendor_gst": vendor.vendor.gst_in,
                    "customer_id": vendor.company_id,
                    "transactions": transactions_data
                })
            response_payload = {
                "data": data
            }
            return Response(response_payload, status=status.HTTP_200_OK)

        except AttributeError as e:
            # Print specific error for debugging
            print(f"AttributeError: {e}")
            return Response({"error": "An attribute error occurred. Please check your data structure."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            # Catch-all for other errors
            print(f"Error: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, team_slug, *args, **kwargs):
        try:
            payload = request.data
            print(f"Received Payload for team '{team_slug}':", payload)

            if not payload.get("bill_number") or not payload.get("company_id"):
                return Response({"message": "Missing required fields: Bill No. or company"},
                                status=status.HTTP_400_BAD_REQUEST)

            print(f"Team Slug: {team_slug}")
            return Response({"message": "Payload received successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error occurred: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
