"""
Main entry point for Match Crew system.
"""
import uvicorn
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def start_api():
    """Start the FastAPI server."""
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api"]
    )

def start_validation_interface():
    """Start the Streamlit validation interface."""
    import subprocess
    
    interface_path = os.path.join("internal_tools", "interface_validacao.py")
    cmd = ["streamlit", "run", interface_path]
    
    print(f"Starting validation interface: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Match Crew System")
    parser.add_argument(
        "--mode", 
        choices=["api", "interface", "legacy"], 
        default="api",
        help="System mode to run"
    )
    
    args = parser.parse_args()
    
    if args.mode == "api":
        print("Starting Match Crew API...")
        start_api()
    elif args.mode == "interface":
        print("Starting Validation Interface...")
        start_validation_interface()
    elif args.mode == "legacy":
        print("Starting Legacy System...")
        legacy_path = os.path.join("legacy", "executar_sistema_completo.py")
        exec(open(legacy_path).read())
    else:
        print("Invalid mode. Use --help for options.")