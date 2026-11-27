# academico/urls.py
# URLs de la app academico.

from django.urls import path

from . import views

# app_name crea un "espacio de nombres": en templates se usa {% url 'academico:inicio' %}
app_name = "academico"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),

    # ---------- Estudiantes ----------
    path("estudiantes/", views.EstudianteListView.as_view(), name="estudiante_lista"),
    path("estudiantes/<int:pk>/pdf/", views.EstudiantePdfView.as_view(), name="estudiante_pdf"),

    # ---------- Matrículas ----------
    path("matriculas/", views.MatriculaListView.as_view(), name="matricula_lista"),
    path("matriculas/crear/", views.MatriculaCreateView.as_view(), name="matricula_crear"),
    path("matriculas/<int:pk>/", views.MatriculaDetailView.as_view(), name="matricula_detalle"),
    path("matriculas/<int:pk>/editar/", views.MatriculaUpdateView.as_view(), name="matricula_editar"),
    path("matriculas/<int:pk>/eliminar/", views.MatriculaDeleteView.as_view(), name="matricula_eliminar"),
]