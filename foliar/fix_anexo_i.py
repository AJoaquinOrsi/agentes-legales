"""Repara el PDF base anexo_i_-_incapacidad.pdf:

El campo `Nombre y Apellido` es uno solo con dos widgets hijos (trabajador y letrado),
por lo que escribir en uno copia el valor al otro. También pasa con `CUIL` o cualquier
otro nombre duplicado.

Este script separa cada hijo en un campo terminal independiente con nombre único:
- 'Nombre y Apellido'           → trabajador (widget de mayor Y)
- 'Nombre y Apellido Letrado'   → letrado (widget de menor Y)

Mismo tratamiento para todos los campos con kids duplicados.
"""
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject, ArrayObject

SRC = Path(r"C:/Users/alexi/OneDrive/Desktop/anexo_i_-_incapacidad.pdf")
DST = Path(r"C:/Users/alexi/OneDrive/Desktop/anexo_i_-_incapacidad_fixed.pdf")

# Sufijos que se aplican al SEGUNDO widget (el que aparece más abajo en la página).
# Si un nombre no está acá, no se renombra el segundo widget.
RENAME_RULES = {
    "Nombre y Apellido": "Nombre y Apellido Letrado",
}


def main():
    reader = PdfReader(str(SRC))
    writer = PdfWriter(clone_from=reader)

    acro_ref = writer._root_object.get("/AcroForm")
    if acro_ref is None:
        print("Sin AcroForm")
        return
    acro = acro_ref.get_object() if hasattr(acro_ref, "get_object") else acro_ref

    fields_ref = acro.get("/Fields")
    if fields_ref is None:
        print("Sin /Fields")
        return
    fields = fields_ref.get_object() if hasattr(fields_ref, "get_object") else fields_ref

    # Buscar y reparar campos compuestos (con /Kids)
    new_fields = ArrayObject()
    fixes = 0

    for fld_ref in fields:
        fld = fld_ref.get_object()
        kids = fld.get("/Kids")
        name = fld.get("/T")

        if kids and len(kids) > 1 and name in RENAME_RULES:
            # Ordenar por Y (de arriba abajo)
            kids_sorted = sorted(
                kids,
                key=lambda k: -(k.get_object().get("/Rect", [0, 0, 0, 0])[1]),
            )

            for i, kid_ref in enumerate(kids_sorted):
                kid = kid_ref.get_object()
                # Copiar /FT, /DA, /Q del padre si los tiene
                for prop in ("/FT", "/DA", "/Q", "/V", "/DV"):
                    if prop in fld and prop not in kid:
                        kid[NameObject(prop)] = fld[prop]
                # Asignar nombre único: el primero conserva el original, el segundo recibe el sufijo
                new_name = name if i == 0 else RENAME_RULES[name]
                kid[NameObject("/T")] = TextStringObject(new_name)
                # Quitar /Parent ya que será un terminal field
                if "/Parent" in kid:
                    del kid["/Parent"]
                new_fields.append(kid_ref)
                fixes += 1

            print(f"Reparado: {name!r} → {len(kids_sorted)} campos terminales")
        else:
            new_fields.append(fld_ref)

    acro[NameObject("/Fields")] = new_fields
    # Forzar regenerar apariencia
    acro[NameObject("/NeedAppearances")] = NameObject("/true")

    with open(DST, "wb") as f:
        writer.write(f)

    print(f"\nGenerado: {DST}")
    print(f"Total campos creados nuevos: {fixes}")

    # Verificación
    r2 = PdfReader(str(DST))
    flds = r2.get_fields() or {}
    print(f"\nTotal campos en PDF reparado: {len(flds)}")
    for n in flds:
        if "Nombre" in n or "CUIL" in n:
            print(f"  · {n}")


if __name__ == "__main__":
    main()
