# ΛUTOVIU — Pendências que dependem do usuário

## 🔴 Bloqueantes (impedem funcionalidade completa)

### 1. SMTP — E-mails transacionais
**O que preciso:** host, porta, user e senha de um servidor SMTP
**Impacto:** confirmação de cadastro, recuperação de senha e alertas por e-mail não funcionam
**Sugestão:** Brevo (ex-Sendinblue) tem tier gratuito de 300 e-mails/dia
**Config esperada em:** variáveis de ambiente `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`

### 2. Google OAuth — Login Social
**O que preciso:** `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`
**Como obter:** console.cloud.google.com → Credenciais → OAuth 2.0
**Impacto:** botão "Entrar com Google" na tela de login não funciona

### 3. Asaas — Pagamentos/Assinaturas
**O que preciso:** API Key do Asaas (produção)
**Impacto:** planos pagos (Pro, Frota) não processam pagamento real
**Nota:** ambiente sandbox já funciona para testes

## 🟡 Decisões de negócio

### 4. Precificação dos planos
- Free: 1 veículo — ok?
- Pro: 3 veículos — R$ ??? /mês
- Frota: ilimitado — R$ ??? /mês

### 5. API de imagem automática do carro
- **Imagin Studio** — melhor qualidade, mas ~$50/mês (pago)
- **Car Imagery API** — alternativa mais barata
- **Sem API** — usuário faz upload da própria foto (grátis, já implementado)
- Qual prefere?

## 🟢 Em desenvolvimento (não bloqueado)

- Animação de garagem (em andamento)
- Mapa de abastecimentos
- Alertas/lembretes de manutenção
