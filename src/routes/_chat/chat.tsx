import ChatInput from "@/components/module/chat/input";
import { cn } from "@/lib/utils";
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

export const Route = createFileRoute("/_chat/chat")({
  component: RouteComponent,
});

function RouteComponent() {
  const prevChat = true;
  const [msg, setMsg] = useState("");
  const handleSend = (msg: string) => {
    console.log(msg);
  };
  return (
    <div
      className={cn("h-[99vh] flex flex-col gap-[12px] items-center", {
        "justify-center": !prevChat,
        "justify-between": prevChat,
      })}
    >
      ajaj
      <ChatInput onSend={handleSend} msg={msg} setMsg={setMsg} />
    </div>
  );
}
