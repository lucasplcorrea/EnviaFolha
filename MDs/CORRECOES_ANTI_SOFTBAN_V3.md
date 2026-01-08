# 🔧 Correções Urgentes - Anti-Softban v3.0

**Objetivo:** Corrigir problemas de "Aguardando Mensagem" no iPhone e prevenir softban

---

## 📋 Checklist de Correções

### ✅ Prioridade CRÍTICA (Implementar AGORA)

- [ ] **1. Aumentar delays entre envios** (2-3min → 5-10min)
- [ ] **2. Aumentar pausas estratégicas** (10-15min → 30-60min)
- [ ] **3. Randomizar intervalo de pausas** (fixo 20 → aleatório 10-25)
- [ ] **4. Remover presença antes de documentos** (causa "Aguardando Mensagem")
- [ ] **5. Adicionar presença "available" ao final** (simular fim de digitação)
- [ ] **6. Aumentar variação dos delays** (±10s → ±50%)

### 🟡 Prioridade ALTA (Implementar em Seguida)

- [ ] **7. Aumentar timeout de envio** (60s → 120s)
- [ ] **8. Adicionar micro-pausas aleatórias** (1-5min ocasionalmente)
- [ ] **9. Melhorar retry strategy** (delays progressivos)

---

## 🛠️ Implementação das Correções

### Correção 1-6: Sistema Anti-Softban v3.0

**Arquivo:** `backend/main_legacy.py`  
**Função:** `process_bulk_send_in_background`  
**Linhas:** ~700-800

#### Código ANTES (v2.0 - Atual):
```python
# SISTEMA ANTI-SOFTBAN V2.0 (INSUFICIENTE)
if idx > 0:
    # Pausa estratégica a cada 20 envios (FIXO)
    if idx % 20 == 0:
        long_delay = round(random.uniform(600.00, 900.00), 2)  # 10-15 minutos
        print(f"🛡️ PAUSA ESTRATÉGICA - 20 ENVIOS COMPLETADOS")
        time.sleep(long_delay)
    else:
        # Delay normal: 2-3 minutos (MUITO CURTO)
        delay = round(random.uniform(120.00, 180.00), 2)
        print(f"⏳ AGUARDANDO {delay:.2f}s antes do envio #{idx+1}...")
        time.sleep(delay)

# Simular presença ANTES de enviar documento (PROBLEMA)
print(f"📝 Simulando digitação para {employee_name}...")
presence_result = loop.run_until_complete(
    evolution_service.send_presence(
        phone=phone_number,
        presence_type="composing",
        delay=5000  # 5 segundos
    )
)
if presence_result.get('success'):
    time.sleep(5.5)  # Aguardar presença

# Enviar documento
result = loop.run_until_complete(
    evolution_service.send_payroll_message(...)
)
```

