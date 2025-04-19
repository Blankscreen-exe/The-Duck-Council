import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="p-2">
      <h3 className="bg-red-600">Welcome Home!</h3>
      <p>heloo</p>
    </div>
  );
}
