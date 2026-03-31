
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
  preview?: {
    sliceIndex: number;
    windowLevel: number;
    windowWidth: number;
    cbctPng: string;
    ctPng: string;
  };
};

const cardStyle: React.CSSProperties = {
  border: "1px solid rgba(148, 163, 184, 0.18)",
  borderRadius: 24,
  padding: 24,
  background: "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.94) 100%)",
  boxShadow: "0 16px 48px rgba(15,23,42,0.06)",
  backdropFilter: "blur(10px)",
};

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "#475569",
  marginBottom: 8,
  display: "block",
  fontWeight: 700,
  letterSpacing: "0.02em",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid rgba(148, 163, 184, 0.32)",
  borderRadius: 16,
  padding: "12px 14px",
  fontSize: 14,
  boxSizing: "border-box",
  background: "rgba(248,250,252,0.9)",
  color: "#0f172a",
  outline: "none",
};

const buttonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: 16,
  padding: "12px 16px",
  cursor: "pointer",
  fontWeight: 700,
  fontSize: 14,
  boxShadow: "0 12px 24px rgba(15,23,42,0.08)",
};

const primaryBtn: React.CSSProperties = {
  ...buttonStyle,
  background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
  color: "#fff",
};

const successBtn: React.CSSProperties = {
  ...buttonStyle,
  background: "linear-gradient(135deg, #059669 0%, #047857 100%)",
  color: "#fff",
};

const mutedBtn: React.CSSProperties = {
  ...buttonStyle,
  background: "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)",
  color: "#334155",
  border: "1px solid rgba(148, 163, 184, 0.24)",
};

const codeBox: React.CSSProperties = {
  background: "#020617",
  color: "#e2e8f0",
  borderRadius: 20,
  padding: 18,
  fontSize: 13,
  whiteSpace: "pre-wrap",
  overflowX: "auto",
  border: "1px solid rgba(148, 163, 184, 0.12)",
};

async function api(path: string, body?: unknown) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await res.text();
  let parsed: any = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = null;
  }

  if (!res.ok) {
    throw new Error(parsed?.error || parsed?.message || parsed?.traceback || text || `HTTP ${res.status}`);
  }
  return parsed;
}

