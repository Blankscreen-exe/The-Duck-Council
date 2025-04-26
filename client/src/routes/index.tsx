import ChatInput from "@/components/module/chat/input";
import { cn } from "@/lib/utils";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import style from "@/styles/chat.module.css";
import { BRAND } from "@/lib/contants";
import { CAccordion } from "@/components/shared/accordion";
import Seo from "@/components/module/seo";

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
    <>
      <Seo />
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
                  className="bg-neutral-100 dark:bg-light-100 hidden md:flex w-full h-96 rounded-[12px]"
                />
              );
            })}
            <CAccordion
              className="md:hidden"
              defaultValue="item-1"
              items={[
                {
                  value: "item-1",
                  title: "Duck 1 (Score: 10.3)",
                  content:
                    "Yes. It adheres to the WAI-ARIA design pattern. Lorem ipsum dolor sit amet, qui minim labore adipisicing minim sint cillum sint consectetur cupidatat.Yes. It adheres to the WAI-ARIA design pattern. Lorem ipsum dolor sit amet, qui minim labore adipisicing minim sint cillum sint consectetur cupidatat.",
                },
                {
                  value: "item-2",
                  title: "Is it styled?",
                  content:
                    "Yes. It comes with default styles that match the aesthetic.",
                },
                {
                  value: "item-3",
                  title: "Is it animated?",
                  content:
                    "Yes. It's animated by default, but you can disable it if you prefer.",
                },
              ]}
            />
          </div>
        </div>

        <div className={cn(style.content_chat, isAnswer && style.answered)}>
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
    </>
  );
}
