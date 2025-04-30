import axios, { AxiosInstance } from "axios";

import { config } from "../index";
import errorHandler from "./error-handler";

const createAxiosInstance = (baseURL: string): AxiosInstance => {
  const instance = axios.create({
    baseURL,
    headers: {
      "Content-Type": "application/json",
      ApiKey: config.API_KEY,
    },
  });

  applyInterceptor(instance);
  return instance;
};

const applyInterceptor = (axiosInstance: AxiosInstance) => {
  axiosInstance.interceptors.request.use(async (request) => {
    return request;
  });
  axiosInstance.interceptors.response.use((response) => response, errorHandler);
};

export const Base = createAxiosInstance(config.API_URL as string);
