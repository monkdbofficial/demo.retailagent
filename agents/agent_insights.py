# import os
# from langchain.tools import tool
# from utils import abspath, run_command, logger

# @tool
# def generate_insights(file_path: str) -> str:
#     """
#     Generate summary statistics and visualizations.
#     Args:
#         file_path (str): Path to the CSV file.
#     Returns:
#         str: Path to the saved visualization JSON or insights text.
#     """
#     script = "gen_insights_force.py"
#     try:
#         out, err, rc = run_command(["python3", script, "--filters-json", "{}"])
#         if rc != 0:
#             return f"ERROR (rc={rc}): {err}\n{out}"
#         return out.strip() or "No insights generated."
#     except Exception as e:
#         logger.exception("generate_insights error")
#         return f"Exception: {e}"



import os
from langchain.tools import StructuredTool
from utils import abspath, run_command, logger

def _generate_insights(file_path: str) -> str:
    """
    Generate summary statistics form csv only, dont imagine anything only give results using _generate_insights.
    Args:
        file_path (str): Path to the CSV file.
    Returns:
        str: JSON Dict.
    """
    file_path = os.path.abspath(file_path)
    script = "gen_insights_force.py"
    try:
        out, err, rc = run_command(["python3", script, "--filters-json", "{}"])
        if rc != 0:
            return f"ERROR (rc={rc}): {err}\n{out}"
        return out.strip() or "No insights generated."
    except Exception as e:
        logger.exception("generate_insights error")
        return f"Exception: {e}"

generate_insights = StructuredTool.from_function(_generate_insights)
