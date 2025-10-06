(function(){
  const statusEl = document.getElementById('status');
  const tbody = document.querySelector('#players tbody');
  const canvas = document.getElementById('map');
  const ctx = canvas.getContext('2d');

  let positions = {}; // name -> {x,y,z,ts}

  function setStatus(text) { statusEl.textContent = text; }
  function pretty(n, d=1){ return (Math.round(n*10**d)/10**d).toFixed(d); }

  function renderTable(){
    const now = Date.now()/1000;
    const names = Object.keys(positions).sort();
    tbody.innerHTML = '';
    for(const name of names){
      const p = positions[name];
      const age = Math.max(0, now - (p.ts || now));
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${name}</td><td>${pretty(p.x)}</td><td>${pretty(p.y)}</td><td>${pretty(p.z)}</td><td>${pretty(age)}</td>`;
      tbody.appendChild(tr);
    }
  }

  function renderMap(){
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== canvas.clientWidth * dpr) {
      canvas.width = canvas.clientWidth * dpr;
      canvas.height = canvas.clientHeight * dpr;
    }
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    ctx.clearRect(0,0,w,h);

    const margin = 40, plotW = Math.max(10, w-2*margin), plotH = Math.max(10, h-2*margin);
    ctx.strokeStyle = '#3a445a'; ctx.strokeRect(margin, margin, plotW, plotH);

    const names = Object.keys(positions);
    if(names.length === 0){
      ctx.fillStyle = '#cbd5e1'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText('En attente de données…', w/2, h/2);
      return;
    }
    const xs = names.map(n => positions[n].x);
    const zs = names.map(n => positions[n].z);
    let minX=Math.min(...xs), maxX=Math.max(...xs), minZ=Math.min(...zs), maxZ=Math.max(...zs);
    const padX = Math.max(5, (maxX-minX)*0.1), padZ = Math.max(5, (maxZ-minZ)*0.1);
    minX-=padX; maxX+=padX; minZ-=padZ; maxZ+=padZ;
    const spanX=Math.max(1e-6, maxX-minX), spanZ=Math.max(1e-6, maxZ-minZ);
    const mapX=x=> margin + (x-minX)/spanX*plotW;
    const mapZ=z=> margin + (maxZ-z)/spanZ*plotH;

    // grid
    ctx.strokeStyle = '#202838'; ctx.setLineDash([3,3]);
    ctx.beginPath();
    ctx.moveTo(margin+plotW/2, margin); ctx.lineTo(margin+plotW/2, margin+plotH);
    ctx.moveTo(margin, margin+plotH/2); ctx.lineTo(margin+plotW, margin+plotH/2);
    ctx.stroke(); ctx.setLineDash([]);

    // labels
    ctx.fillStyle='#9aa1af'; ctx.textAlign='center'; ctx.textBaseline='bottom';
    ctx.fillText('X (est/ouest)', margin+plotW/2, margin-8);
    ctx.save(); ctx.translate(margin-12, margin+plotH/2); ctx.rotate(-Math.PI/2);
    ctx.fillText('Z (nord/sud)', 0, 0); ctx.restore();

    // players
    const namesSorted = names.sort();
    for(const name of namesSorted){
      const p = positions[name];
      const cx = mapX(p.x), cz = mapZ(p.z), r=5;
      ctx.fillStyle = '#00d3ff';
      ctx.beginPath(); ctx.arc(cx, cz, r, 0, Math.PI*2); ctx.fill();
      ctx.fillStyle = '#e5e7eb'; ctx.textAlign='left'; ctx.textBaseline='middle';
      ctx.fillText(`${name} (${Math.round(p.x)},${Math.round(p.z)})`, cx+8, cz);
    }
  }

  function updateAll(){ renderTable(); renderMap(); }

  // SSE connect or fallback polling
  if ('EventSource' in window){
    const es = new EventSource('/stream');
    es.addEventListener('open', () => setStatus('Connecté (SSE).'));
    es.addEventListener('error', () => setStatus('SSE en erreur, tentative de reconnexion…'));
    es.addEventListener('positions', ev => {
      try { const obj = JSON.parse(ev.data); if (obj && obj.data) { positions = obj.data; updateAll(); } } catch(e){}
    });
  } else {
    setStatus('SSE non supporté, mode polling…');
    async function tick(){
      try { const res = await fetch('/api/positions', {cache:'no-store'}); positions = await res.json(); updateAll(); } catch(e){}
      setTimeout(tick, 3000);
    }
    tick();
  }

  window.addEventListener('resize', renderMap);
  updateAll();
})();