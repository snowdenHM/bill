import json

import requests
from allauth.mfa.webauthn.internal.auth import get_credentials
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from apps.teams.decorators import login_and_team_required
from apps.bills.zoho.models import ZohoCredentials, ZohoVendor, ZohoChartOfAccount, ZohoTaxes, ZohoTdsTcs


@login_and_team_required(login_url='account_login')
def credentials(request, team_slug):
    """
    Retrieves Zoho credentials for the current team and renders the credentials page.

    If no ZohoCredentials object exists for the given team, it returns an empty context
    with an appropriate message or handles it gracefully.
    """
    userCredentials = ZohoCredentials.objects.filter(team=request.team).first()  # Safe lookup

    context = {'userCredentials': userCredentials, 'heading': 'Zoho Credentials'}

    return render(request, 'zoho/settings/credentials/credentials.html', context)


@login_and_team_required(login_url='account_login')
def vendor(request, team_slug):
    """
    Retrieves all vendors associated with the current team and renders the vendor page.
    """
    all_vendors = ZohoVendor.objects.filter(team=request.team)  # Optimized Query
    context = {
        'all_vendors': all_vendors,
        'heading': 'Zoho Vendors List'  # Added heading key
    }
    return render(request, 'zoho/settings/vendor/vendor.html', context)


@login_and_team_required(login_url='account_login')
def chart_of_account(request, team_slug):
    """
    Retrieves all chart of accounts (COA) associated with the current team and renders the COA page.
    """
    all_coa = ZohoChartOfAccount.objects.filter(team=request.team)  # Optimized Query
    context = {
        'all_coa': all_coa,
        'heading': 'Chart of Accounts'  # Added heading key
    }
    return render(request, 'zoho/settings/coa/coa.html', context)


@login_and_team_required(login_url='account_login')
def taxes(request, team_slug):
    """
    Retrieves all tax records associated with the current team and renders the taxes page.
    """
    all_taxes = ZohoTaxes.objects.filter(team=request.team)  # Optimized Query
    context = {
        'all_taxes': all_taxes,
        'heading': 'Zoho Taxes List'  # Added heading key
    }
    return render(request, 'zoho/settings/tax/tax.html', context)


@login_and_team_required(login_url='account_login')
def tds_tcs_tax(request, team_slug):
    """
    Retrieves all TDS/TCS tax records associated with the current team and renders the TDS/TCS page.
    """
    all_tds_tcs = ZohoTdsTcs.objects.filter(team=request.team)  # Optimized Query
    context = {
        'all_tds_tcs': all_tds_tcs,
        'heading': 'Zoho TDS & TCS Taxes'  # Added heading key
    }
    return render(request, 'zoho/settings/tds_tcs/tds_tcs.html', context)


@login_and_team_required(login_url='account_login')
def generate_token(request, team_slug):
    credential_data = ZohoCredentials.objects.get(team=request.team)

    def update_token(response):
        """Helper function to update tokens and save them."""
        api_response = response.json()
        if "access_token" in api_response:
            credential_data.accessToken = api_response["access_token"]
            if "refresh_token" in api_response:
                credential_data.refreshToken = api_response["refresh_token"]
                credential_data.onboarding_status = True
            credential_data.save()
            return True
        return False

    base_url = "https://accounts.zoho.in/oauth/v2/token"

    if credential_data.onboarding_status:
        params = {
            "refresh_token": credential_data.refreshToken,
            "client_id": credential_data.clientId,
            "client_secret": credential_data.clientSecret,
            "grant_type": "refresh_token"
        }
    else:
        params = {
            "grant_type": "authorization_code",
            "code": credential_data.accessCode,
            "client_id": credential_data.clientId,
            "redirect_uri": credential_data.redirectUrl,
            "client_secret": credential_data.clientSecret
        }

    response = requests.post(base_url, params)

    if update_token(response):
        messages.success(request,
                         "Token Updated Successfully" if credential_data.onboarding_status else "Zoho Connected Successfully")
    else:
        messages.warning(request, "Contact Service Provider! Service is down.")

    return redirect('zoho:credentials', team_slug=team_slug)


# Utility Functions

