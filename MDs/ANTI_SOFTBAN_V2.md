# 🛡️ Sistema Anti-Softban AVANÇADO - v2.0

## 📋 Resumo das Melhorias

Após o segundo softban ocorrido no final de semana, implementamos um **sistema de proteção muito mais robusto** com múltiplas camadas de segurança para evitar detecção pelo WhatsApp.

---

## 🚀 Novas Funcionalidades

### 1. 🕐 Delays Muito Maiores (120-180 segundos)

**Antes**: 47-73 segundos (muito rápido)  
**Agora**: **2-3 minutos aleatórios** (120-180 segundos)

```
Envio #1  → [SEM DELAY]
Envio #2  → [AGUARDA 2min 34s]
Envio #3  → [AGUARDA 2min 51s]
Envio #4  → [AGUARDA 2min 17s]
```

**Benefício**: Simula comportamento humano mais realista

---

### 2. ⏸️ Pausas Estratégicas (A cada 20 envios)

**Nova funcionalidade**: A cada 20 mensagens enviadas, o sistema faz uma **pausa longa de 10-15 minutos**

```
Envios 1-19   → Delays normais (2-3min)
Envio #20     → PAUSA ESTRATÉGICA (12min 23s)
Envios 21-39  → Delays normais (2-3min)
Envio #40     → PAUSA ESTRATÉGICA (14min 51s)
```

**Benefício**: Evita padrões constantes que o WhatsApp detecta como automação

---

### 3. 🔍 Monitoramento da Evolution API

**Nova proteção**: Sistema verifica se Evolution API está online **ANTES** de cada envio

#### Fluxo de Verificação:

1. **Antes de iniciar**: Verifica se Evolution API está conectada
2. **Antes de cada envio**: Checa status da instância
3. **Se detectar offline**:
   - ⏸️ Pausa envios automaticamente
   - 🔄 Tenta reconectar a cada 2 minutos
   - ⏱️ Aguarda até 30 minutos pela reconexão
   - ❌ Aborta job se não reconectar

#### Estados Monitorados:
```
✅ state: "open"     → Pode enviar
❌ state: "close"    → PAUSA automática
❌ state: "connecting" → PAUSA até conectar
```

**Benefício**: Evita enviar quando WhatsApp já detectou problema

---

### 4. 📝 8 Templates de Mensagem (ao invés de 4)

**Antes**: 4 variações de mensagem  
**Agora**: **8 templates diferentes**

#### Novos Templates Adicionados:

**Template 5**:
```
Bom dia {nome}! Segue em anexo seu contracheque referente a {mes_anterior}. 
Para acessar, use os 4 primeiros dígitos do CPF como senha. 
Qualquer questão, estamos à disposição no RH.
```

**Template 6**:
```
Oi {nome}, tudo bem? Seu holerite de {mes_anterior} já foi processado 
e está anexo nesta mensagem. Senha: 4 primeiros números do CPF. 
Dúvidas? Fale com o RH!
```

**Template 7**:
```
Prezado(a) {nome}, encaminhamos o comprovante de pagamento de {mes_anterior}. 
O arquivo está protegido com os 4 primeiros dígitos do seu CPF. 
Para esclarecimentos, procure o departamento pessoal.
```

**Template 8**:
```
Olá {nome}! Disponibilizamos seu holerite do período {mes_anterior}. 
A senha de acesso corresponde aos 4 primeiros números do CPF cadastrado. 
Em caso de necessidade, contate o RH.
```

---

### 5. 📝 Simulação de Presença "Digitando"

**Nova funcionalidade**: Sistema simula indicador de "digitando..." antes de cada envio

#### Como Funciona:

1. **Antes de enviar**: Sistema ativa presença "composing" (digitando)
2. **Duração**: 5 segundos de digitação simulada
3. **Aguarda**: Sistema espera os 5s antes de enviar mensagem
4. **Visível**: Destinatário vê "digitando..." no WhatsApp

#### Fluxo Visual no WhatsApp:
```
[📝 digitando...]  → 5 segundos
[📄 Mensagem com PDF enviada]
```

**Benefício**: Comportamento 100% humano - ninguém envia mensagem instantaneamente

#### Tratamento de Erros:
- Se presença falhar, envio continua normalmente
- Não bloqueia operação principal
- Registra falha nos logs para análise

**Benefício**: Maior variação = menor chance de detecção por padrões

---

## 📊 Comparação de Performance