#### Código DEPOIS (v3.0 - Corrigido):
```python
# ===============================================
# SISTEMA ANTI-SOFTBAN V3.0 (ULTRA-CONSERVADOR)
# ===============================================
# Baseado nas recomendações WhatsApp Business 2024-2025
# - Delays: 5-10 minutos (±50% variação)
# - Pausas: 30-60 minutos a cada 10-25 envios (aleatório)
# - Sem presença antes de documentos
# - Presença "available" ao final
# ===============================================

if idx > 0:
    # ===== PAUSA ESTRATÉGICA (ALEATÓRIA) =====
    # Sortear quantidade de envios antes da próxima pausa (10-25)
    if not hasattr(job, 'next_pause_at'):
        job.next_pause_at = random.randint(10, 25)
        print(f"🎲 Próxima pausa estratégica será após {job.next_pause_at} envios")
    
    if idx % job.next_pause_at == 0:
        # Pausa longa: 30-60 minutos (1800-3600s)
        long_delay = round(random.uniform(1800.00, 3600.00), 2)
        minutes = int(long_delay // 60)
        seconds = int(long_delay % 60)
        
        print(f"\n🛡️ [JOB {job_id[:8]}] ⏸️  PAUSA ESTRATÉGICA #{idx//job.next_pause_at}")
        print(f"🎯 {job.next_pause_at} envios completados")
        print(f"⏳ Aguardando {long_delay:.2f}s ({minutes}min {seconds}s) - Prevenção de Softban")
        print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")
        
        # Dormir em chunks para permitir verificações
        remaining = long_delay
        while remaining > 0:
            sleep_time = min(120, remaining)  # Verificar a cada 2min
            time.sleep(sleep_time)
            remaining -= sleep_time
            
            if remaining > 0:
                # Verificar Evolution API durante pausa longa
                is_online = loop.run_until_complete(check_evolution_status(evolution_service))
                if not is_online:
                    print(f"⚠️ Evolution API offline durante pausa!")
                    # Pausar job e tentar reconectar (código existente)
                    break
                print(f"   ⏳ Restam {int(remaining)}s da pausa estratégica...")
        
        print(f"✅ Pausa concluída: {datetime.now().strftime('%H:%M:%S')}\n")
        
        # Sortear próxima pausa
        job.next_pause_at = random.randint(10, 25)
        print(f"🎲 Próxima pausa será após mais {job.next_pause_at} envios")
    
    else:
        # ===== DELAY NORMAL COM ALTA VARIAÇÃO =====
        # Base: 5-10 minutos (300-600s)
        # Variação: ±50% (150-900s = 2.5-15min)
        base_delay = random.uniform(300.00, 600.00)
        variation_factor = random.uniform(0.5, 1.5)  # ±50%
        delay = round(base_delay * variation_factor, 2)
        
        # Limitar para não ultrapassar 15 minutos
        delay = min(delay, 900.00)
        
        minutes = int(delay // 60)
        seconds = int(delay % 60)
        time_str = f"{minutes}m{seconds}s"
        
        print(f"\n⏳ [JOB {job_id[:8]}] AGUARDANDO {delay:.2f}s ({time_str}) antes do envio #{idx+1}...")
        print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")
        
        # Adicionar micro-pausa aleatória (10% de chance)
        if random.random() < 0.10:
            micro_pause = round(random.uniform(60.00, 300.00), 2)  # 1-5min extra
            print(f"🎲 Micro-pausa adicional: {int(micro_pause)}s")
            delay += micro_pause
        
        time.sleep(delay)
        print(f"✅ Delay concluído: {datetime.now().strftime('%H:%M:%S')}\n")
else:
    print(f"⚡ [JOB {job_id[:8]}] Primeiro holerite - SEM DELAY")
    # Inicializar contador de pausa
    job.next_pause_at = random.randint(10, 25)
    print(f"🎲 Primeira pausa estratégica será após {job.next_pause_at} envios")

# ===== NÃO ENVIAR PRESENÇA ANTES DE DOCUMENTOS =====
# Motivo: Causa "Aguardando Mensagem" no iPhone
# Presença é útil apenas para mensagens de texto puras

# Enviar documento DIRETAMENTE
print(f"\n📄 [JOB {job_id[:8]}] [{idx + 1}/{len(selected_files)}] Enviando {filename} para {employee_name}...")
if selected_template:
    template_num = message_templates.index(selected_template) + 1
    print(f"📝 Usando Template {template_num}")

result = loop.run_until_complete(
    evolution_service.send_payroll_message(
        phone=phone_number,
        employee_name=employee_name,
        file_path=file_path,
        month_year=month_year,
        message_template=selected_template
    )
)

# ===== ENVIAR PRESENÇA "AVAILABLE" APÓS ENVIO =====
# Motivo: Simular comportamento humano (fim de digitação)
if result['success']:
    try:
        print(f"✅ [JOB {job_id[:8]}] Holerite enviado! Finalizando presença...")
        available_result = loop.run_until_complete(
            evolution_service.send_presence(
                phone=phone_number,
                presence_type="available",
                delay=1000  # 1 segundo apenas
            )
        )
        if available_result.get('success'):
            print(f"✓ Presença 'available' enviada")
    except Exception as e:
        print(f"⚠️ Erro ao enviar presença final: {e}")
        # Não falhar por causa disso
```

**Resumo das Mudanças:**
1. ✅ Delay base: `120-180s` → `300-900s` (5-15min com variação)
2. ✅ Pausa estratégica: `600-900s` → `1800-3600s` (30-60min)
3. ✅ Intervalo da pausa: `fixo 20` → `aleatório 10-25`
4. ✅ Variação: `±10s` → `±50%`
5. ✅ **REMOVIDO** presença "composing" antes de documento
6. ✅ **ADICIONADO** presença "available" após envio
7. ✅ **ADICIONADO** micro-pausas aleatórias (10% de chance)

---

### Correção 7: Aumentar Timeout

**Arquivo:** `backend/app/services/evolution_api.py`  
**Método:** `send_payroll_message`  
**Linha:** ~199

#### ANTES:
```python
response = requests.post(url, headers=self.headers, json=payload, timeout=60)
```

#### DEPOIS:
```python
# Timeout aumentado para PDFs grandes e conexões lentas (especialmente iPhone)
response = requests.post(url, headers=self.headers, json=payload, timeout=120)
```

---

### Correção 8: Adicionar Presença "available"

**Arquivo:** `backend/app/services/evolution_api.py`  
**Método:** Adicionar novo método auxiliar

