// Safari background fetches may omit website session cookies. Perform read-only
// Bilibili API requests in the originating tab, using its existing browser session.
// No cookie values are read, logged, or sent to a different origin.
(() => {
  const api = globalThis.browser ?? globalThis.chrome;
  if (window !== window.top || !location.hostname.endsWith('.bilibili.com')) return;
  api.runtime.onConnect.addListener((port) => {
    if (port.name !== 'bewly:safari:authenticated-get') return;
    if (port.sender?.id && port.sender.id !== api.runtime.id) return;
    port.onMessage.addListener((message) => {
    let url;
    try { url = new URL(message.url); } catch { return; }
    if (url.origin !== 'https://api.bilibili.com' || url.username || url.password) return;
    (async () => {
      const response = await fetch(url.href, {
        method: 'GET', credentials: 'include', mode: 'cors',
        signal: AbortSignal.timeout(12000),
      });
      return { status: response.status, body: await response.text(),
        contentType: response.headers.get('content-type') || 'application/json' };
    })().then(result => { try { port.postMessage(result); } catch {} },
      () => { try { port.postMessage({ error: 'Safari tab request failed' }); } catch {} });
    });
  });
})();
