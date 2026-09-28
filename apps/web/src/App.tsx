import { Route, Routes } from 'react-router-dom';
import { ResourceTopologyPage } from './pages/ResourceTopology';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { IncidentsPage } from './pages/Incidents';
import { IncidentDetailPage } from './pages/IncidentDetail';
import { InvestigatePage } from './pages/Investigate';
import { ResourcesPage } from './pages/Resources';
import { AgentsPage } from './pages/Agents';
import { AuditPage } from './pages/Audit';
import { SettingsPage } from './pages/Settings';
import { ConnectorsPage } from './pages/Connectors';
import { CredentialsPage } from './pages/Credentials';
import { RemediationsPage } from './pages/Remediations';
import { JobStatusPage } from './pages/JobStatus';
import { DiscoverySchedulesPage } from './pages/DiscoverySchedules';
import { OrganizationAccessPage } from './pages/OrganizationAccess';
import { LoginPage } from './pages/Login';
import { SetupPage } from './pages/Setup';
import { SignupPage } from './pages/Signup';
import { ForgotPasswordPage } from './pages/ForgotPassword';
import { ResetPasswordPage } from './pages/ResetPassword';
import { VerifyEmailPage } from './pages/VerifyEmail';
import { SessionsPage } from './pages/Sessions';
import { SSOPage } from './pages/SSO';
import { SSOLoginPage } from './pages/SSOLogin';
import { AlertsPage } from './pages/Alerts';
import { MeteringPage } from './pages/Metering';
import { BillingPage } from './pages/Billing';
import { DeveloperApiPage } from './pages/DeveloperApi';
import { MarketplacePage } from './pages/Marketplace';

export function App() {
  return <Routes>
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
    <Route path="/verify-email" element={<VerifyEmailPage />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/sso-login" element={<SSOLoginPage />} />
    <Route path="/setup" element={<SetupPage />} />
    <Route path="/signup" element={<SignupPage />} />
    <Route element={<ProtectedRoute />}><Route path="/" element={<Layout />}>
      <Route index element={<Dashboard />} /><Route path="dashboard" element={<Dashboard />} />
      <Route path="incidents" element={<IncidentsPage />} /><Route path="incidents/:incidentId" element={<IncidentDetailPage />} />
      <Route path="investigate" element={<InvestigatePage />} /><Route path="resources" element={<ResourcesPage />} />
      <Route path="resources/topology" element={<ResourceTopologyPage />} /><Route path="resources/:resourceId" element={<ResourcesPage />} />
      <Route path="agents" element={<AgentsPage />} /><Route path="agents/:agentId" element={<AgentsPage />} />
      <Route path="audit" element={<AuditPage />} /><Route path="settings" element={<SettingsPage />} />
      <Route path="connectors" element={<ConnectorsPage />} /><Route path="credentials" element={<CredentialsPage />} />
      <Route path="credentials/:credentialId" element={<CredentialsPage />} /><Route path="remediations" element={<RemediationsPage />} />
      <Route path="jobs/:jobId" element={<JobStatusPage />} /><Route path="discovery-schedules" element={<DiscoverySchedulesPage />} />
      <Route path="organization" element={<OrganizationAccessPage />} /><Route path="sessions" element={<SessionsPage />} />
      <Route path="sso" element={<SSOPage />} /><Route path="alerts" element={<AlertsPage />} />
      <Route path="metering" element={<MeteringPage />} /><Route path="billing" element={<BillingPage />} />
      <Route path="marketplace" element={<MarketplacePage />} />
      <Route path="developer-api" element={<DeveloperApiPage />} />
    </Route></Route>
  </Routes>;
}
