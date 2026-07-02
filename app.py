import streamlit as st
import pandas as pd
import os
import json
import ssl
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Configuración de los Secrets (Reemplaza con tus credenciales reales o configúralos en Streamlit Cloud)
DATAROBOT_API_KEY = st.secrets.get("DATAROBOT_API_KEY", "")
DATAROBOT_DEPLOYMENT_ID = st.secrets.get("DATAROBOT_DEPLOYMENT_ID", "")
DATAROBOT_HOST = st.secrets.get("DATAROBOT_HOST", "https://app.datarobot.com")

BATCH_PREDICTIONS_URL = "{host}/api/v2/batchPredictions/"

# -----------------------------------------------------------------------------
# LOGICA DE CONFIGURACIÓN DE PÁGINA (UI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Predicador de Precios de Autos 🚗",
    page_icon="💰",
    layout="wide"
)

# Estilos CSS personalizados para darle más vida, color y diseño responsivo
st.markdown("""
    <style>
    .main {
        background-color: #f7f9fc;
    }
    .main-title {
        color: #1e3d59;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        text-align: center;
        font-weight: bold;
        padding-bottom: 20px;
    }
    .info-box {
        background-color: #e8f1f5;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #17a2b8;
        margin-bottom: 15px;
    }
    .result-card {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-top: 5px solid #28a745;
        text-align: center;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🚗 Validador & Predictor de Precios de Autos 💰</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Introduce las características de tu vehículo a continuación para estimar su valor en el mercado actual.</p>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES PARA DATAROBOT (Adaptadas de predict.py)
# -----------------------------------------------------------------------------
def _request(method, url, data=None):
    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "User-Agent": "IntegrationSnippet-StandAlone-Python",
    }
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json; encoding=utf-8"

    request = Request(url, headers=headers, data=data)
    request.get_method = lambda: method
    ctx = ssl.create_default_context()

    try:
        response = urlopen(request, context=ctx, timeout=600)
        result = response.read()
        response.close()
        return json.loads(result.decode('utf-8'))
    except HTTPError as e:
        st.error(f"Error de API DataRobot: {e.code} - {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def ejecutar_prediccion(df_input):
    if not DATAROBOT_API_KEY or not DATAROBOT_DEPLOYMENT_ID:
        st.error("❌ Por favor configura tus credenciales de DataRobot en los Secrets.")
        return None

    # Guardar temporalmente el dataframe de entrada en formato CSV
    df_input.to_csv("temp_input.csv", index=False)
    
    payload = {"deploymentId": DATAROBOT_DEPLOYMENT_ID}
    
    # 1. Crear el Job de Predicción
    job = _request("POST", BATCH_PREDICTIONS_URL.format(host=DATAROBOT_HOST), data=payload)
    if not job:
        return None

    # 2. Subir el archivo CSV generado
    upload_url = job["links"]["csvUpload"]
    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "User-Agent": "IntegrationSnippet-StandAlone-Python",
        "Content-length": os.path.getsize("temp_input.csv"),
        "Content-type": "text/csv; encoding=utf-8",
    }
    
    try:
        with open("temp_input.csv", "rb") as f:
            req = Request(upload_url, headers=headers, data=f.read())
            req.get_method = lambda: "PUT"
            ctx = ssl.create_default_context()
            urlopen(req, context=ctx).close()
    except Exception as e:
        st.error(f"Error al subir los datos: {e}")
        return None

    # 3. Esperar a que el Job se procese y descargar el resultado
    job_url = job["links"]["self"]
    with st.spinner("🧠 DataRobot está procesando e inteligentemente cotizando el auto..."):
        while True:
            job_status = _request("GET", job_url)
            if not job_status:
                return None
            status = job_status["status"]
            if status in ["COMPLETED", "ABORTED", "FAILED"]:
                if status != "COMPLETED":
                    st.error("El proceso de DataRobot falló o fue abortado.")
                    return None
                break
            time.sleep(2)

        # Descargar resultados
        download_url = job_status["links"]["download"]
        headers_dl = {"Authorization": f"Token {DATAROBOT_API_KEY}"}
        req_dl = Request(download_url, headers=headers_dl)
        ctx = ssl.create_default_context()
        
        with urlopen(req_dl, context=ctx) as response:
            df_output = pd.read_csv(response)
            
    # Limpieza de archivos temporales
    if os.path.exists("temp_input.csv"):
        os.remove("temp_input.csv")
        
    return df_output

# -----------------------------------------------------------------------------
# DISEÑO DE LA INTERFAZ DILIGENCIABLE (FORMULARIO)
# -----------------------------------------------------------------------------

# Secciones interactivas mediante columnas y contenedores coloridos
with st.container():
    st.markdown("### 📝 Características del Vehículo")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🏢 Identificación Básica")
        car_id = st.text_input("🆔 ID del Auto (Car_ID)", value="1001", help="Identificador único del vehículo")
        brand = st.text_input("🏷️ Marca (Brand)", value="Toyota", help="Ej: Toyota, Ford, BMW, etc.")
        model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2022, step=1)
        doors = st.slider("🚪 Cantidad de Puertas (Doors)", min_value=2, max_value=5, value=4, step=1)

    with col2:
        st.subheader("⚙️ Rendimiento y Guías")
        
        # --- Campo: Engine_Size con descripción dinámica ---
        engine_size = st.number_input("🔩 Tamaño del Motor en Litros (Engine_Size)", min_value=0.5, max_value=8.0, value=2.0, step=0.1)
        if engine_size < 1.6:
            st.markdown("<div class='info-box'>ℹ️ <b>Motor Pequeño:</b> Ideal para uso urbano y alta eficiencia de combustible.</div>", unsafe_allow_html=True)
        elif 1.6 <= engine_size <= 3.0:
            st.markdown("<div class='info-box'>ℹ️ <b>Motor Mediano:</b> Equilibrio estándar entre potencia y consumo (Sedanes y SUVs comunes).</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>ℹ️ <b>Motor Grande:</b> Vehículos de alta gama, deportivos o camionetas de gran tracción.</div>", unsafe_allow_html=True)
            
        # --- Campo: Horsepower con descripción dinámica ---
        horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=30, max_value=1000, value=150, step=10)
        if horsepower < 120:
            st.markdown("<div class='info-box'>ℹ️ <b>Potencia Pequeña:</b> Desempeño básico, autos compactos económicos.</div>", unsafe_allow_html=True)
        elif 120 <= horsepower <= 250:
            st.markdown("<div class='info-box'>ℹ️ <b>Potencia Mediana:</b> Conducción ágil y segura en autopistas.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>ℹ️ <b>Potencia Grande:</b> Autos deportivos o vehículos preparados para cargas pesadas.</div>", unsafe_allow_html=True)

    with col3:
        st.subheader("🛣️ Estado y Transmisión")
        mileage = st.number_input("🛣️ Kilometraje/Millas (Mileage)", min_value=0, max_value=500000, value=30000, step=5000)
        owner_count = st.number_input("👤 Número de Dueños Anteriores (Owner_Count)", min_value=0, max_value=10, value=1, step=1)
        fuel_type = st.selectbox("⛽ Tipo de Combustible (Fuel_Type)", ["Gasoline", "Diesel", "Electric", "Hybrid"])
        
        # --- Campo: Transmission con descripción dinámica ---
        transmission = st.selectbox("🕹️ Transmisión (Transmission)", ["Automatic", "Manual"])
        if transmission == "Manual":
            st.markdown("<div class='info-box'>ℹ️ <b>Transmisión Manual:</b> Mayor control de marchas, usualmente asociada a reparaciones más económicas.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>ℹ️ <b>Transmisión Automática:</b> Máxima comodidad en el tráfico y suavidad de manejo.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# EJECUCIÓN Y PRESENTACIÓN DE RESULTADOS
# -----------------------------------------------------------------------------
st.markdown("---")

# Botón interactivo central con estilo destacado
if st.button("🚀 Calcular Predicción de Precio", use_container_width=True):
    
    # Crear el diccionario respetando exactamente los nombres de las variables de tu modelo (basado en variables.png)
    # Se añade la columna objetivo (Price) vacía o con 0 tal como requieren los datasets de scoring
    data_dict = {
        "Brand": [brand],
        "Car_ID": [int(car_id) if car_id.isdigit() else car_id],
        "Doors": [doors],
        "Engine_Size": [engine_size],
        "Fuel_Type": [fuel_type],
        "Horsepower": [horsepower],
        "Mileage": [mileage],
        "Model_Year": [model_year],
        "Owner_Count": [owner_count],
        "Transmission": [transmission],
        "Price": [0] 
    }
    
    df_input = pd.DataFrame(data_dict)
    
    # Ejecutar proceso batch
    resultados = ejecutar_prediccion(df_input)
    
    if resultados is not None:
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        st.markdown("## 🎉 ¡Predicción Completada Exitosamente! 🎉")
        
        # DataRobot suele añadir las predicciones en una columna llamada 'Price_prediction' o similar. 
        # Buscamos de manera dinámica columnas que contengan 'prediction'
        col_prediccion = [c for c in resultados.columns if 'prediction' in c.lower()]
        
        if col_prediccion:
            precio_estimado = resultados[col_prediccion[0]].iloc[0]
            st.metric(
                label="💵 Precio Estimado del Mercado", 
                value=f"${precio_estimado:,.2f} USD"
            )
            st.caption("⚠️ *Nota: El valor arrojado por el modelo de Inteligencia Artificial está expresado en dólares estadounidenses (USD).*")
        else:
            st.warning("Se procesaron los datos, pero no se localizó explícitamente la columna de predicción en la respuesta.")
            st.dataframe(resultados)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Desplegar tabla expansible con el registro enviado para auditoría
        with st.expander("🔍 Ver datos procesados enviados al modelo"):
            st.dataframe(df_input.drop(columns=["Price"]))
