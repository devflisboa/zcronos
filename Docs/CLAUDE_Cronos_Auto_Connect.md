# CLAUDE.md — Cronos Auto Connect

> Documento mestre de contexto, especificação técnica e instruções de implementação para Claude Code / VS Code.
> Idioma de interface, comentários públicos e documentação: **português do Brasil**.
> Situação em 23/10/2026: projeto em fase de protótipo; nenhum aplicativo web ou agente Android está implementado até aqui.

## 1. Missão do projeto

Desenvolver **Cronos Auto Connect**, uma aplicação web mobile-first, instalável como **PWA** no Xiaomi Redmi Note 13 e hospedável em um servidor público do proprietário. O painel deve visualizar o estado reportado pelo celular, manter histórico de conexões Bluetooth com a central Fiat Uconnect, apresentar diagnósticos e preparar automações seguras. Um **agente Android complementar**, futuramente instalado no telefone, fornecerá os dados que navegadores não conseguem coletar.

**Não prometer ou simular espelhamento/Android Auto sem fio.** A Uconnect já executa Android Auto pelo cabo USB; não foi comprovado que aceite o protocolo sem fio. Bluetooth Classic (pareamento para chamadas/áudio) não transmite sozinho o Android Auto, e uma PWA/serviço remoto não transforma uma central USB-only em receptora wireless. A implantação de um adaptador físico compatível seria uma trilha separada e opcional.

## 2. Contexto confirmado (não perguntar novamente)

- Veículo: **Fiat Cronos 2021 1.3 Firefly Flex**, central multimídia **Uconnect original de 7 polegadas**.
- Celular: **Xiaomi Redmi Note 13**, identificador de modelo via ADB `23129RA5FL`, **Android 15**.
- Android Auto **funciona perfeitamente pelo cabo USB**.
- O celular **pareia por Bluetooth** com a Uconnect, mas apenas parear não abre o Android Auto na tela.
- Nome Bluetooth observado: `Uconnect 8AP359A1DMU117850`.
- Endereço Bluetooth observado: `AC:C3:58:4C:5E:7E` (identificador de configuração local, **não** divulgar em logs públicos, capturas ou telemetria sem necessidade).
- Ferramentas locais: **Visual Studio Code**, terminal **PowerShell**; pasta Windows `D:\.ClaudeCode\Desenvolvimento\projetos-pessoais\Cronos_Auto_Connect`.
- Android Debug Bridge (ADB) instalado; dispositivo aparece autorizado como `device`; serial ADB observado `b18898ca` (não publicar).
- `adb shell id` retornou `uid=2000(shell)`; `adb shell command -v su` não retornou executável; `adb shell su` retornou `su: inaccessible or not found`. **Root NÃO está confirmado e não pode ser assumido**, apesar da afirmação inicial do usuário.
- Dump `dumpsys bluetooth_manager` mostrou `State: ON`, Uconnect em `Bonded devices`, `ConnectionState: STATE_DISCONNECTED`, perfil A2DP com `mActiveDevice: null`. Ou seja, **pareado, mas desconectado no momento do teste**.
- O usuário tem **servidor público na internet**, mas tipo de hospedagem, domínio e disponibilidade de Docker são desconhecidos. Evitar bloquear a implementação por isso: suportar Docker e execução local.
- O usuário não pode levar o notebook ao carro neste momento. Implementar com fixtures e modo de demonstração claramente rotulado, sem fabricar estados reais.

## 3. Princípios não negociáveis

