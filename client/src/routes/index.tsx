import ChatInput from "@/components/module/chat/input";
import { cn } from "@/lib/utils";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import style from "@/styles/chat.module.css";
import { BRAND } from "@/lib/contants";
import { CAccordion } from "@/components/shared/accordion";
import Seo from "@/components/module/seo";
import { useCreatePrompt } from "@/service/global";
import Loader from "@/components/module/chat/loader";
import Result from "@/components/module/chat/text";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const { prompt, isPending, data } = useCreatePrompt();
  const situationRef = useRef<HTMLTextAreaElement | null>(null);
  const actionRef = useRef<HTMLTextAreaElement | null>(null);
  const [formState, setFormState] = useState({
    situation: "",
    action: "",
    isSubmit: false,
    isAnswer: false,
  });

  const duckResponse = data?.map((item) => {
    const name = item.duck_name;
    return {
      value: name,
      title: name,
      content: <Result item={item} />,
    };
  });

  useEffect(() => {
    situationRef.current?.focus();
  }, []);

  const handleSend = () => {
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
      const payload = {
        situation: formState.situation,
        action: formState.action,
      };
      prompt(payload);
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

          <div className={cn(style.content_main, !isAnswer && style.hide, "hidden! md:grid!")}>
            {isPending && <Loader />}
            {duckResponse?.map((item) => item.content)}
          </div>

          <div className={cn(style.content_main, !isAnswer && style.hide, "md:hidden! grid")}>
            {isPending && <Loader />}
            {!!duckResponse?.length && (
              <CAccordion
                className="md:hidden"
                defaultValue={duckResponse?.[0].value}
                items={duckResponse}
              />
            )}
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
