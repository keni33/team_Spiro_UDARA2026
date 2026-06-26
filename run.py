"""
StructGuard AI — Server Entry Point
Run this file to start the backend: python run.py
"""
from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  StructGuard AI Backend — Starting...")
    print("="*55)
    print("  API:      http://localhost:5000/api")
    print("  Demo accounts (all passwords: Demo1234!):")
    print("    supervisor@demo.com  → Site Supervisor")
    print("    developer@demo.com   → Developer/Owner")
    print("    inspector@demo.com   → Regulatory Inspector")
    print("    admin@demo.com       → Agency Administrator")
    print("="*55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
