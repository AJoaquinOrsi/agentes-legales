"""Crea un PDF de prueba con datos de un caso de incapacidad laboral."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

output = r"C:\Users\alexi\OneDrive\Desktop\form_agent\caso_prueba.pdf"
c = canvas.Canvas(output, pagesize=A4)
w, h = A4

lines = [
    "INFORME MÉDICO LABORAL - CASO DE INCAPACIDAD",
    "",
    "Datos del Trabajador:",
    "Nombre completo: Juan Carlos García López",
    "CUIL: 20-28456789-3",
    "Fecha de nacimiento: 15/03/1978",
    "",
    "Datos del Empleador:",
    "Razón Social empleador: Metalúrgica Del Sur S.A.",
    "CUIT empleador: 30-71234567-8",
    "Establecimiento: Planta Industrial Norte",
    "Localidad: Quilmes",
    "Provincia: Buenos Aires",
    "",
    "ART (Aseguradora):",
    "Denominación ART: Consolidar ART S.A.",
    "CUIT ART: 30-68432591-4",
    "",
    "Datos del Profesional Médico:",
    "Dr. Roberto Sánchez",
    "Matrícula: 45832 - CABA",
    "CUIT/Email profesional: 20-15678234-7",
    "",
    "Datos del Siniestro:",
    "Tipo de contingencia: Accidente de trabajo",
    "Fecha del accidente: 12/08/2024",
    "Fecha de la denuncia: 13/08/2024",
    "Fecha de baja laboral: 12/08/2024",
    "",
    "Descripción del accidente:",
    "El trabajador sufrió una caída desde una plataforma de trabajo a 2 metros de",
    "altura mientras realizaba tareas de mantenimiento de maquinaria. Impacto directo",
    "sobre el hombro derecho y columna lumbar.",
    "",
    "Diagnósticos:",
    "1. Fractura de clavícula derecha (cerrada, no desplazada)",
    "2. Hernia de disco L4-L5 post-traumática",
    "3. Contractura muscular lumbar",
    "",
    "Estado actual:",
    "- Tratamiento médico en curso: SÍ",
    "- Alta médica: NO",
    "- Incapacidad laboral temporaria: SÍ",
    "- Incapacidad laboral permanente: SÍ",
    "",
    "Porcentaje de incapacidad: 35%",
    "Región del cuerpo afectada: Hombro derecho y columna lumbar",
    "",
    "Prueba ofrecida:",
    "Se ofrecen como prueba: historia clínica del Hospital Quilmes, radiografías",
    "digitales, RMN de columna lumbar, informes de traumatólogo y neurocirujano.",
    "Se solicita pericia médica judicial.",
    "",
    "Prueba pericial médica: SÍ",
    "",
    "Datos procesales:",
    "Expediente Nº: 45892/2024",
    "Jurisdicción: Quilmes",
    "Domicilio de notificación: Domicilio del trabajador",
    "",
    "Trabajador: Juan Carlos García López",
    "Letrado patrocinante: Dr. Martín Eduardo Flores",
    "",
    "Fecha: 21/04/2026",
]

y = h - 2 * cm
c.setFont("Helvetica-Bold", 14)
c.drawString(2 * cm, y, lines[0])
y -= 0.7 * cm
c.setFont("Helvetica", 10)
for line in lines[1:]:
    if y < 2 * cm:
        c.showPage()
        y = h - 2 * cm
        c.setFont("Helvetica", 10)
    if line.startswith("Datos") or line.startswith("ART") or line.startswith("Diagnóstico") or line.startswith("Estado") or line.startswith("Prueba"):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, line)
        c.setFont("Helvetica", 10)
    else:
        c.drawString(2 * cm, y, line)
    y -= 0.5 * cm

c.save()
print(f"Documento de prueba creado: {output}")
