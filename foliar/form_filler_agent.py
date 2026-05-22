"""
Agente de relleno automático de formulario - Anexo I Incapacidad
Uso: python form_filler_agent.py <documento_fuente.pdf> [--output salida.pdf]
"""

import sys
import json
import argparse
from pathlib import Path
import anthropic
import pdfplumber
from pypdf import PdfReader, PdfWriter

SKILLS_PDF_DIR = (
    r"C:\Users\alexi\AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin"
    r"\4a637714-0c3f-4c29-9574-7f58051f174f\6610e005-091e-4389-8dad-ca89c41ea678\skills\pdf"
)
FORM_PDF = r"C:\Users\alexi\OneDrive\Desktop\anexo_i_-_incapacidad.pdf"
FIELD_INFO_JSON = r"C:\Users\alexi\OneDrive\Desktop\field_info.json"

FORM_FIELDS_DESCRIPTION = """
Campos del formulario "Anexo I - Incapacidad" (Argentina - ART):

PÁGINA 1 - Datos del trabajador y empleador:
- CUIL: CUIL del trabajador (formato: XX-XXXXXXXX-X)
- CUIT / Domicilio electrónico: Email o CUIT del médico/profesional presentante
- Matrícula - Jurisdicción: Número de matrícula y jurisdicción del médico
- NombreRazón Social: Nombre o razón social del EMPLEADOR
- CUIT: CUIT del empleador
- Establecimiento del lugar de efectiva prestación de servicios o donde habitualmente reporta: Nombre del establecimiento de trabajo
- Localidad: Localidad del establecimiento
- Provincia: Provincia del establecimiento
- DenominaciónRazón Social: Denominación/Razón social de la empresa (ART o empleador secundario)
- CUIT En caso de empleadores: CUIT de la empresa/ART
- undefined (checkbox pág1 pos1): Marcar si el tipo de contingencia es "Accidente de trabajo"
- undefined_2 (checkbox pág1 pos2): Marcar si el tipo de contingencia es "Accidente in itinere"
- undefined_3 (checkbox pág1 pos3): Marcar si el tipo de contingencia es "Enfermedad profesional"
- Fecha de la denuncia_af_date: Fecha de la denuncia (formato DD/MM/YYYY)
- Fecha de baja laboral_af_date: Fecha de la baja laboral (formato DD/MM/YYYY)
- Fecha de ocurrencia o diagnóstico_af_date: Fecha del accidente o diagnóstico (formato DD/MM/YYYY)
- Detalle accidente o enfermedad profesional: Descripción detallada del accidente o enfermedad

PÁGINA 2 - Diagnósticos y antecedentes:
- Detallá la o las afecciones o diagnósticos derivados de la contingencia: Lista de diagnósticos/lesiones
- Sí (checkbox): ¿Tiene tratamiento médico en curso? SÍ
- No (checkbox): ¿Tiene tratamiento médico en curso? NO
- Sí_2 (checkbox): ¿Fue dado de alta? SÍ
- No_2 (checkbox): ¿Fue dado de alta? NO
- Sí_3 (checkbox): ¿Tiene incapacidad laboral temporaria? SÍ
- No_3 (checkbox): ¿Tiene incapacidad laboral temporaria? NO
- Sí_4 (checkbox): ¿Tiene incapacidad laboral permanente? SÍ
- No_4 (checkbox): ¿Tiene incapacidad laboral permanente? NO
- Las partes deberán ofrecer...: Detalle de la prueba ofrecida (documentación médica, estudios, etc.)
- Sí_5 (checkbox): ¿Hay prueba pericial médica? SÍ
- No_5 (checkbox): ¿Hay prueba pericial médica? NO
- undefined_4 (checkbox pág2): Tipo de contingencia - Accidente de trabajo
- undefined_5 (checkbox pág2): Tipo de contingencia - Accidente in itinere
- Enfermedad Profesional_2 (checkbox): Tipo de contingencia - Enfermedad profesional
- Porcentaje de incapacidad: Porcentaje de incapacidad (ej: "15%")
- Región del cuerpo afectada: Parte del cuerpo afectada (ej: "Columna lumbar", "Miembro superior derecho")
- Detalle prueba judicial: Detalle de la prueba a ofrecer en juicio

PÁGINA 3 - Datos procesales y firmas:
- Nº: Número de expediente judicial (si existe)
- Jurisdicción: Jurisdicción del expediente
- undefined_6 (checkbox pág3): Domicilio del trabajador
- Domicilio de efectiva prestación de servicios (checkbox): Seleccionar si notificar en este domicilio
- Domicilio donde habitualmente reporta (checkbox): Seleccionar si notificar en este domicilio
- Firma Trabajador: Nombre del trabajador (campo firma)
- Aclaración: Aclaración del nombre del trabajador
- Firma Letrado Patrocinante: Nombre del abogado patrocinante
- Aclaración_2: Aclaración del nombre del abogado
- Fecha_af_date: Fecha del formulario (formato DD/MM/YYYY)
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrae texto de un PDF usando pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- PÁGINA {i+1} ---\n{page_text}"
    return text.strip()


def extract_fields_with_claude(source_text: str, api_key: str | None = None) -> dict:
    """Usa Claude para extraer y mapear información del documento fuente."""
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    prompt = f"""Eres un asistente especializado en completar formularios legales argentinos de ART (Aseguradoras de Riesgos del Trabajo).

