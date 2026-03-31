import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import PipelineRunner from "./pages/PipelineRunner";
import DicomGenerator from "./pages/DicomGenerator";
import Method1DatasetBuilder from "./pages/Method1DatasetBuilder";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen">
        <nav className="w-64 bg-gray-50 border-r flex flex-col justify-between">
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

            <NavLink
              to="/method1"
              className={({ isActive }) =>
                `block px-4 py-2 rounded-md mx-2 mb-1 ${
                  isActive
                    ? "bg-blue-100 text-blue-700 font-semibold"
                    : "hover:bg-blue-50 text-gray-700"
                }`
              }
            >
              方法一数据集制作
            </NavLink>
          </div>

          <div className="p-4 text-sm text-gray-500 border-t">
            <span>帮助</span> | <span>设置</span>
          </div>
        </nav>

        <main className="flex-1 overflow-y-auto bg-slate-50">
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
