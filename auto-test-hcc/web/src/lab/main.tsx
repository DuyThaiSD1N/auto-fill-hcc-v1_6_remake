import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import LabApp from "./LabApp";
import "../styles.css";
import "./lab.css";
import "./auto/auto.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LabApp />
  </StrictMode>,
);
