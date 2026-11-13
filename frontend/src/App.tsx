import { BrowserRouter, Route, Routes, Link } from 'react-router-dom'
import AccountScreen from './AccountScreen'
import { SignIn } from './Auth'
import { Layout, RequireSession } from './Layout'
import { Home, Catalog, VehiclePage } from './Marketplace'
import { Bookings } from './Bookings'
import { Dashboard } from './Dashboard'
import { Fleet, MaintenanceIndex, MaintenancePage, Values } from './Owner'

export default function App() {
  return <BrowserRouter basename="/app"><Layout><Routes>
    <Route index element={<Home />} /><Route path="vehicles" element={<Catalog />} />
    <Route path="vehicles/:id" element={<VehiclePage />} /><Route path="sign-in" element={<SignIn />} />
    <Route path="register" element={<AccountScreen screen="signup" />} />
    <Route path="verify-email/:key" element={<AccountScreen screen="verify" />} />
    <Route path="reset-password" element={<AccountScreen screen="request-reset" />} />
    <Route path="reset-password/:key" element={<AccountScreen screen="reset" />} />
    <Route path="account" element={<RequireSession><AccountScreen screen="account" /></RequireSession>} />
    <Route path="dashboard" element={<RequireSession><Dashboard /></RequireSession>} />
    <Route path="owner" element={<RequireSession><Dashboard owner /></RequireSession>} />
    <Route path="bookings/:id" element={<RequireSession><Bookings /></RequireSession>} />
    <Route path="bookings" element={<RequireSession><Bookings /></RequireSession>} />
    <Route path="owner/requests" element={<RequireSession><Bookings owner /></RequireSession>} />
    <Route path="owner/fleet" element={<RequireSession><Fleet /></RequireSession>} />
    <Route path="owner/fleet/:id/maintenance" element={<RequireSession><MaintenancePage /></RequireSession>} />
    <Route path="owner/maintenance" element={<RequireSession><MaintenanceIndex /></RequireSession>} />
    <Route path="owner/value" element={<RequireSession><Values /></RequireSession>} />
    <Route path="*" element={<><h1>Page not found</h1><Link to="/">Return home</Link></>} />
  </Routes></Layout></BrowserRouter>
}
