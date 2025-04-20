import Textarea from "@/components/shared/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Send } from "lucide-react";
import { forwardRef, Ref } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  msg: string;
  setMsg: (msg: string) => void;
  placeholder?: string;
  className?: string;
}

const ChatInput = forwardRef(
  (
    { onSend, msg, setMsg, placeholder, className }: ChatInputProps,
    ref: Ref<HTMLTextAreaElement>,
  ) => {
    const handleSubmit = () => {
      if (!msg.trim()) return;
      onSend(msg.trim());
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    };

    return (
      <div
        className={cn(
          "w-full max-w-xl border border-light-300 bg-light-100 dark:bg-light-100 p-4 rounded-[20px]",
          className,
        )}
      >
        <Textarea
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          ref={ref}
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
  },
);

ChatInput.displayName = "ChatInput";

export default ChatInput;
