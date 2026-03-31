// src/App.tsx
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import PipelineRunner from "./pages/PipelineRunner";
import DicomGenerator from "./pages/DicomGenerator"; // 后续新建

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen">
        {/* 左侧导航栏 */}
        <nav className="w-60 bg-gray-50 border-r flex flex-col justify-between">
          <div>
            <div className="p-4 text-lg font-bold text-gray-800">CBCT → CT 平台</div>

            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `block px-4 py-2 rounded-md mx-2 mb-1 ${
                  isActive
                    ? "bg-blue-100 text-blue-700 font-semibold"
                    : "hover:bg-blue-50 text-gray-700"
                }`
              }
            >
              模型推理 & 图像整理
            </NavLink>

            <NavLink
              to="/dicom"
              className={({ isActive }) =>
                `block px-4 py-2 rounded-md mx-2 mb-1 ${
                  isActive
                    ? "bg-blue-100 text-blue-700 font-semibold"
                    : "hover:bg-blue-50 text-gray-700"
                }`
              }
            >
              生成 DICOM
            </NavLink>
          </div>

          <div className="p-4 text-sm text-gray-500 border-t">
            <a href="#">帮助</a> | <a href="#">设置</a>
          </div>
        </nav>

        {/* 右侧主内容 */}
        <main className="flex-1 overflow-y-auto bg-slate-50">
          <Routes>
            <Route path="/" element={<PipelineRunner />} />
            <Route path="/dicom" element={<DicomGenerator />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
