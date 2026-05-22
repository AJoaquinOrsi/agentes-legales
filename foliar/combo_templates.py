"""
Plantillas y catálogos para la generación combo (telegrama + escrito).

Basado en las guías del Estudio Jurídico Arrechea:
- GUIA TELEGRAMA IA.pdf
- GUIA ESCRITO IA.pdf
- Ejemplos: JUAREZ HERRERA AMP, ESCRITO BRAVO, MODELO AMPLIACION

Filosofía:
1. La IA solo extrae variables (nombres, fechas, lesiones, relato)
2. El backend compone el documento final con plantillas fijas verificadas
"""

from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CATÁLOGO DE ARTs — de la guía oficial
# ═══════════════════════════════════════════════════════════════════════════════

ART_CATALOG = {
    "PROVINCIA":         {"razon": "Provincia Aseguradora de Riesgos del Trabajo S.A.",   "domicilio": "PELLEGRINI CARLOS 0091 05°P",       "cp": "1009",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "EXPERTA":           {"razon": "Experta Aseguradora de Riesgos del Trabajo S.A.",     "domicilio": "AV. DEL LIBERTADOR 6902 12°P",      "cp": "1429",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "SWISS MEDICAL":     {"razon": "Swiss Medical Aseguradora de Riesgos del Trabajo S.A.U.", "domicilio": "CORRIENTES 1865 PB",            "cp": "1045",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "MAPFRE":            {"razon": "Mapfre Argentina Aseguradora de Riesgos del Trabajo S.A.","domicilio": "ELVIRA RAWSON DE DELLEPIA 150 1°P","cp": "1107",  "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "ASOCIART":          {"razon": "Asociart S.A. Aseguradora de Riesgos del Trabajo",     "domicilio": "ALEM LEANDRO N. AV. 621",           "cp": "1001",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "LIDERAR":           {"razon": "Liderar Aseguradora de Riesgos del Trabajo S.A.",      "domicilio": "RECONQUISTA 0585 7°P",              "cp": "1003",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "RECONQUISTA":       {"razon": "Reconquista Aseguradora de Riesgos del Trabajo S.A.",  "domicilio": "PELLEGRINI CARLOS 1069 04°P",       "cp": "1009",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "SMG":               {"razon": "SMG Aseguradora de Riesgos del Trabajo S.A.",          "domicilio": "CORRIENTES AV. 1891 5°P",           "cp": "1045",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "PREVENCION":        {"razon": "Prevención Aseguradora de Riesgos del Trabajo S.A.",   "domicilio": "RUTA NAC 34 KM 257",                "cp": "2322",     "localidad": "SUNCHALES",       "provincia": "SANTA FE"},
    "BERKLEY":           {"razon": "Berkley International Aseguradora de Riesgos del Trabajo S.A.","domicilio":"PELLEGRINI CARLOS 1023 3°P",  "cp": "1009",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "CAMINOS":           {"razon": "Caminos Protegidos Aseguradora de Riesgos del Trabajo S.A.U.","domicilio":"ARCOS 3631",                  "cp": "1429",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "SERENA":            {"razon": "Serena Aseguradora de Riesgos del Trabajo S.A.U.",     "domicilio": "ALEM LEANDRO N. 1050 6°P",          "cp": "C1011AAA", "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "QBE":               {"razon": "QBE Aseguradora de Riesgos del Trabajo S.A.",          "domicilio": "VERA 0565",                          "cp": "1414",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "SOLART":            {"razon": "Solart Aseguradora de Riesgos del Trabajo S.A.",       "domicilio": "BOUCHARD AV. 0547 20°P",             "cp": "1106",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "SUL AMERICA":       {"razon": "Sul America Aseguradora de Riesgos del Trabajo S.A.",  "domicilio": "SAENZ PEÑA 0530",                    "cp": "1035",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "INCA":              {"razon": "Inca Aseguradora de Riesgos del Trabajo S.A.",         "domicilio": "BELGRANO AV. 0680 04°P",             "cp": "1092",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "LA SEGUNDA":        {"razon": "La Segunda Aseguradora de Riesgos del Trabajo S.A.",   "domicilio": "JUAN MANUEL DE ROSAS 0957",          "cp": "2000",     "localidad": "ROSARIO",         "provincia": "SANTA FE"},
    "RESPONSABILIDAD":   {"razon": "Responsabilidad Patronal Aseguradora de Riesgos del Trabajo S.A.","domicilio": "ROCA JULIO A. 0721",      "cp": "1067",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "INTERACCION":       {"razon": "ART Interacción S.A.",                                  "domicilio": "SARMIENTO 2038",                     "cp": "1044",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "FEDERACION":        {"razon": "Federación Patronal Seguros S.A.U.",                    "domicilio": "Av. 51 770",                         "cp": "B1900AWP", "localidad": "LA PLATA",        "provincia": "BUENOS AIRES"},
    "ANDINA":            {"razon": "Andina Aseguradora de Riesgos del Trabajo S.A.",       "domicilio": "Necochea 183",                       "cp": "5500",     "localidad": "MENDOZA",         "provincia": "MENDOZA"},
    "PARANA":            {"razon": "Paraná Aseguradora de Riesgos del Trabajo S.A.",       "domicilio": "Peron 715",                          "cp": "1038",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
    "LUZ":               {"razon": "Luz Aseguradora de Riesgos del Trabajo S.A.",          "domicilio": "LIMA 1029",                          "cp": "1073",     "localidad": "CAPITAL FEDERAL", "provincia": "C.A.B.A."},
}

REMITENTE_FIJO = {
    "domicilio": "Lavalle 1675 Piso 7 of 8",
    "cp":        "1048",
    "localidad": "Capital Federal",
    "provincia": "C.A.B.A.",
}

LETRADO = {
    "nombre":    "ARRECHEA LEANDRO",
    "matricula": "T° 129 F° 33 / CASI T° LII F° 52",
}

# ═══════════════════════════════════════════════════════════════════════════════
# Lookup de ARTs
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize(s: str) -> str:
    """Saca acentos y pasa a mayúsculas para matching robusto."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s or "")
        if unicodedata.category(c) != "Mn"
    ).upper()


def lookup_art(nombre_libre: str) -> dict:
    """Busca una ART por coincidencia parcial en el catálogo. Devuelve dict con
    razon/domicilio/cp/localidad/provincia. Si no encuentra, devuelve datos
    genéricos con la razón social tal como vino."""
    if not nombre_libre:
        return _art_unknown("ART (sin identificar)")
    norm = _normalize(nombre_libre)
    for key, art in ART_CATALOG.items():
        if _normalize(key) in norm:
            return dict(art)
    return _art_unknown(nombre_libre)


def _art_unknown(nombre: str) -> dict:
    return {
        "razon":     nombre,
        "domicilio": "",
        "cp":        "",
        "localidad": "",
        "provincia": "",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FECHA EN LETRAS
# ═══════════════════════════════════════════════════════════════════════════════

_DIAS = {
    1:  "uno",     2:  "dos",     3:  "tres",      4:  "cuatro",   5:  "cinco",
    6:  "seis",    7:  "siete",   8:  "ocho",      9:  "nueve",   10: "diez",
    11: "once",    12: "doce",    13: "trece",     14: "catorce",  15: "quince",
    16: "dieciséis",17:"diecisiete",18:"dieciocho",19:"diecinueve",20:"veinte",
    21:"veintiuno",22:"veintidós",23:"veintitrés",24:"veinticuatro",25:"veinticinco",
    26:"veintiséis",27:"veintisiete",28:"veintiocho",29:"veintinueve",30:"treinta",
    31:"treinta y uno",
}
_MESES = ["enero","febrero","marzo","abril","mayo","junio",
          "julio","agosto","septiembre","octubre","noviembre","diciembre"]


def fecha_en_letras(fecha_iso: str) -> str:
    """Convierte 'YYYY-MM-DD' o 'DD/MM/YYYY' a 'veintiocho de mayo de dos mil veinticinco'."""
    if not fecha_iso:
        return "(fecha del accidente)"
    try:
        s = fecha_iso.strip()
        if "/" in s:
            dt = datetime.strptime(s[:10], "%d/%m/%Y")
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
    except Exception:
        return fecha_iso
    dia = _DIAS.get(dt.day, str(dt.day))
    mes = _MESES[dt.month - 1]
    anio = _anio_en_letras(dt.year)
    return f"{dia} de {mes} de {anio}"


def _anio_en_letras(n: int) -> str:
    """2025 → 'dos mil veinticinco'."""
    if 2000 <= n < 2100:
        resto = n - 2000
        if resto == 0:
            return "dos mil"
        return f"dos mil {_DIAS.get(resto, str(resto))}"
    return str(n)


# ═══════════════════════════════════════════════════════════════════════════════
# TELEGRAMA — composición
# ═══════════════════════════════════════════════════════════════════════════════

TELEGRAMA_PARRAFO_1 = (
    "Me dirijo a ustedes a fin de ampliar la denuncia oportunamente presentada "
    "con motivo del accidente de trabajo ocurrido el día {fecha_letras}."
)

TELEGRAMA_PARRAFO_3 = (
    "Solicito se tenga por ampliada la denuncia inicial, se reconozcan la "
    "totalidad de las secuelas físicas y se disponga la cobertura médica "
    "integral conforme a la Ley N° 24.557. Esta parte impugna expresamente "
    "los estudios médicos practicados por {art_nombre_corto}, por cuanto no "
    "reflejan la real entidad de las lesiones ni el actual estado de salud "
    "de la trabajadora, solicitando la realización de una nueva evaluación "
    "médica imparcial a fin de garantizar la debida tutela administrativa "
    "(conf. Ley 19.549). Asimismo, solicito la aplicación del baremo "
    "vigente al momento del accidente, conforme art. 7 CCyCN y Ley 24.557. "
    "Sin otro particular, saludo atentamente."
)


def compose_telegrama(vars_: dict) -> dict:
    """Devuelve un dict con todas las secciones del telegrama listas para renderizar.

    vars_ esperado:
      - nombre_trabajador (str)
      - dni (str con o sin puntos)
      - fecha_accidente (YYYY-MM-DD o DD/MM/YYYY)
      - art_nombre (str libre, se busca en catálogo)
      - lesiones_y_estudios (str — párrafo 2 redactado por la IA)
      - fecha_envio (DD/MM/YYYY) — opcional, default hoy
    """
    art = lookup_art(vars_.get("art_nombre", ""))
    fecha_envio = vars_.get("fecha_envio") or datetime.utcnow().strftime("%d/%m/%Y")
    art_corto = (vars_.get("art_nombre") or art.get("razon", "ART")).upper()

    return {
        "destinatario": {
            "razon":     art.get("razon", ""),
            "ramo":      "Aseguradora de Riesgos del Trabajo",
            "domicilio": art.get("domicilio", ""),
            "cp":        art.get("cp", ""),
            "localidad": art.get("localidad", ""),
            "provincia": art.get("provincia", ""),
        },
        "remitente": {
            "nombre":    (vars_.get("nombre_trabajador") or "").upper(),
            "dni":       _formatea_dni(vars_.get("dni", "")),
            "domicilio": REMITENTE_FIJO["domicilio"],
            "cp":        REMITENTE_FIJO["cp"],
            "localidad": REMITENTE_FIJO["localidad"],
            "provincia": REMITENTE_FIJO["provincia"],
            "fecha":     "",
        },
        "cuerpo": [
            TELEGRAMA_PARRAFO_1.format(fecha_letras=fecha_en_letras(vars_.get("fecha_accidente", ""))),
            (vars_.get("lesiones_y_estudios") or "").strip() or
                "Como consecuencia del hecho sufrí lesiones múltiples, dolor crónico, "
                "limitación funcional, afectación psicológica. Asimismo solicito la "
                "realización de los siguientes estudios y tratamientos médicos: "
                "RMN de las zonas afectadas, radiografías, evaluación psicológica.",
            TELEGRAMA_PARRAFO_3.format(art_nombre_corto=art_corto),
        ],
        "tipo_comunicacion": 3,
    }


def _formatea_dni(dni_raw: str) -> str:
    """'17805434' → '17.805.434'."""
    if not dni_raw:
        return ""
    digits = "".join(c for c in dni_raw if c.isdigit())
    if not digits:
        return dni_raw
    rev = digits[::-1]
    chunks = [rev[i:i + 3] for i in range(0, len(rev), 3)]
    return ".".join(c[::-1] for c in reversed(chunks))


# ═══════════════════════════════════════════════════════════════════════════════
# ESCRITO — plantilla completa
# ═══════════════════════════════════════════════════════════════════════════════

ESCRITO_TITULO = (
    "PARTE ACTORA RELATA HECHOS- OFRECE PRUEBA MÉDICA- SOLICITA INAPLICABILIDAD "
    "DE BAREMO 549/2025- SOLICITA SE DESIGNE AUDIENCIA MÉDICA.-"
)

ESCRITO_ENCABEZADO = (
    "Señor Superintendente:\n\n"
    "ARRECHEA LEANDRO T° 129 F° 33 / CASI T° LII F° 52 en mi carácter de letrado "
    "patrocinante de la parte actora en las presentes actuaciones, en virtud del "
    "decreto 5/2026 vengo por el presente a ofrecer prueba; solicitando se tenga "
    "por presentada y se de íntegro cumplimiento al Art 1 bis, inciso a, de la "
    "Ley 19.549, el cual establece el principio de la tutela administrativa "
    "efectiva, el cual debe primar en todo proceso administrativo.\n\n"
    "En virtud de esta disposición, corresponde reconocer y garantizar al Sr "
    "<b>{NOMBRE_CLIENTE}</b> los derechos fundamentales de un debido proceso adjetivo "
    "en el marco de los procedimientos administrativos, tales como:\n\n"
    "1.- El derecho a ser oído por parte de la autoridad administrativa "
    "competente.\n\n"
    "2.- El derecho a <b>ofrecer y producir prueba</b> que acredite los hechos que "
    "sustentan la solicitud (y que la misma se produzca en búsqueda de la "
    "verdad material). -\n\n"
    "3.- El derecho a recibir una decisión fundada en un plazo razonable, "
    "conforme al principio de razonabilidad y celeridad en la tramitación de "
    "los procedimientos administrativos. En este contexto, se pretende que se "
    "reconozcan y garanticen estos derechos procesales del trabajador, con el "
    "fin de que se resuelva el presente reclamo conforme a derecho y dentro de "
    "los plazos establecidos, en virtud de la legislación vigente, en especial "
    "la Ley 24.557."
)

ESCRITO_HECHOS = (
    "II.- HECHOS:\n\n"
    "{RELATO_HECHOS}"
)

ESCRITO_PRUEBA_A = (
    "III.- OFRECE PRUEBA.-\n\n"
    "En cumplimiento con la Res. SRT 5/2026 ofrezco la siguiente prueba:\n\n"
    "III. A) OFRECE PRUEBA PERICIAL MÉDICA. SE OPONE A LOS RESULTADOS DE "
    "ESTUDIOS MÉDICOS INCORPORADOS POR LA ART - SOLICITA SE DESIGNE AUDIENCIA "
    "MÉDICA - SOLICITA REVISIÓN MÉDICA INTEGRAL.-\n\n"
    "Desde ya, esta parte se opone expresamente a los resultados de los "
    "estudios médicos aportados por la aseguradora <b>{NOMBRE_ART}</b>. En tanto los "
    "mismos no reflejan adecuadamente la gravedad de las lesiones sufridas por "
    "el trabajador ni el real estado de su salud actual. Resulta llamativo "
    "—por no decir contradictorio— que, pese a la entidad de los hechos "
    "denunciados y la multiplicidad de lesiones documentadas en la historia "
    "clínica, los informes presentados por la ART minimicen e incluso omitan "
    "consideraciones fundamentales sobre el estado físico del Sr "
    "<b>{NOMBRE_CLIENTE}</b>. Por ello, se impugnan formalmente dichos informes, y "
    "se solicita la producción de una nueva revisión médica imparcial que "
    "garantice la debida tutela administrativa conforme a la Ley 19.549. –\n\n"
    "Solicito que la misma sea llevada a cabo por profesional médico "
    "especializado en medicina del trabajo, medicina legal o la especialidad "
    "que se estime pertinente, facultado para realizar los exámenes, estudios "
    "clínicos y complementarios necesarios.\n\n"
    "El médico legista deberá:\n\n"
    "1.- Determinar si las lesiones descriptas por el trabajador y sus "
    "secuelas guardan relación causal directa con el hecho denunciado, "
    "conforme los antecedentes asistenciales, estudios médicos e historia "
    "clínica obrantes en el expediente. –\n\n"
    "2.- Describir técnicamente cada una de las lesiones padecidas por el "
    "trabajador, conforme diagnóstico clínico, imágenes, prácticas médicas "
    "realizadas y evolución registrada en su historia clínica.\n\n"
    "3.- Determinar el grado de incapacidad que presenta el trabajador como "
    "consecuencia de las siguientes lesiones y afecciones:\n\n"
    "4.- Determinar la existencia de factores de ponderación, conforme "
    "Decreto 659/96, evaluando edad, tareas habituales, impacto en la vida "
    "cotidiana, entre otros criterios relevantes.\n\n"
    "5.- Informar si el trabajador presenta, a la fecha, algún grado de "
    "incapacidad laborativa permanente, y en su caso, el porcentaje "
    "correspondiente conforme Baremo Decreto 659/96.-\n\n"
    "6.- Determinar si el cuadro clínico se encuentra consolidado y si ha "
    "finalizado el período de rehabilitación, o si por el contrario requiere "
    "nuevas prestaciones médicas o tratamientos complementarios, conforme lo "
    "previsto en la Ley 24.557.\n\n"
    "7.- Indicar si, a raíz de las secuelas físicas y funcionales que "
    "presenta el trabajador, resulta aconsejable o necesaria su recalificación "
    "profesional o reubicación laboral, considerando la imposibilidad o "
    "restricción para desempeñar las tareas que desarrollaba al momento del "
    "accidente para el empleador <b>{NOMBRE_EMPLEADOR}</b>. A tales efectos, el "
    "médico interviniente en la junta médica otorgada por la SRT, deberá "
    "valorar la aptitud laboral residual del trabajador y la razonabilidad de "
    "continuar en su puesto habitual sin comprometer su salud.\n\n"
    "Pido se tenga presente lo manifestado a sus efectos en cuanto a las "
    "oposiciones efectuadas y, en consecuencia, se produzca la prueba ofrecida "
    "precedentemente (prueba pericial médica y psicológica). –"
)

ESCRITO_PRUEBA_B = (
    "III.B.- SOLICITA INAPLICABILIDAD DECRETO 549/2025. SOLICITA APLICABILIDAD "
    "DECRETO 659/96. –\n\n"
    "a).- Solicita aplicación del Baremo vigente al momento del siniestro -\n\n"
    "El artículo 3 del Decreto 549/2025 dispone: \"La 'Tabla de Evaluación de "
    "Incapacidades Laborales', sustituida por el artículo 1° del presente "
    "decreto, entrará en vigencia a los ciento ochenta (180) días corridos, "
    "contados desde su publicación en el Boletín Oficial, y a partir de esa "
    "fecha resultará de aplicación a toda valoración o determinación de "
    "incapacidad laboral que no haya sido aún dictada, independientemente de "
    "la instancia administrativa o judicial en la que se encuentre.\" (el "
    "destacado me pertenece).-\n\n"
    "La norma transcripta resulta manifiestamente inconstitucional en cuanto "
    "pretende imponer la aplicación del nuevo baremo a contingencias "
    "anteriores a su dictado y a procesos en trámite, alterando situaciones "
    "jurídicas constituidas y créditos indemnizatorios consolidados, "
    "violentando de tal modo el derecho de propiedad y a la reparación "
    "integral de indudable raigambre constitucional.-\n\n"
    "En consecuencia, corresponde declarar su inconstitucionalidad y, por "
    "ende, la inaplicabilidad del nuevo baremo introducido por el Decreto "
    "549/2025 al caso de autos, debiendo aplicarse la Tabla de Evaluación de "
    "Incapacidades Laborales aprobada por el Decreto 659/1996, vigente al "
    "momento del infortunio.\n\n"
    "En primer término, es evidente que corresponde aplicar el baremo vigente "
    "al momento del accidente o primera manifestación invalidante, pues es en "
    "ese instante cuando nace el deber de reparar en cabeza de la "
    "Aseguradora de Riesgos del Trabajo y, correlativamente, el crédito "
    "indemnizatorio en favor del trabajador.\n\n"
    "Así lo establece el artículo 2 de la Ley 26.773 al disponer que: \"El "
    "derecho a la reparación dineraria se computará, más allá del momento en "
    "que se determine su procedencia y alcance, desde que acaeció el evento "
    "dañoso o se determinó la relación causal adecuada de la enfermedad "
    "profesional\".\n\n"
    "La disposición es clara: el derecho surge con el hecho dañoso y no con "
    "la sentencia ni con la determinación judicial o administrativa de "
    "incapacidad. Por consiguiente, las reglas que inciden en la "
    "cuantificación del daño — entre ellas el baremo que fija el porcentaje "
    "de incapacidad— deben ser las vigentes al momento en que el crédito se "
    "incorpora al patrimonio del trabajador.-\n\n"
    "En este sentido, el artículo 7 del Código Civil y Comercial de la Nación "
    "establece: \"A partir de su entrada en vigencia, las leyes se aplican a "
    "las consecuencias de las relaciones y situaciones jurídicas existentes. "
    "Las leyes no tienen efecto retroactivo, sean o no de orden público, "
    "excepto disposición en contrario. La retroactividad establecida por la "
    "ley no puede afectar derechos amparados por garantías constitucionales.\"\n\n"
    "A la luz de esta norma, el nuevo baremo no puede aplicarse a "
    "contingencias anteriores a su dictado. En primer lugar, porque el "
    "derecho indemnizatorio constituye un derecho consolidado desde el "
    "momento del accidente. Desde entonces nace la obligación resarcitoria y "
    "el crédito integra el patrimonio del trabajador, aun cuando su "
    "cuantificación definitiva se produzca con posterioridad.-\n\n"
    "En segundo lugar, porque aun cuando se pretendiera otorgar efecto "
    "retroactivo al nuevo régimen —lo que el artículo 7 CCyC admite solo de "
    "manera excepcional— tal retroactividad no puede afectar derechos "
    "amparados por garantías constitucionales, lo que ocurriría en el caso "
    "toda vez que la aplicación de un baremo posterior más restrictivo "
    "importa reducir el quantum indemnizatorio respecto del régimen vigente "
    "al momento del hecho, afectando de tal modo el derecho de propiedad "
    "consagrado en el artículo 17 de la Constitución Nacional y el principio "
    "de reparación integral que encuentra sustento en el artículo 19 de la "
    "Carta Magna y en los tratados internacionales con jerarquía "
    "constitucional (artículo 75 inciso 22 CN).-\n\n"
    "Por todo lo expuesto, corresponde declarar la inconstitucionalidad del "
    "artículo 3 del Decreto 549/2025, disponer la inaplicabilidad del nuevo "
    "baremo al caso de autos y ordenar la aplicación de la Tabla de "
    "Evaluación de Incapacidades Laborales aprobada por el Decreto 659/1996, "
    "en resguardo de los principios de irretroactividad, tutela judicial "
    "efectiva y protección del trabajador.\n\n"
    "b.- Solicita SE DESIGNE AUDIENCIA MÉDICA - Inconstitucionalidad "
    "manifiesta de la dispensa del examen médico presencial y de la "
    "realización de nuevos estudios médicos.-\n\n"
    "El Decreto 549/2025 incorpora una previsión de extrema gravedad "
    "institucional al establecer que el examen físico no se considerará un "
    "requisito indispensable para la valoración del daño. Dicha cláusula "
    "constituye una alteración sustancial, regresiva y arbitraria del régimen "
    "de determinación de la incapacidad laboral. Autorizar que la divergencia "
    "se resuelva sin examen médico presencial y sin nuevos estudios implica "
    "convalidar acríticamente la evaluación de la aseguradora, privando al "
    "trabajador de toda posibilidad real de revisión. Ello configura una "
    "violación palmaria del derecho de defensa (art. 18 CN) y del debido "
    "proceso, consolidando una asimetría estructural en favor de la ART. En "
    "consecuencia, debe ordenarse que el presente reclamo sea resuelto "
    "mediante una evaluación médica presencial, integral, actualizada e "
    "independiente, con realización de los estudios complementarios "
    "necesarios, como condición indispensable de validez constitucional del "
    "procedimiento.-"
)

ESCRITO_LESION_AFECCION = (
    "IV.- DIFERENCIA ENTRE LESIÓN Y AFECCIÓN. LÍMITES DE LA OBLIGACIÓN DE "
    "DENUNCIA.-\n\n"
    "Es necesario efectuar una distinción precisa y relevante entre los "
    "conceptos de lesión y afección en el análisis de la situación clínica "
    "del trabajador. La lesión hace referencia al daño físico concreto e "
    "inmediato que resulta del hecho dañoso. La afección comprende todas "
    "aquellas consecuencias orgánicas, funcionales o psicológicas que se "
    "desarrollan con posterioridad a la lesión original, ya sea por "
    "mecanismos compensatorios o adaptativos del cuerpo.\n\n"
    "En este contexto, no corresponde exigir que el trabajador haya "
    "denunciado individualmente todas las afecciones secundarias derivadas "
    "del accidente inicial, dado que la legislación vigente no impone tal "
    "obligación. La Ley 24.557 y su Decreto Reglamentario 717/96 establecen "
    "claramente que la denuncia debe circunscribirse al accidente de trabajo "
    "o a la enfermedad profesional sufrida, y no requiere la "
    "individualización de las afecciones posteriores. La jurisprudencia del "
    "fuero laboral ha sido categórica al respecto (cfr. \"Indartt, Sebastián "
    "Gabriel c/ A.R.T. Interacción S.A. s/ Accidente Ley Especial\", Sala I, "
    "C.N.A.T.).\n\n"
    "Por lo tanto, resulta improcedente exigir al trabajador que haya debido "
    "denunciar de manera autónoma y específica cada una de las afecciones "
    "que se manifestaron con posterioridad al accidente inicial. Corresponde "
    "a la Aseguradora de Riesgos del Trabajo y, en su caso, a la Comisión "
    "Médica, realizar la valoración integral y de oficio de todo el cuadro "
    "clínico, con el fin de asegurar que se brinde una reparación justa y "
    "adecuada conforme a la legislación aplicable. –"
)

ESCRITO_PERICIAL_PSI = (
    "V.- PERICIAL PSICOLÓGICA.\n\n"
    "Ante lo traumático del accidente sufrido y la dificultad para realizar "
    "acciones tan cotidianas y simples, el actor padece importantes secuelas "
    "psíquicas, que se manifiestan como episodios de frustración. Atento "
    "ello, solicito se designe perito psicológico, para que conteste los "
    "siguientes puntos de pericia, a saber:\n\n"
    "1.- La realización de un estudio psicodiagnóstico exhaustivo, que "
    "incluya entrevistas clínicas, test proyectivos, escalas estandarizadas "
    "y cualquier otro recurso profesional que el especialista considere "
    "pertinente, con el objeto de valorar de manera objetiva y actual el "
    "estado psíquico del trabajador. –\n\n"
    "2.- Informe si existe una relación causal entre el hecho denunciado y "
    "los síntomas emocionales que presenta el trabajador, tales como: "
    "estrés postraumático, angustia, dificultad para reintegrarse a su vida "
    "social y laboral, entre otros.\n\n"
    "3.- Determine y cuantifique el grado de incapacidad psicofísica que el "
    "trabajador padece como consecuencia de las secuelas emocionales del "
    "hecho traumático sufrido, aplicando los parámetros del Baremo aprobado "
    "por Decreto 659/96. -\n\n"
    "4.- Determine si, al día de la fecha, el trabajador requiere "
    "tratamiento psiquiátrico, en concordancia con la indicación médica que "
    "surge de la historia clínica confeccionada oportunamente por los "
    "profesionales de la <b>{NOMBRE_ART}</b>."
)

ESCRITO_PROTECTORIO = (
    "VI.- PRINCIPIO PROTECTORIO – EL TRABAJADOR COMO SUJETO DE PREFERENTE "
    "TUTELA CONSTITUCIONAL\n\n"
    "La aplicación de una reglamentación vigente al momento del inicio del "
    "trámite ante la Superintendencia de Riesgos del Trabajo, en desmedro de "
    "la normativa vigente al momento del acaecimiento del infortunio "
    "laboral, resulta manifiestamente improcedente y violatoria del orden "
    "constitucional.\n\n"
    "Conforme el régimen instaurado por la Ley 24.557 y sus modificatorias, "
    "los derechos del trabajador nacen y se incorporan a su patrimonio "
    "jurídico al momento del hecho generador, no pudiendo ser posteriormente "
    "alterados por disposiciones reglamentarias sin vulnerar el principio de "
    "irretroactividad consagrado en el art. 7 del Código Civil y Comercial "
    "de la Nación, así como las garantías de legalidad, seguridad jurídica y "
    "propiedad reconocidas por los arts. 17, 18 y 19 de la Constitución "
    "Nacional.\n\n"
    "La Corte Suprema de Justicia de la Nación ha sido categórica al sostener "
    "que las normas no pueden aplicarse retroactivamente cuando afectan "
    "derechos ya consolidados (CSJN, \"Espósito, Miguel Ángel c/ Provincia "
    "ART S.A.\", Fallos: 339:781), criterio reiterado en materia de riesgos "
    "del trabajo. A ello se suma el respeto irrestricto del principio "
    "protectorio, piedra angular del Derecho del Trabajo, consagrado en el "
    "art. 14 bis de la Constitución Nacional y reforzado por los "
    "instrumentos internacionales de derechos humanos con jerarquía "
    "constitucional (art. 75 inc. 22 CN).\n\n"
    "La Corte Suprema, en \"Madorrán, Marta A. c/ Administración Nacional de "
    "Aduanas\" y \"Vizzoti, Carlos A. c/ AMSA S.A.\", consagró al trabajador "
    "como sujeto de preferente tutela constitucional. La Corte Interamericana "
    "de Derechos Humanos, en su Opinión Consultiva sobre acceso a la justicia "
    "como garantía de los derechos económicos, sociales y culturales, ha "
    "destacado que los Estados deben remover los obstáculos normativos o "
    "procedimentales que impidan el acceso real y efectivo a la justicia.\n\n"
    "En consecuencia, la aplicación retroactiva de reglamentaciones emanadas "
    "de la SRT deviene inconstitucional, en tanto importa una restricción "
    "ilegítima de derechos adquiridos, vulnera el principio protectorio y el "
    "principio pro homine, y frustra el acceso del trabajador a una revisión "
    "judicial amplia y efectiva."
)

ESCRITO_PETITORIO = (
    "VII.- PETITORIO. –\n\n"
    "En atención a las consideraciones de hecho y de derecho expuestas a lo "
    "largo del presente y en cumplimiento con las disposiciones legales "
    "vigentes, solicitamos que:\n\n"
    "a.- Se tengan presentes todas y cada una de las lesiones psicofísicas "
    "padecidas por el trabajador expuestas en el presente escrito. -\n\n"
    "b.- Se lleve a cabo una pericia médica y psicológica que contemple "
    "exhaustivamente todas las lesiones y secuelas que el trabajador padece, "
    "y se determine con precisión el grado de incapacidad que le corresponde "
    "conforme al Baremo de Incapacidades en vigor. –\n\n"
    "c.- Se evalúe la posibilidad de recalificación de las tareas del "
    "trabajador, teniendo en cuenta las secuelas derivadas del accidente, a "
    "fin de garantizar que su desempeño laboral no comprometa su salud "
    "física ni psíquica.\n\n"
    "d.- Se reconozca y respete el derecho del trabajador a ser escuchado, a "
    "ofrecer y producir prueba, y a recibir una decisión fundada dentro de "
    "un plazo razonable, conforme a lo estipulado por el artículo 1 bis, "
    "inciso a de la Ley 19.549. –\n\n"
    "e.- Se otorgue al trabajador el tratamiento y las prestaciones en "
    "especie establecidas por la Ley 24.557, y que se asegure la reparación "
    "integral de los daños sufridos, en concordancia con la normativa "
    "aplicable.-\n\n"
    "Por lo expuesto, solicito que se tenga por presentado este escrito y se "
    "dé curso a las peticiones realizadas, conforme a derecho.-\n\n"
    "Proveer de conformidad,\n\n"
    "SERÁ JUSTICIA.-"
)


def _esc_xml(s: str) -> str:
    """Escapa caracteres XML/HTML para insertar safely en Paragraph de reportlab."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def compose_escrito(vars_: dict) -> list[tuple[str, str]]:
    """Devuelve una lista de (tipo, texto) donde tipo ∈ {'titulo','para'}.
    El texto puede contener HTML inline (<b>, <u>, <i>) que el renderer interpreta.

    vars_ esperado:
      - nombre_cliente (str) — ej "BRAVO, Aurelio" o "PERALTA, Claudia Patricia"
      - nombre_art    (str) — razón social o nombre corto
      - nombre_empleador (str)
      - relato_hechos (str) — párrafo único en tercera persona
    """
    art_nombre = (vars_.get("art_nombre") or vars_.get("nombre_art") or "la ART").strip()
    art_match = lookup_art(art_nombre)
    art_render = art_match.get("razon", art_nombre) if art_match.get("razon") else art_nombre

    # Los valores se escapan porque entran dentro de markup HTML (<b>...</b>)
    repl = {
        "NOMBRE_CLIENTE":   _esc_xml((vars_.get("nombre_cliente") or "el actor").strip()),
        "NOMBRE_ART":       _esc_xml(art_render),
        "NOMBRE_EMPLEADOR": _esc_xml((vars_.get("nombre_empleador") or "el empleador").strip()),
        "RELATO_HECHOS":    _esc_xml((vars_.get("relato_hechos")    or "(relato de hechos pendiente)").strip()),
    }

    def fmt(s: str) -> str:
        for k, v in repl.items():
            s = s.replace("{" + k + "}", v)
        return s

    blocks = [
        ("titulo",  ESCRITO_TITULO),
        ("para",    fmt(ESCRITO_ENCABEZADO)),
        ("para",    fmt(ESCRITO_HECHOS)),
        ("para",    fmt(ESCRITO_PRUEBA_A)),
        ("para",    fmt(ESCRITO_PRUEBA_B)),
        ("para",    fmt(ESCRITO_LESION_AFECCION)),
        ("para",    fmt(ESCRITO_PERICIAL_PSI)),
        ("para",    fmt(ESCRITO_PROTECTORIO)),
        ("para",    fmt(ESCRITO_PETITORIO)),
    ]
    return blocks


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS DE EXTRACCIÓN — solo extraen variables, no redactan el documento
# ═══════════════════════════════════════════════════════════════════════════════

PROMPT_EXTRACCION = """Sos un asistente legal que prepara documentos para el Estudio Arrechea.
Te paso el texto de un PDF de antecedentes (denuncia ART, formulario, expediente).
Tu tarea es EXTRAER datos para completar un telegrama Ley 23.789 y un escrito judicial.

Devolvé EXCLUSIVAMENTE un objeto JSON válido con esta estructura exacta:

{
  "nombre_trabajador": "APELLIDO Y NOMBRE en mayúsculas (ej: PERALTA CLAUDIA PATRICIA)",
  "nombre_cliente": "Apellido, Nombre (ej: 'PERALTA, Claudia Patricia')",
  "dni": "12345678 (solo dígitos)",
  "fecha_accidente": "YYYY-MM-DD",
  "art_nombre": "nombre tal como figura en el PDF (ej: 'Provincia ART', 'Swiss Medical', 'Prevención')",
  "nombre_empleador": "razón social del empleador",
  "lesiones_y_estudios": "PÁRRAFO ÚNICO en primera persona del singular ('sufrí ... solicito ...') con: (a) lesiones del expediente, (b) lesiones derivadas/inferidas por la mecánica, (c) síntomas (dolor crónico, limitación funcional, etc.), (d) afectación psicológica SIEMPRE incluida, (e) estudios solicitados (RMN de zonas afectadas, radiografías, ecografías, evaluación psicológica). Empezar con: 'Como consecuencia del hecho sufrí ...'. Terminar con: 'Asimismo solicito la realización de los siguientes estudios y tratamientos médicos: ...'.",
  "relato_hechos": "PÁRRAFO ÚNICO en TERCERA PERSONA narrando: fecha del accidente, lugar, tarea que realizaba, mecánica del accidente, lesiones sufridas, atención médica, estado actual. Empezar con: 'El día [FECHA], el trabajador, quien desempeñaba tareas como ...'."
}

Reglas:
- Si algún dato no figura en el PDF, devolvé "" (string vacío) en ese campo.
- NO inventes datos. Si dudás, dejá vacío.
- Las fechas siempre en formato YYYY-MM-DD.
- El DNI solo dígitos sin puntos.
- NO agregues comentarios, NO uses markdown, devolvé SOLO el JSON.
"""
