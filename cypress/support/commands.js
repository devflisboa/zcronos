/**
 * cy.login(email, senha) — faz login via UI e aguarda o dashboard
 */
Cypress.Commands.add('login', (email, senha) => {
  const testEmail = email || Cypress.env('TEST_USER_EMAIL')
  const testSenha = senha || Cypress.env('TEST_USER_SENHA')

  cy.session(
    [testEmail],
    () => {
      cy.visit('/auth/login')
      cy.get('input[name="email"]').clear().type(testEmail)
      cy.get('input[name="senha"]').clear().type(testSenha)
      cy.get('form').submit()
      // Aguarda redirect: ou dashboard ou página de veículo
      cy.url().should('not.include', '/auth/login')
    },
    {
      validate() {
        cy.request({ url: '/', followRedirect: false }).then((resp) => {
          // 200 = dashboard, 302 sem /auth/login = autenticado
          expect(resp.status).to.be.oneOf([200, 302])
          if (resp.status === 302) {
            expect(resp.headers.location).to.not.include('/auth/login')
          }
        })
      },
    }
  )
})

/**
 * cy.logout() — clica no link de sair e aguarda tela de login
 */
Cypress.Commands.add('logout', () => {
  cy.visit('/auth/logout')
  cy.url().should('include', '/auth/login')
})

/**
 * cy.getCsrfToken() — extrai o CSRF token da meta tag
 */
Cypress.Commands.add('getCsrfToken', () => {
  return cy.get('meta[name="csrf-token"]').invoke('attr', 'content')
})
