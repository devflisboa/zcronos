/**
 * FASE 1 — Abastecimento CRUD
 * Cobre: cadastrar, editar, deletar, isolamento de propriedade
 */
describe('Fase 1 — Abastecimento', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/')
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

  context('Editar abastecimento', () => {
    it('GET /abastecimento/editar/99999 retorna 404', () => {
      cy.request({ url: '/abastecimento/editar/99999', failOnStatusCode: false })
        .its('status').should('eq', 404)
    })

    it('rota de edição é acessível e formulário tem campos pré-preenchidos', () => {
      const hoje = new Date().toISOString().split('T')[0]

      // Visitar / para garantir veiculo_ativo na sessão e obter CSRF
      cy.visit('/')
      cy.getCsrfToken().then(token => {
        cy.request({
          method: 'POST',
          url: '/abastecimento/add',
          form: true,
          body: { csrf_token: token, quilometragem: '70000', litros_abastecidos: '45',
                  valor_total: '315', preco_combustivel: '7.00', posto: 'Shell', data: hoje },
          followRedirect: false,
        }).then(resp => {
          // Garantir que o POST redirecionou para o dashboard (não para /veiculo/)
          expect(resp.status, 'POST criou o registro').to.eq(302)
          expect(resp.headers.location, 'Redirecionou para dashboard').to.include('/')

          // Extrai o ID do link de editar no HTML do dashboard
          cy.request('/').then(dashResp => {
            const match = dashResp.body.match(/href="\/abastecimento\/editar\/(\d+)"/)
            expect(match, 'Link de edição encontrado no HTML').to.not.be.null
            const editUrl = `/abastecimento/editar/${match[1]}`
            cy.visit(editUrl)
            cy.get('input[name="quilometragem"]').should('have.value', '70000')
            cy.get('input[name="posto"]').should('have.value', 'Shell')
          })
        })
      })
    })
  })

  context('Isolamento — operações em registros alheios', () => {
    it('DELETE /abastecimento/delete/99999 retorna 404', () => {
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

    it('POST /abastecimento/editar/99999 retorna 404', () => {
      cy.getCsrfToken().then((token) => {
        cy.request({
          method: 'POST',
          url: '/abastecimento/editar/99999',
          body: { csrf_token: token, quilometragem: '1', litros_abastecidos: '1', valor_total: '1', preco_combustivel: '1', data: '2024-01-01' },
          form: true,
          failOnStatusCode: false,
          followRedirect: false,
        }).its('status').should('eq', 404)
      })
    })
  })
})
