// Importa commands customizados
import './commands'

beforeEach(() => {
  cy.e2eControle('reset', {}).its('body.ambiente').should('eq', 'autoviu-cypress-descartavel')
  // Bibliotecas visuais não são o objeto desta suíte; evitar dependência de CDN.
  cy.intercept('https://cdn.jsdelivr.net/**', {headers: {'content-type': 'application/javascript'},
    body: 'window.Chart=function(){this.destroy=function(){};}; window.Chart.defaults={font:{}}; window.Chart.getChart=function(){return null;};'})
  cy.intercept('https://unpkg.com/lucide@*/**', {headers: {'content-type': 'application/javascript'},
    body: 'window.lucide={createIcons:function(){}};'})
})

// Ignorar somente o aviso conhecido do observador de layout, sem ocultar falhas da aplicação.
Cypress.on('uncaught:exception', (err) => {
  if (err.message.includes('ResizeObserver loop')) return false
})
