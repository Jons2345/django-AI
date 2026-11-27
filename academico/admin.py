# academico/admin.py
# Configuración del panel de administración (/admin/) para los 11 modelos.

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Carrera, Curso, Estudiante, Facultad, Matricula, Nota,
    Periodo, Profesor, Seccion, Semestre, Universidad,
)

# Textos que se ven en la parte de arriba del admin
admin.site.site_header = "Sistema Académico"
admin.site.site_title = "Sistema Académico"
admin.site.index_title = "Panel de administración"


# ============================================================
# CLASE BASE: todos los admins heredan de aquí
# ============================================================
class BaseAdmin(admin.ModelAdmin):
    # Campos de ModeloBase que se MUESTRAN pero no se pueden editar
    readonly_fields = ("user", "fecha_creacion", "fecha_modificacion")
    list_per_page = 20  # cuántos registros por página en la lista

    def save_model(self, request, obj, form, change):
        # request.user es el usuario que inició sesión en el admin.
        # Solo lo asignamos si el registro aún no tiene usuario: así se guarda
        # quién lo REGISTRÓ y no se sobrescribe cada vez que alguien lo edita.
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)  # guarda normalmente

    def save_formset(self, request, form, formset, change):
        # Los "inlines" (como la Nota dentro de la Matrícula) NO pasan por save_model,
        # pasan por aquí. Hacemos lo mismo: ponerles el usuario.
        instancias = formset.save(commit=False)  # obtiene los objetos sin guardarlos aún
        for obj in formset.deleted_objects:      # borra los que se marcaron para eliminar
            obj.delete()
        for obj in instancias:
            if not obj.user_id:
                obj.user = request.user
            obj.save()
        formset.save_m2m()


# ============================================================
# UNIVERSIDAD
# ============================================================
@admin.register(Universidad)  # esto es lo mismo que admin.site.register(Universidad, UniversidadAdmin)
class UniversidadAdmin(BaseAdmin):
    list_display = ("siglas", "nombre", "ciudad", "ver_logo")  # columnas de la lista
    search_fields = ("nombre", "siglas", "ciudad")           # campos donde busca la lupa
    list_filter = ("ciudad",)                                # filtros de la barra derecha

    @admin.display(description="Logo")
    def ver_logo(self, obj):
        # Muestra una miniatura del logo en la lista (si tiene logo)
        if obj.logo:
            return format_html('<img src="{}" style="height:40px;">', obj.logo.url)
        return "—"


# ============================================================
# FACULTAD
# ============================================================
@admin.register(Facultad)
class FacultadAdmin(BaseAdmin):
    list_display = ("nombre", "universidad", "decano")
    search_fields = ("nombre", "decano", "universidad__nombre")  # "__" = buscar en el modelo relacionado
    list_filter = ("universidad",)
    list_select_related = ("universidad",)  # optimiza: trae la universidad en la misma consulta


# ============================================================
# CARRERA
# ============================================================
@admin.register(Carrera)
class CarreraAdmin(BaseAdmin):
    list_display = ("codigo", "nombre", "facultad", "duracion_semestres")
    search_fields = ("codigo", "nombre")
    list_filter = ("facultad__universidad", "facultad")
    list_select_related = ("facultad__universidad",)


# ============================================================
# SEMESTRE
# ============================================================
@admin.register(Semestre)
class SemestreAdmin(BaseAdmin):
    list_display = ("numero", "nombre")
    search_fields = ("nombre",)


# ============================================================
# PERIODO
# ============================================================
@admin.register(Periodo)
class PeriodoAdmin(BaseAdmin):
    list_display = ("nombre", "fecha_inicio", "fecha_fin", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)
    list_editable = ("activo",)  # permite marcar/desmarcar "activo" directo desde la lista


# ============================================================
# CURSO
# ============================================================
@admin.register(Curso)
class CursoAdmin(BaseAdmin):
    list_display = ("codigo", "nombre", "carrera", "semestre", "creditos")
    search_fields = ("codigo", "nombre")
    list_filter = ("carrera", "semestre")
    list_select_related = ("carrera", "semestre")


