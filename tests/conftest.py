import os

# Las pruebas nunca deben conectarse a una base de datos real, aunque exista un .env
os.environ["MONGODB_URI"] = ""
os.environ["CONFIRMAR_AUTOMATICAMENTE"] = ""
os.environ["COOKIE_SEGURA"] = ""
os.environ["GITHUB_CLIENT_ID"] = ""
os.environ["GITHUB_CLIENT_SECRET"] = ""
os.environ["BASE_URL"] = ""