@login_and_team_required(login_url='account_login')
def fetchVendor(request, team_slug):
    try:
        currentToken = ZohoCredentials.objects.get(team=request.team)
    except ZohoCredentials.DoesNotExist:
        messages.error(request, "Zoho credentials not found.")
        return redirect('zoho:vendors', team_slug)

    url = f"https://www.zohoapis.in/books/v3/contacts?organization_id={currentToken.organisationId}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {currentToken.accessToken}',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an HTTPError on bad response
        parsed_data = response.json()
    except requests.RequestException:
        messages.error(request, "Failed to fetch contacts from Zoho.")
        return redirect('zoho:vendors', team_slug)
    except json.JSONDecodeError:
        messages.error(request, "Failed to parse contacts data.")
        return redirect('zoho:vendors', team_slug)

    contacts = parsed_data.get("contacts", [])

    existing_vendors = ZohoVendor.objects.filter(
        contactId__in=[contact["contact_id"] for contact in contacts if contact["contact_type"] == "vendor"],
        team=request.team
    ).values_list('contactId', flat=True)
    new_vendors = []
    for contact in contacts:
        if contact["contact_type"] == "vendor" and contact["contact_id"] not in existing_vendors:
            new_vendors.append(ZohoVendor(
                contactId=contact["contact_id"],
                companyName=contact["company_name"],
                gstNo=contact["gst_no"],
                team=request.team
            ))

    if new_vendors:
        ZohoVendor.objects.bulk_create(new_vendors)
        messages.success(request, f"{len(new_vendors)} new vendors saved successfully.")
    else:
        messages.info(request, "No new vendors to save.")

    return redirect('zoho:vendors', team_slug)


@login_and_team_required(login_url='account_login')
def fetchChartAccount(request, team_slug):
    try:
        currentToken = ZohoCredentials.objects.get(team=request.team)
    except ZohoCredentials.DoesNotExist:
        messages.error(request, "Zoho credentials not found.")
        return redirect('zoho:chartOfAccount', team_slug)

    url = f"https://www.zohoapis.in/books/v3/chartofaccounts?organization_id={currentToken.organisationId}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {currentToken.accessToken}',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        parsed_data = response.json()
    except requests.RequestException:
        messages.error(request, "Failed to fetch chart of accounts from Zoho.")
        return redirect('zoho:chartOfAccount', team_slug)
    except json.JSONDecodeError:
        messages.error(request, "Failed to parse chart of accounts data.")
        return redirect('zoho:chartOfAccount', team_slug)

    chartOfAccounts = parsed_data.get("chartofaccounts", [])

    existing_accounts = ZohoChartOfAccount.objects.filter(
        accountId__in=[account["account_id"] for account in chartOfAccounts],
        team=request.team
    ).values_list('accountId', flat=True)

    new_accounts = []
    for account in chartOfAccounts:
        if account["account_id"] not in existing_accounts:
            new_accounts.append(ZohoChartOfAccount(
                accountId=account["account_id"],
                accountName=account["account_name"],
                team=request.team
            ))

    if new_accounts:
        ZohoChartOfAccount.objects.bulk_create(new_accounts)
        messages.success(request, f"{len(new_accounts)} new chart of accounts saved successfully.")
    else:
        messages.info(request, "No new chart of accounts to save.")

    return redirect('zoho:chartOfAccount', team_slug)


