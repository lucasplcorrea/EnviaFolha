"""
Script para popular leave_records a partir dos CSVs existentes.
Processa todos os CSVs da pasta Analiticos e cria registros de afastamento
baseado na coluna Situação.
"""
import os
import sys
import calendar
from datetime import datetime, date

# Adicionar path do backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv('../.env')

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

from app.models.employee import Employee
from app.models.leave import LeaveRecord
from app.models.base import Base

# Mapeamento de códigos de situação para tipos de afastamento
SITUATION_TO_LEAVE_TYPE = {
    2: 'Férias',
    3: 'Auxílio Doença',
    9: 'Licença Remunerada',
    13: 'Licença Maternidade',
    14: 'Auxílio Doença',  # até 15 dias
    23: 'Auxílio Doença',  # dentro 60 dias
    31: 'Licença Paternidade',
}

# Situações que devem ser ignoradas
IGNORE_SITUATIONS = {1, 7}  # Trabalhando, Demitido


def process_csv_for_leaves(csv_path: str, year: int, month: int, db_session):
    """Processa um CSV e cria registros de afastamento"""
    import pandas as pd
    
    try:
        df = pd.read_csv(csv_path, encoding='latin1', sep=';', dtype=str)
    except Exception as e:
        print(f"  ❌ Erro ao ler CSV: {e}")
        return 0
    
    if 'Situação' not in df.columns:
        print(f"  ⚠️ Coluna 'Situação' não encontrada")
        return 0
    
    # Calcular primeiro e último dia do mês
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    created = 0
    
    for _, row in df.iterrows():
        try:
            # Extrair código do funcionário
            codigo_func = str(row.get('Código Funcionário', '')).strip()
            if not codigo_func:
                continue
            
            # Extrair situação
            situacao = row.get('Situação', None)
            if situacao is None:
                continue
            
            try:
                situacao_code = int(situacao)
            except (ValueError, TypeError):
                continue
            
            # Ignorar situações normais
            if situacao_code in IGNORE_SITUATIONS:
                continue
            
            # Determinar tipo de afastamento
            leave_type = SITUATION_TO_LEAVE_TYPE.get(situacao_code)
            if not leave_type:
                descricao = row.get('Descrição', f'Situação {situacao_code}')
                leave_type = str(descricao) if descricao else 'Outro'
            
            # Buscar employee pelo código (tentando variações de matrícula)
            employee = None
            for prefix in ['0059', '0060']:
                matricula = f"{prefix}{codigo_func.zfill(5)}"
                employee = db_session.query(Employee).filter(
                    Employee.unique_id == matricula
                ).first()
                if employee:
                    break
            
            if not employee:
                continue
            
            # Verificar se já existe registro
            existing = db_session.query(LeaveRecord).filter(
                and_(
                    LeaveRecord.employee_id == employee.id,
                    LeaveRecord.start_date == start_date,
                    LeaveRecord.end_date == end_date
                )
            ).first()
            
            if existing:
                # Atualizar se tipo mudou
                if existing.leave_type != leave_type:
                    existing.leave_type = leave_type
            else:
                # Criar novo
                leave_record = LeaveRecord(
                    employee_id=employee.id,
                    unified_code=employee.unique_id,
                    leave_type=leave_type,
                    start_date=start_date,
                    end_date=end_date,
                    days=float(last_day),
                    notes=f'Importado do CSV {os.path.basename(csv_path)}',
                    created_at=datetime.now()
                )
                db_session.add(leave_record)
                created += 1
                
        except Exception as e:
            continue
    
    return created


def main():
    # Conectar ao banco
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não configurada")
        return
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Diretórios de CSVs
    csv_dirs = [
        '../Analiticos/Infraestrutura',
        '../Analiticos/Empreendimentos'
    ]
    
    total_created = 0
    
    for csv_dir in csv_dirs:
        if not os.path.exists(csv_dir):
            print(f"⚠️ Diretório não encontrado: {csv_dir}")
            continue
        
        print(f"\n📁 Processando diretório: {csv_dir}")
        
        for filename in sorted(os.listdir(csv_dir)):
            if not filename.endswith('.CSV'):
                continue
            
            # Ignorar arquivos de adiantamento, complementar, etc.
            if any(x in filename for x in ['Adiantamento', 'Complementar', 'Integral']):
                continue
            
            # Extrair mês e ano do nome do arquivo (formato: MM-YYYY.CSV)
            try:
                parts = filename.replace('.CSV', '').split('-')
                month = int(parts[0])
                year = int(parts[1])
            except:
                print(f"  ⚠️ Nome de arquivo inválido: {filename}")
                continue
            
            csv_path = os.path.join(csv_dir, filename)
            print(f"  📄 {filename} ({month:02d}/{year})...", end=' ')
            
            created = process_csv_for_leaves(csv_path, year, month, db)
            total_created += created
            
            if created > 0:
                print(f"✅ {created} afastamentos criados")
            else:
                print("(nenhum afastamento)")
    
    # Commit final
    try:
        db.commit()
        print(f"\n✅ Total de afastamentos criados: {total_created}")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro ao salvar: {e}")
    finally:
        db.close()
    
    # Mostrar resumo
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    print("\n📊 Resumo de afastamentos no banco:")
    from sqlalchemy import func
    result = db.query(
        LeaveRecord.leave_type,
        func.count(LeaveRecord.id)
    ).group_by(LeaveRecord.leave_type).all()
    
    for leave_type, count in result:
        print(f"  - {leave_type}: {count}")
    
    db.close()


if __name__ == '__main__':
    main()
