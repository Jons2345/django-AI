# Bitácora de prompts · Sistema Académico

> **BORRADOR.** Revísalo y complétalo con tus propias palabras antes de entregar:
> en la defensa te preguntarán por estos errores y cómo los resolviste.

| # | Prompt (guía) | Qué pedí | ¿Funcionó a la primera? | Qué falló | Cómo lo corregí |
|---|---|---|---|---|---|
| 0 | Prompt 0 · Contexto | Se le dio a la ia las intrucciones de lo que debe hacer
| 1 | Prompt 1 · Modelos | Se creo en `core/models.py` y los 11 modelos de `academico`, ademas se comparo los models de la guia y de la ia 
| 2 | Prompt 2 · Admin y datos | Se creo `BaseAdmin`, los 11 admins y el comando `poblar_datos`, ademas no sabía por dónde crear `management/commands/`. Se crearon las carpetas dentro de `academico` con sus `__init__.py` vacíos |
| 3 | Prompt 3 · Base del proyecto | Se configuraron el settings, login/logout, inicio, `base.html` | Tuve problemas porque salia el `TemplateDoesNotExist: base.html` y se creo el `registration/login.html` | La carpeta `templates/` estaba dentro de `sistema_academico/sistema_academico/`; la moví junto a `manage.py` |
| 3b | Corrección | Abrí `http://127.0.0.1:8000/` con python manage.py runserver y salio este mensaje, Página 404: la raíz no tenía ruta | Agregué `RedirectView` en `sistema_academico/urls.py` hacia `academico:inicio` |
| 3c | Corrección | VS Code subrayaba `from django...` | No | Pylance: "La importación no se ha podido resolver" | Activé el `venv`, instalé las librerías y elegí el intérprete `venv\Scripts\python.exe` |
| 4 | Prompt 4 · CRUD básico Estudiante | Se creo un Form con `clean_cedula`, crear, editar, ver y eliminar, faltaba todo el CRUD; solo tenía la lista | Lo hice después de revisar el proyecto con la guía |
| 5 | Prompt 5 · Filtros + columnas | se crearon el `valor_campo`, `FiltroCamposMixin`, `_filtros.html` | se probo `?campos=user__password` y se ignora |
| 6 | Prompt 6 · Excel | `exportar_excel`, `ExportarMixin` | No | `La importación "openpyxl" no se ha podido resolver` | `pip install openpyxl xhtml2pdf` con el venv activo |
| 7 | Prompt 7 · Listado PDF | `render_pdf`, `link_callback`, `pdf/listado.html` | No | El pie del panel quedó **duplicado** (una copia fuera del `<form>`) | Dejé un solo `card-footer` con Excel, PDF, Limpiar y Filtrar dentro del form |
| 8 | Prompt 8 · Ficha PDF | `ComprobantePdfMixin`, `EstudiantePdfView` | Parcial | El botón "Ficha PDF" no estaba en la lista ni en el detalle | Agregué la columna Acciones y el botón en `estudiante_detalle.html` |
| 9 | Prompt 9 · Matrícula + Nota | `MatriculaNotaMixin`, `inlineformset_factory` | Sí | — | Probé carrera incorrecta, cupo lleno y nota 150 |
| 10 | Prompt 10 · Filtros en Matrículas | `FiltroMatriculaForm` | Sí | — | `Decimal("0")` es falso: usé `is not None` en promedio_desde |
| 11 | Prompt 11 · Comprobante de matrícula | `MatriculaPdfView` | Sí | — | — |
| M | Corrección de modelos | `makemigrations --check` | No | Mi `models.py` era una versión vieja y NO coincidía con mi migración `0001_initial.py` (hecha con los modelos de referencia) | Volví a poner `core/models.py` y `academico/models.py` de la guía (2.4) y ajusté el admin y 3 templates que usaban `profesor.nombre_completo` |
| R | Prompt «Revisar mi código» | Revisión de `views.py` como el profesor | — | Faltaban comentarios, espacios sobrantes, logo sin imagen, el enlace Estudiantes comentado y un `</ul>` sin cerrar en `base.html` | Apliqué cada cambio señalado |

