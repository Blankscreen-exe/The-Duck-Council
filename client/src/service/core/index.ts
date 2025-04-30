import { Http } from "@/configs/http/method";

export const Apis = {
  global: {
    prompt: (body: IBodyPrompt) => Http.post<IRespPrompt>("/prompt", body),
  },
};
