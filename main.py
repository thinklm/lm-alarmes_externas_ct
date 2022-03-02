# IMPORTS
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import mysql.connector
import pandas as pd
import time, pytz
st.set_page_config(layout="wide")



# CONNECTION
def init_connection():
  try:
    conn = mysql.connector.connect(**st.secrets["mysql"])
  except Exception as e:
    st.write(f"Erro na conexão do Banco de Dados: {e}")

  return conn

# QUERY MANAGE
def __run_query(conn, query):
  cursor = conn.cursor(buffered=True)
  cursor.execute(query)    

  return cursor


def bt_callback(conn, id, mode="Aceito") -> None:
  if mode in ["Aceito", "Ignorado"]:  # Modos aceitos atualmente
    query = f"UPDATE alarmes_externas SET status = '{mode}' WHERE idalarmes = {id};"

    _ = __run_query(conn, query)
    conn.commit()

    st.experimental_rerun()   # Força rodar o script novamente

  else:
    st.error("Erro no callback")


def imprime_alarmes(conn, rows, title) -> None:
  st.write(f"<h2>{title}</h2>", unsafe_allow_html=True)    

  for (id, hora, _, medida, tipo, valor, vref_min, vref_max,
      unidade, tempo, prioridade, _) in rows:

      msg = f"{hora.date().strftime('%d/%m/%Y')} - {hora.time()}: {medida} - {tipo}"
      msg_min = f"Valor mínimo: {vref_min} {unidade}" if vref_min else ""
      msg_max = f"Valor máximo: {vref_max} {unidade}" if vref_max else ""

      explainer = f"<h4>{hora.date().strftime('%d/%m/%Y')}&ensp;&ensp;{hora.time()} </br> {medida}&ensp;&ensp;&ensp; ({tipo})</h4>" + \
        f"<p>Prioridade: {prioridade}</p></br><p>Referência: "          

      if vref_min: 
        explainer += f"</br>&ensp;&ensp;{msg_min}</p>"
      if vref_max:
        explainer += f"</br>&ensp;&ensp;{msg_max}</p>"

      explainer += f"<p>Valor Observado: {valor} {unidade} por {tempo} min</p>"


      with st.expander(msg):    # ISSUE: Intertravamento com User ID
        st.write(explainer, unsafe_allow_html=True)
        if st.button("Aceitar", key=f"{id}"):
          bt_callback(conn, id, mode="Aceito")
        if st.button("Ignorar", key=f"{id}"):
          bt_callback(conn, id, mode="Ignorado")

        st.write("\n\n")




def tela_home (conn) -> None:
  st.write('<h1 style="text-align:center">Alarmes Áreas Externas</h1>', unsafe_allow_html=True)

  # Apresentação Alarmes (Tela principal)
  col_1, col_vazia, col_2 = st.columns([4,1,4])

  with col_1:
    # Executa a query
    rows_24h = __run_query(conn, "SELECT * FROM alarmes_externas WHERE status = 'Aberta' AND TIMESTAMP >= now() - INTERVAL 1 day ORDER BY prioridade DESC, TIMESTAMP DESC;")

    # Apresenta os alarmes em aberto em menos de 24h
    imprime_alarmes(conn, rows_24h, title="Alarmes nas últimas 24h")


  with col_vazia:
    st.empty()


  with col_2:
    # Executa a query
    rows_old = __run_query(conn, "SELECT * FROM alarmes_externas WHERE status = 'Aberta' AND TIMESTAMP < now() - INTERVAL 1 day ORDER BY prioridade DESC, TIMESTAMP DESC;")

    # Apresenta os alarmes em aberto em menos de 24h
    imprime_alarmes(conn, rows_old, title="Alarmes Anteriores")



# ISSUE: Tela de Análises
def tela_analises (conn):
  st.header(":hammer: Tela em fila de Construção")




# FUNCAO PRINCIPAL
def main() -> None:
  # Inicia conexão e query
  conn = init_connection()

  # Menu lateral com escolha para página a ser apresentada
  choice = st.sidebar.radio(label="Menu", options=["Home", "Análise"])

  # Apresenta os alarmes na tela principal
  if choice == "Home":  
    tela_home(conn)
  elif choice == "Análise":
    tela_analises(conn)

  # Fecha a conexão com o DB
  conn.close()

  
  

if __name__ == "__main__":
  # update every 2 mins
  interval = 2    # min
  st_autorefresh(interval=interval*60000, key="dataframerefresh")

  main()



