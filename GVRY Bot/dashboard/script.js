// ════════════════════════════════════════════════════════════
// State & Init
// ════════════════════════════════════════════════════════════
let API_URL='', API_KEY='', configData={};
let currentTicket='general', currentEmbed='startup';
let sessionsData=[], citationsData=[], modData=[], econData=[], vehiclesData=[];
let statsInterval=null;

// Initialize
window.onload = loadSavedAuth;

// ════════════════════════════════════════════════════════════
// Navigation & UI
// ════════════════════════════════════════════════════════════
function showPage(name){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('#sidebar nav a').forEach(a=>a.classList.remove('active'));
    document.getElementById('page-'+name).classList.add('active');
    const link=document.querySelector('[data-page="'+name+'"]');
    if(link) link.classList.add('active');
    
    const map={
        sessions:loadSessions, 
        citations:loadCitations, 
        moderation:loadModeration, 
        economy:loadEconomy, 
        vehicles:loadVehicles, 
        overview:loadStats,
        guild:loadGuildData,
        logs:loadLogs
    };
    if(map[name]) map[name]();
    if(name==='embeds') refreshPreview();
}

function toast(msg,type='ok'){
    const c=document.getElementById('toast-container');
    const el=document.createElement('div');
    el.className='toast t-'+type;
    el.innerHTML=`<span>${type==='ok'?'✅':'⚠️'}</span><span>${msg}</span>`;
    c.appendChild(el);
    setTimeout(()=>el.remove(), 3000);
}

function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// ════════════════════════════════════════════════════════════
// Auth Logic
// ════════════════════════════════════════════════════════════
function loadSavedAuth(){
    API_URL=localStorage.getItem('gvry_url')||window.location.origin;
    API_KEY=localStorage.getItem('gvry_key')||'';
    if(API_URL&&API_KEY){
        document.getElementById('auth-url').value=API_URL;
        document.getElementById('auth-key').value=API_KEY;
        doConnect(true);
    }
}

async function doConnect(silent=false){
    API_URL=document.getElementById('auth-url').value.trim().replace(/\/$/,'');
    API_KEY=document.getElementById('auth-key').value.trim();
    const errEl=document.getElementById('auth-error');
    
    try {
        const resp = await fetch(API_URL+'/api/stats',{headers:{'Authorization':'Bearer '+API_KEY}});
        if(!resp.ok) throw new Error();
        
        localStorage.setItem('gvry_url',API_URL);
        localStorage.setItem('gvry_key',API_KEY);
        document.getElementById('auth-screen').style.display='none';
        document.getElementById('conn-dot').style.color='var(--green)';
        document.getElementById('conn-dot').textContent = '● Connected';
        loadStats(); loadConfig();
    } catch(e) {
        if(!silent) {
            errEl.style.display='block';
            errEl.textContent='Connection Failed. Check URL and Secret Key.';
        }
    }
}

function disconnect(){
    localStorage.clear();
    location.reload();
}

// ════════════════════════════════════════════════════════════
// NEW FEATURES: Logs & Guild Data
// ════════════════════════════════════════════════════════════
async function loadLogs(){
    const container = document.getElementById('log-container');
    try {
        const data = await apiGet('/api/logs');
        container.innerHTML = data.logs.map(l => `<div style="color:#0f0; margin-bottom:4px;">> ${esc(l)}</div>`).join('');
        container.scrollTop = container.scrollHeight;
    } catch(e) { container.innerHTML = "Failed to load logs."; }
}

async function loadGuildData(){
    try {
        const data = await apiGet('/api/guild/data');
        document.getElementById('g-name').textContent = data.name;
        document.getElementById('g-id').textContent = data.id;
        if(data.icon) document.getElementById('g-icon').src = data.icon;
        
        const tb = document.getElementById('roles-body');
        tb.innerHTML = data.roles.map(r => `
            <tr>
                <td style="color:${r.color==='0'?'#fff':r.color}">${esc(r.name)}</td>
                <td class="mono">${r.id}</td>
                <td>${r.members}</td>
            </tr>
        `).join('');
    } catch(e) { toast("Failed to load guild data", "err"); }
}

// ════════════════════════════════════════════════════════════
// Existing API & Stats logic (reorganized)
// ════════════════════════════════════════════════════════════
async function apiGet(p){
    const r=await fetch(API_URL+p,{headers:{'Authorization':'Bearer '+API_KEY}});
    return r.json();
}