1. **Precisão:** distinguir `pareado`, `Bluetooth ligado`, `conectado ao carro`, `conexão A2DP/HFP`, `Android Auto USB`, `Android Auto wireless` e `sem dados`. Não inferir um estado pelo outro.
2. **Offline-friendly:** dashboard renderiza sem agente; mostrar `Sem agente conectado` ou `Última atualização em ...`, nunca um verde falso.
3. **Mínimo privilégio:** não requerer root para MVP; nunca disponibilizar ADB, shell ou execução arbitrária via API pública.
4. **Segurança:** HTTPS, autenticação do painel, credencial individual do agente, secrets fora do repositório, rate limiting, validação de entrada, CORS restrito, logs sanitizados.
5. **Privacidade:** somente metadados necessários; não enviar contatos, mídia, mensagens, localização, logs de sistema integrais nem identificadores brutos ao servidor sem opt-in explícito.
6. **Boa experiência móvel:** português BR, visual limpo, acessível, responsivo, instalável como PWA; sem interação ao dirigir.
7. **Transparência:** usar dados reais apenas se recebidos e validados do agente; simulações devem ter rótulo permanente `DEMONSTRAÇÃO`.
8. **Entrega incremental verificável:** construir primeiro painel e API locais, depois agente Android; não confundir o protótipo web com solução para wireless AA.
9. **Não armazenar senhas ou tokens em `localStorage`**, não adicionar endpoint remoto de comando root/ADB.
10. **Não inventar compatibilidade**, APIs Android, recursos nativos ou modelos de hardware que não tenham sido verificados.

## 4. Escopo funcional

### MVP — entregar primeiro

- Interface PWA em `/`: painel com estado do telefone, Bluetooth, Wi-Fi, Uconnect e último relatório.
- Tela `/dispositivos`: Uconnect cadastrada (nome e MAC mascarado), perfil do Redmi, status de pareamento e conexão com fontes identificadas.
- Tela `/historico`: eventos de estado com horário, origem (`demo`, `android_agent`, `manual_test`) e filtros.
- Tela `/diagnostico`: verificações e instruções para ADB; relatórios de diagnóstico textuais reduzidos, sanitizados, exportação JSON.
- Tela `/configuracoes`: apelido do carro, MAC configurável, preferências de notificação, idioma, modo demonstração.
- API REST documentada em `/docs`, endpoint `/health`, banco SQLite local (migrável a PostgreSQL) e autenticação do painel.
- Gerador de eventos sintéticos **apenas no modo demo explícito**, com destaque visual.
- PWA com `manifest.webmanifest`, ícones próprios e service worker com cache somente de recursos estáticos; não cachear dados sensíveis autenticados por padrão.
- README com execução no Windows PowerShell e deploy via Docker Compose.
- Testes automatizados backend e smoke tests frontend.

### Fase 2 — agente Android

Preferir **Kotlin** para integração Bluetooth nativa, mesmo com backend Python. Se o usuário exigir Python no celular, avaliar ponte nativa (Kivy/pyjnius) experimental, mas não prometer equivalência de APIs nem execução confiável em segundo plano. O agente deve:

- Solicitar permissão `BLUETOOTH_CONNECT` (Android 12+) em runtime para aparelhos pareados e estados acessíveis; `BLUETOOTH_SCAN` só se necessário e justificado.
- Registrar estados do adaptador Bluetooth, aparelhos pareados, eventos `ACTION_ACL_CONNECTED` / `ACTION_ACL_DISCONNECTED` quando acessíveis, e estados de perfis via APIs públicas permitidas; identificar limitações de HFP/A2DP.
- Reportar eventos ao servidor por HTTPS com credencial própria, device ID aleatório, `event_id` UUID e carimbo UTC.
- Disponibilizar **foreground service** (se necessário e permitido), notificação visível, botão Pausar e desligamento voluntário; respeitar restrições de background e bateria do Android 15/HyperOS.
- Manter fila local com reenvio exponencial e deduplicação quando offline.
- Não controlar módulos sensíveis silenciosamente; abrir telas de configuração do sistema quando precisar de ação do usuário.
- Permitir iniciar aplicativos autorizados pelo usuário quando houver gatilho confiável; distinguir ação permitida de tentativa bloqueada pelo sistema.
- Implementar tela local de emparelhamento seguro com servidor (QR/código temporário), rotação/revogação do token e autorização explícita.

### Fora de escopo (até prova de viabilidade)

- Transmitir Android Auto wireless para Uconnect com **somente browser, Python ou Bluetooth**.
- Transmitir vídeo da tela do Redmi via Bluetooth Classic.
- Modificar firmware da Uconnect, forçar modo engenharia, contornar proteções, desbloquear bootloader ou instalar root.
- Controle remoto arbitrário do telefone pela internet ou execução de comandos enviados pelo servidor.
- Ler dados do carro via OBD sem hardware/protocolo adicional.

