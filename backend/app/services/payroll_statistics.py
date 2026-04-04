"""
Endpoint simplificado de estatísticas de folha de pagamento
Organizado nas 7 seções conforme especificação RH
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


def calculate_payroll_statistics(
    db_session: Session,
    companies: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    months: Optional[List[int]] = None,
    period_ids: Optional[List[int]] = None,
    department_ids: Optional[List[str]] = None,
    employee_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Calcula estatísticas de folha organizadas por seções
    
    Ordem dos filtros: Empresa, Anos, Meses, Período, Setores, Colaboradores
    
    Seções:
    1. Resumo de Filtro
    2. Informações Salariais
    3. Adicionais e Benefícios
    4. Encargos Trabalhistas
    5. Horas Extras
    6. Atestados Médicos e Horas Faltas
    7. Empréstimos
    """
    
    # Construir filtro SQL (ordem: Empresa, Anos, Meses, Período, Setores, Colaboradores)
    where_clauses = []
    params = {}
    
    if companies:
        where_clauses.append("pp.company = ANY(:companies)")
        params['companies'] = companies
    
    if years:
        where_clauses.append("pp.year = ANY(:years)")
        params['years'] = years
    
    if months:
        where_clauses.append("pp.month = ANY(:months)")
        params['months'] = months
    
    if period_ids:
        where_clauses.append("pd.period_id = ANY(:period_ids)")
        params['period_ids'] = period_ids
    
    if department_ids:
        where_clauses.append("""(
            e.department = ANY(:department_ids)
            OR (e.department IS NULL AND 'Sem departamento cadastrado' = ANY(:department_ids))
        )""")
        params['department_ids'] = department_ids
    
    if employee_ids:
        where_clauses.append("e.id = ANY(:employee_ids)")
        params['employee_ids'] = employee_ids
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # ===============================
    # QUERY ÚNICA PARA TODAS AS SEÇÕES (exceto benefícios iFood)
    # Benefícios iFood são agregados em consulta separada para evitar
    # dupla contagem quando há múltiplos períodos de folha no mesmo mês.
    # ===============================
    query = text(f"""
        SELECT 
            -- Resumo de Filtro
            COUNT(DISTINCT e.id) as total_funcionarios,
            COALESCE(SUM((pd.additional_data->>'Total de Proventos')::numeric), 0) as total_proventos,
            COALESCE(SUM((pd.additional_data->>'Total de Descontos')::numeric), 0) as total_descontos,
            COALESCE(SUM((pd.additional_data->>'Líquido de Cálculo')::numeric), 0) as total_liquido,
            
            -- Informações Salariais (com count de registros para média correta)
            COALESCE(SUM((pd.additional_data->>'Salário Mensal')::numeric), 0) as total_salarios_base,
            COUNT(pd.id) as total_registros,
            
            -- Adicionais e Benefícios
            COALESCE(SUM((pd.earnings_data->>'GRATIFICACAO_FUNCAO_20')::numeric), 0) as total_gratificacoes,
            COALESCE(SUM((pd.earnings_data->>'PERICULOSIDADE')::numeric), 0) as total_periculosidade,
            COALESCE(SUM((pd.earnings_data->>'INSALUBRIDADE')::numeric), 0) as total_insalubridade,
            COALESCE(SUM((pd.earnings_data->>'PLANO_SAUDE')::numeric), 0) as total_plano_saude,
            COALESCE(SUM((pd.earnings_data->>'TRANSFERENCIA_FILIAL')::numeric), 0) as total_transferencia_filial,
            COALESCE(SUM((pd.earnings_data->>'AJUDA_CUSTO')::numeric), 0) as total_ajuda_custo,
            COALESCE(SUM((pd.earnings_data->>'LICENCA_PATERNIDADE')::numeric), 0) as total_licenca_paternidade,
            
            -- Benefícios iFood (preenchidos por consulta separada)
            0::numeric as total_vale_refeicao,
            0::numeric as total_vale_alimentacao,
            0::numeric as total_vale_mobilidade,
            0::numeric as total_saldo_livre,
            
            -- Encargos Trabalhistas
            COALESCE(SUM((pd.deductions_data->>'INSS')::numeric), 0) as total_inss,
            COALESCE(SUM((pd.deductions_data->>'IRRF')::numeric), 0) as total_irrf,
            COALESCE(SUM((pd.deductions_data->>'FGTS')::numeric), 0) as total_fgts,
            
            -- Horas Extras
            COALESCE(SUM((pd.earnings_data->>'DSR_HE_DIURNAS')::numeric), 0) as total_dsr_diurno,
            COALESCE(SUM((pd.earnings_data->>'HE_50_DIURNAS')::numeric), 0) as total_he50_diurno,
            COALESCE(SUM((pd.earnings_data->>'HE_100_DIURNAS')::numeric), 0) as total_he100_diurno,
            COALESCE(SUM((pd.earnings_data->>'ADICIONAL_NOTURNO')::numeric), 0) as total_adicional_noturno,
            COALESCE(SUM((pd.earnings_data->>'DSR_HE_NOTURNAS')::numeric), 0) as total_dsr_noturno,
            COALESCE(SUM((pd.earnings_data->>'HE_50_NOTURNAS')::numeric), 0) as total_he50_noturno,
            COALESCE(SUM((pd.earnings_data->>'HE_100_NOTURNAS')::numeric), 0) as total_he100_noturno,
            
            -- Atestados e Faltas
            COALESCE(SUM((pd.additional_data->>'Horas Faltas')::numeric), 0) as total_horas_faltas,
            COALESCE(SUM((pd.additional_data->>'Atestados Médicos')::numeric), 0) as total_atestados_medicos,
            
            -- Empréstimos
            COALESCE(SUM((pd.deductions_data->>'EMPRESTIMO_TRABALHADOR')::numeric), 0) as total_emprestimo_trabalhador,
            COALESCE(SUM((pd.deductions_data->>'ADIANTAMENTO')::numeric), 0) as total_adiantamentos
            
        FROM payroll_data pd
        INNER JOIN employees e ON e.id = pd.employee_id
        INNER JOIN payroll_periods pp ON pp.id = pd.period_id
        WHERE {where_sql}
    """)
    
    result = db_session.execute(query, params).fetchone()
    
    if not result:
        return _empty_statistics()

    benefits_totals = _calculate_benefits_totals(
        db_session=db_session,
        where_sql=where_sql,
        params=params,
    )
    
    # Calcular médias
    total_funcionarios = int(result[0]) if result[0] else 0
    total_registros = int(result[5]) if result[5] else 1  # Total de registros para média correta
    total_salarios_base = float(result[4])
    total_liquido = float(result[3])
    
    # Média por REGISTRO (não por funcionário único)
    salario_medio = total_salarios_base / total_registros if total_registros > 0 else 0
    liquido_medio = total_liquido / total_registros if total_registros > 0 else 0
    
    # ===============================
    # ORGANIZAR POR SEÇÕES
    # ===============================
    return {
        "success": True,
        
        # Seção 1: Resumo de Filtro
        "resumo_filtro": {
            "funcionarios": int(result[0]),
            "total_proventos": float(result[1]),
            "total_descontos": float(result[2]),
            "total_liquido": float(result[3])
        },
        
        # Seção 2: Informações Salariais
        "informacoes_salariais": {
            "total_salarios_base": float(result[4]),
            "salario_medio": salario_medio,
            "liquido_medio": liquido_medio
        },
        
        # Seção 3: Adicionais e Benefícios
        "adicionais_beneficios": {
            "gratificacoes": float(result[6]),
            "periculosidade": float(result[7]),
            "insalubridade": float(result[8]),
            "vale_transporte": 0.0,  # Zerado conforme solicitado
            "plano_saude": float(result[9]),
            "vale_mobilidade": benefits_totals["vale_mobilidade"],
            "vale_refeicao": benefits_totals["vale_refeicao"],
            "vale_alimentacao": benefits_totals["vale_alimentacao"],
            "saldo_livre": benefits_totals["saldo_livre"],
            "transferencia_filial": float(result[10]),
            "ajuda_custo": float(result[11]),
            "licenca_paternidade": float(result[12]),
            "total": (
                float(result[6]) + float(result[7]) + float(result[8]) + float(result[9]) + 
                float(result[10]) + float(result[11]) + float(result[12]) +
                benefits_totals["vale_refeicao"] + benefits_totals["vale_alimentacao"] +
                benefits_totals["saldo_livre"] + benefits_totals["vale_mobilidade"]
            )
        },
        
        # Seção 4: Encargos Trabalhistas
        "encargos_trabalhistas": {
            "inss": float(result[17]),
            "irrf": float(result[18]),
            "fgts": float(result[19]),
            "total": float(result[17]) + float(result[18]) + float(result[19])
        },
        
        # Seção 5: Horas Extras
        "horas_extras": {
            "dsr_diurno": float(result[20]),
            "he50_diurno": float(result[21]),
            "he100_diurno": float(result[22]),
            "adicional_noturno": float(result[23]),
            "dsr_noturno": float(result[24]),
            "he50_noturno": float(result[25]),
            "he100_noturno": float(result[26]),
            "total": float(result[20]) + float(result[21]) + float(result[22]) + float(result[23]) + float(result[24]) + float(result[25]) + float(result[26])
        },
        
        # Seção 6: Atestados e Faltas
        "atestados_faltas": {
            "horas_faltas": float(result[27]),
            "atestados_medicos": float(result[28]),
            "total": float(result[27]) + float(result[28])
        },
        
        # Seção 7: Empréstimos
        "emprestimos": {
            "emprestimo_trabalhador": float(result[29]),
            "adiantamentos": float(result[30]),
            "total": float(result[29]) + float(result[30])
        }
    }


