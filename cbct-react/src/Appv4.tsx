import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import PipelineRunner from "./pages/PipelineRunner";
import DicomGenerator from "./pages/DicomGenerator";
import Method1DatasetBuilder from "./pages/Method1DatasetBuilder";

const navItems = [
  { to: "/", label: "推理与整理", description: "模型推理、流式日志与结果整理" },
  { to: "/dicom", label: "DICOM 导出", description: "将生成结果恢复为 DICOM 序列" },
  { to: "/method1", label: "数据集制作（ORB）", description: "基于 ORB 的数据集对齐与制作流程" },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="app-sidebar">
          <div>
            <div className="app-brand">
              <div className="app-brand-mark">C</div>
              <div>
                <div className="app-brand-title">CBCT → CT 平台</div>
                <div className="app-brand-subtitle">Research Workstation</div>
              </div>
            </div>

            <div className="app-nav-group-title">功能模块</div>
            <nav className="app-nav">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `app-nav-link ${isActive ? "app-nav-link-active" : ""}`
                  }
                >
                  <span className="app-nav-link-title">{item.label}</span>
                  <span className="app-nav-link-desc">{item.description}</span>
                </NavLink>
              ))}
            </nav>
          </div>

          <div className="app-sidebar-footer">
            <div>医学图像生成与导出工具</div>
            <div>UI refresh · workflow preserved</div>
          </div>
        </aside>

        <main className="app-main">
          <Routes>
            <Route path="/" element={<PipelineRunner />} />
            <Route path="/dicom" element={<DicomGenerator />} />
            <Route path="/method1" element={<Method1DatasetBuilder />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
