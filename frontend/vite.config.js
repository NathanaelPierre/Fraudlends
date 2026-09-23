import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// FraudLens frontend. Talks to the FastAPI backend directly (see src/api/client.js);
// no proxy is required as long as FRONTEND_ORIGIN on the backend matches this dev
// server's origin (http://localhost:5173 by default) so CORS allows the requests.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
