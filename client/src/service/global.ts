import { useMutation } from "@tanstack/react-query";
import { Apis } from "./core/";

export const useCreatePrompt = () => {
  const { data, mutate, isPending, isError } = useMutation<
    IRespPrompt,
    Error,
    IBodyPrompt
  >({
    mutationFn: (body: IBodyPrompt) => Apis.global.prompt(body),
  });

  return {
    prompt: mutate,
    data,
    isPending,
    isError,
  };
};
