import { API_BASE_URL } from './apiConfig';

class ApiService {
  constructor() {
    this.apiUrl = API_BASE_URL;
  }

  async request(endpoint, method, data) {
    const url = `${this.apiUrl}${endpoint}`;
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    };

    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async sendMessage(philosopher, message) {
    try {
      const data = await this.request('/chat', 'POST', {
        message,
        character_id: philosopher.id
      });

      return data.response;
    } catch (error) {
      console.error('Error sending message to API:', error);
      return this.getFallbackResponse(philosopher);
    }
  }

  getFallbackResponse(philosopher) {
    return `I'm sorry, ${philosopher.name || 'the philosopher'} is unavailable at the moment. Please try again later.`;
  }

  async resetMemory() {
    try {
      const response = await fetch(`${this.apiUrl}/reset-memory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to reset memory');
      }

      return await response.json();
    } catch (error) {
      console.error('Error resetting memory:', error);
      throw error;
    }
  }
}

export default new ApiService();
