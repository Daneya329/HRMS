"""
Start the HRMS web application.

    python app.py

Then open http://127.0.0.1:8000 in your browser.
"""
import os

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  HRMS is running:  http://127.0.0.1:{port}\n  Default login:    admin@hrms.local / Admin@123\n"
          f"  Press CTRL+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=False)