# ============================================================
# PROFESOR
# ============================================================
@admin.register(Profesor)
class ProfesorAdmin(BaseAdmin):
    list_display = ("cedula", "nombre_completo", "email", "titulo")
    search_fields = ("cedula", "nombres", "apellidos", "email")


# ============================================================
# ESTUDIANTE
# ============================================================
@admin.register(Estudiante)
class EstudianteAdmin(BaseAdmin):
    list_display = ("cedula", "nombre_completo", "carrera", "email", "telefono")
    search_fields = ("cedula", "nombres", "apellidos", "email")
    list_filter = ("carrera__facultad", "carrera")
    list_select_related = ("carrera",)


# ============================================================
# SECCION
# ============================================================
@admin.register(Seccion)
class SeccionAdmin(BaseAdmin):
    # "inscritos" es la propiedad del modelo: el admin también puede mostrarla
    list_display = ("curso", "periodo", "paralelo", "jornada", "profesor", "cupo", "inscritos")
    search_fields = ("curso__nombre", "curso__codigo", "profesor__apellidos")
    list_filter = ("periodo", "jornada", "curso__carrera")
    list_select_related = ("curso", "periodo", "profesor")
    # autocomplete: en vez de una lista desplegable enorme, muestra un buscador
    autocomplete_fields = ("curso", "profesor")


# ============================================================
# NOTA como INLINE (se edita DENTRO de la matrícula)
# ============================================================
class NotaInline(admin.StackedInline):
    model = Nota
    max_num = 1      # una matrícula solo puede tener 1 nota
    extra = 1        # muestra 1 formulario vacío si todavía no tiene nota
    fields = ("n1", "n2", "n3", "promedio", "estado")
    readonly_fields = ("promedio", "estado")  # se calculan solos en save()


# ============================================================
# MATRICULA
# ============================================================
@admin.register(Matricula)
class MatriculaAdmin(BaseAdmin):
    list_display = ("estudiante", "seccion", "fecha", "ver_promedio", "ver_estado")
    search_fields = ("estudiante__cedula", "estudiante__apellidos", "seccion__curso__nombre")
    list_filter = ("seccion__periodo", "seccion__jornada", "seccion__curso")
    list_select_related = ("estudiante", "seccion__curso", "seccion__periodo", "nota")
    autocomplete_fields = ("estudiante", "seccion")
    inlines = [NotaInline]  # ← aquí se agrega la Nota dentro del formulario de Matrícula

    @admin.display(description="Promedio")
    def ver_promedio(self, obj):
        # getattr con valor por defecto: si la matrícula todavía no tiene nota, devuelve None
        nota = getattr(obj, "nota", None)
        return nota.promedio if nota else "—"

    @admin.display(description="Estado")
    def ver_estado(self, obj):
        nota = getattr(obj, "nota", None)
        return nota.get_estado_display() if nota else "Sin nota"


# ============================================================
# NOTA (también tiene su propia pantalla)
# ============================================================
@admin.register(Nota)
class NotaAdmin(BaseAdmin):
    list_display = ("ver_estudiante", "ver_curso", "n1", "n2", "n3", "promedio", "estado")
    search_fields = ("matricula__estudiante__cedula", "matricula__estudiante__apellidos")
    list_filter = ("estado", "matricula__seccion__periodo", "matricula__seccion__jornada")
    list_select_related = ("matricula__estudiante", "matricula__seccion__curso")
    autocomplete_fields = ("matricula",)
    # Sumamos promedio y estado a los campos de solo lectura de BaseAdmin
    readonly_fields = BaseAdmin.readonly_fields + ("promedio", "estado")

    @admin.display(description="Estudiante", ordering="matricula__estudiante__apellidos")
    def ver_estudiante(self, obj):
        return obj.matricula.estudiante.nombre_completo

    @admin.display(description="Curso", ordering="matricula__seccion__curso__nombre")
    def ver_curso(self, obj):
        return obj.matricula.seccion.curso.nombre