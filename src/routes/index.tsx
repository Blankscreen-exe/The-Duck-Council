import ChatInput from "@/components/module/chat/input";
import { cn } from "@/lib/utils";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import style from "@/styles/chat.module.css";
import { BRAND } from "@/lib/contants";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const situationRef = useRef<HTMLTextAreaElement | null>(null);
  const actionRef = useRef<HTMLTextAreaElement | null>(null);
  const [formState, setFormState] = useState({
    situation: "",
    action: "",
    isSubmit: false,
    isAnswer: false,
  });

  useEffect(() => {
    situationRef.current?.focus();
  }, []);

  const handleSend = (msg: string) => {
    if (formState.situation && !isSubmit) {
      setFormState((prev) => ({ ...prev, isSubmit: true }));
      actionRef.current?.focus();
    } else if (formState.isSubmit && formState.situation && formState.action) {
      situationRef.current?.focus();
      setFormState({
        situation: "",
        action: "",
        isSubmit: false,
        isAnswer: true,
      });
      console.log(msg);
    }
  };
  const handleBackToSituation = () => {
    setFormState((prev) => ({ ...prev, isSubmit: false }));
    situationRef.current?.focus();
  };

  const { isSubmit, isAnswer } = formState;

  return (
    <div
      className={cn(style.parent, "custom-scrollbar", {
        "justify-center": !isAnswer,
        "justify-between": isAnswer,
      })}
    >
      <div className={style.content}>
        <div className={cn(style.content_header, isAnswer && style.hide)}>
          <h1>{BRAND.title}</h1>
          <p>{BRAND.description}</p>
        </div>

        <div className={cn(style.content_main, !isAnswer && style.hide)}>
          {Array.from({ length: 4 }).map((_, id) => {
            return (
              <div
                key={id}
                className="bg-neutral-100 dark:bg-light-100 w-full h-96 rounded-[12px]"
              />
            );
          })}
        </div>
      </div>

      <div className={cn(style.content_chat, isAnswer && "fixed bottom-2")}>
        <div className={isSubmit ? style.hide : style.show}>
          <ChatInput
            onSend={handleSend}
            msg={formState.situation}
            setMsg={(value) =>
              setFormState((prev) => ({ ...prev, situation: value }))
            }
            placeholder="Your Situation"
            ref={situationRef}
          />
        </div>

        <div className={cn(isSubmit ? [style.show] : [style.hide])}>
          <ChatInput
            onSend={handleSend}
            msg={formState.action}
            setMsg={(value) =>
              setFormState((prev) => ({ ...prev, action: value }))
            }
            isBack
            handleBack={handleBackToSituation}
            placeholder="Your Action"
            ref={actionRef}
          />
        </div>
      </div>
    </div>
  );
}
