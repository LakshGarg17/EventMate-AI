const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Normalizes HTTP and network error responses into user-friendly error messages.
 */
function normalizeError(status, data, defaultMsg = 'An error occurred') {
  if (status === 404) {
    return new Error(data?.detail || 'The requested resource was not found.');
  }

  if (status === 422) {
    if (data?.errors && Array.isArray(data.errors)) {
      const fieldMsgs = data.errors.map(e => `${e.field}: ${e.message}`).join(', ');
      return new Error(`Validation Error: ${fieldMsgs}`);
    }
    if (data?.detail && Array.isArray(data.detail)) {
      const fieldMsgs = data.detail.map(d => {
        const loc = Array.isArray(d.loc) ? d.loc.slice(1).join('.') : 'Field';
        return `${loc || 'field'}: ${d.msg}`;
      }).join(', ');
      return new Error(`Validation Error: ${fieldMsgs}`);
    }
    return new Error(data?.detail || 'Invalid parameters submitted.');
  }

  if (status === 429) {
    return new Error(data?.detail || 'Request quota limit reached. Please wait a moment and try again.');
  }

  if (status === 502) {
    return new Error(data?.detail || 'Upstream service error. Please try again.');
  }

  if (status === 504) {
    return new Error('Request timed out. Please try again.');
  }

  return new Error(data?.detail || `${defaultMsg} (${status}).`);
}

/**
 * Universal request wrapper with AbortController timeout and error normalization.
 */
async function apiRequest(path, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${API_BASE_URL}${path}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
      signal: controller.signal,
    });

    if (response.status === 204) {
      return null;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw normalizeError(response.status, data);
    }

    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`Request to ${path} timed out after ${timeoutMs / 1000} seconds.`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

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
  return await apiRequest('/api/events/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, timeoutMs);
}

// ==========================================
// Day 2 Persistent Event Management APIs
// ==========================================

export async function listEvents() {
  return await apiRequest('/api/events', { method: 'GET' });
}

export async function getEvent(eventId) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}`, { method: 'GET' });
}

export async function createEvent(payload) {
  return await apiRequest('/api/events', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateEvent(eventId, payload) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteEvent(eventId) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}`, {
    method: 'DELETE',
  });
}

// ==========================================
// Day 2 Expenses APIs
// ==========================================

export async function listExpenses(eventId) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/expenses`, { method: 'GET' });
}

export async function createExpense(eventId, payload) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/expenses`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateExpense(expenseId, payload) {
  return await apiRequest(`/api/expenses/${encodeURIComponent(expenseId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteExpense(expenseId) {
  return await apiRequest(`/api/expenses/${encodeURIComponent(expenseId)}`, {
    method: 'DELETE',
  });
}

// ==========================================
// Day 2 Tasks APIs
// ==========================================

export async function listTasks(eventId, statusFilter = null) {
  const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/tasks${query}`, { method: 'GET' });
}

export async function createTask(eventId, payload) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/tasks`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateTask(taskId, payload) {
  return await apiRequest(`/api/tasks/${encodeURIComponent(taskId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteTask(taskId) {
  return await apiRequest(`/api/tasks/${encodeURIComponent(taskId)}`, {
    method: 'DELETE',
  });
}