## 5. Arquitetura

```text
             Redmi Note 13 / Android 15
         +-----------------------------+
         | Chrome: PWA instalada       |
         | Painel HTTPS                |
         +-------------+---------------+
                       | HTTPS
                       v
Internet      +-------------------------+
              | Reverse proxy TLS       |
              | FastAPI / Python        |
              | REST + auth + events    |
              | SQLite / PostgreSQL     |
              +------------+------------+
                           ^
                           | HTTPS eventos autenticados
                           |
         +-----------------+-----------+
         | Agente Android (FASE 2)     |
         | Kotlin + Bluetooth APIs     |
         | Notificação e fila offline  |
         +-----------------------------+
                           |
                           | Bluetooth Classic (áudio/chamadas)
                           v
                  Uconnect Fiat Cronos

Android Auto pelo USB já funciona: fluxo independente.
```

**Frontend recomendado:** React + TypeScript + Vite, CSS/Tailwind opcional (não obrigatório), React Router, TanStack Query, i18n pt-BR. **Backend:** Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, uvicorn. **Banco:** SQLite para desenvolvimento/usuário único, PostgreSQL opcional na produção. **Empacotamento:** Docker multi-stage + Compose e documentação para execução sem Docker. Não usar um framework sofisticado se ele prejudicar a entrega do MVP.

### Estrutura sugerida

```text
Cronos_Auto_Connect/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .env.example
├── compose.yaml
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── core/{config.py,security.py}
│   │   ├── api/{auth.py,devices.py,events.py,health.py,settings.py}
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── db/
│   ├── alembic/
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── index.html
│   ├── public/{manifest.webmanifest,icons/}
│   ├── src/{app,components,pages,services,styles}
│   └── tests/
├── android-agent/          # criar somente na Fase 2
│   └── README.md
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── android-permissions.md
│   ├── deployment.md
│   └── threat-model.md
└── scripts/
    └── adb_diagnostics.ps1
```

Se uma estrutura simples for mais prática, Claude pode adaptá-la, mas deve justificar mudanças e manter a separação entre PWA, servidor e agente nativo.

## 6. Modelo de dados

- `User`: `id`, `username`, `password_hash`, `created_at`, `disabled`.
- `Vehicle`: `id`, `owner_id`, `nickname`, `make`, `model`, `year`, `head_unit_name`, `bluetooth_address_encrypted_or_hashed`, `created_at`.
- `Phone`: `id`, `owner_id`, `display_name`, `model_code`, `android_version`, `last_seen_at`, `agent_status`.
- `AgentCredential`: `id`, `phone_id`, `token_hash`, `created_at`, `expires_at`, `revoked_at`.
- `ConnectionEvent`: `id` UUID, `phone_id`, `vehicle_id`, `occurred_at` UTC, `received_at` UTC, `source`, `event_type`, `bluetooth_enabled` nullable, `paired` nullable, `acl_connected` nullable, `a2dp_connected` nullable, `hfp_connected` nullable, `wifi_enabled` nullable, `android_auto_usb` nullable, `android_auto_wireless` nullable, `details` objeto validado reduzido.
- `UserSettings`: flags de modo demo, notificações e preferências de visualização.

**Estado desconhecido = `null`**, nunca `false` por ausência de telemetria. Campos AA USB/wireless só podem ter valor real se houver mecanismo comprovado de observação; caso contrário permanecer `null`, exceto indicação manual rotulada como tal. Indexar `occurred_at`, `phone_id` e `vehicle_id`; impor unique em `event_id` para deduplicação. Prazos de retenção configuráveis.

## 7. Contrato da API proposto

Base: `/api/v1`. JSON, ISO 8601 UTC, erros consistentes `{ "error": {"code": "...", "message": "..."} }`.

