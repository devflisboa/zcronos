document.querySelectorAll('.documento-import').forEach(section => {
  const button = section.querySelector('.documento-enviar');
  const status = section.querySelector('.documento-status');
  const form = section.closest('form');
  button.addEventListener('click', async () => {
    const files = [...section.querySelector('input[type=file]').files];
    const limiteArquivos = section.dataset.tipo === 'cnh' ? 2 : 1;
    if (!files.length || files.length > limiteArquivos || files.reduce((n,f) => n + f.size,0) > 10*1024*1024) {
      status.textContent = section.dataset.tipo === 'cnh'
        ? 'Selecione um PDF ou até duas imagens, com até 10 MB no total.'
        : 'Selecione um arquivo JPG, PNG ou PDF de até 10 MB.';
      return;
    }
    if (files.length > 1 && files.some(file => file.type === 'application/pdf')) {
      status.textContent = 'Envie um PDF completo ou duas imagens da CNH, sem misturar os formatos.'; return;
    }
    if (!section.querySelector('.documento-consentimento').checked) {
      status.textContent = 'Confirme a autorização de envio antes de continuar.'; return;
    }
    const data = new FormData(); files.forEach(file => data.append('documentos',file));
    data.append('consentimento','sim');
    const salvar = [...(form?.querySelectorAll('button[type="submit"]') || [])];
    const estados = salvar.map(element => element.disabled);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 75000);
    button.disabled = true;
    salvar.forEach(element => { element.disabled = true; });
    section.setAttribute('aria-busy', 'true');
    status.textContent = 'Analisando documento… Aguarde para revisar os campos.';
    try {
      const token = document.querySelector('meta[name="csrf-token"]')?.content || form?.querySelector('input[name="csrf_token"]')?.value;
      const response = await fetch(section.dataset.endpoint, {method:'POST',body:data, signal:controller.signal,
        headers:{'X-CSRFToken':token}});
      if (response.redirected || response.status === 401) {
        throw new Error('Sua sessão expirou. Entre novamente para importar o documento.');
      }
      if (response.status === 413) throw new Error('O arquivo excede o tamanho permitido. Use até 10 MB.');
      const result = await response.json().catch(() => { throw new Error('Não foi possível ler a resposta. Tente novamente.'); });
      if (!response.ok) throw new Error(result.erro || 'Não foi possível importar o documento.');
      if (!result.campos || typeof result.campos !== 'object' || Array.isArray(result.campos)) {
        throw new Error('Não foi possível identificar os campos do documento. Preencha manualmente.');
      }
      const campos = Object.entries(result.campos).map(([name,value]) => ({
        input: form?.elements.namedItem(name), value
      })).filter(({input,value}) => input instanceof HTMLElement && typeof value === 'string' && value.trim());
      if (!campos.length) {
        status.textContent = 'Nenhum campo legível foi identificado. Use outro arquivo ou preencha manualmente.'; return;
      }
      const substituir = campos.some(({input,value}) => input.value.trim() && input.value !== value);
      if (substituir && !window.confirm('Os dados lidos vão substituir alguns campos já preenchidos. Deseja continuar?')) {
        status.textContent = 'Seus campos foram mantidos. Você pode preencher ou corrigir os dados manualmente.'; return;
      }
      campos.forEach(({input,value}) => {
        input.value = value.trim();
        input.dataset.extraido = 'true';
        input.dispatchEvent(new Event('input',{bubbles:true}));
      });
      status.textContent = `${campos.length} campo(s) preenchido(s). Revise os dados destacados e complete o que faltar antes de salvar.`;
      section.querySelector('input[type=file]').value = '';
    } catch(error) {
      status.textContent = error.name === 'AbortError'
        ? 'A leitura demorou mais que o esperado. Seus campos foram preservados; tente novamente.'
        : error instanceof TypeError ? 'Falha de conexão. Seus campos foram preservados.' : error.message;
    } finally {
      clearTimeout(timeout);
      button.disabled = false;
      salvar.forEach((element,index) => { element.disabled = estados[index]; });
      section.removeAttribute('aria-busy');
    }
  });
});
