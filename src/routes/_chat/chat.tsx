import ChatInput from "@/components/module/chat/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";

export const Route = createFileRoute("/_chat/chat")({
  component: RouteComponent,
});

function RouteComponent() {
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
  };

  const { isSubmit, isAnswer } = formState;

  return (
    <div
      className={cn(
        "h-[99vh] overflow-y-auto custom-scrollbar flex flex-col gap-[12px] items-center",
        {
          "justify-center": !isAnswer,
          "justify-between": isAnswer,
        },
      )}
    >
      <div className="max-w-2xl mx-auto ">
        <div
          className={cn(
            "flex items-center justify-center flex-col gap-[4px] *:text-center h-[40vh] transition-all duration-500 ease-in-out",
            isAnswer
              ? "opacity-0 max-h-0 overflow-hidden pointer-events-none"
              : "opacity-100",
          )}
        >
          <h1>The Duck Council</h1>
          <p className="text-lg font-secondary font-semibold">
            Lorem ipsum dolor sit amet, qui minim labore adipisicing minim sint
            cillum sint consectetur cupidatat. Lorem ipsum dolor sit amet, qui
            minim labore adipisicing minim sint cillum sint consectetur
            cupidatat.
          </p>
        </div>

        <div
          className={cn(
            "grid grid-cols-2 gap-5 transition-all duration-500 ease-in-out",
            isAnswer
              ? "opacity-100 w-full pb-20 pt-2"
              : "opacity-0 max-h-0 overflow-hidden pointer-events-none",
          )}
        >
          {Array.from({ length: 10 }).map((_, id) => {
            return (
              <div
                key={id}
                className="bg-light-300 dark:bg-light-100 w-full h-40"
              ></div>
            );
          })}
        </div>
      </div>

      <div
        className={cn(
          "w-full flex justify-center flex-col gap-2 *:w-full *:flex *:justify-center *:items-center transition-all duration-300 ease-in-out",
          {
            "absolute bottom-2": isAnswer,
          },
        )}
      >
        <div
          className={cn(
            "transition-all duration-500 ease-in-out",
            isSubmit
              ? "opacity-0 max-h-0 overflow-hidden pointer-events-none"
              : "opacity-100 max-h-40",
          )}
        >
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

        <div
          className={cn(
            "transition-all duration-500 ease-in-out flex-col gap-[8px]",
            isSubmit
              ? "opacity-100"
              : "opacity-0 max-h-0 overflow-hidden pointer-events-none",
          )}
        >
          <ChatInput
            onSend={handleSend}
            msg={formState.action}
            setMsg={(value) =>
              setFormState((prev) => ({ ...prev, action: value }))
            }
            placeholder="Your Action"
            ref={actionRef}
          />
          <Button
            onClick={handleBackToSituation}
            className="text-sm underline text-muted-foreground hover:text-foreground transition-opacity duration-300"
            variant={"none"}
          >
            Back to Situation
          </Button>
        </div>
      </div>
    </div>
  );
}
