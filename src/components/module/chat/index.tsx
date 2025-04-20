import { useState } from "react";
import ChatInput from "./input";
import { cn } from "@/lib/utils";

export default function Index() {
  const prevChat = true;
  const [msg, setMsg] = useState("");
  const handleSend = (msg: string) => {
    console.log(msg);
  };

  return (
    <div
      className={cn("h-dvh flex flex-col gap-[12px] items-center", {
        "justify-center": !prevChat,
        "justify-between": prevChat,
      })}
    >
      ajaj
      <ChatInput onSend={handleSend} msg={msg} setMsg={setMsg} />
    </div>
  );
}
