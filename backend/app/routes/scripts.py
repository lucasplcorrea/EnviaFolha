"""
Rotas para execução de scripts utilitários do sistema.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.utility_scripts import UtilityScriptsService

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("/{script_id}/preview")
async def preview_script(
    script_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Visualiza as alterações que um script faria sem executá-las.
    Requer permissões de administrador.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem visualizar scripts")
    
    service = UtilityScriptsService(db)
    
    try:
        result = service.preview_script(script_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao executar preview: {str(e)}")


@router.post("/{script_id}")
async def execute_script(
    script_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Executa um script utilitário.
    Requer permissões de administrador.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem executar scripts")
    
    service = UtilityScriptsService(db)
    
    try:
        result = service.execute_script(script_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao executar script: {str(e)}")
