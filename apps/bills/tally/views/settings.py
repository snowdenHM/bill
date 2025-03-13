from django.shortcuts import render
from django.db.models import Value
from django.http import JsonResponse
from apps.bills.tally.models import Ledger, ParentLedger
from apps.teams.models import Team
from apps.teams.decorators import login_and_team_required
from django.db.models.functions import Trim, Replace


@login_and_team_required(login_url='account_login')
def ledger(request, team_slug):
    parent_ledger = ParentLedger.objects.filter(team=request.team).prefetch_related('ledger_set')
    context = {'allLedger': parent_ledger, "heading": "Tally Ledgers"}
    return render(request, 'tally/settings/ledgers.html', context)


@login_and_team_required(login_url='account_login')
def fetchVendorGst(request, team_slug):
    if request.method == 'GET':
        vendor = request.GET.get('vendor_id')
        # Replace the following line with your logic to fetch GST information based on the vendor_id
        gst_info = Ledger.objects.get(id=vendor)
        return JsonResponse({'gst': gst_info.gst_in})
    else:
        return JsonResponse({'gst': 'N/A'})
