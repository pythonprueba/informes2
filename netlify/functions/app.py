# -*- coding: utf-8 -*-
from flask import Flask, request, send_file
import datetime
import io
from pathlib import Path
from docxtpl import DocxTemplate
import serverless_wsgi

# --- Configuración para Netlify ---
# La función se ejecuta desde un directorio base.
# Los 'included_files' se colocan en el mismo directorio que este script.
base_path = Path(__file__).parent
plantilla_path = base_path / "plantilla_informe.docx"

# El nombre de la app de Flask y el template_folder ya no son necesarios
# porque Netlify servirá el HTML directamente.
app = Flask(__name__)

def generar_informe_docx(context):
    """
    Genera un informe .docx en memoria a partir de la plantilla y un diccionario de contexto.
    """
    try:
        doc = DocxTemplate(plantilla_path)
        hoy = datetime.date.today()
        context['fecha_actual'] = hoy.strftime("%d-%m-%Y")
        context['fecha_examen'] = hoy.strftime("%d-%m-%Y")

        try:
            fecnac_str = context.get('fecha_nacimiento', '')
            if fecnac_str:
                fecha_nacimiento = datetime.datetime.strptime(fecnac_str, "%Y-%m-%d").date()
                edad_delta = hoy - fecha_nacimiento
                edad = edad_delta.days // 365
                context['edad'] = edad
                context['fecha_nacimiento'] = fecha_nacimiento.strftime("%d-%m-%Y")
            else:
                context['edad'] = "N/A"
                context['fecha_nacimiento'] = "N/A"
        except (ValueError, AttributeError):
            context['edad'] = "N/A"
            context['fecha_nacimiento'] = "N/A"

        doc.render(context)
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream
    except Exception as e:
        print(f"ERROR al generar el DOCX: {e}")
        return None

# La única ruta que necesita nuestra función es /generar
@app.route('/generar', methods=['POST'])
def generar():
    """
    Recibe los datos del formulario, genera el informe
    y lo devuelve como un archivo para descargar.
    """
    try:
        context = {
            "centro_medico": request.form.get('centro_medico', 'Centro Médico por Defecto'),
            "nombre": request.form.get('nombre', 'Sin Nombre'),
            "run": request.form.get('run', 'Sin RUN'),
            "fecha_nacimiento": request.form.get('fecnac', ''),
            "TIPO_EXAMEN": request.form.get('tipo_examen', 'Examen no especificado'),
            "antecedentes": request.form.get('antecedentes', 'No se informan.'),
            "hallazgos": request.form.get('hallazgos', 'Dentro de límites normales.'),
            "conclusion": request.form.get('conclusion', 'Sin hallazgos patológicos.')
        }

        file_stream = generar_informe_docx(context)

        if file_stream:
            fecha_hoy = datetime.date.today().strftime("%d-%m-%Y")
            nombre_archivo = f"Informe_{context['nombre'].replace(' ', '_')}_{fecha_hoy}.docx"
            return send_file(
                file_stream,
                as_attachment=True,
                download_name=nombre_archivo,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        return "Error interno al generar el documento.", 500
    except Exception as e:
        print(f"ERROR en la ruta /generar: {e}")
        return "Ocurrió un error inesperado en el servidor.", 500

# Adaptador para Netlify
def handler(event, context):
    return serverless_wsgi.handle(app, event, context)

