import React, { useState } from "react";
import { PlayIcon } from "@heroicons/react/24/solid";
import Spinner from "../components/Spinner";

const API_BASE = import.meta.env.VITE_API_BASE || "";

type ModelDir = "model_cstgan" | "model_attn_vit" | "model_mask";
type ModelKind = "cstgan_c" | "mb_taylor" | "vit-unet" | "attn" | "0106";
type DatasetName = "005_046" | "029_031" | "046_047" | "048_050";

export default function DicomGenerator() {
  const [modelDir, setModelDir] = useState<ModelDir>("model_cstgan");
  const [modelKind, setModelKind] = useState<ModelKind>("cstgan_c");
  const [dataset, setDataset] = useState<DatasetName>("005_046");
  const [gpuIds, setGpuIds] = useState("0");
  const [log, setLog] = useState("");
  const [running, setRunning] = useState(false);

  async function runPipeline() {
    if (!dataset || !modelDir || !modelKind) {
      alert("请先选择数据集、模型目录和模型类型！");
      return;
    }

    setRunning(true);
    setLog("");

    try {
      const payload = {
        dataset,
        modelCategory: modelDir,
        modelName: modelKind,
        gpuIds,
      };

      const res = await fetch(`${API_BASE}/api/dicom/export`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const text = await res.text();

      let json: any = null;
      try {
        json = JSON.parse(text);
      } catch {
        setLog(`❌ 返回内容不是合法 JSON：\n${text}`);
        return;
      }

      if (!res.ok || !json?.ok) {
        setLog(
          [
            "❌ 请求失败",
            json?.message || res.statusText || "Unknown error",
            text,
          ]
            .filter(Boolean)
            .join("\n\n")
        );
        return;
      }

      const result = json?.data?.data;
      const cmd = result?.cmd ?? "";
      const stdout = result?.stdout ?? "";
      const returncode = result?.returncode;

      setLog(
        [
          cmd ? `CMD: ${cmd}` : "",
          stdout,
          returncode !== undefined ? `\n[returncode] ${returncode}` : "",
        ]
          .filter(Boolean)
          .join("\n")
      );

      setTimeout(() => {
        const ta = document.getElementById("pipeline-log") as HTMLTextAreaElement | null;
        if (ta) ta.scrollTop = ta.scrollHeight;
      }, 0);
    } catch (e: any) {
      setLog(`❌ 生成 DICOM 失败: ${e?.message || e}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page-shell space-y-6">
      <section className="page-hero">
        <div className="page-eyebrow">DICOM Export</div>
        <h1 className="page-title">CBCT→CT DICOM 导出</h1>
        <p className="page-subtitle">
          已改为 Spring 后端接口 <code>/api/dicom/export</code>，将推理结果恢复为 DICOM 序列。
        </p>
      </section>

      <section className="rounded-3xl border border-slate-200/70 bg-white/90 p-6 shadow-[0_16px_48px_rgba(15,23,42,0.06)] backdrop-blur">
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-4">
          <label className="space-y-2">
            <span className="text-sm font-semibold text-slate-700">模型目录</span>
            <select
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              value={modelDir}
              onChange={(e) => {
                const v = e.target.value as ModelDir;
                setModelDir(v);
                if (v === "model_cstgan") setModelKind("cstgan_c");
                if (v === "model_attn_vit") setModelKind("vit-unet");
                if (v === "model_mask") setModelKind("0106");
              }}
              disabled={running}
            >
              <option value="model_cstgan">model_cstgan</option>
              <option value="model_attn_vit">model_attn_vit</option>
              <option value="model_mask">model_mask</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-sm font-semibold text-slate-700">模型类型</span>
            <select
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              value={modelKind}
              onChange={(e) => setModelKind(e.target.value as ModelKind)}
              disabled={running}
            >
              {modelDir === "model_cstgan" && (
                <>
                  <option value="cstgan_c">cstgan_c</option>
                  <option value="mb_taylor">mb_taylor</option>
                </>
              )}
              {modelDir === "model_attn_vit" && (
                <>
                  <option value="vit-unet">vit-unet</option>
                  <option value="attn">attn</option>
                </>
              )}
              {modelDir === "model_mask" && <option value="0106">0106</option>}
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-sm font-semibold text-slate-700">数据集</span>
            <select
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              value={dataset}
              onChange={(e) => setDataset(e.target.value as DatasetName)}
              disabled={running}
            >
              <option value="005_046">005_046</option>
              <option value="029_031">029_031</option>
              <option value="046_047">046_047</option>
              <option value="048_050">048_050</option>
            </select>
          </label>

          <label className="space-y-2">
            <span className="text-sm font-semibold text-slate-700">GPU IDs</span>
            <input
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              value={gpuIds}
              onChange={(e) => setGpuIds(e.target.value)}
              disabled={running}
            />
          </label>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={runPipeline}
            disabled={running}
            className="inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {running ? (
              <>
                <Spinner className="h-4 w-4" />
                生成中...
              </>
            ) : (
              <>
                <PlayIcon className="h-4 w-4" />
                开始生成 DICOM
              </>
            )}
          </button>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200/70 bg-slate-950 p-6 shadow-[0_16px_48px_rgba(15,23,42,0.12)]">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-200/80">
              Pipeline Log
            </div>
            <div className="mt-1 text-lg font-semibold text-white">执行输出</div>
          </div>
          {running && (
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-blue-100">
              <Spinner className="h-3.5 w-3.5" />
              Running
            </div>
          )}
        </div>

        <textarea
          id="pipeline-log"
          value={log}
          readOnly
          className="min-h-[420px] w-full rounded-2xl border border-white/10 bg-slate-900/80 p-4 font-mono text-sm leading-6 text-slate-100 outline-none"
        />
      </section>
    </div>
  );
}