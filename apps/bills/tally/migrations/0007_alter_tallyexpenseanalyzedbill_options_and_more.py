# Generated by Django 5.1.5 on 2025-03-20 14:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0006_alter_tallyexpenseanalyzedproduct_debit_or_credit'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tallyexpenseanalyzedbill',
            options={'verbose_name_plural': 'Expense Analyzed Bill'},
        ),
        migrations.AddField(
            model_name='tallyexpenseanalyzedbill',
            name='cgst_taxes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cgst_tally_expense_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AddField(
            model_name='tallyexpenseanalyzedbill',
            name='igst_taxes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='igst_tally_expense_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AddField(
            model_name='tallyexpenseanalyzedbill',
            name='sgst_taxes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sgst_tally_expense_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AddField(
            model_name='tallyvendoranalyzedbill',
            name='cgst_taxes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cgst_tally_vendor_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AddField(
            model_name='tallyvendoranalyzedbill',
            name='igst_taxes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='igst_tally_vendor_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AddField(
            model_name='tallyvendoranalyzedbill',
            name='sgst_taxes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sgst_tally_vendor_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AlterField(
            model_name='tallyexpenseanalyzedbill',
            name='cgst',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='tallyexpenseanalyzedbill',
            name='igst',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='tallyexpenseanalyzedbill',
            name='sgst',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='tallyexpenseanalyzedbill',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vendor_tally_expense_analyzed_bills', to='tally.ledger'),
        ),
        migrations.AlterField(
            model_name='tallyvendoranalyzedbill',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vendor_tally_vendor_analyzed_bills', to='tally.ledger'),
        ),
    ]
