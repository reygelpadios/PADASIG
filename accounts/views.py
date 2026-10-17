from django.conf import settings
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from announcements.models import Announcement
from .models import ChangeLog, Senior
from .security import authenticate_senior


def page(request, template, **context):
    senior = getattr(request, "senior", None)
    context.update(lang=request.session.get("portal_language", "fil"), help_number=settings.HELP_DESK_NUMBER,
                   senior=senior, idle_seconds=settings.SENIOR_IDLE_SECONDS,
                   text_size=senior.text_size if senior else "normal")
    return render(request, f"accounts/{template}.html", context)


def next_step(senior):
    if senior.must_change_password:
        return "accounts:password"
    return "accounts:consent" if senior.consent_accepted_at is None else "accounts:portal"


@require_GET
def home(request):
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def sign_in(request):
    if getattr(request, "senior", None):
        return redirect(next_step(request.senior))
    error = False
    if request.method == "POST":
        senior_id = request.POST.get("senior_id", "")[:100]
        password = request.POST.get("password", "")
        user = authenticate_senior(request, senior_id, password)
        if user:
            senior = user.senior
            language = request.session.get("portal_language", senior.preferred_language)
            login(request, user)
            request.session["portal_language"] = language
            request.session["senior_activity"] = timezone.now().timestamp()
            request.session["login_loading_pending"] = True
            destination = next_step(senior)
            return redirect("accounts:loading" if destination == "accounts:portal" else destination)
        error = True
    return page(request, "login", error=error, expired="expired" in request.GET)


@require_http_methods(["GET", "POST"])
def password_setup(request):
    if not request.senior.must_change_password:
        return redirect(next_step(request.senior))
    form = SetPasswordForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Recheck under locks: concurrent staff resets must invalidate this form.
            user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
            senior = Senior.objects.select_for_update().get(pk=request.senior.pk)
            if user.password != request.user.password:
                logout(request)
                return redirect("accounts:login")
            if not senior.must_change_password:
                return redirect(next_step(senior))
            if user.check_password(form.cleaned_data["new_password1"]):
                form.add_error("new_password1", "Gumamit ng ibang password. / Choose a different password.")
            else:
                form.user = user
                form.save()
                Senior.objects.filter(pk=senior.pk).update(must_change_password=False)
                ChangeLog.objects.create(senior=senior, action="first_time_password_changed")
                request.user = user
                update_session_auth_hash(request, user)
                return redirect("accounts:consent")
    return page(request, "password", form=form)


@require_http_methods(["GET", "POST"])
def consent(request):
    if request.senior.consent_accepted_at:
        return redirect("accounts:portal")
    if request.method == "POST":
        with transaction.atomic():
            senior = Senior.objects.select_for_update().get(pk=request.senior.pk)
            if senior.must_change_password:
                return redirect("accounts:password")
            if senior.consent_accepted_at is None:
                senior.consent_accepted_at = timezone.now()
                senior.save(update_fields=["consent_accepted_at"])
                ChangeLog.objects.create(senior=senior, action="privacy_notice_accepted", details={"version": "development-draft-1"})
        return redirect("accounts:loading" if request.session.get("login_loading_pending") else "accounts:portal")
    return page(request, "consent")


@require_GET
def loading(request):
    if not request.session.pop("login_loading_pending", False):
        return redirect("accounts:portal")
    return render(request, "accounts/loading.html")


@require_GET
def portal(request):
    today = timezone.localdate()
    posts = list(Announcement.objects.active_main(today).select_related("benefit").order_by("-publish_date", "-pk"))
    records = {
        record.announcement_id: record
        for record in request.senior.inclusion_records.filter(announcement_id__in=[post.pk for post in posts])
    }
    benefits = []
    for post in posts:
        benefits.append({
            "post": post,
            "record": records.get(post.pk),
            "days_until": (post.payout_date - today).days,
            "documents": post.required_documents.splitlines(),
            "proxy_documents": post.proxy_requirements.splitlines(),
        })
    latest_post = (Announcement.objects.filter(is_published=True, publish_date__lte=today)
                   .select_related("benefit").order_by("-publish_date", "-pk").first())
    return page(request, "portal", benefits=benefits, latest_post=latest_post, demo=settings.DEBUG)


@require_POST
def text_size(request):
    value = request.POST.get("text_size")
    if value in {"normal", "large", "xlarge"}:
        request.senior.text_size = value
        request.senior.save(update_fields=["text_size"])
    return redirect("accounts:portal")


@require_GET
def password_help(request):
    return page(request, "help")


@require_POST
def language(request):
    value = request.POST.get("language")
    if value in {"fil", "en"}:
        request.session["portal_language"] = value
    # Named destinations only: never redirect to an arbitrary submitted URL.
    destination = request.POST.get("destination", "login")
    if destination not in {"login", "password", "consent", "portal", "help"}:
        destination = "login"
    return redirect(f"accounts:{destination}")


@require_POST
def sign_out(request):
    language = request.session.get("portal_language", "fil")
    logout(request)
    request.session["portal_language"] = language
    return redirect("accounts:login")


@require_GET
def session_status(request):
    remaining = settings.SENIOR_IDLE_SECONDS - (timezone.now().timestamp() - request.session["senior_activity"])
    return JsonResponse({"remaining": max(0, int(remaining))})


@require_POST
def session_touch(request):
    request.session["senior_activity"] = timezone.now().timestamp()
    return JsonResponse({"remaining": settings.SENIOR_IDLE_SECONDS})
