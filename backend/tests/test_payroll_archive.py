import io
import os
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

from app.routes.payroll import PayrollRouter


class _Handler:
    path = '/api/v1/payrolls/export-batch'


class _ArchiveRouter(PayrollRouter):
    def __init__(self, processed_dir, sent_dir):
        super().__init__(_Handler())
        self.processed_dir = processed_dir
        self.sent_dir = sent_dir
        self.response = None

    def _get_processed_base_dirs(self):
        return [self.processed_dir]

    def _get_sent_base_dirs(self):
        return [self.sent_dir]

    def get_request_data(self):
        return {'payrollType': '11', 'month': 3, 'year': 2026}

    def send_binary_response(self, data, content_type, filename, status_code=200):
        self.response = (data, content_type, filename, status_code)

    def send_json_response(self, data, status_code=200):
        self.response = (data, status_code)


class PayrollArchiveTests(unittest.TestCase):
    def test_parses_current_and_legacy_names(self):
        self.assertEqual(
            PayrollRouter._parse_period_from_filename('EN_005900001_11_03_2026.pdf'),
            ('11', 3, 2026),
        )
        self.assertEqual(
            PayrollRouter._parse_period_from_filename('005900001_holerite_marco_2026.pdf'),
            ('11', 3, 2026),
        )

    def test_zip_combines_processed_and_sent_and_prefers_processed_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            processed = os.path.join(temp_dir, 'processed')
            sent = os.path.join(temp_dir, 'sent')
            os.makedirs(processed)
            os.makedirs(sent)

            duplicate = 'EN_005900001_11_03_2026.pdf'
            sent_only = 'EN_005900002_11_03_2026.pdf'
            with open(os.path.join(sent, duplicate), 'wb') as file_obj:
                file_obj.write(b'sent-copy')
            with open(os.path.join(processed, duplicate), 'wb') as file_obj:
                file_obj.write(b'processed-copy')
            with open(os.path.join(sent, sent_only), 'wb') as file_obj:
                file_obj.write(b'sent-only')

            router = _ArchiveRouter(processed, sent)
            router.handle_export_payroll_batch()

            data, content_type, filename, status_code = router.response
            self.assertEqual(status_code, 200)
            self.assertEqual(content_type, 'application/zip')
            self.assertEqual(filename, 'Holerites_11_03_2026.zip')
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.assertEqual(set(archive.namelist()), {duplicate, sent_only})
                self.assertEqual(archive.read(duplicate), b'processed-copy')
                self.assertEqual(archive.read(sent_only), b'sent-only')


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class _Session:
    def __init__(self):
        self.closed = False
        self.period = SimpleNamespace(id=7, year=2026, month=2, period_name='Fevereiro 2026')
        self.records = [
            SimpleNamespace(employee_id=10, gross_salary=2500, net_salary=2100),
            SimpleNamespace(employee_id=11, gross_salary=3000, net_salary=2400),
        ]

    def query(self, model):
        if model.__name__ == 'PayrollPeriod':
            return _Query([self.period])
        return _Query(self.records)

    def close(self):
        self.closed = True


class _PeriodComparisonRouter(PayrollRouter):
    def __init__(self):
        handler = _Handler()
        handler.path = '/api/v1/payroll/period-comparison'
        super().__init__(handler)
        self.response = None

    def send_json_response(self, data, status_code=200):
        self.response = (data, status_code)


class PeriodComparisonTests(unittest.TestCase):
    def test_active_route_uses_modular_handler_and_returns_totals(self):
        session = _Session()
        router = _PeriodComparisonRouter()

        with patch('app.routes.payroll.SessionLocal', return_value=session):
            router.handle_get('/api/v1/payroll/period-comparison')

        data, status_code = router.response
        self.assertEqual(status_code, 200)
        self.assertEqual(data['periods'], [{
            'year': 2026,
            'month': 2,
            'period_names': 'Fevereiro 2026',
            'employee_count': 2,
            'total_earnings': 5500.0,
            'total_deductions': 1000.0,
            'total_net': 4500.0,
        }])
        self.assertTrue(session.closed)

    def test_rejects_invalid_month_range(self):
        with self.assertRaisesRegex(ValueError, 'YYYY-MM'):
            PayrollRouter._parse_comparison_month('2026-13')


if __name__ == '__main__':
    unittest.main()
