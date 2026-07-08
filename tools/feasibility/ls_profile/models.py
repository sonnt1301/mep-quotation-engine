from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ExtractedItem:
    source_page: int
    layout_name: str
    product_family: str
    type: str
    pole: str
    rated_current: str
    breaking_capacity: str
    material_code: str
    description: str
    unit: str
    unit_price: int
    currency: str
    confidence: float
    extraction_method: str
    evidence_text: str
    source_supplier: str = "LS"
    validation_status: str = "valid"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_supplier": self.source_supplier,
            "source_page": self.source_page,
            "layout_name": self.layout_name,
            "product_family": self.product_family,
            "type": self.type,
            "pole": self.pole,
            "rated_current": self.rated_current,
            "breaking_capacity": self.breaking_capacity,
            "material_code": self.material_code,
            "description": self.description,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "evidence_text": self.evidence_text,
            "validation_status": self.validation_status,
            "errors": self.errors,
            "warnings": self.warnings
        }
