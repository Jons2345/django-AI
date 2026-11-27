# academico/urls.py
# URLs de la app academico.

from django.urls import path

from . import views

# app_name crea un "espacio de nombres": en templates se usa {% url 'academico:inicio' %}
app_name = "academico"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),  # → /academico/

    # ---------- Estudiantes ----------
    path("estudiantes/", views.EstudianteListView.as_view(), name="estudiante_lista"),
    path("estudiantes/crear/", views.EstudianteCreateView.as_view(), name="estudiante_crear"),
    # <int:pk> captura el número de la URL y la vista lo usa para buscar el estudiante
    path("estudiantes/<int:pk>/", views.EstudianteDetailView.as_view(), name="estudiante_detalle"),
    path("estudiantes/<int:pk>/editar/", views.EstudianteUpdateView.as_view(), name="estudiante_editar"),
    path("estudiantes/<int:pk>/eliminar/", views.EstudianteDeleteView.as_view(), name="estudiante_eliminar"),
    path("estudiantes/<int:pk>/pdf/", views.EstudiantePdfView.as_view(), name="estudiante_pdf"),

    # ---------- Matrículas ----------
    path("matriculas/", views.MatriculaListView.as_view(), name="matricula_lista"),
    path("matriculas/crear/", views.MatriculaCreateView.as_view(), name="matricula_crear"),
    path("matriculas/<int:pk>/", views.MatriculaDetailView.as_view(), name="matricula_detalle"),
    path("matriculas/<int:pk>/editar/", views.MatriculaUpdateView.as_view(), name="matricula_editar"),
    path("matriculas/<int:pk>/eliminar/", views.MatriculaDeleteView.as_view(), name="matricula_eliminar"),
    path("matriculas/<int:pk>/pdf/", views.MatriculaPdfView.as_view(), name="matricula_pdf"),
]