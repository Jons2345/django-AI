# academico/views.py
# Vistas de la app academico (solo vistas basadas en clases).

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from core.mixins import ComprobantePdfMixin, ExportarMixin

from .forms import FiltroEstudianteForm, MatriculaForm, NotaFormSet
from .models import NOTA_MINIMA_APROBACION, EstadoNota, Estudiante, Matricula, Nota, Periodo


# ============================================================
# INICIO
# ============================================================
class InicioView(LoginRequiredMixin, TemplateView):
    template_name = "academico/inicio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo_activo = Periodo.objects.filter(activo=True).first()
        secciones_periodo = periodo_activo.secciones.count() if periodo_activo else 0
        resumen = Nota.objects.aggregate(
            total=Count("id"),
            aprobados=Count("id", filter=Q(estado=EstadoNota.APROBADO)),
        )
        total_notas = resumen["total"]
        aprobados = resumen["aprobados"]
        porcentaje = round(aprobados * 100 / total_notas, 1) if total_notas else 0
        context.update({
            "total_estudiantes": Estudiante.objects.count(),
            "periodo_activo": periodo_activo,
            "secciones_periodo": secciones_periodo,
            "total_matriculas": Matricula.objects.count(),
            "total_notas": total_notas,
            "aprobados": aprobados,
            "porcentaje_aprobados": porcentaje,
        })
        return context


# ============================================================
# ESTUDIANTES
# ============================================================
class EstudianteListView(LoginRequiredMixin, ExportarMixin, ListView):
    # Orden de herencia: 1) exige login, 2) agrega filtros/columnas, 3) el ListView normal
    model = Estudiante
    # select_related trae carrera y facultad en la MISMA consulta (evita 1 consulta extra por fila)
    queryset = Estudiante.objects.select_related("carrera__facultad")
    template_name = "academico/estudiante_lista.html"
    paginate_by = 10  # 10 estudiantes por página
    logo_reporte = "img/logo.png"  # archivo en static/img/logo.png

    # ---------- Configuración del componente de filtros ----------
    filtro_form_class = FiltroEstudianteForm
    campos_disponibles = [
        ("cedula", "Cédula"),
        ("apellidos", "Apellidos"),
        ("nombres", "Nombres"),
        ("email", "Correo"),
        ("telefono", "Teléfono"),
        ("fecha_nacimiento", "Nacimiento"),
        ("carrera__nombre", "Carrera"),
        ("carrera__facultad__nombre", "Facultad"),
    ]
    campos_por_defecto = ["cedula", "apellidos", "nombres", "carrera__nombre"]

    def filtrar(self, queryset, datos):
        # datos = cleaned_data del FiltroEstudianteForm (ya validado y convertido)
        texto = datos.get("texto")
        if texto:
            # Separamos por palabras: "ana torres" busca "ana" Y "torres".
            # Cada palabra puede estar en nombres O apellidos O cédula (eso hace Q con |).
            for palabra in texto.split():
                queryset = queryset.filter(
                    Q(nombres__icontains=palabra)
                    | Q(apellidos__icontains=palabra)
                    | Q(cedula__icontains=palabra)
                )
        if datos.get("carrera"):
            queryset = queryset.filter(carrera=datos["carrera"])
        if datos.get("facultad"):
            # "__" también sirve para filtrar por un modelo relacionado
            queryset = queryset.filter(carrera__facultad=datos["facultad"])
        if datos.get("nacido_desde"):
            queryset = queryset.filter(fecha_nacimiento__gte=datos["nacido_desde"])  # gte = >=
        if datos.get("nacido_hasta"):
            queryset = queryset.filter(fecha_nacimiento__lte=datos["nacido_hasta"])  # lte = <=
        return queryset
    
    
class EstudiantePdfView(LoginRequiredMixin, ComprobantePdfMixin, DetailView):
    # Orden: 1) exige login, 2) cambia HTML por PDF, 3) DetailView busca el estudiante por <pk>
    model = Estudiante
    # La ficha muestra carrera, facultad y universidad: las traemos en UNA consulta
    queryset = Estudiante.objects.select_related("carrera__facultad__universidad")
    template_pdf = "academico/pdf/estudiante_ficha.html"
    nombre_archivo = "estudiante"  # → estudiante-<pk>.pdf
    # DetailView llama al objeto "estudiante" en el template (por el nombre del modelo)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # self.object = el estudiante. Sus matrículas con todo lo que la tabla necesita:
        #   seccion__curso   → nombre del curso
        #   seccion__periodo → nombre del periodo
        #   nota             → promedio y estado (OneToOne inverso: también se puede select_related)
        # Sin select_related, cada fila haría 3 consultas más.
        context["matriculas"] = (
            self.object.matriculas
            .select_related("seccion__curso", "seccion__periodo", "nota")
            .order_by("-seccion__periodo__fecha_inicio", "seccion__curso__nombre")
        )
        return context
    
# ============================================================
# MATRÍCULAS
# ============================================================
# Consulta reutilizable: la matrícula con TODO lo que muestran las pantallas
MATRICULAS_COMPLETAS = Matricula.objects.select_related(
    "estudiante__carrera",
    "seccion__curso",
    "seccion__periodo",
    "seccion__profesor",
    "nota",  # OneToOne inverso: también se puede traer con select_related
)


