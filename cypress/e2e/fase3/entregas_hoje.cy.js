const senha = 'TesteSenha123!'
const login = (email, pw) => cy.login(email, pw || senha)
const cotacao = '/fipe/?modo=meu&veiculo_id=1&tipo=cars&marca=1&modelo=101&ano=2022-1'
const manutencao = {veiculo_id: '1', tipo: 'oleo', descricao: 'Manutenção Cypress', status: 'pendente', custo: '0'}

describe('Entregas de hoje — autenticação e onboarding', () => {
  before(() => cy.e2eControle('reset', {}))
  it('registra, confirma e inicia onboarding sem atribuir veículo de outra conta', () => {
    cy.visit('/auth/registro')
    cy.get('#nome').type('Nova Conta')
    cy.get('#email').type('nova@example.test')
    cy.get('#senha').type(senha, {log: false})
    cy.get('#confirmar_senha').type(senha, {log: false})
    cy.get('form').submit()
    cy.e2eControle('tokens?email=nova@example.test').then(({body}) => {
      cy.visit('/auth/confirmar/' + body.confirmacao)
      cy.get('button[type=submit]').click()
    })
    login('nova@example.test')
    cy.visit('/')
    cy.location('pathname').should('eq', '/condutor/')
    cy.contains('Informar condutor depois').click()
    cy.location('pathname').should('eq', '/veiculos/novo')
    cy.get('input[name=modelo]').should('have.value', '')
  })

  it('recuperação é genérica e não envia SMTP real', () => {
    cy.visit('/auth/recuperar-senha')
    cy.get('input[name=email]').type('inexistente@example.test')
    cy.get('form').submit()
    cy.contains('Se o endereço possuir uma conta com senha').should('be.visible')
    cy.e2eControle().its('body.emails').should('eq', 0)
  })

  it('recusa mudança com senha atual incorreta e mantém login anterior', () => {
    login()
    cy.postSeguro('/auth/senha', {senha_atual: 'incorreta', nova_senha: 'OutraSenha123!', confirmar_senha: 'OutraSenha123!'})
    cy.visit('/auth/seguranca')
    cy.contains('Senha atual incorreta').should('be.visible')
  })

  it('redefine senha com token e rejeita reutilização', () => {
    cy.e2eControle('tokens?email=teste@zcronos.local').then(({body}) => {
      const url = '/auth/redefinir-senha/' + body.senha
      cy.visit(url)
      cy.get('input[name=senha]').type('SenhaNovaCypress123!', {log: false})
      cy.get('input[name=confirmar_senha]').type('SenhaNovaCypress123!', {log: false})
      cy.get('form').submit()
      cy.contains('Senha redefinida').should('be.visible')
      cy.visit(url)
      cy.location('pathname').should('eq', '/auth/recuperar-senha')
    })
  })

  it('conta sem veículos segue para condutor e permite pular', () => {
    login('vazio@example.test')
    cy.visit('/')
    cy.location('pathname').should('eq', '/condutor/')
    cy.contains('Informar condutor depois').click()
    cy.location('pathname').should('eq', '/veiculos/novo')
  })
})

describe('Entregas de hoje — isolamento real entre duas contas', () => {
  before(() => cy.e2eControle('reset', {}))
  beforeEach(() => login())
  for (const url of ['/veiculos/3/editar', '/veiculos/3/fotos', '/relatorios/3/exportar.csv', '/fipe/?modo=meu&veiculo_id=3']) {
    it('recusa leitura privada: ' + url, () => cy.request({url, failOnStatusCode: false}).its('status').should('eq', 404))
  }
  for (const url of ['/despesa/delete/1', '/abastecimento/delete/1', '/manutencao/delete/2', '/manutencao/concluir/2']) {
    it('recusa alteração privada: ' + url, () => {
      cy.postSeguro(url).its('status').should('eq', 404)
      cy.logout()
      login('b@example.test')
      cy.visit('/')
      cy.contains('Segredo do usuário B').should('exist')
      const registro = url.includes('/despesa/') ? 'Despesa privada B' : url.includes('/abastecimento/') ? 'Posto privado B' : 'Manutenção privada B'
      cy.contains(registro).should('exist')
    })
  }
  it('dashboard e lista não revelam registros privados', () => {
    cy.visit('/')
    cy.get('body').should('not.contain', 'Despesa privada B').and('not.contain', 'Posto privado B')
    cy.visit('/veiculos/')
    cy.get('body').should('not.contain', 'Segredo do usuário B')
  })
  it('CSRF é obrigatório mesmo autenticado', () => {
    cy.request({method: 'POST', url: '/manutencao/add', form: true, body: manutencao, failOnStatusCode: false}).its('status').should('eq', 400)
  })
})

