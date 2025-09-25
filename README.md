# 🧠 Agentic AI in Retail, Powered by MonkDB

Monk-RET (**Monk Retail Insights Engine**) is an intelligent retail analytics platform powered by **MonkDB**, **MonkDB's MCP** **LangChain**, **Streamlit**, and modern AI/ML pipelines.  
It helps businesses gain actionable insights from large-scale retail data by orchestrating data ingestion, processing, and visualization seamlessly.  

---

## ✨ Features  

- 📊 **Retail Analytics Engine** – Ingests and processes large-scale retail datasets into MonkDB.
- 🧩 **LangChain Orchestrator** – Modular orchestration of tasks with LLMs  
- ⚡ **Batch Data Processing** – Automated CSV ingestion & database syncing  
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

### 4️⃣ Move `_sample_products.csv` to `csv_folder/`
This shall trigger the watch and downstream agent orchestration logic which do the following in phases:

- Chunk the data to 5000 records, and leverage dask to process the records before publishing to MonkDB tables.
- Generate a streamlit dashboard app with insights based on MonkDB's sql queries. 
- The streamlit dashboard is deployed to its destination that has the dashboard, charts, and metrics in those charts.

---

## 🛠️ Tech Stack  

- **Languages:** Python  
- **Database:** MonkDB and its python sdk
- **Frameworks:** MonkDB's MCP, LangChain
- **Data:** Dask  
- **DevOps:** Watchdog  
- **Visualization:** Plotly, Streamlit  

---

## 📊 Example Workflow  

1. Drop a new retail CSV into the `/csv_folder` folder  
2. `watchdog_.py` detects and inserts data → DB  
3. `langchain_orch.py` & `gen_insights_force.py` generate AI-powered insights  
4. Open `streamlit_app.py` → interactive analytics dashboard  

---

## License

This repo is licensed under permissive **Apache 2.0** license.