function JsonSummary({ value }: { value?: Record<string, any> }) {
  if (!value || Object.keys(value).length === 0) return null;
  return (
    <div style={{ marginTop: 10 }}>
      {Object.entries(value).map(([k, v]) => (
        <div key={k} style={{ marginBottom: 6, fontSize: 14 }}>
          <strong>{k}：</strong>
          <span>{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
        </div>
      ))}
    </div>
  );
}

function FilesPanel({ title, files, locations }: { title: string; files?: string[]; locations?: Record<string, string> }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 12, color: "#0f172a" }}>{title}</div>
      {files && files.length > 0 ? (
        <>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>本步生成文件</div>
          <ul style={{ paddingLeft: 18, marginTop: 0 }}>
            {files.map((f) => (
              <li key={f} style={{ marginBottom: 6, wordBreak: "break-all" }}>{f}</li>
            ))}
          </ul>
        </>
      ) : (
        <div style={{ color: "#64748b" }}>本步暂无文件清单</div>
      )}
      {locations && Object.keys(locations).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>保存位置</div>
          {Object.entries(locations).map(([k, v]) => (
            <div key={k} style={{ marginBottom: 6, wordBreak: "break-all" }}>
              <strong>{k}：</strong>{v}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StepCard(props: {
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  const parts = props.title.split("：");
  const step = parts[0];
  const label = parts.slice(1).join("：") || props.title;
  return (
    <div style={{ ...cardStyle, marginBottom: 20 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", marginBottom: 10 }}>
        <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", padding: "6px 12px", borderRadius: 999, background: "rgba(37,99,235,0.08)", color: "#1d4ed8", fontSize: 12, fontWeight: 800, letterSpacing: "0.04em", textTransform: "uppercase" }}>{step}</span>
        <div style={{ fontSize: 22, fontWeight: 800, color: "#0f172a" }}>{label}</div>
      </div>
      <div style={{ color: "#475569", lineHeight: 1.7, marginBottom: 16, maxWidth: 980 }}>{props.description}</div>
      {props.children}
    </div>
  );
}

export default function Method1DatasetBuilder() {
  const [sourceRoot, setSourceRoot] = useState(String.raw`F:\mimi0209\HeadNeck-selected`);
  const [workspaceRoot, setWorkspaceRoot] = useState(String.raw`F:\mimi0209\output-test`);

  const [matches, setMatches] = useState<PatientMatches[]>([]);
  const [matchedTxt, setMatchedTxt] = useState("");
  const [patientFolder, setPatientFolder] = useState("");
  const [matchText, setMatchText] = useState("");
  const [cbctName, setCbctName] = useState("");
  const [qactName, setQactName] = useState("");

  const [roiOptions, setRoiOptions] = useState<string[]>([]);
  const [roiName, setRoiName] = useState("");

  const [shift, setShift] = useState("108");
  const [cbctYExtra, setCbctYExtra] = useState("44");
  const [ctYShift, setCtYShift] = useState("50");
  const [applyCtMask, setApplyCtMask] = useState(false);

  const [step1Result, setStep1Result] = useState<StepResult | null>(null);
  const [step2Result, setStep2Result] = useState<StepResult | null>(null);
  const [step3Result, setStep3Result] = useState<StepResult | null>(null);
  const [step4Result, setStep4Result] = useState<StepResult | null>(null);
  const [step5Result, setStep5Result] = useState<any | null>(null);
  const [step6Result, setStep6Result] = useState<any | null>(null);

  const [processedRawPath, setProcessedRawPath] = useState("");
  const [modelName, setModelName] = useState("mb_taylor");

  const [busy, setBusy] = useState<string>("");
  const [logs, setLogs] = useState<string>("");
  const getDefaultProcessedRawPath = () => {
    if (!workspaceRoot || !patientFolder || !cbctName) return "";
    return `${workspaceRoot}\\${patientFolder}\\${cbctName}\\interpolated_CBCT_b_spline_centered.raw`;
  };

  const selectedPatient = useMemo(
    () => matches.find((m) => m.patientFolder === patientFolder),
    [matches, patientFolder]
  );

  useEffect(() => {
    api("/api/method1/defaults")
      .then((d) => {
        if (d?.sourceRoot) setSourceRoot(d.sourceRoot);
        if (d?.workspaceRoot) setWorkspaceRoot(d.workspaceRoot);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!matchText) {
      setCbctName("");
      setQactName("");
      return;
    }
    const hit = selectedPatient?.matches.find((m) => m.matchText === matchText);
    if (hit) {
      setCbctName(hit.cbctName);
      setQactName(hit.qactName);
    }
  }, [matchText, selectedPatient]);

  const appendLog = (text: string) => {
    setLogs((prev) => `${prev}${prev ? "\n" : ""}${text}`);
  };

  const payloadBase = {
    sourceRoot,
    workspaceRoot,
    patientFolder,
    cbctName,
    qactName,
    matchText,
  };

  const runMatch = async () => {
    try {
      setBusy("match");
      appendLog("===== Run Match =====");
      const res = await api("/api/method1/run_match", { sourceRoot, workspaceRoot });
      setMatches(res.matches || []);
      setMatchedTxt(res.matchedTxt || "");
      appendLog(res.message || "Run Match 完成");
    } catch (e: any) {
      appendLog("===== Run Match Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  const runStep1 = async () => {
    try {
      setBusy("step1");
      appendLog("===== Step 1 =====");
      const res = await api("/api/method1/step1", payloadBase);
      setStep1Result(res);
      appendLog(res.message || "Step 1 完成");
      setRoiOptions([]);
      setRoiName("");
      setStep2Result(null);
      setStep3Result(null);
      setStep4Result(null);
      setStep5Result(null);
      setStep6Result(null);
      setProcessedRawPath("");
    } catch (e: any) {
      appendLog("===== Step 1 Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  const loadRois = async () => {
    try {
      setBusy("roi");
      appendLog("===== Load ROI Options =====");
      const res = await api("/api/method1/roi_options", payloadBase);
      const opts = res.roiOptions || [];
      setRoiOptions(opts);
      if (opts.length > 0) setRoiName((prev) => prev || opts[0]);
      appendLog(`加载 ROI 列表成功，共 ${opts.length} 个`);
    } catch (e: any) {
      appendLog("===== Load ROI Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  const runStep2 = async () => {
    try {
      setBusy("step2");
      appendLog("===== Step 2 =====");
      const res = await api("/api/method1/step2", { ...payloadBase, roiName });
      setStep2Result(res);
      appendLog(res.message || "Step 2 完成");
    } catch (e: any) {
      appendLog("===== Step 2 Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  const runStep3 = async () => {
    try {
      setBusy("step3");
      appendLog("===== Step 3 =====");
      const res = await api("/api/method1/step3", payloadBase);
      setStep3Result(res);
      const recommended = String(res?.summary?.recommendedShift ?? "108");
      setShift(recommended);
      appendLog(res.message || "Step 3 完成");
    } catch (e: any) {
      appendLog("===== Step 3 Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };



  const runStep5 = async () => {
    try {
      setBusy("step5");
      appendLog("===== Step 5 =====");
      const res = await api("/api/method1/step5", {
        ...payloadBase,
        shift: Number(shift),
        cbctYExtra: Number(cbctYExtra),
        processedRawPath: processedRawPath || undefined,
      });
      setStep5Result(res);
      appendLog(res.message || "Step 5 完成");
    } catch (e: any) {
      appendLog("===== Step 5 Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  const runStep6 = async () => {
    try {
      setBusy("step6");
      appendLog("===== Step 6 =====");
      const res = await api("/api/method1/step6", {
        ...payloadBase,
        shift: Number(shift),
        cbctYExtra: Number(cbctYExtra),
        modelName,
      });
      setStep6Result(res);
      appendLog(res.message || "Step 6 完成");
    } catch (e: any) {
      appendLog("===== Step 6 Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  const runStep4 = async () => {
    try {
      setBusy("step4");
      appendLog("===== Step 4 =====");
      const res = await api("/api/method1/step4", {
        ...payloadBase,
        shift: Number(shift),
        cbctYExtra: Number(cbctYExtra),
        ctYShift: Number(ctYShift),
        applyCtMask,
      });
      setStep4Result(res);
      setStep5Result(null);
      setStep6Result(null);
      setProcessedRawPath(getDefaultProcessedRawPath());
      appendLog(res.message || "Step 4 完成");
    } catch (e: any) {
      appendLog("===== Step 4 Error =====");
      appendLog(String(e?.message || e));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="page-shell" style={{ minHeight: "100%" }}>
      <section className="page-hero">
        <div className="page-eyebrow">ORB Dataset Workflow</div>
        <h1 className="page-title">基于 ORB 的数据集制作</h1>
        <div className="page-subtitle">用于训练前的数据集对齐与制作。保留现有 Step 0–6 的全部参数、按钮与接口行为，只优化页面的布局、层级与展示方式。</div>
        <div className="page-note-row">
          <span className="page-note-chip">工作输出目录仅使用 output-test</span>
          <span className="page-note-chip">Step 4 预览保持 WL=-300 / WW=1500</span>
          <span className="page-note-chip">现有工作流逻辑不变</span>
        </div>
      </section>

      <StepCard
        title="Step 0：运行 Match 并选择病人 / 配对"
        description="先指定数据源根目录与工作输出根目录。运行 Match 后，系统会扫描 HeadNeck-selected 下的病人文件夹，自动找到同一天的 CBCT / QACT 配对，并生成 matched_folders.txt 供你逐条选择。"
      >
        <div style={{ display: "grid", gridTemplateColumns: "minmax(320px, 1fr) minmax(320px, 1fr)", gap: 14, marginBottom: 14 }}>
          <div>
            <label style={labelStyle}>数据源根目录</label>
            <input style={inputStyle} value={sourceRoot} onChange={(e) => setSourceRoot(e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>工作输出根目录</label>
            <input style={inputStyle} value={workspaceRoot} onChange={(e) => setWorkspaceRoot(e.target.value)} />
          </div>
        </div>
        <button style={primaryBtn} onClick={runMatch} disabled={busy !== ""}>
          {busy === "match" ? "运行中..." : "1. 运行 Match"}
        </button>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(320px, 1fr) minmax(320px, 1fr)", gap: 14, marginTop: 18 }}>
          <div>
            <label style={labelStyle}>选择病人</label>
            <select
              style={inputStyle}
              value={patientFolder}
              onChange={(e) => {
                setPatientFolder(e.target.value);
                setMatchText("");
              }}
            >
              <option value="">请选择</option>
              {matches.map((m) => (
                <option key={m.patientFolder} value={m.patientFolder}>
                  {m.patientFolder}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label style={labelStyle}>选择 Match</label>
            <select style={inputStyle} value={matchText} onChange={(e) => setMatchText(e.target.value)}>
              <option value="">请选择</option>
              {(selectedPatient?.matches || []).map((m) => (
                <option key={m.matchText} value={m.matchText}>
                  {m.matchText}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginTop: 14, color: "#334155", lineHeight: 1.6 }}>
          <div><strong>matched_folders.txt：</strong>{matchedTxt || "尚未生成"}</div>
          {cbctName && qactName && (
            <div style={{ marginTop: 8 }}>
              <strong>当前选择：</strong>{patientFolder} / {cbctName} ↔ {qactName}
            </div>
          )}
        </div>
      </StepCard>

      <StepCard
        title="Step 1：DICOM → raw 与插值"
        description="这一步会读取当前选择的 CBCT / QACT DICOM 序列，生成原始 raw 文件，并将 CBCT 根据 QACT 的 pixel spacing / slice thickness 做插值，得到 interpolated_CBCT_b_spline.raw。生成后的数值信息和文件位置会显示在下方。"
      >
        <button
          style={primaryBtn}
          onClick={runStep1}
          disabled={busy !== "" || !patientFolder || !matchText}
        >
          {busy === "step1" ? "执行中..." : "2. 执行 Step 1"}
        </button>

        {step1Result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{step1Result.message}</div>
            <JsonSummary value={step1Result.summary} />
            <div style={{ marginTop: 14 }}>
              <FilesPanel title="Step 1 产物与位置" files={step1Result.generatedFiles} locations={step1Result.savedLocations} />
            </div>
          </div>
        )}
      </StepCard>

      <StepCard
        title="Step 2：选择 ROI 并生成中间 mask"
        description="必须先完成 Step 1。然后点击“加载 ROI 列表”，系统会读取当前 match 对应的 RT Structure，提供可选 ROI 下拉框。你只需要选择一个 ROI，系统会同时默认生成 Patient 的 mask。该步生成的是中间文件，后续病人可能会覆盖。"
      >
        <div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}>
          <button style={mutedBtn} onClick={loadRois} disabled={busy !== "" || !step1Result}>
            {busy === "roi" ? "加载中..." : "加载 ROI 列表"}
          </button>
          <div style={{ minWidth: 280 }}>
            <label style={labelStyle}>ROI 选择</label>
            <select
              style={inputStyle}
              value={roiName}
              onChange={(e) => setRoiName(e.target.value)}
              disabled={!step1Result || roiOptions.length === 0}
            >
              <option value="">请选择 ROI</option>
              {roiOptions.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <button
            style={primaryBtn}
            onClick={runStep2}
            disabled={busy !== "" || !step1Result || !roiName}
          >
            {busy === "step2" ? "执行中..." : "3. 执行 Step 2"}
          </button>
        </div>

        {step2Result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{step2Result.message}</div>
            <JsonSummary value={step2Result.summary} />
            <div style={{ marginTop: 14 }}>
              <FilesPanel title="Step 2 中间文件与位置" files={step2Result.generatedFiles} locations={step2Result.savedLocations} />
            </div>
          </div>
        )}
      </StepCard>

      <StepCard
        title="Step 3：slice shift 检测"
        description="这一步会比较 CBCT 与 CT 的 slice 对应关系，估计一个推荐 shift（差值众数），供 Step 4 使用。你仍然可以在 Step 4 里手工修改。"
      >
        <button
          style={primaryBtn}
          onClick={runStep3}
          disabled={busy !== "" || !step1Result}
        >
          {busy === "step3" ? "执行中..." : "4. 执行 Step 3"}
        </button>

        {step3Result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{step3Result.message}</div>
            <JsonSummary value={step3Result.summary} />
            <div style={{ marginTop: 14 }}>
              <FilesPanel title="Step 3 输出摘要" files={step3Result.generatedFiles} locations={step3Result.savedLocations} />
            </div>
          </div>
        )}
      </StepCard>

      <StepCard
        title="Step 4：手动微调并生成最终数据集"
        description="这一步使用 Step 3 推荐的 shift 和你手工指定的微调参数，生成 centered / cropped / mask raw，以及最终的 2D 数据集。CBCT 文件夹里保存的是把 interpolated_CBCT_b_spline_centered.raw 按 slice 拆开的 raw 文件；完成后会展示 CBCT 与 CT 的第 70 张 slice，按 WL=-300 / WW=1500 并排预览，方便你判断对齐是否正确。"
      >
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
          <div>
            <label style={labelStyle}>shift</label>
            <input style={inputStyle} value={shift} onChange={(e) => setShift(e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>CBCT Y extra</label>
            <input style={inputStyle} value={cbctYExtra} onChange={(e) => setCbctYExtra(e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>CT / Mask Y shift</label>
            <input style={inputStyle} value={ctYShift} onChange={(e) => setCtYShift(e.target.value)} />
          </div>
        </div>

        <div style={{ marginTop: 14, ...cardStyle, background: "#f8fafc", boxShadow: "none" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={applyCtMask}
              onChange={(e) => setApplyCtMask(e.target.checked)}
            />
            对 CT 应用 Patient mask（默认不勾选）
          </label>
          <div style={{ color: "#475569", marginTop: 8, lineHeight: 1.6 }}>
            Patient mask 来源于 CT，不对应 CBCT。训练和测试时建议整套数据统一选择 masked CT 或 unmasked CT。
            当前选项只影响 Step 4 最终用于生成 <code>QACT_*_centered.raw</code>、<code>QACT_*_cropped_centered.raw</code> 和 2D CT 图像的数据来源。
            无论是否勾选，系统都会额外保存一份 <code>QACT_*_Patientmasked.raw</code> 作为参考文件。
          </div>
        </div>

        <div style={{ marginTop: 14 }}>
          <button
            style={successBtn}
            onClick={runStep4}
            disabled={busy !== "" || !step1Result || !step2Result}
          >
            {busy === "step4" ? "执行中..." : "5. 执行 Step 4 并生成预览"}
          </button>
        </div>

        {step4Result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{step4Result.message}</div>
            <JsonSummary value={step4Result.summary} />
            <div style={{ marginTop: 14 }}>
              <FilesPanel title="Step 4 产物与位置" files={step4Result.generatedFiles} locations={step4Result.savedLocations} />
            </div>

            {step4Result.preview && (
              <div style={{ marginTop: 18 }}>
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>
                  Slice {step4Result.preview.sliceIndex} 预览（WL={step4Result.preview.windowLevel} / WW={step4Result.preview.windowWidth}）
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(320px, 1fr) minmax(320px, 1fr)",
                    gap: 16,
                    alignItems: "start",
                  }}
                >
                  <div style={{ ...cardStyle, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>CBCT Slice</div>
                    <img
                      src={step4Result.preview.cbctPng}
                      alt="CBCT preview"
                      style={{
                        width: "100%",
                        maxHeight: 420,
                        objectFit: "contain",
                        display: "block",
                        borderRadius: 10,
                        background: "#0f172a",
                      }}
                    />
                  </div>
                  <div style={{ ...cardStyle, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>CT Slice</div>
                    <img
                      src={step4Result.preview.ctPng}
                      alt="CT preview"
                      style={{
                        width: "100%",
                        maxHeight: 420,
                        objectFit: "contain",
                        display: "block",
                        borderRadius: 10,
                        background: "#0f172a",
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </StepCard>



      <StepCard
        title="Step 5：回插验证"
        description="这一步默认使用 Step 4 生成的 interpolated_CBCT_b_spline_centered.raw，先取其 128:384 的 centered 区域，再按照当前 Step 4 参数自动反推出 offset，并将这个 256×256 区域回插到原始 interpolated_CBCT_b_spline.raw；如果你传入的是 fake_B.raw 这类 256×256 raw，则会直接按同一 offset 回插。"
      >
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
          <div>
            <label style={labelStyle}>待回插 raw 路径（默认使用 Step 4 生成的 interpolated_CBCT_b_spline_centered.raw）</label>
            <input style={inputStyle} value={processedRawPath || getDefaultProcessedRawPath()} onChange={(e) => setProcessedRawPath(e.target.value)} placeholder={getDefaultProcessedRawPath() || `${workspaceRoot}\\${patientFolder || 'HNxxx'}\\${cbctName || 'CBCT_xxx'}\\interpolated_CBCT_b_spline_centered.raw`} />
          </div>
        </div>
        <div style={{ marginTop: 14 }}>
          <button style={successBtn} onClick={runStep5} disabled={busy !== "" || !step4Result}>
            {busy === "step5" ? "执行中..." : "6. 执行 Step 5 回插验证"}
          </button>
        </div>

        {step5Result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{step5Result.message}</div>
            <JsonSummary value={step5Result.summary} />
            <div style={{ marginTop: 14 }}>
              <FilesPanel title="Step 5 产物与位置" files={step5Result.generatedFiles} locations={step5Result.savedLocations} />
            </div>
            {step5Result.preview && (
              <div style={{ marginTop: 18 }}>
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>
                  Slice {step5Result.preview.sliceIndex} 回插验证预览（WL={step5Result.preview.windowLevel} / WW={step5Result.preview.windowWidth}）
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 1fr) minmax(260px, 1fr) minmax(260px, 1fr)", gap: 16, alignItems: "start" }}>
                  <div style={{ ...cardStyle, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>原始 interpolated CBCT</div>
                    <img src={step5Result.preview.originalPng} alt="Original preview" style={{ width: "100%", maxHeight: 360, objectFit: "contain", display: "block", borderRadius: 10, background: "#0f172a" }} />
                  </div>
                  <div style={{ ...cardStyle, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>待回插 256×256</div>
                    <img src={step5Result.preview.processedPng} alt="Processed preview" style={{ width: "100%", maxHeight: 360, objectFit: "contain", display: "block", borderRadius: 10, background: "#0f172a" }} />
                  </div>
                  <div style={{ ...cardStyle, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>回插后预览</div>
                    <img src={step5Result.preview.reinsertedPng} alt="Reinserted preview" style={{ width: "100%", maxHeight: 360, objectFit: "contain", display: "block", borderRadius: 10, background: "#0f172a" }} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </StepCard>

      <StepCard
        title="Step 6：生成 patient_params.json / Patient_rename.json 建议条目"
        description="这一步不会改动你已有的 json 文件，只会根据当前 workflow 结果，总结出建议写入 patient_params.json 的条目，并按照你现有 DICOM 生成脚本的 UID 规则，为当前模型名生成一份 Patient_rename.json 建议条目，供你手工复制和微调。不同模型名会得到各自独立的一组 generated UID。"
      >
        <div style={{ display: "grid", gridTemplateColumns: "minmax(260px, 1fr)", gap: 14 }}>
          <div>
            <label style={labelStyle}>模型名（用于 Patient_rename.json 的 generated 键）</label>
            <input style={inputStyle} value={modelName} onChange={(e) => setModelName(e.target.value)} />
          </div>
        </div>
        <div style={{ marginTop: 14 }}>
          <button style={successBtn} onClick={runStep6} disabled={busy !== "" || !step1Result}>
            {busy === "step6" ? "执行中..." : "7. 执行 Step 6 生成 JSON 建议条目"}
          </button>
        </div>

        {step6Result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>{step6Result.message}</div>
            <JsonSummary value={step6Result.summary} />
            <div style={{ marginTop: 14 }}>
              <FilesPanel title="Step 6 参考位置" files={step6Result.generatedFiles} locations={step6Result.savedLocations} />
            </div>
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>patient_params.json 建议条目</div>
              <div style={codeBox}>{JSON.stringify(step6Result.patientParamsEntry || {}, null, 2)}</div>
            </div>
            <div style={{ marginTop: 18 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Patient_rename.json 建议条目</div>
              <div style={codeBox}>{JSON.stringify(step6Result.patientRenameEntry || {}, null, 2)}</div>
            </div>
          </div>
        )}
      </StepCard>

      <div style={{ ...cardStyle, marginTop: 18, background: "#0b1736", color: "#f8fafc" }}>
        <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 10 }}>执行日志</div>
        <div style={codeBox}>{logs || "暂无日志"}</div>
      </div>
    </div>
  );
}