describe('Entregas de hoje — manutenção, falhas e alertas', () => {
  before(() => cy.e2eControle('reset', {}))
  beforeEach(() => login())
  for (const [campo, valor] of [['km_previsto','-1'], ['km_previsto','1.5'], ['km_previsto','2147483648'], ['custo','NaN'], ['custo','-2'], ['custo','1.001'], ['status','inventado'], ['tipo','inventado'], ['data_prevista','invalida']]) {
    it('recusa ' + campo + '=' + valor + ' sem gravar', () => {
      cy.postSeguro('/manutencao/add', {...manutencao, [campo]: valor}, {headers: {Accept: 'application/json'}}).then(r => {
        expect(r.status).to.eq(422)
        expect(r.body.ok).to.eq(false)
      })
      cy.visit('/')
      cy.get('body').should('not.contain', 'Manutenção Cypress')
    })
  }
  it('POST HTML preserva campos e abre somente o modal de cadastro', () => {
    cy.visit('/')
    cy.window().then(win => win.openModal('manutencao'))
    cy.get('#modal-manutencao form').then($form => {
      $form.find('[name=tipo]').val('oleo')
      $form.find('[name=descricao]').val('Texto preservado <seguro>')
      $form.find('[name=custo]').val('-1')
      $form[0].submit()
    })
    cy.get('#modal-manutencao.open [name=descricao]').should('have.value', 'Texto preservado <seguro>')
    cy.get('#modal-manutencao [role=alert]').should('contain', 'custo')
    cy.get('.modal-overlay.open').should('have.length', 1)
  })
  it('JSON de validação preserva os valores e permite correção', () => {
    cy.visit('/')
    cy.window().then(win => win.openModal('manutencao'))
    cy.get('#modal-manutencao [name=tipo]').select('oleo')
    cy.get('#modal-manutencao [name=descricao]').type('Preservar no navegador')
    cy.get('#modal-manutencao [name=data_realizada]').type('2099-01-01')
    cy.get('#modal-manutencao button[type=submit]').click()
    cy.get('#modal-manutencao [role=status]').should('contain', 'futuro')
    cy.get('#modal-manutencao [name=descricao]').should('have.value', 'Preservar no navegador')
    cy.get('#modal-manutencao button[type=submit]').should('be.enabled')
  })
  it('falha de rede mantém campos e bloqueia repetição incerta', () => {
    cy.intercept('POST', '/manutencao/add', {forceNetworkError: true})
    cy.visit('/')
    cy.window().then(win => win.openModal('manutencao'))
    cy.get('#modal-manutencao [name=tipo]').select('oleo')
    cy.get('#modal-manutencao [name=descricao]').type('Conferir antes de reenviar')
    cy.get('#modal-manutencao button[type=submit]').click()
    cy.get('#modal-manutencao [role=status]').should('contain', 'Não foi possível confirmar')
    cy.get('#modal-manutencao button[type=submit]').should('be.disabled')
    cy.get('#modal-manutencao [name=descricao]').should('have.value', 'Conferir antes de reenviar')
  })
  it('troca de veículo em outra aba recusa gravação no carro diferente', () => {
    cy.postSeguro('/veiculos/2/selecionar')
    cy.postSeguro('/manutencao/add', manutencao, {headers:{Accept:'application/json'}}).its('status').should('eq',409)
  })
  it('conclui com custo zero e não permite sobrescrever na repetição', () => {
    cy.postSeguro('/manutencao/concluir/1', {veiculo_id:'1', custo:'0', km_realizada:'0'}).its('status').should('eq',302)
    cy.postSeguro('/manutencao/concluir/1', {veiculo_id:'1', custo:'900'}).its('status').should('eq',302)
    cy.request('/relatorios/1/exportar.csv?tipo=manutencoes').its('body').should('contain', ';0.0;realizada')
    cy.visit('/alertas/')
    cy.get('body').should('not.contain', 'Revisão — Toyota Corolla')
  })
  it('rejeita odômetro inválido e preserva o anterior', () => {
    cy.postSeguro('/km/atualizar', {km_atual:'-1'})
    cy.visit('/veiculos/1/editar')
    cy.get('[name=km_atual]').should('have.value','12000')
  })
  it('mostra urgência, data e km, com destino para revisar a CNH', () => {
    cy.visit('/alertas/')
    cy.contains('Urgente').should('be.visible')
    cy.contains('Limite ultrapassado em 2.000 km').should('be.visible')
    cy.get('a[href="/condutor/"]').should('contain','Revisar')
  })
})

