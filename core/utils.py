# core/utils.py
# Funciones de ayuda reutilizables. No saben nada de estudiantes ni de ningún modelo concreto.

# core/utils.py
# Funciones de ayuda reutilizables. No saben nada de estudiantes ni de ningún modelo concreto.

import os
import re
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from urllib.parse import unquote, urlparse

from django import forms
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from xhtml2pdf import pisa

def valor_campo(objeto, ruta):
    """
    Lee un dato de un objeto siguiendo una ruta con "__", igual que en los filtros de Django.

    Ejemplos:
        valor_campo(estudiante, "cedula")                     → "0950000001"
        valor_campo(estudiante, "carrera__facultad__nombre")  → "Facultad de Ciencias e Ingeniería"
        valor_campo(seccion, "jornada")                       → "Nocturna"  (texto del choice)
        valor_campo(matricula, "nota__promedio")              → ""  si la matrícula no tiene nota
    """
    actual = objeto
    partes = ruta.split("__")  # "carrera__facultad__nombre" → ["carrera", "facultad", "nombre"]

    for posicion, parte in enumerate(partes):
        # Si en el camino algo está vacío (ej: un ForeignKey en None), no seguimos
        if actual is None:
            return ""

        es_ultima_parte = posicion == len(partes) - 1
        try:
            # En la última parte, si el campo tiene choices, Django crea get_<campo>_display()
            # que devuelve el texto bonito ("Nocturna") en vez del valor guardado ("nocturna")
            if es_ultima_parte:
                metodo_display = getattr(actual, f"get_{parte}_display", None)
                if callable(metodo_display):
                    return metodo_display()

            # Avanzamos un paso: estudiante → carrera → facultad → nombre
            actual = getattr(actual, parte)

        # AttributeError: el campo no existe.
        # ObjectDoesNotExist: un OneToOne inverso vacío (ej: matricula.nota sin nota).
        except (AttributeError, ObjectDoesNotExist):
            return ""

    if actual is None:
        return ""
    if isinstance(actual, bool):  # True/False → "Sí"/"No" (útil para Periodo.activo)
        return "Sí" if actual else "No"
    return actual  # fechas y números se devuelven tal cual: el template los formatea en es-ec


def aplicar_estilos_bootstrap(form):
    """
    Agrega a cada campo del formulario la clase CSS de Bootstrap que le corresponde.
    Así cualquier formulario se ve bien sin escribir las clases a mano.
    """
    for campo in form.fields.values():
        widget = campo.widget
        if isinstance(widget, forms.CheckboxInput):
            clase = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            clase = "form-select"
        else:
            clase = "form-control"
        # Conservamos las clases que ya tuviera el widget y sumamos la nueva
        clases_actuales = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{clases_actuales} {clase}".strip()
    return form

# ============================================================
# EXPORTAR A EXCEL
# ============================================================
COLOR_ENCABEZADO = "0C4B33"  # verde oscuro
ANCHO_MAXIMO_COLUMNA = 50


def _preparar_valor_excel(valor):
    """
    Convierte un valor a algo que openpyxl sepa guardar.
    (El guion bajo al inicio indica que es una función "interna" de este archivo.)
    """
    # datetime va ANTES que date porque un datetime también es un date
    if isinstance(valor, datetime):
        # Excel no acepta zonas horarias: pasamos a hora de Guayaquil y quitamos la zona
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor).replace(tzinfo=None)
        return valor
    if isinstance(valor, (str, int, float, Decimal, date)):
        return valor  # tipos que Excel entiende directamente
    # Cualquier otra cosa (un objeto de modelo, un archivo de imagen…) se guarda como texto
    return str(valor)


