import { API_BASE_URL } from './config';

/**
 * Normalizes HTTP and network error responses into user-friendly error messages.
 */
function normalizeError(status, data, responseHeaders = null, defaultMsg = 'An error occurred') {
  let err;
  if (status === 404) {
    err = new Error(data?.detail || 'The requested resource was not found.');
  } else if (status === 409) {
    err = new Error(data?.detail || 'Conflict error: resource state has changed.');
    err.reason = data?.detail || 'Conflict';
  } else if (status === 422) {
    if (data?.errors && Array.isArray(data.errors)) {
      const fieldMsgs = data.errors.map(e => `${e.field}: ${e.message}`).join(', ');
      err = new Error(`Validation Error: ${fieldMsgs}`);
    } else if (data?.detail && Array.isArray(data.detail)) {
      const fieldMsgs = data.detail.map(d => {
        const loc = Array.isArray(d.loc) ? d.loc.slice(1).join('.') : 'Field';
        return `${loc || 'field'}: ${d.msg}`;
      }).join(', ');
      err = new Error(`Validation Error: ${fieldMsgs}`);
    } else {
      err = new Error(data?.detail || 'Invalid parameters submitted.');
    }
  } else if (status === 429) {
    const retryAfter = responseHeaders?.get?.('retry-after') || data?.retry_after || 60;
    err = new Error(`Too many AI requests. Try again in ${retryAfter} seconds.`);
  } else if (status === 502) {
    err = new Error(data?.detail || 'Upstream service error. Please try again.');
  } else if (status === 503) {
    err = new Error(data?.detail || 'Service currently unavailable. Please try again later.');
  } else if (status === 504) {
    err = new Error('Request timed out. Please try again.');
  } else {
    err = new Error(data?.detail || `${defaultMsg} (${status}).`);
  }

  err.status = status;
  err.data = data;
  return err;
}

/**
 * Universal request wrapper with AbortController timeout, slow-start retry on GET,
 * and error normalization.
 */
async function apiRequest(path, options = {}, timeoutMs = 15000, isRetry = false) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${API_BASE_URL}${path}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  const method = (options.method || 'GET').toUpperCase();

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
      throw normalizeError(response.status, data, response.headers);
    }

    return data;
  } catch (error) {
    // Slow-start retry for GET requests on free hosting (Render/Cold starts)
    if (method === 'GET' && !isRetry && (error.name === 'AbortError' || error.name === 'TypeError')) {
      clearTimeout(timeoutId);
      await new Promise(r => setTimeout(r, 3000));
      try {
        return await apiRequest(path, options, timeoutMs, true);
      } catch (retryErr) {
        throw new Error('The server may be waking up. Please try again in a moment.');
      }
    }

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
export async function generateEventPlan(payload, timeoutMs = 65000) {
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

// ==========================================
// Day 3 Assistant & Plan Modification APIs
// ==========================================

export async function askAssistant(eventId, payload, timeoutMs = 65000) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/assistant`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, timeoutMs);
}

export async function proposeChanges(eventId, payload, timeoutMs = 65000) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/assistant/propose-changes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, timeoutMs);
}

export async function applyChanges(eventId, payload, timeoutMs = 25000) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/assistant/apply-changes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }, timeoutMs);
}

export async function discardProposal(eventId, proposalId, timeoutMs = 15000) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/assistant/proposals/${encodeURIComponent(proposalId)}/discard`, {
    method: 'POST',
  }, timeoutMs);
}

// ==========================================
// Day 3 Theme & Creative Recommendation APIs
// ==========================================

export async function recommendThemes(payload, timeoutMs = 65000) {
  return await apiRequest('/api/themes/recommend', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, timeoutMs);
}

// ==========================================
// Day 3 Invitation Generator APIs
// ==========================================

export async function generateInvitation(payload, timeoutMs = 65000) {
  return await apiRequest('/api/invitations/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, timeoutMs);
}

// ==========================================
// Day 3 Vendor Management & Quotation APIs
// ==========================================

export async function listVendors(eventId, categoryFilter = null, statusFilter = null) {
  const params = new URLSearchParams();
  if (categoryFilter) params.append('category', categoryFilter);
  if (statusFilter) params.append('status', statusFilter);
  const queryStr = params.toString() ? `?${params.toString()}` : '';
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/vendors${queryStr}`, {
    method: 'GET',
  });
}

export async function createVendor(eventId, payload) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/vendors`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateVendor(vendorId, payload) {
  return await apiRequest(`/api/vendors/${encodeURIComponent(vendorId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteVendor(vendorId) {
  return await apiRequest(`/api/vendors/${encodeURIComponent(vendorId)}`, {
    method: 'DELETE',
  });
}

export async function getVendorComparison(eventId) {
  return await apiRequest(`/api/events/${encodeURIComponent(eventId)}/vendors/comparison`, {
    method: 'GET',
  });
}
