import axios from 'axios'
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api' })
api.interceptors.request.use(config => { const token = localStorage.getItem('access'); if (token) config.headers.Authorization = `Bearer ${token}`; return config })
api.interceptors.response.use(r => r, async error => { const request = error.config; if (error.response?.status === 401 && !request?._retried && localStorage.getItem('refresh')) { request._retried = true; try { const {data} = await axios.post(`${api.defaults.baseURL}/auth/refresh/`, {refresh:localStorage.getItem('refresh')}); localStorage.setItem('access',data.access); request.headers.Authorization=`Bearer ${data.access}`; return api(request) } catch { localStorage.clear(); window.dispatchEvent(new Event('auth-expired')) } } return Promise.reject(error) })
export const errorText = (e: unknown) => { const x:any=e; if (!x.response) return 'Network error. Check that the server is running.'; const data=x.response.data; return typeof data==='string'?data:Object.values(data).flat().join(' ') || `Request failed (${x.response.status}).` }
export default api
