import { Activity, BarChart3, Database, MapPinned, Waves } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Intro", icon: Waves, end: true },
  { to: "/graphs", label: "Graphs", icon: BarChart3 },
  { to: "/predictions", label: "Predictions", icon: Activity },
  { to: "/map", label: "Map", icon: MapPinned },
  { to: "/data", label: "Data", icon: Database },
];

export default function Layout() {
  return (
    <div className="app-shell">
      <header className="top-nav">
        <div className="top-nav__inner">
          <NavLink to="/" className="brand">
            <span className="brand-mark">LT</span>
            <span>Lake Tanganyika</span>
          </NavLink>
          <nav className="nav-links" aria-label="Primary navigation">
            {navItems.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
                <Icon aria-hidden="true" size={18} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="page-wrap">
        <Outlet />
      </main>
    </div>
  );
}
