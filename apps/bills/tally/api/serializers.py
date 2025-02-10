from rest_framework import serializers

from apps.bills.tally.models import Ledger, ParentLedger


class LedgerSerializer(serializers.ModelSerializer):
    parent = serializers.CharField(source='parent.parent', read_only=True)  # Return parent name instead of ID

    class Meta:
        model = Ledger
        fields = ('id', 'master_id', 'alter_id', 'name', 'parent', 'alias', 'opening_balance', 'gst_in', 'company')


class JournalIDSerializer(serializers.Serializer):
    id = serializers.UUIDField()


class InvoiceIDSerializer(serializers.Serializer):
    id = serializers.UUIDField()
