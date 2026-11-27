# academico/models.py
# Modelos del negocio: el sistema académico.
# TODOS heredan de ModeloBase, así que todos tienen user, fecha_creacion y fecha_modificacion.

from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import ModeloBase


# ============================================================
# CONSTANTES
# ============================================================
NOTA_MINIMA_APROBACION = Decimal("70")  # promedio mínimo para aprobar
NOTA_MINIMA = Decimal("0")
NOTA_MAXIMA = Decimal("100")

# Validadores reutilizables: la nota debe estar entre 0 y 100
VALIDADORES_NOTA = [
    MinValueValidator(NOTA_MINIMA),
    MaxValueValidator(NOTA_MAXIMA),
]


# ============================================================
# CHOICES (opciones fijas)
# TextChoices crea una lista de opciones: (valor guardado, texto que se muestra)
# ============================================================
class Jornada(models.TextChoices):
    DIURNA = "diurna", "Diurna"
    NOCTURNA = "nocturna", "Nocturna"


class EstadoNota(models.TextChoices):
    APROBADO = "aprobado", "Aprobado"
    REPROBADO = "reprobado", "Reprobado"


# ============================================================
# UNIVERSIDAD
# ============================================================
class Universidad(ModeloBase):
    nombre = models.CharField(max_length=200, unique=True, verbose_name="nombre")
    siglas = models.CharField(max_length=20, verbose_name="siglas")
    ciudad = models.CharField(max_length=100, verbose_name="ciudad")
    # ImageField necesita pillow. Las imágenes se guardan en MEDIA_ROOT/universidades/
    logo = models.ImageField(upload_to="universidades/", blank=True, null=True, verbose_name="logo")

    class Meta:
        verbose_name = "universidad"
        verbose_name_plural = "universidades"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.siglas} - {self.nombre}"


# ============================================================
# FACULTAD
# ============================================================
class Facultad(ModeloBase):
    # PROTECT: no deja borrar una universidad si todavía tiene facultades
    universidad = models.ForeignKey(
        Universidad,
        on_delete=models.PROTECT,
        related_name="facultades",  # permite hacer: universidad.facultades.all()
        verbose_name="universidad",
    )
    nombre = models.CharField(max_length=200, verbose_name="nombre")
    decano = models.CharField(max_length=200, blank=True, verbose_name="decano")  # opcional

    class Meta:
        verbose_name = "facultad"
        verbose_name_plural = "facultades"
        ordering = ["universidad__nombre", "nombre"]
        constraints = [
            # El mismo nombre de facultad NO se puede repetir dentro de la misma universidad,
            # pero sí puede existir en otra universidad distinta.
            models.UniqueConstraint(
                fields=["universidad", "nombre"],
                name="facultad_unica_por_universidad",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.universidad.siglas})"


# ============================================================
# CARRERA
# ============================================================
class Carrera(ModeloBase):
    facultad = models.ForeignKey(
        Facultad,
        on_delete=models.PROTECT,
        related_name="carreras",  # facultad.carreras.all()
        verbose_name="facultad",
    )
    codigo = models.CharField(max_length=20, unique=True, verbose_name="código")
    nombre = models.CharField(max_length=200, verbose_name="nombre")
    duracion_semestres = models.PositiveSmallIntegerField(default=8, verbose_name="duración (semestres)")

    class Meta:
        verbose_name = "carrera"
        verbose_name_plural = "carreras"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# ============================================================
# SEMESTRE
# ============================================================
class Semestre(ModeloBase):
    # Solo se permiten números del 1 al 12
    numero = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="número",
    )
    nombre = models.CharField(max_length=50, verbose_name="nombre")  # ej: "Primer semestre"

    class Meta:
        verbose_name = "semestre"
        verbose_name_plural = "semestres"
        ordering = ["numero"]

    def __str__(self):
        return self.nombre


# ============================================================
# PERIODO
# ============================================================
class Periodo(ModeloBase):
    nombre = models.CharField(max_length=20, unique=True, verbose_name="nombre")  # ej: "2026-1"
    fecha_inicio = models.DateField(verbose_name="fecha de inicio")
    fecha_fin = models.DateField(verbose_name="fecha de fin")
    activo = models.BooleanField(default=True, verbose_name="activo")

    class Meta:
        verbose_name = "periodo"
        verbose_name_plural = "periodos"
        ordering = ["-fecha_inicio"]  # el signo "-" ordena del más reciente al más antiguo

    def __str__(self):
        return self.nombre

    def clean(self):
        # clean() se ejecuta al validar formularios (o al llamar full_clean()).
        # Solo comparamos si las dos fechas tienen valor.
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            # Al usar un diccionario, el error aparece junto al campo fecha_fin en el formulario
            raise ValidationError(
                {"fecha_fin": "La fecha de fin debe ser posterior a la fecha de inicio."}
            )


