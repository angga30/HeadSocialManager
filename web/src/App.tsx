import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/", label: "💬 Composer", end: true },
  { to: "/brands", label: "👤 Brands" },
  { to: "/channels", label: "🔗 Channels" },
  { to: "/studio", label: "🎨 Studio" },
  { to: "/calendar", label: "📅 Calendar" },
  { to: "/insights", label: "📈 Insights" },
];

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Head of Social</h1>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}