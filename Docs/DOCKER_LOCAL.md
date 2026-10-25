# AUTOVIU — Operação no Docker local

## Escopo e referências

Ambiente Windows/PowerShell com Docker Desktop e containers Linux. Este procedimento usa exclusivamente `docker-compose.local.yml`, projeto Compose `dashboardcarro`, sem implantar em produção. Referências consultadas: `ROADMAP.md` e `FASE3_ROADMAP.md` (escopo, funcionalidades e pendências); `ARQUITETURA_SAAS.md` (Flask, Gunicorn e MySQL); `PLANO_MIGRACAO.md` (backup e preservação); `GUIA_UIUX_MOBILE.md` (formulários). O detalhamento por funcionalidade e arquivo permanece no roadmap da Fase 3, sem duplicar sua especificação.

## Serviços, portas e persistência

| Serviço | Execução | Acesso no Windows | Persistência |
|---|---|---|---|
| web | Python 3.11, Gunicorn, 1 worker gthread/4 threads | http://localhost:5012 | Código montado em `/app`; fotos em `static/uploads/veiculos` do checkout |
| db | MySQL 8.0 | `127.0.0.1:3311` | Volume `dashboardcarro_mysql_data_local` |

As portas são publicadas somente em `127.0.0.1`. O serviço web lê `.env.local` e substitui `DB_HOST` por `db:3306`. Alertas automáticos são forçados a `false` no Compose local, impedindo disparos pelo scheduler. O MySQL possui healthcheck; a aplicação aguarda o banco saudável. A senha fixa do MySQL neste Compose é exclusiva de desenvolvimento e não deve ser reutilizada em produção.

O Dockerfile executa o processo como `appuser`. `.dockerignore` exclui ambientes, segredos, backups, uploads e PDFs da pasta Docs do contexto de build. O bind mount local permite leitura do checkout pelo container: as exclusões de build não são isolamento do diretório montado. O Compose de produção usa outra configuração de ambiente e volume de fotos.

## Configuração

Preservar `.env.local` existente; não sobrescrevê-lo com exemplos. Em uma máquina nova, usar `.env.example` como referência, com `FLASK_ENV=development`, segredo aleatório próprio, `DB_USER=root`, `DB_NAME=car_management` e credenciais compatíveis com o banco do Compose local. Não imprimir nem versionar valores reais. SMTP, OpenAI/modelo, Google, RP/origem HTTPS, VAPID e Asaas continuam opcionais até configurar suas funcionalidades. FIPE aceita token opcional no backend. Frota permanece dependente de decisão comercial.

`ENVIRONMENT` identifica o perfil da classe de configuração para o diagnóstico. Ele não depende de `DEBUG`, pois a CLI Flask pode sobrescrever esse sinalizador. HTTP/cookies locais não devem ser confundidos com os requisitos HTTPS de produção ou das passkeys.

## Atualizar um banco local existente

1. Iniciar Docker Desktop. Confirmar o projeto correto e preservar volumes.
2. Iniciar somente o banco e construir a imagem: comandos abaixo.
3. Fazer dump antes de qualquer migração. O dump contém dados privados e deve permanecer em `backups/`, ignorado pelo Git/build.
4. Auditar vínculos com a factory sem criação automática de tabelas/scheduler.
5. Se houver órfãos, interromper e identificar seus proprietários. Não escolher automaticamente o primeiro usuário. A migração histórica a001 contém atribuições antigas; o banco desta implantação foi auditado antes de executá-la.
6. Aplicar migrações somente após backup e auditoria; subir a aplicação.

```powershell
docker compose -f docker-compose.local.yml up -d db
docker compose -f docker-compose.local.yml build web
# Dump dentro do container, usando sua variável de ambiente sem imprimir senha
docker compose -f docker-compose.local.yml exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --routines --triggers --no-tablespaces "$MYSQL_DATABASE" --result-file=/tmp/autoviu-pre-local.sql'
New-Item -ItemType Directory -Force backups | Out-Null
# Trocar o nome a cada atualização para preservar backups anteriores
docker compose -f docker-compose.local.yml cp db:/tmp/autoviu-pre-local.sql backups/autoviu-pre-atualizacao.sql
docker compose -f docker-compose.local.yml run --rm --no-deps web flask --app "app:create_app('development', initialize_database=False, start_scheduler=False)" dados-auditar
docker compose -f docker-compose.local.yml run --rm --no-deps web alembic upgrade head
docker compose -f docker-compose.local.yml up -d
```

