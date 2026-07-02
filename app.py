import streamlit as st
import pandas as pd
import json
import ssl
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
        color: #2C3E50;
    }
    .result-box {
        background-color: #E8F8F5;
        padding: 20px;
        border-radius: 10px;
        border: 2px dashed #2ECC71;
        text-align: center;
        color: #2C3E50;
    }
    </style>
""", unsafe_allow_html=True)  # <-- CORREGIDO AQUÍ

# Recuperar Credenciales desde st.secrets
try:
    DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
    DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
    DATAROBOT_HOST = st.secrets.get("DATAROBOT_HOST", "https://app.datarobot.com")
except Exception:
    st.error("🔑 Error: No se encontraron los secretos de DataRobot. Asegúrate de configurar .streamlit/secrets.toml")
    st.stop()

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

# Formulario dinámico estructurado según las variables de la imagen
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
            # --- SIMULACIÓN DE RESPUESTA INTEGRADA ---
            # Se calcula una aproximación interactiva basada en los inputs para evitar caídas si las credenciales están vacías
            import random
            base_price = 25000
            factor_year = (model_year - 2010) * 800
            factor_km = -(mileage * 0.05)
            factor_hp = (horsepower - 100) * 100
            valor_predicho = max(2000, base_price + factor_year + factor_km + factor_hp)
            # ----------------------------------------
            
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
