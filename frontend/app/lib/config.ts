const apiServer = process.env.API_URL;               // set on Vercel
const apiClient = process.env.NEXT_PUBLIC_API_URL;   // already set

export const API_BASE =
  apiServer ?? apiClient ?? (() => { throw new Error("API base URL not set"); })();
