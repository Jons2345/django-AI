# academico/management/commands/poblar_datos.py
# Comando para llenar la base de datos con datos de prueba.
# Se ejecuta con:  python manage.py poblar_datos
# Usa get_or_create, así que puedes correrlo varias veces sin duplicar datos.

import unicodedata
from collections import Counter
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from academico.models import (
    Carrera, Curso, EstadoNota, Estudiante, Facultad, Jornada, Matricula,
    Nota, Periodo, Profesor, Seccion, Semestre, Universidad,
)

# ------------------------------------------------------------
# DATOS DE PRUEBA (todos inventados)
# ------------------------------------------------------------
# (codigo, nombre, carrera, semestre, creditos)
DATOS_CURSOS = [
    ("SOF-101", "Programación I", "SOF", 1, 4),
    ("SOF-102", "Matemática Discreta", "SOF", 1, 3),
    ("SOF-201", "Programación II", "SOF", 2, 4),
    ("ADM-101", "Contabilidad General", "ADM", 1, 4),
    ("ADM-201", "Microeconomía", "ADM", 2, 3),
    ("ENF-101", "Anatomía Humana", "ENF", 1, 5),
]

# (cedula, nombres, apellidos, titulo)
DATOS_PROFESORES = [
    ("0911111111", "Roberto Carlos", "Lozano Vera", "Ing. en Sistemas, MSc."),
    ("0922222222", "Mónica Elizabeth", "Suárez Palma", "Lcda. en Matemáticas, PhD."),
    ("1733333333", "Hernán Patricio", "Carrillo Mena", "Ing. Comercial, MBA"),
]

# (curso, paralelo, jornada, posición del profesor en DATOS_PROFESORES)
DATOS_SECCIONES = [
    ("SOF-101", "A", Jornada.DIURNA, 0),
    ("SOF-102", "A", Jornada.NOCTURNA, 1),
    ("ADM-101", "A", Jornada.DIURNA, 2),
    ("ENF-101", "A", Jornada.NOCTURNA, 1),
]

# (cedula, nombres, apellidos, carrera)  → 10 de Software, 3 de Administración, 2 de Enfermería
DATOS_ESTUDIANTES = [
    ("0950000001", "Ana Lucía", "Torres Mendoza", "SOF"),
    ("0950000002", "Carlos Andrés", "Vera Zambrano", "SOF"),
    ("0950000003", "María José", "Cedeño Alvarado", "SOF"),
    ("0950000004", "Luis Fernando", "Mora Castro", "SOF"),
    ("0950000005", "Daniela Paola", "Ruiz Benítez", "SOF"),
    ("0950000006", "Jorge Esteban", "Salazar León", "SOF"),
    ("0950000007", "Valeria Sofía", "Andrade Pérez", "SOF"),
    ("0950000008", "Kevin Alexander", "Bravo Ortiz", "SOF"),
    ("0950000009", "Camila Fernanda", "Rivas Quiñónez", "SOF"),
    ("0950000010", "Diego Sebastián", "Núñez Villacís", "SOF"),
    ("0950000011", "Gabriela Estefanía", "Chávez Molina", "ADM"),
    ("0950000012", "Andrés Felipe", "Paredes Rosales", "ADM"),
    ("0950000013", "Paula Alejandra", "Espinoza Cruz", "ADM"),
    ("1750000014", "Sofía Isabel", "Herrera Ponce", "ENF"),
    ("1750000015", "Mateo Joaquín", "Guerrero Loor", "ENF"),
]

# Notas de ejemplo (n1, n2, n3). Se reparten en orden y vuelven a empezar al terminar.
NOTAS_EJEMPLO = [
    (85, 90, 78),  # 84.33 → aprobado
    (60, 55, 62),  # 59.00 → reprobado
    (70, 70, 70),  # 70.00 → aprobado (justo en el límite)
    (95, 88, 92),  # 91.67 → aprobado
    (45, 60, 50),  # 51.67 → reprobado
    (72, 68, 69),  # 69.67 → reprobado (¡casi!)
    (80, 75, 85),  # 80.00 → aprobado
]


