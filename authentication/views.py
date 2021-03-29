import re

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import auth_logout
from django.shortcuts import render, redirect

from authentication.models import SteamUser
from verifier import settings


def index(request):
    context = {
        'email_domains': settings.ALLOWED_EMAIL_DOMAINS,
        'group_id': settings.STEAM_GROUP_ID,
    }
    u = request.user
    action = request.GET.get("action")

    if u.is_authenticated and u.email:
        context['email_prefix'] = u.email.split("@")[0]

        u = SteamUser.objects.get(id=u.id)
        if u.is_email_verified:
            context['email_domains'] = [u.email.split("@")[-1]]

    if action == 'add_email':
        if not u.is_authenticated:
            context['error'] = 'Not Logged In'
            return render(request, 'index.html', context)

        u = SteamUser.objects.get(id=u.id)

        if not u.can_verify_email:
            context['error'] = '一天只能验证一次，请 24 小时后重试'
            return render(request, 'index.html', context)

        email_prefix = request.POST.get("email_prefix")
        email_domain = request.POST.get("email_domain")

        if not email_prefix or not email_domain:
            context['error'] = 'Invalid E-Mail'
            return render(request, 'index.html', context)

        email_prefix = email_prefix.lower()

        if email_domain not in settings.ALLOWED_EMAIL_DOMAINS:
            context['error'] = 'Invalid Domain'
            return render(request, 'index.html', context)

        if re.sub(r'[^a-z0-9_\-.]', '', email_prefix) != email_prefix:
            context['error'] = 'Invalid E-Mail'
            return render(request, 'index.html', context)

        u.email = email_prefix + "@" + email_domain
        if u.send_verification_mail():
            context['success'] = '邮件发送成功，记得查找垃圾邮件箱'
            u.save()
        else:
            context['error'] = '邮件发送失败'

    elif action == 'verify':
        if not u.is_authenticated:
            context['error'] = 'Not Logged In'
            return render(request, 'index.html', context)

        steamid = request.GET.get("steamid")
        verification_code = request.GET.get("verification_code")

        u = SteamUser.objects.get(steamid=steamid)

        if u.is_already_in_group:
            return redirect("/")

        if u.verify_totp(verification_code):
            context['success'] = '邮箱验证成功'
        else:
            context['error'] = '邮箱验证失败'

    elif action == 'approve':
        if not u.is_authenticated:
            context['error'] = 'Not Logged In'
            return render(request, 'index.html', context)

        u = SteamUser.objects.get(id=u.id)

        if u.is_already_in_group:
            return redirect("/")

        if not u.is_email_verified:
            context['error'] = '邮箱尚未验证'
        else:
            try:
                if u.add_to_group():
                    context['success'] = '审批进组成功'
                else:
                    context['error'] = '审批进组失败'
            except Exception as e:
                context['error'] = str(e)
    else:
        context["suffix"] = "?action=add_email"

    return render(request, 'index.html', context)


@login_required(login_url='/')
def logout(request):
    auth_logout(request)
    return redirect('auth:index')