### Sistema Antigo (v1.0)
```
232 holerites
Delay médio: 60s (47-73s)
Tempo total: ~4 horas
Pausas estratégicas: NENHUMA
Monitoramento API: NÃO
Templates: 4
Resultado: SOFTBAN após 232 envios
```

### Sistema Novo (v2.0)
```
232 holerites
Delay médio: 150s (120-180s) = 2.5x MAIS LENTO
Pausas a cada 20: 11x pausas de 12.5min
Tempo total: ~12-15 horas (3x mais lento)
Monitoramento API: SIM (contínuo)
Templates: 8 (2x mais variação)
Proteção: MÁXIMA
```

---

## 🎯 Estimativas de Tempo

### Para 50 holerites:
- Delays normais: 49 × 2.5min = **2h 2min**
- Pausas (2×): 2 × 12.5min = **25min**
- **Total**: ~**2h 30min**

### Para 100 holerites:
- Delays normais: 99 × 2.5min = **4h 7min**
- Pausas (5×): 5 × 12.5min = **1h 2min**
- **Total**: ~**5h 10min**

### Para 232 holerites (caso do softban):
- Delays normais: 231 × 2.5min = **9h 37min**
- Pausas (11×): 11 × 12.5min = **2h 17min**
- Presença "digitando": 232 × 5.5s = **21min**
- **Total**: ~**12-15 horas**

---

## 🔧 Configurações Técnicas

### Backend (`main_legacy.py`)

#### Delays Configurados:
```python
# Delay normal entre envios
delay = random.uniform(120.00, 180.00)  # 2-3 minutos

# Pausa estratégica a cada 20 envios
if idx % 20 == 0:
    long_delay = random.uniform(600.00, 900.00)  # 10-15 minutos
```

#### Verificação de Status:
```python
async def check_evolution_status(evolution_service):
    result = await evolution_service.check_instance_status()
    instance_state = result.get('data', {}).get('instance', {}).get('state')
    return instance_state == 'open'
```

#### Simulação de Presença:
```python
# Ativar indicador "digitando" antes do envio
presence_result = await evolution_service.send_presence(
    phone=phone_number,
    presence_type="composing",
    delay=5000  # 5 segundos
)
time.sleep(5.5)  # Aguardar a simulação
```

#### Reconexão Automática:
```python
max_wait_time = 30 * 60  # 30 minutos
wait_interval = 2 * 60   # Tentar a cada 2 minutos
```

---

## 🚀 Como Usar

### 1. Fazer Deploy no Servidor

```bash
cd /app/docker/nexorh

# Parar containers
docker compose down

# Baixar imagens atualizadas
docker pull lucasplcorrea/nexo-rh-backend:latest
docker pull lucasplcorrea/nexo-rh-frontend:latest

# Subir containers
docker compose up -d

# Verificar logs
docker logs nexo-rh-backend --tail 50
```

### 2. Configurar Templates no Frontend

1. Acesse: http://192.168.230.253:7080
2. Vá para "Enviar Holerites"
3. **Preencha os 8 templates** (quanto mais, melhor)
4. Use variações de:
   - Saudações (Olá, Oi, Prezado, Bom dia)
   - Vocabulário (holerite, contracheque, comprovante)
   - Tom (formal, informal, neutro)

### 3. Iniciar Envio

O sistema mostrará nova mensagem de confirmação:

```
⚠️ SISTEMA ANTI-SOFTBAN AVANÇADO ⚠️

Arquivos a enviar: 232
Templates ativos: 8

PROTEÇÕES:
• Delay entre envios: 2-3 minutos (aleatório)
• Pausa estratégica: 10-15min a cada 20 envios
• Monitoramento: Evolution API (pausa se offline)
• Variação: 8 templates randomizados
• Presença "digitando": 5s antes de cada envio

⏱️ Tempo estimado: 12h 30min

O sistema pausará automaticamente se detectar problemas.
Você pode navegar em outras páginas durante o envio.

Deseja continuar?
```

### 4. Monitorar Progresso

O modal mostrará informações em tempo real:
- 📊 Progresso: 45/232 (19.4%)
- ✅ Enviados: 44
- ❌ Falhas: 1
- ⏱️ Tempo: 1h 52min
- 📄 Atual: colaborador_046.pdf
- 🛡️ Próxima pausa em: 5 envios

---

## 🐛 Troubleshooting

### "Evolution API está offline"

**Sintoma**: Job pausa e mostra "aguardando reconexão"

