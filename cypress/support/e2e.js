// Importa commands customizados
import './commands'

// Suprimir erros de JS não-críticos do app (ex: Chart.js warnings)
Cypress.on('uncaught:exception', (err) => {
  // Ignora erros não-críticos do app que não afetam os testes
  const ignored = ['ResizeObserver', 'Non-Error', 'Chart is not defined', 'lucide']
  if (ignored.some(msg => err.message.includes(msg))) return false
})
