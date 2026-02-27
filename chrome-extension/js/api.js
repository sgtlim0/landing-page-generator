const API_IMAGE_URL = 'https://sgtlim0--landing-page-generator-generate.modal.run';
const API_COPY_URL = 'https://sgtlim0--landing-page-generator-generate-copy.modal.run';
const API_TIMEOUT_MS = 10 * 60 * 1000;

const Api = {
  async generateImage(payload) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

    try {
      const resp = await fetch(API_IMAGE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`API Error ${resp.status}: ${text}`);
      }

      const contentType = resp.headers.get('content-type');
      if (contentType && contentType.includes('image/png')) {
        return { type: 'image', blob: await resp.blob() };
      }

      const data = await resp.json();
      if (data.error) {
        throw new Error(data.error);
      }
      return { type: 'json', data };
    } finally {
      clearTimeout(timeoutId);
    }
  },

  async generateCopy(payload) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

    try {
      const resp = await fetch(API_COPY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`API Error ${resp.status}: ${text}`);
      }

      const data = await resp.json();
      if (data.error) {
        throw new Error(data.error);
      }
      return data;
    } finally {
      clearTimeout(timeoutId);
    }
  },
};
