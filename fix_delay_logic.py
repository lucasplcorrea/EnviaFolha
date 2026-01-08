#!/usr/bin/env python3
"""Fix delay logic to be per-instance instead of global"""

import re

file_path = 'backend/main_legacy.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the delay section
old_section_start = "# ===== SISTEMA ANTI-SOFTBAN AVANÇADO COM OTIMIZAÇÃO MULTI-INSTÂNCIA ====="
old_section_pattern = re.compile(
    r"(# ===== SISTEMA ANTI-SOFTBAN AVANÇADO COM OTIMIZAÇÃO MULTI-INSTÂNCIA =====\s+"
    r"if idx > 0:.*?"
    r"print\(f\"✅ \[JOB \{job_id\[:8\]\}\] \{online_count\}/\{len\(all_status\)\} instância\(s\) online e disponível\(is\)\"\))",
    re.DOTALL
)

new_section = """# ===== SISTEMA ANTI-SOFTBAN AVANÇADO COM OTIMIZAÇÃO MULTI-INSTÂNCIA =====
            if idx > 0:
                # 🎯 DELAY INTELIGENTE POR INSTÂNCIA
                # Cada instância tem seu próprio cooldown, permitindo envios paralelos
                
                # Descobrir qual será a próxima instância
                next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
                
                if not next_instance:
                    print(f"⚠️ [JOB {job_id[:8]}] TODAS as instâncias estão OFFLINE! Pausando envios...")
                    job.status = 'paused'
                    job.error_message = 'Todas as instâncias WhatsApp estão offline. Aguardando reconexão...'
                    
                    # Tentar reconectar a cada 2 minutos por até 30 minutos
                    max_wait_time = 30 * 60  # 30 minutos
                    wait_interval = 2 * 60   # 2 minutos
                    total_waited = 0
                    
                    while total_waited < max_wait_time:
                        print(f"⏳ [JOB {job_id[:8]}] Aguardando {wait_interval}s para verificar reconexão...")
                        time.sleep(wait_interval)
                        total_waited += wait_interval
                        
                        all_status = loop.run_until_complete(instance_manager.check_all_instances_status())
                        online_count = sum(1 for status in all_status.values() if status)
                        
                        if online_count > 0:
                            print(f"✅ [JOB {job_id[:8]}] {online_count} instância(s) voltaram online! Retomando envios...")
                            job.status = 'running'
                            job.error_message = None
                            next_instance = loop.run_until_complete(instance_manager.get_next_available_instance())
                            break
                        else:
                            print(f"❌ [JOB {job_id[:8]}] Todas ainda offline. Tentando novamente em {wait_interval}s...")
                    
                    if not next_instance:
                        job.status = 'failed'
                        job.error_message = f'Todas as instâncias permaneceram offline por mais de {max_wait_time/60} minutos'
                        job.end_time = datetime.now()
                        print(f"❌ [JOB {job_id[:8]}] Abortando job - Nenhuma instância reconectou")
                        return
                
                # Verificar quanto tempo passou desde último envio NESTA instância
                instance_delay = instance_manager.get_instance_delay(next_instance)
                min_delay_per_instance = 30  # Mínimo 30s entre envios da mesma instância
                
                if instance_delay < min_delay_per_instance:
                    # Precisa aguardar para esta instância
                    wait_time = min_delay_per_instance - instance_delay
                    print(f"⏳ [JOB {job_id[:8]}] Instância {next_instance} precisa aguardar {wait_time:.1f}s (último envio há {instance_delay:.1f}s)")
                    print(f"⏰ Início do delay: {datetime.now().strftime('%H:%M:%S')}")
                    time.sleep(wait_time)
                    print(f"✅ Delay concluído: {datetime.now().strftime('%H:%M:%S')}")
                else:
                    print(f"⚡ [JOB {job_id[:8]}] Instância {next_instance} pronta (último envio há {instance_delay:.1f}s) - SEM DELAY")"""

# Try to replace
if old_section_start in content:
    print("Found section to replace")
    new_content = old_section_pattern.sub(new_section, content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Successfully replaced delay logic!")
    else:
        print("❌ Regex didn't match - trying manual approach")
else:
    print("❌ Could not find section marker")
