# IMPORTS
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import mysql.connector
import pandas as pd
import time, pytz
st.set_page_config(layout="wide")



# CONNECTION
#@st.cache(allow_output_mutation=True)
def init_connection():
  try:
    conn = mysql.connector.connect(**st.secrets["mysql"])
  except Exception as e:
    st.write("Erro na conexão do Banco de Dados")

  return conn

# QUERY MANAGE
#@st.cache(ttl=60)
def run_query(conn, query):
  cursor = conn.cursor(buffered=True)
  cursor.execute(query)    

  return cursor


def bt_aceitar_callback(conn, id) -> None:
  st.write(f"TESTANDO: ID {id}")
  query = f"UPDATE alarmes_externas SET status = 'Aceito' WHERE idalarmes = {id};"

  _ = run_query(conn, query)
  conn.commit()

  st.experimental_rerun()   # Força rodar o script novamente

def bt_ignorar_callback(conn, id) -> None:
  st.write(f"TESTANDO: ID {id}")
  query = f"UPDATE alarmes_externas SET status = 'Ignorado' WHERE idalarmes = {id};"

  _ = run_query(conn, query)
  conn.commit()

  st.experimental_rerun()   # Força rodar o script novamente


def apresenta_alarmes(conn, rows) -> None:
  # Layout básico da lista de alarmes
  col_vazia1, col_alarmes, col_vazia2 = st.columns([2,1,2])

  with col_vazia1:
    st.empty()

  with col_alarmes:
    st.write("<h2>Alarmes</h2>", unsafe_allow_html=True)    # Ajustar CSS
    

    for (id, hora, _, medida, tipo, valor, vref_min, vref_max,
        unidade, tempo, prioridade, _) in rows:

        msg = f"{hora.date().strftime('%d/%m/%Y')} {hora.time()}: {medida} - {tipo}"

        # explainer = f"<h3>Tipo: {tipo}</h3><p>Ref. mín.: {vref_min} {unidade} &ensp;&ensp;&ensp; Ref. máx.: {vref_max} {unidade}</p>"
        # explainer += f"<p>Valor Alarmado: {valor} {unidade}</p>"

        msg_min = f"Valor mínimo: {vref_min} {unidade}" if vref_min else ""
        msg_max = f"Valor máximo: {vref_max} {unidade}" if vref_max else ""

        explainer = f"<h4>{hora.date().strftime('%d/%m/%Y')}&ensp;&ensp;{hora.time()} </br> {medida}&ensp;&ensp;&ensp; ({tipo})</h4>" + \
          f"<p>Valor Observado de {valor} {unidade} por mais de {tempo} min</p>" + \
            f"</br><p>Referência: </p>"

        if vref_min: 
          explainer += f"&ensp;&ensp;{msg_min}</p>"
        if vref_max:
          explainer += f"&ensp;&ensp;{msg_max}</p>"
          
        #explainer += f"<p>Valor Observado: {valor} {unidade} por mais de {tempo} min</p>"

        with st.expander(msg): # issue: Intertravamento com ID 
          st.write(explainer, unsafe_allow_html=True)
          
          if st.button("Aceitar", key=f"{id}"):
            bt_aceitar_callback(conn, id)
          if st.button("Ignorar", key=f"{id}"):
            bt_ignorar_callback(conn, id)

          st.write("\n\n")

  with col_vazia2:
    st.empty()



# FUNCAO PRINCIPAL
def main() -> None:
  # Inicia conexão e query
  conn = init_connection()

  # Executa a query
  rows = run_query(conn, "SELECT * FROM alarmes_externas WHERE status = 'Aberta';")

  # Apresenta os alarmes em aberto
  apresenta_alarmes(conn, rows)

  # Fecha a conexão com o DB
  conn.close()

  


if __name__ == "__main__":
  # update every 2 mins
  interval = 2    # min
  st_autorefresh(interval=interval*60000, key="dataframerefresh")

  main()


