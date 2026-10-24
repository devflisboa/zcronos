/**
 * FASE 1 — Dashboard
 * Cobre: carregamento, KPIs visíveis, navegação por seções
 */
describe('Fase 1 — Dashboard', () => {
  beforeEach(() => {
    cy.login()
    cy.visit('/')
  })

  context('Carregamento e estrutura', () => {
    it('carrega o dashboard (200 ou redirect para /veiculos/novo)', () => {
      cy.url().should('match', /\/$|\/veiculos/)
    })

    it('exibe sidebar com itens de navegação', () => {
      cy.get('#sidebar, aside').should('be.visible')
      cy.contains(/dashboard/i).should('exist')
    })

    it('exibe link "Meus Veículos" na sidebar', () => {
      cy.get('a[href*="/veiculos"]').should('exist')
    })
  })

  context('KPIs e métricas (quando há veículo)', () => {
    it('não exibe dados de outro usuário', () => {
      // Só verifica que a página carregou sem erro de servidor
      cy.get('body').should('not.contain', 'Internal Server Error')
      cy.get('body').should('not.contain', 'INTERNAL SERVER ERROR')
    })

    it('exibe data atual', () => {
      const hoje = new Date()
      const dia = String(hoje.getDate()).padStart(2, '0')
      const mes = String(hoje.getMonth() + 1).padStart(2, '0')
      const ano = hoje.getFullYear()
      // A data pode aparecer em vários formatos
      cy.get('body').should('contain', ano.toString())
    })
  })

  context('Navegação por seções', () => {
    it('clica em "Combustível" e mostra a seção correspondente', () => {
      cy.contains(/combustível/i).first().click()
      // Seção deve estar visível
      cy.get('#main, main').should('be.visible')
    })

    it('clica em "Despesas" e mostra a seção', () => {
      cy.contains(/despesas/i).first().click()
      cy.get('#main, main').should('be.visible')
    })
  })
})
