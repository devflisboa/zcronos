describe('Fase 3 — auditoria local de navegação e responsividade', () => {
  before(() => {expect(Cypress.config('baseUrl')).to.match(/^http:\/\/(127\.0\.0\.1|localhost):5087$/);});
  function login(){cy.login();}
  for(const width of [360,1280]){
    it('renderiza cadastro em '+width,()=>{cy.viewport(width,900);cy.visit('/auth/registro');cy.get('input[name="nome"]').should('be.visible');cy.get('button[type=submit]').should('be.visible');cy.document().then(doc=>expect(doc.documentElement.scrollWidth).to.be.at.most(width));cy.screenshot('fase3-registro-'+width,{capture:'viewport'});});
    it('navega por todas as novas telas em '+width,()=>{cy.viewport(width,900);login();
      for(const [url,name] of [['/condutor/','condutor'],['/alertas/','alertas'],['/plano','plano'],['/auth/seguranca','seguranca'],['/veiculos/1/fotos','galeria'],['/veiculos/novo','veiculo']]){
        cy.visit(url);cy.get('main').should('be.visible');cy.document().then(doc=>expect(doc.documentElement.scrollWidth,name).to.be.at.most(width));cy.screenshot('fase3-'+name+'-'+width,{capture:'viewport'});
      }
    });
  }
  it('salva perfil e mantém os dados ao retornar',()=>{login();cy.visit('/condutor/');cy.get('#nome').clear().type('Condutor Cypress');cy.contains('button','Salvar perfil').click();cy.contains('Perfil do condutor atualizado.').should('be.visible');cy.visit('/condutor/');cy.get('#nome').should('have.value','Condutor Cypress');});
  it('upload e lightbox funcionam no navegador',()=>{login();cy.visit('/veiculos/1/fotos');
    cy.get('#fotos').selectFile('static/image/icons/icon-192.png');
    cy.contains('button','Adicionar fotos').click();cy.get('.foto-item').should('have.length',1);cy.get('.foto-abrir').click();cy.get('#foto-lightbox').should('be.visible');cy.get('#foto-fechar').click();cy.get('.foto-legenda').type('Foto de teste');cy.contains('button','Salvar legenda').click();cy.contains('Alteração salva.').should('be.visible');
  });
});
