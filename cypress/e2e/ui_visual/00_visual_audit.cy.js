/**
 * Auditoria Visual — Screenshots de todas as telas
 * Captura mobile (375px) e desktop (1280px) para análise de UI/UX.
 * Não faz assertions de negócio — foca em capturar estado visual.
 */

const MOBILE  = { width: 375, height: 812, name: 'mobile' }
const DESKTOP = { width: 1280, height: 800, name: 'desktop' }
const VIEWPORTS = [MOBILE, DESKTOP]

function shot(label) {
  cy.screenshot(label, { overwrite: true, capture: 'fullPage' })
}

describe('Auditoria Visual — Screenshots', () => {

  // ── Login ──────────────────────────────────────────────────────────────────
  context('Tela de Login', () => {
    VIEWPORTS.forEach(({ width, height, name }) => {
      it(`login — ${name}`, () => {
        cy.viewport(width, height)
        cy.visit('/auth/login')
        cy.get('form').should('be.visible')
        shot(`login/${name}/01_tela_inicial`)

        // Estado: campo com erro
        cy.get('input[name="email"]').type('invalido@email.com')
        cy.get('input[name="senha"]').type('senhaerrada')
        cy.get('form').submit()
        cy.url().should('include', '/auth/login')
        shot(`login/${name}/02_erro_credenciais`)
      })
    })
  })

  // ── Lista de Veículos ──────────────────────────────────────────────────────
  context('Meus Veículos', () => {
    VIEWPORTS.forEach(({ width, height, name }) => {
      it(`veiculos/index — ${name}`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit('/veiculos/')
        cy.get('body').should('not.contain', 'Internal Server Error')
        shot(`veiculos/${name}/01_lista`)

        // Sidebar aberta no mobile
        if (name === 'mobile') {
          cy.get('#sb-toggle').click()
          cy.wait(400)
          shot(`veiculos/${name}/02_sidebar_aberta`)
          cy.get('#sb-overlay').click()
          cy.wait(300)
        }
      })
    })
  })

  // ── Formulário de Veículo ──────────────────────────────────────────────────
  context('Novo Veículo — Formulário', () => {
    VIEWPORTS.forEach(({ width, height, name }) => {
      it(`veiculos/novo — ${name}`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit('/veiculos/novo')
        cy.get('form').should('be.visible')
        shot(`veiculos/${name}/03_form_vazio`)

        // Formulário preenchido
        cy.get('input[name="marca"]').type('Honda')
        cy.get('input[name="modelo"]').type('Civic')
        cy.get('input[name="ano"]').clear().type('2023')
        cy.get('input[name="placa"]').type('ABC1D23')
        cy.get('input[name="km_atual"]').clear().type('25000')
        shot(`veiculos/${name}/04_form_preenchido`)
      })
    })
  })

  // ── Dashboard Principal ────────────────────────────────────────────────────
  context('Dashboard', () => {
    VIEWPORTS.forEach(({ width, height, name }) => {
      it(`dashboard — ${name}`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit('/')
        cy.url().should('match', /\/$|\/veiculos/)
        cy.wait(800)  // aguarda animações/boot screen

        // Só captura dashboard se não redirecionou para veículos
        cy.url().then((url) => {
          if (url.includes('/veiculos')) {
            shot(`dashboard/${name}/01_sem_veiculo_redirect`)
          } else {
            shot(`dashboard/${name}/01_dashboard_inicial`)

            // Scroll para ver mais conteúdo
            cy.scrollTo('bottom', { duration: 500 })
            shot(`dashboard/${name}/02_dashboard_scroll_bottom`)
            cy.scrollTo('top')

            // Sidebar aberta no mobile
            if (name === 'mobile') {
              cy.get('#sb-toggle').first().click({ force: true })
              cy.wait(400)
              shot(`dashboard/${name}/03_sidebar_aberta`)
              cy.get('#sb-overlay').click({ force: true })
              cy.wait(300)
            }

            // Seção Combustível
            cy.contains(/combustível/i).first().click({ force: true })
            cy.wait(300)
            shot(`dashboard/${name}/04_secao_combustivel`)

            // Seção Despesas
            cy.contains(/despesas/i).first().click({ force: true })
            cy.wait(300)
            shot(`dashboard/${name}/05_secao_despesas`)
          }
        })
      })
    })
  })

  // ── Fluxo Abastecimento ────────────────────────────────────────────────────
  context('Formulário de Abastecimento', () => {
    VIEWPORTS.forEach(({ width, height, name }) => {
      it(`abastecimento/cadastrar — ${name}`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit('/abastecimento/cadastrar')
        cy.get('body').should('not.contain', 'Internal Server Error')
        shot(`abastecimento/${name}/01_form`)
      })
    })
  })

  // ── Fluxo Despesa ──────────────────────────────────────────────────────────
  context('Formulário de Despesa', () => {
    VIEWPORTS.forEach(({ width, height, name }) => {
      it(`despesa/cadastrar — ${name}`, () => {
        cy.login()
        cy.viewport(width, height)
        cy.visit('/despesa/cadastrar')
        cy.get('body').should('not.contain', 'Internal Server Error')
        shot(`despesa/${name}/01_form`)
      })
    })
  })

})
