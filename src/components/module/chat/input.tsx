import Textarea from "@/components/shared/textarea";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";
import { useRef, useEffect } from "react";

export default function ChatInput({
  onSend,
  msg,
  setMsg,
}: {
  onSend: (message: string) => void;
  msg: string;
  setMsg: (msg: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [msg]);

  const handleSubmit = () => {
    if (!msg.trim()) return;
    onSend(msg.trim());
    setMsg("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-xl border border-neutral-500 bg-neutral-700 p-4 rounded-[20px]">
      <Textarea
        value={msg}
        onChange={(e) => setMsg(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Send a problem"
      />
      <div className="flex justify-end">
        <Button
          variant={"none"}
          size={"auto"}
          onClick={handleSubmit}
          disabled={!msg}
        >
          <Send className="size-[18px]" />
        </Button>
      </div>
    </div>
  );
}