A continuación te proporciono:
1. La descripción de los campos del formulario "Anexo I - Incapacidad"
2. El texto extraído del documento fuente con la información del caso

Tu tarea es analizar el documento fuente y extraer los valores correspondientes para cada campo del formulario.

DESCRIPCIÓN DE CAMPOS DEL FORMULARIO:
{FORM_FIELDS_DESCRIPTION}

DOCUMENTO FUENTE (información del caso):
{source_text}

Devuelve un JSON con exactamente este formato (solo el JSON, sin explicaciones adicionales):
{{
  "CUIL": "valor o null",
  "CUIT / Domicilio electrónico": "valor o null",
  "Matrícula - Jurisdicción": "valor o null",
  "NombreRazón Social": "valor o null",
  "CUIT": "valor o null",
  "Establecimiento del lugar de efectiva prestación de servicios o donde habitualmente reporta": "valor o null",
  "Localidad": "valor o null",
  "Provincia": "valor o null",
  "DenominaciónRazón Social": "valor o null",
  "CUIT En caso de empleadores": "valor o null",
  "tipo_contingencia": "accidente_trabajo|accidente_in_itinere|enfermedad_profesional|null",
  "Fecha de la denuncia_af_date": "DD/MM/YYYY o null",
  "Fecha de baja laboral_af_date": "DD/MM/YYYY o null",
  "Fecha de ocurrencia o diagnóstico_af_date": "DD/MM/YYYY o null",
  "Detalle accidente o enfermedad profesional": "valor o null",
  "Detallá la o las afecciones o diagnósticos derivados de la contingencia": "valor o null",
  "tratamiento_en_curso": true|false|null,
  "dado_de_alta": true|false|null,
  "incapacidad_temporaria": true|false|null,
  "incapacidad_permanente": true|false|null,
  "Las partes deberán ofrecer en su primera presentación toda la prueba de la que intenten valerse acompa\\u00f1ando en": "valor o null",
  "prueba_pericial_medica": true|false|null,
  "Porcentaje de incapacidad": "valor o null",
  "Región del cuerpo afectada": "valor o null",
  "Detalle prueba judicial": "valor o null",
  "Nº": "valor o null",
  "Jurisdicción": "valor o null",
  "domicilio_notificacion": "trabajador|prestacion_servicios|habitualmente_reporta|null",
  "Firma Trabajador": "valor o null",
  "Aclaración": "valor o null",
  "Firma Letrado Patrocinante": "valor o null",
  "Aclaración_2": "valor o null",
  "Fecha_af_date": "DD/MM/YYYY o null"
}}

