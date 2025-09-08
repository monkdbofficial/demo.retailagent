# 🧠 Monk-RET  

Monk-RET (**Monk Retail Insights Engine**) is an intelligent retail analytics platform powered by **MonkDB**, its **MCP server**, **LangChain**, **Streamlit**.  
It helps businesses gain actionable insights from large-scale retail data by orchestrating data ingestion, processing, and visualization seamlessly.  

---

## ✨ Features  

- 📊 **Retail Analytics Engine** – Ingests, processes large-scale retail datasets and writes to MonkDB.
- 🧩 **LangChain Orchestrator** – Modular orchestration of tasks with LLMs  
- ⚡ **Batch Data Processing** – Automated CSV ingestion & MonkDB syncing  
- 📈 **Interactive Dashboards** – Streamlit-based UI for analytics & insights  
- 🔄 **Automation** – Watchdog-powered auto-refresh for new datasets  

---

## 🚀 Getting Started  

### 1️⃣ Clone the repo
```bash
git clone https://github.com/monkdbofficial/demo.retailagent.git
cd demo.retailagent
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Run the Watchdong 
```bash
python watchdog_.py
```

### 4️⃣ (Optional) Start the Streamlit dashboard locally
```bash
python orchestrator.py
```

---

## 🛠️ Tech Stack  

- **Languages:** Python  
- **Frameworks:** LangChain, Streamlit, FastAPI, Flask  
- **Data:** Pandas, SQLAlchemy, MongoDB  
- **DevOps:** Docker, Watchdog, Jenkins, Terraform  
- **Visualization:** Plotly, Chart.js, Streamlit  

---

## 📊 Example Workflow  

1. Drop a new retail CSV into the `/data` folder  
2. `watchdog_.py` detects and inserts data → DB  
3. `langchain_orch.py` & `gen_insights_force.py` generate AI-powered insights  
4. Open `streamlit_app.py` → interactive analytics dashboard  

---