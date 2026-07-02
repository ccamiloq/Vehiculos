import streamlit as st
import pandas as pd
import os
import json
import ssl
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Configuración de los Secrets
DATAROBOT_API_KEY = st.secrets.get("DATAROBOT_API_KEY", "")
DATAROBOT_DEPLOYMENT_ID = st.secrets.get("DATAROBOT_DEPLOYMENT_ID", "")
DATAROBOT_HOST = st.secrets.get("DATAROBOT_HOST", "https://app.datarobot.com")

BATCH_PREDICTIONS_URL = "{host}/api/v2/batchPredictions/"

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA E INTERFAZ VISUAL EN MODO OSCURO (UI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Predicador de Precios de Autos 🚗",
    page_icon="💰",
    layout="wide"
)

# Inyección de estilos CSS avanzados para eliminar fondos blancos y asegurar legibilidad
st.markdown("""
    <style>
    /* Cambiar el fondo global de toda la aplicación a un tono oscuro y elegante */
    .stApp {
        background-color: #0F172A !important; /* Azul pizarra oscuro */
    }
    
    /* Modificar los contenedores de inputs de Streamlit para que combinen con el fondo */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="slider"] {
        background-color: #1E293B !important;
        border-radius: 8px !important;
    }
    
    /* Asegurar que todos los textos de etiquetas sean blancos o contrastantes */
    label p, .stMarkdown p, h1, h2, h3, span {
        color: #F8FAFC !important; /* Blanco hueso muy legible */
    }
    
    /* Título Principal */
    .main-title {
        color: #38BDF8 !important; /* Azul celeste brillante */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        text-align: center;
        font-weight: 800;
        padding-top: 10px;
        font-size: 2.6rem;
    }
    
    /* Subtítulo */
    .subtitle {
        text-align: center; 
        color: #94A3B8 !important; /* Gris claro */
        font-size: 1.1rem;
        margin-bottom: 35px;
    }
    
    /* Títulos de sección */
    .section-title {
        color: #FBBF24 !important; /* Amarillo ámbar de alto contraste */
        font-weight: 700;
        border-bottom: 2px solid #334155;
        padding-bottom: 8px;
        margin-bottom: 20px;
        font-size: 1.3rem;
    }
    
    /* Tarjetas de información y guías dinámicas (Fondo oscuro, texto contrastado) */
    .info-box {
        background-color: #1E3A8A; /* Azul marino */
        color: #E0F2FE !important; /* Azul cielo clarito */
        padding: 14px;
        border-radius: 8px;
        border-left: 5px solid #38BDF8;
        margin-top: 10px;
        margin-bottom: 15px;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    .info-box b, .info-box strong {
        color: #FBBF24 !important; /* Resaltados dentro de la caja en amarillo */
    }
    
    /* Tarjeta de resultados destacados */
    .result-card {
        background-color: #1E293B;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        border: 2px solid #10B981; /* Verde esmeralda */
        text-align: center;
        margin-top: 25px;
    }
    
    /* Texto pequeño de ayuda (como el del Car_ID) */
    .opcional-text {
        color: #A1A1AA !important;
        font-size: 0.82rem;
        margin-top: -12px;
        margin-bottom: 10px;
        display: block;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🚗 Validador & Predictor de Precios de Autos 💰</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Ajusta los parámetros sobre el fondo optimizado para calcular una tasación precisa utilizando Inteligencia Artificial.</p>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FUNCIONES AUXILIARES PARA DATAROBOT
# -----------------------------------------------------------------------------
def _request(method, url, data=None):
    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "User-Agent": "IntegrationSnippet-StandAlone-Python",
    }
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
        headers.update({"Content-Type": "application/json; encoding=utf-8"})

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
    with st.spinner("🧠 Sincronizando con DataRobot para estimar la tasación..."):
        while True:
            job_status = _request("GET", job_url)
            if not job_status:
                return None
            status = job_status["status"]
            if status in ["COMPLETED", "ABORTED", "FAILED"]:
                if status != "COMPLETED":
                    st.error("El procesamiento falló en los servidores de DataRobot.")
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
# DISEÑO DE FORMULARIO - ALTO CONTRASTE / MODO OSCURO
# -----------------------------------------------------------------------------
MARCAS_DISPONIBLES = [
    "Toyota", "Ford", "Chevrolet", "Honda", "Nissan", "Hyundai", 
    "Kia", "Volkswagen", "BMW", "Mercedes-Benz", "Audi", "Mazda", 
    "Subaru", "Jeep", "Renault", "Peugeot", "Fiat", "Suzuki"
]

with st.container():
    col1, col2, col3 = st.columns(3, gap="large")
    
    with col1:
        st.markdown("<div class='section-title'>🏢 Datos Básicos</div>", unsafe_allow_html=True)
        
        # CAMBIO SOLICITADO: Indicación clara de que car_id NO requiere ser diligenciado obligatoriamente
        car_id = st.text_input("🆔 ID del Auto (Car_ID)", value="", placeholder="Ej: 1001 (Opcional)")
        st.markdown("<span class='opcional-text'>⚠️ No es obligatorio diligenciar este campo. Si se deja vacío, el sistema asignará uno de forma automática.</span>", unsafe_allow_html=True)
        
        brand = st.selectbox("🏷️ Marca del Vehículo (Brand)", options=sorted(MARCAS_DISPONIBLES), index=0)
        model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2022, step=1)
        doors = st.slider("🚪 Cantidad de Puertas (Doors)", min_value=2, max_value=5, value=4, step=1)

    with col2:
        st.markdown("<div class='section-title'>⚙️ Rendimiento y Dimensiones</div>", unsafe_allow_html=True)
        
        engine_size = st.number_input("🔩 Tamaño del Motor en Litros (Engine_Size)", min_value=0.5, max_value=8.0, value=2.0, step=0.1)
        if engine_size < 1.6:
            st.markdown("<div class='info-box'>🚙 <b>Vehículo Pequeño:</b> Cilindrada baja. Máxima eficiencia urbana de combustible.</div>", unsafe_allow_html=True)
        elif 1.6 <= engine_size <= 3.0:
            st.markdown("<div class='info-box'>🚗 <b>Vehículo Mediano:</b> Cilindrada estándar. Equilibrio ideal entre consumo diario y respuesta en autopistas.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>🚛 <b>Vehículo Grande:</b> Alta potencia y tamaño. Ideal para camionetas comerciales, tracción pesada o SUVs familiares grandes.</div>", unsafe_allow_html=True)
            
        horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=30, max_value=1000, value=150, step=10)
        if horsepower < 120:
            st.markdown("<div class='info-box'>🏎️ <b>Potencia Pequeña:</b> Desempeño suave y conservador, ideal para recorridos citadinos estables.</div>", unsafe_allow_html=True)
        elif 120 <= horsepower <= 250:
            st.markdown("<div class='info-box'>⚡ <b>Potencia Mediana:</b> Respuesta enérgica, ágil en adelantamientos y pendientes pronunciadas.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>🔥 <b>Potencia Grande:</b> Impulso de alto rendimiento deportivo o capacidad superior de arrastre de carga.</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='section-title'>🛣️ Historial y Componentes</div>", unsafe_allow_html=True)
        mileage = st.number_input("🛣️ Kilometraje/Millas acumuladas (Mileage)", min_value=0, max_value=500000, value=30000, step=5000)
        owner_count = st.number_input("👤 Cantidad de Dueños Anteriores (Owner_Count)", min_value=0, max_value=10, value=1, step=1)
        fuel_type = st.selectbox("⛽ Tipo de Combustible (Fuel_Type)", ["Gasoline", "Diesel", "Electric", "Hybrid"])
        
        transmission = st.selectbox("🕹️ Caja de Cambios (Transmission)", ["Automatic", "Manual"])
        if transmission == "Manual":
            st.markdown("<div class='info-box'>⚙️ <b>Transmisión Pequeña/Manual:</b> Mayor control de revoluciones por parte del conductor. Mantenimiento simplificado.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='info-box'>🕹️ <b>Transmisión Avanzada/Automática:</b> Conducción relajada y transiciones imperceptibles en tráfico pesado.</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# EJECUCIÓN Y CÁLCULOS
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 Calcular Predicción del Valor del Auto", use_container_width=True, type="primary"):
    
    # Manejo dinámico del Car_ID si el usuario lo deja vacío
    final_car_id = int(car_id) if (car_id.strip().isdigit()) else 9999
    
    data_dict = {
        "Brand": [brand],
        "Car_ID": [final_car_id],
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
    resultados = ejecutar_prediccion(df_input)
    
    if resultados is not None:
        st.markdown("<div class='result-card'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #34D399; font-weight: 700; margin-top: 0;'>🎉 ¡Tasación Completada!</h2>", unsafe_allow_html=True)
        
        col_prediccion = [c for c in resultados.columns if 'prediction' in c.lower()]
        
        if col_prediccion:
            precio_estimado = resultados[col_prediccion[0]].iloc[0]
            
            st.metric(
                label="💵 VALOR ESTIMADO DEL AUTO EN EL MERCADO", 
                value=f"${precio_estimado:,.2f} USD"
            )
            st.markdown("<p style='color: #94A3B8; font-weight: 600; font-size: 0.95rem; margin-top: 15px;'>⚠️ Nota aclaratoria: Este precio ha sido calculado en <b>Dólares Estadounidenses (USD)</b>.</p>", unsafe_allow_html=True)
        else:
            st.warning("Predicción generada, pero el formato de la columna de salida cambió.")
            st.dataframe(resultados)
            
        st.markdown("</div>", unsafe_allow_html=True)
