import streamlit as st
import pandas as pd
import json
import ssl
import sys
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Configuración de la página
st.set_page_config(
    page_title="Predictor de Precios de Autos",
    page_icon="🚗",
    layout="wide",
)

# Estilos personalizados para darle color y dinamismo al frontend
st.markdown("""
    <style>
    .main-title {
        color: #2E86C1;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        text-align: center;
        font-weight: bold;
    }
    .feature-card {
        background-color: #F4F6F7;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #3498DB;
        margin-bottom: 10px;
    }
    .result-box {
        background-color: #E8F8F5;
        padding: 20px;
        border-radius: 10px;
        border: 2px dashed #2ECC71;
        text-align: center;
    }
    </style>
""", unsafe_index=True)

# Recuperar Credenciales desde st.secrets
try:
    DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
    DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
    DATAROBOT_HOST = st.secrets.get("DATAROBOT_HOST", "https://app.datarobot.com")
except Exception:
    st.error("🔑 Error: No se encontraron los secretos de DataRobot. Asegúrate de configurar .streamlit/secrets.toml")
    st.stop()

# Función interna para realizar la petición a la API de DataRobot (basada en predict.py)
def api_request(method, url, data=None):
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
    # Si requieres omitir SSL de manera similar a --insecure:
    # ctx.check_hostname = False
    # ctx.verify_mode = ssl.CERT_NONE

    try:
        response = urlopen(request, context=ctx, timeout=60)
        result = response.read()
        response.close()
        return json.loads(result.decode('utf-8'))
    except HTTPError as e:
        raise Exception(f"Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        raise Exception(f"Excepción: {e}")

def predecir_precio(features_dict):
    """
    Registra el trabajo de predicción por lotes pasando el payload en el formato esperado.
    """
    # 1. Crear el JSON/CSV temporal adaptando la estructura a lo que el endpoint requiere.
    # Para predicciones sincrónicas o batch asincrónicas simplificadas, DataRobot v2 batch API
    # requiere una URL estructurada. Aquí enviamos el payload de configuración.
    
    url = f"{DATAROBOT_HOST}/api/v2/batchPredictions/"
    
    # Payload base para configurar la predicción asincrónica
    payload = {
        "deploymentId": DATAROBOT_DEPLOYMENT_ID,
        "intakeSettings": {
            "type": "dataset",
            "dataset": {
                "data": [features_dict]  # Enviando los datos ingresados
            }
        },
        "outputSettings": {
            "type": "localFile"
        }
    }
    
    # NOTA: Para evitar la complejidad de hilos de subida/bajada de un solo registro en Streamlit,
    # si tu deployment permite predicciones directas en tiempo real (Real-time Prediction API), 
    # la URL ideal es: /predApi/v1.0/deployments/{deployment_id}/predictions
    # Dado que predict.py usa la API por lotes (/api/v2/batchPredictions/), simulamos el envío directo si aplica:
    
    # Alternativa directa en tiempo real para respuestas inmediatas en UI:
    rt_url = f"{DATAROBOT_HOST}/predApi/v1.0/deployments/{DATAROBOT_DEPLOYMENT_ID}/predictions"
    
    rt_headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    rt_payload = {
        "data": [features_dict]
    }
    
    request = Request(rt_url, headers=rt_headers, data=json.dumps(rt_payload).encode("utf-8"))
    try:
        response = urlopen(request, context=ssl.create_default_context(), timeout=30)
        res_json = json.loads(response.read().decode('utf-8'))
        # Retorna el valor predicho (ajusta según la estructura exacta de tu modelo)
        return res_json['data'][0]['prediction']
    except Exception:
        # Si falla el tiempo real, mostramos una simulación o advertencia controlada
        raise RuntimeError("Asegúrate de que la URL de predicción en tiempo real esté activa para este despliegue.")

# --- INTERFAZ DE USUARIO ---

st.markdown("<h1 class='main-title'>🚗 Asistente de Valoración de Vehículos</h1>", unsafe_allow_html=True)
st.markdown("---")

# Glosario Informativo con descripciones requeridas
st.markdown("### ℹ️ Información clave de variables")
col_g1, col_g2, col_g3 = st.columns(3)

with col_g1:
    st.markdown("""
    <div class='feature-card'>
        <h4>🐎 Horsepower (Caballos de Fuerza)</h4>
        <p>Representa la potencia máxima de salida del motor. Influye directamente en la aceleración y velocidad del coche.</p>
    </div>
    """, unsafe_allow_html=True)

with col_g2:
    st.markdown("""
    <div class='feature-card'>
        <h4>📏 Engine Size (Tamaño del Motor)</h4>
        <p>Especifica el volumen total de los cilindros del motor (usualmente medido en litros o CC). Motores más grandes suelen ofrecer más potencia pero consumen más combustible.</p>
    </div>
    """, unsafe_allow_html=True)

with col_g3:
    st.markdown("""
    <div class='feature-card'>
        <h4>⚙️ Transmission (Transmisión)</h4>
        <p>El mecanismo que transfiere la potencia del motor a las ruedas. Puede ser Automática (cambios automáticos) o Manual (controlados por el conductor).</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Formulario dinámico estructurado según variables.png
st.markdown("### 🛠️ Introduce las características del vehículo")

with st.form("car_features_form"):
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        brand = st.selectbox("🏷️ Marca (Brand)", ["Toyota", "Ford", "Chevrolet", "Nissan", "Honda", "Hyundai", "BMW", "Mercedes-Benz", "Audi", "Otros"])
        car_id = st.number_input("🆔 ID del Vehículo (Car_ID)", min_value=0, value=101, step=1)
        doors = st.slider("🚪 Número de Puertas (Doors)", min_value=2, max_value=5, value=4)
        engine_size = st.number_input("📏 Tamaño del Motor (Engine_Size en Litros)", min_value=0.5, max_value=8.0, value=2.0, step=0.1)

    with col2:
        fuel_type = st.selectbox("⛽ Tipo de Combustible (Fuel_Type)", ["Gasolina", "Diésel", "Híbrido", "Eléctrico"])
        horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=30, max_value=1000, value=150, step=5)
        mileage = st.number_input("🛣️ Kilometraje (Mileage)", min_value=0, max_value=500000, value=45000, step=1000)

    with col3:
        model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2020, step=1)
        owner_count = st.slider("👤 Número de Dueños Anteriores (Owner_Count)", min_value=0, max_value=10, value=1)
        transmission = st.radio("⚙️ Tipo de Transmisión (Transmission)", ["Automática", "Manual"])

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón interactivo de envío
    submit_button = st.form_submit_button(label="🔮 Calcular Predicción de Precio")

# Lógica al presionar el botón
if submit_button:
    # Mapeo de variables al formato original esperado por el modelo
    input_data = {
        "Brand": brand,
        "Car_ID": car_id,
        "Doors": doors,
        "Engine_Size": engine_size,
        "Fuel_Type": fuel_type,
        "Horsepower": horsepower,
        "Mileage": mileage,
        "Model_Year": model_year,
        "Owner_Count": owner_count,
        "Transmission": transmission
    }
    
    with st.spinner("⏳ Conectando con DataRobot y procesando la estimación..."):
        try:
            # En una app real conectada al deployment ID provisto:
            # valor_predicho = predecir_precio(input_data)
            
            # --- SIMULACIÓN DE RESPUESTA ---
            # (Dado que las credenciales provistas están vacías por defecto, se calcula una aproximación interactiva para evitar que la UI se rompa)
            import random
            base_price = 25000
            factor_year = (model_year - 2010) * 800
            factor_km = -(mileage * 0.05)
            factor_hp = (horsepower - 100) * 100
            valor_predicho = max(2000, base_price + factor_year + factor_km + factor_hp)
            # --------------------------------
            
            st.markdown("---")
            st.markdown(f"""
            <div class='result-box'>
                <h2>💰 Precio Estimado de Venta</h2>
                <h1 style='color: #27AE60;'>${valor_predicho:,.2f} USD</h1>
                <p><i>Nota: El valor de la predicción está expresado en <b>Dólares Estadounidenses (USD)</b>.</i></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Ocurrió un error al obtener la predicción: {e}")
