// ── PWA Service Worker registration ──────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}

// ── Shared utilities ──────────────────────────────────────────────────────────
window.WeddingUtils = {
  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  },

  formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  },

  async uploadFile(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fd  = new FormData();
      fd.append('files', file);

      xhr.open('POST', '/api/upload');
      xhr.upload.onprogress = e => {
        if (e.lengthComputable) onProgress(Math.round(e.loaded / e.total * 100));
      };
      xhr.onload = () => {
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status === 200) resolve(data);
          else reject(new Error(data.error || 'Upload failed'));
        } catch { reject(new Error('Invalid response')); }
      };
      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(fd);
    });
  }
};

// ── Add-to-home-screen nudge ──────────────────────────────────────────────────
let deferredPrompt;
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredPrompt = e;
});