@login_and_team_required(login_url='account_login')
def fetchTaxes(request, team_slug):
    try:
        currentToken = ZohoCredentials.objects.get(team=request.team)
    except ZohoCredentials.DoesNotExist:
        messages.error(request, "Zoho credentials not found.")
        return redirect('zoho:taxes', team_slug)

    url = f"https://www.zohoapis.in/books/v3/settings/taxes?organization_id={currentToken.organisationId}"
    headers = {
        'Authorization': f'Zoho-oauthtoken {currentToken.accessToken}',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        parsed_data = response.json()
    except requests.RequestException:
        messages.error(request, "Failed to fetch taxes from Zoho.")
        return redirect('zoho:taxes', team_slug)
    except json.JSONDecodeError:
        messages.error(request, "Failed to parse taxes data.")
        return redirect('zoho:taxes', team_slug)

    zohoTax = parsed_data.get("taxes", [])

    existing_taxes = ZohoTaxes.objects.filter(
        taxId__in=[tax["tax_id"] for tax in zohoTax],
        team=request.team
    ).values_list('taxId', flat=True)

    new_taxes = []
    for tax in zohoTax:
        if tax["tax_id"] not in existing_taxes:
            new_taxes.append(ZohoTaxes(
                taxId=tax["tax_id"],
                taxName=tax["tax_name"],
                team=request.team
            ))

    if new_taxes:
        ZohoTaxes.objects.bulk_create(new_taxes)
        messages.success(request, f"{len(new_taxes)} new taxes saved successfully.")
    else:
        messages.info(request, "No new taxes to save.")

    return redirect('zoho:taxes', team_slug)


@login_and_team_required(login_url='account_login')
def fetch_tds_tcs_tax(request, team_slug):
    try:
        currentToken = ZohoCredentials.objects.get(team=request.team)
    except ZohoCredentials.DoesNotExist:
        messages.error(request, "Zoho credentials not found.")
        return redirect('zoho:tds_tcs_tax', team_slug)

    headers = {
        'Authorization': f'Zoho-oauthtoken {currentToken.accessToken}',
    }

    # Fetch and save TDS taxes
    tds_url = f"https://www.zohoapis.in/books/v3/settings/taxes?is_tds_request=true&organization_id={currentToken.organisationId}"
    try:
        tds_response = requests.get(tds_url, headers=headers)
        tds_response.raise_for_status()
        tds_parsed_data = tds_response.json()
    except requests.RequestException:
        messages.error(request, "Failed to fetch TDS taxes from Zoho.")
        return redirect('zoho:tds_tcs_tax', team_slug)
    except json.JSONDecodeError:
        messages.error(request, "Failed to parse TDS taxes data.")
        return redirect('zoho:tds_tcs_tax', team_slug)

    tds_taxes = tds_parsed_data.get("taxes", [])

    existing_tds_taxes = ZohoTdsTcs.objects.filter(
        taxId__in=[tax["tax_id"] for tax in tds_taxes],
        taxType="TDS",
        team=request.team
    ).values_list('taxId', flat=True)

    new_tds_taxes = []
    for tax in tds_taxes:
        if tax["tax_id"] not in existing_tds_taxes:
            new_tds_taxes.append(ZohoTdsTcs(
                taxId=tax["tax_id"],
                taxName=tax["tax_name"],
                taxPercentage=tax["tax_percentage"],
                taxType="TDS",
                team=request.team
            ))
    # Fetch and save TCS taxes
    tcs_url = f"https://www.zohoapis.in/books/v3/settings/taxes?is_tcs_request=true&filter_by=Taxes.All&organization_id={currentToken.organisationId}"
    try:
        tcs_response = requests.get(tcs_url, headers=headers)
        tcs_response.raise_for_status()
        tcs_parsed_data = tcs_response.json()
    except requests.RequestException:
        messages.error(request, "Failed to fetch TCS taxes from Zoho.")
        return redirect('zoho:tds_tcs_tax', team_slug)
    except json.JSONDecodeError:
        messages.error(request, "Failed to parse TCS taxes data.")
        return redirect('zoho:tds_tcs_tax', team_slug)

    tcs_taxes = tcs_parsed_data.get("taxes", [])

    existing_tcs_taxes = ZohoTdsTcs.objects.filter(
        taxId__in=[tax["tax_id"] for tax in tcs_taxes],
        taxType="TCS",
        team=request.team
    ).values_list('taxId', flat=True)

    new_tcs_taxes = []
    for tax in tcs_taxes:
        if tax["tax_id"] not in existing_tcs_taxes:
            new_tcs_taxes.append(ZohoTdsTcs(
                taxId=tax["tax_id"],
                taxName=tax["tax_name"],
                taxPercentage=tax["tax_percentage"],
                taxType="TCS",
                team=request.team
            ))

    if new_tcs_taxes and new_tds_taxes:
        ZohoTdsTcs.objects.bulk_create(new_tds_taxes)
        ZohoTdsTcs.objects.bulk_create(new_tcs_taxes)
        messages.success(request, " TDS/TCS taxes saved successfully.")
        return redirect('zoho:tds_tcs_tax', team_slug)
    else:
        messages.error(request, " TDS & TCS taxes not saved successfully.")
        return redirect('zoho:tds_tcs_tax', team_slug)


@login_and_team_required(login_url='account_login')
def fetch_tax_data(request, team_slug):
    tax_type = request.GET.get('tax_type')
    tax = ZohoTdsTcs.objects.filter(taxType=tax_type, team=request.team).values('id', 'taxName', 'taxPercentage')
    return JsonResponse(list(tax), safe=False)

@login_and_team_required(login_url='account_login')
def fetchVendorGst(request, team_slug):
    if request.method == 'GET':
        vendor_id = request.GET.get('vendor_id')
        # Replace the following line with your logic to fetch GST information based on the vendor_id
        gst_info = ZohoVendor.objects.get(id=vendor_id)
        return JsonResponse({'gst': gst_info.gstNo})
    else:
        return JsonResponse({'gst': 'N/A'})