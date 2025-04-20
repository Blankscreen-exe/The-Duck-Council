import { createFileRoute, Link, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/_public/layout")({
  component: Layout,
});

function Layout() {
  return (
    <>
      <div className="flex items-center gap-[8px]">
        <Link to="/">Home</Link>
        <Link to="/about">About</Link>
        <Link to="/chat">Chat</Link>
      </div>
      <Outlet />
    </>
  );
}
