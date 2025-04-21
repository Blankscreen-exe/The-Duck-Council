import Textarea from "@/components/shared/textarea";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ArrowLeft, Send } from "lucide-react";
import { forwardRef, Ref } from "react";
import style from "@/styles/chat.module.css";

const ChatInput = forwardRef(
  (
    {
      onSend,
      msg,
      setMsg,
      placeholder,
      className,
      handleBack,
      isBack,
    }: IChatInput,
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
      <div className={cn(style.parent_input, className)}>
        <Textarea
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          ref={ref}
        />
        <div>
          {isBack && (
            <Button
              onClick={handleBack}
              className={style.input_back}
              variant={"none"}
              size={"auto"}
              title="Back to Situation"
            >
              <ArrowLeft />
            </Button>
          )}
          <Button
            variant={"none"}
            size={"auto"}
            onClick={handleSubmit}
            disabled={!msg}
          >
            <Send />
          </Button>
        </div>
      </div>
    );
  },
);

ChatInput.displayName = "ChatInput";

export default ChatInput;