# ============================================================
# CURSO (la materia)
# ============================================================
class Curso(ModeloBase):
    carrera = models.ForeignKey(
        Carrera,
        on_delete=models.PROTECT,
        related_name="cursos",  # carrera.cursos.all()
        verbose_name="carrera",
    )
    semestre = models.ForeignKey(
        Semestre,
        on_delete=models.PROTECT,
        related_name="cursos",  # semestre.cursos.all()
        verbose_name="semestre",
    )
    codigo = models.CharField(max_length=20, unique=True, verbose_name="código")
    nombre = models.CharField(max_length=200, verbose_name="nombre")
    creditos = models.PositiveSmallIntegerField(verbose_name="créditos")

    class Meta:
        verbose_name = "curso"
        verbose_name_plural = "cursos"
        ordering = ["carrera__nombre", "semestre__numero", "nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# ============================================================
# PROFESOR
# ============================================================
class Profesor(ModeloBase):
    cedula = models.CharField(max_length=10, unique=True, verbose_name="cédula")
    nombres = models.CharField(max_length=100, verbose_name="nombres")
    apellidos = models.CharField(max_length=100, verbose_name="apellidos")
    email = models.EmailField(verbose_name="correo electrónico")
    titulo = models.CharField(max_length=150, verbose_name="título")  # ej: "Ing. en Sistemas, MSc."

    class Meta:
        verbose_name = "profesor"
        verbose_name_plural = "profesores"
        ordering = ["apellidos", "nombres"]

    @property
    def nombre_completo(self):
        # @property permite usarlo como campo: profesor.nombre_completo (sin paréntesis)
        return f"{self.apellidos} {self.nombres}"

    def __str__(self):
        return self.nombre_completo


# ============================================================
# ESTUDIANTE
# ============================================================
class Estudiante(ModeloBase):
    cedula = models.CharField(max_length=10, unique=True, verbose_name="cédula")
    nombres = models.CharField(max_length=100, verbose_name="nombres")
    apellidos = models.CharField(max_length=100, verbose_name="apellidos")
    email = models.EmailField(verbose_name="correo electrónico")
    telefono = models.CharField(max_length=15, verbose_name="teléfono")
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="fecha de nacimiento")  # opcional
    carrera = models.ForeignKey(
        Carrera,
        on_delete=models.PROTECT,
        related_name="estudiantes",  # carrera.estudiantes.all()
        verbose_name="carrera",
    )
    foto = models.ImageField(upload_to="estudiantes/", blank=True, null=True, verbose_name="foto")

    class Meta:
        verbose_name = "estudiante"
        verbose_name_plural = "estudiantes"
        ordering = ["apellidos", "nombres"]

    @property
    def nombre_completo(self):
        return f"{self.apellidos} {self.nombres}"

    def __str__(self):
        return f"{self.cedula} - {self.nombre_completo}"


# ============================================================
# SECCION (la oferta de un curso en un periodo)
# ============================================================
class Seccion(ModeloBase):
    curso = models.ForeignKey(
        Curso, on_delete=models.PROTECT, related_name="secciones", verbose_name="curso"
    )
    periodo = models.ForeignKey(
        Periodo, on_delete=models.PROTECT, related_name="secciones", verbose_name="periodo"
    )
    profesor = models.ForeignKey(
        Profesor, on_delete=models.PROTECT, related_name="secciones", verbose_name="profesor"
    )
    paralelo = models.CharField(max_length=5, default="A", verbose_name="paralelo")
    jornada = models.CharField(
        max_length=10,
        choices=Jornada.choices,   # solo permite "diurna" o "nocturna"
        default=Jornada.DIURNA,
        verbose_name="jornada",
    )
    cupo = models.PositiveSmallIntegerField(default=30, verbose_name="cupo")
    # Relación N:M con Estudiante, pero usando la tabla intermedia Matricula.
    # "through" significa: la relación se guarda en el modelo Matricula (que tiene datos extra como la fecha).
    estudiantes = models.ManyToManyField(
        "Estudiante",
        through="Matricula",
        related_name="secciones",  # estudiante.secciones.all()
        verbose_name="estudiantes",
    )

    class Meta:
        verbose_name = "sección"
        verbose_name_plural = "secciones"
        ordering = ["periodo__nombre", "curso__nombre", "paralelo"]
        constraints = [
            # No puede haber dos secciones iguales del mismo curso, periodo, paralelo y jornada
            models.UniqueConstraint(
                fields=["curso", "periodo", "paralelo", "jornada"],
                name="seccion_unica",
            ),
        ]

    @property
    def inscritos(self):
        # Cuenta cuántas matrículas tiene esta sección
        return self.matriculas.count()

    def __str__(self):
        return f"{self.curso.nombre} - {self.paralelo} ({self.get_jornada_display()}) - {self.periodo}"


