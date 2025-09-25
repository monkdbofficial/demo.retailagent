# langchain_orch.py
import argparse
import os
from pathlib import Path
import logging
from utils import abspath, run_command
from langchain_ollama import ChatOllama
from langchain.agents import initialize_agent, AgentType

from agents.agent_upload import upload
from agents.agent_insights import generate_insights
from agents.agent_deploy import deploy_dashboard

# -------------------------------------------------------------------
# Setup logging
# -------------------------------------------------------------------
logger = logging.getLogger("orch")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
ch.setFormatter(formatter)
logger.addHandler(ch)

# -------------------------------------------------------------------
# Instantiate LLM
# -------------------------------------------------------------------
model_name = os.getenv("OLLAMA_MODEL", "mistral")
logger.info("Using Ollama model: %s", model_name)
llm = ChatOllama(model=model_name)

# -------------------------------------------------------------------
# Tools & Agents
# -------------------------------------------------------------------
uploader = initialize_agent(
    tools=[upload],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

insighter = initialize_agent(
    tools=[generate_insights],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

deployer = initialize_agent(
    tools=[deploy_dashboard],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
)

# -------------------------------------------------------------------
# Agent Invocation
# -------------------------------------------------------------------
def invoke_agent(agent, instruction: str, timeout: int = 120):
    """Robustly invoke a LangChain agent; catch exceptions and return structured result."""
    logger.info("Invoking agent with instruction: %s", instruction)
    try:
        res = agent.run(instruction)
        logger.info("Agent completed successfully.")
        logger.debug("Agent raw output: %s", res)
        return {"success": True, "output": res}
    except Exception as e:
        logger.exception("Agent invocation failed: %s", e)
        return {"success": False, "error": str(e)}

# -------------------------------------------------------------------
# Workflow
# -------------------------------------------------------------------
def multi_agent_workflow(csv_file_path: str):
    csv_file_path = str(Path(csv_file_path).resolve())
    logger.info("🚀 Starting multi-agent pipeline for %s", csv_file_path)

    # Upload
    res1 = invoke_agent(uploader, {csv_file_path})
    if not res1["success"]:
        return res1
    logger.info("Uploader Output:\n%s", res1["output"])

    # # Insights
    # res2 = invoke_agent(insighter,{csv_file_path})
    # if not res2["success"]:
    #     return res2
    # logger.info("Insights Output:\n%s", res2["output"])

    # Deploy
    res3 = invoke_agent(deployer, {csv_file_path})
    if not res3["success"]:
        return res3
    logger.info("Deployer Output:\n%s", res3["output"])

    logger.info("✅ Multi-agent workflow finished successfully.")
    return {"success": True, "deployer": res3["output"]}

# -------------------------------------------------------------------
# CLI Entrypoint
# -------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="CSV file path")
    args = parser.parse_args()
    result = multi_agent_workflow(args.file_path)
    print("\n=== FINAL RESULT ===")
    print(result)
