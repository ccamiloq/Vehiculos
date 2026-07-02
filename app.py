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
# CONFIGURACIÓN DE LA PÁGINA E INTERFAZ VISUAL (UI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Predicador de Precios de Autos 🚗",
    page_icon="💰",
    layout="wide"
)

# Estilos CSS optimizados para máxima legibilidad, accesibilidad y contraste
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #FAFAFB;
    }
    
    /* Título Principal con alto contraste */
    .main-title {
        color: #111827; /* Gris casi negro muy legible */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        text-align: center;
        font-weight: 800;
        padding-top: 10px;
        padding-bottom: 5px;
        font-size: 2.5rem;
    }
    
    /* Subtítulo descriptivo */
    .subtitle {
        text-align: center; 
        color: #4B5563; /* Gris oscuro intermedio */
        font-size: 1.1rem;
        margin-bottom: 35px;
    }
    
    /* Títulos de sección */
    .section-title {
        color: #1F2937;
        font-weight: 700;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 8px;
        margin-bottom: 15px;
    }
    
    /* Tarjetas de información y guías dinámicas (Texto oscuro sobre fondo pastel) */
    .info-box {
        background-color: #EFF6FF; /* Azul sutil */
        color: #1E40AF; /* Azul oscuro legible */
        padding: 12px 16px;
        border-radius: 8px;
        border-left: 4px solid #3B82F6;
        margin-top: 8px;
        margin-bottom: 15px;
        font-size: 0.92rem;
        line-height: 1.4;
    }
    
    /* Tarjeta de resultados destacados */
    .result-card {
        background-color: #FFFFFF;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 2px solid #10B981; /* Verde esmeralda exitoso */
        text-align: center;
        margin-top: 25px;
    }
    
    /* Ajustes de contraste para etiquetas nativas de Streamlit */
    label p {
        color: #1F2937 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🚗 Validador & Predictor de Precios de Autos 💰</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Selecciona las especificaciones precisas del vehículo para obtener una tasación predictiva e instantánea.</p>", unsafe_allow_html=True)

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

    df_input.to_csv("temp_input.csv", index=False)
    payload = {"deploymentId": DATAROBOT_DEPLOYMENT_ID}
    
    job = _request("POST", BATCH_PREDICTIONS_URL.format(host=DATAROBOT_HOST), data=payload)
    if not job:
        return None

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

    job_url = job["links"]["self"]
    with st.spinner("🧠 El motor de DataRobot está calculando el valor comercial de forma inteligente..."):
        while True:
            job_status = _request("GET", job_url)
            if not job_status:
                return None
            status = job_status["status"]
            if status in ["COMPLETED", "ABORTED", "FAILED"]:
                if status != "COMPLETED":
                    st.error("El procesamiento de DataRobot falló o fue cancelado.")
                    return None
                break
            time.sleep(1.5)

        download_url = job_status["links"]["download"]
        headers_dl = {"Authorization": f"Token {DATAROBOT_API_KEY}"}
        req_dl = Request(download_url, headers=headers_dl)
        ctx = ssl.create_default_context()
        
        with urlopen(req_dl, context=ctx) as response:
            df_output = pd.read_csv(response)
            
    if os.path.exists("temp_input.csv"):
        os.remove("temp_input.csv")
        
    return df_output

# -----------------------------------------------------------------------------
# DISEÑO DEL FORMULARIO DE ENTRADA (MÁXIMA LEGIBILIDAD)
# -----------------------------------------------------------------------------

# Lista de marcas sugeridas y comunes para el menú desplegable
MARCAS_DISPONIBLES = [
    "Toyota", "Ford", "Chevrolet", "Honda", "Nissan", "Hyundai", 
    "Kia", "Volkswagen", "BMW", "Mercedes-Benz", "Audi", "Mazda", 
    "Subaru", "Jeep", "Renault", "Peugeot", "Fiat", "Suzuki"
]

with st.container():
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        st.markdown("<div class='section-title'>🏢 Identificación Básica</div>", unsafe_allow_html=True)
        car_id = st.text_input("🆔 ID del Auto (Car_ID)", value="1001", help="Identificador alfanumérico del registro")
        
        # CAMBIO SOLICITADO: Casilla desplegable para las marcas de vehículos
        brand = st.selectbox("🏷️ Marca del Vehículo (Brand)", options=sorted(MARCAS_DISPONIBLES), index=0)
        
        model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2022, step=1)
        doors = st.slider("🚪 Cantidad de Puertas (Doors)", min_value=2, max_value=5, value=4, step=1)

    with col2:
        st.markdown("<div class='section-title'>⚙️ Rendimiento y Dimensiones</div>", unsafe_allow_html=True)
        
        # --- Campo: Engine_Size con descripción dinámica ---
        engine_size = st.number_input("🔩 Tamaño del Motor en Litros (Engine_Size)", min_value=0.5, max_value=8.0, value=2.0, step=0.1)
        if engine_size < 1.6:
            st.markdown("<div class='info-box'>🚙 <b>Vehículo Pequeño:</b> Cilindrada reducida. Excelente eficiencia de combustible y maniobrabilidad urbana.</div>", unsafe_allow_html=True)
        elif 1.6 <= engine_size <= 3.0:
            st.markdown("<div class='info-box'>🚗 <b>Vehículo Mediano:</b> Cilindrada estándar. Equilibrio óptimo entre potencia para autopista y consumo equilibrado.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>🚛 <b>Vehículo Grande:</b> Alta cilindrada. Diseñado para altas prestaciones, SUVs pesadas o camionetas de gran arrastre.</div>", unsafe_allow_html=True)
            
        # --- Campo: Horsepower con descripción dinámica ---
        horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=30, max_value=1000, value=150, step=10)
        if horsepower < 120:
            st.markdown("<div class='info-box'>🏎️ <b>Potencia Pequeña:</b> Desempeño urbano controlado, óptimo para el uso diario en ciudad.</div>", unsafe_allow_html=True)
        elif 120 <= horsepower <= 250:
            st.markdown("<div class='info-box'>⚡ <b>Potencia Mediana:</b> Aceleración ágil y segura en adelantamientos de carretera.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>🔥 <b>Potencia Grande:</b> Desempeño deportivo de alta gama o capacidad superior para transporte de carga masiva.</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='section-title'>🛣️ Historial y Transmisión</div>", unsafe_allow_html=True)
        mileage = st.number_input("🛣️ Kilometraje/Millas acumuladas (Mileage)", min_value=0, max_value=500000, value=30000, step=5000)
        owner_count = st.number_input("👤 Cantidad de Dueños Anteriores (Owner_Count)", min_value=0, max_value=10, value=1, step=1)
        fuel_type = st.selectbox("⛽ Tipo de Combustible (Fuel_Type)", ["Gasoline", "Diesel", "Electric", "Hybrid"])
        
        # --- Campo: Transmission con descripción dinámica ---
        transmission = st.selectbox("🕹️ Caja de Cambios (Transmission)", ["Automatic", "Manual"])
        if transmission == "Manual":
            st.markdown("<div class='info-box'>⚙️ <b>Transmisión Pequeña/Estándar:</b> Mayor control mecánico sobre la aceleración, costos de mantenimiento generalmente inferiores.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>🕹️ <b>Transmisión Avanzada/Mediana:</b> Confort de manejo continuo, elimina la fatiga en atascos de tráfico pesado.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PROCESAMIENTO Y GENERACIÓN DEL RESULTADO
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

# Botón interactivo estilizado por Streamlit de manera completa
if st.button("🚀 Calcular Predicción del Valor del Auto", use_container_width=True, type="primary"):
    
    # Empaquetado estricto respetando las variables originales de variables.png
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
        "Price": [0] # Variable objetivo requerida por la estructura de Batch Predictions
    }
    
    df_input = pd.DataFrame(data_dict)
    resultados = ejecutar_prediccion(df_input)
    
    if resultados is not None:
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #065F46; font-weight: 700; margin-top: 0;'>🎉 ¡Análisis Completado con Éxito!</h2>", unsafe_allow_html=True)
        
        # Detección flexible de la columna arrojada por la predicción batch de DataRobot
        col_prediccion = [c for c in resultados.columns if 'prediction' in c.lower()]
        
        if col_prediccion:
            precio_estimado = resultados[col_prediccion[0]].iloc[0]
            
            # Muestra métrica con tamaño de letra generoso y gran visibilidad
            st.metric(
                label="💵 VALOR ESTIMADO DEL VEHÍCULO", 
                value=f"${precio_estimado:,.2f} USD"
            )
            st.markdown("<p style='color: #374151; font-weight: 600; font-size: 0.95rem; margin-top: 15px;'>⚠️ Importante: El precio arrojado por este modelo inteligente está expresado única y exclusivamente en <b>Dólares Estadounidenses (USD)</b>.</p>", unsafe_allow_html=True)
        else:
            st.warning("Se procesó la solicitud pero la respuesta no contiene el patrón exacto de columna de predicción esperado.")
            st.dataframe(resultados)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Desplegable secundario con baja carga cognitiva para el usuario
        with st.expander("🔍 Inspeccionar matriz de datos enviada a DataRobot"):
            st.dataframe(df_input.drop(columns=["Price"]))