describe('Entregas de hoje — FIPE pelo backend simulado', () => {
  before(() => cy.e2eControle('reset', {}))
  beforeEach(() => login())
  it('entende meu carro sem escolher automaticamente versão', () => {
    cy.visit('/fipe/?pergunta=quanto%20meu%20carro%20ta%20valendo')
    cy.contains('Seu veículo: Toyota Corolla').should('be.visible')
    cy.get('#fipe-modelo').should('have.value','')
    cy.get('#fipe-resposta').should('not.exist')
  })
  it('consulta outro veículo sem cadastrar ou alterar o atual', () => {
    cy.visit(cotacao.replace('modo=meu&veiculo_id=1','modo=outro'))
    cy.contains('R$ 100.000,00').should('be.visible')
    cy.contains('Esta consulta não cadastrou').should('be.visible')
    cy.get('form[action*="/confirmar"]').should('not.exist')
  })
  it('salva referência confirmada preservando compra e valor manual', () => {
    cy.visit(cotacao)
    cy.get('[name=confirmar]').check()
    cy.get('form[action*="/confirmar"]').submit()
    cy.visit('/veiculos/1/editar')
    cy.get('[name=valor_atual]').invoke('val').should('match',/^90000/)
    cy.get('[name=valor_compra]').invoke('val').should('match',/^80000/)
    cy.contains('002001-1').should('exist')
  })
  it('aplica preço somente com autorização explícita', () => {
    cy.visit(cotacao)
    cy.get('[name=confirmar]').check()
    cy.get('[name=atualizar_valor]').check()
    cy.get('form[action*="/confirmar"]').submit()
    cy.visit('/veiculos/1/editar')
    cy.get('[name=valor_atual]').invoke('val').should('match',/^100000/)
  })
  it('recusa token adulterado sem mudar valores', () => {
    cy.postSeguro('/fipe/1/confirmar',{confirmar:'sim',cotacao_token:'adulterado'})
    cy.visit('/veiculos/1/editar')
    cy.get('[name=valor_atual]').invoke('val').should('match',/^90000/)
  })
  it('reutiliza cache sem segunda chamada ao provedor', () => {
    cy.visit(cotacao)
    cy.e2eControle().then(({body}) => {
      const chamadas = body.chamadas.length
      cy.reload()
      cy.e2eControle().its('body.chamadas').should('have.length',chamadas)
    })
  })
  it('mostra indisponibilidade sem inventar preço', () => {
    cy.e2eControle('cenario',{fipe_erro:429})
    cy.visit(cotacao)
    cy.contains('limite de consultas').should('be.visible')
    cy.get('#fipe-resposta').should('not.exist')
  })
  it('alterar identidade invalida referência salva', () => {
    cy.visit(cotacao)
    cy.get('[name=confirmar]').check()
    cy.get('form[action*="/confirmar"]').submit()
    cy.visit('/veiculos/1/editar')
    cy.get('[name=modelo]').clear().type('Outro modelo')
    cy.get('form').submit()
    cy.visit('/veiculos/1/editar')
    cy.contains('002001-1').should('not.exist')
  })
})

