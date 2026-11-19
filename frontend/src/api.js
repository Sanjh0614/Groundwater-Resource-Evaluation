const BASE = import.meta.env.VITE_API_URL || "";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`Server returned ${res.status}. Is the backend running?`);
  return res.json();
}

export const getDevices = () => get("/api/devices");
export const getDashboard = (deviceId, days) =>
  get(`/api/dashboard?device_id=${encodeURIComponent(deviceId)}&days=${days}`);
