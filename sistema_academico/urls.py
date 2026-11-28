from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views  # vistas de login/logout que ya trae Django
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # LoginView usa por defecto el template registration/login.html.
    # redirect_authenticated_user=True: si ya iniciaste sesión, no te muestra el login otra vez.
    path(
        "login/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    # LogoutView solo acepta POST (por seguridad). Por eso el botón es un formulario.
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Todas las URLs de la app academico empiezan con /academico/
    path("academico/", include("academico.urls")),
    
    path("", RedirectView.as_view(pattern_name="academico:inicio", permanent=False)),
]

# Solo en desarrollo (DEBUG = True): Django sirve los archivos subidos (logos, fotos)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