async function apiPost(p,b){
    const r=await fetch(API_URL+p,{method:'POST',headers:{'Authorization':'Bearer '+API_KEY,'Content-Type':'application/json'},body:JSON.stringify(b)});
    return r.json();
}

function calcDur(start,end){
    try{const p=t=>{const[h,m]=(t||'').split(':').map(Number);return h*60+(m||0);};const s=p(start),e=p(end);if(isNaN(s)||isNaN(e)||!start||!end)return'—';let d=e-s;if(d<0)d+=1440;return Math.floor(d/60)+'h '+d%60+'m';}
    catch{return'—';}
}

async function loadStats(){
    try{
        const s=await apiGet('/api/stats');
        document.getElementById('s-cit-unpaid').textContent=s.citations_unpaid;
        document.getElementById('s-sessions').textContent=s.sessions_total;
        document.getElementById('s-mod').textContent=s.moderation_total;
        document.getElementById('s-econ').textContent=s.economy_users;
        document.getElementById('s-wallet').textContent='$'+Number(s.total_wallet).toLocaleString();
        document.getElementById('s-bank').textContent='$'+Number(s.total_bank).toLocaleString();
        document.getElementById('s-vehicles').textContent=s.vehicles_total;
        document.getElementById('s-latency').textContent=s.latency+'ms';
    }catch(e){}
}

// Configuration, Sessions, Citations, etc (Ported from old index.html)
async function loadConfig(){
    configData = await apiGet('/api/config');
    const b=configData.bot||{}, r=configData.roles||{}, ch=configData.channels||{};
    document.getElementById('cfg-prefix').value=b.prefix||'';
    document.getElementById('cfg-color').value=b.embed_color||'#c19beb';
    
    // Load Channels
    document.getElementById('cfg-ch-session').value=ch.session_commands_channel_id||'';
    document.getElementById('cfg-ch-session2').value=ch.session_commands_channel_id_2||'';
    document.getElementById('cfg-ch-money').value=ch.money_drop_channel_id||'';
    document.getElementById('cfg-ch-feedback').value=ch.feedback_Channel_id||'';
    document.getElementById('cfg-ch-citation').value=ch.citation_logs_channel_id||'';
    document.getElementById('cfg-ch-modlogs').value=ch.mod_logs_channel_id||'';
    document.getElementById('cfg-ch-cmdlogs').value=ch.command_logs_channel_id||'';
}

async function saveConfig(){
    configData.bot.prefix = document.getElementById('cfg-prefix').value;
    configData.bot.embed_color = document.getElementById('cfg-color').value;
    
    configData.channels.session_commands_channel_id = document.getElementById('cfg-ch-session').value;
    configData.channels.mod_logs_channel_id = document.getElementById('cfg-ch-modlogs').value;
    configData.channels.command_logs_channel_id = document.getElementById('cfg-ch-cmdlogs').value;

    await fetch(API_URL+'/api/config', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + API_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify(configData)
    });
    await apiPost('/api/config', configData);
    toast("Settings Saved!");
}

// Table Loading Helpers
async function loadSessions(){
    sessionsData = await apiGet('/api/sessions');
    const tb = document.getElementById('sessions-body');
    tb.innerHTML = sessionsData.map(s => `<tr><td class="mono">${s.id}</td><td>${s.user_id}</td><td>${s.session_type}</td><td>${s.session_date}</td><td><button class="btn btn-ghost btn-xs">✏️</button></td></tr>`).join('');
    tb.innerHTML = sessionsData.map(s => `<tr>
      <td class="mono">${s.id}</td>
      <td class="mono"><span class="trunc">${esc(s.user_id)}</span></td>
      <td><span class="badge ${s.session_type==='Host'?'b-purple':'b-yellow'}">${esc(s.session_type)}</span></td>
      <td>${esc(s.session_date)}</td>
      <td>${esc(s.start_time)}</td>
      <td>${esc(s.end_time)}</td>
      <td><span class="badge b-green">${calcDur(s.start_time,s.end_time)}</span></td>
      <td><span class="trunc">${esc(s.notes)}</span></td>
      <td><button class="btn btn-ghost btn-xs">✏️</button></td>
    </tr>`).join('');
}

