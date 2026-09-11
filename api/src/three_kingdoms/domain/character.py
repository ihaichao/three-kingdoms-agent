from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Character(BaseModel):
    id: str = Field(description="unique identifier of the role")
    name: str = Field(description="name of the role")
    perspective: str = Field(description="perspective of the role")
    style: str = Field(description="talking style of the role")

    def __str__(self) -> str:
        return f"Character(id={self.id}, name={self.name}, perspective={self.perspective}, style={self.style})"


class CharacterExtract(BaseModel):
    id: str = Field(description="unique identifier of the role")
    urls: list[str] = Field(description="list of URLs with information about the role")

    @classmethod
    def from_json(cls, metadata_file: Path) -> list[CharacterExtract]:
        with open(metadata_file, "r", encoding="utf-8") as f:
            characters_data = json.load(f)

        return [cls(**character) for character in characters_data]