| Método | Rota | Descrição | Autenticação |
|---|---|---|---|
| GET | `/health` | Liveness (`status`) | pública, sem dados sensíveis |
| POST | `/api/v1/auth/login` | Login + cookie de sessão HttpOnly/Secure | rate limited |
| POST | `/api/v1/auth/logout` | Sair | sessão |
| GET | `/api/v1/me` | Conta atual | sessão |
| GET | `/api/v1/vehicles` | Veículos próprios | sessão |
| PATCH | `/api/v1/vehicles/{id}` | Editar apelido/configuração | sessão + CSRF |
| GET | `/api/v1/phones` | Telefones próprios | sessão |
| GET | `/api/v1/status` | Últimos estados + freshness + source | sessão |
| GET | `/api/v1/events?limit=50&cursor=...` | Histórico paginado | sessão |
| GET | `/api/v1/settings` | Preferências | sessão |
| PATCH | `/api/v1/settings` | Alterar preferências | sessão + CSRF |
| POST | `/api/v1/agent/enroll/start` | Iniciar pareamento temporário | sessão + CSRF |
| POST | `/api/v1/agent/enroll/complete` | Finalizar pareamento | token de uso único |
| POST | `/api/v1/agent/events` | Ingestão de evento validado | token escopado agente |
| POST | `/api/v1/agent/revoke/{id}` | Revogar agente | sessão + CSRF |

Payload ilustrativo para `/api/v1/agent/events`:

```json
{
  "event_id": "a267b659-1127-4d44-bfb9-912999ffbb01",
  "occurred_at": "2026-10-23T18:31:00Z",
  "event_type": "bluetooth_state_changed",
  "bluetooth_enabled": true,
  "paired": true,
  "acl_connected": null,
  "a2dp_connected": null,
  "hfp_connected": null,
  "wifi_enabled": true,
  "android_auto_usb": null,
  "android_auto_wireless": null,
  "source": "android_agent"
}
```

Esse JSON é **exemplo de esquema**, não telemetria real. Backend deve garantir que o agente só envie eventos associados à sua própria identidade, validar campos e tamanho dos payloads e aplicar deduplicação. Identificadores fornecidos pelo agente nunca dão acesso a dados de outras contas. Não coletar localidade/latitude por padrão.

## 8. Regras de status e UX

Prioridade de exibição:

1. `DEMONSTRAÇÃO`: sempre indicar quando evento/screen vem de fixture.
2. `SEM DADOS`: agente não instalado ou nenhum relatório recebido.
3. `DESATUALIZADO`: último dado além de janela configurável, mostrar timestamp; não assumir desconectado.
4. `PAREADO`: Bluetooth no banco de pareados, **não** conectado.
5. `CONECTADO`: evento específico do dispositivo-alvo confirmado por API adequada; mostrar perfil disponível.

Telas devem exibir fonte e data/hora dos dados. A UI **não** deve ter botão “Conectar Android Auto sem fio” prometendo ação impossível. Pode conter seção “Android Auto USB: funciona (informado pelo usuário)” e aviso “Wireless: não verificado/suporte da central não confirmado”. Gráficos de eventos são opcionais, não prioritários. Layout principal para ~360–430 px de largura, contraste WCAG AA, estados de carregamento/erro, modo escuro opcional.

## 9. Desenvolvimento local no Windows / VS Code

Pré-requisitos: Python 3.12+, Node.js LTS, npm, Git; ADB opcional apenas para diagnóstico. Não exigir Android Studio para MVP web.

Fluxo desejado no README:

```powershell
# Executar na pasta do projeto no terminal do VS Code
cd D:\.ClaudeCode\Desenvolvimento\projetos-pessoais\Cronos_Auto_Connect

# backend (exemplo; ajustar ao pyproject.toml gerado)
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# outro terminal
cd D:\.ClaudeCode\Desenvolvimento\projetos-pessoais\Cronos_Auto_Connect\frontend
npm install
npm run dev
```

Adicionar script de bootstrap caso a política PowerShell bloqueie Activate.ps1 (alternativa: chamar `.venv\Scripts\python.exe` diretamente). Backend deve oferecer `GET /health`; frontend proxy `/api` para `http://127.0.0.1:8000` apenas em dev. Fornecer seed **somente para demo**, nunca misturar dados de teste com produção. Documentar criação segura do primeiro usuário administrador por CLI/setup inicial controlado, sem senha default fixa.

