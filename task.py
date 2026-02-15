import threading
import requests
import time
from datetime import datetime
import os
from google import genai

# Diccionario global compartido (para prod: Redis)
tareas = {}

def procesar_ai_async(task_id, prompt, GOOGLE_AI_KEY):

    def target():
        print(f"Task {task_id} started at {datetime.now()}")
        try:
            tareas[task_id]["status"] = "procesando"

            client = genai.Client(api_key=GOOGLE_AI_KEY)

            # gemini-2.5-flash-lite
            # gemini-3-flash-preview

            resp = client.models.generate_content(
                model="gemini-2.5-flash-lite", contents=prompt
            )
            
            if resp and resp.text:
                texto = resp.text
                print(texto)
                tareas[task_id]["result"] = texto
            else:
                tareas[task_id]["result"] = "Error API: No response text received"
                print("Error API: No response text received")
                
        except Exception as e:
            tareas[task_id]["result"] = f"Error: {str(e)}"
        finally:
            tareas[task_id]["status"] = "terminada"
            tareas[task_id]["event"].set()  # ¡Libera al cliente!
    
    t = threading.Thread(target=target, daemon=True)
    t.start()
