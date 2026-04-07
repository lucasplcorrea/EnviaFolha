"""Modular route handlers for RH indicator endpoints."""

from calendar import monthrange
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from sqlalchemy import func

from app.models.employee import Employee
from app.models.leave import LeaveRecord
from app.models.payroll import PayrollData, PayrollPeriod
from app.routes.base import BaseRouter
from app.services.hr_indicators import HRIndicatorsService
from app.services.runtime_compat import SessionLocal, invalidate_employees_cache


class IndicatorsRouter(BaseRouter):
    """Router para endpoints de indicadores de RH."""

    def handle_get(self, path: str):
        if path == '/api/v1/indicators/overview':
            self.handle_overview()
            return

        if path == '/api/v1/indicators/headcount':
            self.handle_headcount()
            return

        if path == '/api/v1/indicators/turnover':
            self.handle_turnover()
            return

        if path == '/api/v1/indicators/demographics':
            self.handle_demographics()
            return

        if path == '/api/v1/indicators/tenure':
            self.handle_tenure()
            return

        if path == '/api/v1/indicators/leaves':
            self.handle_leaves()
            return

        if path == '/api/v1/indicators/payroll':
            self.handle_payroll()
            return

        self.send_error('Endpoint não encontrado', 404)

    def handle_post(self, path: str):
        if path == '/api/v1/indicators/cache/invalidate':
            self.handle_cache_invalidate()
            return

        self.send_error('Endpoint não encontrado', 404)

    def _delegate_legacy(self, method_name: str):
        handler_method = getattr(self.handler, method_name, None)
        if not handler_method:
            self.send_error('Endpoint não encontrado', 404)
            return

        handler_method()

    def _parse_filters(self):
        query_params = self._query_params()
        company = query_params.get('company', ['all'])[0]
        division = query_params.get('division', ['all'])[0]
        year = query_params.get('year', [None])[0]
        month = query_params.get('month', [None])[0]
        months_range = int(query_params.get('months_range', ['12'])[0])
        return company, division, year, month, months_range

    def _query_params(self):
        from urllib.parse import parse_qs, urlparse

        return parse_qs(urlparse(self.handler.path).query)

    def _get_db(self):
        return SessionLocal() if SessionLocal else None

    def _resolve_period(self, db, year, month):
        if not year or not month:
            latest_period = db.query(PayrollPeriod).order_by(
                PayrollPeriod.year.desc(),
                PayrollPeriod.month.desc()
            ).first()
            if not latest_period:
                return None, None
            return int(latest_period.year), int(latest_period.month)
        return int(year), int(month)

    def handle_headcount(self):
        try:
            company, division, year, month, months_range = self._parse_filters()
            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                year, month = self._resolve_period(db, year, month)
                if not year or not month:
                    self.send_json_response({'error': 'Nenhum período encontrado'}, 404)
                    return

                current_date = date(year, month, 1)
                full_response_cache_key = None
                if company == 'all' and division == 'all':
                    full_response_cache_key = 'headcount'
                    cache_period_start = current_date - relativedelta(months=months_range - 1)
                    cache_period_end = current_date
                    service = HRIndicatorsService(db)
                    cached = service._get_cached_indicator(
                        full_response_cache_key,
                        cache_period_start,
                        cache_period_end,
                    )
                    if cached and cached.get('metrics'):
                        self.send_json_response(cached['metrics'])
                        return

                current_metrics = self._get_headcount_for_period(db, year, month, company, division, calculate_variation=True)

                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    metrics = self._get_headcount_for_period(db, p_year, p_month, company, division, calculate_variation=False)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month - 1]}/{str(p_year)[2:]}",
                        'headcount': metrics['headcount'],
                        'total_cost': metrics['total_cost'],
                        'total_earnings': metrics.get('total_earnings', 0.0),
                        'total_deductions': metrics.get('total_deductions', 0.0),
                        'avg_cost_per_employee': metrics['avg_cost_per_employee'],
                    })

                by_company = current_metrics.get('by_company', [])
                top_divisions = current_metrics.get('top_divisions', [])[:10]
                top_positions = self._get_top_positions(db, year, month, company, division, limit=10)

                result = {
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range,
                    },
                    'current': {
                        'headcount': current_metrics['headcount'],
                        'total_cost': current_metrics['total_cost'],
                        'avg_cost_per_employee': current_metrics['avg_cost_per_employee'],
                        'total_earnings': current_metrics['total_earnings'],
                        'total_deductions': current_metrics['total_deductions'],
                        'variation_vs_previous': current_metrics['variation_vs_previous'],
                    },
                    'evolution': evolution_data,
                    'by_company': by_company,
                    'top_divisions': top_divisions,
                    'top_positions': top_positions,
                }

                if full_response_cache_key:
                    try:
                        service = HRIndicatorsService(db)
                        service._save_to_cache(
                            indicator_type=full_response_cache_key,
                            metrics=result,
                            total_records=len(evolution_data),
                            calculation_time_ms=0,
                            period_start=cache_period_start,
                            period_end=cache_period_end,
                        )
                    except Exception as cache_error:
                        print(f"⚠️  Erro ao salvar cache de headcount: {cache_error}")

                self.send_json_response(result)
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def handle_overview(self):
        try:
            company, division, year, month, _months_range = self._parse_filters()
            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                year, month = self._resolve_period(db, year, month)
                if not year or not month:
                    self.send_json_response({'error': 'Nenhum período encontrado'}, 404)
                    return

                current_headcount = self._get_headcount_for_period(db, year, month, company, division, calculate_variation=True)
                current_turnover = self._get_turnover_for_period(db, year, month, company, division)
                current_tenure = self._get_tenure_for_period(db, year, month, company, division)
                current_demographics = self._get_demographics_for_period(db, year, month, company, division)
                current_leaves = self._get_leaves_for_period(db, date(year, month, 1), company, division, [])

                # Mantem compatibilidade com telas novas (campos flat)
                # e antigas (objetos por indicador).
                self.send_json_response({
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                    },
                    'total_employees': current_headcount.get('headcount', 0),
                    'employee_variation': current_headcount.get('variation_vs_previous'),
                    'total_payroll_cost': current_headcount.get('total_cost', 0),
                    'cost_variation': None,
                    'admissions': current_turnover.get('admissions', 0),
                    'terminations': current_turnover.get('terminations', 0),
                    'turnover_rate': current_turnover.get('turnover_rate', 0),
                    'by_company': current_headcount.get('by_company', []),
                    'top_divisions': current_headcount.get('top_divisions', [])[:5],
                    'headcount': {
                        'total_active': current_headcount.get('headcount', 0),
                        'by_company': current_headcount.get('by_company', []),
                        'by_department': current_headcount.get('top_divisions', []),
                    },
                    'turnover': {
                        'rates': {
                            'turnover': current_turnover.get('turnover_rate', 0),
                        },
                        'movements': {
                            'admissions': current_turnover.get('admissions', 0),
                            'terminations': current_turnover.get('terminations', 0),
                        },
                    },
                    'tenure': current_tenure,
                    'leaves': current_leaves,
                    'demographics': current_demographics,
                })
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def _get_headcount_for_period(self, db, year, month, company='all', division='all', calculate_variation=True):
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month,
        )
        if company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)

        periods = period_query.all()
        if not periods:
            return {
                'headcount': 0,
                'total_cost': 0.0,
                'avg_cost_per_employee': 0.0,
                'total_earnings': 0.0,
                'total_deductions': 0.0,
                'variation_vs_previous': None,
                'by_company': [],
                'top_divisions': [],
            }

        period_ids = [p.id for p in periods]
        payroll_records = db.query(PayrollData).filter(PayrollData.period_id.in_(period_ids)).all()

        unique_employee_ids = {record.employee_id for record in payroll_records}
        employee_map = {}
        if unique_employee_ids:
            employees = db.query(Employee).filter(Employee.id.in_(unique_employee_ids)).all()
            employee_map = {employee.id: employee for employee in employees}

        if division != 'all':
            filtered_ids = {employee.id for employee in employee_map.values() if employee.department == division}
            payroll_records = [record for record in payroll_records if record.employee_id in filtered_ids]
            unique_employee_ids = {record.employee_id for record in payroll_records}

        headcount = len(unique_employee_ids)
        total_cost = sum(float(record.net_salary or 0) for record in payroll_records)
        total_earnings = sum(float(record.gross_salary or 0) for record in payroll_records)
        total_deductions = total_earnings - total_cost
        avg_cost = (total_cost / headcount) if headcount > 0 else 0.0

        variation = None
        if calculate_variation:
            if month == 1:
                prev_year, prev_month = year - 1, 12
            else:
                prev_year, prev_month = year, month - 1
            previous = self._get_headcount_for_period(
                db,
                prev_year,
                prev_month,
                company,
                division,
                calculate_variation=False,
            )
            prev_headcount = previous.get('headcount', 0)
            if prev_headcount > 0:
                variation = ((headcount - prev_headcount) / prev_headcount) * 100

        by_company = []
        if company == 'all':
            periods_by_company = {}
            for period in periods:
                periods_by_company.setdefault(period.company, []).append(period.id)

            for company_code, company_period_ids in periods_by_company.items():
                company_records = [record for record in payroll_records if record.period_id in company_period_ids]
                company_count = len({record.employee_id for record in company_records})
                company_cost = sum(float(record.net_salary or 0) for record in company_records)
                by_company.append({'company': company_code, 'count': company_count, 'total_cost': company_cost})

        by_division = {}
        for emp_id in unique_employee_ids:
            employee = employee_map.get(emp_id)
            if not employee:
                continue
            division_name = employee.department or 'Não informado'
            by_division.setdefault(division_name, set()).add(emp_id)

        top_divisions = sorted(
            [{'division': division_name, 'count': len(emp_ids)} for division_name, emp_ids in by_division.items()],
            key=lambda item: item['count'],
            reverse=True,
        )

        return {
            'headcount': headcount,
            'total_cost': float(total_cost),
            'avg_cost_per_employee': float(avg_cost),
            'total_earnings': float(total_earnings),
            'total_deductions': float(total_deductions),
            'variation_vs_previous': float(variation) if variation is not None else None,
            'by_company': by_company,
            'top_divisions': top_divisions,
        }

    def _get_top_positions(self, db, year, month, company='all', division='all', limit=10):
        period_query = db.query(PayrollPeriod).filter(
            PayrollPeriod.year == year,
            PayrollPeriod.month == month,
        )
        if company != 'all':
            period_query = period_query.filter(PayrollPeriod.company == company)

        periods = period_query.all()
        if not periods:
            return []

        period_ids = [period.id for period in periods]
        payroll_records = db.query(PayrollData).filter(PayrollData.period_id.in_(period_ids)).all()
        employee_ids = {record.employee_id for record in payroll_records}
        if not employee_ids:
            return []

        employees = db.query(Employee).filter(Employee.id.in_(employee_ids)).all()
        if division != 'all':
            employees = [employee for employee in employees if employee.department == division]

        by_position = {}
        for employee in employees:
            position = employee.position or 'Não informado'
            by_position.setdefault(position, set()).add(employee.id)

        top_positions = sorted(
            [{'position': position, 'count': len(emp_ids)} for position, emp_ids in by_position.items()],
            key=lambda item: item['count'],
            reverse=True,
        )
        return top_positions[:limit]

    def handle_turnover(self):
        try:
            company, division, year, month, months_range = self._parse_filters()
            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                year, month = self._resolve_period(db, year, month)
                if not year or not month:
                    self.send_json_response({'error': 'Nenhum período encontrado'}, 404)
                    return

                current_date = date(year, month, 1)
                current_metrics = self._get_turnover_for_period(db, year, month, company, division)

                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    metrics = self._get_turnover_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month - 1]}/{str(p_year)[2:]}",
                        'turnover_rate': metrics['turnover_rate'],
                        'admissions': metrics['admissions'],
                        'terminations': metrics['terminations'],
                        'avg_headcount': metrics['avg_headcount'],
                        'avg_tenure_months': metrics.get('avg_tenure_months', 0.0),
                    })

                self.send_json_response({
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range,
                    },
                    'current': {
                        'turnover_rate': current_metrics['turnover_rate'],
                        'admissions': current_metrics['admissions'],
                        'terminations': current_metrics['terminations'],
                        'avg_headcount': current_metrics['avg_headcount'],
                        'avg_tenure_months': current_metrics.get('avg_tenure_months', 0.0),
                    },
                    'evolution': evolution_data,
                    'by_company': [],
                    'top_divisions': [],
                })
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def _get_turnover_for_period(self, db, year, month, company='all', division='all'):
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1)
        else:
            period_end = date(year, month + 1, 1)

        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        periods_query = db.query(PayrollPeriod).filter(
            ((PayrollPeriod.year == year) & (PayrollPeriod.month == month)) |
            ((PayrollPeriod.year == prev_year) & (PayrollPeriod.month == prev_month))
        )
        if company != 'all':
            periods_query = periods_query.filter(PayrollPeriod.company == company)

        periods = periods_query.all()
        current_period_ids = [p.id for p in periods if p.year == year and p.month == month]
        prev_period_ids = [p.id for p in periods if p.year == prev_year and p.month == prev_month]

        current_headcount = 0
        prev_headcount = 0
        employee_ids_current = set()

        if current_period_ids:
            hc_query = db.query(PayrollData.employee_id).filter(PayrollData.period_id.in_(current_period_ids)).distinct()
            employee_ids_current = {row[0] for row in hc_query.all()}
            current_headcount = len(employee_ids_current)
            if division != 'all' and employee_ids_current:
                employees = db.query(Employee).filter(Employee.id.in_(employee_ids_current), Employee.department == division).all()
                employee_ids_current = {employee.id for employee in employees}
                current_headcount = len(employee_ids_current)

        if prev_period_ids:
            prev_query = db.query(PayrollData.employee_id).filter(PayrollData.period_id.in_(prev_period_ids)).distinct()
            prev_ids = {row[0] for row in prev_query.all()}
            if division != 'all' and prev_ids:
                employees = db.query(Employee).filter(Employee.id.in_(prev_ids), Employee.department == division).all()
                prev_ids = {employee.id for employee in employees}
            prev_headcount = len(prev_ids)

        avg_headcount = (current_headcount + prev_headcount) / 2 if (current_headcount + prev_headcount) > 0 else 0

        admissions_query = db.query(Employee).filter(
            Employee.admission_date >= period_start,
            Employee.admission_date < period_end,
        )
        terminations_query = db.query(Employee.admission_date, Employee.termination_date).filter(
            Employee.termination_date >= period_start,
            Employee.termination_date < period_end,
        )

        if division != 'all':
            admissions_query = admissions_query.filter(Employee.department == division)
            terminations_query = terminations_query.filter(Employee.department == division)

        if employee_ids_current:
            admissions_query = admissions_query.filter(Employee.id.in_(employee_ids_current))
            terminations_query = terminations_query.filter(Employee.id.in_(employee_ids_current))

        admissions = admissions_query.count()
        terminated_employees = terminations_query.all()
        terminations = len(terminated_employees)

        total_tenure_days = 0
        valid_tenure_count = 0
        for admission_date, termination_date in terminated_employees:
            if admission_date and termination_date:
                total_tenure_days += (termination_date - admission_date).days
                valid_tenure_count += 1

        avg_tenure_months = 0.0
        if valid_tenure_count > 0:
            avg_tenure_months = (total_tenure_days / valid_tenure_count) / 30.416

        turnover_rate = 0.0
        if avg_headcount > 0:
            turnover_rate = ((admissions + terminations) / 2) / avg_headcount * 100

        return {
            'turnover_rate': round(turnover_rate, 2),
            'admissions': admissions,
            'terminations': terminations,
            'avg_headcount': round(avg_headcount, 1),
            'avg_tenure_months': avg_tenure_months,
            'by_company': [],
            'top_divisions_turnover': [],
        }

    def handle_demographics(self):
        try:
            company, division, year, month, months_range = self._parse_filters()
            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                year, month = self._resolve_period(db, year, month)
                if not year or not month:
                    self.send_json_response({'error': 'Nenhum período encontrado'}, 404)
                    return

                current_date = date(year, month, 1)
                current_metrics = self._get_demographics_for_period(db, year, month, company, division)

                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    metrics = self._get_demographics_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month - 1]}/{str(p_year)[2:]}",
                        'average_age': metrics['average_age'],
                        'male_count': metrics['male_count'],
                        'female_count': metrics['female_count'],
                        'total_employees': metrics['total_employees'],
                    })

                self.send_json_response({
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range,
                    },
                    'current': current_metrics,
                    'evolution': evolution_data,
                })
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def _get_demographics_for_period(self, db, year, month, company='all', division='all'):
        periods_query = db.query(PayrollPeriod).filter(PayrollPeriod.year == year, PayrollPeriod.month == month)
        if company != 'all':
            periods_query = periods_query.filter(PayrollPeriod.company == company)

        periods = periods_query.all()
        if not periods:
            return {'average_age': 0, 'male_count': 0, 'female_count': 0, 'total_employees': 0, 'by_sex': [], 'age_ranges': []}

        period_ids = [period.id for period in periods]
        employee_ids = [row[0] for row in db.query(PayrollData.employee_id).filter(PayrollData.period_id.in_(period_ids)).distinct().all()]
        if not employee_ids:
            return {'average_age': 0, 'male_count': 0, 'female_count': 0, 'total_employees': 0, 'by_sex': [], 'age_ranges': []}

        emp_query = db.query(Employee).filter(Employee.id.in_(employee_ids))
        if division != 'all':
            emp_query = emp_query.filter(Employee.department == division)

        by_sex = db.query(Employee.sex, func.count(Employee.id).label('count')).filter(Employee.id.in_(employee_ids), Employee.sex.isnot(None))
        if division != 'all':
            by_sex = by_sex.filter(Employee.department == division)
        by_sex = by_sex.group_by(Employee.sex).all()

        today = date.today()
        employees = db.query(Employee.name, Employee.birth_date, Employee.department).filter(
            Employee.id.in_(employee_ids),
            Employee.birth_date.isnot(None)
        )
        if division != 'all':
            employees = employees.filter(Employee.department == division)
        emps = employees.all()

        age_groups = {'16-20': {'count': 0, 'employees': []}, '21-30': {'count': 0, 'employees': []}, '31-40': {'count': 0, 'employees': []}, '41-50': {'count': 0, 'employees': []}, '51-60': {'count': 0, 'employees': []}, '60+': {'count': 0, 'employees': []}}
        total_age = 0
        for name, birth_date, department in emps:
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            total_age += age

            if age <= 20:
                bucket = '16-20'
            elif age <= 30:
                bucket = '21-30'
            elif age <= 40:
                bucket = '31-40'
            elif age <= 50:
                bucket = '41-50'
            elif age <= 60:
                bucket = '51-60'
            else:
                bucket = '60+'

            age_groups[bucket]['count'] += 1
            age_groups[bucket]['employees'].append({'name': name, 'age': age, 'department': department or 'Não informado'})

        age_ranges = []
        for bucket in ['16-20', '21-30', '31-40', '41-50', '51-60', '60+']:
            if age_groups[bucket]['count'] > 0:
                age_ranges.append({
                    'range': bucket,
                    'count': age_groups[bucket]['count'],
                    'employees': sorted(age_groups[bucket]['employees'], key=lambda x: x['name'])
                })

        avg_age = (total_age / len(emps)) if emps else 0
        male_count = 0
        female_count = 0
        for sex, count in by_sex:
            if sex == 'M':
                male_count = count
            elif sex == 'F':
                female_count = count

        known_gender_total = male_count + female_count
        total_employees = len(employee_ids)

        return {
            'average_age': int(round(float(avg_age))) if avg_age else 0,
            'male_count': male_count,
            'female_count': female_count,
            'other_count': max(total_employees - known_gender_total, 0),
            'total_employees': total_employees,
            'by_sex': [{'sex': sex or 'Não informado', 'count': count} for sex, count in by_sex],
            'age_ranges': age_ranges,
        }

    def handle_payroll(self):
        try:
            company, division, year, month, _months_range = self._parse_filters()
            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                year, month = self._resolve_period(db, year, month)
                if not year or not month:
                    self.send_json_response({'error': 'Nenhum período encontrado'}, 404)
                    return

                period_query = db.query(PayrollPeriod).filter(PayrollPeriod.year == year, PayrollPeriod.month == month)
                if company != 'all':
                    period_query = period_query.filter(PayrollPeriod.company == company)

                periods = period_query.all()
                if not periods:
                    self.send_json_response({'periods': [], 'financial_stats': {}, 'totals': {}}, 200)
                    return

                period_ids = [period.id for period in periods]
                payroll_query = db.query(PayrollData).filter(PayrollData.period_id.in_(period_ids))
                if division != 'all':
                    employee_ids = [row[0] for row in db.query(Employee.id).filter(Employee.department == division).all()]
                    if not employee_ids:
                        self.send_json_response({'periods': [], 'financial_stats': {}, 'totals': {}}, 200)
                        return
                    payroll_query = payroll_query.filter(PayrollData.employee_id.in_(employee_ids))

                records = payroll_query.all()
                total_earnings = sum(float(record.gross_salary or 0) for record in records)
                total_net = sum(float(record.net_salary or 0) for record in records)
                total_deductions = total_earnings - total_net

                self.send_json_response({
                    'periods': [{'id': period.id, 'year': period.year, 'month': period.month, 'company': period.company} for period in periods],
                    'financial_stats': {
                        'total_earnings': total_earnings,
                        'total_deductions': total_deductions,
                        'total_net': total_net,
                    },
                    'totals': {
                        'employees': len({record.employee_id for record in records}),
                        'records': len(records),
                    },
                })
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def handle_tenure(self):
        try:
            company, division, year, month, months_range = self._parse_filters()
            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                year, month = self._resolve_period(db, year, month)
                if not year or not month:
                    self.send_json_response({'error': 'Nenhum período encontrado'}, 404)
                    return

                current_date = date(year, month, 1)
                current_metrics = self._get_tenure_for_period(db, year, month, company, division)

                evolution_data = []
                month_names_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                for i in range(months_range - 1, -1, -1):
                    period_date = current_date - relativedelta(months=i)
                    p_year = period_date.year
                    p_month = period_date.month
                    metrics = self._get_tenure_for_period(db, p_year, p_month, company, division)
                    evolution_data.append({
                        'year': p_year,
                        'month': p_month,
                        'month_name': f"{month_names_pt[p_month - 1]}/{str(p_year)[2:]}",
                        'average_tenure_years': metrics['average_tenure_years'],
                        'average_tenure_months': metrics['average_tenure_months'],
                        'total_employees': metrics['total_employees'],
                    })

                self.send_json_response({
                    'filters': {
                        'year': year,
                        'month': month,
                        'company': company,
                        'division': division,
                        'months_range': months_range,
                    },
                    'current': current_metrics,
                    'evolution': evolution_data,
                })
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def _get_tenure_for_period(self, db, year, month, company='all', division='all'):
        periods_query = db.query(PayrollPeriod).filter(PayrollPeriod.year == year, PayrollPeriod.month == month)
        if company != 'all':
            periods_query = periods_query.filter(PayrollPeriod.company == company)

        periods = periods_query.all()
        if not periods:
            return {'average_tenure_years': 0, 'average_tenure_months': 0, 'total_employees': 0, 'tenure_ranges': [], 'by_department': [], 'by_role': [], 'by_gender': {}}

        period_ids = [period.id for period in periods]
        employee_ids = [row[0] for row in db.query(PayrollData.employee_id).filter(PayrollData.period_id.in_(period_ids)).distinct().all()]
        if not employee_ids:
            return {'average_tenure_years': 0, 'average_tenure_months': 0, 'total_employees': 0, 'tenure_ranges': [], 'by_department': [], 'by_role': [], 'by_gender': {}}

        reference_date = date(year, month, 1)
        filtered_employee_ids = employee_ids
        if division != 'all':
            filtered_employee_ids = [row[0] for row in db.query(Employee.id).filter(Employee.id.in_(employee_ids), Employee.department == division).all()]
            if not filtered_employee_ids:
                return {'average_tenure_years': 0, 'average_tenure_months': 0, 'total_employees': 0, 'tenure_ranges': [], 'by_department': [], 'by_role': [], 'by_gender': {}}

        from sqlalchemy import func

        avg_tenure_days = db.query(
            func.avg(reference_date - Employee.admission_date)
        ).filter(
            Employee.id.in_(filtered_employee_ids),
            Employee.admission_date.isnot(None)
        ).scalar()

        if avg_tenure_days:
            if hasattr(avg_tenure_days, 'days'):
                total_days = avg_tenure_days.days
            else:
                total_days = float(avg_tenure_days)
            avg_tenure_years = total_days / 365.25
            avg_tenure_months = int(round(total_days / 30.44))
        else:
            avg_tenure_years = 0
            avg_tenure_months = 0

        employees = db.query(Employee.name, Employee.admission_date, Employee.department, Employee.position, Employee.sex).filter(
            Employee.id.in_(filtered_employee_ids),
            Employee.admission_date.isnot(None)
        ).all()

        tenure_groups = {
            'Até 6 meses': {'count': 0, 'employees': []},
            '6-12 meses': {'count': 0, 'employees': []},
            '1-3 anos': {'count': 0, 'employees': []},
            '3-5 anos': {'count': 0, 'employees': []},
            '5-10 anos': {'count': 0, 'employees': []},
            '10+ anos': {'count': 0, 'employees': []},
        }
        dept_totals = {}
        role_totals = {}
        gender_totals = {'M': {'total_months': 0, 'count': 0}, 'F': {'total_months': 0, 'count': 0}}

        for name, admission_date, dept, position, sex in employees:
            days = (reference_date - admission_date).days
            months = days / 30.44
            if months <= 6:
                bucket = 'Até 6 meses'
            elif months <= 12:
                bucket = '6-12 meses'
            elif days < 1095:
                bucket = '1-3 anos'
            elif days < 1825:
                bucket = '3-5 anos'
            elif days < 3650:
                bucket = '5-10 anos'
            else:
                bucket = '10+ anos'

            tenure_years_val = int(days / 365.25)
            tenure_months_val = int(round(days / 30.44)) % 12
            if tenure_years_val == 0 and tenure_months_val == 0:
                tenure_str = '0 meses'
            elif tenure_years_val == 0:
                tenure_str = f"{tenure_months_val} {'mês' if tenure_months_val == 1 else 'meses'}"
            elif tenure_months_val == 0:
                tenure_str = f"{tenure_years_val} {'ano' if tenure_years_val == 1 else 'anos'}"
            else:
                tenure_str = f"{tenure_years_val}a {tenure_months_val}m"

            tenure_groups[bucket]['count'] += 1
            tenure_groups[bucket]['employees'].append({'name': name, 'tenure': tenure_str, 'department': dept or 'Não informado'})

            dept_key = dept or 'Não informado'
            dept_totals.setdefault(dept_key, {'total_months': 0, 'count': 0})
            dept_totals[dept_key]['total_months'] += months
            dept_totals[dept_key]['count'] += 1

            role_key = position or 'Não informado'
            role_totals.setdefault(role_key, {'total_months': 0, 'count': 0})
            role_totals[role_key]['total_months'] += months
            role_totals[role_key]['count'] += 1

            sex_key = sex or 'Não informado'
            if sex_key in ['M', 'F']:
                gender_totals[sex_key]['total_months'] += months
                gender_totals[sex_key]['count'] += 1

        tenure_ranges = []
        for bucket in ['Até 6 meses', '6-12 meses', '1-3 anos', '3-5 anos', '5-10 anos', '10+ anos']:
            if tenure_groups[bucket]['count'] > 0:
                tenure_ranges.append({
                    'range': bucket,
                    'count': tenure_groups[bucket]['count'],
                    'employees': sorted(tenure_groups[bucket]['employees'], key=lambda item: item['name'])
                })

        by_department_results = []
        for department, totals in dept_totals.items():
            if totals['count'] > 0:
                by_department_results.append({'department': department, 'avg_months': int(round(totals['total_months'] / totals['count']))})
        by_department_results.sort(key=lambda item: item['department'])

        by_role_results = []
        for role, totals in role_totals.items():
            if totals['count'] > 0:
                by_role_results.append({'role': role, 'avg_months': int(round(totals['total_months'] / totals['count']))})
        by_role_results.sort(key=lambda item: item['avg_months'], reverse=True)
        by_role_results = by_role_results[:10]

        by_gender_results = {sex: (int(round(totals['total_months'] / totals['count'])) if totals['count'] > 0 else 0) for sex, totals in gender_totals.items()}

        return {
            'average_tenure_years': int(round(avg_tenure_years)),
            'average_tenure_months': avg_tenure_months,
            'total_employees': len(employees),
            'tenure_ranges': tenure_ranges,
            'by_department': by_department_results,
            'by_role': by_role_results,
            'by_gender': by_gender_results,
        }

    def handle_leaves(self):
        try:
            company, division, year, month, months_range = self._parse_filters()
            query_params = self._query_params()
            filter_leave_types = query_params.get('leave_type', [])
            if len(filter_leave_types) == 1 and filter_leave_types[0] == 'all':
                filter_leave_types = []

            db = self._get_db()
            if not db:
                self.send_json_response({'error': 'PostgreSQL não disponível'}, 500)
                return

            try:
                if year and month:
                    reference_date = date(int(year), int(month), 1)
                else:
                    reference_date = date.today().replace(day=1)

                leave_types = db.query(LeaveRecord.leave_type).distinct().all()
                leave_types_list = [item[0] for item in leave_types if item[0]]

                evolution = []
                for i in range(months_range - 1, -1, -1):
                    period_date = reference_date - relativedelta(months=i)
                    evolution.append(self._get_leaves_for_period(db, period_date, company, division, filter_leave_types))

                current_metrics = evolution[-1] if evolution else {}
                self.send_json_response({'evolution': evolution, 'current': current_metrics, 'leave_types': leave_types_list})
            finally:
                db.close()
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)

    def _get_leaves_for_period(self, db, reference_date, company=None, division=None, leave_type=None):
        if reference_date.month == 12:
            last_day = reference_date.replace(day=31)
        else:
            last_day = (reference_date.replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)

        employees_query = db.query(Employee).filter(Employee.is_active == True)
        if company and company != 'all':
            employees_query = employees_query.filter(Employee.company_code == company)
        if division and division != 'all':
            employees_query = employees_query.filter(Employee.department == division)

        total_employees = employees_query.count()

        base_query = db.query(
            Employee.id.label('emp_id'),
            Employee.name,
            Employee.department,
            Employee.position,
            Employee.company_code,
            Employee.unique_id,
            LeaveRecord.leave_type,
            LeaveRecord.days,
            LeaveRecord.start_date,
            LeaveRecord.end_date,
        ).join(LeaveRecord, LeaveRecord.employee_id == Employee.id).filter(
            Employee.is_active == True,
            LeaveRecord.start_date <= last_day,
            LeaveRecord.end_date >= reference_date,
        )

        if company and company != 'all':
            base_query = base_query.filter(
                (Employee.company_code == company) |
                (Employee.unique_id.like(f"{company}%"))
            )
        if division and division != 'all':
            base_query = base_query.filter(Employee.department == division)
        if leave_type and len(leave_type) > 0:
            base_query = base_query.filter(LeaveRecord.leave_type.in_(leave_type))

        leaves_data = base_query.all()

        unique_employees = set()
        by_type_dict = {}
        by_department_dict = {}
        by_role_dict = {}
        by_company_dict = {}
        total_duration = 0
        valid_duration_records = 0

        for emp_id, name, dept, pos, comp_code, uniq_id, l_type, days_col, start_date, end_date in leaves_data:
            unique_employees.add(emp_id)

            l_type = l_type or 'Não especificado'
            dept = dept or 'Não especificado'
            pos = pos or 'Não especificado'

            comp_val = str(comp_code).strip() if comp_code else ''
            if not comp_val and uniq_id and len(uniq_id) >= 4:
                comp_val = uniq_id[:4]

            if comp_val in ['0059', '59']:
                company_name = 'Infraestrutura'
            elif comp_val in ['0060', '60']:
                company_name = 'Empreendimentos'
            else:
                company_name = f"Matriz {comp_val}" if comp_val else 'Outra'

            calc_days = days_col if days_col is not None else (end_date - start_date).days if (end_date and start_date) else 0

            employee_payload = {'name': name, 'department': dept, 'type': l_type, 'days': calc_days}

            by_type_dict.setdefault(l_type, {'count': 0, 'employees': []})
            by_type_dict[l_type]['count'] += 1
            by_type_dict[l_type]['employees'].append(employee_payload)

            by_department_dict.setdefault(dept, {'count': 0, 'employees': []})
            by_department_dict[dept]['count'] += 1
            by_department_dict[dept]['employees'].append(employee_payload)

            by_role_dict.setdefault(pos, {'count': 0, 'employees': []})
            by_role_dict[pos]['count'] += 1
            by_role_dict[pos]['employees'].append(employee_payload)

            by_company_dict.setdefault(company_name, {'count': 0, 'employees': []})
            by_company_dict[company_name]['count'] += 1
            by_company_dict[company_name]['employees'].append(employee_payload)

            total_duration += float(calc_days)
            valid_duration_records += 1

        total_on_leave = len(unique_employees)
        absenteeism_rate = (total_on_leave / total_employees * 100) if total_employees > 0 else 0
        avg_duration = (total_duration / valid_duration_records) if valid_duration_records > 0 else 0
        total_leaves = len(leaves_data)

        by_type_results = []
        for leave_type_name, data in by_type_dict.items():
            by_type_results.append({
                'type': leave_type_name,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda item: item['name']),
            })

        by_department_results = []
        for dept_name, data in by_department_dict.items():
            by_department_results.append({
                'department': dept_name,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda item: item['name']),
            })
        by_department_results.sort(key=lambda item: item['count'], reverse=True)

        by_role_results = []
        for role_name, data in by_role_dict.items():
            by_role_results.append({
                'role': role_name,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda item: item['name']),
            })
        by_role_results.sort(key=lambda item: item['count'], reverse=True)
        by_role_results = by_role_results[:10]

        by_company_results = []
        for company_name, data in by_company_dict.items():
            by_company_results.append({
                'company': company_name,
                'count': data['count'],
                'percentage': round((data['count'] / total_leaves * 100), 1) if total_leaves > 0 else 0,
                'employees': sorted(data['employees'], key=lambda item: item['name']),
            })
        by_company_results.sort(key=lambda item: item['count'], reverse=True)

        return {
            'year': reference_date.year,
            'month': reference_date.month,
            'total_employees': total_employees,
            'total_on_leave': total_on_leave,
            'total_leave_records': total_leaves,
            'absenteeism_rate': round(absenteeism_rate, 2),
            'average_duration_days': round(avg_duration, 1),
            'by_type': by_type_results,
            'by_department': by_department_results,
            'by_role': by_role_results,
            'by_company': by_company_results,
        }

    def handle_cache_invalidate(self):
        try:
            data = self.get_request_data()
            indicator_type = data.get('indicator_type') if data else None

            invalidate_employees_cache()

            db = self._get_db()
            if db:
                try:
                    service = HRIndicatorsService(db)
                    service.invalidate_cache(indicator_type=indicator_type)
                finally:
                    db.close()

            message = f'Cache invalidado: {indicator_type} + employees' if indicator_type else 'Todo cache invalidado (indicators + employees)'
            self.send_json_response({'success': True, 'message': message})
        except Exception as ex:
            self.send_json_response({'error': str(ex)}, 500)