# core/models.py
# Aquí van los componentes reutilizables del proyecto.
# ModeloBase es "abstracto": Django NO crea una tabla para él,
# solo copia sus campos en cada modelo que herede de él.

from django.conf import settings
from django.db import models


class ModeloBase(models.Model):
    # Usuario que registró el dato.
    # settings.AUTH_USER_MODEL apunta al modelo User de Django (es la forma recomendada).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # si se borra el usuario, el registro queda con user vacío
        null=True,                  # permite NULL en la base de datos
        blank=True,                 # permite dejarlo vacío en formularios
        editable=False,             # no aparece en formularios ni en el admin para editar
        # %(app_label)s y %(class)s se reemplazan solos, ej: "academico_estudiante_registrados".
        # Así cada modelo hijo tiene un related_name distinto y no chocan entre sí.
        related_name="%(app_label)s_%(class)s_registrados",
        verbose_name="usuario",
    )
    # Se llena automáticamente UNA sola vez, cuando se crea el registro
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="fecha de creación")
    # Se actualiza automáticamente CADA vez que se guarda el registro
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="fecha de modificación")

    class Meta:
        abstract = True  # ← esto lo convierte en modelo abstracto (sin tabla propia)