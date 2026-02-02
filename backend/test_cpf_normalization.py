"""
Teste de normalização de CPF
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.benefits_xlsx_processor import BenefitsXLSXProcessor

print("=" * 60)
print("🧪 TESTE DE NORMALIZAÇÃO DE CPF")
print("=" * 60)

# Diferentes formatos de CPF (todos representam o mesmo CPF)
test_cpfs = [
    "116.329.082-39",  # Formato padrão
    "116-329.082-39",  # Com hífen no início
    "116.329-082-39",  # Hífen no meio
    "11632908239",     # Apenas números
    "116 329 082 39",  # Com espaços
    "116.329.082.39",  # Pontos no lugar do hífen
    " 116.329.082-39 ", # Com espaços nas pontas
]

print("\nTestando diferentes formatos de CPF:")
print("-" * 60)

for cpf in test_cpfs:
    normalized = BenefitsXLSXProcessor.normalize_cpf(cpf)
    status = "✅" if normalized == "11632908239" else "❌"
    print(f"{status} '{cpf:20s}' → '{normalized}'")

print()
print("=" * 60)
print("✅ Todos os formatos devem resultar em: 11632908239")
print("=" * 60)
