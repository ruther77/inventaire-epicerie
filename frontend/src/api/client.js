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

export const fetchCategories = async () => {
  const { data } = await api.get('/categories');
  return data;
};

export const createCategory = async (payload) => {
  const { data } = await api.post('/categories', payload);
  return data;
};

export const updateCategory = async (categoryId, payload) => {
  const { data } = await api.patch(`/categories/${categoryId}`, payload);
  return data;
};

export const deleteCategory = async (categoryId) => {
  await api.delete(`/categories/${categoryId}`);
};

export const fetchClients = async () => {
  const { data } = await api.get('/clients');
  return data;
};

export const createClient = async (payload) => {
  const { data } = await api.post('/clients', payload);
  return data;
};

export const updateClient = async (clientId, payload) => {
  const { data } = await api.patch(`/clients/${clientId}`, payload);
  return data;
};

export const deleteClient = async (clientId) => {
  await api.delete(`/clients/${clientId}`);
};

export const fetchSuppliers = async () => {
  const { data } = await api.get('/suppliers');
  return data;
};

export const createSupplier = async (payload) => {
  const { data } = await api.post('/suppliers', payload);
  return data;
};

export const updateSupplier = async (supplierId, payload) => {
  const { data } = await api.patch(`/suppliers/${supplierId}`, payload);
  return data;
};

export const deleteSupplier = async (supplierId) => {
  await api.delete(`/suppliers/${supplierId}`);
};

export const fetchOrders = async () => {
  const { data } = await api.get('/orders');
  return data;
};

export const createOrder = async (payload) => {
  const { data } = await api.post('/orders', payload);
  return data;
};

export const updateOrder = async (orderId, payload) => {
  const { data } = await api.patch(`/orders/${orderId}`, payload);
  return data;
};

export const fetchProcurements = async () => {
  const { data } = await api.get('/procurements');
  return data;
};

export const createProcurement = async (payload) => {
  const { data } = await api.post('/procurements', payload);
  return data;
};

export const updateProcurement = async (procurementId, payload) => {
  const { data } = await api.patch(`/procurements/${procurementId}`, payload);
  return data;
};

export default api;
