const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    // Sobrescrito por cypress.env.json (BASE_URL)
    baseUrl: 'http://127.0.0.1:5087',
    viewportWidth: 1280,
    viewportHeight: 800,
    defaultCommandTimeout: 10000,
    requestTimeout: 15000,
    responseTimeout: 15000,
    video: false,
    screenshotOnRunFailure: true,
    screenshotsFolder: 'cypress/screenshots',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: 'cypress/support/e2e.js',

    env: {
      TEST_USER_EMAIL: 'teste@zcronos.local',
      TEST_USER_SENHA: 'TesteSenha123!',
    },

    setupNodeEvents(on, config) {
      if (config.env.BASE_URL) {
        config.baseUrl = config.env.BASE_URL
      }
      const alvo = new URL(config.baseUrl)
      if (!['127.0.0.1', 'localhost'].includes(alvo.hostname) || alvo.port !== '5087') {
        throw new Error('Cypress deve usar somente a instância descartável local na porta 5087.')
      }
      config.env.TEST_USER_EMAIL = 'teste@zcronos.local'
      config.env.TEST_USER_SENHA = 'TesteSenha123!'
      return config
    },
  },
})
