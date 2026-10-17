from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.sign_in, name="login"),
    path("login/loading/", views.loading, name="loading"),
    path("setup/password/", views.password_setup, name="password"),
    path("setup/privacy/", views.consent, name="consent"),
    path("portal/", views.portal, name="portal"),
    path("portal/text-size/", views.text_size, name="text_size"),
    path("help/password/", views.password_help, name="help"),
    path("language/", views.language, name="language"),
    path("logout/", views.sign_out, name="logout"),
    path("session/status/", views.session_status, name="session_status"),
    path("session/touch/", views.session_touch, name="session_touch"),
]
