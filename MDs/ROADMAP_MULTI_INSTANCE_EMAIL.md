# 🚀 Plano de Implementação - Melhorias Sistema de Envio v2.0

**Data:** 19 de dezembro de 2025  
**Objetivo:** Escalar envios com múltiplas instâncias WhatsApp e adicionar canal Email

---

## 📊 Visão Geral das Melhorias

### 1️⃣ Sistema Multi-Instância WhatsApp
**Problema Atual:**
- 1 número WhatsApp = 1 fila de envio
- Delays longos (5-15min) = envios muito demorados
- 100 holerites = ~22 horas

**Solução:**
- Múltiplas instâncias WhatsApp (2-5 números)
- Balanceamento de carga (round-robin)
- 100 holerites com 3 números = ~7-8 horas

### 2️⃣ Sistema de Envio por Email
**Problema Atual:**
- 100% dependência do WhatsApp
- Risco de softban crítico
- Sem alternativa de envio

**Solução:**
- Email como canal complementar
- Fallback automático (WhatsApp falhou → Email)
- Preferência do colaborador (alguns preferem email)
- Reduz carga no WhatsApp

---

## 🎯 Fase 1: Sistema Multi-Instância WhatsApp

### Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────┐
│                  GERENCIADOR DE INSTÂNCIAS              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Instância 1: +55 11 99999-0001 [ATIVA] ✅             │
│  ├─ Status: Conectada                                   │
│  ├─ QR Code: [Gerar] [Reconectar]                      │
│  ├─ Última atividade: há 2 minutos                     │
│  └─ Envios hoje: 45                                     │
│                                                         │
│  Instância 2: +55 11 99999-0002 [ATIVA] ✅             │
│  ├─ Status: Conectada                                   │
│  ├─ QR Code: [Gerar] [Reconectar]                      │
│  ├─ Última atividade: há 1 minuto                      │
│  └─ Envios hoje: 48                                     │
│                                                         │
│  Instância 3: +55 11 99999-0003 [OFFLINE] ❌           │
│  ├─ Status: Desconectada                               │
│  ├─ QR Code: [Gerar] [Reconectar]                      │
│  ├─ Última atividade: há 3 horas                       │
│  └─ Envios hoje: 0                                      │
│                                                         │
│  [+ Adicionar Nova Instância]                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Estratégia: ⚙️ Round-Robin                            │
│  Instâncias Ativas: 2 de 3                             │
│  Total de Envios Hoje: 93                              │
└─────────────────────────────────────────────────────────┘
```

### 1.1 Banco de Dados - Nova Tabela

```sql
CREATE TABLE whatsapp_instances (
    id SERIAL PRIMARY KEY,
    instance_name VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'disconnected', -- connected, disconnected, error
    qr_code TEXT,  -- Base64 do QR Code (temporário)
    qr_code_expires_at TIMESTAMP,
    evolution_instance_name VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 1,  -- Para priorização
    daily_send_limit INTEGER DEFAULT 200,  -- Limite diário
    sends_today INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    metadata JSONB  -- Config adicional
);

-- Índices
CREATE INDEX idx_instances_status ON whatsapp_instances(status);
CREATE INDEX idx_instances_active ON whatsapp_instances(is_active);
CREATE INDEX idx_instances_evolution ON whatsapp_instances(evolution_instance_name);

-- Resetar contador diário (executar 1x por dia)
CREATE OR REPLACE FUNCTION reset_daily_sends()
RETURNS void AS $$
BEGIN
    UPDATE whatsapp_instances SET sends_today = 0;
END;
$$ LANGUAGE plpgsql;
```

### 1.2 Backend - Novos Modelos

**Arquivo:** `backend/app/models/whatsapp_instance.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin

class WhatsAppInstance(Base, TimestampMixin):
    __tablename__ = 'whatsapp_instances'
    
    id = Column(Integer, primary_key=True)
    instance_name = Column(String(100), unique=True, nullable=False)
    phone_number = Column(String(20))
    status = Column(String(20), default='disconnected')  # connected, disconnected, error
    qr_code = Column(Text)  # Base64 temporário
    qr_code_expires_at = Column(DateTime)
    evolution_instance_name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=1)
    daily_send_limit = Column(Integer, default=200)
    sends_today = Column(Integer, default=0)
    last_activity_at = Column(DateTime)
    created_by = Column(Integer, ForeignKey('users.id'))
    metadata = Column(JSON)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    @property
    def is_available(self) -> bool:
        """Instância está disponível para envio?"""
        return (
            self.is_active and 
            self.status == 'connected' and 
            self.sends_today < self.daily_send_limit
        )
    
    @property
    def remaining_sends(self) -> int:
        """Quantos envios restam hoje?"""
        return max(0, self.daily_send_limit - self.sends_today)
    
    def increment_sends(self):
        """Incrementar contador de envios"""
        self.sends_today += 1
        self.last_activity_at = datetime.now()
