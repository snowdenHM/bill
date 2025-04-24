import re
from rest_framework import status
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from apps.teams.models import Team
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
        match = re.search(r"/org/([^/]+)/bills/", request.path)
        team = match.group(1) if match else None
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
                    parent_ledger, _ = ParentLedger.objects.get_or_create(parent=parent_name,
                                                                          team=Team.objects.get(slug=team))

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
                        team=Team.objects.get(slug=team)
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
            print(e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MasterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("Incoming Data:", request.data)
        return Response({'message': 'Incoming Data Received'}, status=status.HTTP_200_OK)


class TallyExpenseApi(APIView):
    """
    API View that handles both POST (to receive payload) and GET (to retrieve all synced data with products).
    """
    permission_classes = [AllowAny]

    def get(self, request, team_slug, *args, **kwargs):
        """
        Retrieve all synced expense bills with related products.
        """
        try:
            # Get all expenses where the associated TallyExpenseBill status is 'Synced'
            expenses = TallyExpenseAnalyzedBill.objects.filter(
                selectBill__status='Synced', selectBill__team__slug=team_slug
            ).select_related('vendor', 'selectBill')

            data = [
                {
                    "id": expense.id,
                    "voucher": expense.voucher or "N/A",
                    "bill_no": expense.bill_no or "N/A",
                    "bill_date": expense.bill_date.strftime('%Y-%m-%d') if expense.bill_date else None,
                    "total": float(expense.total) if expense.total else 0.0,
                    "vendor": {
                        "name": expense.vendor.name if expense.vendor else "No Vendor",
                        "company": expense.vendor.company if expense.vendor else "No Company",
                        "gst_in": expense.vendor.gst_in if expense.vendor else "No GST",
                    },
                    "taxes": {
                        "igst": {
                            "amount": float(expense.igst) if expense.igst else 0.0,
                            "ledger": str(expense.igst_taxes) if expense.igst_taxes else "No Tax Ledger",
                        },
                        "cgst": {
                            "amount": float(expense.cgst) if expense.cgst else 0.0,
                            "ledger": str(expense.cgst_taxes) if expense.cgst_taxes else "No Tax Ledger",
                        },
                        "sgst": {
                            "amount": float(expense.sgst) if expense.sgst else 0.0,
                            "ledger": str(expense.sgst_taxes) if expense.sgst_taxes else "No Tax Ledger",
                        }
                    },
                    "note": expense.note or "No Notes",
                    "products": [
                        {
                            "id": product.id,
                            "item_details": product.item_details or "N/A",
                            "chart_of_accounts": str(
                                product.chart_of_accounts.name) if product.chart_of_accounts else "No Chart",
                            "amount": float(product.amount) if product.amount else 0.0,
                            "debit_or_credit": product.debit_or_credit or "credit",
                        }
                        for product in expense.products.all()
                    ],
                    "created_at": expense.created_at.strftime('%Y-%m-%d %H:%M:%S') if expense.created_at else None,
                }
                for expense in expenses
            ]

            return Response({"data": data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, team_slug, *args, **kwargs):
        """
        Receives and validates incoming expense bill data.
        """
        try:
            payload = request.data
            print(f"Received Payload for team '{team_slug}':", payload)

            # Validate that the required fields exist
            bill_details = payload.get("bill_details", {})
            if not bill_details.get("voucher"):
                return Response({"message": "Missing required field: voucher"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Extract bill details
            bill_data = {
                "bill_id": payload.get("bill_id", ""),
                "reference_number": bill_details.get("reference_number", "N/A"),
                "bill_date": bill_details.get("bill_date", None),
                "voucher": bill_details.get("voucher", "N/A"),
                "total_amount": float(bill_details.get("total_amount", 0.0)),
                "company_id": bill_details.get("company_id", ""),
                "vendor": payload.get("vendor", {}),
                "taxes": payload.get("taxes", {}),
                "notes": payload.get("notes", "No Notes"),
                "line_items": payload.get("line_items", []),
            }

            return Response({"message": "Payload received successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TallyVendor(APIView):
    """
    API View that handles both POST (to receive payload) and GET (to retrieve all synced data with products).
    """
    permission_classes = [AllowAny]

    def get(self, request, team_slug, *args, **kwargs):
        """
        Retrieve all synced bills with related product transactions.
        """
        try:
            # Get all invoices where the associated TallyVendorBill status is 'Synced'
            vendors = TallyVendorAnalyzedBill.objects.filter(
                selectBill__status='Synced', selectBill__team__slug=team_slug
            ).select_related('vendor', 'selectBill')

            data = [
                {
                    "id": vendor.id,
                    "bill_no": vendor.bill_no,
                    "bill_date": vendor.bill_date.strftime('%Y-%m-%d') if vendor.bill_date else None,
                    "total": float(vendor.total),
                    "igst": float(vendor.igst),
                    "cgst": float(vendor.cgst),
                    "sgst": float(vendor.sgst),
                    "vendor": {
                        "name": vendor.vendor.name if vendor.vendor else "No Vendor",
                        "company": vendor.vendor.company if vendor.vendor else "No Company",
                        "gst_in": vendor.vendor.gst_in if vendor.vendor else "No GST",
                    },
                    "customer_id": vendor.selectBill.team.id if vendor.selectBill.team else None,
                    "transactions": [
                        {
                            "id": transaction.id,
                            "item_name": transaction.item_name,
                            "item_details": transaction.item_details,
                            "price": float(transaction.price),
                            "quantity": int(transaction.quantity),
                            "amount": float(transaction.amount),
                        }
                        for transaction in vendor.products.all()
                    ]
                }
                for vendor in vendors
            ]

            return Response({"data": data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, team_slug, *args, **kwargs):
        """
        Receives and validates incoming bill data.
        """
        try:
            payload = request.data
            # print(f"Received Payload for team '{team_slug}':", payload)
            # Ensure bill_number is present
            if not payload.get("bill_details", {}).get("bill_number"):
                return Response({"message": "Missing required field: bill_number"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Additional data processing logic can go here...
            return Response({"message": "Payload received successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
