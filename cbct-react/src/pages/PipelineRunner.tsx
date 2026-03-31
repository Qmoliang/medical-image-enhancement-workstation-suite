import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "";

type RunResponse = {
  cmd?: string;
  stdout?: string;
  returncode?: number;
  error?: string;
};

function unwrapApiPayload(parsed: any) {
  let cur = parsed;
  while (cur && typeof cur === "object" && cur.data && typeof cur.data === "object") {
    if (Array.isArray(cur.data)) break;
    if (cur.data === cur) break;
    cur = cur.data;
  }
  return cur;
}

async function postJson(path: string, body: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let parsed: any = null;
  try { parsed = text ? JSON.parse(text) : null; } catch { parsed = null; }
  if (!res.ok) throw new Error(parsed?.error || parsed?.message || text || `HTTP ${res.status}`);
  return unwrapApiPayload(parsed) as RunResponse;
}

export default function PipelineRunner() {
  const [modelDir, setModelDir] = useState("model_cstgan");
  const [modelKind, setModelKind] = useState("cstgan_c");
  const [dataset, setDataset] = useState("005_046");
  const [gpuIds, setGpuIds] = useState("0");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [progress, setProgress] = useState(0);
  const [log, setLog] = useState("");
  const [cmd, setCmd] = useState("");
  const [status, setStatus] = useState<"idle" | "success" | "error" | "running">("idle");
  const [toast, setToast] = useState<{type:"success"|"error"; message:string} | null>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<number | null>(null);

  const kinds = useMemo(() => {
    if (modelDir === "model_cstgan") return ["cstgan_c", "mb_taylor"];
    if (modelDir === "model_attn_vit") return ["vit-unet", "attn"];
    if (modelDir === "model_mask") return ["0106"];
    return [];
  }, [modelDir]);

  useEffect(() => {
    if (!kinds.includes(modelKind) && kinds.length) setModelKind(kinds[0]);
  }, [kinds, modelKind]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  useEffect(() => {
    if (loading || streaming) {
      setStatus("running");
      setProgress(8);
      timerRef.current = window.setInterval(() => {
        setProgress((p) => (p < 90 ? p + Math.random() * 6 + 2 : p));
      }, 400) as unknown as number;
    } else if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => { if (timerRef.current) window.clearInterval(timerRef.current); };
  }, [loading, streaming]);

  const payload = { modelDir: modelDir, modelKind: modelKind, datasetName: dataset, gpuIds: gpuIds };

  async function runModel() {
    setLoading(true);
    setToast(null);
    setLog("");
    setCmd("");
    try {
      const data = await postJson("/api/inference/run", payload);
      if (data?.error) throw new Error(String(data.error));
      setCmd(String(data.cmd || ""));
      setLog(String(data.stdout || ""));
      if (Number(data.returncode) === 0) {
        setStatus("success");
        setToast({ type: "success", message: "推理完成 ✅" });
      } else {
        setStatus("error");
        setToast({ type: "error", message: "执行失败，返回码 " + String(data.returncode) });
      }
    } catch (err: any) {
      setStatus("error");
      setLog(String(err?.message || err || "Unknown error"));
      setToast({ type: "error", message: "网络或后端错误，请检查 Spring 服务是否启动。" });
    } finally {
      setLoading(false);
      setProgress(100);
      setTimeout(() => setProgress(0), 900);
    }
  }

  async function runModelStream() {
    setStreaming(true);
    setToast(null);
    setLog("");
    setCmd("");
    try {
      const res = await fetch(`${API_BASE}/api/inference/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      if (!res.body) throw new Error("无法建立流式连接");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const line = block.split("\n").filter((x) => x.startsWith("data:")).map((x) => x.replace(/^data:\s?/, "")).join("\n");
          if (!line) continue;
          if (line === "__DONE__") {
            setStatus("success");
            setToast({ type: "success", message: "流式推理完成 ✅" });
            setStreaming(false);
            return;
          }
          if (line.startsWith("CMD: ")) setCmd(line.slice(5));
          else setLog((prev) => (prev ? prev + "\n" : "") + line);
        }
      }
      setStatus("success");
    } catch (e: any) {
      setStatus("error");
      setLog((prev) => prev + `${prev ? "\n" : ""}❌ 流式连接异常：${String(e?.message || e)}`);
      setToast({ type: "error", message: "流式推理失败" });
    } finally {
      setStreaming(false);
      setProgress(100);
      setTimeout(() => setProgress(0), 900);
    }
  }

  async function mergeData() {
    setLog("");
    setCmd("");
    setStatus("running");
    try {
      const data = await postJson("/api/inference/merge", payload);
      if (data?.error) throw new Error(String(data.error));
      setCmd(String(data.cmd || ""));
      setLog("执行命令:\n" + String(data.cmd || "") + "\n\n输出:\n" + String(data.stdout || ""));
      setStatus(Number(data.returncode) === 0 ? "success" : "error");
    } catch (err: any) {
      setLog("❌ 网络或服务器错误：" + String(err?.message || err));
      setStatus("error");
    }
  }

  return (
    <div className="page-shell text-slate-800">
      <TopBar />
      <section className="page-hero mb-8">
        <div className="page-eyebrow">Inference & Post-processing</div>
        <h1 className="page-title">CBCT→CT 推理与结果整理</h1>
        <p className="page-subtitle">已改为对接 Spring 后端接口，支持一次性推理、流式推理与 merge。</p>
        <div className="page-note-row">
          <span className="page-note-chip">/api/inference/run</span>
          <span className="page-note-chip">/api/inference/stream</span>
          <span className="page-note-chip">/api/inference/merge</span>
        </div>
      </section>
      <div className="mx-auto max-w-7xl">
        {status === "running" && <div className="mb-4"><ProgressBar value={progress} /></div>}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <section className="lg:col-span-4 rounded-3xl border border-slate-200/70 bg-white/90 p-1 shadow-[0_16px_48px_rgba(15,23,42,0.06)] backdrop-blur">
            <Card title="任务配置" subtitle="选择模型、数据集与执行设备">
              <Field label="模型目录"><Select value={modelDir} onChange={setModelDir} options={[{label:"model_cstgan", value:"model_cstgan"},{label:"model_attn_vit", value:"model_attn_vit"},{label:"model_mask", value:"model_mask"}]} /></Field>
              <Field label="模型类型"><Select value={modelKind} onChange={setModelKind} options={kinds.map(k => ({label:k, value:k}))} /></Field>
              <Field label="数据集"><Select value={dataset} onChange={setDataset} options={[{label:"005_046", value:"005_046"},{label:"029_031", value:"029_031"},{label:"048_050", value:"048_050"},{label:"046_047", value:"046_047"}]} /></Field>
              <Field label="GPU IDs"><Input value={gpuIds} onChange={setGpuIds} placeholder="0" /></Field>
              <div className="mt-4 flex items-center gap-3 flex-wrap">
                <RunButton onClick={runModel} loading={loading} />
                <button onClick={runModelStream} disabled={loading || streaming} className="inline-flex items-center justify-center gap-2 rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-70">{streaming ? <><Spinner className="h-4 w-4" />实时推理中...</> : <>启动流式推理</>}</button>
                <button onClick={mergeData} disabled={loading || streaming} className="inline-flex items-center justify-center gap-2 rounded-md bg-orange-500 px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-70">合并数据</button>
                <StatusBadge status={status} />
              </div>
            </Card>
            <Card className="mt-6" title="执行说明"><ul className="list-disc pl-5 text-sm text-slate-600 space-y-2"><li>Spring 负责接口与工程化；具体推理仍由 Python 脚本执行。</li><li>日志区可直接看到命令与标准输出。</li><li>method1 / method2 页面不再依赖 Flask。</li></ul></Card>
          </section>
          <section className="lg:col-span-8 space-y-6"><Card title="执行命令"><CodeBlock text={cmd || "尚未产生命令"} /></Card><Card className="mt-6" title="执行日志" subtitle="最新日志在底部，滚动区可复制粘贴"><LogViewer log={log} innerRef={logRef} /></Card></section>
        </div>
      </div>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}

function TopBar() { return <div className="sticky top-0 z-40 w-full border-b border-slate-200 bg-white/90 backdrop-blur"><div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3"><div className="flex items-center gap-3"><div className="h-8 w-8 rounded-lg bg-blue-600"></div><span className="text-sm font-medium text-slate-700">CBCT→CT 推理平台</span></div></div></div>; }
function Card({ title, subtitle, className = "", children }: {title?:string; subtitle?:string; className?:string; children:any}) { return <div className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>{(title || subtitle) && <div className="mb-4">{title && <h2 className="text-lg font-semibold text-slate-800">{title}</h2>}{subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}</div>}{children}</div>; }
function Field({ label, children }: {label:string; children:any}) { return <label className="block"><span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>{children}</label>; }
function Select({ value, onChange, options }:{value:string; onChange:(v:string)=>void; options:{label:string; value:string}[]}) { return <select className="mt-1 w-full rounded-md border border-slate-300 bg-white p-2 text-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200" value={value} onChange={(e)=>onChange(e.target.value)}>{options.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}</select>; }
function Input({ value, onChange, placeholder }:{value:string; onChange:(v:string)=>void; placeholder?:string}) { return <input className="mt-1 w-full rounded-md border border-slate-300 bg-white p-2 text-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-200" value={value} onChange={(e)=>onChange(e.target.value)} placeholder={placeholder} />; }
function RunButton({ onClick, loading }:{onClick:()=>void; loading:boolean}) { return <button onClick={onClick} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70">{loading ? <><Spinner className="h-4 w-4" />正在运行...</> : <>开始执行</>}</button>; }
function StatusBadge({ status }:{status:"idle"|"success"|"error"|"running"}) { const map = { idle: { text: "待命", color: "bg-slate-300" }, running: { text: "运行中", color: "bg-blue-500" }, success: { text: "成功", color: "bg-emerald-500" }, error: { text: "失败", color: "bg-rose-500" } } as const; const s = map[status]; return <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700"><span className={`h-2 w-2 rounded-full ${s.color} animate-pulse`} />{s.text}</div>; }
function ProgressBar({ value }:{value:number}) { return <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>; }
function CodeBlock({ text }:{text:string}) { return <pre className="max-h-48 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800"><code className="whitespace-pre-wrap break-all font-mono">{text}</code></pre>; }
function LogViewer({ log, innerRef }:{log:string; innerRef:any}) { const lines = useMemo(() => (log ? log.split(/\r?\n/) : []), [log]); return <div ref={innerRef} className="h-[520px] w-full overflow-auto rounded-lg border border-slate-800 bg-slate-900 p-3 text-[12px] leading-relaxed text-slate-200 shadow-inner">{lines.length === 0 ? <div className="text-slate-400">尚无日志输出</div> : <ul className="space-y-1">{lines.map((line, idx) => <li key={idx} className="font-mono"><span className="select-none text-slate-500">{String(idx + 1).padStart(3, "0")}</span><span className="mx-2 text-slate-700">|</span><span className={line.toLowerCase().includes("error") || line.toLowerCase().includes("exception") ? "text-rose-300" : line.toLowerCase().includes("warning") ? "text-amber-300" : "text-slate-200"}>{line || "\u00A0"}</span></li>)}</ul>}</div>; }
function Toast({ toast, onClose }:{toast: {type:"success"|"error"; message:string} | null; onClose:()=>void}) { useEffect(() => { if (!toast) return; const t = setTimeout(onClose, 3200); return () => clearTimeout(t); }, [toast, onClose]); if (!toast) return null; const color = toast.type === "success" ? "bg-emerald-600" : "bg-rose-600"; return <div className="fixed bottom-6 right-6 z-50"><div className={`flex items-center gap-3 rounded-lg ${color} px-4 py-3 text-white shadow-lg`}><span className="text-sm">{toast.message}</span><button className="ml-2 rounded p-1 hover:bg-white/20" onClick={onClose}>×</button></div></div>; }
function Spinner({ className="" }) { return <svg className={`animate-spin ${className}`} viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path></svg>; }
