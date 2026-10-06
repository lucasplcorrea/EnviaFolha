"""
Companies Router — CRUD completo para /api/v1/companies
"""
from .base import BaseRouter
from datetime import datetime
from app.services.runtime_compat import SessionLocal


def _company_to_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "trade_name": c.trade_name,
        "cnpj": c.cnpj,
        "payroll_prefix": c.payroll_prefix,
        "address": c.address,
        "phone": c.phone,
        "email": c.email,
        "is_active": c.is_active,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        # contagem de relacionamentos (se já carregados)
        "employees_count": len(c.employees) if c.employees is not None else 0,
        "work_locations_count": len(c.work_locations) if c.work_locations is not None else 0,
    }


class CompaniesRouter(BaseRouter):
    """CRUD para empresas do grupo"""

    # ── GET /api/v1/companies ─────────────────────────────────────────────
    def handle_list(self):
        from app.models import Company
        from sqlalchemy.orm import joinedload

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            companies = (
                db.query(Company)
                .options(joinedload(Company.employees), joinedload(Company.work_locations))
                .order_by(Company.payroll_prefix)
                .all()
            )
            self.send_json_response([_company_to_dict(c) for c in companies])
        except Exception as e:
            import traceback; traceback.print_exc()
            self.send_error(f"Erro ao listar empresas: {str(e)}", 500)
        finally:
            db.close()

    # ── GET /api/v1/companies/<id> ────────────────────────────────────────
    def handle_get(self, company_id: int):
        from app.models import Company
        from sqlalchemy.orm import joinedload

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            company = (
                db.query(Company)
                .options(joinedload(Company.employees), joinedload(Company.work_locations))
                .filter(Company.id == company_id)
                .first()
            )
            if not company:
                self.send_error("Empresa não encontrada", 404); return
            self.send_json_response(_company_to_dict(company))
        except Exception as e:
            self.send_error(f"Erro: {str(e)}", 500)
        finally:
            db.close()

    # ── POST /api/v1/companies ────────────────────────────────────────────
    def handle_create(self):
        from app.models import Company

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            data = self.get_request_data()

            # Validações obrigatórias
            if not data.get("name"):
                self.send_error("Campo 'name' é obrigatório", 400); return
            if not data.get("payroll_prefix"):
                self.send_error("Campo 'payroll_prefix' é obrigatório", 400); return

            # Verificar prefixo duplicado
            existing = db.query(Company).filter(
                Company.payroll_prefix == data["payroll_prefix"]
            ).first()
            if existing:
                self.send_error(
                    f"Prefixo '{data['payroll_prefix']}' já pertence à empresa '{existing.name}'", 400
                ); return

            company = Company(
                name=data["name"],
                trade_name=data.get("trade_name"),
                cnpj=data.get("cnpj"),
                payroll_prefix=data["payroll_prefix"],
                address=data.get("address"),
                phone=data.get("phone"),
                email=data.get("email"),
                is_active=data.get("is_active", True),
                notes=data.get("notes"),
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print(f"✅ Empresa criada: {company.name} (prefixo {company.payroll_prefix})")
            self.send_json_response(_company_to_dict(company), 201)
        except Exception as e:
            db.rollback()
            import traceback; traceback.print_exc()
            self.send_error(f"Erro ao criar empresa: {str(e)}", 500)
        finally:
            db.close()

    # ── PUT /api/v1/companies/<id> ────────────────────────────────────────
    def handle_update(self, company_id: int):
        from app.models import Company

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                self.send_error("Empresa não encontrada", 404); return

            data = self.get_request_data()
            updatable = ["name", "trade_name", "cnpj", "payroll_prefix",
                         "address", "phone", "email", "is_active", "notes"]
            for field in updatable:
                if field in data:
                    setattr(company, field, data[field])

            db.commit()
            db.refresh(company)
            print(f"✅ Empresa atualizada: {company.name}")
            self.send_json_response(_company_to_dict(company))
        except Exception as e:
            db.rollback()
            self.send_error(f"Erro ao atualizar empresa: {str(e)}", 500)
        finally:
            db.close()

    # ── DELETE /api/v1/companies/<id> ─────────────────────────────────────
    def handle_delete(self, company_id: int):
        from app.models import Company

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return
            if not user.is_admin:
                self.send_error("Apenas administradores podem remover empresas", 403); return

            company = db.query(Company).filter(Company.id == company_id).first()
            if not company:
                self.send_error("Empresa não encontrada", 404); return

            # Soft-delete: apenas desativa
            company.is_active = False
            db.commit()
            print(f"🗑️ Empresa desativada: {company.name}")
            self.send_success(f"Empresa '{company.name}' desativada com sucesso")
        except Exception as e:
            db.rollback()
            self.send_error(f"Erro ao remover empresa: {str(e)}", 500)
        finally:
            db.close()
