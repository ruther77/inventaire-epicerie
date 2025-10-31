import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchProducts = async () => {
  const { data } = await api.get('/products');
  return data;
};

export const fetchInventorySummary = async () => {
  const { data } = await api.get('/inventory/summary');
  return data;
};

export const checkoutCart = async (payload) => {
  const { data } = await api.post('/pos/checkout', payload);
  return data;
};

export default api;