Si un dato no está disponible en el documento fuente, usa null. No inventes información.
"""

    print("Analizando documento con Claude...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    # Extraer JSON de la respuesta
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()

    return json.loads(response_text)


def build_field_values(extracted: dict, field_info: list) -> list:
    """Construye la lista de field_values para el script de relleno."""
    field_values = []

    # Mapa de campo del formulario a valor extraído
    direct_map = {
        "CUIL": extracted.get("CUIL"),
        "CUIT / Domicilio electrónico": extracted.get("CUIT / Domicilio electrónico"),
        "Matrícula - Jurisdicción": extracted.get("Matrícula - Jurisdicción"),
        "NombreRazón Social": extracted.get("NombreRazón Social"),
        "CUIT": extracted.get("CUIT"),
        "Establecimiento del lugar de efectiva prestación de servicios o donde habitualmente reporta": extracted.get(
            "Establecimiento del lugar de efectiva prestación de servicios o donde habitualmente reporta"
        ),
        "Localidad": extracted.get("Localidad"),
        "Provincia": extracted.get("Provincia"),
        "DenominaciónRazón Social": extracted.get("DenominaciónRazón Social"),
        "CUIT En caso de empleadores": extracted.get("CUIT En caso de empleadores"),
        "Fecha de la denuncia_af_date": extracted.get("Fecha de la denuncia_af_date"),
        "Fecha de baja laboral_af_date": extracted.get("Fecha de baja laboral_af_date"),
        "Fecha de ocurrencia o diagnóstico_af_date": extracted.get(
            "Fecha de ocurrencia o diagnóstico_af_date"
        ),
        "Detalle accidente o enfermedad profesional": extracted.get(
            "Detalle accidente o enfermedad profesional"
        ),
        "Detallá la o las afecciones o diagnósticos derivados de la contingencia": extracted.get(
            "Detallá la o las afecciones o diagnósticos derivados de la contingencia"
        ),
        "Las partes deberán ofrecer en su primera presentación toda la prueba de la que intenten valerse acompa\u00f1ando en": extracted.get(
            "Las partes deberán ofrecer en su primera presentación toda la prueba de la que intenten valerse acompa\u00f1ando en"
        ),
        "Porcentaje de incapacidad": extracted.get("Porcentaje de incapacidad"),
        "Región del cuerpo afectada": extracted.get("Región del cuerpo afectada"),
        "Detalle prueba judicial": extracted.get("Detalle prueba judicial"),
        "Nº": extracted.get("Nº"),
        "Jurisdicción": extracted.get("Jurisdicción"),
        "Firma Trabajador": extracted.get("Firma Trabajador"),
        "Aclaración": extracted.get("Aclaración"),
        "Firma Letrado Patrocinante": extracted.get("Firma Letrado Patrocinante"),
        "Aclaración_2": extracted.get("Aclaración_2"),
        "Fecha_af_date": extracted.get("Fecha_af_date"),
    }

    # Tipo de contingencia (checkboxes pág 1)
    tipo = extracted.get("tipo_contingencia")
    checkbox_tipo_p1 = {
        "undefined": tipo == "accidente_trabajo",
        "undefined_2": tipo == "accidente_in_itinere",
        "undefined_3": tipo == "enfermedad_profesional",
    }

    # Sí/No checkboxes pág 2
    si_no_map = {
        "Sí": extracted.get("tratamiento_en_curso"),
        "No": (
            False if extracted.get("tratamiento_en_curso") is True
            else (True if extracted.get("tratamiento_en_curso") is False else None)
        ),
        "Sí_2": extracted.get("dado_de_alta"),
        "No_2": (
            False if extracted.get("dado_de_alta") is True
            else (True if extracted.get("dado_de_alta") is False else None)
        ),
        "Sí_3": extracted.get("incapacidad_temporaria"),
        "No_3": (
            False if extracted.get("incapacidad_temporaria") is True
            else (True if extracted.get("incapacidad_temporaria") is False else None)
        ),
        "Sí_4": extracted.get("incapacidad_permanente"),
        "No_4": (
            False if extracted.get("incapacidad_permanente") is True
            else (True if extracted.get("incapacidad_permanente") is False else None)
        ),
        "Sí_5": extracted.get("prueba_pericial_medica"),
        "No_5": (
            False if extracted.get("prueba_pericial_medica") is True
            else (True if extracted.get("prueba_pericial_medica") is False else None)
        ),
    }

    # Tipo contingencia pág 2
    checkbox_tipo_p2 = {
        "undefined_4": tipo == "accidente_trabajo",
        "undefined_5": tipo == "accidente_in_itinere",
        "Enfermedad Profesional_2": tipo == "enfermedad_profesional",
    }

    # Domicilio notificación pág 3
    dom = extracted.get("domicilio_notificacion")
    checkbox_dom = {
        "undefined_6": dom == "trabajador",
        "Domicilio de efectiva prestación de servicios": dom == "prestacion_servicios",
        "Domicilio donde habitualmente reporta": dom == "habitualmente_reporta",
    }

    # Construir lista
    for field in field_info:
        fid = field["field_id"]
        ftype = field["type"]
        page = field["page"]
        value = None

        if ftype == "text" and fid in direct_map and direct_map[fid] is not None:
            value = str(direct_map[fid])
            field_values.append({
                "field_id": fid,
                "description": fid,
                "page": page,
                "value": value,
            })

        elif ftype == "checkbox":
            checked = None
            if fid in checkbox_tipo_p1:
                checked = checkbox_tipo_p1[fid]
            elif fid in si_no_map:
                checked = si_no_map[fid]
            elif fid in checkbox_tipo_p2:
                checked = checkbox_tipo_p2[fid]
            elif fid in checkbox_dom:
                checked = checkbox_dom[fid]

            if checked is not None:
                val = field["checked_value"] if checked else field["unchecked_value"]
                field_values.append({
                    "field_id": fid,
                    "description": fid,
                    "page": page,
                    "value": val,
                })

    return field_values


def fill_form(field_values: list, output_pdf: str):
    """Rellena el formulario PDF con los valores extraídos."""
    reader = PdfReader(FORM_PDF)

    fields_by_page: dict[int, dict] = {}
    for fv in field_values:
        page = fv["page"]
        fields_by_page.setdefault(page, {})[fv["field_id"]] = fv["value"]

    writer = PdfWriter(clone_from=reader)
    for page_num, vals in fields_by_page.items():
        writer.update_page_form_field_values(
            writer.pages[page_num - 1], vals, auto_regenerate=False
        )

    writer.set_need_appearances_writer(True)

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"\nFormulario rellenado guardado en: {output_pdf}")


def main():
    parser = argparse.ArgumentParser(
        description="Agente que rellena el Anexo I de Incapacidad a partir de un documento PDF fuente."
    )
    parser.add_argument("source_pdf", help="PDF fuente con la información del caso")
    parser.add_argument(
        "--output",
        default=r"C:\Users\alexi\OneDrive\Desktop\anexo_i_rellenado.pdf",
        help="Ruta del PDF de salida rellenado",
    )
    parser.add_argument("--api-key", help="Clave API de Anthropic (opcional si está en env ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    source_path = args.source_pdf
    if not Path(source_path).exists():
        print(f"ERROR: No se encontró el archivo: {source_path}")
        sys.exit(1)

    # 1. Extraer texto del documento fuente
    print(f"Extrayendo texto de: {source_path}")
    source_text = extract_text_from_pdf(source_path)
    if not source_text:
        print("ADVERTENCIA: No se pudo extraer texto del PDF. El documento puede ser escaneado.")
        print("Por favor asegurate de que el PDF tenga texto seleccionable.")
        sys.exit(1)

    print(f"Texto extraído: {len(source_text)} caracteres")

    # 2. Usar Claude para extraer los datos
    extracted = extract_fields_with_claude(source_text, args.api_key)
    print("\nDatos extraídos por Claude:")
    for k, v in extracted.items():
        if v is not None:
            print(f"  {k}: {v}")

    # 3. Cargar field_info
    with open(FIELD_INFO_JSON, encoding="utf-8") as f:
        field_info = json.load(f)

    # 4. Construir field_values
    field_values = build_field_values(extracted, field_info)
    print(f"\nCampos a rellenar: {len(field_values)}")

    # Guardar field_values para auditoría
    fv_path = str(Path(args.output).parent / "field_values_generados.json")
    with open(fv_path, "w", encoding="utf-8") as f:
        json.dump(field_values, f, ensure_ascii=False, indent=2)
    print(f"Valores guardados en: {fv_path}")

    # 5. Rellenar el formulario
    fill_form(field_values, args.output)


if __name__ == "__main__":
    main()
