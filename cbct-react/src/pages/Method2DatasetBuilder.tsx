import React, { useEffect, useMemo, useState } from "react";

type MatchItem = {
  cbctName: string;
  qactName: string;
  matchText: string;
};

type PatientMatches = {
  patientFolder: string;
  matches: MatchItem[];
};

type StepResult = {
  ok?: boolean;
  message?: string;
  summary?: Record<string, any>;
  generatedFiles?: string[];
  savedLocations?: Record<string, string>;
  preview?: any;
  patientParamsEntry?: Record<string, any>;
  patientRenameEntry?: Record<string, any>;
};

const cardStyle: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.18)",
  borderRadius: 24,
  padding: 24,
  background: "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.94) 100%)",
  boxShadow: "0 16px 48px rgba(15,23,42,0.06)",
  backdropFilter: "blur(10px)",
};
const labelStyle: React.CSSProperties = { fontSize: 12, color: "#475569", marginBottom: 8, display: "block", fontWeight: 700, letterSpacing: "0.02em" };
const inputStyle: React.CSSProperties = { width: "100%", border: "1px solid rgba(148, 163, 184, 0.32)", borderRadius: 16, padding: "12px 14px", fontSize: 14, boxSizing: "border-box", background: "rgba(248,250,252,0.9)", color: "#0f172a", outline: "none" };
const buttonStyle: React.CSSProperties = { border: "none", borderRadius: 16, padding: "12px 16px", cursor: "pointer", fontWeight: 700, fontSize: 14, boxShadow: "0 12px 24px rgba(15,23,42,0.08)" };
const primaryBtn: React.CSSProperties = { ...buttonStyle, background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)", color: "#fff" };
const successBtn: React.CSSProperties = { ...buttonStyle, background: "linear-gradient(135deg, #059669 0%, #047857 100%)", color: "#fff" };
const codeBox: React.CSSProperties = { background: "#020617", color: "#e2e8f0", borderRadius: 20, padding: 18, fontSize: 13, whiteSpace: "pre-wrap", overflowX: "auto", border: "1px solid rgba(148, 163, 184, 0.12)" };

async function api(path: string, body?: unknown) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let parsed: any = null;
  try { parsed = text ? JSON.parse(text) : null; } catch { parsed = null; }
  if (!res.ok) throw new Error(parsed?.error || parsed?.message || parsed?.traceback || text || `HTTP ${res.status}`);
  return parsed;
}

function JsonSummary({ value }: { value?: Record<string, any> }) {
  if (!value || Object.keys(value).length === 0) return null;
  return <div style={{ marginTop: 10 }}>{Object.entries(value).map(([k, v]) => <div key={k} style={{ marginBottom: 6, fontSize: 14, wordBreak: "break-all" }}><strong>{k}：</strong><span>{typeof v === "object" ? JSON.stringify(v) : String(v)}</span></div>)}</div>;
}

function FilesPanel({ title, files, locations }: { title: string; files?: string[]; locations?: Record<string, string> }) {
  return <div style={cardStyle}><div style={{ fontSize: 18, fontWeight: 800, marginBottom: 12, color: "#0f172a" }}>{title}</div>{files && files.length > 0 ? <><div style={{ fontWeight: 600, marginBottom: 8 }}>本步生成文件</div><ul style={{ paddingLeft: 18, marginTop: 0 }}>{files.map((f) => <li key={f} style={{ marginBottom: 6, wordBreak: "break-all" }}>{f}</li>)}</ul></> : <div style={{ color: "#64748b" }}>本步暂无文件清单</div>}{locations && Object.keys(locations).length > 0 && <div style={{ marginTop: 10 }}><div style={{ fontWeight: 600, marginBottom: 8 }}>保存位置</div>{Object.entries(locations).map(([k, v]) => <div key={k} style={{ marginBottom: 6, wordBreak: "break-all" }}><strong>{k}：</strong>{v}</div>)}</div>}</div>;
}

function StepCard(props: { title: string; description: string; children?: React.ReactNode }) {
  const parts = props.title.split("：");
  const step = parts[0];
  const label = parts.slice(1).join("：") || props.title;
  return <div style={{ ...cardStyle, marginBottom: 20 }}><div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", marginBottom: 10 }}><span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", padding: "6px 12px", borderRadius: 999, background: "rgba(37,99,235,0.08)", color: "#1d4ed8", fontSize: 12, fontWeight: 800, letterSpacing: "0.04em", textTransform: "uppercase" }}>{step}</span><div style={{ fontSize: 22, fontWeight: 800, color: "#0f172a" }}>{label}</div></div><div style={{ color: "#475569", lineHeight: 1.7, marginBottom: 16, maxWidth: 980 }}>{props.description}</div>{props.children}</div>;
}

