import pandas as pd
import chardet

# ==========================================
# 1. DETECTAR CODIFICACIÓN REAL
# ==========================================
file_path = "../data/processed/conversaciones_clean.csv"

with open(file_path, 'rb') as f:
    raw_data = f.read(20000)  # Leemos una muestra del archivo
    detection = chardet.detect(raw_data)
    encoding_detectado = detection['encoding']
    print(f"Codificación detectada: {encoding_detectado}")

# ==========================================
# 2. LEER CSV
# ==========================================
# Leemos con la codificación detectada o latin1 para capturar los bytes "sucios"
df = pd.read_csv(file_path, encoding=encoding_detectado)

# ==========================================
# 3. FUNCION DE REPARACIÓN PROFUNDA
# ==========================================
def fix_mojibake(text):
    if pd.isna(text) or text == 'nan':
        return text
    
    try:
        # Paso A: Si el texto fue leído como latin1 pero era utf-8, 
        # esto revierte los "Ã³" a sus caracteres correctos.
        return text.encode('latin1').decode('utf-8')
    except:
        try:
            # Paso B: Si el error es inverso
            return text.encode('utf-8').decode('latin1')
        except:
            # Si nada funciona, devolvemos el original
            return text

# Columnas a procesar
text_columns = ["mensaje_usuario", "respuesta_bot"]

for col in text_columns:
    if col in df.columns:
        print(f"Corrigiendo columna: {col}...")
        # Aseguramos que sea string antes de aplicar
        df[col] = df[col].astype(str).apply(fix_mojibake)

# ==========================================
# 4. GUARDAR EN FORMATO UNIVERSAL (UTF-8 con BOM)
# ==========================================
output_path = "../data/processed/conversaciones_clean_fixed.csv"

# 'utf-8-sig' es la clave para que Excel y otros programas 
# no confundan los acentos nunca más.
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"Proceso finalizado. Archivo guardado en: {output_path}")

# ==========================================
# 5. VERIFICACIÓN VISUAL RÁPIDA
# ==========================================
if "mensaje_usuario" in df.columns:
    print("\nPrimeras filas corregidas:")
    print(df[text_columns].head())