// Keep requests in the tab/profile that initiated them. Fall back to the original
// request when that tab is gone or the content script cannot handle the request.
async function bewlySafariFetch(url, options, tabId) {
  if (Number.isInteger(tabId) && options.method.toUpperCase() === 'GET' &&
      options.credentials === 'include' && new URL(url).origin === 'https://api.bilibili.com') {
    try {
      options.signal?.throwIfAborted();
      const result = await new Promise((resolve, reject) => {
        const port = (globalThis.browser ?? globalThis.chrome).tabs.connect(tabId,
          { name: 'bewly:safari:authenticated-get', frameId: 0 });
        let settled = false;
        const finish = (value, error) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          options.signal?.removeEventListener('abort', abort);
          port.disconnect();
          error ? reject(error) : resolve(value);
        };
        const abort = () => finish(null, options.signal.reason);
        const timer = setTimeout(() => finish(null, new Error('Tab request timed out')), 13000);
        port.onMessage.addListener(value => finish(value));
        port.onDisconnect.addListener(() => finish(null, new Error('Tab disconnected')));
        options.signal?.addEventListener('abort', abort, { once: true });
        port.postMessage({ url });
      });
      options.signal?.throwIfAborted();
      if (result && !result.error && result.status >= 200 && result.status < 600) {
        return new Response(result.body, { status: result.status,
          headers: { 'content-type': result.contentType } });
      }
    } catch (error) { options.signal?.throwIfAborted(); }
  }
  return fetch(url, options);
}
