# # agent_deploy.py
# import os
# from langchain.tools import tool
# from utils import abspath, run_command, logger

# @tool
# def deploy_dashboard(file_path: str) -> str:
#     """
#     Upload a CSV file, deploy stats
#     Args:
#         file_path (str): Path to the CSV file.
#     Returns:
#         str: Path to the saved visualization file.
#     """
#     file_path = os.path.abspath(file_path)
#     # Commit & push is optional: use env var to gate
#     try:
#         script = abspath("streamlit_app.py")
#         # Use nohup or python -m to run; here run in background is left to deployment infra
#         out, err, rc = run_command(["streamlit", "run", script, "--server.port", "8501"])
#         if rc != 0:
#             logger.warning("streamlit run returned rc=%s err=%s", rc, err)
#             return f"Streamlit launch error (rc={rc}): {err}\n{out}"
#         return "Streamlit launched. Check logs."
#     except Exception as e:
#         logger.exception("deploy_dashboard error")
#         return f"Exception: {e}"

import os
from langchain.tools import StructuredTool
from utils import abspath, run_command, logger

def _deploy_dashboard(file_path: str) -> str:
    """
    Deploy a dashboard with streamlit using _deploy_dashboard.
    Args:
        file_path (str): Path to the CSV file.
    Returns:
        str: Deployment confirmation message.
    """
    file_path = os.path.abspath(file_path)
    try:
        script = abspath("streamlit_app.py")
        out, err, rc = run_command(["streamlit", "run", script, "--server.port", "8501"])
        if rc != 0:
            logger.warning("streamlit run returned rc=%s err=%s", rc, err)
            return f"Streamlit launch error (rc={rc}): {err}\n{out}"
        return "Deployment success."
    except Exception as e:
        logger.exception("deploy_dashboard error")
        return f"Exception: {e}"

deploy_dashboard = StructuredTool.from_function(_deploy_dashboard)
