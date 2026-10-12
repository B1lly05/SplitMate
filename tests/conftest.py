import os

# Las pruebas nunca deben conectarse a una base de datos real, aunque exista un .env
os.environ["MONGODB_URI"] = ""
os.environ["CONFIRMAR_AUTOMATICAMENTE"] = ""
os.environ["COOKIE_SEGURA"] = ""