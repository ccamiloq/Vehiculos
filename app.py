import streamlit as st
import pandas as pd
import os
import subprocess
import json

# Configuración de las credenciales de DataRobot (Sustituye con tus datos reales)
DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
DATAROBOT_HOST = st.secrets["DATAROBOT_HOST"]

# Configuración de la página con un toque de color y emoji
st.set_page_config(
    page_title="Predicción de Vehículos 🚗",
    page_icon="🏎️",
    layout="centered"
)

# Estilos personalizados para darle más vida y colores a la interfaz
st.markdown("""
    <style>
    .main-title {
        color: #FF4B4B;
        text-align: center;
        font-weight: bold;
    }
    .section-predict {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #00c853;
    }
    </style>
""", unsafe_allow_index=True)

st.markdown("<h1 class='main-title'>🚗 Evaluador Dinámico de Vehículos 📊</h1>", unsafe_allow_index=True)
st.write("Introduce las características del coche a continuación para calcular su estimación.")

st.divider()

# --- FORMULARIO INTERACTIVO Y EN ESPAÑOL ---
st.subheader("🛠️ Características del Vehículo")

col1, col2 = st.columns(2)

with col1:
    car_id = st.text_input("🆔 ID del Coche (Car_ID)", "12345", help="Identificador único del vehículo.")
    brand = st.selectbox("🏭 Marca (Brand)", ["Toyota", "Ford", "Chevrolet", "Honda", "Nissan", "Volkswagen", "BMW", "Mercedes-Benz", "Audi", "Otro"])
    model_year = st.number_input("📅 Año del Modelo (Model_Year)", min_value=1980, max_value=2027, value=2020)
    transmission = st.radio("⚙️ Transmisión (Transmission)", ["Manual", "Automática"], horizontal=True)
    fuel_type = st.selectbox("⛽ Tipo de Combustible (Fuel_Type)", ["Gasolina", "Diésel", "Híbrido", "Eléctrico", "Gas (GLP/GNV)"])

with col2:
    engine_size = st.number_input("🧪 Tamaño del Motor en Litros (Engine_Size)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
    horsepower = st.number_input("🐎 Caballos de Fuerza (Horsepower)", min_value=1, max_value=1000, value=150)
    doors = st.slider("🚪 Número de Puertas (Doors)", min_value=2, max_value=5, value=4)
    mileage = st.number_input("🛣️ Kilometraje / Millas (Mileage)", min_value=0, value=50000, step=1000)
    owner_count = st.number_input("👤 Número de Dueños Anteriores (Owner_Count)", min_value=0, max_value=20, value=1)

# Variable oculta o inicial para el objetivo (se suele enviar vacía o con un valor dummy si el modelo lo requiere)
price = 0 

st.divider()

# --- BOTÓN DE ACCIÓN INTERACTIVO ---
if st.button("🚀 Calcular Predicción", type="primary", use_container_width=True):
    
    # Validar que se hayan ingresado las credenciales
    if DATAROBOT_API_KEY == "TU_API_KEY_AQUI" or DATAROBOT_DEPLOYMENT_ID == "TU_DEPLOYMENT_ID_AQUI":
        st.error("⚠️ Por favor, configura tus credenciales de DataRobot (`DATAROBOT_API_KEY` y `DATAROBOT_DEPLOYMENT_ID`) al inicio del archivo `app.py`.")
    else:
        with st.spinner("🧠 Conectando con la IA de DataRobot... Por favor, espera."):
            
            # Mapas de traducción interna (si tu modelo requiere los datos en inglés para procesar)
            # Si tu modelo fue entrenado con los textos en español, puedes comentar o borrar este mapeo.
            trans_map = {"Manual": "Manual", "Automática": "Automatic", "Gasolina": "Petrol", "Diésel": "Diesel", "Híbrido": "Hybrid", "Eléctrico": "Electric", "Gas (GLP/GNV)": "Gas"}
            
            # 1. Crear el diccionario con las columnas exactas de tu imagen
            datos_usuario = {
                "Car_ID": [car_id],
                "Brand": [brand],
                "Model_Year": [model_year],
                "Engine_Size": [engine_size],
                "Fuel_Type": [trans_map.get(fuel_type, fuel_type)],
                "Transmission": [trans_map.get(transmission, transmission)],
                "Mileage": [mileage],
                "Doors": [doors],
                "Owner_Count": [owner_count],
                "Horsepower": [horsepower],
                "Price": [price]  # Target / Variable a predecir
            }
            
            # 2. Generar los archivos temporales CSV para la comunicación
            df_input = pd.DataFrame(datos_usuario)
            input_csv = "temp_input.csv"
            output_csv = "temp_output.csv"
            
            df_input.to_csv(input_csv, index=False)
            
            # 3. Construir la línea de comando para ejecutar predict.py de manera nativa
            comando = [
                "python", "predict.py",
                input_csv,
                output_csv,
                DATAROBOT_DEPLOYMENT_ID,
                "--api_key", DATAROBOT_API_KEY,
                "--host", DATAROBOT_HOST
            ]
            
            try:
                # Ejecutar el script predict.py adjunto
                resultado_proceso = subprocess.run(comando, capture_output=True, text=True, check=True)
                
                # 4. Leer el resultado devuelto por DataRobot
                if os.path.exists(output_csv):
                    df_output = pd.read_csv(output_csv)
                    
                    # Mostrar resultados de forma muy visual
                    st.balloons()
                    st.markdown("<div class='section-predict'>", unsafe_allow_index=True)
                    st.subheader("🎉 ¡Resultado de la Estimación!")
                    
                    # DataRobot suele nombrar la columna de predicción como "Prediction" o el nombre de tu target original
                    # Buscamos dinámicamente cualquier columna que tenga el resultado
                    col_prediccion = [c for c in df_output.columns if 'prediction' in c.lower() or 'price' in c.lower()]
                    
                    if col_prediccion:
                        valor_predicho = df_output[col_prediccion[0]].iloc[0]
                        # Suponiendo que el precio es un valor numérico continuo:
                        st.metric(label="💵 Precio Estimado del Vehículo", value=f"${valor_predicho:,.2f}")
                    else:
                        st.write("Datos recibidos del servidor:")
                        st.dataframe(df_output)
                        
                    st.markdown("</div>", unsafe_allow_index=True)
                else:
                    st.error("❌ El archivo de resultados no se generó de manera correcta.")
                    st.text(resultado_proceso.stderr)
                    
            except subprocess.CalledProcessError as e:
                st.error("💥 Ocurrió un error al ejecutar la predicción en DataRobot.")
                st.code(e.stderr)
                
            finally:
                # Limpieza de archivos temporales creados para la ejecución
                if os.path.exists(input_csv):
                    os.remove(input_csv)
                if os.path.exists(output_csv):
                    os.remove(output_csv)
