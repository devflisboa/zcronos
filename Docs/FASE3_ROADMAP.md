# AUTOVIU — Roadmap Fase 3

**Criado em:** 24/10/2026  
**Atualizado em:** 24/10/2026  
**Status:** Em execução

---

## Estado atual (baseline 24/10/2026)

| Item | Status |
|---|---|
| Fase 0–2 (auth, multi-tenant, múltiplos veículos) | ✅ Produção |
| Rebrand AUTOVIU (gold/dark, Orbitron, Λ) | ✅ Produção |
| UI/UX mobile-first (Lucide icons, sidebar, overflow corrigido) | ✅ Produção |
| Cypress 53/53 + Visual Audit 24 screenshots | ✅ Produção |
| Auditoria 360° (redesign Meus Veículos, boot timing, None fix) | ✅ Produção |

---

## Visão Geral

A Fase 3 expande o AUTOVIU de uma ferramenta de gestão pessoal para um SaaS completo com monetização, perfil de condutor e inteligência documental.

---

## 3.1 — Monetização (Asaas)

**Objetivo:** Converter usuários do plano `free` em pagantes.

| Plano | Veículos | Preço |
|---|---|---|
| Free | 1 | R$ 0/mês |
| Pro | 3 | R$ 14,90/mês |
| Frota | Ilimitado | R$ 39,90/mês |

**Implementação:**
- Integração com Asaas (API de cobranças)
- Webhook para atualizar `plano` no banco ao confirmar pagamento
- Tela de upgrade dentro do app (`/plano`)
- Trial de 14 dias para o plano Pro

---

## 3.2 — Cadastro Público (Registro de Usuários)

**Objetivo:** Permitir novos usuários se cadastrarem sem intervenção do superadmin.

**Fluxo:**
1. Tela `/registro` pública com e-mail + senha + nome
2. Verificação por e-mail (token de ativação)
3. Usuário entra no plano `free` automaticamente
4. Onboarding: perfil do condutor com CNH opcional, seguido do primeiro veículo com CRLV opcional; revisão antes de salvar

---

### Entrega local — cadastro público (24/10/2026)

Implementado e validado localmente; publicação e entrega real de e-mail pendentes.

- Cadastro: GET/POST `/auth/registro`, nome, e-mail normalizado e senha confirmada.
- Novas contas: plano `free`, status `pendente`, `email_confirmado=False`. Esses campos já existem; nenhuma migração de banco necessária.
- Confirmação: GET abre a tela; POST protegido por CSRF ativa a conta. Token assinado com validade de 24 horas, vinculado ao ID e ao e-mail; após ativação não pode ser reutilizado.
- Reenvio: GET/POST `/auth/reenviar-confirmacao`. Resposta genérica para não informar se um endereço existe. Cadastro repetido não altera a senha nem dispara novo envio.
- Contas existentes com status ativo continuam funcionando mesmo sem confirmação anterior. Novas contas pendentes não conseguem iniciar sessão.
- Após login, usuários sem veículo e sem perfil seguem para `/condutor/?cadastro=1`. Podem preencher manualmente, importar a CNH ou escolher informar o condutor depois. O próximo passo é `/veiculos/novo`, com importação opcional do CRLV. Esse direcionamento foi integrado posteriormente ao cadastro inicial.
- Limites de POST por IP: registro 5/hora, reenvio 3/hora e confirmação 30/hora. Seguem o Flask-Limiter existente; em development os limites ficam desativados pela configuração do projeto.
- Falha SMTP preserva a conta pendente e permite tentar o reenvio após corrigir a configuração. Logs registram apenas a classe da falha, sem destinatário ou token.
- Templates de autenticação compartilham o layout de login existente. Respostas usam `Cache-Control: no-store` e `Referrer-Policy: no-referrer`.

**Arquivos:** `blueprints/auth/routes.py` (fluxo e proteção do redirecionamento de login), `services/email_service.py` (tokens e SMTP), `config.py` e `.env.example` (configuração), `templates/auth/login.html` e três novos templates de registro/confirmação/reenvio (interface), `tests/test_registro.py` (verificação isolada).

**Configuração antes de publicar:** preencher no ambiente do container `PUBLIC_BASE_URL` (origem pública confiável, HTTPS em produção), `MAIL_SERVER`, `MAIL_PORT` (587), `MAIL_USE_TLS` (true), `MAIL_USERNAME`, `MAIL_PASSWORD` e `MAIL_DEFAULT_SENDER`. O Compose existente já recebe o arquivo de ambiente. Transporte implementado: SMTP com STARTTLS; não SMTP SSL implícito na porta 465. Não gravar segredos no Git.

**Validação:** no PowerShell, na raiz do projeto, executar `python -m unittest discover -s tests -v`. Resultado local: 11 testes aprovados com SQLite em memória e SMTP simulado; nenhum envio real e nenhum acesso ao banco de produção. Antes de liberar cadastro publicamente, validar entrega com o provedor configurado e fazer teste de ponta a ponta no ambiente de homologação.

**Referências e lacunas:** este fluxo segue a prioridade 3.2 deste documento, o blueprint auth e o isolamento definidos em `ARQUITETURA_SAAS.md`, e a preservação de dados de `PLANO_MIGRACAO.md`. O provedor de e-mail e suas credenciais ainda precisam ser definidos. A divergência de preço/limites Frota entre este documento e `ROADMAP.md` permanece pendente para a etapa de monetização; os limites atuais não foram alterados. Rate limiting compartilhado entre workers continua dependente da configuração de armazenamento do Flask-Limiter; memória local não fornece limite global entre processos.

---

## 3.3 — Perfil do Condutor

**Objetivo:** Associar dados do motorista ao veículo.

**Campos:**
- Nome completo, CPF, data de nascimento
- Categoria CNH, número de registro CNH
- Data de validade da CNH
- Alertas automáticos de vencimento (30 dias antes)

**Modelo de dados:**
```python
class Condutor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    nome = db.Column(db.String(120))
    cpf = db.Column(db.String(14))
    cnh_numero = db.Column(db.String(20))
    cnh_categoria = db.Column(db.String(5))      # A, B, AB, C, D, E
    cnh_validade = db.Column(db.Date)
    cnh_primeira_habilitacao = db.Column(db.Date)
```

---

## 3.4 — Upload Inteligente de Documentos (CNH + CRLV)

**Objetivo:** O usuário faz upload da foto/PDF do documento e o app preenche os campos automaticamente via OCR + IA.

### Integração do cadastro — atualização local de 24/10/2026