```python
async def finalize_presence(self, phone: str) -> Dict[str, Any]:
    """
    Envia presença 'available' para indicar fim de interação
    Simula comportamento humano (parou de digitar/interagir)
    
    Args:
        phone: Número do telefone
    
    Returns:
        Dict com success (bool) e message (str)
    """
    try:
        return await self.send_presence(
            phone=phone,
            presence_type="available",
            delay=1000  # 1 segundo apenas
        )
    except Exception as e:
        logger.warning(f"Erro ao finalizar presença: {e}")
        return {"success": False, "message": str(e)}
```

---

### Correção 9: Melhorar Retry Strategy

**Arquivo:** `backend/app/services/evolution_api.py`  
**Método:** `send_payroll_message`  
**Linhas:** ~197-225

#### ANTES:
```python
# Tentar envio com retry
for attempt in range(3):
    try:
        response = requests.post(url, headers=self.headers, json=payload, timeout=60)
        response.raise_for_status()
        return {"success": True, "message": "..."}
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            time.sleep(60)  # FIXO
            continue
        elif attempt < 2:
            time.sleep(30)  # FIXO
            continue
```

#### DEPOIS:
```python
# Tentar envio com retry PROGRESSIVO
retry_delays = [60, 90, 120]  # Delays progressivos: 1min, 1.5min, 2min

for attempt in range(3):
    try:
        response = requests.post(url, headers=self.headers, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        message_id = result.get('key', {}).get('id', 'N/A')
        
        return {
            "success": True, 
            "message": f"Holerite enviado com sucesso. ID: {message_id}"
        }
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:  # Rate limit
            wait_time = retry_delays[attempt]
            logger.warning(f"Rate limit! Tentativa {attempt+1}/3. Aguardando {wait_time}s...")
            time.sleep(wait_time)
            continue
            
        elif e.response.status_code in [401, 404]:
            # Erros não recuperáveis
            return {"success": False, "message": f"Erro de API: {e.response.status_code}"}
            
        else:
            if attempt < 2:
                wait_time = retry_delays[attempt]
                logger.warning(f"Erro HTTP {e.response.status_code}. Tentativa {attempt+1}/3. Aguardando {wait_time}s...")
                time.sleep(wait_time)
                continue
            return {"success": False, "message": f"Erro HTTP: {e.response.status_code}"}
            
    except requests.exceptions.Timeout:
        if attempt < 2:
            wait_time = retry_delays[attempt]
            logger.warning(f"Timeout! Tentativa {attempt+1}/3. Aguardando {wait_time}s...")
            time.sleep(wait_time)
            continue
        return {"success": False, "message": "Timeout após 3 tentativas"}
        
    except Exception as e:
        if attempt < 2:
            wait_time = retry_delays[attempt]
            logger.warning(f"Erro inesperado! Tentativa {attempt+1}/3. Aguardando {wait_time}s...")
            time.sleep(wait_time)
            continue
        return {"success": False, "message": f"Erro após 3 tentativas: {str(e)}"}

return {"success": False, "message": "Falha após 3 tentativas"}
```

**Mudanças:**
- ✅ Delays progressivos: 60s → 90s → 120s
- ✅ Logs mais detalhados (tentativa X de 3)
- ✅ Timeout aumentado para 120s

---

## 🧪 Como Testar as Correções

### Teste 1: Delay Aumentado
```bash
# Iniciar envio de 5 holerites
# Observar logs:

⏳ AGUARDANDO 487.32s (8m7s) antes do envio #2...
✅ Delay concluído

⏳ AGUARDANDO 623.18s (10m23s) antes do envio #3...
✅ Delay concluído

# ✅ Esperado: delays entre 5-15 minutos (variável)
```

### Teste 2: Pausa Aleatória
```bash
# Logs devem mostrar:

🎲 Próxima pausa estratégica será após 17 envios
...
🛡️ PAUSA ESTRATÉGICA #1 - 17 envios completados
⏳ Aguardando 2341.54s (39min 1s)
✅ Pausa concluída
🎲 Próxima pausa será após mais 13 envios

# ✅ Esperado: pausas em intervalos diferentes (10-25)
```

### Teste 3: Presença "available"
```bash
# Logs devem mostrar:

✅ Holerite enviado! Finalizando presença...
✓ Presença 'available' enviada

# ✅ Esperado: presença enviada APÓS documento (não antes)
```

### Teste 4: iPhone "Aguardando Mensagem"
```bash
# Enviar holerite para iPhone
# Verificar no dispositivo:

✅ ANTES: "Aguardando Mensagem" (não carrega)
✅ DEPOIS: Mensagem chega normalmente

# Motivo: presença removida antes de documento
```

