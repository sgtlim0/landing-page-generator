const Storage = {
  async saveCredentials(credentials) {
    return chrome.storage.local.set({ aws_credentials: credentials });
  },

  async loadCredentials() {
    const result = await chrome.storage.local.get('aws_credentials');
    return result.aws_credentials || null;
  },

  async clearCredentials() {
    return chrome.storage.local.remove('aws_credentials');
  },
};
