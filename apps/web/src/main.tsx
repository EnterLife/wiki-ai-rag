import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { initializeAuthentication } from "./auth";
import "./styles.css";

void initializeAuthentication()
  .catch(() => false)
  .finally(() => {
    ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>,
    );
  });
