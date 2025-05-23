# Generated by Django 5.1.5 on 2025-03-20 16:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tally', '0009_tallyconfig_chart_of_accounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='tallyconfig',
            name='chart_of_accounts_expense',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ex_coa_tally_config', to='tally.parentledger', verbose_name='EX COA Parent Ledger'),
        ),
    ]