def exportar_excel(titulo, encabezados, filas, nombre_archivo):
    """
    Crea un archivo Excel y lo devuelve como descarga.

        titulo         → texto de la fila 1
        encabezados    → ["Cédula", "Apellidos", ...]                  (fila 3)
        filas          → [["0950000001", "Torres Mendoza", ...], ...]  (desde la fila 4)
        nombre_archivo → "estudiantes"  → se descarga "estudiantes.xlsx"
    """
    libro = Workbook()   # un libro de Excel nuevo
    hoja = libro.active  # la primera hoja
    # El nombre de una hoja tiene máximo 31 caracteres y no acepta [ ] : * ? / \
    hoja.title = re.sub(r"[\[\]:*?/\\]", "", titulo)[:31] or "Reporte"

    # ---------- Fila 1: título ----------
    hoja.cell(row=1, column=1, value=titulo).font = Font(bold=True, size=14)

    # ---------- Fila 2: fecha de generación y cantidad (información extra) ----------
    generado = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    hoja.cell(row=2, column=1, value=f"Generado el {generado} · {len(filas)} registros").font = Font(
        italic=True, size=9, color="666666"
    )

    # ---------- Fila 3: encabezados ----------
    fuente_encabezado = Font(bold=True, color="FFFFFF")  # negrita, letra blanca
    fondo_encabezado = PatternFill(fill_type="solid", fgColor=COLOR_ENCABEZADO)
    for columna, texto in enumerate(encabezados, start=1):  # en Excel las columnas empiezan en 1
        celda = hoja.cell(row=3, column=columna, value=texto)
        celda.font = fuente_encabezado
        celda.fill = fondo_encabezado
        celda.alignment = Alignment(horizontal="center", vertical="center")

    # ---------- Fila 4 en adelante: datos ----------
    for numero_fila, fila in enumerate(filas, start=4):
        for columna, valor in enumerate(fila, start=1):
            celda = hoja.cell(row=numero_fila, column=columna, value=_preparar_valor_excel(valor))
            # Formato de fecha para que Excel la muestre como 02/02/2004
            if isinstance(celda.value, datetime):
                celda.number_format = "DD/MM/YYYY HH:MM"
            elif isinstance(celda.value, date):
                celda.number_format = "DD/MM/YYYY"

    # ---------- Ancho automático de columnas ----------
    # Se mide el texto más largo de cada columna (encabezado + datos, NO el título de la fila 1)
    for columna, encabezado in enumerate(encabezados, start=1):
        textos = [str(encabezado)] + [str(fila[columna - 1]) for fila in filas]
        ancho = max(len(texto) for texto in textos) + 2  # +2 de margen
        hoja.column_dimensions[get_column_letter(columna)].width = min(ancho, ANCHO_MAXIMO_COLUMNA)

    # ---------- Congelar encabezados ----------
    # "A4" congela todo lo que está ARRIBA de la fila 4: al bajar, el título y los encabezados se quedan quietos
    hoja.freeze_panes = "A4"

    # ---------- Autofiltro (extra): flechitas de filtro de Excel en los encabezados ----------
    if encabezados:
        ultima_columna = get_column_letter(len(encabezados))
        ultima_fila = max(3, len(filas) + 3)
        hoja.auto_filter.ref = f"A3:{ultima_columna}{ultima_fila}"

    # ---------- Respuesta de descarga ----------
    respuesta = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    # "attachment" le dice al navegador: descárgalo, no lo abras en la pestaña
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.xlsx"'
    libro.save(respuesta)  # openpyxl escribe el archivo directamente dentro de la respuesta
    return respuesta


# ============================================================
# TEXTO CORTO DE UN VALOR (para PDF y para describir filtros)
# ============================================================
def texto_valor(valor):
    """Convierte un valor a texto corto: fechas en dd/mm/aaaa, True → "Sí", None → ""."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):  # va ANTES que date (un datetime también es date)
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)  # a hora de Guayaquil
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return str(valor)


# ============================================================
# EXPORTAR A PDF (xhtml2pdf)
# ============================================================
def link_callback(uri, rel):
    """
    xhtml2pdf NO es un navegador: no sabe descargar "/media/foto.jpg" del servidor.
    Esta función le traduce cada URL a la ruta REAL del archivo en el disco.

        "/media/estudiantes/foto.jpg" → "C:/.../sistema_academico/media/estudiantes/foto.jpg"
        "/static/img/logo.png"        → "C:/.../sistema_academico/static/img/logo.png"
    """
    # urlparse(...).path quita "http://servidor" si viniera; unquote convierte %20 en espacio
    ruta = unquote(urlparse(uri).path).lstrip("/")
    # Quitamos la "/" inicial de todo para comparar igual ("media/" vs "/media/")
    media_url = settings.MEDIA_URL.lstrip("/")
    static_url = settings.STATIC_URL.lstrip("/")

    archivo = None
    if media_url and ruta.startswith(media_url):
        # Archivos subidos por los usuarios → están en MEDIA_ROOT
        archivo = os.path.join(settings.MEDIA_ROOT, ruta[len(media_url):])
    elif static_url and ruta.startswith(static_url):
        relativa = ruta[len(static_url):]
        # finders.find busca en STATICFILES_DIRS y en la carpeta static/ de cada app
        archivo = finders.find(relativa)
        if not archivo and getattr(settings, "STATIC_ROOT", None):
            archivo = os.path.join(settings.STATIC_ROOT, relativa)  # por si usas collectstatic

    # Si encontramos el archivo, devolvemos su ruta en disco; si no, la URL tal cual
    if archivo and os.path.isfile(archivo):
        return archivo
    return uri


def render_pdf(template, contexto, nombre_archivo, descargar=False):
    """
    Convierte un template HTML en PDF y lo devuelve como respuesta.

        descargar=False → "inline": el PDF se ABRE en el navegador
        descargar=True  → "attachment": el PDF se DESCARGA
    """
    # 1) Template + contexto → texto HTML
    html = render_to_string(template, contexto)

    # 2) HTML → PDF, escrito en un "archivo en memoria" (BytesIO), sin tocar el disco
    buffer = BytesIO()
    resultado = pisa.CreatePDF(
        html,
        dest=buffer,
        encoding="utf-8",             # para que salgan bien las tildes y la ñ
        link_callback=link_callback,  # para que salgan las imágenes
    )

    # Si xhtml2pdf tuvo un error, avisamos en vez de entregar un PDF dañado
    if resultado.err:
        return HttpResponse("Ocurrió un error al generar el PDF.", status=500)

    # 3) Respuesta con el contenido del PDF
    respuesta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    modo = "attachment" if descargar else "inline"
    respuesta["Content-Disposition"] = f'{modo}; filename="{nombre_archivo}.pdf"'
    return respuesta