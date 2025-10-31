import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token ?? null;
  if (authToken) {
    api.defaults.headers.common.Authorization = `Bearer ${authToken}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

export const clearAuthToken = () => {
  authToken = null;
  delete api.defaults.headers.common.Authorization;
};

api.interceptors.request.use((config) => {
  // eslint-disable-next-line no-param-reassign
  config.headers = config.headers ?? {};
  if (authToken && !config.headers.Authorization) {
    // eslint-disable-next-line no-param-reassign
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

export const loginUser = async (payload) => {
  const { data } = await api.post('/auth/login', payload);
  return data;
};

export const fetchCurrentUser = async () => {
  const { data } = await api.get('/users/me');
  return data;
};

export const fetchUsers = async () => {
  const { data } = await api.get('/users');
  return data;
};

export const createUserAccount = async (payload) => {
  const { data } = await api.post('/users', payload);
  return data;
};

export const updateUserAccount = async (userId, payload) => {
  const { data } = await api.patch(`/users/${userId}`, payload);
  return data;
};

export const deleteUserAccount = async (userId) => {
  await api.delete(`/users/${userId}`);
};

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
