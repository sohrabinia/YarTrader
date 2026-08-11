// Vercel Serverless Proxy function for YarTrader
// Dynamically routes all requests to BACKEND_API_URL environment variable

export default async function handler(req, res) {
  // Disable caching for API proxying
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');

  const backendUrl = process.env.BACKEND_API_URL;
  if (!backendUrl) {
    return res.status(502).json({
      detail: "Backend Unreachable: BACKEND_API_URL environment variable is not configured on Vercel."
    });
  }

  // Parse original request URL
  const parsedUrl = new URL(req.url, 'http://localhost');
  const pathParam = parsedUrl.searchParams.get('path') || '';

  // Remove the 'path' param which is only used for Vercel mapping
  parsedUrl.searchParams.delete('path');

  // Reconstruct target URL
  const cleanBackend = backendUrl.endsWith('/') ? backendUrl.slice(0, -1) : backendUrl;
  const separator = pathParam.startsWith('/') ? '' : '/';
  const targetQuery = parsedUrl.search; // includes "?" and other query parameters
  const targetUrl = `${cleanBackend}${separator}${pathParam}${targetQuery}`;

  // Filter and prepare headers to forward
  const headers = {};
  for (const [key, val] of Object.entries(req.headers)) {
    if (key.toLowerCase() !== 'host') {
      headers[key] = val;
    }
  }

  try {
    // Read request body if present
    let body = undefined;
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      if (typeof req.body === 'object') {
        body = JSON.stringify(req.body);
      } else {
        body = req.body;
      }
    }

    const response = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      redirect: 'manual'
    });

    // Forward response status & headers
    res.status(response.status);
    for (const [key, val] of response.headers.entries()) {
      res.setHeader(key, val);
    }

    const responseText = await response.text();
    return res.send(responseText);
  } catch (error) {
    return res.status(502).json({
      detail: `Backend Unreachable: Failed to establish real backend connection to ${targetUrl}. Error: ${error.message}`
    });
  }
}
