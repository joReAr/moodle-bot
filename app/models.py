from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Manual(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    source_path: str  # ruta local del PDF original
    created_at: datetime = Field(default_factory=datetime.utcnow)

    chunks: List["Chunk"] = Relationship(back_populates="manual")
    pills: List["Pill"] = Relationship(back_populates="manual")

class Chunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    manual_id: int = Field(foreign_key="manual.id", index=True)
    page: int = Field(default=0, index=True)
    text: str
    images_json: str = Field(default="[]")  # lista [{ref,page,bbox,caption}], JSON str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    manual: Manual = Relationship(back_populates="chunks")

class Pill(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    manual_id: int = Field(foreign_key="manual.id", index=True)
    chunk_id: int = Field(foreign_key="chunk.id", index=True)
    pill_json: str  # JSON normalizado con flashcards/mcq/images
    audio_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    manual: Manual = Relationship(back_populates="pills")

# índice de assets (opcional, por si sirves figuras/audio como objetos)
class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str  # "figure" | "audio" | "pdf"
    ref: str   # ruta local relativa, ej. /files/figures/...
    manual_id: Optional[int] = Field(default=None, index=True)
    page: Optional[int] = Field(default=None)
    meta_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
