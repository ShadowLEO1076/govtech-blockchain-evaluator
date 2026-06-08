import json, random, os

def crear_evaluaciones(n=3):
    if not os.path.exists("evaluaciones"): os.makedirs("evaluaciones")
    for i in range(n):
        doc = {
            "id": f"DOC-{random.randint(100,999)}",
            "involucramiento": random.randint(1,4),
            "razonamiento": random.randint(1,4),
            "retroalimentacion": random.randint(1,4)
        }
        with open(f"evaluaciones/docente_{i}.json", "w") as f:
            json.dump(doc, f)
    print("3 archivos creados en carpeta /evaluaciones")

crear_evaluaciones()