```

### 1.3 Backend - Serviço de Gerenciamento

**Arquivo:** `backend/app/services/instance_manager.py`

```python
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from ..models.whatsapp_instance import WhatsAppInstance
from .evolution_api import EvolutionAPIService

logger = logging.getLogger(__name__)

class InstanceManager:
    """Gerenciador de instâncias WhatsApp"""
    
    def __init__(self):
        self.current_instance_index = 0
    
    def get_all_instances(self, db: Session) -> List[WhatsAppInstance]:
        """Listar todas as instâncias"""
        return db.query(WhatsAppInstance).order_by(
            WhatsAppInstance.priority.desc(),
            WhatsAppInstance.id
        ).all()
    
    def get_active_instances(self, db: Session) -> List[WhatsAppInstance]:
        """Listar instâncias ativas e conectadas"""
        return db.query(WhatsAppInstance).filter(
            WhatsAppInstance.is_active == True,
            WhatsAppInstance.status == 'connected'
        ).order_by(
            WhatsAppInstance.priority.desc()
        ).all()
    
    def get_available_instances(self, db: Session) -> List[WhatsAppInstance]:
        """Instâncias disponíveis para envio (com capacidade)"""
        instances = self.get_active_instances(db)
        return [inst for inst in instances if inst.is_available]
    
    def get_next_instance(self, db: Session) -> Optional[WhatsAppInstance]:
        """
        Obter próxima instância disponível (Round-Robin)
        
        Estratégia:
        1. Listar instâncias disponíveis
        2. Usar round-robin para distribuir carga
        3. Se todas estouraram limite, retornar None
        """
        available = self.get_available_instances(db)
        
        if not available:
            logger.warning("Nenhuma instância disponível para envio!")
            return None
        
        # Round-robin
        instance = available[self.current_instance_index % len(available)]
        self.current_instance_index += 1
        
        logger.info(f"Selecionada instância: {instance.instance_name} "
                   f"({instance.remaining_sends} envios restantes)")
        
        return instance
    
    def create_instance(
        self,
        db: Session,
        instance_name: str,
        evolution_instance_name: str,
        phone_number: Optional[str] = None,
        daily_limit: int = 200,
        user_id: Optional[int] = None
    ) -> WhatsAppInstance:
        """Criar nova instância"""
        instance = WhatsAppInstance(
            instance_name=instance_name,
            evolution_instance_name=evolution_instance_name,
            phone_number=phone_number,
            daily_send_limit=daily_limit,
            created_by=user_id
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)
        
        logger.info(f"Instância criada: {instance_name}")
        return instance
    
    async def generate_qr_code(
        self,
        db: Session,
        instance_id: int
    ) -> Dict[str, Any]:
        """
        Gerar QR Code para conectar instância
        
        Fluxo:
        1. Obter instância
        2. Chamar Evolution API para gerar QR
        3. Salvar QR em base64 (temporário, 5min)
        4. Retornar QR para frontend exibir
        """
        instance = db.query(WhatsAppInstance).filter(
            WhatsAppInstance.id == instance_id
        ).first()
        
        if not instance:
            return {"success": False, "message": "Instância não encontrada"}
        
        try:
            # Chamar Evolution API
            evolution = EvolutionAPIService()
            
            # Endpoint: POST /instance/connect/{instance_name}
            # Retorna: { base64: "...", code: "..." }
            result = await evolution.connect_instance(instance.evolution_instance_name)
            
            if result.get('success'):
                qr_base64 = result.get('qr_code')
                
                # Salvar QR temporário (expira em 5 minutos)
                instance.qr_code = qr_base64
                instance.qr_code_expires_at = datetime.now() + timedelta(minutes=5)
                instance.status = 'connecting'
                db.commit()
                
                logger.info(f"QR Code gerado para {instance.instance_name}")
                
                return {
                    "success": True,
                    "qr_code": qr_base64,
                    "expires_at": instance.qr_code_expires_at.isoformat(),
                    "message": "Escaneie o QR Code no WhatsApp"
                }
            else:
                return {
                    "success": False,
                    "message": result.get('message', 'Erro ao gerar QR Code')
                }
                
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code: {e}")
            return {"success": False, "message": str(e)}
    
    async def check_instance_status(
        self,
        db: Session,
        instance_id: int
    ) -> Dict[str, Any]:
        """Verificar status da instância na Evolution API"""
        instance = db.query(WhatsAppInstance).filter(
            WhatsAppInstance.id == instance_id
        ).first()
        
        if not instance:
            return {"success": False, "message": "Instância não encontrada"}
        
        try:
            evolution = EvolutionAPIService()
            is_connected = await evolution.check_instance_status_by_name(
                instance.evolution_instance_name
            )
            
            # Atualizar status no banco
            old_status = instance.status
            instance.status = 'connected' if is_connected else 'disconnected'
            
            if is_connected:
                instance.last_activity_at = datetime.now()
                # Limpar QR Code antigo
                instance.qr_code = None
                instance.qr_code_expires_at = None
            
            db.commit()
            
            if old_status != instance.status:
                logger.info(f"Status de {instance.instance_name}: {old_status} → {instance.status}")
            
            return {
                "success": True,
                "status": instance.status,
                "is_connected": is_connected
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar status: {e}")
            instance.status = 'error'
            db.commit()
            return {"success": False, "message": str(e)}
    
    def reset_daily_counters(self, db: Session):
        """Resetar contadores diários (executar 1x por dia via cron)"""
        db.query(WhatsAppInstance).update({"sends_today": 0})
        db.commit()
        logger.info("Contadores diários resetados")
```

### 1.4 Backend - API Routes

**Arquivo:** `backend/app/routes/instances.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..models.base import get_db
from ..models.whatsapp_instance import WhatsAppInstance
from ..schemas.instance import (
    InstanceCreate, InstanceResponse, InstanceUpdate,
    QRCodeResponse, InstanceStatusResponse
)
from ..services.instance_manager import InstanceManager
from ..core.auth import get_current_user, require_permission

router = APIRouter(prefix="/api/v1/instances", tags=["WhatsApp Instances"])

@router.get("/", response_model=List[InstanceResponse])
async def list_instances(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Listar todas as instâncias WhatsApp"""
    manager = InstanceManager()
    instances = manager.get_all_instances(db)
    return instances

@router.get("/active", response_model=List[InstanceResponse])
async def list_active_instances(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Listar instâncias ativas"""
    manager = InstanceManager()
    instances = manager.get_active_instances(db)
    return instances

@router.post("/", response_model=InstanceResponse)
async def create_instance(
    data: InstanceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin"))
):
    """Criar nova instância WhatsApp"""
    manager = InstanceManager()
    
    try:
        instance = manager.create_instance(
            db=db,
            instance_name=data.instance_name,
            evolution_instance_name=data.evolution_instance_name,
            phone_number=data.phone_number,
            daily_limit=data.daily_send_limit or 200,
            user_id=current_user.id
        )
        return instance
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{instance_id}/qr-code", response_model=QRCodeResponse)
async def generate_qr_code(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin"))
):
    """Gerar QR Code para conectar instância"""
    manager = InstanceManager()
    result = await manager.generate_qr_code(db, instance_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('message'))
    
    return result

@router.get("/{instance_id}/status", response_model=InstanceStatusResponse)
async def check_instance_status(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Verificar status da instância"""
    manager = InstanceManager()
    result = await manager.check_instance_status(db, instance_id)
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('message'))
    
    return result

@router.patch("/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: int,
    data: InstanceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin"))
):
    """Atualizar configurações da instância"""
    instance = db.query(WhatsAppInstance).filter(
        WhatsAppInstance.id == instance_id
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instância não encontrada")
    
    # Atualizar campos
    if data.is_active is not None:
        instance.is_active = data.is_active
    if data.priority is not None:
        instance.priority = data.priority
    if data.daily_send_limit is not None:
        instance.daily_send_limit = data.daily_send_limit
    
    db.commit()
    db.refresh(instance)
    
    return instance

@router.delete("/{instance_id}")
async def delete_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_permission("admin"))
):
    """Deletar instância"""
    instance = db.query(WhatsAppInstance).filter(
        WhatsAppInstance.id == instance_id
    ).first()
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instância não encontrada")
    
    db.delete(instance)
    db.commit()
    
    return {"success": True, "message": "Instância removida"}
```

### 1.5 Backend - Schemas Pydantic

**Arquivo:** `backend/app/schemas/instance.py`

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InstanceCreate(BaseModel):
    instance_name: str = Field(..., description="Nome amigável da instância")
    evolution_instance_name: str = Field(..., description="Nome na Evolution API")
    phone_number: Optional[str] = Field(None, description="Número do WhatsApp")
    daily_send_limit: Optional[int] = Field(200, description="Limite diário de envios")

class InstanceUpdate(BaseModel):
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    daily_send_limit: Optional[int] = None

class InstanceResponse(BaseModel):
    id: int
    instance_name: str
    phone_number: Optional[str]
    status: str
    evolution_instance_name: str
    is_active: bool
    priority: int
    daily_send_limit: int
    sends_today: int
    remaining_sends: int
    last_activity_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class QRCodeResponse(BaseModel):
    success: bool
    qr_code: Optional[str] = None
    expires_at: Optional[str] = None
    message: str

class InstanceStatusResponse(BaseModel):
    success: bool
    status: str
    is_connected: bool
    message: Optional[str] = None
```

### 1.6 Frontend - Página de Gerenciamento

**Arquivo:** `frontend/src/pages/InstanceManagement.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'react-hot-toast';

export default function InstanceManagement() {
  const [instances, setInstances] = useState([]);
  const [showQRModal, setShowQRModal] = useState(false);
  const [currentQR, setCurrentQR] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadInstances();
    // Verificar status a cada 30 segundos
    const interval = setInterval(loadInstances, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadInstances = async () => {
    try {
      const response = await api.get('/instances');
      setInstances(response.data);
    } catch (error) {
      console.error('Erro ao carregar instâncias:', error);
    }
  };

  const handleGenerateQR = async (instanceId) => {
    setLoading(true);
    try {
      const response = await api.post(`/instances/${instanceId}/qr-code`);
      setCurrentQR(response.data);
      setShowQRModal(true);
      
      // Verificar conexão a cada 5 segundos
      const checkInterval = setInterval(async () => {
        const status = await api.get(`/instances/${instanceId}/status`);
        if (status.data.is_connected) {
          clearInterval(checkInterval);
          setShowQRModal(false);
          toast.success('Instância conectada com sucesso!');
          loadInstances();
        }
      }, 5000);
      
      // Timeout de 5 minutos
      setTimeout(() => {
        clearInterval(checkInterval);
        if (showQRModal) {
          setShowQRModal(false);
          toast.error('QR Code expirado. Tente novamente.');
        }
      }, 300000);
      
    } catch (error) {
      toast.error('Erro ao gerar QR Code');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (instanceId, currentStatus) => {
    try {
      await api.patch(`/instances/${instanceId}`, {
        is_active: !currentStatus
      });
      toast.success('Status atualizado!');
      loadInstances();
    } catch (error) {
      toast.error('Erro ao atualizar status');
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Gerenciamento de Instâncias WhatsApp</h1>
        <button 
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          onClick={() => {/* Modal criar nova instância */}}
        >
          + Nova Instância
        </button>
      </div>

      <div className="grid gap-4">
        {instances.map(instance => (
          <div key={instance.id} className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold">{instance.instance_name}</h3>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    instance.status === 'connected' 
                      ? 'bg-green-100 text-green-800'
                      : instance.status === 'connecting'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {instance.status === 'connected' ? '✅ Conectada' :
                     instance.status === 'connecting' ? '🔄 Conectando...' :
                     '❌ Desconectada'}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                  <div>
                    <strong>Telefone:</strong> {instance.phone_number || 'Não informado'}
                  </div>
                  <div>
                    <strong>Última atividade:</strong>{' '}
                    {instance.last_activity_at 
                      ? new Date(instance.last_activity_at).toLocaleString('pt-BR')
                      : 'Nunca'}
                  </div>
                  <div>
                    <strong>Envios hoje:</strong>{' '}
                    <span className={instance.remaining_sends < 50 ? 'text-orange-600 font-semibold' : ''}>
                      {instance.sends_today} / {instance.daily_send_limit}
                    </span>
                  </div>
                  <div>
                    <strong>Disponíveis:</strong>{' '}
                    <span className="font-semibold text-blue-600">
                      {instance.remaining_sends}
                    </span>
                  </div>
                </div>

                {instance.remaining_sends < 50 && instance.is_active && (
                  <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded text-sm text-orange-800">
                    ⚠️ Atenção: Menos de 50 envios restantes hoje
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2">
                {instance.status !== 'connected' && (
                  <button
                    onClick={() => handleGenerateQR(instance.id)}
                    disabled={loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    📱 Gerar QR Code
                  </button>
                )}
                
                <button
                  onClick={() => handleToggleActive(instance.id, instance.is_active)}
                  className={`px-4 py-2 rounded ${
                    instance.is_active
                      ? 'bg-red-100 text-red-700 hover:bg-red-200'
                      : 'bg-green-100 text-green-700 hover:bg-green-200'
                  }`}
                >
                  {instance.is_active ? 'Desativar' : 'Ativar'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal QR Code */}
      {showQRModal && currentQR && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md">
            <h2 className="text-xl font-bold mb-4">Escaneie o QR Code</h2>
            <p className="text-gray-600 mb-4">
              Abra o WhatsApp no celular e escaneie este código
            </p>
            <div className="flex justify-center mb-4">
              <img 
                src={`data:image/png;base64,${currentQR.qr_code}`}
                alt="QR Code"
                className="w-64 h-64"
              />
            </div>
            <p className="text-sm text-gray-500 text-center">
              QR Code expira em 5 minutos
            </p>
            <button
              onClick={() => setShowQRModal(false)}
              className="mt-4 w-full bg-gray-300 text-gray-700 py-2 rounded hover:bg-gray-400"
            >
              Fechar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 1.7 Integração com Processo de Envio

**Modificação em:** `backend/main_legacy.py` - função `process_bulk_send_in_background`

```python
# No início da função, após criar fila:

# 🔄 OBTER INSTÂNCIAS DISPONÍVEIS
from app.services.instance_manager import InstanceManager

instance_manager = InstanceManager()
available_instances = instance_manager.get_available_instances(db)

if not available_instances:
    job.status = 'failed'
    job.error_message = 'Nenhuma instância WhatsApp disponível'
    job.end_time = datetime.now()
    print(f"❌ [JOB {job_id[:8]}] Sem instâncias disponíveis!")
    return

print(f"📱 [JOB {job_id[:8]}] {len(available_instances)} instância(s) disponível(is)")
for inst in available_instances:
    print(f"   • {inst.instance_name}: {inst.remaining_sends} envios restantes")

# No loop de envio, ANTES de enviar cada holerite:

# 🎯 SELECIONAR PRÓXIMA INSTÂNCIA (ROUND-ROBIN)
selected_instance = instance_manager.get_next_instance(db)

if not selected_instance:
    # Todas as instâncias atingiram o limite diário
    print(f"⚠️ [JOB {job_id[:8]}] Todas as instâncias atingiram limite diário!")
    job.status = 'paused'
    job.error_message = 'Limite diário de envios atingido em todas as instâncias'
    break

print(f"📱 Usando instância: {selected_instance.instance_name}")

# Criar Evolution service com instância específica
evolution_service = EvolutionAPIService(
    instance_name=selected_instance.evolution_instance_name
)

# ... enviar mensagem normalmente ...

# Após envio bem-sucedido:
if result['success']:
    # Incrementar contador da instância
    selected_instance.increment_sends()
    db.commit()
    print(f"📊 {selected_instance.instance_name}: {selected_instance.sends_today} envios hoje")
```

---

## 📧 Fase 2: Sistema de Envio por Email

### Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────┐
│              CONFIGURAÇÃO DE EMAIL                      │
├─────────────────────────────────────────────────────────┤
│  Provedor: ⚙️ SMTP / Gmail / SendGrid / AWS SES        │
│  Host: smtp.gmail.com                                   │
│  Porta: 587                                             │
│  Email remetente: rh@empresa.com.br                     │
│  Nome exibido: RH - Empresa XYZ                         │
│  Autenticação: [•••••••••]                             │
│  [Testar Conexão] [Salvar]                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│          PREFERÊNCIAS DO COLABORADOR                    │
├─────────────────────────────────────────────────────────┤
│  Nome: João Silva                                       │
│  Email: joao.silva@empresa.com.br                       │
│                                                         │
│  Canal preferencial de envio:                          │
│  ○ WhatsApp apenas                                      │
│  ○ Email apenas                                         │
│  ● Ambos (WhatsApp + Email)                            │
│  ○ Email com fallback para WhatsApp                    │
│                                                         │
│  ✓ Receber confirmação por email após envio WhatsApp   │
└─────────────────────────────────────────────────────────┘
```

### 2.1 Banco de Dados - Modificações

```sql
-- Adicionar campos em employees
ALTER TABLE employees ADD COLUMN preferred_channel VARCHAR(20) DEFAULT 'whatsapp';
-- valores: 'whatsapp', 'email', 'both', 'email_fallback'

ALTER TABLE employees ADD COLUMN receive_email_confirmation BOOLEAN DEFAULT FALSE;

-- Nova tabela para configuração de email
CREATE TABLE email_config (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,  -- smtp, gmail, sendgrid, ses
    smtp_host VARCHAR(255),
    smtp_port INTEGER,
    smtp_user VARCHAR(255),
    smtp_password TEXT,  -- Encriptado
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    daily_send_limit INTEGER DEFAULT 500,
    sends_today INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Adicionar tracking de envios por email
ALTER TABLE payroll_sends ADD COLUMN channel VARCHAR(20) DEFAULT 'whatsapp';
-- valores: 'whatsapp', 'email', 'both'

ALTER TABLE payroll_sends ADD COLUMN email_sent_at TIMESTAMP;
ALTER TABLE payroll_sends ADD COLUMN email_opened_at TIMESTAMP;
```

### 2.2 Backend - Serviço de Email

**Arquivo:** `backend/app/services/email_service.py`

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailService:
    """Serviço para envio de emails"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user')
        self.smtp_password = config.get('smtp_password')
        self.sender_email = config.get('sender_email')
        self.sender_name = config.get('sender_name', 'RH')
    
    def send_payroll(
        self,
        to_email: str,
        employee_name: str,
        file_path: str,
        month_year: str
    ) -> Dict[str, Any]:
        """
        Enviar holerite por email
        
        Args:
            to_email: Email do destinatário
            employee_name: Nome do colaborador
            file_path: Caminho do PDF
            month_year: Referência (ex: "outubro de 2025")
        
        Returns:
            Dict com success e message
        """
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.sender_name, self.sender_email))
            msg['To'] = to_email
            msg['Subject'] = f'Holerite - {month_year}'
            
            # Corpo do email (HTML)
            first_name = employee_name.split()[0]
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #2563eb;">Holerite - {month_year}</h2>
                  
                  <p>Olá {first_name},</p>
                  
                  <p>Segue em anexo seu holerite referente a <strong>{month_year}</strong>.</p>
                  
                  <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>🔒 Senha do arquivo:</strong></p>
                    <p style="margin: 5px 0 0 0; font-size: 16px;">
                      Os <strong>4 primeiros dígitos do seu CPF</strong>
                    </p>
                  </div>
                  
                  <p>Em caso de dúvidas, entre em contato com o RH.</p>
                  
                  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                  
                  <p style="font-size: 12px; color: #6b7280;">
                    Esta é uma mensagem automática. Por favor, não responda este email.
                  </p>
                </div>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Anexar PDF
            if Path(file_path).exists():
                with open(file_path, 'rb') as f:
                    pdf = MIMEApplication(f.read(), _subtype='pdf')
                    pdf.add_header(
                        'Content-Disposition',
                        'attachment',
                        filename=Path(file_path).name
                    )
                    msg.attach(pdf)
            else:
                return {"success": False, "message": "Arquivo não encontrado"}
            
            # Enviar via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email enviado com sucesso para {to_email}")
            return {
                "success": True,
                "message": f"Email enviado para {to_email}"
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def send_notification(
        self,
        to_email: str,
        employee_name: str,
        whatsapp_sent: bool = True
    ) -> Dict[str, Any]:
        """
        Enviar email de confirmação após envio via WhatsApp
        
        Args:
            to_email: Email do destinatário
            employee_name: Nome do colaborador
            whatsapp_sent: Se foi enviado via WhatsApp
        
        Returns:
            Dict com success e message
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.sender_name, self.sender_email))
            msg['To'] = to_email
            msg['Subject'] = 'Confirmação de Envio - Holerite'
            
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h2 style="color: #10b981;">✅ Holerite Enviado</h2>
                  <p>Olá {employee_name.split()[0]},</p>
                  <p>Confirmamos o envio do seu holerite via <strong>WhatsApp</strong>.</p>
                  <p>Caso não tenha recebido, entre em contato com o RH.</p>
                </div>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return {"success": True, "message": "Notificação enviada"}
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {e}")
            return {"success": False, "message": str(e)}
```

### 2.3 Integração com Processo de Envio

**Modificação em:** `backend/main_legacy.py`

```python
# Adicionar no início da função:
from app.services.email_service import EmailService
from app.models.email_config import EmailConfig

# Carregar configuração de email
email_config = db.query(EmailConfig).filter(EmailConfig.is_active == True).first()
email_service = None
if email_config:
    email_service = EmailService({
        'smtp_host': email_config.smtp_host,
        'smtp_port': email_config.smtp_port,
        'smtp_user': email_config.smtp_user,
        'smtp_password': email_config.smtp_password,  # Descriptografar
        'sender_email': email_config.sender_email,
        'sender_name': email_config.sender_name
    })

# No loop de envio, verificar preferência do colaborador:

employee_email = employee.get('email')
preferred_channel = employee.get('preferred_channel', 'whatsapp')
receive_confirmation = employee.get('receive_email_confirmation', False)

# Lógica de envio baseada em preferência:
if preferred_channel == 'email':
    # Enviar apenas por email
    if email_service and employee_email:
        result = email_service.send_payroll(
            to_email=employee_email,
            employee_name=employee_name,
            file_path=file_path,
            month_year=month_year
        )
    else:
        result = {"success": False, "message": "Email não configurado"}

elif preferred_channel == 'both':
    # Enviar por WhatsApp E Email
    whatsapp_result = loop.run_until_complete(
        evolution_service.send_payroll_message(...)
    )
    
    if email_service and employee_email:
        email_result = email_service.send_payroll(...)
    
    result = {
        "success": whatsapp_result['success'] or email_result['success'],
        "message": f"WhatsApp: {whatsapp_result['message']} | Email: {email_result['message']}"
    }

elif preferred_channel == 'email_fallback':
    # Tentar WhatsApp primeiro, se falhar tentar Email
    whatsapp_result = loop.run_until_complete(
        evolution_service.send_payroll_message(...)
    )
    
    if not whatsapp_result['success'] and email_service and employee_email:
        print(f"⚠️ WhatsApp falhou, tentando email...")
        result = email_service.send_payroll(...)
    else:
        result = whatsapp_result

else:  # 'whatsapp' (padrão)
    # Enviar apenas por WhatsApp
    result = loop.run_until_complete(
        evolution_service.send_payroll_message(...)
    )
    
    # Se enviou com sucesso E colaborador quer confirmação por email
    if result['success'] and receive_confirmation and email_service and employee_email:
        email_service.send_notification(
            to_email=employee_email,
            employee_name=employee_name
        )
```

---

## 📊 Fase 3: Estatísticas e Monitoramento

### Dashboard de Envios

```
┌─────────────────────────────────────────────────────────┐
│              DASHBOARD DE ENVIOS                        │
├─────────────────────────────────────────────────────────┤
│  Hoje: 19/12/2025                                       │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ WhatsApp    │  │ Email       │  │ Total       │    │
│  │ 156 envios  │  │ 34 envios   │  │ 190 envios  │    │
│  │ 3 falhas    │  │ 2 falhas    │  │ 5 falhas    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                         │
│  Instâncias WhatsApp:                                   │
│  ┌─────────────────────────────────────────────┐       │
│  │ 📱 RH Principal: 89/200 (45%)  ██████░░░░░  │       │
│  │ 📱 RH Backup:    67/200 (34%)  █████░░░░░░  │       │
│  │ 📱 Financeiro:   0/200  (0%)   ░░░░░░░░░░  │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  Tempo médio de envio: 8min 32s                        │
│  Próxima pausa estratégica: em 12 envios               │
│                                                         │
│  [Ver Histórico] [Exportar Relatório]                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Plano de Implementação Detalhado

### Sprint 1: Multi-Instância WhatsApp (5-7 dias)

**Dia 1-2: Backend Básico**
- [ ] Criar tabela `whatsapp_instances`
- [ ] Criar modelo `WhatsAppInstance`
- [ ] Criar `InstanceManager` service
- [ ] Implementar round-robin básico

**Dia 3-4: API e Evolution Integration**
- [ ] Criar rotas `/api/v1/instances`
- [ ] Implementar geração de QR Code
- [ ] Implementar verificação de status
- [ ] Testes com Evolution API 2.3.7

**Dia 5-6: Frontend**
- [ ] Criar página `InstanceManagement.jsx`
- [ ] Implementar display de QR Code
- [ ] Implementar gerenciamento de instâncias
- [ ] Polling de status

**Dia 7: Integração e Testes**
- [ ] Integrar com `process_bulk_send_in_background`
- [ ] Testes com 2-3 instâncias simultâneas
- [ ] Validar round-robin funcionando
- [ ] Deploy

### Sprint 2: Sistema de Email (4-5 dias)

**Dia 1-2: Backend**
- [ ] Criar tabela `email_config`
- [ ] Criar `EmailService`
- [ ] Implementar envio de holerite por email
- [ ] Implementar envio de confirmação

**Dia 3: Integração**
- [ ] Adicionar campo `preferred_channel` em employees
- [ ] Modificar lógica de envio (WhatsApp/Email/Both)
- [ ] Implementar fallback

**Dia 4-5: Frontend e Testes**
- [ ] Página de configuração de email
- [ ] Campo de preferência no cadastro de colaborador
- [ ] Testes de envio
- [ ] Deploy

### Sprint 3: Melhorias e Monitoramento (3-4 dias)

**Dia 1-2: Dashboard**
- [ ] Criar página de estatísticas
- [ ] Gráficos de envios por canal
- [ ] Monitoramento de instâncias em tempo real

**Dia 3-4: Otimizações**
- [ ] Job para resetar contadores diários
- [ ] Alertas quando instância atinge limite
- [ ] Relatórios exportáveis
- [ ] Documentação completa

---

## 📈 Benefícios Esperados

### Tempo de Envio (100 holerites)

**Cenário Atual:**
- 1 instância WhatsApp
- Delays: 5-10 minutos
- **Tempo total: ~22 horas**

**Com 3 Instâncias:**
- 3 instâncias WhatsApp (round-robin)
- Delays: 5-10 minutos (mantidos)
- **Tempo total: ~7-8 horas** ✅ (redução de 65%)

**Com 3 Instâncias + Email (50/50):**
- 50 por WhatsApp (3 instâncias)
- 50 por Email (sem delays)
- **Tempo total: ~4 horas** ✅ (redução de 82%)

### Confiabilidade

- ✅ **Redundância:** Se 1 instância cai, outras continuam
- ✅ **Fallback:** WhatsApp falhou → tenta Email
- ✅ **Limite distribuído:** 200/instância = 600 envios/dia total
- ✅ **Menos risco de softban:** Carga distribuída

### Experiência do Usuário

- ✅ **Flexibilidade:** Colaborador escolhe canal preferido
- ✅ **Confirmação:** Email de notificação opcional
- ✅ **Visibilidade:** Dashboard mostra progresso de cada instância

---

## ⚠️ Considerações Importantes

### Custos

**WhatsApp (Evolution API):**
- Precisa de múltiplos números
- ~R$ 20-50/mês por número (chip celular)
- Servidor Evolution API (já tem)

**Email (SMTP):**
- Gmail: Grátis até 500 emails/dia
- SendGrid: Grátis até 100 emails/dia, depois ~$15/mês
- AWS SES: ~$0.10 por 1000 emails

### Infraestrutura

**Banco de Dados:**
- +2 tabelas: `whatsapp_instances`, `email_config`
- Relativamente leve

**Backend:**
- +3 serviços: `InstanceManager`, `EmailService`, tracking
- Sem impacto significativo

**Frontend:**
- +2 páginas: gerenciamento de instâncias, config de email
- +1 campo: preferência do colaborador

---

## 🎯 Recomendação de Priorização

### Fase 1 (AGORA): ✅ Presença Removida
- [x] Remover envio de presença
- Impacto imediato: Fix "Aguardando Mensagem" no iPhone

### Fase 2 (PRÓXIMA): Multi-Instância WhatsApp
- Maior impacto na velocidade de envio
- Reduz tempo de 22h → 7h (3 instâncias)
- Reduz risco de softban

### Fase 3 (DEPOIS): Sistema de Email
- Complementa WhatsApp
- Fallback confiável
- Reduz dependência total de WhatsApp

### Fase 4 (FUTURO): Melhorias e Monitoramento
- Dashboard avançado
- Alertas inteligentes
- Relatórios automatizados

---

**Está pronto para começar com a Fase 2 (Multi-Instância)? Ou prefere implementar Email primeiro?**
