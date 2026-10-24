const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    // Sobrescrito por cypress.env.json (BASE_URL)
    baseUrl: 'http://zcronos.duckdns.org',
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
      TEST_USER_SENHA: 'TesteSenha123',
    },

    setupNodeEvents(on, config) {
      if (config.env.BASE_URL) {
        config.baseUrl = config.env.BASE_URL
      }
      return config
    },
  },
})
