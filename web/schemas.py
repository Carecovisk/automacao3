from typing import List, Optional

from pydantic import BaseModel


class PastedData(BaseModel):
    data: list[list[str|None]]
    description: str
    description_column: str  # Name of the column containing descriptions to match


class ExcelData(BaseModel):
    fileName: str
    skipRows: int
    filterText: Optional[str] = None
    isRegex: bool = False
    columns: "ExcelColumns"
    columnIndices: "ExcelColumnIndices"
    data: List["ExcelRow"]


class ExcelColumns(BaseModel):
    description: str
    quantity: str
    value: str


class ExcelColumnIndices(BaseModel):
    description: int
    quantity: int
    value: int


class ExcelRow(BaseModel):
    description: str
    quantity: float
    value: float


# Task Status and Results Models
class MatchedItem(BaseModel):
    description: str
    distance: float
    score: float


class MatchResult(BaseModel):
    query: str
    matched_items: List[MatchedItem]


class TaskStatus(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int
    total: int
    percentage: float
    results: Optional[List[MatchResult]] = None
    error: Optional[str] = None
