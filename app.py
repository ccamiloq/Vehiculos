import streamlit as st
import pandas as pd
import json
import ssl
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Predicción de Precio de Autos",
    page_icon="🚗",
    layout="centered"
)

# --- CARGAR SECRETS ---
# Asegúrate de configurar estos valores en tu archivo .streamlit/secrets.toml
try:
    DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
    DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
    DATAROBOT_HOST = st.secrets.get("DATAROBOT_HOST", "https://app.datarobot.com")
except Exception:
    st.error("⚠️ Error al cargar las credenciales. Asegúrate de configurar los `st.secrets` correctamente.")
    st.stop()

# --- FUNCIÓN DE PREDICCIÓN (Adaptada de predict.py) ---
def realizar_prediccion(df_input):
    url = f"{DATAROBOT_HOST}/api/v2/batchPredictions/"
    
    payload = {
        "deploymentId": DATAROBOT_DEPLOYMENT_ID,
        "passthroughColumnsSet": "all"
    }
    
    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "User-Agent": "IntegrationSnippet-StandAlone-Python",
        "Content-Type": "application/json; encoding=utf-8"
    }
    
    # Crear el trabajo de predicción masiva (Batch Prediction)
    try:
        # 1. Crear el Job
        req_job = Request(url, headers=headers, data=json.dumps(payload).encode("utf-8"))
        req_job.get_method = lambda: "POST"
        
        ctx = ssl.create_default_context()
        with urlopen(req_job, context=ctx) as response:
            job_data = json.loads(response.read().decode('utf-8'))
        
        upload_url = job_data["links"]["csvUpload"]
        download_url = job_data["links"]["download"]
        
        # 2. Subir los datos en formato CSV
        csv_data = df_input.to_csv(index=False).encode('utf-8')
        headers_upload = {
            "Authorization": f"Token {DATAROBOT_API_KEY}",
            "Content-length": len(csv_data),
            "Content-type": "text/csv; encoding=utf-8",
        }
        req_upload = Request(upload_url, headers=headers_upload, data=csv_data)
        req_upload.get_method = lambda: "PUT"
        with urlopen(req_upload, context=ctx) as resp:
            pass
            
        # 3. Esperar y descargar el resultado (Polleamos de forma simplificada)
        import time
        job_url = job_data["links"]["self"]
        headers_get = {"Authorization": f"Token {DATAROBOT_API_KEY}"}
        
        for _ in range(30): # Timeout de seguridad
            req_status = Request(job_url, headers=headers_get)
            with urlopen(req_status, context=ctx) as resp:
                status_data = json.loads(resp.read().decode('utf-8'))
            
            if status_data["status"] == "COMPLETED":
                req_download = Request(download_url, headers=headers_get)
                with urlopen(req_download, context=ctx) as resp:
                    df_res = pd.read_csv(resp)
                return df_res
            elif status_data["status"] in ["FAILED", "ABORTED"]:
                raise Exception("El trabajo en DataRobot falló o fue abortado.")
            time.sleep(2)
            
        raise Exception("Tiempo de espera agotado para la predicción.")
        
    except HTTPError as e:
        raise Exception(f"Error de DataRobot API ({e.code}): {e.read().decode('utf-8')}")
    except Exception as e:
        raise Exception(f"Error en la conexión: {str(e)}")


# --- INTERFAZ DE USUARIO ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🚗 Cotizador Inteligente de Autos</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555555;'>Ingresa los datos del vehículo para calcular su valor estimado en el mercado.</p>", unsafe_allow_html=True)

# Organización visual mediante pestañas o columnas
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Identificación Básica")
    car_id = st.number_input("🆔 ID del Auto (Car_ID)", min_value=0, value=123, step=1)
    brand = st.text_input("🏢 Marca (Brand)", value="Toyota")
    model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2020, step=1)
    mileage = st.number_input("🛣️ Kilometraje / Millas (Mileage)", min_value=0, value=50000, step=1000)

