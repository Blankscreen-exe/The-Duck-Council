import { cn } from "@/lib/utils";
import { useRef, useEffect } from "react";

export default function Textarea({
  value,
  className = "",
  ...props
}: ITextArea) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
        "w-full max-h-[50vh] resize-none custom-scrollbar overflow-y-auto text-sm focus:outline-none",
        className,
      )}
    />
  );
}
