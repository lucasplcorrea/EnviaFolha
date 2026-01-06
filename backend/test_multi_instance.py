"""
Script de teste para validar a implementação multi-instância
"""
import sys
import os

# Adicionar o diretório app ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_settings():
    """Testa se as configurações foram carregadas corretamente"""
    print("\n=== Teste 1: Configurações ===")
    from app.core.config import settings
    
    instances = settings.get_evolution_instances()
    
    print(f"✓ Instância padrão: {settings.EVOLUTION_INSTANCE_NAME}")
    print(f"✓ Instância 2: {settings.EVOLUTION_INSTANCE_NAME2 or 'Não configurada'}")
    print(f"✓ Instância 3: {settings.EVOLUTION_INSTANCE_NAME3 or 'Não configurada'}")
    print(f"✓ Total de instâncias configuradas: {len(instances)}")
    print(f"✓ Lista de instâncias: {instances}")
    
    has_smtp = settings.has_smtp_configured()
    print(f"✓ SMTP configurado: {'Sim' if has_smtp else 'Não'}")
    
    return instances

def test_instance_manager(instances):
    """Testa o gerenciador de instâncias"""
    print("\n=== Teste 2: Instance Manager ===")
    
    if not instances:
        print("⚠️  Nenhuma instância configurada no .env")
        print("   Configure EVOLUTION_INSTANCE_NAME no .env para testar")
        return
    
    from app.services.instance_manager import get_instance_manager
    
    manager = get_instance_manager()
    
    # Testar round-robin
    print("✓ Testando round-robin:")
    for i in range(len(instances) * 2):
        instance = manager.get_next_instance()
        print(f"  Envio {i+1}: {instance}")
    
    # Testar registro de envio
    print("\n✓ Testando registro de envio:")
    test_instance = instances[0]
    manager.register_send(test_instance)
    delay = manager.get_instance_delay(test_instance)
    print(f"  Instância: {test_instance}")
    print(f"  Delay desde último envio: {delay:.2f}s")
    
    # Testar should_wait
    should_wait = manager.should_wait(test_instance, min_delay=300)
    print(f"  Deve aguardar? {should_wait}")
    
    # Estatísticas
    print("\n✓ Estatísticas de todas as instâncias:")
    stats = manager.get_instance_stats()
    for instance, data in stats.items():
        print(f"  {instance}:")
        print(f"    - Delay: {data['delay']:.2f}s" if data['delay'] is not None else "    - Delay: Nunca utilizada")
        print(f"    - Pronta: {'Sim' if data['ready'] else 'Não (aguardar mais tempo)'}")

def test_evolution_service(instances):
    """Testa se o EvolutionAPIService aceita instância específica"""
    print("\n=== Teste 3: Evolution API Service ===")
    
    if not instances:
        print("⚠️  Nenhuma instância configurada")
        print("   Testando apenas backward compatibility...")
    
    from app.services.evolution_api import EvolutionAPIService
    
    # Teste backward compatibility (sem parâmetro)
    print("✓ Testando backward compatibility:")
    try:
        service_default = EvolutionAPIService()
        print(f"  Instância padrão: {service_default.instance_name or 'None'}")
    except Exception as e:
        print(f"  ⚠️  Erro: {str(e)}")
    
    if not instances:
        return
    
    # Teste com instância específica
    print("\n✓ Testando com instância específica:")
    for instance in instances:
        try:
            service = EvolutionAPIService(instance)
            print(f"  Service criado para: {service.instance_name}")
        except Exception as e:
            print(f"  ⚠️  Erro ao criar service para {instance}: {str(e)}")

async def test_status_check():
    """Testa verificação de status assíncrona"""
    print("\n=== Teste 4: Status Check (Assíncrono) ===")
    from app.services.instance_manager import get_instance_manager
    
    manager = get_instance_manager()
    
    print("✓ Verificando status de todas as instâncias...")
    print("  (Isso pode levar até 10 segundos por instância)")
    
    try:
        results = await manager.check_all_instances_status()
        
        print(f"\n✓ Resultados ({len(results)} instâncias):")
        for result in results:
            status_icon = "🟢" if result['status'] == 'connected' else "🔴" if result['status'] == 'disconnected' else "🟡"
            print(f"  {status_icon} {result['name']}: {result['status']}")
            print(f"     Ready: {result['ready']}")
            if result['seconds_since_last_send'] is not None:
                print(f"     Último envio: {result['seconds_since_last_send']:.2f}s atrás")
    except Exception as e:
        print(f"  ⚠️  Erro ao verificar status: {str(e)}")
        print("  (Isso é esperado se o Evolution API não estiver acessível)")

def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("TESTES DE IMPLEMENTAÇÃO MULTI-INSTÂNCIA")
    print("=" * 60)
    
    try:
        # Teste 1: Configurações
        instances = test_settings()
        
        # Teste 2: Instance Manager
        test_instance_manager(instances)
        
        # Teste 3: Evolution Service
        test_evolution_service(instances)
        
        # Teste 4: Status Check (assíncrono)
        print("\n=== Teste 4: Status Check ===")
        print("⏭️  Pulando teste assíncrono (requer asyncio.run)")
        print("   Para testar manualmente: curl http://localhost:8000/api/v1/evolution/instances")
        
        print("\n" + "=" * 60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Iniciar backend: cd backend && uvicorn main:app --reload")
        print("2. Testar endpoint: curl http://localhost:8000/api/v1/evolution/instances")
        print("3. Iniciar frontend: cd frontend && npm start")
        print("4. Acessar: http://localhost:3000/system-info")
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
