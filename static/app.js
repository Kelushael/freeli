// PEEPEESEE Frontend Logic
let modelsCache = [];
let activeModel = null;
let currentAgentId = "user_" + Math.floor(Math.random() * 1000);

// --- NAVIGATION ---
function showSection(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));
    
    document.getElementById(id).classList.add('active');
    // Find nav link corresponding to section (simple approach)
    const links = document.querySelectorAll('.nav-links li');
    if(id === 'dashboard') links[0].classList.add('active');
    if(id === 'hybridizer') links[1].classList.add('active');
    if(id === 'chat') links[2].classList.add('active');
    if(id === 'tools') links[3].classList.add('active');
}

// --- DATA FETCHING ---
async function fetchStatus() {
    try {
        const res = await fetch('/');
        const data = await res.json();
        
        activeModel = data.active_model;
        modelsCache = data.available_models;

        // Update Dashboard
        document.getElementById('active-model').innerText = activeModel || 'None';
        document.getElementById('hybrid-status').innerText = data.dashboard.hybridizer_status;
        document.getElementById('hybrid-progress').style.width = data.dashboard.hybridization_percent;
        
        // Update Model List (Dashboard)
        const list = document.getElementById('model-list');
        list.innerHTML = '';
        modelsCache.forEach(m => {
            const li = document.createElement('li');
            li.innerText = m;
            if(m === activeModel) li.classList.add('active');
            li.onclick = () => loadModel(m);
            list.appendChild(li);
        });

        // Update Quick List (Hybridizer)
        const quickList = document.getElementById('quick-model-list');
        quickList.innerHTML = '';
        modelsCache.forEach(m => {
            const chip = document.createElement('div');
            chip.className = 'chip';
            chip.innerText = m;
            chip.onclick = () => fillLobe(m);
            quickList.appendChild(chip);
        });

        document.getElementById('system-status-text').innerText = "SYSTEM ONLINE";
        document.getElementById('system-status-dot').style.background = "#00ff41";
    } catch (e) {
        console.error(e);
        document.getElementById('system-status-text').innerText = "OFFLINE";
        document.getElementById('system-status-dot').style.background = "#ff0000";
    }
}

// --- ACTIONS ---
async function loadModel(model) {
    if(!confirm(`Switch active host to ${model}?`)) return;
    addMessage('system', `Switching to host: ${model}...`);
    await fetch('/v1/models/load', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({model: model})
    });
    fetchStatus();
}

// Hybridizer Logic
let lastLobe = 'a'; // alternate filling
function fillLobe(model) {
    if(lastLobe === 'a') {
        document.getElementById('model-a').value = model;
        lastLobe = 'b';
    } else {
        document.getElementById('model-b').value = model;
        lastLobe = 'a';
    }
}

async function engageHybrid() {
    const mA = document.getElementById('model-a').value;
    const mB = document.getElementById('model-b').value;
    
    if(!mA && !mB) return alert('Select at least one model for the lobes.');
    
    const models = [];
    if(mA) models.push(mA);
    if(mB) models.push(mB);

    addMessage('system', `Initiating Hybrid Sequence: ${models.join(' + ')}`);
    
    await fetch('/v1/hybridize/configure', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({models: models})
    });
    
    // Switch to Dashboard to show progress
    showSection('dashboard');
    fetchStatus();
}

// Chat Logic
function handleChatKey(e) {
    if(e.key === 'Enter') sendChat();
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value;
    if(!msg) return;
    
    addMessage('user', msg);
    input.value = '';

    // If first message, ensure agent exists
    // (For simplicity, we assume agent registry is open or auto-creates)
    // We'll use the existing /v1/agents/chat endpoint but first ensure agent exists
    // Actually, let's just create it on page load? No, lazy create.
    
    try {
        // Ensure agent exists (idempotent-ish in our backend logic hopefully, or we just try chat and fail)
        // Let's just create it every session start for now
        if(!window.agentCreated) {
            await fetch('/v1/agents/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: currentAgentId, model: "active_hybrid"})
            });
            window.agentCreated = true;
        }

        const res = await fetch('/v1/agents/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({agent_id: currentAgentId, message: msg})
        });
        
        const data = await res.json();
        addMessage('ai', data.response);
    } catch(e) {
        addMessage('system', `Error: ${e}`);
    }
}

function addMessage(role, text) {
    const history = document.getElementById('chat-history');
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerText = `${role.toUpperCase()}: ${text}`;
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
}

// Tools Logic
async function fetchTools() {
    const res = await fetch('/v1/tools');
    const data = await res.json();
    const list = document.getElementById('tools-list');
    list.innerHTML = '';
    
    if(data.tools) {
        data.tools.forEach(t => {
            const item = document.createElement('div');
            item.className = 'tool-item';
            item.innerHTML = `<div class="tool-name">${t.name}</div><div class="tool-desc">${t.description}</div>`;
            list.appendChild(item);
        });
    }
}

async function addTool() {
    const name = document.getElementById('tool-name').value;
    const desc = document.getElementById('tool-desc').value;
    if(!name || !desc) return alert('Details required');

    await fetch('/v1/tools/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, description: desc})
    });
    
    fetchTools();
    document.getElementById('tool-name').value = '';
    document.getElementById('tool-desc').value = '';
}

// Init
setInterval(fetchStatus, 3000);
fetchStatus();
fetchTools();