def obtener_nota(matricula):
    """Devuelve la nota de la matrícula o None si todavía no tiene."""
    # Si no hay nota, matricula.nota lanza un error; getattr con None lo evita
    return getattr(matricula, "nota", None)


class MatriculaListView(LoginRequiredMixin, ListView):
    queryset = MATRICULAS_COMPLETAS
    template_name = "academico/matricula_lista.html"
    context_object_name = "matriculas"  # en el template se usa "matriculas" en vez de "object_list"
    paginate_by = 10


class MatriculaDetailView(LoginRequiredMixin, DetailView):
    queryset = MATRICULAS_COMPLETAS
    template_name = "academico/matricula_detalle.html"
    # DetailView llama al objeto "matricula" en el template

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nota"] = obtener_nota(self.object)
        return context


class MatriculaNotaMixin:
    """
    Formulario MAESTRO (Matricula) + DETALLE (NotaFormSet) en la misma pantalla.
    Lo usan MatriculaCreateView y MatriculaUpdateView.
    Antes de llamar a post(), cada vista debe dejar listo self.object.
    """

    model = Matricula
    form_class = MatriculaForm
    template_name = "academico/matricula_form.html"
    titulo = ""          # lo define cada vista
    mensaje_exito = ""   # lo define cada vista

    def get_nota_formset(self):
        # prefix="nota": los campos se llaman "nota-0-n1", así no chocan con los del formulario principal
        kwargs = {"instance": self.object, "prefix": "nota"}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST  # con datos enviados → se puede validar
        return NotaFormSet(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Si viene de form_invalid ya trae el formset CON errores; si no, creamos uno nuevo
        if "nota_formset" not in context:
            context["nota_formset"] = self.get_nota_formset()
        context["titulo"] = self.titulo
        context["nota_minima"] = NOTA_MINIMA_APROBACION
        return context

    def post(self, request, *args, **kwargs):
        form = self.get_form()                # formulario principal con los datos del POST
        nota_formset = self.get_nota_formset()
        # Validamos LOS DOS por separado (no con "and" directo) para que ambos calculen
        # sus errores. Con "and", si el primero falla, el segundo ni se revisaría.
        form_ok = form.is_valid()             # aquí también corre Matricula.clean()
        formset_ok = nota_formset.is_valid()
        if form_ok and formset_ok:
            return self.form_valid(form, nota_formset)
        return self.form_invalid(form, nota_formset)

    def form_valid(self, form, nota_formset):
        # transaction.atomic(): o se guardan LOS DOS, o no se guarda ninguno
        with transaction.atomic():
            # 1) Matrícula: ponemos el usuario solo si es nueva (quién la REGISTRÓ)
            if not form.instance.user_id:
                form.instance.user = self.request.user
            self.object = form.save()

            # 2) Nota: la atamos a la matrícula recién guardada
            nota_formset.instance = self.object
            notas = nota_formset.save(commit=False)  # objetos Nota sin guardar todavía
            for nota in notas:
                if not nota.user_id:
                    nota.user = self.request.user
                nota.save()  # aquí Nota.save() calcula promedio y estado

        messages.success(self.request, self.mensaje_exito)
        return redirect(self.get_success_url())

    def form_invalid(self, form, nota_formset):
        # Volvemos a dibujar la página con los dos formularios y sus errores
        return self.render_to_response(
            self.get_context_data(form=form, nota_formset=nota_formset)
        )

    def get_success_url(self):
        # Después de guardar, vamos al detalle de la matrícula
        return reverse("academico:matricula_detalle", kwargs={"pk": self.object.pk})


class MatriculaCreateView(LoginRequiredMixin, MatriculaNotaMixin, CreateView):
    titulo = "Nueva matrícula"
    mensaje_exito = "Matrícula registrada correctamente."

    def post(self, request, *args, **kwargs):
        self.object = None  # al crear todavía no existe
        return super().post(request, *args, **kwargs)  # → MatriculaNotaMixin.post()


class MatriculaUpdateView(LoginRequiredMixin, MatriculaNotaMixin, UpdateView):
    queryset = MATRICULAS_COMPLETAS
    titulo = "Editar matrícula"
    mensaje_exito = "Matrícula actualizada correctamente."

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()  # la matrícula que se está editando (o 404)
        return super().post(request, *args, **kwargs)


class MatriculaDeleteView(LoginRequiredMixin, DeleteView):
    queryset = MATRICULAS_COMPLETAS
    template_name = "academico/matricula_confirmar_eliminar.html"
    success_url = reverse_lazy("academico:matricula_lista")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nota"] = obtener_nota(self.object)
        return context

    def form_valid(self, form):
        # Guardamos el nombre ANTES de borrar, para el mensaje
        nombre = self.object.estudiante.nombre_completo
        respuesta = super().form_valid(form)  # borra la matrícula (y su nota, por CASCADE)
        messages.success(self.request, f"Se eliminó la matrícula de {nombre}.")
        return respuesta