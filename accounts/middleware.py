from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone


class SeniorSessionMiddleware:
    """Senior-only gates; Django staff administration keeps its own session flow."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if getattr(request, "resolver_match", None) and request.resolver_match.namespace == "accounts":
            response["Cache-Control"] = "no-store, private"
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if match.namespace != "accounts":
            return None
        name = match.url_name
        public = {"login", "language", "help", "logout", "home"}
        api = name in {"session_status", "session_touch"}
        if not request.user.is_authenticated:
            if name not in public:
                return JsonResponse({"expired": True}, status=401) if api else redirect("accounts:login")
            return None
        senior = getattr(request.user, "senior", None)
        if senior is None or request.user.is_staff:
            if name not in public:
                return JsonResponse({"expired": True}, status=403) if api else redirect("accounts:login")
            return None
        now = timezone.now().timestamp()
        last = request.session.get("senior_activity", 0)
        if now - last >= settings.SENIOR_IDLE_SECONDS:
            logout(request)
            if api:
                return JsonResponse({"expired": True}, status=401)
            return redirect("/login/?expired=1")
        request.senior = senior
        if name not in public and not api:
            if senior.must_change_password and name != "password":
                return redirect("accounts:password")
            if not senior.must_change_password and senior.consent_accepted_at is None and name != "consent":
                return redirect("accounts:consent")
            request.session["senior_activity"] = now
        return None
