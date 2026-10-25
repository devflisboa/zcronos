/**
 * Testes de Responsividade — Fases 2 e 3 da auditoria
 *
 * Verifica ausência de overflow horizontal, colapso correto de grids,
 * sidebar comportamento mobile, e elementos dentro do viewport nos
 * breakpoints críticos: 320, 375, 480, 768, 900, 1100, 1280px.
 */

const VIEWPORTS = [
  { width: 320,  height: 568,  name: '320_xsmall'   },
  { width: 375,  height: 812,  name: '375_mobile'   },
  { width: 480,  height: 850,  name: '480_mobile_lg'},
  { width: 768,  height: 1024, name: '768_tablet'   },
  { width: 900,  height: 800,  name: '900_tablet_lg'},
  { width: 1100, height: 768,  name: '1100_small_dt'},
  { width: 1280, height: 800,  name: '1280_desktop' },
]

// Verifica que não há scroll horizontal na página
function noHorizontalScroll() {
  cy.window().then((win) => {
    expect(win.document.documentElement.scrollWidth).to.be.lte(
      win.document.documentElement.clientWidth + 2, // 2px de tolerância para bordas/scrollbar
      'Não deve haver overflow horizontal'
    )
  })
}

// Verifica que um seletor está dentro da largura do viewport
function inViewport(selector) {
  cy.get(selector).first().then(($el) => {
    const rect = $el[0].getBoundingClientRect()
    expect(rect.right).to.be.lte(Cypress.config('viewportWidth') + 2,
      `${selector} não deve transbordar o viewport à direita`)
  })
}

describe('Responsividade — Sem Overflow Horizontal', () => {

  // ── Login ──────────────────────────────────────────────────────────────────
  VIEWPORTS.forEach(({ width, height, name }) => {
    it(`login sem overflow — ${name}`, () => {
      cy.viewport(width, height)
      cy.visit('/auth/login')
      cy.get('form').should('be.visible')
      noHorizontalScroll()
      inViewport('input[name="email"]')
      inViewport('.btn-login')
    })
  })
})

describe('Responsividade — Dashboard', () => {

  before(() => { cy.login() })

  VIEWPORTS.forEach(({ width, height, name }) => {
    it(`dashboard layout — ${name}`, () => {
      cy.login()
      cy.viewport(width, height)
      cy.visit('/')
      // Aguarda boot desaparecer
      cy.get('#boot', { timeout: 5000 }).should('not.be.visible')

      cy.url().then((url) => {
        if (url.includes('/veiculos')) {
          // Sem veículo ativo — apenas verifica overflow na lista
          noHorizontalScroll()
          return
        }

        noHorizontalScroll()

        // KPI cards devem estar visíveis
        cy.get('.kpi').first().should('be.visible')
        inViewport('.kpi')

        // Em mobile (≤768px): sidebar deve estar fora da tela por padrão
        if (width <= 768) {
          cy.get('#sidebar').should('have.css', 'transform').and('include', 'matrix')
          cy.get('#sb-toggle').should('be.visible')

          // Abre e fecha sidebar no mobile
          cy.get('#sb-toggle').first().click({ force: true })
          cy.get('#sidebar').should('have.class', 'open')
          cy.wait(200)
          cy.get('#sb-overlay').click({ force: true })
          cy.get('#sidebar').should('not.have.class', 'open')
        } else {
          // Em desktop: sidebar visível, toggle oculto
          cy.get('#sidebar').should('be.visible')
          cy.get('#sb-toggle').should('not.be.visible')
        }

        // Grid-3 (KPI row) deve ter número correto de colunas
        cy.get('.grid-3').first().then(($grid) => {
          const cols = parseInt(
            window.getComputedStyle($grid[0]).gridTemplateColumns.split(' ').length
          )
          if (width <= 768) {
            // 1 coluna em mobile
            expect(cols).to.equal(1)
          } else {
            // 3 colunas em tablet/desktop (grid-3 não colapsa para 2)
            expect(cols).to.equal(3)
          }
        })

        // Scroll até o fundo sem overflow
        cy.scrollTo('bottom')
        noHorizontalScroll()
        cy.scrollTo('top')
      })
    })
  })
})

describe('Responsividade — Formulários', () => {

  const FORM_PAGES = [
    { path: '/abastecimento/cadastrar', name: 'abastecimento', formSel: 'form' },
    { path: '/despesa/cadastrar',       name: 'despesa',        formSel: 'form' },
    { path: '/veiculos/novo',           name: 'veiculo',        formSel: 'form' },
  ]

  FORM_PAGES.forEach(({ path, name, formSel }) => {
    VIEWPORTS.slice(0, 5).forEach(({ width, height, vpName = name }) => { // até 900px
      it(`${name} sem overflow — ${width}px`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit(path)
        cy.get(formSel).should('be.visible')
        noHorizontalScroll()
        inViewport(`${formSel} input`)
        // Botão de submit deve estar dentro do viewport
        cy.get(`${formSel} button[type="submit"], ${formSel} .btn-primary`).first()
          .should('be.visible')
          .then(($btn) => {
            const rect = $btn[0].getBoundingClientRect()
            expect(rect.right).to.be.lte(width + 2, 'Botão submit não deve transbordar')
          })
      })
    })
  })
})

describe('Responsividade — Grid colapso correto', () => {

  it('grid-4 → 2 colunas em 1100px', () => {
    cy.login()
    cy.viewport(1100, 768)
    cy.visit('/')
    cy.get('#boot', { timeout: 5000 }).should('not.be.visible')
    cy.url().then((url) => {
      if (url.includes('/veiculos')) return
      cy.get('.grid-4').first().then(($grid) => {
        const cols = $grid[0].style.gridTemplateColumns ||
          window.getComputedStyle($grid[0]).gridTemplateColumns
        // 2 colunas = 2 valores separados por espaço
        expect(cols.trim().split(' ').filter(Boolean).length).to.equal(2)
      })
    })
  })

  it('grid-3 permanece 3 colunas em 900px', () => {
    cy.login()
    cy.viewport(900, 768)
    cy.visit('/')
    cy.get('#boot', { timeout: 5000 }).should('not.be.visible')
    cy.url().then((url) => {
      if (url.includes('/veiculos')) return
      cy.get('.grid-3').first().then(($grid) => {
        const cols = window.getComputedStyle($grid[0]).gridTemplateColumns
        expect(cols.trim().split(' ').filter(Boolean).length).to.equal(3)
      })
    })
  })

  it('todos os grids → 1 coluna em 768px', () => {
    cy.login()
    cy.viewport(768, 1024)
    cy.visit('/')
    cy.get('#boot', { timeout: 5000 }).should('not.be.visible')
    cy.url().then((url) => {
      if (url.includes('/veiculos')) return
      cy.get('.grid-3, .grid-4, .grid-2').each(($grid) => {
        const cols = window.getComputedStyle($grid[0]).gridTemplateColumns
        expect(cols.trim().split(' ').filter(Boolean).length).to.equal(1)
      })
    })
  })
})

describe('Responsividade — Páginas de Conta', () => {

  const CONTA_PAGES = [
    '/condutor/',
    '/alertas/',
    '/relatorios/',
    '/auth/seguranca',
  ]

  const MOBILE_VIEWPORTS = VIEWPORTS.slice(0, 3) // 320, 375, 480

  CONTA_PAGES.forEach((path) => {
    MOBILE_VIEWPORTS.forEach(({ width, height, name }) => {
      it(`${path} sem overflow — ${name}`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit(path)
        cy.get('body').should('not.contain', 'Internal Server Error')
        noHorizontalScroll()
      })
    })
  })
})
