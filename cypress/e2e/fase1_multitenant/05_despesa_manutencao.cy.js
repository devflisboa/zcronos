/**
 * FASE 1 — Despesas e Manutenção CRUD
 * Cobre: cadastrar despesa, manutenção, isolamento de propriedade
 */
describe('Fase 1 — Despesa e Manutenção', () => {
  beforeEach(() => {
    cy.login()
  })

  // ── Despesas ──────────────────────────────────────────────────────────────
  context('Despesas', () => {
    it('acessa a página de cadastro de despesa', () => {
      cy.visit('/despesa/cadastrar')
      cy.url().should('not.include', '/auth/login')
    })

    it('exibe formulário com campo de categoria', () => {
      cy.visit('/despesa/cadastrar')
      cy.get('select[name="categoria_id"]').should('exist')
      cy.get('select[name="categoria_id"] option').should('have.length.at.least', 2)
    })

    it('cadastra despesa com dados válidos', () => {
      cy.visit('/despesa/cadastrar')
      const hoje = new Date().toISOString().split('T')[0]
      cy.get('input[name="descricao"]').type('IPVA 2026')
      cy.get('input[name="valor"]').type('1500')
      cy.get('input[name="data"]').type(hoje)
      cy.get('select[name="categoria_id"]').select(1) // primeira categoria
      cy.get('form').submit()
      cy.url().should('match', /\/$|\/despesa/)
      cy.contains(/adicionada|sucesso/i).should('be.visible')
    })

    it('DELETE /despesa/delete/99999 retorna 404', () => {
      cy.visit('/')
      cy.getCsrfToken().then((token) => {
        cy.request({
          method: 'POST',
          url: '/despesa/delete/99999',
          body: { csrf_token: token },
          form: true,
          failOnStatusCode: false,
          followRedirect: false,
        }).its('status').should('eq', 404)
      })
    })

    it('GET /despesa/editar/99999 retorna 404', () => {
      cy.request({ url: '/despesa/editar/99999', failOnStatusCode: false })
        .its('status').should('eq', 404)
    })

    it('POST /despesa/editar/99999 retorna 404', () => {
      cy.visit('/')
      cy.getCsrfToken().then((token) => {
        cy.request({
          method: 'POST',
          url: '/despesa/editar/99999',
          body: { csrf_token: token, descricao: 'Teste', valor: '100', data: '2024-01-01', categoria_id: '1' },
          form: true,
          failOnStatusCode: false,
          followRedirect: false,
        }).its('status').should('eq', 404)
      })
    })
  })

  // ── Manutenção ────────────────────────────────────────────────────────────
  context('Manutenção', () => {
    it('cadastra manutenção via POST /manutencao/add', () => {
      cy.visit('/')
      cy.getCsrfToken().then((token) => {
        const amanha = new Date(Date.now() + 86400000).toISOString().split('T')[0]
        cy.request({
          method: 'POST',
          url: '/manutencao/add',
          body: {
            csrf_token: token,
            tipo: 'oleo',
            descricao: 'Troca de óleo Cypress Test',
            data_prevista: amanha,
            km_previsto: '70000',
            custo: '0',
            status: 'pendente',
          },
          form: true,
          followRedirect: false,
        }).its('status').should('eq', 302)
      })
    })

    it('DELETE /manutencao/delete/99999 retorna 404 ou redirect', () => {
      cy.visit('/')
      cy.getCsrfToken().then((token) => {
        cy.request({
          method: 'POST',
          url: '/manutencao/delete/99999',
          body: { csrf_token: token },
          form: true,
          failOnStatusCode: false,
          followRedirect: false,
        }).its('status').should('eq', 404)
      })
    })
  })
})
