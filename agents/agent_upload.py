# # agent_upload.py
# import os
# from langchain.tools import tool
# from utils import abspath, run_command, logger

# @tool
# def upload(file_path: str) -> str:
#     """
#     Upload a CSV file, generate summary statistics and visualizations.
#     Args:
#         file_path (str): Path to the CSV file.
#     Returns:
#         str: Path to the saved visualization file.
#     """
#     file_path = os.path.abspath(file_path)
#     script = abspath("csv_insertion_batch.py")
#     try:
#         out, err, rc = run_command(["python3", script, file_path])
#         logger.info("upload output rc=%s", rc)
#         if rc != 0:
#             return f"ERROR (rc={rc}): {err}\n{out}"
#         return out or "Upload & visualize completed."
#     except Exception as e:
#         logger.exception("upload failed")
#         return f"Exception: {e}"
import os
from langchain.tools import StructuredTool
from utils import abspath, run_command, logger

def _upload(file_path: str) -> str:
    """
    Upload a CSV file using _upload.
    Args:
        file_path (str): Path to the CSV file.
    Returns:
        str: Success MSG.
    """
    file_path = file_path.replace('"', '').replace("'", '').replace('`','')
    file_path = os.path.abspath(file_path)
    print("final file name", file_path)

    script = abspath("csv_insertion_batch.py")
    try:
        out, err, rc = run_command(["python3", script, file_path])
        logger.info("upload output rc=%s", rc)
        if rc != 0:
            return f"ERROR (rc={rc}): {err}\n{out}"
        return out or "Upload completed."
    except Exception as e:
        logger.exception("upload failed")
        return f"Exception: {e}"

upload = StructuredTool.from_function(_upload)
