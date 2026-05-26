// Magpie ↔ Python bridge over QWebChannel.
// Exposes window.magpie with promise-based wrappers and a tiny event hub.
(function () {
  const listeners = {};
  const hub = {
    on(event, fn) {
      (listeners[event] = listeners[event] || []).push(fn);
      return () => { listeners[event] = (listeners[event] || []).filter(f => f !== fn); };
    },
    emit(event, payload) {
      (listeners[event] || []).slice().forEach(fn => {
        try { fn(payload); } catch (err) { console.error('[magpie hub]', err); }
      });
    }
  };

  const promise = new Promise((resolve, reject) => {
    if (typeof QWebChannel === 'undefined') {
      reject(new Error('QWebChannel not available — bridge.js loaded outside QtWebEngine?'));
      return;
    }
    new QWebChannel(qt.webChannelTransport, (channel) => {
      const api = channel.objects.magpieApi;
      if (!api) { reject(new Error('magpieApi not registered on channel')); return; }

      // Wrap each slot to return a Promise. Slots return JSON strings to keep
      // QVariant marshalling deterministic across types (lists, nested dicts).
      const wrap = (name) => (...args) => new Promise((res, rej) => {
        try {
          api[name](...args, (raw) => {
            if (raw === undefined || raw === null) { res(null); return; }
            try { res(typeof raw === 'string' ? JSON.parse(raw) : raw); }
            catch (e) { rej(e); }
          });
        } catch (err) { rej(err); }
      });

      const slots = [
        'getInitialState', 'pickFolder', 'pickFile', 'loadImageFolder',
        'confirmRecursive', 'getImageData', 'classifyImage', 'undo', 'redo',
        'getPreferences', 'savePreferences', 'clearRecord', 'copyToClipboard',
        'addRecentFolder', 'saveAppState', 'showAbout', 'showShortcuts',
      ];
      const wrapped = {};
      slots.forEach(name => { if (typeof api[name] === 'function') wrapped[name] = wrap(name); });

      api.toast.connect((msg, color) => hub.emit('toast', { msg, color }));
      api.preferencesChanged.connect((data) => {
        try { hub.emit('preferences', JSON.parse(data)); } catch (e) { console.error(e); }
      });

      resolve({ ...wrapped, on: hub.on });
    });
  });

  window.magpieReady = promise;
})();
