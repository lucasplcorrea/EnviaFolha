"""
Serviço para execução de scripts utilitários do sistema.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.employee import Employee

logger = logging.getLogger(__name__)


class UtilityScriptsService:
    """Serviço para gerenciar e executar scripts utilitários."""
    
    def __init__(self, db: Session):
        self.db = db
        self.scripts = {
            'fix_unique_id_zeros': self._fix_unique_id_zeros
        }
        self.preview_handlers = {
            'fix_unique_id_zeros': self._preview_fix_unique_id_zeros
        }
    
    def preview_script(self, script_id: str) -> Dict[str, Any]:
        """
        Retorna preview das alterações que um script faria.
        
        Args:
            script_id: ID do script a ser visualizado
            
        Returns:
            Dict com informações sobre as alterações que seriam feitas
        """
        if script_id not in self.preview_handlers:
            raise ValueError(f"Script '{script_id}' não encontrado")
        
        preview_handler = self.preview_handlers[script_id]
        return preview_handler()
    
    def execute_script(self, script_id: str) -> Dict[str, Any]:
        """
        Executa um script utilitário.
        
        Args:
            script_id: ID do script a ser executado
            
        Returns:
            Dict com resultado da execução
        """
        if script_id not in self.scripts:
            raise ValueError(f"Script '{script_id}' não encontrado")
        
        script_handler = self.scripts[script_id]
        return script_handler()
    
    def _preview_fix_unique_id_zeros(self) -> Dict[str, Any]:
        """
        Preview do script que corrige unique_ids com zeros faltantes.
        """
        logger.info("Gerando preview de correção de unique_ids")
        
        # Buscar colaboradores com unique_id começando com 59 ou 60
        employees = self.db.query(Employee).filter(
            or_(Employee.unique_id.like('59%'), Employee.unique_id.like('60%'))
        ).all()
        
        preview_items = []
        already_correct = 0
        to_fix = 0
        unexpected_format = 0
        
        for employee in employees:
            old_id = employee.unique_id
            
            # Verificar se já tem o formato correto (9 caracteres começando com 00)
            if len(old_id) == 9 and old_id.startswith('00'):
                already_correct += 1
                continue
            
            # Se tem 7 caracteres e começa com 59/60, precisa correção
            if len(old_id) == 7 and (old_id.startswith('59') or old_id.startswith('60')):
                new_id = f"00{old_id}"
                to_fix += 1
                preview_items.append({
                    'id': employee.id,
                    'full_name': employee.full_name,
                    'old_id': old_id,
                    'new_id': new_id
                })
            else:
                unexpected_format += 1
        
        return {
            'message': f'Encontrados {to_fix} colaboradores para correção',
            'affected_count': to_fix,
            'preview_items': preview_items[:50],  # Limitar a 50 para não sobrecarregar UI
            'total_items': to_fix,
            'details': {
                'already_correct': already_correct,
                'to_fix': to_fix,
                'unexpected_format': unexpected_format,
                'total_analyzed': len(employees)
            }
        }
    
    def _fix_unique_id_zeros(self) -> Dict[str, Any]:
        """
        Corrige unique_ids que perderam zeros à esquerda.
        Adiciona '00' à esquerda de IDs que começam com 59 ou 60 e têm 7 caracteres.
        """
        logger.info("Iniciando correção de unique_ids com zeros faltantes")
        
        # Buscar colaboradores com unique_id começando com 59 ou 60
        employees = self.db.query(Employee).filter(
            or_(Employee.unique_id.like('59%'), Employee.unique_id.like('60%'))
        ).all()
        
        corrections = []
        conflicts = []
        
        for employee in employees:
            old_id = employee.unique_id
            
            # Verificar se já tem o formato correto
            if len(old_id) == 9 and old_id.startswith('00'):
                continue
            
            # Se tem 7 caracteres e começa com 59/60, adiciona 00 à esquerda
            if len(old_id) == 7 and (old_id.startswith('59') or old_id.startswith('60')):
                new_id = f"00{old_id}"
                
                # Verificar se o novo ID já existe em outro colaborador
                existing = self.db.query(Employee).filter(
                    Employee.unique_id == new_id,
                    Employee.id != employee.id
                ).first()
                
                if existing:
                    conflicts.append({
                        'employee': employee.full_name,
                        'old_id': old_id,
                        'new_id': new_id,
                        'conflict_with': existing.full_name
                    })
                    logger.warning(
                        f"Conflito: {employee.full_name} ({old_id} -> {new_id}) "
                        f"já existe em {existing.full_name}"
                    )
                    continue
                
                # Aplicar correção
                employee.unique_id = new_id
                corrections.append({
                    'employee': employee.full_name,
                    'old_id': old_id,
                    'new_id': new_id
                })
                
                logger.info(f"Corrigido: {employee.full_name} - {old_id} -> {new_id}")
        
        # Commit das alterações
        if corrections:
            self.db.commit()
            logger.info(f"Correção concluída: {len(corrections)} colaboradores atualizados")
        else:
            logger.info("Nenhuma correção necessária")
        
        return {
            'message': f'Correção concluída com sucesso! {len(corrections)} colaboradores atualizados.',
            'affected_count': len(corrections),
            'details': {
                'corrected': len(corrections),
                'conflicts': len(conflicts),
                'corrections_list': corrections[:20],  # Primeiros 20
                'conflicts_list': conflicts
            }
        }
