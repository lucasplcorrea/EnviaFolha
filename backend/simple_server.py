import sys
print(f"🐍 Python {sys.version}")

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    app = FastAPI(title="Sistema RH - Teste")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    def read_root():
        return {"message": "🚀 Sistema RH funcionando!", "python": sys.version}
    
    @app.post("/api/v1/auth/login")
    def login(credentials: dict):
        if credentials.get("username") == "admin":
            return {
                "access_token": "test-token",
                "token_type": "bearer", 
                "user": {"username": "admin", "full_name": "Admin"}
            }
        return {"error": "Invalid credentials"}
    
    if __name__ == "__main__":
        print("🎯 Servidor simples iniciando...")
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
        
except ImportError as e:
    print(f"❌ Erro: {e}")
    print("💡 Execute: python quick_install.py")
