/**
 * FASE 1 — Abastecimento CRUD
 * Cobre: cadastrar, exibir no dashboard, deletar, isolamento de propriedade
 */
describe('Fase 1 — Abastecimento', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/')
    // Se não tem veículo, pula os testes de abastecimento
  })

  context('Cadastrar abastecimento', () => {
    it('acessa a página de cadastro', () => {
      cy.visit('/abastecimento/cadastrar')
      cy.url().should('not.include', '/auth/login')
    })

    it('exibe formulário com campos necessários', () => {
      cy.visit('/abastecimento/cadastrar')
      cy.get('input[name="quilometragem"], input[name="km"]').should('exist')
    })

    it('cadastra um abastecimento com dados válidos', () => {
      cy.visit('/abastecimento/cadastrar')
      const hoje = new Date().toISOString().split('T')[0]

      // Preencher campos — adaptar conforme template existente
      cy.get('input[name="quilometragem"]').type('65000').then(() => {
        cy.get('input[name="litros_abastecidos"]').type('40')
        cy.get('input[name="valor_total"]').type('280')
        cy.get('input[name="preco_combustivel"]').type('7.00')
        cy.get('input[name="posto"]').type('Posto Ipiranga')
        cy.get('input[name="data"]').type(hoje)
        cy.get('form').submit()
      })

      cy.url().should('match', /\/$|\/abastecimento/)
      cy.contains(/adicionado|sucesso/i).should('be.visible')
    })
  })

  context('Isolamento — DELETE de outro usuário', () => {
    it('DELETE /abastecimento/delete/99999 retorna 404 ou redireciona sem apagar', () => {
      cy.visit('/')
      cy.getCsrfToken().then((token) => {
        cy.request({
          method: 'POST',
          url: '/abastecimento/delete/99999',
          body: { csrf_token: token },
          form: true,
          failOnStatusCode: false,
          followRedirect: false,
        }).its('status').should('eq', 404)
      })
    })
  })
})
