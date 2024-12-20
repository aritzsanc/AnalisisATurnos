import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import plotly.express as px
from bs4 import BeautifulSoup
import re
 


# Función para analizar un archivo HTML
def analiza_fichero(file) :
    try :
        #with open(path, "r", encoding="utf-8") as file:
        contenido_html = file.read()
        # Analiza el HTML con BeautifulSoup
        soup = BeautifulSoup(contenido_html, "lxml")

        elementos_row = soup.find_all(id=re.compile("^row"))

        clases_busqueda = set()  # Usamos un conjunto para evitar duplicados

        # Buscar todos los elementos que contienen la clase "progress-bar"
        for elemento in soup.find_all(class_="progress-bar"):
            # Obtener todas las clases del elemento
            clases = elemento.get("class", [])
            
            # Añadir las clases que no sean "progress-bar" a la lista de acompañantes
            clases_busqueda.update(clase for clase in clases if clase != "pro gress-bar")

        # Convertir el conjunto a lista si se necesita, o imprimir directamente
        clases_busqueda = list(clases_busqueda)
        #print(clases_busqueda)

        # Crear una lista para almacenar la información de cada elemento
        data = []
        # Extraer la información específica de cada elemento
        for elemento in elementos_row:
            elemento_id = elemento.get("id")

            # Recorrer cada clase que contiene la información en "data-original-title"
            for clase in clases_busqueda:
                sub_elementos = elemento.find_all(class_=clase)
                
                for sub_elemento in sub_elementos:
                    data_original_title = sub_elemento.get("data-original-title", "")
                    
                    # Separar las líneas en cada `<br>`
                    lineas = data_original_title.split("<br>")
                    lineas = [BeautifulSoup(line, "lxml").get_text(strip=True) for line in lineas if line.strip()]

                    # Crear un diccionario con la información extraída
                    fila = {"row_id": elemento_id, "class": clase}
                    
                    # Agregar cada línea como una columna
                    for i, linea in enumerate(lineas):
                        fila[f"line_{i+1}"] = linea
                    
                    # Agregar la fila a los datos
                    data.append(fila)

        # Crear un DataFrame a partir de la lista de diccionarios
        df = pd.DataFrame(data)
        # Lista de columnas que deben estar presentes
        required_columns = [f"line_{i}" for i in range(1, 12)]

        # Añadir columnas vacías si no existen
        for col in required_columns:
            if col not in df.columns:
                df[col] = None  # O usa otro valor por defecto, como np.nan o una lista vacía
        # Mostrar el DataFrame
        #print(df.head(20))

        df['fecha'] = pd.to_datetime(df['row_id'].str.replace('row-', ''))

        clases=['planned', 'planned_holidays', 'time-absenteeism']

        df['tipo'] = df['line_1'].where(df['class'].isin(clases), "fichaje")

        # Patrón de búsqueda con regex
        patron = r"\b\d{2}:\d{2} - "#\d{2}:\d{2}\b"
        columnas = ["line_1", "line_2", "line_3", "line_4"]
        # Función para identificar la columna que contiene el patrón
        def identificar_columna_y_dividir(row):
            for col in columnas:
                if pd.notna(row[col]) and re.search(patron, str(row[col])):
                    # Dividir el valor encontrado en 'Inicio' y 'Fin'
                    tiempos = row[col].split(" - ")
                    row["Inicio_str"] = tiempos[0]
                    row["Fin_str"] = tiempos[1]
                    row["patron_hora"] = col  # Indicar la columna que contiene el patrón
                    return row  # Retorna la fila actualizada
            # Si no se encuentra el patrón, asignar valores nulos
            row["Inicio_str"] = None
            row["Fin_str"] = None
            row["patron_hora"] = None
            return row

        # Aplicar la función fila por fila
        df = df.apply(identificar_columna_y_dividir, axis=1)
        #print(df.head(20))

        df['Inicio'] = pd.to_datetime(df['fecha'].astype(str) + " " + df['Inicio_str'], errors='coerce', format='%Y-%m-%d %H:%M')
        df['Fin'] = pd.to_datetime(df['fecha'].astype(str) + " " + df['Fin_str'], errors='coerce', format='%Y-%m-%d %H:%M')

        df['metodo_ini'] = np.nan

        #Entradas sin marcador en linea_5
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & ~(df['line_5'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = 'Automatico'
        #Entradas con marcador en linea_5
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & (df['line_5'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = df.loc[mask, 'line_5']
        #Entradas sin marcador en linea_5
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & ~(df['line_5'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = 'Automatico'
        #Entradas con marcador en linea_6
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & (df['line_6'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = df.loc[mask, 'line_6']

        #Entradas sin marcador (teletrabajo, desplazamiento)
        mask = (df['line_2'].str.contains('Entrada', case=False, na=False)) & ~(df['line_3'].str.contains('Check', case=False, na=False))
        df.loc[mask, 'metodo_ini'] = df.loc[mask, 'line_3']

        #Salidas sin marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & ~(df['line_9'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] ='Automatico'
        #Salidas con marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & (df['line_9'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_9']
        #Salidas con marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & (df['line_10'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_10']

        #Salidas sin marcador
        mask = (df['line_6'].str.contains('Salida', case=False, na=False)) & ~(df['line_7'].str.contains('Check', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_7']

        #Salidas sin marcador
        mask = (df['line_5'].str.contains('Salida', case=False, na=False)) 
        df.loc[mask, 'metodo_fin'] ='Automatico'

        #Salidas con marcador
        mask = (df['line_7'].str.contains('Salida', case=False, na=False)) & (df['line_10'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_10']
        #Salidas con marcador
        mask = (df['line_7'].str.contains('Salida', case=False, na=False)) & (df['line_11'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] = df.loc[mask, 'line_11']
        #Salidas sin marcador
        mask = (df['line_7'].str.contains('Salida', case=False, na=False)) & ~(df['line_10'].str.contains('Tipo', case=False, na=False)) & ~(df['line_11'].str.contains('Tipo', case=False, na=False))
        df.loc[mask, 'metodo_fin'] ='Automatico'

        df['tipo'] = df['tipo'].str.replace(r"^\[\-\] ", "", regex=True)
        df['metodo_ini'] = df['metodo_ini'].str.replace(r"Tipo: ", "", regex=True)
        df['metodo_fin'] = df['metodo_fin'].str.replace(r"Tipo: ", "", regex=True)

        #Cálculo de tiempo trabajado
        df['horas'] =  (df['Fin'] - df['Inicio']).dt.total_seconds() / 3600

        columnas_a_eliminar = ['patron_hora', 'row_id', 'line_1', 'line_2', 'line_3', 'line_4', 'line_5', 'line_6', 'line_7', 'line_8', 'line_9', 'line_10', 'line_11', 'Inicio_str', 'Fin_str']
        df["Inicio"] = df["Inicio"].dt.strftime("%H:%M")  # Formato HH:MM
        df["Fin"] = df["Fin"].dt.strftime("%H:%M")        # Formato HH:MM
        df['Semana'] = df['fecha'].dt.isocalendar().week
        df['combi'] = df['class'] + '_' + df['tipo']

        # Eliminar las columnas del DataFrame
        df = df.drop(columns=columnas_a_eliminar)
        #print(df.head(50))

        return False, df

    except Exception as e:
        # En caso de error, devolvemos error = True y un DataFrame vacío
        print(f"Error al abrir o analizar el archivo: {e}")
        return True, pd.DataFrame()  # Devuelve True para error y un DataFrame vacío#hasta aqui la función que analiza el fichero html descargado

st.set_page_config(layout="wide")
#Para que las tablas ocupe todo el espacio
st.markdown(
    """
    <style>
    .main {
        max-width: 80% !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# Título de la aplicación
st.title("Visor de Datos ATurnos")
# Barra lateral para la selección del archivo y opciones de filtrado
st.sidebar.header("Opciones")

# Cargar archivo desde la barra lateral
uploaded_file = st.sidebar.file_uploader("Selecciona un archivo html", type=["html"])
#print(uploaded_file)
# Crear el panel principal a la derecha
if uploaded_file is not None:
    st.session_state.show_image = False
    error, df = analiza_fichero(uploaded_file)
    required_columns = ['class', 'tipo']
    missing_columns = [col for col in required_columns if col not in df.columns]
    print(missing_columns)
    if (df.empty) or (error==True) or (len(missing_columns) > 0):
        st.subheader("El fichero cargado no es correcto. No contiene la información requerida")
    else :
        # Mostrar los datos en el panel derecho
        st.subheader("Datos cargados:")

        # Selección de columnas para filtrar y graficar
        #solo_fichajes = st.sidebar.checkbox("Mostrar solo fichajes")
        #if solo_fichajes is True:
        #    df_filtered = df[df["class"]=="time-checkin"]
        #else: 
        #    df_filtered = df
        df_filtered = df
        st.dataframe(df_filtered, use_container_width=True)

        st.write("Sumas totales agrupadas")
        totales = df.groupby(['class', 'tipo'], as_index=False)['horas'].sum()
        st.dataframe(totales)
        tabla_pivot_filt = df_filtered.pivot_table(
            values='horas',  # Columna a agregar
            index='Semana',  # Filas: número de semana
            columns='combi',  # Columnas: combinaciones únicas
            aggfunc='sum',  # Agregación: suma
            fill_value=0  # Rellenar valores faltantes con 0
        )
        st.write("Totales por semana")
        st.dataframe(tabla_pivot_filt)
        
        filtro_clases = st.sidebar.multiselect(f"Selecciona valores de class", df["class"].unique(), default=["time-checkin"])
        #columnas_numericas = df.select_dtypes(include='number').columns.tolist()
        #columnas = df.columns.tolist()

        # Selección de columna para filtrar
        #columna_filtro = st.sidebar.selectbox("Selecciona la columna para filtrar", columnas)
        #if columna_filtro:
        #    valores_filtro = st.sidebar.multiselect(f"Selecciona valores de '{columna_filtro}'", df[columna_filtro].unique())
        st.subheader("Tablas aplicando el filtro seleccionado")

        # Aplicar filtro
        if filtro_clases:
            df_filtered = df[df["class"].isin(filtro_clases)]
            st.write(f"Datos filtrados por class")
            st.dataframe(df_filtered, use_container_width=True)
            totales_filt = df_filtered.groupby(['class', 'tipo'], as_index=False)['horas'].sum()
            # Crear una tabla dinámica
            tabla_pivot_filt = df_filtered.pivot_table(
                values='horas',  # Columna a agregar
                index='Semana',  # Filas: número de semana
                columns='combi',  # Columnas: combinaciones únicas
                aggfunc='sum',  # Agregación: suma
                fill_value=0  # Rellenar valores faltantes con 0
            )
            st.write("Sumas totales agrupadas")
            st.dataframe(totales_filt)
            st.write("Totales por semana")
            st.dataframe(tabla_pivot_filt)

        # Selección de columnas para gráficos
        def no_comments():
            '''
            st.sidebar.subheader("Opciones de Gráficos")
            
            columna_x = st.sidebar.selectbox("Selecciona la columna para el eje X", columnas_numericas)
            columna_y = st.sidebar.selectbox("Selecciona la columna para el eje Y", columnas_numericas)

            
            if columna_x and columna_y:
                # Crear gráfico
                st.subheader("Gráfico de Datos")
                fig, ax = plt.subplots()
                ax.plot(df[columna_x], df[columna_y], marker='o', linestyle='-')
                ax.set_xlabel(columna_x)
                ax.set_ylabel(columna_y)
                ax.set_title(f"Gráfico de {columna_y} vs {columna_x}")
                
                # Mostrar gráfico
                st.pyplot(fig)
            
        filters = {}
        colors = {}

        # Checkboxes dinámicos para cada valor único en la columna "Tipo"
        for tipo in df["tipo"].unique():
            st.sidebar.subheader(f"{tipo}")
            
            # Checkbox para filtrar por cada tipo
            is_selected = st.sidebar.checkbox(f"Incluir {tipo}", value=True)
            filters[tipo] = is_selected
            
            # Color Picker asociado al tipo
            color = st.sidebar.color_picker(f"Color para {tipo}", "#ffffff")
            colors[tipo] = color

        # Aplicar filtros según los checkboxes seleccionados
        selected_types = [tipo for tipo, is_selected in filters.items() if is_selected]
        filtered_df = df[df["tipo"].isin(selected_types)]

        # Aplicar colores dinámicos a la tabla
        def apply_styles(row):
            color = colors.get(row["tipo"], "#ffffff")  # Obtener el color para el tipo
            return [f"background-color: {color}"] * len(row)
            '''


else:
    st.subheader("Descarga la página de ATurnos eligiendo los meses que quieres importar")
    st.write("Entra en la página de ATurnos")
    st.write("https://www.aturnos.com/puntos_detalle_trabajador")
    st.write("Selecciona las fechas de las que quieras procesar los fichajes")
    st.image('./CapturaEjemplo.png', caption='Mi Imagen PNG', use_container_width=True)
    st.write("Guarda la página web en tu ordenador (Ctrl+s)") 
    st.write("Carga el fichero usando el menu de la barra lateral")
     
