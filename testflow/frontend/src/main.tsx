import React from 'react'
import ReactDOM from 'react-dom/client'
import {BrowserRouter, Navigate, Route, Routes, Outlet, useLocation} from 'react-router-dom'
import {AuthProvider, useAuth} from './context/AuthContext'
import {Layout} from './components/Layout'
import {AuthLayout,LoginPage,RegisterPage,OTPPage,EmailPage,ForgotPage,ResetPage} from './security/auth-pages'
import {ProfilePage,SecurityPage} from './security/profile-pages'
import {DashboardPage,UsersPage,EventsPage} from './security/admin-pages'
import {ToastProvider} from './security/state'
import './security/style.css'
import {Dashboard} from './pages/Dashboard'
import {Projects} from './pages/Projects'
import {ProjectWorkspace} from './pages/ProjectWorkspace'
import {TestCaseForm, TestCases} from './pages/TestCases'
import {TestCaseDetail} from './pages/TestCaseDetail'
import {Defects, Executions, Forbidden, Reports, Users} from './pages/OtherPages'
import {Analytics} from './pages/Analytics'
import {AIAssistant} from './pages/AIAssistant'
import {Requirements} from './pages/Requirements'
import {TestRuns} from './pages/TestRuns'
import {TestSuites} from './pages/TestSuites'
import {APITesting} from './pages/APITesting'
import './styles/base.css'
import './styles/ui.css'

function Guard({children, roles}: {children: React.ReactNode; roles?: string[]}) {
  const {user, loading} = useAuth()
  const location=useLocation()
  if (loading) return <div className="boot">Завантаження WebTestCase…</div>
  if (!user) return <Navigate to="/login" replace/>
  if (!user.email_verified && location.pathname!=="/profile") return <Navigate to="/profile" replace/>
  if (roles && !roles.includes(user.role)) return <Forbidden/>
  return <>{children}</>
}

function App() {
  return <Routes>
    <Route element={<section className="security-area"><AuthLayout><Outlet/></AuthLayout></section>}>
      <Route path="/login" element={<LoginPage/>}/><Route path="/registration" element={<RegisterPage/>}/><Route path="/register" element={<RegisterPage/>}/>
      <Route path="/two-factor" element={<OTPPage/>}/><Route path="/check-email" element={<EmailPage/>}/><Route path="/verify-email" element={<EmailPage verify/>}/><Route path="/forgot-password" element={<ForgotPage/>}/><Route path="/reset-password" element={<ResetPage/>}/>
    </Route>
    <Route element={<Guard><Layout/></Guard>}>
      <Route path="/security" element={<section className="security-area"><SecurityPage/></section>}/>
      <Route path="/security/overview" element={<Guard roles={['ADMIN']}><section className="security-area"><DashboardPage/></section></Guard>}/>
      <Route path="/security/users" element={<Guard roles={['ADMIN']}><section className="security-area"><UsersPage/></section></Guard>}/>
      <Route path="/security/events" element={<Guard roles={['ADMIN']}><section className="security-area"><EventsPage/></section></Guard>}/>
      <Route path="/dashboard" element={<Dashboard/>}/><Route path="/projects" element={<Projects/>}/><Route path="/projects/:projectId" element={<ProjectWorkspace/>}/><Route path="/projects/:projectId/:section" element={<ProjectWorkspace/>}/><Route path="/requirements" element={<Requirements/>}/>
      <Route path="/test-cases" element={<TestCases/>}/><Route path="/test-cases/create" element={<Guard roles={['ADMIN', 'MANAGER']}><TestCaseForm/></Guard>}/><Route path="/projects/:projectId/test-cases/create" element={<Guard roles={['ADMIN', 'MANAGER']}><TestCaseForm/></Guard>}/><Route path="/projects/:projectId/test-cases/:id" element={<TestCaseDetail/>}/><Route path="/projects/:projectId/test-cases/:id/edit" element={<Guard roles={['ADMIN', 'MANAGER']}><TestCaseForm/></Guard>}/><Route path="/test-cases/:id" element={<TestCaseDetail/>}/><Route path="/test-cases/:id/edit" element={<Guard roles={['ADMIN', 'MANAGER']}><TestCaseForm/></Guard>}/>
      <Route path="/executions" element={<Executions/>}/><Route path="/test-suites" element={<Guard roles={['ADMIN', 'MANAGER']}><TestSuites/></Guard>}/><Route path="/test-runs" element={<TestRuns/>}/><Route path="/testing-api" element={<Guard roles={['ADMIN', 'MANAGER']}><APITesting/></Guard>}/><Route path="/defects" element={<Defects/>}/><Route path="/reports" element={<Reports/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/ai-assistant" element={<AIAssistant/>}/><Route path="/profile" element={<section className="security-area"><ProfilePage/></section>}/><Route path="/admin/users" element={<Guard roles={['ADMIN']}><Users/></Guard>}/>
    </Route>
    <Route path="*" element={<Navigate to="/dashboard"/>}/>
  </Routes>
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><ToastProvider><AuthProvider><App/></AuthProvider></ToastProvider></BrowserRouter></React.StrictMode>)
