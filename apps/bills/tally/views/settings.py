from django.shortcuts import render
from django.db.models import Value
from django.http import JsonResponse
from apps.bills.tally.models import Ledger
from apps.teams.models import Team
from apps.teams.decorators import login_and_team_required
from django.db.models.functions import Trim, Replace


@login_and_team_required(login_url='account_login')
def ledger(request, team_slug):
    team = Team.objects.get(slug=team_slug)

    # Remove \r and \n from the company field and trim any extra whitespace
    allLedger = Ledger.objects.annotate(
        cleaned_company=Trim(
            Replace(
                Replace('company', Value('\r'), Value('')),
                Value('\n'),
                Value('')
            )
        )
    ).filter(cleaned_company=team.name)

    print(allLedger)
    context = {'allLedger': allLedger, "heading": "Tally Ledgers"}
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
