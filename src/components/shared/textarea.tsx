import { cn } from "@/lib/utils";
import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";

const Textarea = forwardRef<HTMLTextAreaElement, ITextArea>(
  ({ value, className = "", ...props }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Expose internal ref to parent via forwarded ref
    useImperativeHandle(ref, () => textareaRef.current!, []);

    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      }
    }, [value]);

    return (
      <textarea
        {...props}
        ref={textareaRef}
        value={value}
        rows={1}
        className={cn(
          "w-full max-h-[30vh] text-tertiary resize-none custom-scrollbar overflow-y-auto text-sm focus:outline-none",
          className,
        )}
      />
    );
  },
);

Textarea.displayName = "Textarea";
export default Textarea;
