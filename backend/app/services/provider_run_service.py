import json
import re
from typing import List, Any
from sqlalchemy.orm import Session
from app.models.provider import ProviderRunLog
from app.schemas.provider_schema import ProviderRunLogCreate

def redact_payload(payload: Any) -> Any:
    """
    Recursively redacts secrets from dictionaries or lists.
    Also handles JSON strings.
    """
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if isinstance(parsed, (dict, list)):
                return json.dumps(redact_payload(parsed))
        except json.JSONDecodeError:
            pass
        return payload
        
    if isinstance(payload, dict):
        redacted_dict = {}
        secret_keys = re.compile(r'api_key|token|secret|authorization|password', re.IGNORECASE)
        for k, v in payload.items():
            if secret_keys.search(str(k)):
                redacted_dict[k] = "[REDACTED]"
            else:
                redacted_dict[k] = redact_payload(v)
        return redacted_dict
        
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
        
    return payload

def _safe_json_dumps(payload: Any) -> str:
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload
    return json.dumps(payload)

def create_run_log(db: Session, log_in: ProviderRunLogCreate) -> ProviderRunLog:
    # Ensure sensitive data is redacted before database insertion
    safe_request = redact_payload(log_in.request_json)
    safe_response = redact_payload(log_in.response_json)
    
    db_log = ProviderRunLog(
        project_id=log_in.project_id,
        scene_id=log_in.scene_id,
        provider_name=log_in.provider_name,
        model_name=log_in.model_name,
        modality=log_in.modality,
        operation=log_in.operation,
        provider_job_id=log_in.provider_job_id,
        status=log_in.status,
        request_json=_safe_json_dumps(safe_request),
        response_json=_safe_json_dumps(safe_response),
        error_message=log_in.error_message
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def list_project_run_logs(db: Session, project_id: int) -> List[ProviderRunLog]:
    return db.query(ProviderRunLog).filter(ProviderRunLog.project_id == project_id).order_by(ProviderRunLog.created_at.desc()).all()

def list_scene_run_logs(db: Session, scene_id: int) -> List[ProviderRunLog]:
    return db.query(ProviderRunLog).filter(ProviderRunLog.scene_id == scene_id).order_by(ProviderRunLog.created_at.desc()).all()

def list_recent_run_logs(db: Session, limit: int = 50) -> List[ProviderRunLog]:
    return db.query(ProviderRunLog).order_by(ProviderRunLog.created_at.desc()).limit(limit).all()
