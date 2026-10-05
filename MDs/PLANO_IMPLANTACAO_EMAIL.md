# Plano de implantação — envio de holerites por e-mail

## Objetivo

Permitir o envio individual e em lote de holerites por e-mail, mantendo WhatsApp e e-mail como canais independentes, com rastreabilidade, prevenção de duplicidade e acesso aos PDFs em `processed/` e `enviados/`.

## Marco 1 — infraestrutura SMTP

- [x] Configurar os modos STARTTLS, SSL/TLS e conexão sem criptografia.
- [x] Definir timeout e limite de tamanho do anexo.
- [x] Criar serviço SMTP isolado com mensagem texto/HTML e PDF anexo.
- [x] Validar destinatário e proteger cabeçalhos contra injeção.
- [x] Criar testes com SMTP simulado, sem envio externo.
- [x] Disponibilizar teste de conexão autenticado na API.
- [x] Adicionar o teste de conexão à tela de Scripts Úteis nas configurações.

Critério de aceite: conexão testável sem expor credenciais e mensagem gerada corretamente em teste automatizado.

## Marco 2 — auditoria por canal

- [x] Adicionar canal, destinatário, tentativas e identificador da mensagem ao registro de envio.
- [x] Generalizar item de fila para telefone ou e-mail.
- [x] Criar migração idempotente para bancos existentes.
- [x] Adicionar chave de idempotência por funcionário, competência, arquivo, canal e destinatário.
- [x] Preservar relatórios existentes de WhatsApp e contabilizar aceitações por e-mail.

Critério de aceite: sucessos e falhas de WhatsApp/e-mail aparecem separadamente e uma repetição acidental não duplica o envio.

## Marco 3 — processamento em lote por e-mail

- [x] Criar endpoint autenticado para iniciar o lote.
- [x] Resolver o PDF em `processed/` e `enviados/`, sem confiar em caminho enviado pelo navegador.
- [x] Validar previamente e-mails ausentes ou inválidos.
- [x] Processar a fila em segundo plano com tentativas e espera progressiva.
- [x] Não mover o PDF após o e-mail; o ciclo do arquivo não deve pertencer a um canal.
- [x] Registrar aceitação SMTP, falha e motivo sanitizado.

Critério de aceite: um lote continua em segundo plano, pode ser acompanhado e funciona mesmo quando o PDF já foi enviado pelo WhatsApp.

## Marco 4 — frontend

- [x] Adicionar seletor WhatsApp ou E-mail.
- [ ] Adicionar a opção combinada Ambos.
- [x] Exibir telefone/e-mail e elegibilidade por canal.
- [x] Adicionar assunto e corpo específicos do e-mail.
- [ ] Mostrar contagem prévia de válidos, inválidos e já enviados.
- [x] Mostrar resultados enviados, ignorados e falhas durante o lote.
- [ ] Acompanhar progresso por canal e repetir apenas falhas.
- [ ] Adicionar envio de teste na configuração SMTP.

Critério de aceite: o usuário confirma claramente destinatários e canais antes de criar o lote.

## Marco 5 — homologação e produção

- [ ] Configurar remetente corporativo e credenciais via variáveis de ambiente.
- [ ] Validar SPF, DKIM e DMARC do domínio remetente.
- [ ] Homologar com contas de teste de provedores diferentes.
- [ ] Confirmar limite de anexo e política de volume do servidor SMTP.
- [ ] Criar backup do banco antes da migração.
- [ ] Publicar imagens versionadas e manter a versão anterior disponível para rollback.

Critério de aceite: lote piloto aprovado pelo RH, logs sem dados sensíveis e rollback documentado.

## Decisões técnicas

- A aceitação do SMTP será registrada como `accepted`, não como `delivered`.
- WhatsApp e e-mail terão estados independentes.
- Credenciais, CPF, senha do PDF e conteúdo do anexo não serão registrados em logs.
- O backend resolverá o arquivo por nome em diretórios autorizados.
- Um envio já aceito exigirá uma ação explícita de reenvio.
