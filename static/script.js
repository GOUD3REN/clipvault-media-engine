let ffmpegOk = false;

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    checkStatus();
    setInterval(checkStatus, 1500);
    document.getElementById('process-btn').addEventListener('click', startProcess);
});

function parseNum(id, fallback) {
    const raw = (document.getElementById(id).value || '').trim().replace(/,/g, '.');
    const v = parseFloat(raw);
    return isNaN(v) ? fallback : v;
}

async function checkHealth() {
    const banner = document.getElementById('ffmpeg-banner');
    try {
        const res = await fetch('/api/health');
        if (!res.ok) {
            ffmpegOk = false;
            banner.className = 'banner error';
            banner.textContent =
                'FFMPEG ERROR: backend returned ' + res.status + ' on /api/health. ' +
                'Update src/main.py and restart the server (python run.py).';
            document.getElementById('process-btn').disabled = true;
            return;
        }
        const h = await res.json();
        if (h && h.ok) {
            ffmpegOk = true;
            banner.className = 'banner ok';
            banner.textContent = 'FFMPEG OK: ' + h.ffmpeg + '  |  ' + (h.version || '');
        } else {
            ffmpegOk = false;
            banner.className = 'banner error';
            banner.textContent = 'FFMPEG ERROR: ' + (h && h.error ? h.error : JSON.stringify(h));
        }
    } catch (e) {
        ffmpegOk = false;
        banner.className = 'banner error';
        banner.textContent = 'Cannot reach backend (/api/health). Is the server running?';
    }
    document.getElementById('process-btn').disabled = !ffmpegOk;
}

async function checkStatus() {
    try {
        const res = await fetch('/api/status');
        updateUI(await res.json());
    } catch (e) {}
}

function updateUI(data) {
    const badge = document.getElementById('status-badge');
    const processBtn = document.getElementById('process-btn');
    const jobPanel = document.getElementById('job-panel');

    if (!data || data.status === 'READY') {
        badge.className = 'badge ready'; badge.innerText = '● READY';
        processBtn.disabled = !ffmpegOk;
        processBtn.innerText = "PROCESS ALL";
        jobPanel.classList.add('hidden');
        return;
    }

    badge.className = 'badge ' + (data.status === 'PROCESSING' ? 'processing' : data.status.toLowerCase());
    badge.innerText = '● ' + data.status;
    processBtn.disabled = !ffmpegOk || data.status === 'PROCESSING';
    if (data.status === 'PROCESSING') processBtn.innerText = "PROCESSING...";

    jobPanel.classList.remove('hidden');
    const pct = data.total > 0 ? (data.completed / data.total) * 100 : 0;
    document.getElementById('progress-bar').style.width = pct + '%';
    document.getElementById('progress-text').innerText = data.completed + ' / ' + data.total + ' completed';

    const list = document.getElementById('task-list');
    list.innerHTML = '';
    (data.tasks || []).forEach(task => {
        const li = document.createElement('li');
        let statusClass = 'status-pending', statusText = 'PENDING';
        if (task.status === 'COMPLETED') { statusClass = 'status-completed'; statusText = '✓ ' + task.output_filename; }
        else if (task.status === 'FAILED') { statusClass = 'status-failed'; statusText = '✗ ' + task.filename + ' (' + (task.error || 'Error') + ')'; }
        else if (['ANALYZING', 'RENDERING', 'COMPOSITING'].includes(task.status)) { statusClass = 'status-processing'; statusText = '◌ Processing...'; }
        li.innerHTML = '<span>' + task.filename + '</span><span class="' + statusClass + '">' + statusText + '</span>';
        list.appendChild(li);
    });
}

async function startProcess() {
    if (!ffmpegOk) { alert("FFmpeg não está executável. Veja o banner vermelho no topo."); return; }
    const payload = {
        input_dir: document.getElementById('input-dir').value,
        image_path: document.getElementById('image-path').value,
        jumpscare_position_pct: parseNum('position', 50),
        jumpscare_duration: parseNum('duration', 0.5),
        output_width: parseInt(document.getElementById('width').value) || 1080,
        output_height: parseInt(document.getElementById('height').value) || 1920,
        output_naming_prefix: document.getElementById('naming').value,
        template_name: document.getElementById('template-select').value
    };
    try {
        const res = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) alert('Error: ' + (await res.json()).detail);
    } catch (e) { alert("Network error starting job."); }
}