def _calculate_benefits_totals(
    db_session: Session,
    where_sql: str,
    params: Dict[str, Any],
) -> Dict[str, float]:
    """Agrega benefícios sem duplicar registros entre múltiplos períodos de folha."""
    query = text(f"""
        SELECT
            COALESCE(SUM(x.refeicao), 0) AS total_vale_refeicao,
            COALESCE(SUM(x.alimentacao), 0) AS total_vale_alimentacao,
            COALESCE(SUM(x.mobilidade), 0) AS total_vale_mobilidade,
            COALESCE(SUM(x.livre), 0) AS total_saldo_livre
        FROM (
            SELECT DISTINCT
                bd.id,
                bd.refeicao,
                bd.alimentacao,
                bd.mobilidade,
                bd.livre
            FROM payroll_data pd
            INNER JOIN employees e ON e.id = pd.employee_id
            INNER JOIN payroll_periods pp ON pp.id = pd.period_id
            INNER JOIN benefits_periods bp
                ON bp.year = pp.year
                AND bp.month = pp.month
                AND bp.company = pp.company
            INNER JOIN benefits_data bd
                ON bd.period_id = bp.id
                AND bd.employee_id = e.id
            WHERE {where_sql}
        ) x
    """)

    row = db_session.execute(query, params).fetchone()

    if not row:
        return {
            "vale_refeicao": 0.0,
            "vale_alimentacao": 0.0,
            "vale_mobilidade": 0.0,
            "saldo_livre": 0.0,
        }

    return {
        "vale_refeicao": float(row[0] or 0),
        "vale_alimentacao": float(row[1] or 0),
        "vale_mobilidade": float(row[2] or 0),
        "saldo_livre": float(row[3] or 0),
    }