with col2:
    st.subheader("🔧 Especificaciones Técnicas")
    fuel_type = st.selectbox("⛽ Tipo de Combustible (Fuel_Type)", ["Gasoline", "Diesel", "Electric", "Hybrid"])
    transmission = st.selectbox("⚙️ Transmisión (Transmission)", ["Automatic", "Manual"])
    
    # Breve descripción dinámica según la transmisión
    if transmission == "Manual":
        st.caption("ℹ️ *Ideal para autos pequeños/económicos o deportivos donde se busca mayor control.*")
    else:
        st.caption("ℹ️ *Común en autos medianos y grandes (SUVs) para una conducción más confortable.*")

    doors = st.slider("🚪 Número de Puertas (Doors)", min_value=2, max_value=5, value=4, step=1)
    owner_count = st.slider("👤 Cantidad de Dueños Anteriores (Owner_Count)", min_value=0, max_value=5, value=1, step=1)

st.write("---")
st.subheader("💪 Potencia y Motorización")

col3, col4 = st.columns(2)

with col3:
    engine_size = st.number_input("📐 Tamaño del Motor en Litros (Engine_Size)", min_value=0.0, max_value=8.0, value=2.0, step=0.1)
    # Descripción según el tamaño del motor
    if engine_size <= 1.4:
        st.info("🚗 **Auto Pequeño:** Motor compacto y de bajo consumo, ideal para la ciudad.")
    elif engine_size <= 2.5:
        st.info("🚙 **Auto Mediano:** Equilibrio óptimo entre potencia y consumo, perfecto para sedanes o SUVs compactas.")
    else:
        st.info("🚛 **Auto Grande:** Motor de alta cilindrada, diseñado para camionetas grandes, SUVs de 3 filas o deportivos.")

with col4:
    horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=10, max_value=1000, value=150, step=10)
    # Descripción según los caballos de fuerza
    if horsepower <= 110:
        st.caption("ℹ️ *Orientado a autos pequeños urbanos.*")
    elif horsepower <= 250:
        st.caption("ℹ️ *Estándar para autos medianos y viajes familiares.*")
    else:
        st.caption("ℹ️ *Común en autos grandes, camionetas de carga o vehículos de alto rendimiento.*")


st.write("---")

# --- BOTÓN DE ACCIÓN ---
if st.button("🔮 Calcular Precio Estimado", type="primary", use_container_width=True):
    
    # Crear el DataFrame con la estructura idéntica a la solicitada por el modelo
    # Se incluye 'Price' vacío en caso de que el modelo requiera la columna objetivo en el input
    input_data = {
        "Car_ID": [car_id],
        "Brand": [brand],
        "Model_Year": [model_year],
        "Mileage": [mileage],
        "Fuel_Type": [fuel_type],
        "Transmission": [transmission],
        "Doors": [doors],
        "Owner_Count": [owner_count],
        "Engine_Size": [engine_size],
        "Horsepower": [horsepower],
        "Price": [0]  
    }
    
    df_scoring = pd.DataFrame(input_data)
    
    with st.spinner("🤖 Conectando con DataRobot y calculando el precio... Por favor espera."):
        try:
            df_resultado = realizar_prediccion(df_scoring)
            
            # DataRobot suele nombrar la columna de predicción como 'Price_PREDICTION' o similar.
            # Buscaremos cualquier columna que contenga 'prediction' de manera dinámica
            col_prediccion = [c for c in df_resultado.columns if 'prediction' in c.lower()]
            
            st.success("🎉 ¡Predicción completada con éxito!")
            
            if col_prediccion:
                precio_final = float(df_resultado[col_prediccion[0]].iloc[0])
                
                # Cuadro de resultados vistoso
                st.markdown(
                    f"""
                     <div style="background-color:#D1FAE5; padding:20px; border-radius:10px; border-left: 8px solid #10B981; text-align:center;">
                        <h2 style="color:#065F46; margin:0;">Precio Estimado del Vehículo</h2>
                        <h1 style="color:#047857; margin:10px 0;">${precio_final:,.2f} USD</h1>
                        <p style="color:#065F46; font-weight:bold; margin:0;">⚠️ El precio calculado se expresa en dólares americanos (USD).</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                # Si no viene mapeado con ese nombre, mostramos la tabla completa devuelta
                st.warning("Se obtuvo respuesta, pero no se localizó explícitamente la columna de predicción.")
                st.dataframe(df_resultado)
                
        except Exception as error:
            st.error(f"❌ Ocurrió un error al procesar la solicitud: {str(error)}")