- Sequência: conta confirmada → condutor/CNH opcional → veículo/CRLV → painel. Login por senha, Google e passkey reutilizam o mesmo direcionamento. Contas com veículo ativo seguem para o painel.
- O cadastro público continua solicitando nome, e-mail e senha. Importar documentos exige sessão autenticada, conforme o requisito de segurança já documentado.
- O perfil aproveita o nome da conta como preenchimento inicial; o nome completo extraído da CNH é revisado e salvo no perfil do condutor, sem substituir automaticamente o nome de acesso da conta.
- O usuário pode pular o perfil por POST protegido por CSRF. A preferência vale para sua sessão e é vinculada ao ID da conta; documentos e dados pessoais não são guardados na sessão. Caso saia antes de cadastrar o veículo e não tenha criado perfil, a etapa opcional poderá aparecer novamente no próximo login.
- No formulário do veículo, uma opção explícita permite vincular o perfil do próprio usuário como condutor. IDs de condutores enviados pelo cliente não são utilizados para esse vínculo.
- CNH e CRLV compartilham o mesmo componente de importação. O arquivo é opcional, o conteúdo extraído preenche os campos do formulário e os campos ausentes permanecem para preenchimento manual. Não se garante extrair todas as informações de documentos ilegíveis nem campos fora do cadastro definido.
- A interface pede confirmação antes de substituir valores existentes, destaca os campos preenchidos e informa quantos campos foram extraídos. Falhas, sessão expirada e tempo excedido não apagam os campos; o botão de salvar fica desabilitado durante a leitura.
- Sem OPENAI_API_KEY e OPENAI_VISION_MODEL configurados, a interface informa a indisponibilidade da leitura automática e mantém o cadastro manual utilizável. O serviço externo não foi acionado nesta atualização.

**Arquivos desta integração:** novo `services/cadastro_service.py` (direcionamento centralizado); `blueprints/auth/routes.py`, `blueprints/auth/google.py`, `blueprints/auth/seguranca.py` e `blueprints/main/routes.py` (entrada no fluxo); `blueprints/condutor/routes.py` (salvar/continuar ou pular); `blueprints/veiculo/routes.py` (vínculo autorizado do condutor); `templates/auth/registro.html`, `templates/condutor/perfil.html`, `templates/veiculos/form.html`, `templates/_importar_cnh.html`, novos `templates/_cadastro_etapas.html` e `templates/_importar_documento.html`; `static/js/documentos.js` e novo `static/css/cadastro.css` (interface, revisão e estados).

**Referências e lacunas:** as seções 3.2–3.4 deste documento orientam a sequência e os campos; `ARQUITETURA_SAAS.md` orienta o isolamento; `GUIA_UIUX_MOBILE.md`, seções 7–9, orienta etapas, labels, preservação de dados e estados de carregamento/erro. A ligação entre as telas não estava documentada de forma completa; este registro passa a descrevê-la. A configuração do provedor de OCR continua pendente. Este ajuste não adiciona migrações, mas depende dos modelos e migrações da Fase 3 já preparados anteriormente.

**Validação:** revisão por leitura dos arquivos; nenhum teste foi executado, conforme orientação de reservar testes para a etapa final. Incluir nessa etapa os redirecionamentos após os três modos de login, pular/retomar cadastro, vínculo de condutor, revisão de campos importados, erros de leitura e telas pequenas. As expectativas dos testes anteriores sobre o primeiro login devem acompanhar a nova sequência.

### Fluxo do CRLV (Certificado de Registro e Licenciamento de Veículo)

```
Upload CRLV (foto/PDF)
        ↓
OCR + extração via GPT-4 Vision
        ↓
Campos extraídos:
  - Placa
  - Marca / Modelo
  - Ano de fabricação / Ano modelo
  - Cor
  - Chassi
  - Renavam
  - Proprietário
        ↓
Pré-preenche formulário de cadastro do veículo
        ↓
Usuário revisa e confirma
```

### Fluxo da CNH (Carteira Nacional de Habilitação)

```
Upload CNH (foto frente + verso, ou PDF digital)
        ↓
OCR + extração via GPT-4 Vision
        ↓
Campos extraídos:
  - Nome completo
  - CPF
  - Data de nascimento
  - Número de registro
  - Categoria (A, B, AB, C, D, E)
  - Data de validade
  - Data da primeira habilitação
        ↓
Pré-preenche formulário do perfil do condutor
        ↓
Usuário revisa e confirma
```

### Stack técnica

| Componente | Opção Principal | Alternativa |
|---|---|---|
| OCR | GPT-4 Vision (OpenAI API) | Google Cloud Vision |
| Armazenamento temporário | `/tmp` do servidor (apagar após extração) | AWS S3 (criptografado) |
| Formato aceito | JPG, PNG, PDF (até 10 MB) | — |
| Biblioteca PDF | PyMuPDF (`fitz`) | pdf2image + Pillow |

### Endpoint backend

```python
@bp.route('/veiculo/upload-crlv', methods=['POST'])
@login_required
def upload_crlv():
    arquivo = request.files.get('crlv')
    # 1. Salva temporariamente
    # 2. Converte PDF → imagem se necessário
    # 3. Envia para GPT-4 Vision com prompt estruturado
    # 4. Parseia JSON de resposta
    # 5. Deleta arquivo temporário
    # 6. Retorna campos extraídos como JSON
    return jsonify(campos_extraidos)
```

### Prompt para GPT-4 Vision (CRLV)

```
Analise esta imagem de um CRLV (Certificado de Registro e Licenciamento de Veículo) 
brasileiro e extraia os seguintes campos em formato JSON:
{
  "placa": "",
  "marca": "",
  "modelo": "",
  "ano_fabricacao": "",
  "ano_modelo": "",
  "cor": "",
  "chassi": "",
  "renavam": ""
}
Retorne apenas o JSON, sem explicações. Se um campo não estiver visível, use null.
```

### Segurança

