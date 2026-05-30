/* ─── Upload Page ─────────────────────────────────────────────── */

let fileQueue = [];

const dropZone   = document.getElementById('dropZone');
const fileInput  = document.getElementById('fileInput');
const queueEl    = document.getElementById('fileQueue');
const queueList  = document.getElementById('queueList');
const queueCount = document.getElementById('queueCount');

// ── Drag & Drop ───────────────────────────────────────────────────
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  addFiles([...e.dataTransfer.files]);
});
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => addFiles([...fileInput.files]));

// ── Queue management ──────────────────────────────────────────────
function addFiles(files) {
  const allowed = ['image/jpeg','image/png','image/webp','image/gif',
                   'video/mp4','video/quicktime','video/webm','video/avi'];
  const MAX = 200 * 1024 * 1024;

  files.forEach(f => {
    if (!allowed.includes(f.type) && !f.name.match(/\.(jpg|jpeg|png|webp|gif|mp4|mov|webm|avi)$/i)) {
      showToast(`${f.name}: unsupported format`); return;
    }
    if (f.size > MAX) { showToast(`${f.name}: file too large (max 200 MB)`); return; }
    if (fileQueue.find(q => q.file.name === f.name && q.file.size === f.size)) return;
    fileQueue.push({ file: f, id: Date.now() + Math.random(), status: 'pending' });
  });

  renderQueue();
  fileInput.value = '';
}

function renderQueue() {
  if (!fileQueue.length) {
    queueEl.style.display = 'none';
    return;
  }
  queueEl.style.display = 'block';
  const pending = fileQueue.filter(q => q.status === 'pending');
  queueCount.textContent = `${fileQueue.length} file${fileQueue.length !== 1 ? 's' : ''} selected`;

  queueList.innerHTML = '';
  fileQueue.forEach(item => {
    const li = document.createElement('li');
    li.className = `queue-item${item.status === 'done' ? ' done' : item.status === 'error' ? ' error' : ''}`;
    li.id = `qi-${item.id}`;

    const isVideo = item.file.type.startsWith('video');
    const thumbHtml = isVideo
      ? `<div class="queue-thumb-video">🎥</div>`
      : `<img class="queue-thumb" src="${URL.createObjectURL(item.file)}" alt=""/>`;

    let statusText = '';
    if (item.status === 'uploading') statusText = `<div class="queue-status uploading">Uploading… ${item.progress || 0}%</div>`;
    else if (item.status === 'done')  statusText = `<div class="queue-status done">✓ Uploaded</div>`;
    else if (item.status === 'error') statusText = `<div class="queue-status error">✗ Failed</div>`;

    li.innerHTML = `
      ${thumbHtml}
      <div class="queue-info">
        <div class="queue-name">${escHtml(item.file.name)}</div>
        <div class="queue-meta">${WeddingUtils.formatSize(item.file.size)}</div>
        ${statusText}
      </div>
      ${item.status === 'pending'
        ? `<button class="queue-remove" onclick="removeFile('${item.id}')" title="Remove">✕</button>`
        : ''}
    `;
    queueList.appendChild(li);
  });

  // Upload button
  const uploadAllBtn = document.getElementById('uploadAllBtn');
  uploadAllBtn.style.display = pending.length ? 'block' : 'none';
  uploadAllBtn.textContent = `Upload ${pending.length} Memor${pending.length !== 1 ? 'ies' : 'y'} ✦`;
}

function removeFile(id) {
  fileQueue = fileQueue.filter(q => String(q.id) !== id);
  renderQueue();
}

function clearQueue() {
  fileQueue = fileQueue.filter(q => q.status !== 'pending');
  if (!fileQueue.length) {
    queueEl.style.display = 'none';
  } else {
    renderQueue();
  }
}

// ── Upload all ────────────────────────────────────────────────────
async function uploadAll() {
  const pending = fileQueue.filter(q => q.status === 'pending');
  if (!pending.length) return;

  const overallProg = document.getElementById('overallProgress');
  const overallFill = document.getElementById('overallFill');
  const overallLabel = document.getElementById('overallLabel');
  overallProg.style.display = 'block';
  document.getElementById('uploadAllBtn').disabled = true;

  let done = 0, failed = 0;

  for (let i = 0; i < pending.length; i++) {
    const item = pending[i];
    item.status = 'uploading';
    item.progress = 0;
    renderQueue();
    overallLabel.textContent = `Uploading ${i + 1} of ${pending.length}…`;

    try {
      await WeddingUtils.uploadFile(item.file, pct => {
        item.progress = pct;
        const li = document.getElementById(`qi-${item.id}`);
        if (li) {
          const s = li.querySelector('.queue-status');
          if (s) s.textContent = `Uploading… ${pct}%`;
        }
      });
      item.status = 'done';
      done++;
    } catch {
      item.status = 'error';
      failed++;
    }
    renderQueue();
    overallFill.style.width = `${Math.round((i + 1) / pending.length * 100)}%`;
  }

  overallProg.style.display = 'none';

  // Show success
  document.getElementById('batchSuccess').style.display = 'block';
  document.getElementById('successCount').textContent =
    `${done} file${done !== 1 ? 's' : ''} uploaded successfully${failed ? ` · ${failed} failed` : ''}.`;
  queueEl.style.display = 'none';
  dropZone.style.display = 'none';
}

// ── Utils ─────────────────────────────────────────────────────────
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showToast(msg) {
  const t = document.createElement('div');
  t.style.cssText = `
    position:fixed;bottom:24px;left:50%;transform:translateX(-50%);
    background:#2a2118;color:#fff;padding:10px 20px;border-radius:50px;
    font-size:.8rem;z-index:9000;animation:fadeUp .3s ease;
    max-width:90vw;text-align:center;
  `;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
