import { Base } from "./interceptor";

export class Http {
  static async get<T>(url: string, params?: unknown) {
    const response = await Base.get<T>(url, { params });
    return response?.data;
  }

  static async post<T>(url: string, data: unknown, options?: any) {
    const response = await Base.post<T>(url, data, options);
    return response?.data;
  }

  static async put<T>(url: string, data: unknown) {
    const response = await Base.put<T>(url, data);
    return response?.data;
  }

  static async delete<T>(url: string) {
    const response = await Base.delete<T>(url);
    return response?.data;
  }
}
