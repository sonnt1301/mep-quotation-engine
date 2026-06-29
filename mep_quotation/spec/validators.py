from typing import Dict, Any
from pydantic import ValidationError
from mep_quotation.spec.models import (
    QuotationPackageModel,
    NormalizedQuotationModel,
    CorrectionsFileModel,
    AuditLogEntryModel
)

def validate_package_data(data: Dict[str, Any]) -> QuotationPackageModel:
    """Validate dữ liệu package.json."""
    try:
        return QuotationPackageModel.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid package data: {e}")

def validate_normalized_data(data: Dict[str, Any]) -> NormalizedQuotationModel:
    """Validate dữ liệu normalized.json."""
    try:
        return NormalizedQuotationModel.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid normalized quotation data: {e}")

def validate_corrections_data(data: Dict[str, Any]) -> CorrectionsFileModel:
    """Validate dữ liệu corrections.json."""
    try:
        return CorrectionsFileModel.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid corrections data: {e}")

def validate_audit_log_entry_data(data: Dict[str, Any]) -> AuditLogEntryModel:
    """Validate một dòng audit log JSONL."""
    try:
        return AuditLogEntryModel.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid audit log entry: {e}")
