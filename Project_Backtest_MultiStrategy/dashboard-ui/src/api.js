import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8001",
  timeout: 30000,
});

export default api;