---

## 📊 Comparação: v2.0 vs v3.0

| Métrica | v2.0 (Atual) | v3.0 (Corrigido) | Melhoria |
|---------|--------------|------------------|----------|
| **Delay mínimo** | 2 min | 5 min | +150% |
| **Delay máximo** | 3 min | 15 min | +400% |
| **Pausa estratégica** | 10-15 min | 30-60 min | +300% |
| **Intervalo de pausa** | Fixo (20) | Aleatório (10-25) | Imprevisível |
| **Variação** | ±10s | ±50% | +400% |
| **Presença antes doc** | ✅ Sim | ❌ Não | Fix iPhone |
| **Presença após** | ❌ Não | ✅ Sim | Mais humano |
| **Micro-pausas** | ❌ Não | ✅ Sim (10%) | Menos padrão |
| **Timeout** | 60s | 120s | +100% |
| **Retry delays** | Fixo 30s | Progressivo | Melhor |

---

## ⏱️ Impacto no Tempo Total de Envio

### Exemplo: 100 Holerites

**v2.0 (Atual):**
```
100 envios × 2.5min (média) = 250min = 4h 10min
+ 4 pausas × 12.5min (média) = 50min
TOTAL: ~5 horas
```

**v3.0 (Corrigido):**
```
100 envios × 10min (média) = 1000min = 16h 40min
+ 5-8 pausas × 45min (média) = 315min = 5h 15min
TOTAL: ~22 horas (quase 1 dia)
```

**⚠️ ATENÇÃO:** Envios vão demorar **4x mais tempo**!

### Estratégias para Reduzir Impacto:

1. **Enviar em horário comercial estendido** (8h às 20h)
2. **Distribuir em 2-3 dias** ao invés de 1 dia
3. **Priorizar colaboradores críticos** (enviar primeiro)
4. **Agendar envios noturnos** (pausas longas à noite)

---

## 🚀 Plano de Implementação

### Fase 1: Teste Controlado (10 envios)
```bash
1. Implementar correções
2. Enviar 10 holerites de teste
3. Monitorar:
   - Entregas bem-sucedidas
   - "Aguardando Mensagem" (iPhone)
   - Tempo real vs esperado
   - Logs de presença
4. Validar: nenhum erro, todos receberam
```

### Fase 2: Teste Médio (50 envios)
```bash
1. Se Fase 1 OK, enviar 50 holerites
2. Monitorar:
   - Pausas estratégicas ocorrendo
   - Delays variáveis funcionando
   - Sem softban até o final
3. Tempo estimado: ~8-10 horas
```

### Fase 3: Produção (100+ envios)
```bash
1. Se Fase 2 OK, envio completo
2. Distribuir em 2 dias se necessário
3. Monitoramento contínuo
```

---

## 📋 Checklist de Deploy

- [ ] Fazer backup do código atual
- [ ] Implementar mudanças em `main_legacy.py`
- [ ] Implementar mudanças em `evolution_api.py`
- [ ] Testar localmente com 2-3 envios
- [ ] Commit: "fix: Implement anti-softban v3.0 with increased delays"
- [ ] Build Docker images
- [ ] Push to Docker Hub
- [ ] Deploy em staging (se disponível)
- [ ] Teste controlado (10 envios)
- [ ] Se OK, deploy em produção
- [ ] Monitorar primeiro envio real

---

## 🎯 Resultados Esperados

### Após Implementação:

✅ **Problema iPhone resolvido**
- "Aguardando Mensagem" deve desaparecer
- Mensagens chegam normalmente

✅ **Softban prevenido**
- Delays muito maiores (5-15min)
- Pausas mais longas (30-60min)
- Comportamento mais imprevisível

✅ **Mais humanizado**
- Presença "available" ao final
- Micro-pausas aleatórias
- Variação de ±50%

⚠️ **Desvantagem:**
- Envios demoram 4x mais tempo
- 100 holerites = ~1 dia inteiro

---

## 📞 Suporte

Se após implementação ainda houver problemas:

1. **iPhone ainda "Aguardando Mensagem":**
   - Verificar logs: presença foi enviada antes de documento?
   - Verificar timeout: 120s foi aplicado?
   - Testar reduzir tamanho do PDF (comprimir)

2. **Softban ainda ocorre:**
   - Aumentar ainda mais delays (10-20min)
   - Pausas de 60-90min
   - Enviar mensagem de texto antes de documento

3. **Demora excessiva:**
   - Reduzir variação (±30% ao invés de ±50%)
   - Ajustar delays para 4-8min (meio termo)
   - Aceitar risco moderado de softban

---

**Próximo passo:** Implementar as correções ou fazer teste controlado?
