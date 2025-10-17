export function getApiBase(): string {
  const server = process.env.API_URL;               
  const client = process.env.NEXT_PUBLIC_API_URL;   
  const val = server ?? client;

  if (!val) {
    if (process.env.CI) return "http://127.0.0.1:8000";
    throw new Error("API base URL not set");
  }
  return val;
}