def _empty_statistics() -> Dict[str, Any]:
    """Retorna estrutura vazia quando não há dados"""
    return {
        "success": True,
        "resumo_filtro": {
            "funcionarios": 0,
            "total_proventos": 0.0,
            "total_descontos": 0.0,
            "total_liquido": 0.0
        },
        "informacoes_salariais": {
            "total_salarios_base": 0.0,
            "salario_medio": 0.0,
            "liquido_medio": 0.0
        },
        "adicionais_beneficios": {
            "gratificacoes": 0.0,
            "periculosidade": 0.0,
            "insalubridade": 0.0,
            "vale_transporte": 0.0,
            "plano_saude": 0.0,
            "vale_mobilidade": 0.0,
            "vale_refeicao": 0.0,
            "vale_alimentacao": 0.0,
            "saldo_livre": 0.0,
            "transferencia_filial": 0.0,
            "ajuda_custo": 0.0,
            "licenca_paternidade": 0.0,
            "total": 0.0
        },
        "encargos_trabalhistas": {
            "inss": 0.0,
            "irrf": 0.0,
            "fgts": 0.0,
            "total": 0.0
        },
        "horas_extras": {
            "dsr_diurno": 0.0,
            "he50_diurno": 0.0,
            "he100_diurno": 0.0,
            "adicional_noturno": 0.0,
            "dsr_noturno": 0.0,
            "he50_noturno": 0.0,
            "he100_noturno": 0.0,
            "total": 0.0
        },
        "atestados_faltas": {
            "horas_faltas": 0.0,
            "atestados_medicos": 0.0,
            "total": 0.0
        },
        "emprestimos": {
            "emprestimo_trabalhador": 0.0,
            "adiantamentos": 0.0,
            "total": 0.0
        }
    }