def quitar_tildes(texto):
    # "Núñez" → "Nunez" (para armar correos sin tildes ni ñ)
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def crear_email(nombres, apellidos, dominio):
    # "Ana Lucía", "Torres Mendoza" → "ana.torres@dominio"
    usuario = f"{nombres.split()[0]}.{apellidos.split()[0]}".lower()
    return f"{quitar_tildes(usuario)}@{dominio}"


class Command(BaseCommand):
    # Texto que aparece con: python manage.py help poblar_datos
    help = "Crea datos de prueba para el sistema académico (sin duplicar)."

    def obtener_o_crear(self, modelo, defaults=None, **busqueda):
        """
        Ayudante sobre get_or_create:
        - 'busqueda' son los campos que identifican al registro (ej: cedula=...).
        - 'defaults' son los demás campos, que solo se usan si hay que CREARLO.
        Además cuenta cuántos registros nuevos se crearon de cada modelo.
        """
        defaults = defaults or {}
        defaults.setdefault("user", self.usuario)  # el campo user de ModeloBase
        obj, creado = modelo.objects.get_or_create(defaults=defaults, **busqueda)
        if creado:
            self.nuevos[modelo] += 1
        return obj

    # transaction.atomic: si algo falla a la mitad, se deshace TODO (no quedan datos a medias)
    @transaction.atomic
    def handle(self, *args, **options):
        self.nuevos = Counter()  # contador de registros nuevos por modelo

        # Usamos el primer superusuario como "user" que registró los datos
        self.usuario = get_user_model().objects.filter(is_superuser=True).first()
        if self.usuario is None:
            self.stdout.write(self.style.WARNING(
                "No hay superusuario: los datos quedarán sin usuario. "
                "Crea uno con: python manage.py createsuperuser"
            ))

        # ---------- 1. Universidades (2) ----------
        uel = self.obtener_o_crear(
            Universidad, nombre="Universidad Estatal del Litoral",
            defaults={"siglas": "UEL", "ciudad": "Guayaquil"},
        )
        uap = self.obtener_o_crear(
            Universidad, nombre="Universidad Andina del Pichincha",
            defaults={"siglas": "UAP", "ciudad": "Quito"},
        )

        # ---------- 2. Facultades (3) ----------
        fac_ing = self.obtener_o_crear(
            Facultad, universidad=uel, nombre="Facultad de Ciencias e Ingeniería",
            defaults={"decano": "Ing. Ramiro Ochoa, MSc."},
        )
        fac_adm = self.obtener_o_crear(
            Facultad, universidad=uel, nombre="Facultad de Ciencias Administrativas",
            defaults={"decano": "Econ. Teresa Villamar, MBA"},
        )
        fac_sal = self.obtener_o_crear(
            Facultad, universidad=uap, nombre="Facultad de Ciencias de la Salud",
            defaults={"decano": "Dra. Patricia Jaramillo"},
        )

        # ---------- 3. Carreras (3) ----------
        # Diccionario {codigo: carrera} para buscarlas fácil después
        carreras = {
            "SOF": self.obtener_o_crear(Carrera, codigo="SOF", defaults={
                "facultad": fac_ing, "nombre": "Ingeniería de Software", "duracion_semestres": 8}),
            "ADM": self.obtener_o_crear(Carrera, codigo="ADM", defaults={
                "facultad": fac_adm, "nombre": "Administración de Empresas", "duracion_semestres": 8}),
            "ENF": self.obtener_o_crear(Carrera, codigo="ENF", defaults={
                "facultad": fac_sal, "nombre": "Enfermería", "duracion_semestres": 9}),
        }

        # ---------- 4. Semestres (2) ----------
        semestres = {
            1: self.obtener_o_crear(Semestre, numero=1, defaults={"nombre": "Primer semestre"}),
            2: self.obtener_o_crear(Semestre, numero=2, defaults={"nombre": "Segundo semestre"}),
        }

        # ---------- 5. Periodo activo (1) ----------
        periodo = self.obtener_o_crear(Periodo, nombre="2026-2", defaults={
            "fecha_inicio": date(2026, 10, 5),
            "fecha_fin": date(2027, 2, 26),
            "activo": True,
        })

        # ---------- 6. Cursos (6) ----------
        cursos = {}
        for codigo, nombre, carrera, semestre, creditos in DATOS_CURSOS:
            cursos[codigo] = self.obtener_o_crear(Curso, codigo=codigo, defaults={
                "nombre": nombre,
                "carrera": carreras[carrera],
                "semestre": semestres[semestre],
                "creditos": creditos,
            })

        # ---------- 7. Profesores (3) ----------
        profesores = []
        for cedula, nombres, apellidos, titulo in DATOS_PROFESORES:
            profesores.append(self.obtener_o_crear(Profesor, cedula=cedula, defaults={
                "nombres": nombres,
                "apellidos": apellidos,
                "titulo": titulo,
                "email": crear_email(nombres, apellidos, "docentes.edu.ec"),
            }))

        # ---------- 8. Secciones (4: 2 diurnas y 2 nocturnas) ----------
        secciones = []
        for codigo_curso, paralelo, jornada, idx_profesor in DATOS_SECCIONES:
            secciones.append(self.obtener_o_crear(
                Seccion,
                # estos 4 campos son la restricción única de Seccion
                curso=cursos[codigo_curso], periodo=periodo, paralelo=paralelo, jornada=jornada,
                defaults={"profesor": profesores[idx_profesor], "cupo": 30},
            ))

        # ---------- 9. Estudiantes (15) ----------
        estudiantes = []
        for i, (cedula, nombres, apellidos, carrera) in enumerate(DATOS_ESTUDIANTES, start=1):
            estudiantes.append(self.obtener_o_crear(Estudiante, cedula=cedula, defaults={
                "nombres": nombres,
                "apellidos": apellidos,
                "carrera": carreras[carrera],
                "email": crear_email(nombres, apellidos, "estudiantes.edu.ec"),
                "telefono": f"09912345{i:02d}",            # :02d → rellena con cero: 01, 02...
                "fecha_nacimiento": date(2004, (i % 12) + 1, (i % 28) + 1),
            }))

        # ---------- 10. Matrículas (25) ----------
        # Cada estudiante solo se matricula en secciones de SU carrera (regla de Matricula.clean)
        # Software: 10 × 2 secciones = 20 | Administración: 3 × 1 = 3 | Enfermería: 2 × 1 = 2 → 25
        secciones_por_carrera = {
            "SOF": [secciones[0], secciones[1]],
            "ADM": [secciones[2]],
            "ENF": [secciones[3]],
        }
        matriculas = []
        for estudiante in estudiantes:
            for seccion in secciones_por_carrera[estudiante.carrera.codigo]:
                matriculas.append(
                    self.obtener_o_crear(Matricula, estudiante=estudiante, seccion=seccion)
                )

        # ---------- 11. Notas (25, variadas) ----------
        for i, matricula in enumerate(matriculas):
            # i % 7 → 0,1,2,...,6,0,1,... así se repiten los 7 ejemplos
            n1, n2, n3 = NOTAS_EJEMPLO[i % len(NOTAS_EJEMPLO)]
            # Al crearse, Nota.save() calcula solo el promedio y el estado
            self.obtener_o_crear(Nota, matricula=matricula, defaults={
                "n1": Decimal(n1), "n2": Decimal(n2), "n3": Decimal(n3),
            })

        # ---------- RESUMEN ----------
        self.stdout.write(self.style.SUCCESS("\n✔ Datos de prueba listos\n"))
        modelos = [Universidad, Facultad, Carrera, Semestre, Periodo, Curso,
                   Profesor, Estudiante, Seccion, Matricula, Nota]
        for modelo in modelos:
            nombre = modelo._meta.verbose_name_plural.capitalize()
            # :<14 → alinea el texto a la izquierda en 14 espacios (para que se vea como tabla)
            self.stdout.write(
                f"  {nombre:<14} total: {modelo.objects.count():>3}   nuevos: {self.nuevos[modelo]}"
            )
        aprobados = Nota.objects.filter(estado=EstadoNota.APROBADO).count()
        reprobados = Nota.objects.filter(estado=EstadoNota.REPROBADO).count()
        self.stdout.write(f"\n  Aprobados: {aprobados} | Reprobados: {reprobados}\n")