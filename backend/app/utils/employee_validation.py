"""Validation helpers for manually maintained employee identifiers."""

import re


SUPPORTED_COMPANY_CODES = {'0059', '0060'}


def normalize_cpf(value: str) -> str:
    digits = re.sub(r'\D', '', str(value or ''))
    if len(digits) != 11 or digits == digits[0] * 11:
        raise ValueError('CPF inválido')
    for length in (9, 10):
        total = sum(int(digits[index]) * (length + 1 - index) for index in range(length))
        if (total * 10 % 11) % 10 != int(digits[length]):
            raise ValueError('CPF inválido')
    return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'


def normalize_company_code(value: str) -> str:
    digits = re.sub(r'\D', '', str(value or '')).zfill(4)
    if digits not in SUPPORTED_COMPANY_CODES:
        raise ValueError('Código da empresa inválido')
    return digits
