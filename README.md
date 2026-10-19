# PCBA 包装 BOM 及运费报价系统

一个 Flask API + React/Vite 前端的 PCBA 包装报价系统，支持根据产品尺寸、重量、数量、目的地、物流产品自动估算包装方案、包装 BOM、箱型、内衬、托盘码垛、包装成本、运费、成本区间、包装验证等级和历史纠偏。

## 主要能力

- 自动箱型 / 内衬 / 托盘码垛建议
- 跨越运费模型，支持始发地、目的地、物流产品和折扣系数
- 包装成本 BOM 与单价配置清单
- 成本低位 / 常用 / 高位区间
- 包装验证等级与建议验证项
- 报价历史记录与实际价纠偏回填

## 本地启动

### 后端

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m webapp.api_server
```

默认后端地址：`http://127.0.0.1:5055`

### 前端

```powershell
cd webapp/frontend
npm install
npm run dev -- --host 127.0.0.1
```

默认前端地址：`http://127.0.0.1:5173`

## 测试

```powershell
python -m pytest tests/packaging_core/test_service_adapter.py tests/test_webapp_api.py -q
cd webapp/frontend
node src/resultViewModel.test.mjs
node src/formOptions.test.mjs
npm run build
```

## 部署说明

仓库包含 GitHub Pages 工作流，仅部署前端静态页面。后端 Flask API 需要另行部署到支持 Python 的服务。
