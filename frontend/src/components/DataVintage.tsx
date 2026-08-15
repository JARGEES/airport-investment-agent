import { useState, useRef, useEffect } from "react";
import type { HealthResponse } from "../types";

interface Props {
  health: HealthResponse | null;
  onUpdateSettings: (patch: { model?: string; analysis_mode?: string }) => void;
}

export function DataVintage({ health, onUpdateSettings }: Props) {
  const [modelOpen, setModelOpen] = useState(false);
  const [customMode, setCustomMode] = useState(false);
  const [customModel, setCustomModel] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const customInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setModelOpen(false);
        setCustomMode(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  useEffect(() => {
    if (customMode && customInputRef.current) {
      customInputRef.current.focus();
    }
  }, [customMode]);

  if (!health) return null;

  const vintage = health.data_vintage;
  const model = health.model || "unknown";
  const modelShort = model.includes("/") ? model.split("/").pop()! : model;
  const mode = health.analysis_mode || "fast";
  const models = health.available_models || [];

  const isPreset = models.some((m) => m.id === model);

  function handleCustomSubmit() {
    const val = customModel.trim();
    if (val) {
      onUpdateSettings({ model: val });
      setModelOpen(false);
      setCustomMode(false);
      setCustomModel("");
    }
  }

  return (
    <div className="vintage">
      <div className="vintage__model-wrapper" ref={dropdownRef}>
        <button
          className="vintage__model vintage__model--btn"
          onClick={() => setModelOpen(!modelOpen)}
          title="Change LLM model"
        >
          {modelShort}
          <span className="vintage__caret">{modelOpen ? "▲" : "▼"}</span>
        </button>
        {modelOpen && (
          <div className="vintage__dropdown">
            {models.map((m) => (
              <button
                key={m.id}
                className={`vintage__dropdown-item${m.id === model ? " vintage__dropdown-item--active" : ""}`}
                onClick={() => {
                  onUpdateSettings({ model: m.id });
                  setModelOpen(false);
                  setCustomMode(false);
                }}
              >
                <span className="vintage__dropdown-name">{m.name}</span>
                <span className="vintage__dropdown-provider">{m.provider}</span>
              </button>
            ))}
            <div className="vintage__dropdown-divider" />
            {customMode ? (
              <div className="vintage__custom-input">
                <input
                  ref={customInputRef}
                  type="text"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCustomSubmit();
                    if (e.key === "Escape") {
                      setCustomMode(false);
                      setCustomModel("");
                    }
                  }}
                  placeholder="provider/model-name"
                />
                <button onClick={handleCustomSubmit} disabled={!customModel.trim()}>
                  Set
                </button>
              </div>
            ) : (
              <button
                className={`vintage__dropdown-item vintage__dropdown-item--custom${!isPreset ? " vintage__dropdown-item--active" : ""}`}
                onClick={() => setCustomMode(true)}
              >
                <span className="vintage__dropdown-name">Custom model...</span>
                <span className="vintage__dropdown-provider">LiteLLM</span>
              </button>
            )}
          </div>
        )}
      </div>

      <button
        className={`vintage__mode vintage__mode--${mode}`}
        onClick={() =>
          onUpdateSettings({ analysis_mode: mode === "fast" ? "deep" : "fast" })
        }
        title={
          mode === "fast"
            ? "Fast: top 100 airports. Click for Deep analysis (all airports)"
            : "Deep: all airports. Click for Fast analysis (top 100)"
        }
      >
        {mode === "fast" ? "Fast" : "Deep"}
      </button>

      {vintage && vintage.record_count > 0 ? (
        <span className="vintage__data">
          Data: {vintage.latest_period} &middot;{" "}
          {vintage.record_count.toLocaleString()} records
        </span>
      ) : (
        <span className="vintage__data vintage__data--warn">No BTS data loaded</span>
      )}
    </div>
  );
}