**Causas possíveis**:
1. WhatsApp Web desconectou
2. Evolution API reiniciou
3. Problemas de rede

**Solução**:
1. Verificar Evolution API: http://192.168.230.253:8080
2. Reconectar instância se necessário
3. Sistema retoma automaticamente quando detectar online

### "Job ficou em 'paused' por muito tempo"

**Se passar de 30 minutos pausado**:
1. Verificar logs: `docker logs nexo-rh-backend | grep JOB`
2. Verificar Evolution API manualmente
3. Se necessário, cancelar job e tentar novamente

### Logs do Sistema

```bash
# Ver logs de um job específico
docker logs nexo-rh-backend | grep "JOB 1a2b3c4d"

# Ver pausas estratégicas
docker logs nexo-rh-backend | grep "PAUSA ESTRATÉGICA"

# Ver verificações da Evolution API
docker logs nexo-rh-backend | grep "Verificando Evolution API"
```

---

## 📈 Melhorias Futuras Sugeridas

### Nível 1 (Já Implementado ✅):
- ✅ Delays de 2-3 minutos
- ✅ Pausas a cada 20 envios
- ✅ Monitoramento da Evolution API
- ✅ 8 templates de mensagem
- ✅ Simulação de presença "digitando" (5s)

### Nível 2 (Sugestões Adicionais):

1. **Horário Inteligente** 🕐
   - Evitar envios entre 22h-7h (horário de descanso)
   - Limitar quantidade por dia (ex: máximo 100/dia)
   - Distribuir ao longo do dia útil

2. **Análise de Comportamento** 📊
   - Registrar histórico de envios por dia/semana
   - Alertar se estiver próximo de limites suspeitos
   - Sugerir melhor horário para envio

3. **Variação de Conteúdo** 🎲
   - Adicionar emojis aleatórios (opcional)
   - Variar ordem das informações
   - Usar sinônimos programaticamente

4. **Rotação de Instâncias** 🔄
   - Configurar múltiplas instâncias do WhatsApp
   - Rotacionar entre elas automaticamente
   - Reduzir carga por número

5. **Whitelist de Números** ✅
   - Priorizar envios para números já contactados
   - Iniciar conversas com números novos gradualmente

---

## ✅ Checklist de Deploy

- [ ] Pull das novas imagens Docker
- [ ] Containers reiniciados
- [ ] Logs sem erros
- [ ] Frontend mostra 8 campos de template
- [ ] Mensagem de confirmação atualizada
- [ ] Testar com 2-3 arquivos primeiro
- [ ] Verificar delays de 2-3min funcionando
- [ ] Confirmar pausa estratégica aos 20 envios
- [ ] Validar monitoramento da Evolution API

---

## 🎉 Resultado Esperado

Com todas essas proteções:

✅ **Delays 2.5× mais longos** - Comportamento mais humano  
✅ **Pausas estratégicas** - Quebra de padrões constantes  
✅ **Monitoramento ativo** - Pausa se detectar problemas  
✅ **8 templates** - Variação máxima de conteúdo  
✅ **Sistema responsivo** - Não trava mais durante envio  
✅ **Reconexão automática** - Resiliente a quedas  

**Probabilidade de softban**: **SIGNIFICATIVAMENTE REDUZIDA** 🛡️

---

## 📞 Suporte

Se mesmo com todas essas proteções ocorrer novo softban:

1. **Documente**:
   - Quantidade de mensagens enviadas antes do ban
   - Horário dos envios
   - Logs do backend do período

2. **Analise padrões**:
   - Verificar se Evolution API ficou offline
   - Ver se houve sequências muito rápidas
   - Checar se pausas estratégicas funcionaram

3. **Ajuste configurações**:
   - Aumentar delays (ex: 3-5min ao invés de 2-3min)
   - Mais pausas (a cada 15 ao invés de 20)
   - Limitar quantidade diária

---

## 📊 Imagens Docker

**Backend v2.0**:
- `lucasplcorrea/nexo-rh-backend:latest`
- Digest: `sha256:7bbf0a95605e36096930eaee202633338142ac2cfbc1c879b8916ecd0e4d6f08`

**Frontend v2.0**:
- `lucasplcorrea/nexo-rh-frontend:latest`
- Digest: `sha256:c4da794093d0acc459c0fa3c03d36a7c9ea32a74ff8a8ebb23d8ee0d04b5761a`

---

**Última atualização**: 8 de dezembro de 2025  
**Versão**: 2.0 (Anti-Softban Avançado)
