export default function errorHandler(error: any) {
  const status = error?.response?.status;
  const message = error?.response?.data?.message;
  const payload = error?.response?.config?.data;
  const path = error?.response?.config?.url;

  console.log({
    error_apis: {
      status,
      message,
      path,
      payload,
    },
  });
  return Promise.reject(error);
}
