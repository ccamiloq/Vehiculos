import streamlit as st
import pandas as pd
import json
import ssl
import time
import io
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA Y ESTILOS (FRONTEND VIVO)
# ==========================================
st.set_page_config(
    page_title="Predicciones DataRobot - Vehículos 🚗",
    page_icon="✨",
    layout="centered"
)

# Estilos personalizados para inyectar más color y dinamismo visual
st.markdown("""
    <style>
    .main-title {
        color: #FF4B4B;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        text-align: center;
        font-weight: bold;
    }
    .subtitle {
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 30px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 12px;
        padding: 10px 24px;
        font-size: 18px;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: scale(1.02);
    }
    .result-box {
        background-color: #E8F5E9;
        border-left: 6px solid #2E7D32;
        padding: 20px;
        border-radius: 8px;
        margin-top: 20px;
    }
    .info-text {
        font-size: 12px;
        color: #666666;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🚗 Evaluador Inteligente de Vehículos</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Introduce las especificaciones de tu vehículo para calcular el valor estimado en <b>dólares (USD)</b> optimizado por <b>DataRobot</b> ✨</p>", unsafe_allow_html=True)

# ==========================================
# CARGA DE CREDENCIALES DESDE SECRETS
# ==========================================
try:
    API_KEY = st.secrets["DATAROBOT_API_KEY"]
    DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
    HOST = st.secrets["DATAROBOT_HOST"]
except KeyError as e:
    st.error(f"❌ Error de configuración: Falta definir la variable secreta {e} en tus Secrets de Streamlit.")
    st.stop()

# ==========================================
# CONSTANTES Y PETICIÓN API ORIGINAL REFACTORIZADA
# ==========================================
BATCH_PREDICTIONS_URL = f"{HOST}/api/v2/batchPredictions/"

def _request(method, url, data=None):
    headers = {
        "Authorization": f"Token {API_KEY}",
        "User-Agent": "IntegrationSnippet-StandAlone-Python",
    }
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json; encoding=utf-8"

    request = Request(url, headers=headers, data=data)
    request.get_method = lambda: method
    
    ctx = ssl.create_default_context()
    
    try:
        response = urlopen(request, context=ctx, timeout=60)
        return response
    except HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"Error {e.code}: {error_body}")

def lanzar_prediccion_batch(df_input):
    csv_buffer = io.StringIO()
    df_input.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue().encode('utf-8')

    payload = {
        "deploymentId": DEPLOYMENT_ID,
    }

    # 1. Crear el Trabajo (Job)
    job_response = _request("POST", BATCH_PREDICTIONS_URL, data=payload)
    job = json.loads(job_response.read().decode('utf-8'))
    links = job["links"]
    job_url = links["self"]

    # 2. Subir los datos CSV genearos dinámicamente
    upload_url = links["csvUpload"]
    upload_request = Request(upload_url, headers={
        "Authorization": f"Token {API_KEY}",
        "Content-length": len(csv_data),
        "Content-type": "text/csv; encoding=utf-8",
    }, data=csv_data)
    upload_request.get_method = lambda: "PUT"
    urlopen(upload_request, context=ssl.create_default_context()).close()

    # 3. Monitorear el progreso
    progress_bar = st.progress(0)
    status_text = st.empty()

    while True:
        job_check = _request("GET", job_url)
        job_data = json.loads(job_check.read().decode('utf-8'))
        status = job_data["status"]

        if status == "INITIALIZING":
            status_text.info("⏳ Inicializando el motor de predicción de DataRobot...")
            progress_bar.progress(10)
        elif status == "RUNNING":
            pct = int(float(job_data.get("percentageCompleted", 0)))
            status_text.warning(f"⚙️ Procesando cálculos en la nube... {pct}% completado.")
            progress_bar.progress(max(10, min(pct, 95)))
        elif status == "COMPLETED":
            progress_bar.progress(100)
            status_text.success("✅ ¡Cálculo completado exitosamente!")
            break
        elif status in ["ABORTED", "FAILED"]:
            status_text.error(f"❌ El proceso ha fallado en DataRobot: {job_data.get('statusDetails')}")
            return None
        
        time.sleep(3)

    # 4. Descargar los resultados
    download_url = job_data["links"]["download"]
    download_response = _request("GET", download_url)
    res_csv = download_response.read().decode('utf-8')
    
    return pd.read_csv(io.StringIO(res_csv))

# ==========================================
# INTERFAZ DE USUARIO CON ENTRADAS DINÁMICAS
# ==========================================
st.markdown("### 📝 Rellena los datos del vehículo")

col1, col2 = st.columns(2)

with col1:
    brand = st.selectbox("🏷️ Marca del Vehículo (Brand)", ["Toyota", "Ford", "Honda", "Chevrolet", "Nissan", "Hyundai", "BMW", "Mercedes", "Otro"])
    
    model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2022, step=1)
    
    engine_size = st.number_input("💡 Tamaño del Motor en Litros (Engine_Size)", min_value=0.5, max_value=8.0, value=2.0, step=0.1)
    st.markdown("<p class='info-text'>ℹ️ <i>Carros pequeños: menos de 1.6L | Medianos: 1.6L a 2.5L | Grandes / Motores potentes: más de 2.5L</i></p>", unsafe_allow_html=True)
    
    fuel_type = st.radio("⛽ Tipo de Combustible (Fuel_Type)", ["Gasoline", "Diesel", "Electric", "Hybrid"])

with col2:
    doors = st.slider("🚪 Número de Puertas (Doors)", min_value=2, max_value=5, value=4, step=1)
    
    horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=30, max_value=1000, value=150, step=5)
    st.markdown("<p class='info-text'>ℹ️ <i>Carros urbanos/pequeños: menos de 110 HP | Sedanes/Suvs medianos: 110 a 200 HP | Deportivos/Grandes: más de 200 HP</i></p>", unsafe_allow_html=True)
    
    mileage = st.number_input("🛣️ Kilometraje / Millaje (Mileage)", min_value=0, max_value=500000, value=45000, step=1000)
    
    owner_count = st.slider("👤 Número de Dueños Anteriores (Owner_Count)", min_value=0, max_value=10, value=1, step=1)
    
    transmission = st.selectbox("⚙️ Transmisión (Transmission)", ["Automatic", "Manual", "CVT"])

# ==========================================
# ACCIÓN AL PRESIONAR EL BOTÓN INTERACTIVO
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 Calcular Valor Estimado con DataRobot", use_container_width=True):
    
    # Mapeo de columnas enviando valores por defecto o fijos para las variables retiradas si el modelo las exige
    datos_vehiculo = {
        "Brand": [brand],
        "Car_ID": ["AUTO-BATCH"], # Enviado por defecto internamente para no romper la firma del modelo
        "Doors": [doors],
        "Engine_Size": [engine_size],
        "Fuel_Type": [fuel_type],
        "Horsepower": [horsepower],
        "Mileage": [mileage],
        "Model_Year": [model_year],
        "Owner_Count": [owner_count],
        "Price": [0],             # Si Price era tu variable objetivo (target), pasamos 0 para la predicción
        "Transmission": [transmission]
    }
    
    df_entrada = pd.DataFrame(datos_vehiculo)
    
    with st.spinner("Conectando con los servidores de DataRobot..."):
        try:
            df_resultados = lanzar_prediccion_batch(df_entrada)
            
            if df_resultados is not None:
                st.markdown("<div class='result-box'>", unsafe_allow_html=True)
                st.markdown("### 🎉 Resultados de la Predicción")
                
                col_prediccion = [c for c in df_resultados.columns if 'prediction' in c.lower() or 'pred' in c.lower()]
                
                if col_prediccion:
                    valor_prediccion = df_resultados[col_prediccion[0]].iloc[0]
                    # Se indica explícitamente en la métrica que el resultado es en dólares (USD)
                    st.metric(label="🎯 Precio Estimado (Predicción en Dólares USD)", value=f"${valor_prediccion:,.2f}")
                else:
                    st.info("Predicción realizada con éxito. Mira los datos devueltos:")
                
                st.markdown("**Vista detallada de la respuesta:**")
                st.dataframe(df_resultados)
                st.markdown("</div>", unsafe_allow_html=True)
                
        except Exception as ex:
            st.error(f"❌ Ocurrió un error al procesar la predicción: {ex}")
