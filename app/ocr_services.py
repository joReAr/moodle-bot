import json, sys
from typing import List, Dict, Optional, Any
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# --------------------------
# Utilidades
# --------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

 

def clean_text(s: str) -> str:
    s = s.replace("\r", "\n")
    # normalización mínima
    lines = [ln.strip() for ln in s.split("\n")]
    # colapsa líneas vacías múltiples
    out, prev_blank = [], False
    for ln in lines:
        blank = (ln == "")
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank
    return "\n".join(out).strip()

def guess_caption(text_blocks: List[Dict[str, Any]], img_bbox: List[float]) -> Optional[str]:
    """
    Heurística simple: buscar la línea de texto más cercana *debajo* de la imagen
    y devolverla si parece un caption (empieza con 'Fig'/'Figura' o es corta).
    """
    x0, y0, x1, y1 = img_bbox
    area_below_y = y1 + 4  # un pequeño margen
    candidates = []
    for blk in text_blocks:
        if blk["type"] != 0:
            continue
        # blk["lines"] es una lista de líneas, con spans
        for ln in blk.get("lines", []):
            # bbox de la línea
            l_x0 = min(sp["bbox"][0] for sp in ln["spans"])
            l_y0 = min(sp["bbox"][1] for sp in ln["spans"])
            l_x1 = max(sp["bbox"][2] for sp in ln["spans"])
            l_y1 = max(sp["bbox"][3] for sp in ln["spans"])
            # solo líneas inmediatamente debajo de la imagen y alineadas horizontalmente
            vertically_below = l_y0 >= area_below_y and (l_y0 - area_below_y) < 120
            horizontally_overlap = not (l_x1 < x0 or l_x0 > x1)
            if vertically_below and horizontally_overlap:
                text_line = "".join(sp["text"] for sp in ln["spans"]).strip()
                if text_line:
                    # preferir líneas que empiecen por 'Fig'/'Figura' o cortas
                    score = 0
                    tl = text_line.lower()
                    if tl.startswith("fig") or tl.startswith("figura"):
                        score += 2
                    if len(text_line) <= 120:
                        score += 1
                    # penalizar líneas muy largas
                    score -= 1 if len(text_line) > 200 else 0
                    candidates.append((score, text_line))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0], reverse=True)
    return candidates[0][1]

# --------------------------
# Extracción por página
# --------------------------

def raster_crop(page: Any, bbox: List[float], zoom: float = 2.0) -> Image.Image:
    """
    Recorta una región de la página renderizada con zoom (para buena calidad).
    """
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (int(pix.width), int(pix.height)), pix.samples)
    x0, y0, x1, y1 = bbox
    # escalar bbox al raster (por el zoom)
    box = (int(x0 * zoom), int(y0 * zoom), int(x1 * zoom), int(y1 * zoom))
    # asegurar límites
    box = (max(0, box[0]), max(0, box[1]),
           min(img.width, box[2]), min(img.height, box[3]))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("BBox inválido para recorte.")
    return img.crop(box)

def extract_page_assets(page: Any, out_pages: Path, out_images: Path, page_idx: int) -> Dict[str, Any]:
    
    text_plain = clean_text(page.get_text("text"))

    d = page.get_text("dict")  
    blocks = d.get("blocks", [])

    images_info = []
    img_count = 0

    for blk in blocks:
        if blk.get("type") == 1:
            # Bloque de imagen
            bbox = blk.get("bbox")
            if not bbox:
                continue
            try:
                crop = raster_crop(page, bbox, zoom=2.0)
            except Exception:
                continue
            img_count += 1
            img_name = f"p{page_idx:04d}_img{img_count:02d}.png"
            crop.save(out_images / img_name, "PNG")

            caption = guess_caption(blocks, bbox)  # puede ser None
            images_info.append({
                "file": str(Path("images") / img_name).replace("\\", "/"),
                "bbox": [round(float(x), 2) for x in bbox],
                "caption": caption
            })

    # Guardar texto por página
    with open(out_pages / f"page_{page_idx:04d}.txt", "w", encoding="utf-8") as f:
        f.write(text_plain)

    return {
        "page_index": page_idx,
        "text_file": str(Path("pages") / f"page_{page_idx:04d}.txt").replace("\\", "/"),
        "images": images_info
    }

# --------------------------
# Driver principal
# --------------------------

def extract_pdf(pdf_path: Path, out_dir: Path) -> Dict[str, Any]:
    ensure_dir(out_dir)
    out_pages = out_dir / "pages"
    out_images = out_dir / "images"
    ensure_dir(out_pages)
    ensure_dir(out_images)

    doc = fitz.open(pdf_path)
    manifest = {
        "pdf": str(pdf_path),
        "num_pages": len(doc),
        "pages": []
    }
    for i in range(len(doc)):
        page = doc[i]
        page_info = extract_page_assets(page, out_pages, out_images, i + 1)
        manifest["pages"].append(page_info)

    # Escribir manifest
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    doc.close()
    return manifest

def main():
    if len(sys.argv) < 3:
        print("Uso: python ocr_services.py <input.pdf> <output_dir>")
        sys.exit(1)
    pdf_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    manifest = extract_pdf(pdf_path, out_dir)
    print(f"[OK] Páginas: {manifest['num_pages']}")
    print(f"[OK] Manifest: {out_dir/'manifest.json'}")
    print(f"[OK] Textos:   {out_dir/'pages'}")
    print(f"[OK] Imágenes: {out_dir/'images'}")

if __name__ == "__main__":
    main()


