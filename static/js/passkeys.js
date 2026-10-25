(() => {
  const status=document.getElementById('passkey-status');
  const decode=value=>Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4)),c=>c.charCodeAt(0));
  const encode=buffer=>btoa(String.fromCharCode(...new Uint8Array(buffer))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
  async function post(url,data={}){const token=document.querySelector('meta[name="csrf-token"]')?.content||document.querySelector('input[name="csrf_token"]')?.value;
    const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify(data)});
    if(response.redirected)throw new Error('Entre novamente com sua senha antes de gerenciar passkeys.');
    let json;try{json=await response.json();}catch(e){throw new Error('Serviço indisponível. Tente novamente.');}if(!response.ok)throw new Error(json.erro||'Não foi possível concluir.');return json;
  }
  function pack(credential){const response=credential.response;const result={id:credential.id,rawId:encode(credential.rawId),type:credential.type,response:{clientDataJSON:encode(response.clientDataJSON)},clientExtensionResults:credential.getClientExtensionResults()};
    if(response.attestationObject){result.response.attestationObject=encode(response.attestationObject);result.response.transports=response.getTransports?.()||[];}
    else {result.response.authenticatorData=encode(response.authenticatorData);result.response.signature=encode(response.signature);result.response.userHandle=response.userHandle?encode(response.userHandle):null;}return result;
  }
  async function execute(button,fn){button.disabled=true;if(status)status.textContent='Aguardando confirmação no dispositivo…';try{if(!window.PublicKeyCredential)throw new Error('Este navegador não suporta passkeys.');await fn();}catch(e){if(status)status.textContent=e.name==='NotAllowedError'?'Operação cancelada ou expirada. Tente novamente.':e.message;}finally{button.disabled=false;}}
  const register=document.getElementById('passkey-register');if(register)register.onclick=()=>execute(register,async()=>{const options=await post('/auth/webauthn/register/begin');options.challenge=decode(options.challenge);options.user.id=decode(options.user.id);options.excludeCredentials?.forEach(c=>c.id=decode(c.id));
    const credential=await navigator.credentials.create({publicKey:options});await post('/auth/webauthn/register/finish',{credential:pack(credential),nome:document.getElementById('dispositivo').value});localStorage.setItem('autoviu-passkey','1');location.reload();});
  const login=document.getElementById('passkey-login');if(login){login.hidden=!window.PublicKeyCredential;login.onclick=()=>execute(login,async()=>{const options=await post('/auth/webauthn/login/begin');options.challenge=decode(options.challenge);options.allowCredentials?.forEach(c=>c.id=decode(c.id));const credential=await navigator.credentials.get({publicKey:options});const result=await post('/auth/webauthn/login/finish',pack(credential));location.href=result.destino;});}
  document.querySelectorAll('.passkey-remove').forEach(button=>button.onclick=()=>{if(confirm('Remover esta passkey?'))execute(button,async()=>{await post(button.dataset.url,{senha:document.getElementById('senha-'+button.dataset.id).value});location.reload();});});
})();