# ============================================================
# MATRICULA (tabla intermedia entre Estudiante y Seccion)
# ============================================================
class Matricula(ModeloBase):
    estudiante = models.ForeignKey(
        Estudiante, on_delete=models.PROTECT, related_name="matriculas", verbose_name="estudiante"
    )
    seccion = models.ForeignKey(
        Seccion, on_delete=models.PROTECT, related_name="matriculas", verbose_name="sección"
    )
    # Se pasa la FUNCIÓN timezone.localdate (sin paréntesis) para que calcule
    # la fecha de HOY cada vez que se crea una matrícula, con la zona America/Guayaquil.
    fecha = models.DateField(default=timezone.localdate, verbose_name="fecha")

    class Meta:
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"
        ordering = ["-fecha"]
        constraints = [
            # Un estudiante no se puede matricular dos veces en la misma sección
            models.UniqueConstraint(
                fields=["estudiante", "seccion"],
                name="matricula_unica",
            ),
        ]

    def __str__(self):
        return f"{self.estudiante.nombre_completo} → {self.seccion}"

    def clean(self):
        # Si todavía no se eligió estudiante o sección, no validamos (el formulario ya avisará)
        if not self.estudiante_id or not self.seccion_id:
            return

        # Regla 1: el curso de la sección debe pertenecer a la carrera del estudiante
        if self.seccion.curso.carrera_id != self.estudiante.carrera_id:
            raise ValidationError(
                {"seccion": "El curso de esta sección no pertenece a la carrera del estudiante."}
            )

        # Regla 2: la sección debe tener cupo disponible.
        # exclude(pk=self.pk) evita contarse a sí misma cuando se está EDITANDO una matrícula.
        ocupados = self.seccion.matriculas.exclude(pk=self.pk).count()
        if ocupados >= self.seccion.cupo:
            raise ValidationError({"seccion": "La sección ya no tiene cupo disponible."})


# ============================================================
# NOTA (1 nota por matrícula)
# ============================================================
class Nota(ModeloBase):
    # OneToOne: cada matrícula tiene UNA sola nota. CASCADE: si se borra la matrícula, se borra su nota.
    matricula = models.OneToOneField(
        Matricula,
        on_delete=models.CASCADE,
        related_name="nota",  # matricula.nota (singular, porque es solo una)
        verbose_name="matrícula",
    )
    # max_digits=5 y decimal_places=2 → permite hasta 999.99, los validadores limitan a 0-100
    n1 = models.DecimalField(max_digits=5, decimal_places=2, default=NOTA_MINIMA,
                             validators=VALIDADORES_NOTA, verbose_name="nota 1")
    n2 = models.DecimalField(max_digits=5, decimal_places=2, default=NOTA_MINIMA,
                             validators=VALIDADORES_NOTA, verbose_name="nota 2")
    n3 = models.DecimalField(max_digits=5, decimal_places=2, default=NOTA_MINIMA,
                             validators=VALIDADORES_NOTA, verbose_name="nota 3")
    # Estos dos campos NO se editan a mano: los calcula save()
    promedio = models.DecimalField(max_digits=5, decimal_places=2, default=NOTA_MINIMA,
                                   editable=False, verbose_name="promedio")
    estado = models.CharField(max_length=10, choices=EstadoNota.choices,
                              default=EstadoNota.REPROBADO, editable=False, verbose_name="estado")

    class Meta:
        verbose_name = "nota"
        verbose_name_plural = "notas"
        ordering = ["matricula__estudiante__apellidos", "matricula__estudiante__nombres"]

    def __str__(self):
        return f"{self.matricula.estudiante.nombre_completo} - {self.promedio} ({self.get_estado_display()})"

    def calcular_promedio(self):
        # Sumamos las 3 notas, dividimos para 3 y redondeamos a 2 decimales.
        # quantize(Decimal("0.01")) = dejar 2 decimales; ROUND_HALF_UP = redondeo normal (0.005 → 0.01)
        total = Decimal(self.n1) + Decimal(self.n2) + Decimal(self.n3)
        return (total / 3).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        # Antes de guardar, calculamos promedio y estado
        self.promedio = self.calcular_promedio()
        if self.promedio >= NOTA_MINIMA_APROBACION:
            self.estado = EstadoNota.APROBADO
        else:
            self.estado = EstadoNota.REPROBADO
        super().save(*args, **kwargs)  # ahora sí guardamos normalmente