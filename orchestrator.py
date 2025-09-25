from agents.agent_upload import upload_task, upload
from agents.agent_insights import insight_task, generate_insights
from agents.agent_deploy import deploy_task, deploy_dashboard
import argparse
import os

def main(file_path: str):
    print("🚀 Starting Orchestration Pipeline")

    # ---------------------------
    # Step 1: Upload & Visualization
    # ---------------------------
    print("📊 Step 1: Upload & Visualization")
    upload_result = upload(file_path)
    print(upload_result)

    # ---------------------------
    # Step 2: Generate Insights
    # ---------------------------
    print("🤖 Step 2: Generate Insights")
    insight_result = generate_insights(file_path)
    print(insight_result)

    # ---------------------------
    # Step 3: Deploy to GitHub
    # ---------------------------
    print("📤 Step 3: Deployment")
    deploy_result = deploy_dashboard()
    print(deploy_result)

    print("✅ Workflow completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run orchestration pipeline for CSV file")
    parser.add_argument("file_path", help="Path to the CSV file to process")
    args = parser.parse_args()

    main(args.file_path)
