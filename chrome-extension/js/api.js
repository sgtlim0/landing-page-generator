const API_BASE_URL = 'https://sgtlim0--copywriter-generator';
const API_DEEP_RESEARCH_URL = `${API_BASE_URL}-deep-research.modal.run`;
const API_TIMEOUT_MS = 10 * 60 * 1000;

const Api = {
  async deepResearch(payload) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

    try {
      const resp = await fetch(API_DEEP_RESEARCH_URL, {
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
