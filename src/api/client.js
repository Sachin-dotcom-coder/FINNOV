export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5050';

export async function analyzeInvoices(files) {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));

  const res = await fetch(`${API_URL}/api/invoices/analyze`, {
    method: 'POST',
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Analyze failed: ${res.status} ${res.statusText} ${text}`);
  }
  return res.json();
}

export async function fetchInvoices() {
  const res = await fetch(`${API_URL}/api/invoices`);
  if (!res.ok) throw new Error('Failed to fetch invoices');
  return res.json();
}

export async function fetchInvoice(id) {
  const res = await fetch(`${API_URL}/api/invoices/${id}`);
  if (!res.ok) throw new Error('Failed to fetch invoice');
  return res.json();
}

export async function updateAnomaly(invoiceId, anomalyId, resolved) {
  const res = await fetch(`${API_URL}/api/invoices/${invoiceId}/anomalies/${anomalyId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resolved }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Update failed: ${res.status} ${res.statusText} ${text}`);
  }
  return res.json();
}
