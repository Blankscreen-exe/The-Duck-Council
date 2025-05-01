declare interface IResponse<T> {
  data: T;
  success: boolean;
  message: string;
}

declare interface IBodyPrompt {
  situation: string;
  action: string;
}

declare interface IPrompt {
  duck_name: string;
  reasoning: string;
  score: number;
  available: boolean;
  image: string;
}
declare interface IRespPrompt extends IResponse<IPrompt[]> {}
