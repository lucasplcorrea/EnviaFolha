"""
WorkLocations Router — CRUD completo para /api/v1/work-locations
"""
from .base import BaseRouter
from app.services.runtime_compat import SessionLocal


def _location_to_dict(loc) -> dict:
    return {
        "id": loc.id,
        "name": loc.name,
        "code": loc.code,
        "company_id": loc.company_id,
        "company_name": loc.company.name if loc.company else None,
        "address_street": loc.address_street,
        "address_number": loc.address_number,
        "address_complement": loc.address_complement,
        "address_neighborhood": loc.address_neighborhood,
        "address_city": loc.address_city,
        "address_state": loc.address_state,
        "address_zip": loc.address_zip,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "is_active": loc.is_active,
        "notes": loc.notes,
        "created_at": loc.created_at.isoformat() if loc.created_at else None,
        "updated_at": loc.updated_at.isoformat() if loc.updated_at else None,
        "employees_count": len(loc.employees) if loc.employees is not None else 0,
    }


class WorkLocationsRouter(BaseRouter):
    """CRUD para locais de atuação / obras"""

    # ── GET /api/v1/work-locations ────────────────────────────────────────
    def handle_list(self):
        from app.models import WorkLocation
        from sqlalchemy.orm import joinedload
        import urllib.parse

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            # Filtros opcionais via query string
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.handler.path).query)
            company_id = qs.get("company_id", [None])[0]
            active_only = qs.get("active", ["true"])[0].lower() == "true"

            q = (
                db.query(WorkLocation)
                .options(joinedload(WorkLocation.company), joinedload(WorkLocation.employees))
                .order_by(WorkLocation.name)
            )
            if company_id:
                q = q.filter(WorkLocation.company_id == int(company_id))
            if active_only:
                q = q.filter(WorkLocation.is_active == True)

            locations = q.all()
            self.send_json_response([_location_to_dict(loc) for loc in locations])
        except Exception as e:
            import traceback; traceback.print_exc()
            self.send_error(f"Erro ao listar locais: {str(e)}", 500)
        finally:
            db.close()

    # ── GET /api/v1/work-locations/<id> ──────────────────────────────────
    def handle_get(self, location_id: int):
        from app.models import WorkLocation
        from sqlalchemy.orm import joinedload

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            loc = (
                db.query(WorkLocation)
                .options(joinedload(WorkLocation.company), joinedload(WorkLocation.employees))
                .filter(WorkLocation.id == location_id)
                .first()
            )
            if not loc:
                self.send_error("Local não encontrado", 404); return
            self.send_json_response(_location_to_dict(loc))
        except Exception as e:
            self.send_error(f"Erro: {str(e)}", 500)
        finally:
            db.close()

    # ── POST /api/v1/work-locations ───────────────────────────────────────
    def handle_create(self):
        from app.models import WorkLocation

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            data = self.get_request_data()
            if not data.get("name"):
                self.send_error("Campo 'name' é obrigatório", 400); return

            loc = WorkLocation(
                name=data["name"],
                code=data.get("code"),
                company_id=data.get("company_id"),
                address_street=data.get("address_street"),
                address_number=data.get("address_number"),
                address_complement=data.get("address_complement"),
                address_neighborhood=data.get("address_neighborhood"),
                address_city=data.get("address_city"),
                address_state=data.get("address_state"),
                address_zip=data.get("address_zip"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                is_active=data.get("is_active", True),
                notes=data.get("notes"),
            )
            db.add(loc)
            db.commit()
            db.refresh(loc)
            print(f"✅ Local criado: {loc.name}")
            self.send_json_response(_location_to_dict(loc), 201)
        except Exception as e:
            db.rollback()
            import traceback; traceback.print_exc()
            self.send_error(f"Erro ao criar local: {str(e)}", 500)
        finally:
            db.close()

    # ── PUT /api/v1/work-locations/<id> ──────────────────────────────────
    def handle_update(self, location_id: int):
        from app.models import WorkLocation

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return

            loc = db.query(WorkLocation).filter(WorkLocation.id == location_id).first()
            if not loc:
                self.send_error("Local não encontrado", 404); return

            data = self.get_request_data()
            updatable = [
                "name", "code", "company_id",
                "address_street", "address_number", "address_complement",
                "address_neighborhood", "address_city", "address_state", "address_zip",
                "latitude", "longitude", "is_active", "notes",
            ]
            for field in updatable:
                if field in data:
                    setattr(loc, field, data[field])

            db.commit()
            db.refresh(loc)
            print(f"✅ Local atualizado: {loc.name}")
            self.send_json_response(_location_to_dict(loc))
        except Exception as e:
            db.rollback()
            self.send_error(f"Erro ao atualizar local: {str(e)}", 500)
        finally:
            db.close()

    # ── DELETE /api/v1/work-locations/<id> ───────────────────────────────
    def handle_delete(self, location_id: int):
        from app.models import WorkLocation

        db = SessionLocal()
        try:
            user = self.handler.get_authenticated_user(db)
            if not user:
                self.send_error("Token de acesso necessário", 401); return
            if not user.is_admin:
                self.send_error("Apenas administradores podem remover locais", 403); return

            loc = db.query(WorkLocation).filter(WorkLocation.id == location_id).first()
            if not loc:
                self.send_error("Local não encontrado", 404); return

            # Soft-delete
            loc.is_active = False
            db.commit()
            print(f"🗑️ Local desativado: {loc.name}")
            self.send_success(f"Local '{loc.name}' desativado com sucesso")
        except Exception as e:
            db.rollback()
            self.send_error(f"Erro ao remover local: {str(e)}", 500)
        finally:
            db.close()
