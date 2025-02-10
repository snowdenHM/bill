from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.teams.decorators import login_and_team_required


def home(request):
    if request.user.is_authenticated:
        team = request.team
        if team:
            return HttpResponseRedirect(reverse("web_team:home", args=[team.slug]))
        else:
            messages.info(
                request,
                _("Teams are enabled but you have no teams. Create a team below to access the rest of the dashboard."),
            )
            return HttpResponseRedirect(reverse("teams:manage_teams"))
    else:
        context = {"heading": "Home"}
        return render(request, "web/landing_page.html", context)


@login_and_team_required(login_url='account_login')
def team_home(request, team_slug):
    assert request.team.slug == team_slug
    return render(
        request,
        "dashboard/team_dashboard.html",
        context={
            "team": request.team,
            "heading": "Main",
            "active_tab": 'team',
            "page_title": _("{team} Dashboard").format(team=request.team),
        },
    )


def simulate_error(request):
    raise Exception("This is a simulated error.")
