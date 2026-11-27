# core/mixins.py
# Mixins reutilizables para las vistas basadas en clases.
# Un "mixin" es una clase pequeña que agrega UNA habilidad extra a otra vista.

# core/mixins.py
# Mixins reutilizables para las vistas basadas en clases.

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .utils import aplicar_estilos_bootstrap, exportar_excel, render_pdf, texto_valor, valor_campo

class UsuarioRegistroMixin:
    """
    Pone automáticamente el usuario que inició sesión en el campo 'user'
    de ModeloBase al guardar un formulario (CreateView / UpdateView).

    Uso (el orden importa):
        class EstudianteCrearView(LoginRequiredMixin, UsuarioRegistroMixin, CreateView):
    """

    def form_valid(self, form):
        # Solo se asigna si todavía no tiene usuario: se conserva quién REGISTRÓ el dato
        if not form.instance.user_id:
            form.instance.user = self.request.user
        return super().form_valid(form)


class FiltroCamposMixin:
    """
    Agrega a un ListView: formulario de filtros + selección de columnas.
    NO sabe nada del modelo: cada vista le dice qué formulario, qué columnas y cómo filtrar.

    Uso:
        class EstudianteListView(LoginRequiredMixin, FiltroCamposMixin, ListView):
            filtro_form_class = FiltroEstudianteForm
            campos_disponibles = [("cedula", "Cédula"), ("carrera__nombre", "Carrera")]
            campos_por_defecto = ["cedula"]

            def filtrar(self, queryset, datos):
                ...
                return queryset
    """

    filtro_form_class = None   # clase del formulario de filtros (un forms.Form)
    campos_disponibles = []    # [("ruta", "Título"), ...] columnas que el usuario PUEDE elegir
    campos_por_defecto = []    # ["ruta", ...] columnas que se muestran si no elige ninguna
    # Parámetros que NO se copian en "consulta" (cada enlace pone el suyo)
    parametros_excluidos = ("page", "exportar")

    # ---------- 1. Filtrar ----------
    def filtrar(self, queryset, datos):
        """Cada vista lo SOBRESCRIBE. 'datos' es el cleaned_data del formulario."""
        return queryset

    def get_filtro_form(self):
        if self.filtro_form_class is None:
            return None
        # "request.GET or None": si la URL no trae parámetros, el formulario queda
        # "sin datos" y no muestra errores al abrir la página por primera vez
        form = self.filtro_form_class(self.request.GET or None)
        return aplicar_estilos_bootstrap(form)

    def get_queryset(self):
        queryset = super().get_queryset()        # el queryset normal del ListView
        self.filtro_form = self.get_filtro_form()  # lo guardamos para enviarlo al template
        # Solo filtramos si el formulario existe y sus datos son válidos
        if self.filtro_form is not None and self.filtro_form.is_valid():
            queryset = self.filtrar(queryset, self.filtro_form.cleaned_data)
        return queryset

    # ---------- 2. Columnas ----------
    def get_campos_seleccionados(self):
        # ?campos=cedula&campos=email → ["cedula", "email"]
        pedidas = self.request.GET.getlist("campos")
        # SEGURIDAD: solo aceptamos rutas que están en campos_disponibles.
        # Sin esto, alguien podría escribir en la URL ?campos=user__password
        # Además, recorrer campos_disponibles mantiene siempre el mismo orden de columnas.
        elegidas = [ruta for ruta, _titulo in self.campos_disponibles if ruta in pedidas]
        return elegidas or list(self.campos_por_defecto)

    # ---------- 3. Consulta actual (para los enlaces) ----------
    def get_consulta(self):
        # request.GET no se puede modificar: .copy() crea una copia que sí se puede
        parametros = self.request.GET.copy()
        for nombre in self.parametros_excluidos:
            parametros.pop(nombre, None)  # quita "page" y "exportar" si existen
        # urlencode() lo convierte en texto: "texto=ana&campos=cedula&campos=email"
        return parametros.urlencode()

    # ---------- 4. Enviar todo al template ----------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        campos = self.get_campos_seleccionados()
        titulos = dict(self.campos_disponibles)  # {"cedula": "Cédula", ...}

        # object_list = los objetos de la PÁGINA actual (ya filtrados y paginados)
        filas = [
            (objeto, [valor_campo(objeto, ruta) for ruta in campos])
            for objeto in context["object_list"]
        ]
        # Guardamos también el objeto: servirá luego para los botones Ver/Editar/Eliminar

        context.update({
            "filtro_form": getattr(self, "filtro_form", None),
            "campos_disponibles": self.campos_disponibles,
            "campos_seleccionados": campos,
            "encabezados": [titulos[ruta] for ruta in campos],
            "filas": filas,
            "consulta": self.get_consulta(),
        })
        return context
    
