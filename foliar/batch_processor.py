"""
Foliar — Procesamiento en lote
Uso:
  python batch_processor.py --input CARPETA_PDFS --output CARPETA_SALIDA
  python batch_processor.py --input CARPETA_PDFS --output CARPETA_SALIDA --clientes clientes.txt

El archivo de clientes (opcional) es un .txt con un nombre por línea.
Si se provee, el formulario de salida usará ese nombre en lugar del nombre del PDF.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ── Importar funciones del backend ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from app import (
    extract_text,
    build_prompt,
    build_field_values,
    fill_form,
    _load_api_key,
)
import anthropic

FIELD_INFO_JSON = str(Path(__file__).parent / "assets" / "field_info.json")


def parse_json_objects(raw: str) -> list[dict]:
    """Extrae objetos JSON del texto libre que devuelve Claude."""
    objects = []
    buf = raw
    while buf:
        start = buf.find("{")
        if start == -1:
            break
        buf = buf[start:]
        depth, in_str, esc, end = 0, False, False, -1
        for i, ch in enumerate(buf):
            if esc:
                esc = False; continue
            if ch == "\\" and in_str:
                esc = True; continue
            if ch == '"':
                in_str = not in_str; continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i; break
        if end == -1:
            break
        candidate = buf[:end + 1]
        buf = buf[end + 1:]
        try:
            objects.append(json.loads(candidate))
        except json.JSONDecodeError:
            pass
    return objects


def process_pdf(pdf_path: str, output_path: str, api_key: str, label: str) -> bool:
    """
    Procesa un PDF y guarda el formulario rellenado en output_path.
    Retorna True si tuvo éxito, False si hubo error.
    """
    print(f"  Leyendo texto…")
    text = extract_text(pdf_path)
    if not text:
        print(f"  ERROR: no se pudo extraer texto del PDF.")
        return False

    print(f"  Enviando a Claude…")
    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            messages=[{"role": "user", "content": build_prompt(text)}],
        )
        raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception as e:
        print(f"  ERROR Claude: {e}")
        return False

    objs = parse_json_objects(raw)
    extracted = {}
    for d in objs:
        fid  = str(d.get("field", "")).strip()
        val  = d.get("value")
        conf = float(d.get("confidence", 0.9))
        if fid and val is not None and str(val) not in ("", "null", "None"):
            extracted[fid] = {"value": str(val), "confidence": conf}

    if not extracted:
        print(f"  ERROR: Claude no devolvió campos.")
        return False

    print(f"  Rellenando formulario ({len(extracted)} campos)…")
    with open(FIELD_INFO_JSON, encoding="utf-8") as f:
        field_info = json.load(f)

    field_values = build_field_values(extracted, field_info)
    fill_form(field_values, output_path)
    print(f"  Guardado: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Foliar — Procesamiento en lote")
    parser.add_argument("--input",    required=True, help="Carpeta con los PDFs de entrada")
    parser.add_argument("--output",   required=True, help="Carpeta donde guardar los formularios")
    parser.add_argument("--clientes", default=None,  help="Archivo .txt con nombres de clientes (uno por línea)")
    args = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"ERROR: la carpeta de entrada no existe: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Cargar lista de clientes (opcional)
    clientes = []
    if args.clientes:
        with open(args.clientes, encoding="utf-8") as f:
            clientes = [line.strip() for line in f if line.strip()]

    # Listar PDFs en la carpeta de entrada
    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No se encontraron PDFs en: {input_dir}")
        sys.exit(0)

    print(f"\nFoliar Batch — {len(pdfs)} PDF(s) encontrado(s)\n")

    # Cargar API key
    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    ok = 0
    errors = []

    for i, pdf_path in enumerate(pdfs):
        # Nombre de salida: usar cliente de la lista si corresponde, si no el nombre del PDF
        if i < len(clientes):
            safe_name = clientes[i].replace("/", "-").replace("\\", "-")
            out_name = f"formulario_{safe_name}.pdf"
        else:
            out_name = f"formulario_{pdf_path.stem}.pdf"

        output_path = str(output_dir / out_name)

        print(f"[{i+1}/{len(pdfs)}] {pdf_path.name}")
        if i < len(clientes):
            print(f"  Cliente: {clientes[i]}")

        success = process_pdf(str(pdf_path), output_path, api_key, out_name)
        if success:
            ok += 1
        else:
            errors.append(pdf_path.name)
        print()

    print("-" * 50)
    print(f"Completado: {ok}/{len(pdfs)} exitosos")
    if errors:
        print(f"Con errores:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
