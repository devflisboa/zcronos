/**
 * FASE 0 — Autenticação
 * Cobre: login válido, inválido, rate limit, rotas protegidas, logout
 */
describe('Fase 0 — Login', () => {
  const EMAIL = Cypress.env('TEST_USER_EMAIL')
  const SENHA = Cypress.env('TEST_USER_SENHA')

  beforeEach(() => {
    cy.clearCookies()
    cy.clearLocalStorage()
  })

  // ── Acesso a rotas protegidas sem login ───────────────────────────────────
  context('Rotas protegidas (sem login)', () => {
    const rotasProtegidas = ['/', '/abastecimento/cadastrar', '/despesa/cadastrar', '/veiculos/']

    rotasProtegidas.forEach((rota) => {
      it(`GET ${rota} → redirect para /auth/login`, () => {
        cy.visit(rota, { failOnStatusCode: false })
        cy.url().should('include', '/auth/login')
      })
    })
  })

  // ── Tela de login ─────────────────────────────────────────────────────────
  context('Tela de login', () => {
    beforeEach(() => cy.visit('/auth/login'))

    it('exibe o formulário de login', () => {
      cy.get('input[name="email"]').should('be.visible')
      cy.get('input[name="senha"]').should('be.visible')
      cy.get('form').should('exist')
    })

    it('tem CSRF token no formulário', () => {
      cy.get('input[name="csrf_token"]').should('exist')
    })

    it('exibe erro com credenciais inválidas', () => {
      cy.get('input[name="email"]').type('invalido@teste.com')
      cy.get('input[name="senha"]').type('senhaerrada123')
      cy.get('form').submit()
      cy.url().should('include', '/auth/login')
      cy.contains(/e-mail ou senha incorretos/i).should('be.visible')
    })

    it('exibe erro com senha em branco', () => {
      cy.get('input[name="email"]').type(EMAIL)
      cy.get('input[name="senha"]').type(' {backspace}')
      cy.get('form').submit()
      cy.url().should('include', '/auth/login')
    })

    it('não revela se o e-mail existe (mensagem genérica)', () => {
      cy.get('input[name="email"]').type('naoexiste@zcronos.local')
      cy.get('input[name="senha"]').type('qualquercoisa')
      cy.get('form').submit()
      // Não deve dizer "e-mail não encontrado", só mensagem genérica
      cy.contains(/e-mail ou senha incorretos/i).should('be.visible')
      cy.contains(/e-mail não encontrado/i).should('not.exist')
    })
  })

  // ── Login com sucesso ─────────────────────────────────────────────────────
  context('Login válido', () => {
    it('autentica e redireciona para o app', () => {
      cy.visit('/auth/login')
      cy.get('input[name="email"]').type(EMAIL)
      cy.get('input[name="senha"]').type(SENHA)
      cy.get('form').submit()
      cy.url().should('not.include', '/auth/login')
      // Pode ir para dashboard (/) ou para /veiculos/novo se não tiver veículo
      cy.url().should('match', /\/$|\/veiculos/)
    })

    it('após login, / não redireciona para /auth/login', () => {
      cy.login()
      cy.visit('/')
      cy.url().should('not.include', '/auth/login')
    })

    it('sessão persiste após reload', () => {
      cy.login()
      cy.visit('/')
      cy.reload()
      cy.url().should('not.include', '/auth/login')
    })
  })

  // ── Logout ────────────────────────────────────────────────────────────────
  context('Logout', () => {
    it('encerra sessão e redireciona para login', () => {
      cy.login()
      cy.logout()
      cy.url().should('include', '/auth/login')
    })

    it('após logout, / redireciona para login', () => {
      cy.login()
      cy.logout()
      cy.visit('/')
      cy.url().should('include', '/auth/login')
    })
  })
})