async function loadCitations(){
    citationsData = await apiGet('/api/citations');
    const tb = document.getElementById('citations-body');
    tb.innerHTML = citationsData.map(c => `<tr><td class="mono">${c.id}</td><td>${c.user_id}</td><td>${c.reason}</td><td>$${c.price}</td><td><button class="btn btn-ghost btn-xs">✏️</button></td></tr>`).join('');
    tb.innerHTML = citationsData.map(c => `<tr>
      <td class="mono">${esc(c.id)}</td>
      <td class="mono">${esc(c.user_id)}</td>
      <td class="mono">${esc(c.officer_id)}</td>
      <td>${esc(c.department)}</td>
      <td>${esc(c.reason)}</td>
      <td class="mono">${esc(c.penal_code)}</td>
      <td class="money">$${Number(c.price).toLocaleString()}</td>
      <td><span class="badge ${c.status==='Paid'?'b-green':'b-red'}">${esc(c.status)}</span></td>
      <td><span class="trunc">${[c.vehicle_make,c.vehicle_plate].filter(Boolean).join(' ')}</span></td>
      <td><button class="btn btn-ghost btn-xs">✏️</button></td>
    </tr>`).join('');
}

async function loadModeration(){
    modData = await apiGet('/api/moderation');
    const tb = document.getElementById('mod-body');
    tb.innerHTML = modData.map(m => `<tr><td class="mono">${m.id}</td><td>${m.user_id}</td><td>${m.type}</td><td>${m.reason}</td><td><button class="btn btn-ghost btn-xs">✏️</button></td></tr>`).join('');
    tb.innerHTML = modData.map(m => `<tr>
      <td class="mono">${esc(m.id)}</td>
      <td class="mono">${esc(m.user_id)}</td>
      <td><span class="badge ${m.type==='ban'?'b-red':'b-purple'}">${esc(m.type)}</span></td>
      <td><span class="trunc">${esc(m.reason)}</span></td>
      <td><span class="trunc">${esc(m.proof)}</span></td>
      <td class="mono">${esc(m.moderator_id)}</td>
      <td>${esc(m.timestamp)}</td>
      <td><span class="badge ${m.cleared?'b-green':'b-red'}">${m.cleared?'Yes':'No'}</span></td>
      <td><button class="btn btn-ghost btn-xs">✏️</button></td>
    </tr>`).join('');
}

async function loadEconomy(){
    econData = await apiGet('/api/economy');
    const tb = document.getElementById('econ-body');
    tb.innerHTML = econData.map(e => `<tr><td class="mono">${e.user_id}</td><td>$${e.wallet}</td><td>$${e.bank}</td><td><button class="btn btn-ghost btn-xs">✏️</button></td></tr>`).join('');
    tb.innerHTML = econData.map(e => `<tr>
      <td class="mono">${esc(e.user_id)}</td>
      <td class="money">$${Number(e.wallet).toLocaleString()}</td>
      <td class="money">$${Number(e.bank).toLocaleString()}</td>
      <td class="money">$${Number(e.wallet + e.bank).toLocaleString()}</td>
      <td>${e.last_work || '—'}</td>
      <td>${e.last_crime || '—'}</td>
      <td><button class="btn btn-ghost btn-xs">✏️</button></td>
    </tr>`).join('');
}

async function loadVehicles(){
    vehiclesData = await apiGet('/api/vehicles');
    const tb = document.getElementById('veh-body');
    tb.innerHTML = vehiclesData.map(v => `<tr><td class="mono">${v.id}</td><td>${v.user_id}</td><td>${v.make} ${v.model}</td><td>${v.plate}</td><td><button class="btn btn-ghost btn-xs">✏️</button></td></tr>`).join('');
    tb.innerHTML = vehiclesData.map(v => `<tr>
      <td class="mono">${v.id}</td>
      <td class="mono">${esc(v.user_id)}</td>
      <td>${esc(v.year)}</td>
      <td>${esc(v.make)}</td>
      <td>${esc(v.model)}</td>
      <td>${esc(v.color)}</td>
      <td><span class="badge b-blue">${esc(v.plate)}</span></td>
      <td><button class="btn btn-ghost btn-xs">✏️</button></td>
    </tr>`).join('');
}