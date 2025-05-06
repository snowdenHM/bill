from django import template
from waffle import flag_is_active

from apps.teams.models import Flag

register = template.Library()


@register.simple_tag(takes_context=True)
def is_flag_active(context, flag_name, slug):
    request = context['request']
    if flag_is_active(request, flag_name):
        try:
            flag = Flag.objects.get(name=flag_name)
            if flag.teams.filter(slug=slug).exists():
                flag_active = True
            else:
                flag_active = False
        except Flag.DoesNotExist:
            print("Flag does not exist")
    else:
        flag_active = False
    return flag_active
