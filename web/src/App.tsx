import { NavLink, Outlet } from "react-router-dom";
import {
  ChartLine,
  ChatCircleDots,
  CalendarBlank,
  LinkSimple,
  PaintBrush,
  Users,
  type Icon,
} from "@phosphor-icons/react";

interface NavItem {
  to: string;
  label: string;
  icon: Icon;
  end?: boolean;
}

const NAV: NavItem[] = [
  { to: "/", label: "Composer", icon: ChatCircleDots, end: true },
  { to: "/brands", label: "Brands", icon: Users },
  { to: "/channels", label: "Channels", icon: LinkSimple },
  { to: "/studio", label: "Studio", icon: PaintBrush },
  { to: "/calendar", label: "Calendar", icon: CalendarBlank },
  { to: "/insights", label: "Insights", icon: ChartLine },
];

export default function App() {
  return (
    <div className="flex h-dvh">
      <aside className="flex w-56 shrink-0 flex-col gap-6 border-r border-line bg-panel p-4">
        <h1 className="text-base font-semibold tracking-tight text-accent">Head of Social</h1>
        <nav className="flex flex-col gap-1">
          {NAV.map(({ to, label, icon: IconCmp, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-panel2 font-medium text-accent"
                    : "text-mute hover:bg-panel2 hover:text-ink"
                }`
              }
            >
              <IconCmp size={17} weight="duotone" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
