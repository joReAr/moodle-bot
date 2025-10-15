from typing import List, Dict, Any
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io, os, json
from .config import settings
from .storage_service import local_path

def _page_has_vector_text(page: fitz.Page) -> bool:
    # Heurística: si extrae texto vectorial > N chars, consideramos no-escaneado
    txt = page.get_text("text")
    return len(txt.strip()) > 50

def _rasterize_page(page: fitz.Page, zoom: float = 2.0) -> Image.Image:
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def _extract_text(page: fitz.Page) -> str:
    if _page_has_vector_text(page):
        return page.get_text("text")
    # Escaneado: rasteriza + OCR
    img = _rasterize_page(page, 2.0)
    return pytesseract.image_to_string(img, lang="spa+eng")

def _extract_figures(page: fitz.Page, manual_dir: str, page_idx: int) -> List[Dict[str, Any]]:
    """
    Extrae imágenes embebidas en la página y devuelve:
    [{ref:'/files/figures/<manual>/<page>_<i>.png', page:page_idx, bbox:[x0,y0,x1,y1], caption:''}]
    """
    figs = []
    # 1) Raster completo (para recortar por bbox si hiciera falta)
    page_img = _rasterize_page(page, 2.0)
    # 2) Recorre XObjects
    image_list = page.get_images(full=True)
    for i, img in enumerate(image_list):
        xref = img[0]
        try:
            rects = page.get_image_bbox(xref)
            # get_image_bbox devuelve un Rect por cada colocación (PyMuPDF >=1.23)
            if not isinstance(rects, list):
                rects = [rects]
        except Exception:
            rects = []

        for j, rect in enumerate(rects):
            x0, y0, x1, y1 = int(rect.x0), int(rect.y0), int(rect.x1), int(rect.y1)
            crop = page_img.crop((x0, y0, x1, y1))
            rel = os.path.join("figures", manual_dir, f"p{page_idx}_img{i}_{j}.png")
            out_path = local_path(rel)
            crop.save(out_path, format="PNG")
            figs.append({
                "ref": f"/files/{rel.replace(os.sep,'/')}",
                "page": page_idx,
                "bbox": [x0, y0, x1, y1],
                "caption": ""  # se llenará con Gemini en pipeline
            })
    return figs

def extract_from_pdf(pdf_path: str, manual_dir: str) -> List[dict]:
    """
    Devuelve una lista de dicts de página:
    [{page:int, text:str, images:[{ref,page,bbox,caption}]}]
    """
    doc = fitz.open(pdf_path)
    out = []
    for p in range(len(doc)):
        page = doc[p]
        text = _extract_text(page)
        figures = _extract_figures(page, manual_dir, p)
        out.append({"page": p, "text": text, "images": figures})
    doc.close()
    return out