### Diagnóstico ADB — apenas computador local, não via endpoint remoto

```powershell
adb devices
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell settings get global bluetooth_on
adb shell settings get global wifi_on
adb shell dumpsys bluetooth_manager
```

Notas: `dumpsys` varia por fabricante/build; `ConnectionState` global não prova conexão especificamente à Uconnect. Filtros por nome/MAC em `Bonded devices` só comprovam pareamento. `su` não está disponível pelo ADB nos testes registrados. Ao exportar logs, mascarar serial, MACs, contas e IDs.

## 10. Publicação no servidor público

Como tipo de servidor é desconhecido, preparar:

- `compose.yaml` para `frontend` (build estático entregue por servidor web) + `backend` + volume persistente de banco, opcional PostgreSQL.
- Reverse proxy HTTPS com domínio e certificado válido (Caddy ou Nginx/Let's Encrypt); **não inventar domínio ou IP**.
- Exemplo `.env.example` apenas com placeholders (`APP_SECRET`, `DATABASE_URL`, `PUBLIC_BASE_URL`, `ALLOWED_ORIGINS`, `SESSION_COOKIE_SECURE`, etc.).
- Backend não deve expor porta desnecessária diretamente à internet. TLS no proxy.
- Habilitar backups, atualizações e rotação de logs. Expor só 80/443 quando aplicável.
- Sessão HttpOnly/Secure/SameSite e proteção CSRF em rotas mutáveis; CSP, headers de segurança, limitação de tentativas de login, restrição CORS.
- Healthcheck, reinício automático, migrações controladas, sem modo debug em produção.
- Configuração/instalação PWA sob HTTPS, incluindo atualização de service worker; evitar caches de API privada.
- Inclua plano alternativo se hospedagem não suporta Docker: build frontend estático + serviço Python via systemd/process manager.

## 11. Plano de entregas e critérios de aceite

### Etapa A — scaffold e backend

- [ ] Repo estruturado, `README.md`, `.env.example`, `.gitignore`.
- [ ] FastAPI sobe localmente e `GET /health` responde 200.
- [ ] Banco, migração inicial e autenticação funcionando.
- [ ] Testes de auth, validação, isolamento por usuário, deduplicação.

### Etapa B — PWA

- [ ] Painel português BR responsivo, instalável.
- [ ] Login/logout e sessão seguros.
- [ ] Páginas painel, dispositivos, histórico, diagnóstico e configurações.
- [ ] Estado real `Sem dados` por padrão; modo demo explicitamente destacado.
- [ ] Testes de responsividade, erros e acessibilidade.

### Etapa C — deploy

- [ ] Docker Compose sobe app completo.
- [ ] README de deploy com domínio variável, HTTPS, backups e rollback.
- [ ] Token/senha nenhum no código-fonte.

### Etapa D — agente Android (projeto independente)

- [ ] Manifest e runtime permissions corretas para Android 15.
- [ ] Lista de pareados após consentimento; leitura com API nativa.
- [ ] Conexões específicas identificadas sem depender só de `ConnectionState` global.
- [ ] Relatórios enviados com autenticação e fila offline.
- [ ] Indicador no app de que agente está ativo/pausado e opção de desligá-lo.
- [ ] Testes reais com a Uconnect **quando o usuário puder ir ao carro**.

**Métrica de sucesso MVP:** usuário consegue abrir URL HTTPS no Redmi, instalar a PWA, fazer login, configurar veículo, ver estado sem dados, acionar demo explicitamente e consultar histórico demo sem equívocos. **Não** medir sucesso como Android Auto wireless funcionando.

## 12. Estratégia de testes

- Backend: pytest + httpx, fixtures isoladas, PostgreSQL opcional em integração, checar 401/403/422, IDs não próprios, eventos duplicados, valores `null`.
- Frontend: unit tests (Vitest) e E2E (Playwright) para login, estados vazios, demo, responsividade e navegação.
- Segurança: ausência de shell remoto, validação de sessão/CSRF, secrets em env, fluxo de expiração de tokens do agente, sanitização de logs.
- Agente: testes instrumentados com permissão negada, BT desligado, BT ligado sem pareamento, pareado mas desconectado, conectado ao alvo, conectado a outro dispositivo, aparelho offline, bateria e reinício.
- Teste físico futuro com carro parado e sem distrações ao volante.

## 13. Riscos e decisões pendentes

| Tema | Situação | Decisão |
|---|---|---|
| Compatibilidade AA wireless | Não confirmada na Uconnect | Não prometer; sugerir hardware à parte se solicitado |
| Root no Redmi | Não disponível via `su` | Projetar sem root |
| Restrição de background Android 15/HyperOS | Requer teste em aparelho | Foreground service, consentimento, degradação graciosa |
| API Bluetooth Classic no browser | Insuficiente | Agente Android nativo |
| Hosting | Servidor público sem especificação | Compatibilidade Docker e manual |
| Wi-Fi do carro | Capacidade não verificada | Não inventar suporte AA wireless |
| Telemetria AA via APIs públicas | Não comprovada | Exibir desconhecido até mecanismo validado |

## 14. Instruções específicas para Claude Code

**Trabalhe em etapas com entregas de código executáveis, não apenas sugestões.** Ao iniciar:

1. Examine o diretório atual, identifique arquivos existentes, não sobrescreva sem revisar e preserve scripts ADB anteriores.
2. Resuma em 5–10 linhas seu entendimento e liste suposições mínimas sem bloquear progresso.
3. Implemente o MVP web/backend primeiro com tecnologias descritas, teste os comandos e corrija erros reais.
4. Documente exatamente quais comandos executar no PowerShell e como acessar a UI no Android pela rede/HTTPS.
5. Evite perguntar sobre sistema do celular, carro, MAC ou funcionamento do Android Auto USB: já constam aqui. Hospedagem específica só é necessária na etapa real de deploy.
6. Não declarar que root existe; tampouco instalar root ou modificar firmware.
7. Não construir endpoints de controle remoto de ADB, nem baixar scripts externos arbitrários.
8. Separe claramente tarefas concluídas de propostas; reporte testes realmente executados e limitações.
9. Inclua screenshots apenas se forem efetivamente geradas e verificadas no ambiente.
10. Ao final de cada etapa, apresente arquivos criados, comandos para iniciar, resultados dos testes e próximos passos.

### Prompt de execução inicial (copiar para Claude)

> Leia integralmente o arquivo `CLAUDE.md` na raiz deste repositório e implemente **Etapas A e B (MVP completo)** do Cronos Auto Connect. Comece inspecionando o projeto existente. Crie backend FastAPI com autenticação, banco de dados, endpoints definidos e testes; depois frontend React/TypeScript responsivo e instalável como PWA, em português BR. Modele corretamente dados desconhecidos, pareados e conectados, com demonstração opt-in rotulada. Preserve a segurança; não assuma root nem suporte Android Auto wireless. Entregue código executável no Windows/VS Code, README e `.env.example`; execute testes disponíveis e informe honestamente o que foi testado. **Não implemente o agente Android ainda**: apenas prepare seu contrato de API. Não faça perguntas que já estão respondidas neste documento.

## 15. Fontes primárias para conferir durante a implementação

- Android — permissões Bluetooth e runtime (Android 12+): https://developer.android.com/develop/connectivity/bluetooth/bt-permissions
- Android — Bluetooth API: https://developer.android.com/develop/connectivity/bluetooth
- Android — restrições serviços em primeiro plano: https://developer.android.com/develop/background-work/services/foreground-services
- Android Auto — requisitos da conexão sem fio: https://www.android.com/intl/pt-BR_br/auto/
- Android Auto — configuração oficial: https://support.google.com/androidauto/answer/6348029
- FastAPI — deploy e HTTPS: https://fastapi.tiangolo.com/deployment/https/
- Web Bluetooth — capacidade BLE/GATT: https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API
- PWA — instalação: https://web.dev/learn/pwa/installation/

**Fim da especificação.**