export default function Method2DatasetBuilder() {
  const [sourceRoot, setSourceRoot] = useState(String.raw`G:\mimi0209\HeadNeck-selected`);
  const [workspaceRoot, setWorkspaceRoot] = useState(String.raw`G:\mimi0209\output-test`);
  const [matches, setMatches] = useState<PatientMatches[]>([]);
  const [matchedTxt, setMatchedTxt] = useState("");
  const [patientFolder, setPatientFolder] = useState("");
  const [matchText, setMatchText] = useState("");
  const [cbctName, setCbctName] = useState("");
  const [qactName, setQactName] = useState("");
  const [roiOptions, setRoiOptions] = useState<string[]>([]);
  const [roiName, setRoiName] = useState("");
  const [processedRawPath, setProcessedRawPath] = useState("");
  const [modelName, setModelName] = useState("mb_taylor");
  const [step1Result, setStep1Result] = useState<StepResult | null>(null);
  const [step2Result, setStep2Result] = useState<StepResult | null>(null);
  const [step3Result, setStep3Result] = useState<StepResult | null>(null);
  const [step4Result, setStep4Result] = useState<StepResult | null>(null);
  const [step5Result, setStep5Result] = useState<StepResult | null>(null);
  const [step6Result, setStep6Result] = useState<StepResult | null>(null);
  const [busy, setBusy] = useState("");
  const [logs, setLogs] = useState("");

  useEffect(() => { (async () => { try { const d = await api("/api/method2/defaults"); if (d?.sourceRoot) setSourceRoot(d.sourceRoot); if (d?.workspaceRoot) setWorkspaceRoot(d.workspaceRoot); } catch {} })(); }, []);

  const selectedPatient = useMemo(() => matches.find((m) => m.patientFolder === patientFolder), [matches, patientFolder]);
  const selectedMatch = useMemo(() => selectedPatient?.matches.find((m) => m.matchText === matchText), [selectedPatient, matchText]);
  useEffect(() => {
    if (selectedMatch) {
      setCbctName(selectedMatch.cbctName);
      setQactName(selectedMatch.qactName);
    }
  }, [selectedMatch]);
  useEffect(() => {
    if (workspaceRoot && patientFolder && cbctName) {
      setProcessedRawPath(`${workspaceRoot}\\${patientFolder}\\registrated_data\\cbct_${cbctName}.raw`);
    }
  }, [workspaceRoot, patientFolder, cbctName]);

  const payloadBase = { sourceRoot, workspaceRoot, patientFolder, matchText, cbctName, qactName };

  async function runMatch() {
    setBusy("match");
    setLogs("===== Run Match =====\n");
    try {
      const res = await api("/api/method2/run_match", { sourceRoot, workspaceRoot });
      setMatches(res.matches || []);
      setMatchedTxt(res.matchedTxt || "");
      if (res.matches?.length) {
        setPatientFolder(res.matches[0].patientFolder);
        const m = res.matches[0].matches?.[0];
        if (m) {
          setMatchText(m.matchText);
          setCbctName(m.cbctName);
          setQactName(m.qactName);
        }
      }
      setLogs((prev) => prev + (res.message || "Run Match 完成") + "\n");
    } catch (e: any) {
      setLogs((prev) => prev + "===== Run Match Error =====\n" + String(e?.message || e) + "\n");
    } finally { setBusy(""); }
  }

  async function loadRoiOptions() { setBusy("roi"); try { const res = await api("/api/method2/roi_options", payloadBase); setRoiOptions(res.roiOptions || []); if ((res.roiOptions || []).length && !roiName) setRoiName(res.roiOptions[0]); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }
  async function runStep1() { setBusy("step1"); try { const res = await api("/api/method2/step1", payloadBase); setStep1Result(res); setLogs((p)=>p+(res.message||"Step 1 完成")+"\n"); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }
  async function runStep2() { setBusy("step2"); try { const res = await api("/api/method2/step2", { ...payloadBase, roiName }); setStep2Result(res); setLogs((p)=>p+(res.message||"Step 2 完成")+"\n"); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }
  async function runStep3() { setBusy("step3"); try { const res = await api("/api/method2/step3", payloadBase); setStep3Result(res); setLogs((p)=>p+(res.message||"Step 3 完成")+"\n"); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }
  async function runStep4() { setBusy("step4"); try { const res = await api("/api/method2/step4", payloadBase); setStep4Result(res); setLogs((p)=>p+(res.message||"Step 4 完成")+"\n"); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }
  async function runStep5() { setBusy("step5"); try { const res = await api("/api/method2/step5", { ...payloadBase, processedRawPath }); setStep5Result(res); setLogs((p)=>p+(res.message||"Step 5 完成")+"\n"); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }
  async function runStep6() { setBusy("step6"); try { const res = await api("/api/method2/step6", { ...payloadBase, modelName }); setStep6Result(res); setLogs((p)=>p+(res.message||"Step 6 完成")+"\n"); } catch (e:any){ setLogs((p)=>p+String(e?.message||e)+"\n"); } finally { setBusy(""); } }

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div style={cardStyle}>
        <div style={{ fontSize: 28, fontWeight: 900, color: "#0f172a", marginBottom: 8 }}>基于 SITK 的 CBCT/CT 数据集制作流程</div>
        <div style={{ color: "#475569", lineHeight: 1.7 }}>方法二沿用 match → raw → ROI → SITK registration → transform1212 → 回插验证 → JSON 参数总结 的流程，默认在 G 盘的 output-test 中完成全部生成。</div>
      </div>

      <StepCard title="Step 0：匹配与任务选择" description="指定 G 盘数据源与 output-test 工作目录，运行匹配并选择病人与一条 CBCT/QACT 对应关系。">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div><label style={labelStyle}>数据源根目录</label><input style={inputStyle} value={sourceRoot} onChange={(e)=>setSourceRoot(e.target.value)} /></div>
          <div><label style={labelStyle}>工作输出根目录（仅写 output-test）</label><input style={inputStyle} value={workspaceRoot} onChange={(e)=>setWorkspaceRoot(e.target.value)} /></div>
        </div>
        <div style={{ marginTop: 16 }}><button style={primaryBtn} onClick={runMatch} disabled={busy !== ""}>运行 Match</button></div>
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16, marginTop: 16 }}>
          <div><label style={labelStyle}>病人</label><select style={inputStyle} value={patientFolder} onChange={(e)=>{ setPatientFolder(e.target.value); setMatchText(""); }}><option value="">请选择</option>{matches.map((m)=><option key={m.patientFolder} value={m.patientFolder}>{m.patientFolder}</option>)}</select></div>
          <div><label style={labelStyle}>匹配条目</label><select style={inputStyle} value={matchText} onChange={(e)=>setMatchText(e.target.value)}><option value="">请选择</option>{(selectedPatient?.matches || []).map((m)=><option key={m.matchText} value={m.matchText}>{m.matchText}</option>)}</select></div>
        </div>
        <div style={{ marginTop: 16, color: "#64748b", fontSize: 14 }}>matched_folders.txt：{matchedTxt || "尚未生成"}</div>
      </StepCard>

      <StepCard title="Step 1：DICOM → raw" description="复用与方法一相同的 dcm_to_raw，将匹配到的 CBCT/QACT 转为 raw，并生成 interpolated_CBCT_b_spline.raw。">
        <button style={primaryBtn} onClick={runStep1} disabled={busy !== "" || !matchText}>执行 Step 1</button>
        {step1Result && <><JsonSummary value={step1Result.summary} /><div style={{ marginTop: 16 }}><FilesPanel title="Step 1 输出" files={step1Result.generatedFiles} locations={step1Result.savedLocations} /></div></>}
      </StepCard>

      <StepCard title="Step 2：提取 ROI / Patient mask" description="复用与方法一相同的 ROI 提取逻辑，先加载 ROI 列表，再选择一个 ROI，同时自动生成 Patient mask。">
        <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
          <div style={{ minWidth: 240 }}><label style={labelStyle}>ROI</label><select style={inputStyle} value={roiName} onChange={(e)=>setRoiName(e.target.value)}><option value="">请选择</option>{roiOptions.map((r)=><option key={r} value={r}>{r}</option>)}</select></div>
          <button style={successBtn} onClick={loadRoiOptions} disabled={busy !== "" || !step1Result}>加载 ROI 列表</button>
          <button style={primaryBtn} onClick={runStep2} disabled={busy !== "" || !roiName}>执行 Step 2</button>
        </div>
        {step2Result && <><JsonSummary value={step2Result.summary} /><div style={{ marginTop: 16 }}><FilesPanel title="Step 2 输出" files={step2Result.generatedFiles} locations={step2Result.savedLocations} /></div></>}
      </StepCard>

      <StepCard title="Step 3：SITK 配准" description="使用 registrator.py 的逻辑，以 QACT 为 moving，interpolated CBCT 为 fixed，用 Step 1 中的 CT spacing 作为 SimpleITK spacing，输出注册后的 CT 和 mask。">
        <button style={primaryBtn} onClick={runStep3} disabled={busy !== "" || !step2Result}>执行 Step 3</button>
        {step3Result && <><JsonSummary value={step3Result.summary} /><div style={{ marginTop: 16 }}><FilesPanel title="Step 3 输出" files={step3Result.generatedFiles} locations={step3Result.savedLocations} /></div></>}
      </StepCard>

      <StepCard title="Step 4：transform1212 生成最终数据集" description="根据注册后的 Patient mask 质心计算 Computed Shift，并对 registered CT / CBCT / ROI mask 一起 centered，生成最终 raw 与 2D slices。">
        <button style={primaryBtn} onClick={runStep4} disabled={busy !== "" || !step3Result}>执行 Step 4</button>
        {step4Result && <><JsonSummary value={step4Result.summary} /><div style={{ marginTop: 16 }}><FilesPanel title="Step 4 输出" files={step4Result.generatedFiles} locations={step4Result.savedLocations} /></div>{step4Result.preview && <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}><div style={cardStyle}><div style={{ fontWeight: 700, marginBottom: 12 }}>CBCT Slice {step4Result.preview.sliceIndex}</div><img src={step4Result.preview.cbctPng} alt="cbct" style={{ width: "100%", display: "block", background: "#000", borderRadius: 16 }} /></div><div style={cardStyle}><div style={{ fontWeight: 700, marginBottom: 12 }}>CT Slice {step4Result.preview.sliceIndex}</div><img src={step4Result.preview.ctPng} alt="ct" style={{ width: "100%", display: "block", background: "#000", borderRadius: 16 }} /></div></div>}</>}
      </StepCard>

      <StepCard title="Step 5：回插验证" description="默认使用 Step 4 刚生成的 centered CBCT raw 作为待回插图像，验证方法二的 centered 结果是否可以正确插回原始 interpolated_CBCT_b_spline.raw。">
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 16, alignItems: "end" }}>
          <div><label style={labelStyle}>待回插 256/512 raw 路径</label><input style={inputStyle} value={processedRawPath} onChange={(e)=>setProcessedRawPath(e.target.value)} /></div>
          <button style={primaryBtn} onClick={runStep5} disabled={busy !== "" || !step4Result}>执行 Step 5</button>
        </div>
        {step5Result && <><JsonSummary value={step5Result.summary} /><div style={{ marginTop: 16 }}><FilesPanel title="Step 5 输出" files={step5Result.generatedFiles} locations={step5Result.savedLocations} /></div>{step5Result.preview && <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}><div style={cardStyle}><div style={{ fontWeight: 700, marginBottom: 12 }}>原始 CBCT Slice {step5Result.preview.sliceIndex}</div><img src={step5Result.preview.cbctOriginalPng} alt="orig" style={{ width: "100%", display: "block", background: "#000", borderRadius: 16 }} /></div><div style={cardStyle}><div style={{ fontWeight: 700, marginBottom: 12 }}>待回插图像 Slice {step5Result.preview.sliceIndex}</div><img src={step5Result.preview.processedPng} alt="proc" style={{ width: "100%", display: "block", background: "#000", borderRadius: 16 }} /></div><div style={cardStyle}><div style={{ fontWeight: 700, marginBottom: 12 }}>回插后预览 Slice {step5Result.preview.sliceIndex}</div><img src={step5Result.preview.reinsertedPng} alt="reins" style={{ width: "100%", display: "block", background: "#000", borderRadius: 16 }} /></div></div>}</>}
      </StepCard>

      <StepCard title="Step 6：生成 JSON 建议条目" description="根据方法二的 centered / 回插逻辑，总结出 patient_params.json 和按模型名区分的 Patient_rename.json 建议条目，供你手动复制到正式配置文件中。">
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 16, alignItems: "end" }}>
          <div><label style={labelStyle}>模型名</label><input style={inputStyle} value={modelName} onChange={(e)=>setModelName(e.target.value)} /></div>
          <button style={primaryBtn} onClick={runStep6} disabled={busy !== "" || !step4Result}>执行 Step 6</button>
        </div>
        {step6Result && <div style={{ display: "grid", gap: 16, marginTop: 16 }}><FilesPanel title="Step 6 摘要" files={step6Result.generatedFiles} locations={step6Result.savedLocations} /><div style={cardStyle}><div style={{ fontWeight: 800, marginBottom: 12 }}>patient_params.json 建议条目</div><pre style={codeBox}>{JSON.stringify(step6Result.patientParamsEntry || {}, null, 2)}</pre></div><div style={cardStyle}><div style={{ fontWeight: 800, marginBottom: 12 }}>Patient_rename.json 建议条目</div><pre style={codeBox}>{JSON.stringify(step6Result.patientRenameEntry || {}, null, 2)}</pre></div></div>}
      </StepCard>

      <div style={cardStyle}><div style={{ fontSize: 18, fontWeight: 800, marginBottom: 12 }}>执行日志</div><div style={codeBox}>{logs || "尚无日志"}</div></div>
    </div>
  );
}
