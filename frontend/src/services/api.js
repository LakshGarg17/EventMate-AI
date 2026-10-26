const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Checks backend health status and AI configuration.
 */
export async function checkHealth(timeoutMs = 5000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Health check returned status ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Health check request timed out');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Calls backend to generate event plan using Gemini AI or demo mode.
 */
export async function generateEventPlan(payload, timeoutMs = 45000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}/api/events/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      // Parse specific HTTP status error structures
      if (response.status === 422) {
        if (data && data.errors && Array.isArray(data.errors)) {
          const fieldMsgs = data.errors.map(e => `${e.field}: ${e.message}`).join(', ');
          throw new Error(`Validation Error: ${fieldMsgs}`);
        }
        throw new Error(data?.detail || 'Invalid event parameters submitted.');
      }

      if (response.status === 429) {
        throw new Error(data?.detail || 'AI quota limit reached. Please wait a moment and try again.');
      }

      if (response.status === 502) {
        throw new Error(data?.detail || 'Upstream AI service error. The model output could not be parsed.');
      }

      if (response.status === 504) {
        throw new Error('AI generation timed out. Please try again.');
      }

      throw new Error(data?.detail || `Server error (${response.status}). Please try again.`);
    }

    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The plan generation request timed out after 45 seconds. The server may be busy, please try again.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