- Arquivos deletados do servidor imediatamente após extração (nunca persistidos)
- Não armazenar dados brutos do documento no banco — apenas os campos extraídos
- Validar tipo MIME antes de processar (aceitar apenas image/* e application/pdf)
- Limite de tamanho: 10 MB por upload
- Rate limit: 5 uploads por hora por usuário

### UX no formulário

```
[ Preencher manualmente ]  ou  [ Importar do CRLV ]
                                        ↓
                              [ Selecionar arquivo ]
                                        ↓
                              [  Analisando...  ]  ← spinner
                                        ↓
                              Campos pré-preenchidos
                              (editáveis pelo usuário)
```

---

## 3.5 — Alertas Inteligentes

**Objetivo:** Notificações proativas via e-mail e push notification.

| Alerta | Gatilho |
|---|---|
| CNH próxima do vencimento | 60 e 30 dias antes |
| CRLV vencendo | 30 dias antes do licenciamento |
| Revisão do fabricante | Km atingido (conforme agenda) |
| Seguro vencendo | 30 dias antes |
| IPVA | Aviso em janeiro com valor estimado |

---

## 3.6 — Galeria de Fotos do Veículo

**Objetivo:** Donos de carro adoram registrar e mostrar o veículo. Uma galeria dentro da ficha do carro cria engajamento e diferencia o AUTOVIU de apps só de gestão.

### Funcionalidades

**Upload de fotos:**
- Câmera do celular ou galeria (input `type="file" accept="image/*" capture="environment"`)
- Múltiplas fotos por veículo (limite: 20 fotos por carro)
- Compressão automática no frontend antes do upload (via `canvas` + `toBlob`) para reduzir tráfego
- Formatos: JPG, PNG, HEIC (convertido para JPG no servidor via Pillow)

**Galeria:**
- Grid de thumbnails na seção "Histórico" do veículo
- Lightbox ao clicar na foto (fullscreen com swipe mobile)
- Cada foto pode ter uma legenda opcional ("Na entrega", "Carnaval 2025", "Rodinha nova")
- Foto de capa (primeira foto = destaque no card do veículo em "Meus Veículos")

**Compartilhamento nas redes sociais:**
- Botão "Compartilhar" gera uma imagem estilizada com:
  - Foto do carro em destaque (fundo preto com borda dourada AUTOVIU)
  - Overlay inferior: `{Marca} {Modelo} {Ano}` + `{Km} km · {Custo/km}`
  - Logo AUTOVIU no canto inferior direito
  - Geração via canvas HTML5 (client-side, sem processamento no servidor)
- Exporta como JPG (1080×1080px para Instagram) ou wide (1200×630px para Twitter/LinkedIn)
- Native Share API no mobile (`navigator.share`) → abre diretamente o app de rede social

### Modelo de dados

```python
class FotoVeiculo(db.Model):
    __tablename__ = 'foto_veiculo'
    id = db.Column(db.Integer, primary_key=True)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculo.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)   # salvo em static/uploads/veiculos/<id>/
    legenda = db.Column(db.String(200))
    ordem = db.Column(db.Integer, default=0)               # 0 = capa
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
```

### Armazenamento

```
static/
  uploads/
    veiculos/
      {veiculo_id}/
        foto_001.jpg   ← thumbnail + original
        foto_001_thumb.jpg
```

- Thumbnails: 400×300px (para o grid)
- Original: máximo 1920px no lado maior (para o lightbox e compartilhamento)
- Em produção: mover para S3/Cloudflare R2 e servir via CDN (quando escalar)

### UX no formulário do veículo

```
[ + Adicionar fotos ]
  ↓ (abre file picker ou câmera no mobile)
[ Processando... ]  ← comprime no client antes de enviar
[ Galeria: thumbnail grid com drag-to-reorder ]
[ Foto de capa: primeira da galeria ]
[ Compartilhar ]  → gera card para redes sociais
```

### Compartilhamento — card gerado

```
┌─────────────────────────────────┐
│  [FOTO DO CARRO - destaque]     │
│                            Λ    │
│  Toyota Corolla 2023            │
│  52.430 km · R$ 0,32/km        │
│  Consumo: 14,2 km/L             │
│                    [ΛUTOVIU]    │
└─────────────────────────────────┘
```

---

## 3.7 — Login Social (Google OAuth)

**Objetivo:** Reduzir atrito no cadastro e login — "Entrar com Google" é o padrão esperado em apps modernos, especialmente mobile.

### Fluxo

```
Tela de Login
   ↓
[ Entrar com Google ]  ← botão abaixo do formulário tradicional
   ↓
Pop-up Google OAuth 2.0 (consentimento)
   ↓
Callback /auth/google/callback
   ↓
Se e-mail já existe → faz login (vincula conta Google)
Se e-mail novo     → cria conta no plano free automaticamente
   ↓
Redireciona para /veiculos/
```

### Stack técnica

| Componente | Opção |
|---|---|
| Biblioteca Python | `Authlib` (OAuth 2.0 client) ou `Flask-Dance` |
| Provider | Google Identity (OAuth 2.0 + OpenID Connect) |
| Credenciais | Google Cloud Console → OAuth 2.0 Client ID |
| Dados recebidos | `email`, `name`, `picture` (avatar) |

### Modelo de dados — campo adicional

```python
class Usuario(db.Model):
    # ... campos existentes ...
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    avatar_url = db.Column(db.String(300), nullable=True)  # foto do Google
```

### Endpoint backend

```python
@auth_bp.route('/auth/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    userinfo = oauth.google.userinfo()
    email = userinfo['email']
    user = Usuario.query.filter_by(email=email).first()
    if not user:
        user = Usuario(email=email, nome=userinfo['name'],
                       google_id=userinfo['sub'], avatar_url=userinfo['picture'],
                       plano='free', ativo=True)
        db.session.add(user)
        db.session.commit()
    login_user(user, remember=True)
    return redirect(url_for('veiculo.index'))
```

### UX no login

```
┌──────────────────────────────┐
│  [Λ] AUTOVIU                 │
│                              │
│  E-mail ________________     │
│  Senha  ________________     │
│                              │
│  [ Entrar ]                  │
│                              │
│  ─────────── ou ──────────   │
│                              │
│  [G]  Entrar com Google      │
└──────────────────────────────┘
```

### Segurança

- Validar `state` anti-CSRF no callback (Authlib faz automaticamente)
- HTTPS obrigatório (já configurado em produção via nginx)
- Nunca armazenar tokens do Google — apenas o `google_id` como identificador
- Usuários criados via Google não têm senha hash — bloquear rota `/auth/redefinir-senha` para esses usuários

---

## 3.8 — Login Biométrico / Passkeys (WebAuthn)

**Objetivo:** Usuário mobile pode entrar com digital, Face ID ou padrão de desbloqueio do celular — zero senha. O padrão W3C WebAuthn é suportado nativamente por todos os browsers mobile modernos (Chrome Android, Safari iOS).

### Como funciona

```
1ª vez (registro da biometria):
  Usuário logado → Configurações → "Ativar login com digital"
      ↓
  Browser solicita autenticação biométrica (Face ID / impressão digital)
      ↓
  Dispositivo gera par de chaves (privada fica no TPM/Secure Enclave)
      ↓
  Chave pública + credentialId enviados ao servidor → salvos no banco

Login subsequente:
  Tela de login → "Entrar com digital"
      ↓
  Desafio (challenge) gerado pelo servidor
      ↓
  Browser solicita biometria → dispositivo assina o challenge com chave privada
      ↓
  Servidor verifica assinatura com chave pública armazenada → login concedido
```

### Compatibilidade

| Plataforma | Biometria suportada |
|---|---|
| Android (Chrome 67+) | Impressão digital, Face Unlock, PIN do dispositivo |
| iOS (Safari 14+) | Face ID, Touch ID |
| Desktop (Chrome/Edge) | Windows Hello, Touch ID Mac, chave de segurança USB |

### Stack técnica

| Componente | Opção |
|---|---|
| Backend Python | `py_webauthn` (Duo Security) |
| Frontend JS | `SimpleWebAuthn` (browser) |
| Armazenamento | Tabela `webauthn_credentials` no banco |

### Modelo de dados

```python
class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credential'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    credential_id = db.Column(db.Text, nullable=False, unique=True)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, default=0)
    device_name = db.Column(db.String(100))   # ex: "iPhone de Felipe"
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
```

### Endpoints backend

```python
# Registro
POST /auth/webauthn/register/begin   → gera options de registro
POST /auth/webauthn/register/finish  → verifica + salva credencial

# Login
POST /auth/webauthn/login/begin      → gera challenge
POST /auth/webauthn/login/finish     → verifica assinatura + faz login
```

### UX

```
Tela de Login:
  [ Entrar ]
  [G] Entrar com Google
  [🔑] Entrar com digital / Face ID   ← aparece só se dispositivo tem credencial registrada
                                         (usa localStorage flag para detectar)

Configurações (usuário logado):
  Segurança
  ├── Alterar senha
  ├── Dispositivos biométricos cadastrados
  │     iPhone de Felipe  [Remover]
  │     MacBook Pro       [Remover]
  └── [+ Adicionar este dispositivo]
```

### Segurança

- `challenge` gerado no servidor com `os.urandom(32)`, validade de 60 segundos (salvo em sessão)
- `sign_count` incrementado a cada autenticação — detecta clonagem de credencial
- Remoção de credencial exige confirmação de senha atual
- HTTPS obrigatório (requisito do WebAuthn — sem exceções)

---

## Entrega local consolidada — Fases 1, 2 e 3

**Atualização operacional — Docker local:** após solicitação explícita para documentar e subir localmente, foi construído/iniciado o ambiente local e aplicado Alembic até a004, com backup e auditoria antes/depois. Procedimento completo, persistência, portas e limitações em [DOCKER_LOCAL.md](DOCKER_LOCAL.md). As notas anteriores de migração/diagnóstico “não executados nesta atualização” são registros históricos das respectivas alterações; não indicam o estado desta operação posterior. Nenhuma migração ou implantação de produção foi realizada. O diagnóstico passou a identificar produção pela configuração `ENVIRONMENT`, evitando confundir o `DEBUG` sobrescrito pela CLI Flask com o perfil selecionado.

**Disponibilidade local confirmada:** login e registro retornaram HTTP 200 por acesso direto sem proxy; aplicação disponível em `http://localhost:5012`, MySQL saudável e revisão `a004 (head)`. Backup salvo antes da migração e contagens auditadas preservadas. Isso é evidência de implantação/disponibilidade, não aprovação dos testes funcionais adiados. Índice de documentação consolidado em `README.md`; guia local acrescentado porque o procedimento e seu histórico ainda não estavam documentados.

**Escopo confirmado pelo usuário:** todos os itens das Fases 1, 2 e 3. Fases 4–6 fora desta entrega. **Testes restantes adiados para a etapa final por solicitação do usuário.** Os resultados anteriores não representam aprovação das alterações posteriores.

### Implementações

| Item | Entrega local |
|---|---|
| Fase 1: autenticação | Cadastro e confirmação já implementados; recuperação e redefinição de senha com token de 1 hora e uso único; contas exclusivamente Google não recebem senha local por recuperação |
| Fase 1: sessões | Versão de autenticação no usuário; alteração de senha invalida sessões e cookies de lembrar anteriores. Reautenticação para operações sensíveis |
| Fase 1: isolamento | Corrigidas consultas globais de Uber/custos e falha de autorização nas exclusões/conclusões quando não havia veículo ativo. IDs de outro usuário retornam 404 |
| Fase 1: dados legados | Comando de auditoria somente leitura e migração a003 para vínculos obrigatórios. Registros órfãos interrompem a migração; não são atribuídos automaticamente a outro usuário |
| Fase 2 | Gestão existente preservada, validação centralizada, seleção determinística do veículo, proteção contra cadastros simultâneos acima do limite e preservação de campos após erro |
| Fase 2 — FIPE | Tela `/fipe/` e serviço implementados localmente: veículo ativo ou consulta avulsa, seleção explícita de versão/ano/combustível, fonte, referência e data. Confirmação assinada antes de salvar; atualização do valor estimado opcional. Migração a004 e integração pendentes de validação |
| 3.1 Monetização | Modelo da tabela assinaturas existente, conta do pagador, histórico de faturas, contratação recorrente PIX/boleto/escolha na fatura Asaas, alteração na próxima cobrança, cancelamento e conciliação |
| 3.1 Webhook | Token próprio, eventos idempotentes, consulta autenticada do estado da cobrança antes da liberação; preço conferido, reembolso revoga o benefício. Nenhum cartão passa pelo servidor Flask |
| 3.1 Trial e expiração | Trial Pro de 14 dias iniciado na confirmação ou no cadastro Google; plano base permanece free. Sem cobrança automática no trial. Expiração bloqueia relatórios/CSV/avisos pagos, preservando dados e gestão básica |
| 3.1 Administração | Painel restrito a superadmin, usuários paginados e recebimentos confirmados no mês; comando local de criação de superadmin com senha oculta |
| 3.3 Condutor | CPF validado, datas e categoria de CNH, associação somente aos veículos do usuário; um perfil de condutor por usuário nesta entrega |
| 3.4 Documentos | JPG/PNG/PDF até 10 MB no total; PDF desbloqueado até 4 páginas, validação do conteúdo, consentimento antes de enviar à OpenAI, campos revisáveis e nenhuma gravação do arquivo. Responses API com saída estruturada e store=false |
| 3.5 Alertas | CNH 60/30 dias e vencida, licenciamento/seguro 30 dias, revisão por data/km e lembrete de IPVA em janeiro. Preferência de e-mail explícita; push por dispositivo com VAPID |
| 3.6 Galeria | Até 20 fotos por veículo, JPG/PNG/HEIC, compressão, remoção de EXIF, thumb 400×300, original até 1920px, legenda/capa/ordenação, lightbox com swipe e exportação social quadrada/horizontal |
| 3.7 Google | Authlib/OpenID Connect, validação do ID token/state/nonce, e-mail verificado; tokens do Google não são persistidos. Vínculo de conta local exige sessão local recente na implementação proposta |
| 3.8 Passkeys | Cadastro e login com verificação criptográfica, user verification obrigatório, RP/origem configurados, desafios no banco por 60 segundos e uso único, contador e remoção com senha atual |
| Relatórios | Relatórios por veículo e exportação CSV protegidos por plano e usuário; proteção contra fórmulas em células exportadas |
| Implantação | Volume Docker para fotos, bloqueio de acesso público a static/uploads, .dockerignore excluindo segredos/documentos e inicialização do app sem criar banco ou iniciar scheduler durante Alembic |

### Complemento local — gestão de assinaturas e faturas

Atualização implementada no código em 24/10/2026, sem chamadas reais ao gateway e sem execução de testes.

- A tela **Meu plano** apresenta comparação dos recursos implementados, um único formulário de contratação, período do trial e situação do período pago. Contratações em andamento ou recorrências existentes impedem a oferta de uma segunda contratação pela mesma tela; a verificação de concorrência do serviço continua sendo aplicada no servidor.
- O proprietário pode atualizar sua assinatura e suas faturas por POST com CSRF, autenticação e limite de 5 solicitações por hora. A ação consulta os registros existentes; não cria outra cobrança.
- O serviço de conciliação é compartilhado pela contratação, pela ação do usuário, pela ação administrativa e pelo comando operacional. O histórico é consultado com paginação e recalculado após a leitura completa, evitando cálculo sobre uma página intermediária. Uma resposta inválida ou incompleta exige nova consulta, sem manter uma atualização parcial.
- Contratações com resultado incerto são procuradas pela referência local e pelo pagador conhecido. Quando a consulta individual não encontra uma recorrência removida, a listagem com `includeDeleted` é usada como alternativa, mantendo a conferência de identidade. Resultado ambíguo exige revisão administrativa; não há tentativa automática de criar outra assinatura.
- O serviço diferencia **rejeição explícita** de uma requisição (HTTP 400/401/403/404/422) de **resultado incerto** por falha de comunicação/resposta. Se não houve confirmação de ID remoto e o serviço rejeitou explicitamente a solicitação, o registro local passa a `rejeitado`, permitindo uma nova contratação posterior. Falhas incertas continuam bloqueando uma nova criação até conciliação.
- Situações `suspenso` e `expirado` são distintas de `cancelado`. O acesso já pago continua limitado à data de renovação. Desativar a recorrência não é tratado como quitação de faturas nem como novo pagamento.
- O cancelamento só é concluído localmente após confirmação de remoção pelo Asaas. Faturas locais pendentes ou vencidas passam a canceladas e perdem o link de pagamento; faturas já pagas, histórico e dados do veículo são preservados. A interface explica esses efeitos antes da confirmação. O trial, que não possui recorrência de cobrança, não exibe ação para cancelar uma cobrança inexistente.
- O histórico apresenta situações em português e mantém a consulta a faturas já pagas. Os controles de alteração/cancelamento ficam em seções expansíveis; valores e recursos de Frota permanecem dependentes da decisão comercial pendente.
- O superadmin vê até 20 contratações recentes aguardando acompanhamento e pode conciliar uma delas por POST, com reautenticação e limite de solicitações. O operador não cria cobranças por essa ação. O comando de conciliação registra falhas por referência local e continua nas demais assinaturas, sem imprimir payloads, dados de pagamento ou credenciais.

**Arquivos alterados:** `services/assinatura_service.py` (consulta, conciliação, estados e cancelamento); `blueprints/assinatura/routes.py` (ações autorizadas do proprietário e superadmin, contexto das telas e webhook); `templates/assinatura/planos.html` (comparação, contratação única, gestão e histórico); `templates/assinatura/admin.html` (contratações pendentes). Não foram acrescentadas migrações: as situações continuam usando o campo textual existente.

**Documentos consultados e influência:** `ROADMAP.md`, itens 3.1–3.8, e este roadmap orientam cobrança, histórico e administração; `ARQUITETURA_SAAS.md` orienta isolamento/autenticação/CSRF; `GUIA_UIUX_MOBILE.md`, seções 2 e 7–9, orienta hierarquia das ações e confirmação de cancelamento; `PLANO_MIGRACAO.md` orienta preservação dos dados. A documentação anterior não detalhava como o usuário atualiza faturas nem como contratações incertas são acompanhadas; este complemento registra o fluxo.

**Referências oficiais:** [remoção de assinatura](https://docs.asaas.com/reference/remover-assinatura), [listagem das cobranças de uma assinatura](https://docs.asaas.com/reference/listar-cobrancas-de-uma-assinatura) e [listagem de assinaturas, incluindo removidas](https://docs.asaas.com/reference/listar-assinaturas). O cancelamento deve preservar a distinção do Asaas entre remoção definitiva e suspensão da recorrência.

**Pendências para a etapa final:** validar rejeição explícita versus timeout, isolamento das ações de consulta, referências duplicadas, paginação incompleta, recorrências removidas, atualização de faturas canceladas/pagas, preservação do período pago, conciliação administrativa e interface mobile. Os resultados anteriores de testes não validam este complemento. Configuração Asaas e homologação ainda pendentes; não houve deploy.

### Consulta FIPE — implementação local de 24/10/2026

A tela autenticada `/fipe/` reconhece perguntas sobre “meu carro” e direciona ao veículo ativo. Consultas sobre outro veículo usam busca avulsa, sem cadastro. O nome ajuda a filtrar marca/modelo; versão, ano modelo e combustível exigem seleção explícita. O resultado apresenta valor em reais, identificação completa, código FIPE, mês de referência, fonte e data da consulta. A busca textual é determinística e não utiliza IA para estimar preços.

**Provedor e operação:** integração de leitura no backend com [FipeAPI / Parallelum v2](https://fipe.api.br/docs/comece-aqui), serviço de terceiros, sem apresentá-lo como API oficial da Fundação FIPE. Os [endpoints documentados](https://fipe.api.br/docs/api/fipe) orientam referências, marcas, modelos, anos e cotação. `FIPE_API_TOKEN` é opcional e permanece no servidor; `FIPE_CACHE_SECONDS` tem padrão de 3600 segundos. O cache mantém até 512 respostas por processo, com referência e mês na chave, preservando a data original da consulta. Não é compartilhado entre workers; observar a quota do provedor ao dimensionar a implantação. Somente IDs do catálogo são enviados, sem CNH, CRLV, placa ou dados pessoais. Timeout, indisponibilidade, limite excedido ou resposta inconsistente geram mensagem sem aplicar preço.

**Preservação do cadastro:** salvar a identificação exige POST com CSRF, autorização do proprietário e confirmação da versão. A cotação é assinada, vinculada ao usuário, veículo e identidade atual do cadastro, com validade de 15 minutos. Alterações posteriores de marca/modelo/versão/ano invalidam o vínculo FIPE. Atualizar o valor estimado é uma opção separada, inicialmente desmarcada, disponível somente para referência do mês atual; o valor de compra é preservado. Referências antigas podem ser consultadas e salvas com o mês indicado, sem atualização do valor estimado.

**Arquivos:** `services/fipe_service.py` concentra catálogo, normalização, consulta, validação e cache; `blueprints/fipe/routes.py` controla consulta e confirmação; `templates/fipe/index.html` e `static/js/fipe.js` oferecem seleção progressiva. `models.py` e `migrations/versions/a004_fipe.py` acrescentam oito campos opcionais à tabela existente `veiculo`, sem reinterpretar valores anteriores. `services/veiculo_service.py` invalida o vínculo após mudança de identidade. `app.py`, `_conta_links.html`, telas de veículos, `config.py` e `.env.example` integram acesso e configuração.

**Documentos consultados e influência:** `ROADMAP.md`, item 2.7, define as duas perguntas, desambiguação e confirmação; `ARQUITETURA_SAAS.md` prevê a integração FIPE e isolamento por usuário; este roadmap orienta os padrões existentes; `GUIA_UIUX_MOBILE.md`, seção 7, orienta os formulários; `PLANO_MIGRACAO.md` orienta a evolução incremental com preservação dos dados. A documentação não definia provedor, IDs persistidos nem política de cache: este complemento registra essas decisões e limitações.

**Pendências:** aplicar a004 em homologação após backup; validar contrato real do provedor, quotas, seleção de versões, referência antiga/virada de mês, falhas de rede, limites, cache, isolamento, confirmação expirada/adulterada, mudança de identidade, preservação de valores e interface mobile. Nenhuma consulta real de preço, execução de testes, migração de banco ou implantação foi realizada nesta atualização. Os testes permanecem para a etapa final solicitada pelo usuário.

### Complemento 3.5 — clareza e acompanhamento dos alertas

Implementado localmente em 24/10/2026: a tela informa a quantidade de avisos e apresenta primeiro os urgentes, com prioridade textual acessível. CNH, licenciamento e seguro exibem data e dias restantes, distinguindo vencimento hoje de documento vencido. A agenda informa data prevista, dias de atraso ou restantes, quilometragem prevista e distância restante ou ultrapassada. Não foram alteradas as janelas de disparo documentadas nem acrescentadas regras de calendário oficial ou cálculo tributário.

Os avisos de CNH direcionam ao perfil; os de documentos do veículo direcionam à edição do veículo correspondente. Para manutenção, o acesso leva à lista de veículos para seleção explícita e abertura da agenda existente, sem alterar o veículo ativo por GET. A leitura das manutenções foi agrupada em uma consulta limitada aos IDs dos veículos ativos do proprietário, eliminando uma consulta por veículo.

No processamento push, assinaturas expiradas continuam sendo removidas. Quando todos os destinos retornam 404/410, o registro recebe `sem_destino` e não é contabilizado como enviado. `enviado` indica aceitação por pelo menos um serviço de entrega, sem comprovar leitura pelo usuário. Falhas continuam sem retentativa automática; registros existentes e chaves de deduplicação foram preservados.

**Arquivos alterados e motivos:** `services/alerta_service.py` (detalhes, ordenação, consulta agrupada e estado de envio); `blueprints/alerta/routes.py` (links autorizados conforme origem do aviso); `templates/alertas.html` (quantidade, prioridade e ações). Nenhuma tabela ou migração adicional foi criada.

**Documentação consultada e influência:** `ROADMAP.md` limita o escopo às Fases 1–3; a seção 3.5 deste documento define os gatilhos; `ARQUITETURA_SAAS.md` orienta isolamento por proprietário; `GUIA_UIUX_MOBILE.md` orienta hierarquia de ações e conteúdo acessível; `PLANO_MIGRACAO.md` orienta preservação dos dados. A documentação não detalhava prioridade, destino dos links ou ausência de destinos push; este complemento registra essas definições.

**Validação pendente para a etapa final:** datas em cada janela e no vencimento, agenda por data/km ou ambos, ordenação, estados vazios, links entre veículos do mesmo proprietário, isolamento entre usuários, manutenção concluída, todos os dispositivos expirados e falha parcial de push. Houve somente revisão por leitura; nenhum teste, envio externo, migração ou deploy foi executado.

### Complemento — consistência da agenda e da quilometragem

Implementado localmente em 24/10/2026, sem execução de testes: validação da entrada de manutenção antes de alterar o banco, seguindo os tipos e status oferecidos pelo formulário existente. Datas devem ser válidas; realização futura é recusada, mantendo a data prevista como campo de agendamento. Registro concluído sem data informada assume a data atual, como já ocorria na ação de conclusão. Quilometragens aceitam inteiros entre 0 e 2147483647; não foi criada uma regra de crescimento obrigatório do odômetro.

Custos devem ser finitos, não negativos, com até duas casas decimais e limite de 9999999999,99. Descrição obrigatória até 200 caracteres; observações opcionais até 5000. Não há normalização automática de dados legados nem alterações de schema. A conclusão preserva custo/km anteriores quando omitidos e aceita zero quando informado explicitamente. Repetir a conclusão de um registro já realizado não sobrescreve os dados. Validação ocorre antes de aplicar os campos, com rollback em falhas de persistência; mensagens SQL não são exibidas ao usuário.

**Arquivos:** novo `services/manutencao_service.py` centraliza as regras e reutiliza `campo_data`/`campo_texto` existentes; `blueprints/manutencao/routes.py` aplica validação, autorização existente e tratamento de erros em cadastro, conclusão e exclusão; `blueprints/main/routes.py` reutiliza a validação na atualização rápida de quilometragem. `Docs/FASE3_ROADMAP.md` registra as regras. Os registros persistidos são preservados em erros; a restauração dos campos no envio por JavaScript e no POST tradicional está descrita nos complementos posteriores.

**Documentos consultados e influência:** `ROADMAP.md` (Fases 1–3 e manutenção básica), seção 3.5 deste documento (agenda alimenta os alertas), `ARQUITETURA_SAAS.md` (Flask, SQLAlchemy e autorização), `GUIA_UIUX_MOBILE.md`, seção 7 (validação e feedback), e `PLANO_MIGRACAO.md` (preservação dos dados). A documentação não detalhava limites e tratamento de entradas inválidas da manutenção; as regras acima completam essa lacuna sem acrescentar um módulo paralelo.

**Etapa final:** validar entradas vazias, zero, negativos, frações, NaN/infinito, limites numéricos, datas inválidas/futuras, status/tipo adulterados, conclusão repetida, rollback e isolamento entre proprietários. Nenhum teste, migração, envio externo ou deploy foi executado nesta atualização.

### Complemento — preservação dos campos de manutenção

O formulário de cadastro e os modais de conclusão agora enviam os dados por `fetch`, mantendo os campos no DOM em caso de erro. Validações são mostradas no próprio formulário, com região de status acessível. Durante o envio, o botão fica bloqueado. Não há armazenamento de descrição/observações no localStorage, sessionStorage ou cookie. O retorno do POST tradicional para erros de validação foi complementado pela renderização descrita a seguir.

As rotas negociam JSON apenas quando solicitado por `Accept: application/json`, preservando CSRF e autorização. O veículo exibido é enviado como campo oculto e conferido com o veículo ativo; uma troca em outra aba resulta em conflito, sem gravar no veículo errado. A conclusão usa bloqueio da linha para serializar duas conclusões simultâneas no MySQL, sem acrescentar migração.

Timeout de 25 segundos, resposta inesperada ou erro de servidor são resultados incertos: não há reenvio automático, os campos permanecem e um novo envio fica bloqueado até o usuário conferir a agenda e recarregar a página. Isso reduz duplicações na interface, mas não substitui uma chave de idempotência de cadastro no servidor. Sessão expirada e erros conhecidos de validação/CSRF permitem correção sem apagar os campos. Nenhum texto retornado pelo servidor é inserido como HTML.

**Arquivos e referências:** `blueprints/manutencao/routes.py` (respostas JSON e conferência do veículo), `templates/index.html` (marcação dos dois formulários), novo `static/js/manutencao.js` (envio e estados); `GUIA_UIUX_MOBILE.md`, seção 7, exige preservação e feedback; `ARQUITETURA_SAAS.md` orienta autenticação/isolamento; `ROADMAP.md`, este roadmap e `PLANO_MIGRACAO.md` mantêm escopo e preservação. Este complemento supre a lacuna de comportamento após falha registrada acima.

**Etapa final:** validar erro de campo, falha de rede antes/depois da gravação, expiração de sessão/CSRF, troca de veículo em outra aba, duas conclusões concorrentes, envio sem JavaScript, teclado/foco e mobile. Somente revisão por leitura nesta atualização; testes, envios e implantação não executados.

### Complemento — diagnóstico local de configuração

Novo comando `configuracao-diagnosticar`, registrado em `app.py`, com lógica em `services/configuracao_service.py`. A saída informa nomes dos serviços, estado de presença, pendências e limites da inspeção. `--json` oferece o mesmo conteúdo para leitura estruturada. Nenhum valor de variável, chave, token, destinatário ou conexão do banco é exibido. O comando não realiza consultas de banco, autenticação com provedores, envios, migrações ou alterações de configuração.

Grupos inspecionados: sessão/cookies, origem pública, SMTP, OCR, Google, passkeys, VAPID, Asaas, armazenamento do limite de requisições, FIPE e decisão comercial Frota. Presença não comprova credenciais válidas, assinatura criptográfica, entrega ou cobrança. Os formatos verificados incluem origem HTTPS, correspondência de domínio das passkeys, ambiente Asaas e comprimento mínimo de segredo/webhook. Frota e vínculo Google continuam sujeitos às decisões documentadas; o comando não aprova essas decisões. Em caso de parâmetros numéricos inválidos que impeçam carregar `config.py`, o operador precisa corrigi-los antes de executar o comando.

No PowerShell, na raiz do projeto, com o ambiente configurado:

```powershell
# Apenas presença/formato; os dois argumentos False evitam criação de tabelas e scheduler
.\.venv\Scripts\python.exe -m flask --app "app:create_app('production', initialize_database=False, start_scheduler=False)" configuracao-diagnosticar
# Alternativa estruturada, também sem valores de configuração
.\.venv\Scripts\python.exe -m flask --app "app:create_app('production', initialize_database=False, start_scheduler=False)" configuracao-diagnosticar --json
```

Os comandos foram preparados e **não foram executados** nesta atualização, respeitando o adiamento das verificações. O diagnóstico não substitui a auditoria de dados, backup, aplicação das migrações ou testes finais.

`services/public_url.py` agora expõe a validação de origem reutilizada pelo diagnóstico e pelos links transacionais. `services/email_service.py` passou a utilizar `public_base_url()` também na confirmação, como recuperação e Google já faziam. Isso elimina a validação duplicada mais permissiva, recusando origem com credenciais, caminho, consulta, fragmento ou porta inválida antes de montar o link. Nenhuma mensagem foi enviada.

**Documentos consultados e influência:** `ROADMAP.md` (pendências das Fases 1–3), este roadmap (credenciais, decisões e homologação), `ARQUITETURA_SAAS.md` (serviços e operação), `PLANO_MIGRACAO.md` (não modificar banco sem preparação) e `GUIA_UIUX_MOBILE.md` (preservação dos formulários no complemento anterior). Faltava um inventário operacional reproduzível sem expor segredos; este comando registra o procedimento e sua limitação. Validar a saída para configuração ausente/parcial, origens inválidas, domínio incompatível, cookies, armazenamento local e ausência de segredos na etapa final.

### Complemento — configuração comercial inválida

`services/assinatura_service.py` passa a omitir Frota do catálogo quando a configuração contiver preço não finito, zero, negativo, acima de 9999999999,99 ou com fração de centavo, ou limite que não seja inteiro não negativo. O erro é registrado sem imprimir o valor configurado. Gratuito e Pro permanecem disponíveis; nenhum preço alternativo é inventado. Em `models.py`, limites Frota inválidos não substituem os limites legados. O valor zero continua significando ilimitado somente para o limite de veículos, não para o preço.

Este ajuste trata configuração inválida, sem resolver a divergência comercial entre `ROADMAP.md` e este documento. `FROTA_PRECO` e `FROTA_LIMITE` permanecem sem alteração nesta execução. Não houve cobrança, migração ou alteração de assinaturas existentes. Tipos numéricos inválidos que impeçam a inicialização de `config.py` continuam exigindo correção pelo operador.

**Referências:** os dois roadmaps definem a pendência comercial; `ARQUITETURA_SAAS.md` orienta preservação dos planos e `PLANO_MIGRACAO.md` orienta não reinterpretar dados existentes. Faltava documentar o comportamento para configuração comercial malformada. Validar esses limites, Frota desabilitada e preservação de usuários legados na etapa final; nenhum teste foi executado nesta atualização.

### Complemento — retorno do POST tradicional de manutenção

Fechada a pendência de restauração após erros de validação do POST tradicional. A rota devolve HTTP 422 com o dashboard renderizado, modal correspondente aberto, mensagem acessível e campos reapresentados. Cadastro e conclusão usam a mesma renderização de dashboard existente, extraída para `renderizar_dashboard()` em `blueprints/main/routes.py`; não foi criada outra página nem duplicada a consulta do dashboard. O helper não é uma rota pública e seus chamadores continuam autenticados.

`blueprints/manutencao/routes.py` fornece o contexto de recuperação somente para erros de validação conhecidos, após rollback. Respostas JSON continuam preservando o DOM; respostas de sucesso continuam redirecionando. Falha de banco ou resultado incerto não provoca renderização adicional que dependa do banco. Conflitos de veículo também não reutilizam os dados antigos em um novo veículo ativo. Não há persistência dos valores submetidos em cookie, sessão ou armazenamento local.

`templates/index.html` restaura campos exclusivamente no formulário que falhou, preserva custo zero, utiliza escape automático do Jinja e acrescenta limites nativos coerentes com o servidor. Valores adulterados incompatíveis com `input type=date/number` podem ser sanitizados pelo navegador; a mensagem de validação continua disponível. Os dois formulários possuem CSRF no HTML e o script geral evita campos duplicados. Um link permite sair do modal de erro sem depender de JavaScript. Isso cobre o retorno do envio tradicional; não representa uma adaptação completa do dashboard para navegação sem JavaScript.

**Documentos consultados e influência:** `GUIA_UIUX_MOBILE.md`, seção 7, exige preservar dados e mostrar feedback; `ROADMAP.md` e este documento delimitam a entrega; `ARQUITETURA_SAAS.md` orienta reutilização do Flask/Jinja e isolamento; `PLANO_MIGRACAO.md` orienta preservar os registros existentes. Esta seção atualiza a lacuna do POST tradicional indicada nos complementos anteriores.

**Validação final pendente:** POST HTML e JSON, restauração de cada campo, custo zero, erro de nova manutenção versus conclusão, caracteres especiais, limites nativos, token CSRF no HTML, retorno após troca de veículo e navegação de saída do modal. Somente revisão por leitura; não foram executados testes, migrações, envios ou deploy.

### Decisões ainda pendentes

1. **Frota:** este documento define R$ 39,90/ilimitado; ROADMAP.md define R$ 49,90/15. Pergunta enviada ao usuário e ainda sem definição. A venda de Frota permanece desabilitada por padrão; os limites legados não foram alterados silenciosamente. Depois da escolha, alinhar ambos os documentos e configurar FROTA_PRECO/FROTA_LIMITE (0 = ilimitado).
2. **Vínculo Google:** o exemplo original vincula contas automaticamente por e-mail. A proposta exige autenticação local prévia e recente para conectar uma conta existente. Direcionamento solicitado ao usuário; Google continua sem credenciais configuradas neste ambiente. Não habilitar a integração antes de resolver essa diferença e homologar o fluxo.
3. **Provedores:** não foram encontradas variáveis das novas integrações nos arquivos .env e .env.local. Definir SMTP, Asaas, Google OAuth, OpenAI/modelo de visão, RP/origem HTTPS e chaves VAPID. Nunca fornecer chaves em documentação ou commits.
4. **IPVA:** sem UF e alíquota documentadas não se calcula imposto; é mostrado um lembrete e o valor estimado do veículo, sem inventar uma estimativa tributária.
5. **Aceite de produção:** pagamento recorrente real, entrega de e-mails, biometria em dispositivos reais e preservação dos dados reais ainda exigem homologação. Não houve deploy nem migração do banco de produção.

### Arquivos afetados e finalidade

- `models.py`, `migrations/versions/a002_fase3.py`, `migrations/versions/a003_isolamento_obrigatorio.py`, `migrations/env.py`: novos dados e migrações incrementais; sem reescrever a001 já existente.
- `app.py`, `config.py`, `extensions.py` existente e `.env.example`: registro de blueprints, autenticação, limites, flags e comandos operacionais (extensions.py foi consultado e reutilizado).
- `blueprints/auth/`, `services/email_service.py`, `services/public_url.py`, `templates/auth/`: confirmação, recuperação, alteração de senha, OAuth e passkeys.
- `blueprints/condutor/`, `blueprints/documento/`, `services/condutor_service.py`, `services/documento_service.py`: perfil e leitura de documentos.
- `blueprints/galeria/`, `services/foto_service.py`, `templates/veiculos/galeria.html`: fotos privadas e compartilhamento voluntário.
- `blueprints/alerta/`, `services/alerta_service.py`, `templates/alertas.html`: preferências e processamento de notificações.
- `blueprints/assinatura/`, `services/assinatura_service.py`, `services/plano_service.py`, `templates/assinatura/`: cobrança, planos e autorização de recursos pagos.
- `blueprints/relatorio/`, `templates/relatorios.html`: relatórios e CSV.
- `blueprints/main/routes.py`, `blueprints/veiculo/routes.py`, `blueprints/uber/routes.py`, `blueprints/abastecimento/routes.py`, `blueprints/despesa/routes.py`, `blueprints/manutencao/routes.py` e serviços existentes: correções de isolamento e validação.
- `templates/conta_base.html`, `templates/_conta_links.html`, `templates/condutor/`, `templates/_importar_cnh.html`, `static/css/conta.css`, novos scripts em `static/js/`, `static/sw.js` e menus existentes: interface consistente e integração ao PWA já existente.
- `Dockerfile`, `docker-compose.prod.yml`, `.dockerignore`, `.gitignore`, `requirements.txt`, `create_user.py`: dependências, persistência, exclusão de segredos do build e administração.
- `tests/` e `cypress/e2e/fase3/`: cenários preparados para a etapa final. Nenhuma execução adicional após a orientação de adiar testes.

### Migração e operação

Antes de alterar qualquer banco real, executar o backup descrito em PLANO_MIGRACAO.md e auditar os vínculos. A migração a003 recusa registros sem proprietário válido. A correção desses registros exige identificar o proprietário real; nunca escolher o primeiro usuário indiscriminadamente.

No PowerShell, na raiz do projeto, com variáveis de ambiente apropriadas:

```powershell
# Instalar as dependências no ambiente virtual do projeto
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Somente leitura: conferir contagens e vínculos no banco configurado
.\.venv\Scripts\python.exe -m flask --app "app:create_app('production', initialize_database=False, start_scheduler=False)" dados-auditar
# Aplicar somente após backup e homologação; não foi executado em produção
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Os comandos `flask ... assinaturas-reconciliar` e `flask ... alertas-enviar` fazem chamadas externas/envios: não foram executados nesta entrega. A conciliação não repete automaticamente uma criação de cobrança com resultado incerto. Configurar o webhook Asaas em /webhooks/asaas, com authToken independente de pelo menos 32 caracteres e eventos PAYMENT_* e de exclusão/inativação de assinatura. Usar sandbox antes de produção.

ALERTAS_AUTOMATICOS é false por padrão. Um único scheduler/worker deve ser responsável pelo agendamento. Envios são registrados por usuário/alerta/canal para evitar duplicações; falhas ficam registradas para revisão, sem retentativa cega que possa duplicar mensagens. Configurar armazenamento compartilhado no Flask-Limiter quando houver múltiplos processos. Incluir o volume vehicle_photos na rotina de backup; não servir static/uploads diretamente por Nginx/CDN.

### Validação final e referências

Os 39 testes aprovados anteriormente precedem as últimas alterações de recuperação, isolamento, relatórios e migração a003. A auditoria Cypress mais recente, iniciada antes do adiamento, terminou com 5 cenários aprovados e 1 falha de largura no plano em 360px. O CSS foi ajustado depois; revalidação adiada. Docker não estava disponível localmente: build e MySQL ainda precisam de validação. Não declarar o conjunto atual validado com base nos resultados anteriores.

Na etapa final, executar novamente os testes de cadastro, recuperação de senha/revogação de sessão, isolamento (incluindo usuário sem veículo), planos expirados, cobranças idempotentes/reembolsos, uploads, OAuth, passkeys, migrações MySQL/rollback e telas mobile. Incluir preservação dos dados reais e os fluxos com os provedores em homologação. Alterações locais anteriores de PWA, placas e interface foram preservadas.

Documentos consultados: ROADMAP.md (tarefas 1–3), FASE3_ROADMAP.md (prioridade e recursos), ARQUITETURA_SAAS.md (Flask, MySQL e isolamento), PLANO_MIGRACAO.md (backup e preservação), GUIA_UIUX_MOBILE.md (layout/controles). MODULO_TELEMETRIA_OBD.md, MODULO_GPS_RASTREAMENTO.md e CLAUDE_Cronos_Auto_Connect.md foram consultados para delimitar o escopo futuro; nenhuma implementação das Fases 4–6 foi iniciada.

Referências oficiais usadas na implementação:
- [Asaas: assinaturas](https://docs.asaas.com/reference/criar-nova-assinatura), [alteração de assinatura](https://docs.asaas.com/reference/atualizar-assinatura-existente) e [consulta de cobrança](https://docs.asaas.com/reference/recuperar-uma-unica-cobranca).
- [Authlib para Flask](https://docs.authlib.org/en/latest/oauth2/client/web/flask.html) e [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect).
- [WebAuthn: registro](https://duo-labs.github.io/py_webauthn/registration.html) e [autenticação](https://duo-labs.github.io/py_webauthn/authentication.html).
- [OpenAI: visão](https://developers.openai.com/api/docs/guides/images-vision), [saídas estruturadas](https://developers.openai.com/api/docs/guides/structured-outputs) e [arquivos](https://developers.openai.com/api/docs/guides/file-inputs).
- [pywebpush](https://github.com/web-push-libs/pywebpush).

---

## Prioridade de Implementação

```
[QW] PWA (manifest.json + SW)   ← 1 dia — app instalável no celular, alto impacto UX
[QW] Máscara de placa (JS)      ← meio dia — AAA-0000 e Mercosul AAA0A00

3.2  Registro público    ← BLOQUEADOR: sem isso não há novos usuários
3.1  Monetização         ← junto com 3.2 (Asaas, planos, webhook)
3.7  Login Google        ← após 3.2 — reduz atrito no cadastro
3.6  Galeria de fotos    ← engajamento e viralização (fácil, alto impacto)
3.3  Perfil do condutor  ← base para 3.4 e 3.5
3.4  Upload CNH/CRLV     ← diferencial competitivo
3.5  Alertas inteligentes ← retenção de usuários
3.8  Login biométrico    ← após 3.7 (WebAuthn/Passkeys)
```

### Estimativas

| Item | Esforço | Impacto |
|---|---|---|
| PWA | 1 dia | App instalável, offline parcial |
| Máscara placa | ½ dia | Qualidade de dados |
| 3.2 Registro público | 3–5 dias | Crítico — crescimento |
| 3.1 Monetização | 4–6 dias | Receita |
| 3.7 Google OAuth | 2 dias | Reduz churn no cadastro |
| 3.6 Galeria de fotos | 4–6 dias | Engajamento + viral |
| 3.3 Perfil condutor | 2–3 dias | Base para 3.4/3.5 |
| 3.4 Upload CNH/CRLV | 3–4 dias | Diferencial |
| 3.5 Alertas | 3–4 dias | Retenção |
| 3.8 WebAuthn | 3–4 dias | UX premium |

---

## Dependências Externas

| Serviço | Uso | Custo estimado |
|---|---|---|
| OpenAI API (GPT-4 Vision) | OCR de documentos CNH/CRLV | ~R$ 0,50 por upload |
| Asaas | Cobranças e assinaturas | 2,49% por transação |
| SendGrid ou Resend | E-mails transacionais | Free tier até 100/dia |
| Redis (opcional) | Rate limiting, sessões | R$ 50/mês no servidor |
| Cloudflare R2 (futuro) | Armazenamento de fotos (escala) | ~R$ 0,015/GB/mês |
| Google Cloud Console | OAuth 2.0 credentials (Client ID + Secret) | Gratuito |
| `Authlib` ou `Flask-Dance` | Google OAuth no Flask | Open source |
| `py_webauthn` + `SimpleWebAuthn` | WebAuthn/Passkeys | Open source |
