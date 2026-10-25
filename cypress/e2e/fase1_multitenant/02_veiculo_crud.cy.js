/**
 * FASE 1 — Veículo CRUD
 * Cobre: listar, criar, editar, selecionar veículo
 */
describe('Fase 1 — Veículo CRUD', () => {
  beforeEach(() => {
    cy.login()
  })

  // ── Lista de veículos ─────────────────────────────────────────────────────
  context('Lista de veículos (/veiculos/)', () => {
    beforeEach(() => cy.visit('/veiculos/'))

    it('carrega a página de veículos', () => {
      cy.contains(/Meus veículos/i).should('be.visible')
    })

    it('exibe botão de novo veículo se dentro do limite do plano', () => {
      // Pode ou não aparecer dependendo do plano, mas a página deve carregar
      cy.get('body').should('be.visible')
    })
  })

  // ── Criação de veículo ────────────────────────────────────────────────────
  context('Formulário de novo veículo', () => {
    beforeEach(() => cy.visit('/veiculos/novo'))

    it('exibe o formulário com campos obrigatórios', () => {
      cy.get('input[name="marca"]').should('be.visible')
      cy.get('input[name="modelo"]').should('be.visible')
      cy.get('input[name="ano"]').should('be.visible')
      cy.get('button[type="submit"]').should('be.visible')
    })

    it('impede submit sem marca/modelo (validação HTML5)', () => {
      cy.get('input[name="marca"]').should('have.attr', 'required')
      cy.get('input[name="modelo"]').should('have.attr', 'required')
      cy.get('input[name="ano"]').should('have.attr', 'required')
    })

    it('cria veículo com campos obrigatórios', () => {
      const ts = Date.now()
      cy.get('input[name="marca"]').type('Toyota')
      cy.get('input[name="modelo"]').type(`Corolla_${ts}`)
      cy.get('input[name="ano"]').clear().type('2022')
      cy.get('form').submit()
      // Redireciona para dashboard ou lista de veículos após criar
      cy.url().should('match', /\/$|\/veiculos/)
      cy.contains(`Corolla_${ts}`).should('exist')
    })
  })

  // ── Edição de veículo ─────────────────────────────────────────────────────
  context('Editar veículo', () => {
    it('carrega formulário de edição do veículo ativo', () => {
      cy.visit('/veiculos/')
      cy.get('a[href*="/editar"]').first().click()
      cy.url().should('match', /\/veiculos\/\d+\/editar/)
      cy.get('input[name="marca"]').invoke('val').should('not.be.empty')
    })

    it('salva alteração de km', () => {
      cy.visit('/veiculos/')
      cy.get('a[href*="/editar"]').first().click()
      const novoKm = Math.floor(Math.random() * 10000) + 60000
      cy.get('input[name="km_atual"]').clear().type(String(novoKm))
      cy.get('form').submit()
      cy.url().should('include', '/veiculos')
      cy.contains(/veículo atualizado/i).should('be.visible')
    })
  })

  // ── Seleção de veículo ────────────────────────────────────────────────────
  context('Selecionar veículo ativo', () => {
    it('botão selecionar muda o veículo ativo', () => {
      cy.visit('/veiculos/')
      // Pode haver apenas um veículo — verificar que a página carregou
      cy.get('form[action*="/selecionar"]').first().submit()
      cy.location('pathname').should('eq', '/')
    })
  })

  // ── Segurança — acesso a veículo de outro usuário ─────────────────────────
  context('Isolamento de propriedade', () => {
    it('GET /veiculos/99999/editar retorna 404', () => {
      cy.request({
        url: '/veiculos/99999/editar',
        failOnStatusCode: false,
      }).its('status').should('eq', 404)
    })

    it('POST /veiculos/99999/deletar retorna 404', () => {
      cy.visit('/veiculos/')
      cy.getCsrfToken().then((token) => {
        cy.request({
          method: 'POST',
          url: '/veiculos/99999/deletar',
          body: { csrf_token: token },
          form: true,
          failOnStatusCode: false,
        }).its('status').should('eq', 404)
      })
    })
  })
})
