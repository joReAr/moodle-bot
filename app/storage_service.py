import json
import os
from typing import Optional, Tuple
from .config import settings
from .db import get_session
from .models import Manual, Chunk, Pill, Asset

FILES_ROOT = settings.LOCAL_STORAGE_DIR  # ./data

def local_path(*parts: str) -> str:
    path = os.path.join(FILES_ROOT, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def register_manual(title: str, pdf_local_path: str) -> Manual:
    from .db import get_session
    with get_session() as s:
        m = Manual(title=title, source_path=pdf_local_path)
        s.add(m); s.commit(); s.refresh(m)
        # también registramos el PDF como Asset
        rel = os.path.relpath(pdf_local_path, FILES_ROOT)
        a = Asset(kind="pdf", ref=f"/files/{rel}", manual_id=m.id)
        s.add(a); s.commit()
        return m

def save_chunk(manual_id: int, page: int, text: str, images: list) -> Chunk:
    with get_session() as s:
        c = Chunk(manual_id=manual_id, page=page, text=text, images_json=json.dumps(images))
        s.add(c); s.commit(); s.refresh(c)
        # registra figuras como assets
        for img in images:
            if "ref" in img:
                a = Asset(kind="figure", ref=img["ref"], manual_id=manual_id, page=img.get("page"))
                s.add(a)
        s.commit()
        return c

def save_pill(manual_id: int, chunk_id: int, pill_obj: dict, audio_url: Optional[str] = None) -> Pill:
    with get_session() as s:
        p = Pill(manual_id=manual_id, chunk_id=chunk_id, pill_json=json.dumps(pill_obj), audio_url=audio_url)
        s.add(p); s.commit(); s.refresh(p)
        return p
