# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, send_file
import datetime
import io
import os
from pathlib import Path
from docxtpl import DocxTemplate
from netlify_wsgi import make_handler

# --- Configuración para Netlify ---
# Usamos pathlib para construir rutas relativas al script actual,
# lo que asegura que funcione correctamente en el entorno de Netlify.
base_path = Path(__file__).parent.parent.parent # Sube tres niveles desde /netlify/functions/app.py a la raíz
template_dir = base_path / 'templates'
plantilla_path = base_path / "plantilla_informe.docx"

app = Flask(__name__, template_folder=str(template_dir))

def generar_informe_docx(context):
    """
    Genera un informe .docx en memoria a partir de la plantilla y un diccionario de contexto.
    """
    try:
        # Carga la plantilla de Word
        doc = DocxTemplate(plantilla_path)

        # --- Lógica de Fechas y Edad ---
        hoy = datetime.date.today()
        context['fecha_actual'] = hoy.strftime("%d-%m-%Y")
        
        # Asigna la fecha del examen (puede ser la actual u otra)
        context['fecha_examen'] = hoy.strftime("%d-%m-%Y")

        # Calcula la edad a partir de la fecha de nacimiento
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

        # Renderiza el contexto en la plantilla
        doc.render(context)
        
        # Guarda el documento en un stream de bytes en memoria
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream
        
    except Exception as e:
        # Imprime cualquier error en los logs de Netlify para facilitar la depuración
        print(f"ERROR al generar el DOCX: {e}")
        return None

@app.route('/', methods=['GET'])
def form():
    """
    Muestra el formulario HTML principal.
    """
    return render_template('index.html')

@app.route('/generar', methods=['POST'])
def generar():
    """
    Recibe los datos del formulario, genera el informe
    y lo devuelve como un archivo para descargar.
    """
    try:
        # Construye el diccionario de contexto con los datos del formulario
        context = {
            "centro_medico": request.form.get('centro_medico', 'Centro Médico por Defecto'),
            "nombre": request.form.get('nombre', 'Sin Nombre'),
            "run": request.form.get('run', 'Sin RUN'),
            "fecha_nacimiento": request.form.get('fecnac', ''), # Formato YYYY-MM-DD del input type="date"
            "TIPO_EXAMEN": request.form.get('tipo_examen', 'Examen no especificado'),
            "antecedentes": request.form.get('antecedentes', 'No se informan.'),
            "hallazgos": request.form.get('hallazgos', 'Dentro de límites normales.'),
            "conclusion": request.form.get('conclusion', 'Sin hallazgos patológicos.')
        }

        # Genera el documento en memoria
        file_stream = generar_informe_docx(context)

        if file_stream:
            # Crea un nombre de archivo descriptivo
            fecha_hoy = datetime.date.today().strftime("%d-%m-%Y")
            nombre_archivo = f"Informe_{context['nombre'].replace(' ', '_')}_{fecha_hoy}.docx"

            # Envía el archivo generado al navegador del usuario
            return send_file(
                file_stream,
                as_attachment=True,
                download_name=nombre_archivo,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        
        # Si la generación del archivo falla
        return "Error interno al generar el documento.", 500

    except Exception as e:
        print(f"ERROR en la ruta /generar: {e}")
        return "Ocurrió un error inesperado en el servidor.", 500

# --- Adaptador para Netlify ---
# Netlify busca un objeto 'handler' para ejecutar la función.
handler = make_handler(app)