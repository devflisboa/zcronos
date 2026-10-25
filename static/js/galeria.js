(() => {
  const grid = document.getElementById('foto-grid'), status = document.getElementById('galeria-status');
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const items = () => [...grid.querySelectorAll('.foto-item')];
  async function send(url,data,raw=false) {
    const headers = {'X-CSRFToken':csrf}; if(!raw) headers['Content-Type']='application/json';
    const response=await fetch(url,{method:'POST',headers,body:raw?data:JSON.stringify(data)});
    let result; try {result=await response.json();}catch(e){throw new Error('Falha na operação. Tente novamente.');}
    if(!response.ok) throw new Error(result.erro || 'Não foi possível concluir.'); return result;
  }
  async function action(button, fn) {button.disabled=true;status.textContent='Processando…';try{await fn();status.textContent='Alteração salva.';}catch(e){status.textContent=e.message;}finally{button.disabled=false;}}
  document.getElementById('foto-upload').addEventListener('submit',e=>{e.preventDefault();const form=e.target,button=form.querySelector('button');action(button,async()=>{
    const files=[...document.getElementById('fotos').files]; if(!files.length || files.length>20) throw new Error('Selecione até 20 fotos.');
    const data=new FormData();
    for(const file of files){
      if(file.size>10*1024*1024)throw new Error('Cada foto deve ter até 10 MB.');
      if(['image/jpeg','image/png'].includes(file.type)){
        const bitmap=await createImageBitmap(file).catch(()=>{throw new Error('Não foi possível ler esta foto. Selecione uma imagem válida.');}), canvas=document.createElement('canvas');const scale=Math.min(1,1920/Math.max(bitmap.width,bitmap.height));
        canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d').drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
        const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.85));if(!blob)throw new Error('Não foi possível preparar a foto.');data.append('fotos',blob,'foto.jpg');
      }else data.append('fotos',file);
    }
    await send(form.dataset.url,data,true);location.reload();
  });});
  const dialog=document.getElementById('foto-lightbox'), expanded=document.getElementById('foto-ampliada');let current=0;
  function show(index){const list=items();if(!list.length)return;current=(index+list.length)%list.length;expanded.src=list[current].dataset.url;expanded.alt=list[current].querySelector('.foto-legenda').value || 'Foto do veículo';}
  document.getElementById('foto-fechar').onclick=()=>dialog.close();document.getElementById('foto-anterior').onclick=()=>show(current-1);document.getElementById('foto-proxima').onclick=()=>show(current+1);
  let touch=0;expanded.addEventListener('touchstart',e=>{touch=e.changedTouches[0].clientX;},{passive:true});expanded.addEventListener('touchend',e=>{const delta=e.changedTouches[0].clientX-touch;if(Math.abs(delta)>40)show(current+(delta<0?1:-1));},{passive:true});
  async function saveOrder(){await send(grid.dataset.ordemUrl,{ordem:items().map(i=>Number(i.dataset.id))});}
  let dragging=null;
  items().forEach(item=>{
    item.querySelector('.foto-abrir').onclick=()=>{show(items().indexOf(item));dialog.showModal();};
    item.querySelector('.foto-salvar').onclick=e=>action(e.target,()=>send(item.dataset.update,{legenda:item.querySelector('.foto-legenda').value}));
    item.querySelector('.foto-remover').onclick=e=>{if(confirm('Remover esta foto permanentemente?'))action(e.target,async()=>{await send(item.dataset.remove,{});location.reload();});};
    item.querySelector('.foto-capa').onclick=e=>action(e.target,async()=>{const before=items();grid.prepend(item);try{await saveOrder();location.reload();}catch(error){before.forEach(node=>grid.append(node));throw error;}});
    item.addEventListener('dragstart',()=>{dragging=item;});item.addEventListener('dragover',e=>e.preventDefault());
    item.addEventListener('drop',e=>{e.preventDefault();if(dragging&&dragging!==item){const before=items();grid.insertBefore(dragging,item);saveOrder().then(()=>location.reload()).catch(err=>{before.forEach(node=>grid.append(node));status.textContent=err.message;});}});
    item.querySelector('.foto-compartilhar').onclick=e=>action(e.target,async()=>{
      const wide=confirm('Usar formato horizontal (1200×630)? Cancelar usa quadrado (1080×1080).');
      const canvas=document.createElement('canvas');canvas.width=wide?1200:1080;canvas.height=wide?630:1080;
      const ctx=canvas.getContext('2d'), image=new Image();image.src=item.dataset.url;await image.decode();
      const scale=Math.max(canvas.width/image.width,canvas.height/image.height);ctx.drawImage(image,(canvas.width-image.width*scale)/2,(canvas.height-image.height*scale)/2,image.width*scale,image.height*scale);
      const grad=ctx.createLinearGradient(0,canvas.height-260,0,canvas.height);grad.addColorStop(0,'transparent');grad.addColorStop(1,'rgba(0,0,0,.95)');ctx.fillStyle=grad;ctx.fillRect(0,canvas.height-260,canvas.width,260);
      ctx.strokeStyle='#D4AF37';ctx.lineWidth=10;ctx.strokeRect(5,5,canvas.width-10,canvas.height-10);const data=document.getElementById('galeria-dados').dataset;
      ctx.fillStyle='#fff';ctx.font='bold 36px sans-serif';ctx.fillText(data.nome,40,canvas.height-130,canvas.width-80);
      ctx.font='28px sans-serif';ctx.fillText(Number(data.km).toLocaleString('pt-BR')+' km · R$ '+Number(data.custo||0).toFixed(2).replace('.',',')+'/km',40,canvas.height-85);
      ctx.font='22px sans-serif';ctx.fillText('Consumo: '+Number(data.consumo||0).toFixed(1).replace('.',',')+' km/L',40,canvas.height-45);ctx.fillStyle='#D4AF37';ctx.textAlign='right';ctx.fillText('ΛUTOVIU',canvas.width-40,canvas.height-45);
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.92)), file=new File([blob],'autoviu.jpg',{type:'image/jpeg'});
      if(navigator.canShare&&navigator.canShare({files:[file]})){try{await navigator.share({files:[file],title:data.nome});}catch(err){if(err.name!=='AbortError')throw err;}}
      else {const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='autoviu.jpg';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    });
  });
})();
