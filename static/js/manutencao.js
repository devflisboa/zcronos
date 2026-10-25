(() => {
  document.querySelectorAll('form[data-manutencao]').forEach(form => {
    const mensagem = document.createElement('p');
    mensagem.className = 'ajuda';
    mensagem.setAttribute('role', 'status');
    mensagem.setAttribute('tabindex', '-1');
    form.prepend(mensagem);
    let bloqueado = false;

    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (bloqueado) return;
      bloqueado = true;
      const botoes = [...form.querySelectorAll('[type="submit"]')];
      botoes.forEach(botao => { botao.disabled = true; });
      form.setAttribute('aria-busy', 'true');
      mensagem.textContent = 'Salvando manutenção…';
      const controle = new AbortController();
      const prazo = setTimeout(() => controle.abort(), 25000);
      let incerto = true;
      try {
        const resposta = await fetch(form.action, {
          method: 'POST', body: new FormData(form), credentials: 'same-origin',
          headers: {Accept: 'application/json'}, signal: controle.signal
        });
        if (resposta.redirected) {
          mensagem.textContent = 'Sua sessão pode ter expirado. Mantenha esta tela aberta e entre novamente em outra aba antes de reenviar.';
          incerto = false;
          return;
        }
        if (!resposta.headers.get('content-type')?.includes('application/json')) {
          if ([400, 401, 403, 404, 429].includes(resposta.status)) {
            incerto = false;
            mensagem.textContent = 'A solicitação foi recusada. Confira sua sessão e o veículo selecionado antes de tentar novamente. Os campos foram mantidos.';
            return;
          }
          throw new Error('Resposta sem confirmação');
        }
        const dados = await resposta.json();
        if (typeof dados.ok !== 'boolean' || typeof dados.mensagem !== 'string') {
          throw new Error('Resposta inválida');
        }
        if (resposta.ok && dados.ok) {
          mensagem.textContent = dados.mensagem;
          const destino = new URL(dados.destino, window.location.origin);
          if (destino.origin !== window.location.origin) throw new Error('Destino inválido');
          window.location.assign(destino.href);
          return;
        }
        if (resposta.status >= 500) throw new Error('Resultado sem confirmação');
        incerto = false;
        mensagem.textContent = dados.mensagem;
      } catch (_) {
        mensagem.textContent = 'Não foi possível confirmar o resultado. Seus campos continuam nesta tela. Confira a agenda em outra aba antes de registrar novamente. Recarregue esta página somente após conferir; não há reenvio automático.';
      } finally {
        clearTimeout(prazo);
        form.removeAttribute('aria-busy');
        if (!incerto) {
          bloqueado = false;
          botoes.forEach(botao => { botao.disabled = false; });
        }
        mensagem.focus();
      }
    });
  });
})();
