import { useState } from "react";

function App() {
  const [modelDir, setModelDir] = useState("model_cstgan");
  const [modelKind, setModelKind] = useState("cstgan_c");
  const [dataset, setDataset] = useState("005_046");
  const [gpuIds, setGpuIds] = useState("0");
  const [log, setLog] = useState("");
  const [loading, setLoading] = useState(false);

  // 当模型目录改变时，自动切换模型类型选项
  const getModelKinds = () => {
    if (modelDir === "model_cstgan") return ["cstgan_c", "mb_taylor"];
    if (modelDir === "model_attn_vit") return ["vit-unet", "attn"];
    if (modelDir === "model_mask") return ["0106"];
    return [];
  };

  const runModel = async () => {
    setLoading(true);
    setLog("正在执行推理，请稍候...\n");

    const res = await fetch("http://localhost:8000/run_model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_dir: modelDir,
        model_kind: modelKind,
        dataset_name: dataset,
        gpu_ids: gpuIds,
      }),
    });

    const data = await res.json();
    setLoading(false);

    if (data.error) setLog("❌ 错误: " + data.error);
    else setLog("执行命令:\n" + data.cmd + "\n\n输出:\n" + data.stdout);
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: 800 }}>
      <h1>CBCT → CT Model Runner</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>模型目录：</label>
        <select value={modelDir} onChange={(e) => setModelDir(e.target.value)}>
          <option value="model_cstgan">model_cstgan</option>
          <option value="model_attn_vit">model_attn_vit</option>
          <option value="model_mask">model_mask</option>
        </select>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label>模型类型：</label>
        <select value={modelKind} onChange={(e) => setModelKind(e.target.value)}>
          {getModelKinds().map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label>数据集：</label>
        <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
          <option value="005_046">005_046</option>
          <option value="029_031">029_031</option>
          <option value="04850">04850</option>
          <option value="046047">046047</option>
        </select>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label>GPU IDs：</label>
        <input
          type="text"
          value={gpuIds}
          onChange={(e) => setGpuIds(e.target.value)}
          style={{ width: "50px" }}
        />
      </div>

      <button onClick={runModel} disabled={loading}>
        {loading ? "运行中..." : "开始执行"}
      </button>

      <pre
        style={{
          background: "#f0f0f0",
          padding: "1rem",
          borderRadius: "8px",
          marginTop: "1rem",
          height: "400px",
          overflow: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        {log}
      </pre>
    </div>
  );
}

export default App;
