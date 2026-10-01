import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import Composer from "./pages/Composer";
import Brands from "./pages/Brands";
import Channels from "./pages/Channels";
import Studio from "./pages/Studio";
import Calendar from "./pages/Calendar";
import Insights from "./pages/Insights";
import "./styles.css";

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <App />,
      children: [
        { index: true, element: <Composer /> },
        { path: "brands", element: <Brands /> },
        { path: "channels", element: <Channels /> },
        { path: "studio", element: <Studio /> },
        { path: "calendar", element: <Calendar /> },
        { path: "insights", element: <Insights /> },
      ],
    },
  ],
  { basename: "/app" }
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);