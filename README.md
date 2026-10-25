# AUTOVIU — Dashboard de veículos

Aplicação Flask/Jinja e MySQL para gestão de veículos, abastecimentos, despesas, manutenção e relatórios, com isolamento por usuário.

## Documentação oficial do projeto

- [Roadmap e escopo das Fases 1–3](Docs/ROADMAP.md).
- [Entregas, arquivos alterados, decisões e limitações](Docs/FASE3_ROADMAP.md).
- [Operação no Docker local e registro da implantação](Docs/DOCKER_LOCAL.md).
- [Arquitetura SaaS](Docs/ARQUITETURA_SAAS.md).
- [Migração e preservação dos dados](Docs/PLANO_MIGRACAO.md).
- [Padrões de interface mobile](Docs/GUIA_UIUX_MOBILE.md).

Os documentos de arquitetura e migração contêm o baseline histórico. O acompanhamento local nos dois roadmaps distingue código implementado, configuração pendente e comportamento ainda não homologado. As Fases 4–6 não fazem parte desta entrega.

## Acesso local

Com o Docker Desktop iniciado e o ambiente configurado conforme o guia:

```powershell
docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml ps
```

Aplicação: <http://localhost:5012>. MySQL: `127.0.0.1:3311`. A instalação com banco existente exige backup, auditoria e migração antes de iniciar a versão nova; consulte o guia. Não use o Compose de produção para esta execução local.

## Recursos implementados no código

- Cadastro, confirmação, recuperação de senha, sessões, Google e passkeys.
- Múltiplos veículos, condutor, CNH/CRLV com OCR e revisão dos dados.
- FIPE do veículo ativo ou consulta avulsa, com confirmação para atualizar o cadastro.
- Galeria privada, alertas, relatórios e exportação CSV.
- Trial, planos, assinaturas/faturas Asaas e administração.
- Validação da agenda, isolamento dos dados e diagnóstico de configuração.

OCR, e-mail, Google, passkeys, push e cobrança dependem de configuração e homologação. Não apresentar presença de código como integração real aprovada. Frota e vínculo Google têm decisões documentais pendentes.

## Verificação e dados

Testes funcionais permanecem reservados para a etapa final por orientação do usuário. O registro de operação Docker distingue build, inicialização, revisão do banco e resposta HTTP dos testes funcionais. `.env`, `.env.local`, documentos pessoais, uploads e backups não devem ser publicados; o contexto Docker já possui exclusões para esses dados.
