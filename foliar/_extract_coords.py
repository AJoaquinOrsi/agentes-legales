import json, base64, anthropic, sys

with open('config.json') as f:
    api_key = json.load(f)['anthropic_api_key']
client = anthropic.Anthropic(api_key=api_key)
with open('TELEGRAMA_BASE.pdf', 'rb') as f:
    data = base64.standard_b64encode(f.read()).decode()

prompt = """El PDF mide 595x842 pt (A4). Origen del coordenadas (0,0) es la esquina INFERIOR IZQUIERDA, eje Y crece hacia arriba.

Por cada campo del formulario (los lugares donde se debe escribir el valor), dame la línea (subrayado) sobre la cual debe sentarse el texto. Es decir, la baseline donde apoyar el texto de un valor con fuente 10pt.

Quiero un objeto Python con esta estructura, con valores precisos según lo que ves en la página:

LAYOUT = {
    "dest_razon":     (x, y_baseline, ancho_max),
    "dest_ramo":      (...),
    "dest_domicilio": (...),
    "dest_cp":        (...),
    "dest_localidad": (...),
    "dest_provincia": (...),
    "rem_nombre":     (...),
    "rem_dni":        (...),
    "rem_fecha":      (...),
    "rem_domicilio":  (...),
    "rem_cp":         (...),
    "rem_localidad":  (...),
    "rem_provincia":  (...),
    "body_top":       (x, y_inicial, ancho_max),
    "body_y_min":     y_minima,
}

Importante: el valor debe sentarse JUSTO ENCIMA del subrayado de cada campo, no superponerse con la línea ni con el label que está abajo del subrayado. Devolveme SOLO el código Python sin explicación.
"""

msg = client.messages.create(
    model='claude-sonnet-4-6', max_tokens=3000,
    messages=[{'role': 'user', 'content': [
        {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': data}},
        {'type': 'text', 'text': prompt},
    ]}],
)
print(''.join(b.text for b in msg.content if hasattr(b, 'text')))
