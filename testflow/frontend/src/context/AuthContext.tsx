import { createContext, useContext, useEffect, useState } from 'react'
import api from '../services/api'
import type { User } from '../types'
type Auth = { user:User|null; loading:boolean; login:(email:string,password:string)=>Promise<void>; logout:()=>void; refresh:()=>Promise<void> }
const AuthContext=createContext<Auth>(null!)
export const useAuth=()=>useContext(AuthContext)
export function AuthProvider({children}:{children:React.ReactNode}) { const [user,setUser]=useState<User|null>(null); const [loading,setLoading]=useState(true); const refresh=async()=>{try { const r=await api.get<User>('/auth/me/'); setUser(r.data)}catch{localStorage.clear();setUser(null)}finally{setLoading(false)}}; useEffect(()=>{refresh(); const h=()=>{setUser(null);setLoading(false)}; window.addEventListener('auth-expired',h);return()=>window.removeEventListener('auth-expired',h)},[]); const login=async(email:string,password:string)=>{const r=await api.post('/auth/login/',{username:email,password});localStorage.setItem('access',r.data.access);localStorage.setItem('refresh',r.data.refresh);await refresh()}; const logout=()=>{localStorage.clear();setUser(null)};return <AuthContext.Provider value={{user,loading,login,logout,refresh}}>{children}</AuthContext.Provider> }
