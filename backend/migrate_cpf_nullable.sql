-- Migração para tornar o campo CPF nullable na tabela employees
-- Necessário para permitir import de CSVs sem informação de CPF

ALTER TABLE employees ALTER COLUMN cpf DROP NOT NULL;
ALTER TABLE employees ALTER COLUMN phone DROP NOT NULL;
