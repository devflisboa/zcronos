// Importa commands customizados
import './commands'

// Suprimir erros de JS não-críticos do app (ex: Chart.js warnings)
Cypress.on('uncaught:exception', (err) => {
  if (err.message.includes('ResizeObserver') || err.message.includes('Non-Error')) {
    return false
  }
})