A cadeia Alembic atual pressupõe as tabelas do baseline histórico; `alembic upgrade head` sozinho não inicializa um banco totalmente vazio. Em uma instalação vazia, criar primeiro o schema dos modelos com a factory sem scheduler e, em seguida, executar as migrações antes de servir tráfego. Não usar esse procedimento para mascarar migração pendente em banco existente. A factory padrão ainda chama `create_all`; isso não substitui a evolução de colunas pelo Alembic.

## Operação e diagnóstico

```powershell
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.local.yml logs --tail 80 web
docker compose -f docker-compose.local.yml exec -T web alembic current
docker compose -f docker-compose.local.yml exec -T web flask --app "app:create_app('development', initialize_database=False, start_scheduler=False)" configuracao-diagnosticar
docker compose -f docker-compose.local.yml exec -T web flask --app "app:create_app('development', initialize_database=False, start_scheduler=False)" dados-auditar
# Parar sem remover containers ou volumes
docker compose -f docker-compose.local.yml stop
# Retomar
docker compose -f docker-compose.local.yml up -d
```

Não remover volumes para corrigir inicialização. Antes de restaurar um dump ou reverter migrações, preservar também o estado atual; restauração substitui dados e precisa de decisão específica. `create_user.py` permite criação interativa de conta pelo operador, sem publicar senha na documentação. As contas existentes foram preservadas nesta subida; nenhuma senha foi redefinida.

## Registro da implantação local — 24/10/2026, horário de Brasília

- Docker Desktop iniciado; imagem `dashboardcarro-web` construída com as dependências atuais.
- Backup pré-migração: `backups/autoviu-pre-docker-20261024.sql`, 15.062 bytes, fora do Git/build.
- Banco anterior sem `alembic_version`; auditoria anterior à migração sem vínculos inválidos.
- Migrações a001, a002, a003 e a004 executadas somente no MySQL Docker local; revisão confirmada `a004 (head)`.
- Contagens antes/depois: 2 veículos, 15 abastecimentos, 14 despesas, 15 manutenções, 0 corridas Uber e 0 semanas Uber; zero vínculos inválidos nas seis relações auditadas. Não equivale a comparação integral de cada campo nem ensaio de restauração do dump.
- Containers `dashboardcarro-db-1` e `dashboardcarro-web-1` iniciados; MySQL saudável e Gunicorn escutando na porta interna 5000.
- Diagnóstico operacional executado sem rede externa; integrações continuam pendentes de configuração/homologação. Perfil local reconhecido como desenvolvimento após ajuste de `ENVIRONMENT`.
- Disponibilidade confirmada: login em `http://localhost:5012/auth/login` e `http://127.0.0.1:5012/auth/login`, e cadastro em `http://127.0.0.1:5012/auth/registro`, retornaram HTTP 200 com `curl.exe --noproxy '*'`. `Invoke-WebRequest` no ambiente apresentou timeout; a causa não foi confirmada. A verificação direta confirmou o acesso, sem alterar proxy ou firewall do Windows.
- Nenhuma implantação de produção, mensagem, cobrança ou consulta de preço FIPE foi realizada. Testes unitários, integração funcional e Cypress continuam reservados para a etapa final; build e disponibilidade não aprovam essas funcionalidades.

## Pendências documentadas

Resolver divergências Frota e vínculo Google; configurar provedores; homologar documentos, autenticação, notificações e cobrança; executar testes finais e validar migração/rollback em ambiente dedicado. A operação local não encerra o aceite das Fases 1–3. Este guia supre a lacuna de implantação local reproduzível e separa evidência operacional de aprovação funcional.
