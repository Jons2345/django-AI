# academico/forms.py
# Formularios de la app academico.

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.forms import inlineformset_factory

from core.utils import aplicar_estilos_bootstrap

from .models import Carrera, Facultad, Matricula, Nota, Seccion


class FiltroEstudianteForm(forms.Form):
    # forms.Form (no ModelForm): solo sirve para filtrar, no guarda nada.
    # required=False en TODOS: el usuario puede llenar solo los que quiera.

    texto = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.TextInput(attrs={"placeholder": "Nombres, apellidos o cédula"}),
    )
    carrera = forms.ModelChoiceField(
        queryset=Carrera.objects.all(),  # lista desplegable con las carreras
        required=False,
        empty_label="Todas",             # texto de la opción vacía
    )
    facultad = forms.ModelChoiceField(
        queryset=Facultad.objects.select_related("universidad"),  # su __str__ usa la universidad
        required=False,
        empty_label="Todas",
    )
    # type="date" muestra el calendario del navegador.
    # format="%Y-%m-%d" es el formato que ese calendario entiende (para que no se borre al filtrar).
    nacido_desde = forms.DateField(
        required=False,
        label="Nacido desde",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    nacido_hasta = forms.DateField(
        required=False,
        label="Nacido hasta",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def clean(self):
        # Validación extra: "desde" no puede ser mayor que "hasta"
        datos = super().clean()
        desde = datos.get("nacido_desde")
        hasta = datos.get("nacido_hasta")
        if desde and hasta and desde > hasta:
            raise ValidationError("La fecha 'Nacido desde' no puede ser mayor que 'Nacido hasta'.")
        return datos
    

# ============================================================
# MATRÍCULA (formulario maestro)
# ============================================================
class SeccionConCupoField(forms.ModelChoiceField):
    """Lista desplegable de secciones que muestra: SOF-101 A · Nocturna · 2026-2 (12/30)"""

    def label_from_instance(self, seccion):
        # label_from_instance decide el TEXTO de cada opción (por defecto sería el __str__)
        # total_inscritos viene del annotate() del queryset (1 sola consulta para todas)
        inscritos = getattr(seccion, "total_inscritos", seccion.inscritos)
        return (
            f"{seccion.curso.codigo} {seccion.paralelo} · {seccion.get_jornada_display()} · "
            f"{seccion.periodo.nombre} ({inscritos}/{seccion.cupo})"
        )


class MatriculaForm(forms.ModelForm):
    # Reemplazamos el campo "seccion" automático por nuestro campo con el texto personalizado.
    # El queryset real se pone en __init__ (aquí .none() es solo un valor inicial).
    seccion = SeccionConCupoField(
        queryset=Seccion.objects.none(),
        label="Sección",
        help_text="Solo secciones del periodo activo. Entre paréntesis: inscritos/cupo.",
    )

    class Meta:
        model = Matricula
        fields = ["estudiante", "seccion", "fecha"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo secciones del periodo activo...
        condicion = Q(periodo__activo=True)
        # ...pero si estamos EDITANDO, también la sección que ya tenía (aunque su periodo no esté activo)
        if self.instance.pk and self.instance.seccion_id:
            condicion |= Q(pk=self.instance.seccion_id)

        self.fields["seccion"].queryset = (
            Seccion.objects.filter(condicion)
            .select_related("curso", "periodo")               # para el texto de la opción
            .annotate(total_inscritos=Count("matriculas"))    # cuenta inscritos en la MISMA consulta
            .order_by("curso__codigo", "paralelo", "jornada")
        )
        aplicar_estilos_bootstrap(self)  # componente de core


# ============================================================
# NOTA (formulario detalle, dentro de la matrícula)
# ============================================================
class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ["n1", "n2", "n3"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_estilos_bootstrap(self)


# Un "inline formset" = formularios de un modelo HIJO (Nota) atados a un PADRE (Matricula).
# Como Nota es OneToOne, como máximo hay 1 formulario.
NotaFormSet = inlineformset_factory(
    Matricula,          # modelo padre
    Nota,               # modelo hijo
    form=NotaForm,      # para que tenga estilos Bootstrap
    fields=["n1", "n2", "n3"],
    extra=1,            # 1 formulario vacío si la matrícula aún no tiene nota
    max_num=1,          # nunca más de 1
    can_delete=False,   # no se muestra la casilla "eliminar"
)