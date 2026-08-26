import { Routes, Route } from "react-router-dom";
import { AppShell } from "./AppShell";
import { Today } from "../pages/Today";
import { Divisions } from "../pages/Divisions";
import { Industry } from "../pages/Industry";
import { Comparison } from "../pages/Comparison";
import { AboutUs } from "../pages/AboutUs";
import { Ask } from "../pages/Ask";
import { Settings } from "../pages/Settings";
import { Digest } from "../pages/Digest";
import { StyleGuide } from "../pages/StyleGuide";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Today />} />
        <Route path="/divisions" element={<Divisions />} />
        <Route path="/industry" element={<Industry />} />
        <Route path="/comparison" element={<Comparison />} />
        <Route path="/about-us" element={<AboutUs />} />
        <Route path="/ask" element={<Ask />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/digest" element={<Digest />} />
        <Route path="/styleguide" element={<StyleGuide />} />
      </Route>
    </Routes>
  );
}