class ExportarMixin(FiltroCamposMixin):
    """
    FiltroCamposMixin + exportar a Excel y PDF con los MISMOS filtros y columnas de la tabla.

    Uso:
        class EstudianteListView(LoginRequiredMixin, ExportarMixin, ListView):
            titulo_reporte = "Listado de estudiantes"
            nombre_archivo = "estudiantes"
    """

    titulo_reporte = "Reporte"                 # título del Excel y del PDF
    nombre_archivo = "reporte"                 # sin extensión
    template_pdf = "core/pdf/listado.html"     # template genérico del PDF
    logo_reporte = None                        # opcional: ruta dentro de static, ej "img/logo.png"

    def get(self, request, *args, **kwargs):
        formato = request.GET.get("exportar")  # None si no viene
        if formato == "excel":
            return self.generar_excel()
        if formato == "pdf":
            return self.generar_pdf()
        return super().get(request, *args, **kwargs)  # página normal

    # ---------- Datos comunes para Excel y PDF ----------
    def obtener_datos_exportacion(self):
        """Devuelve (encabezados, filas) con los mismos filtros y columnas de la tabla, SIN paginar."""
        queryset = self.get_queryset()               # mismos filtros
        campos = self.get_campos_seleccionados()     # mismas columnas (con validación de seguridad)
        titulos = dict(self.campos_disponibles)
        encabezados = [titulos[ruta] for ruta in campos]
        filas = [[valor_campo(objeto, ruta) for ruta in campos] for objeto in queryset]
        return encabezados, filas

    # ---------- Excel ----------
    def generar_excel(self):
        encabezados, filas = self.obtener_datos_exportacion()
        return exportar_excel(self.titulo_reporte, encabezados, filas, self.nombre_archivo)

    # ---------- PDF ----------
    def generar_pdf(self):
        encabezados, filas = self.obtener_datos_exportacion()
        # En Excel conviene la fecha "real"; en el PDF solo necesitamos texto corto
        filas_texto = [[texto_valor(valor) for valor in fila] for fila in filas]
        contexto = {
            "titulo": self.titulo_reporte,
            "encabezados": encabezados,
            "filas": filas_texto,
            "total": len(filas_texto),
            "filtros": self.filtros_aplicados(),
            "fecha": timezone.localtime(),     # fecha y hora de Guayaquil
            "usuario": self.request.user,
            "logo_reporte": self.logo_reporte,
        }
        return render_pdf(self.template_pdf, contexto, self.nombre_archivo)

    def filtros_aplicados(self):
        """
        Describe en texto los filtros que el usuario llenó, con la etiqueta del formulario.
        Ejemplo: ["Buscar: ana", "Carrera: SOF - Ingeniería de Software"]
        """
        form = getattr(self, "filtro_form", None)  # lo creó get_queryset()
        if form is None or not form.is_valid():
            return []

        descripcion = []
        for nombre, campo in form.fields.items():
            valor = form.cleaned_data.get(nombre)

            # Saltamos los filtros vacíos (y las casillas sin marcar)
            if valor in (None, "") or valor is False:
                continue

            # Varios valores (ej: ModelMultipleChoiceField) → "A, B, C"
            if hasattr(valor, "__iter__") and not isinstance(valor, str):
                valores = list(valor)
                if not valores:
                    continue
                texto = ", ".join(texto_valor(v) for v in valores)
            # Lista desplegable de un modelo → el __str__ del objeto elegido
            # (va ANTES de ChoiceField porque ModelChoiceField es un tipo de ChoiceField)
            elif isinstance(campo, forms.ModelChoiceField):
                texto = str(valor)
            # Lista desplegable con choices fijos → el texto visible, no el valor guardado
            elif isinstance(campo, forms.ChoiceField):
                texto = str(dict(campo.choices).get(valor, valor))
            else:
                texto = texto_valor(valor)

            # form[nombre].label usa la etiqueta del campo (o la genera desde el nombre)
            descripcion.append(f"{form[nombre].label}: {texto}")
        return descripcion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["puede_exportar"] = True  # el panel de filtros muestra los botones Excel y PDF
        return context
    
    
class ComprobantePdfMixin:
    """
    Convierte un DetailView en un PDF de UN registro (ficha, comprobante, certificado…).
    No sabe nada del modelo: cada vista dice qué template usar y cómo se llama el archivo.

    Uso:
        class EstudiantePdfView(LoginRequiredMixin, ComprobantePdfMixin, DetailView):
            model = Estudiante
            template_pdf = "academico/pdf/estudiante_ficha.html"
            nombre_archivo = "estudiante"       # → estudiante-5.pdf
    """

    template_pdf = None            # template HTML que se convierte en PDF (obligatorio)
    nombre_archivo = "comprobante" # el pk se agrega al final
    descargar = False              # False = se abre en el navegador; True = se descarga

    def get_nombre_archivo(self):
        # self.object es el registro que buscó el DetailView (por el <pk> de la URL)
        return f"{self.nombre_archivo}-{self.object.pk}"

    def render_to_response(self, context, **response_kwargs):
        # DetailView normalmente llama a render_to_response() para dibujar el HTML.
        # Lo sobrescribimos: en vez de HTML devolvemos el PDF.
        if not self.template_pdf:
            raise ImproperlyConfigured(f"{self.__class__.__name__} debe definir 'template_pdf'.")

        # Datos extra para el pie del comprobante
        context["fecha"] = timezone.localtime()  # fecha y hora de Guayaquil
        context["usuario"] = self.request.user   # quién lo generó

        return render_pdf(
            self.template_pdf,
            context,
            self.get_nombre_archivo(),
            descargar=self.descargar,
        )