describe('Entregas de hoje — documentos, perfil e galeria', () => {
  before(() => cy.e2eControle('reset', {}))
  beforeEach(() => login())
  it('exige consentimento antes de enviar CNH', () => {
    cy.visit('/condutor/')
    cy.get('#documentos-cnh').selectFile('static/image/icons/icon-192.png')
    cy.get('.documento-enviar').click()
    cy.get('.documento-status').should('contain','autorização')
    cy.e2eControle().its('body.chamadas').should('have.length',0)
  })
  for (const [tipo,url] of [['cnh','/condutor/'], ['crlv','/veiculos/novo']]) {
    it('importa '+tipo+' pelo backend e pede revisão sem salvar automaticamente', () => {
      cy.visit(url)
      cy.on('window:confirm',()=>true)
      cy.get('#documentos-'+tipo).selectFile('static/image/icons/icon-192.png')
      cy.get('.documento-consentimento').check()
      cy.get('.documento-enviar').click()
      cy.get('.documento-status').should('contain','Revise os dados')
      cy.get('[data-extraido=true]').should('have.length.at.least',2)
      cy.e2eControle().its('body.chamadas').should('have.length',1)
    })
  }
  it('cancelar substituição mantém campos já digitados', () => {
    cy.visit('/condutor/')
    cy.get('#nome').clear().type('Nome manual')
    cy.on('window:confirm',()=>false)
    cy.get('#documentos-cnh').selectFile('static/image/icons/icon-192.png')
    cy.get('.documento-consentimento').check()
    cy.get('.documento-enviar').click()
    cy.get('.documento-status').should('contain','mantidos')
    cy.get('#nome').should('have.value','Nome manual')
  })
  it('falha OCR libera o formulário e preserva campos', () => {
    cy.e2eControle('cenario',{ocr_erro:true})
    cy.visit('/condutor/')
    cy.get('#nome').clear().type('Manter nome')
    cy.get('#documentos-cnh').selectFile('static/image/icons/icon-192.png')
    cy.get('.documento-consentimento').check()
    cy.get('.documento-enviar').click()
    cy.get('.documento-status').should('contain','Não foi possível')
    cy.get('#nome').should('have.value','Manter nome')
    cy.get('#condutor-form button[type=submit]').should('be.enabled')
  })
  it('OCR desconfigurado mantém preenchimento manual', () => {
    cy.e2eControle('cenario',{ocr_desabilitado:true})
    cy.visit('/condutor/')
    cy.get('#documentos-cnh').should('be.disabled')
    cy.get('#nome').should('be.enabled')
  })
  it('CPF inválido preserva nome e seleção de veículos', () => {
    cy.visit('/condutor/')
    cy.get('#nome').clear().type('Nome preservado')
    cy.get('#cpf').type('11111111111')
    cy.get('[name=veiculos][value=1]').check()
    cy.get('#condutor-form').submit()
    cy.get('#nome').should('have.value','Nome preservado')
    cy.get('[name=veiculos][value=1]').should('be.checked')
  })
  it('bloqueia acesso público aos uploads', () => {
    cy.request({url:'/static/uploads/veiculos/1/arquivo.jpg',failOnStatusCode:false}).its('status').should('eq',404)
  })
})

describe('Entregas de hoje — planos, limites e segurança', () => {
  before(() => cy.e2eControle('reset', {}))
  it('plano gratuito não exporta relatório e não recebe e-mail Pro', () => {
    login('b@example.test')
    cy.request({url:'/relatorios/3/exportar.csv',followRedirect:false}).then(r=>{
      expect(r.status).to.eq(302)
      expect(r.headers.location).to.include('/plano')
    })
    cy.postSeguro('/alertas/',{email:'sim'}).then(r=>expect(r.headers.location).to.include('/plano'))
  })
  it('limite free impede segundo veículo sem excluir o existente', () => {
    login('b@example.test')
    cy.postSeguro('/veiculos/novo',{marca:'Outra',modelo:'Não cadastrar',ano:'2022'})
    cy.visit('/veiculos/')
    cy.get('body').should('not.contain','Não cadastrar')
    cy.contains('Segredo do usuário B').should('exist')
  })
  it('Frota fica fora da contratação enquanto decisão está pendente', () => {
    login('pro@example.test')
    cy.visit('/plano')
    cy.get('#plano-contratar option[value=frota]').should('not.exist')
  })
  it('gateway rejeitado não libera plano nem envia cobrança real', () => {
    login('b@example.test')
    cy.postSeguro('/plano/contratar',{plano:'pro',cpf:'52998224725',aceite:'sim',forma:'PIX'})
    cy.visit('/plano')
    cy.contains('Contratação não concluída').should('be.visible')
    cy.contains('Plano atual: Gratuito').should('be.visible')
    cy.e2eControle().its('body.chamadas').should('have.length',1)
  })
  it('webhook sem segredo é recusado', () => {
    cy.request({method:'POST',url:'/webhooks/asaas',body:{event:'PAYMENT_RECEIVED'},failOnStatusCode:false}).its('status').should('eq',401)
  })
  it('administrador exclusivo e passkeys desconfiguradas', () => {
    login('b@example.test')
    cy.request({url:'/admin/assinaturas',failOnStatusCode:false}).its('status').should('eq',403)
    cy.visit('/auth/seguranca')
    cy.get('#passkey-register').should('be.disabled')
    cy.contains('Login Google aguardando configuração').should('be.visible')
  })
})
