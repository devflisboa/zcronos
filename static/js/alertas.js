(() => {const config=document.getElementById('push-config'),status=document.getElementById('push-status');
async function post(url,data){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(data)});if(!r.ok)throw new Error('Não foi possível salvar as notificações.');}
document.getElementById('ativar-push').onclick=async e=>{e.target.disabled=true;try{if(!('serviceWorker' in navigator)||!('PushManager' in window))throw new Error('Este navegador não oferece push.');
if(await Notification.requestPermission()!=='granted')throw new Error('Permissão de notificações não concedida.');
const key=config.dataset.vapid,padding='='.repeat((4-key.length%4)%4),bytes=Uint8Array.from(atob((key+padding).replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
const registration=await navigator.serviceWorker.ready;const sub=await registration.pushManager.getSubscription()||await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:bytes});await post(config.dataset.url,sub.toJSON());status.textContent='Notificações ativadas.';
}catch(err){status.textContent=err.message;}finally{e.target.disabled=false;}};
document.getElementById('desativar-push').onclick=async()=>{try{const registration=await navigator.serviceWorker.ready,sub=await registration.pushManager.getSubscription();if(sub){await post(config.dataset.remove,{endpoint:sub.endpoint});await sub.unsubscribe();}status.textContent='Notificações desativadas neste dispositivo.';}catch(err){status.textContent=err.message;}};
})();
