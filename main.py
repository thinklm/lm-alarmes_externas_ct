# IMPORTS
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import mysql.connector
from mysql.connector.connection import MySQLConnection, MySQLCursorBuffered
from datetime import datetime, timedelta
st.set_page_config(layout="wide")


# CONNECTION
def __init_connection() -> MySQLConnection:
  """Inicia a conexão com o BD MySQL com os dados contidos no arquivo secrets.toml.

  Returns:
      MySQLConnection: Conexão com o banco.
  """
  try:
    conn = mysql.connector.connect(**st.secrets["mysql"])
  except Exception as e:
    st.write(f"Erro na conexão do Banco de Dados: {e}")

  return conn

# QUERY MANAGE
def __run_query(conn: MySQLConnection, query: str) -> MySQLCursorBuffered:
  """Exceuta queries no banco conectado.

  Args:
      conn (MySQLConnection): Conexão com o MySQL.
      query (str): Query a ser executada no banco.

  Returns:
      MySQLCursorBuffered: Iterator com o resultado da query.
  """
  cursor = conn.cursor(buffered=True)
  cursor.execute(query)    

  return cursor


def __bt_callback(conn: MySQLConnection, id: int, mode: str="Aceito") -> None:
  """Função de callback para os botões de Aceitar e Ignorar os alarmes

  Args:
      conn (MySQLConnection): Conexão com o MySQL.
      id (int): ID correspondente à linha na tabela MySQL.
      mode (str, optional): Modo de tratamento do alarme. Defaults to "Aceito".
  """
  if (mode in ["Aceito", "Ignorado"]) & (st.session_state[f"user_id_input_{id}"] != ""):  # Modos aceitos atualmente
    user_id = st.session_state[f"user_id_input_{id}"]
    datetime_trat = datetime.utcnow()

    query = f"UPDATE alarmes_externas " + \
      f"SET status = '{mode}', datetime_trat = '{datetime_trat}', user_id = '{user_id}' " + \
      f"WHERE idalarmes = {id};"

    _ = __run_query(conn, query)
    conn.commit()

    st.experimental_rerun()   # Força rodar o script novamente

  else:
    st.error("Erro: Verifique se digitou o ID de usuário!")


def __imprime_alarmes(conn: MySQLConnection, rows: MySQLCursorBuffered, title:str) -> None:
  """Imprime os alarmes em expanders a partir de queries prévias.

  Args:
      conn (MySQLConnection): Conexão com o MySQL.
      rows (MySQLCursorBuffered): Resultado da query a ser iterado contendo os alarmes a serem impressos.
      title (str): Título para a colunas de alarmes.
  """
  st.write(f"<h2>{title}</h2>", unsafe_allow_html=True)    

  for (id, hora, _, medida, tipo, valor, vref_min, vref_max,
      unidade, tempo, prioridade, _, _, _) in rows:

      hora = hora - timedelta(hours=3)    # Consertando o horário para timezone UTC-3

      # Construindo a mensagem do alarme
      msg = f"{hora.date().strftime('%d/%m/%Y')} - {hora.time()}: {medida} - {tipo}"
      msg_min = f"Valor MÍNIMO: {vref_min} {unidade}" if vref_min else ""
      msg_max = f"Valor MÁXIMO: {vref_max} {unidade}" if vref_max else ""

      explainer = f"<h4 style='text-align:center'>{hora.date().strftime('%d/%m/%Y')}&ensp;&ensp;{hora.time()}&ensp;&ensp; P {prioridade}</br>" + \
        f"</br> {medida} </br> Tipo:&ensp;&ensp; {tipo}</h4>" + \
        f"</p><p style='text-align:center'>Observado: {valor} {unidade} por {tempo} min</p>" + \
        f"<p style='text-align:center'>Referência: </br>"          

      if vref_min: 
        explainer += f"&ensp;&ensp;{msg_min}</br>"
      if vref_max:
        explainer += f"&ensp;&ensp;{msg_max}"
      explainer += "</p>"      

      # Imprimindo mensagem e tratamento dos alarmes.
      with st.expander(msg): 
        st.write(explainer, unsafe_allow_html=True)
        st.write("\n\n")

        st.text_input(label="ID de Usuário:", max_chars=10, key=f"user_id_input_{id}")
        if st.button("Aceitar", key=f"{id}",):
          __bt_callback(conn, id, mode="Aceito")
        if st.button("Ignorar", key=f"{id}"):
          __bt_callback(conn, id, mode="Ignorado")

        st.write("\n\n")




def __tela_home (conn: MySQLConnection) -> None:
  """Apresenta os alarmes em aberto na tela principal.

  Args:
      conn (MySQLConnection): Conexão com o MySQL.
  """
  st.write('<h1 style="text-align:center">Alarmes Áreas Externas</h1>', unsafe_allow_html=True)

  # Contrução do layout de apresentação da Tela principal
  col_1, col_vazia, col_2 = st.columns([4,1,4])

  with col_1:
    # Executa a query para obter alarmes abertos nas últimas 24h
    rows_24h = __run_query(conn, "SELECT * FROM alarmes_externas WHERE status = 'Aberta' AND TIMESTAMP >= now() - INTERVAL 1 day ORDER BY prioridade DESC, TIMESTAMP DESC;")

    # Apresenta os alarmes em aberto em menos de 24h
    __imprime_alarmes(conn, rows_24h, title="Alarmes nas últimas 24h")


  with col_vazia:
    st.empty()


  with col_2:
    # Executa a query para obter alarmes abertos antes das últimas 24h
    rows_old = __run_query(conn, "SELECT * FROM alarmes_externas WHERE status = 'Aberta' AND TIMESTAMP < now() - INTERVAL 1 day ORDER BY prioridade DESC, TIMESTAMP DESC;")

    # Apresenta os alarmes em aberto em menos de 24h
    __imprime_alarmes(conn, rows_old, title="Alarmes Anteriores")



# ISSUE: Tela de Análises
def __tela_analise (conn: MySQLConnection) -> None:
  st.header(":hammer: Tela em fila de Construção")




# FUNCAO PRINCIPAL
def main() -> None:
  # Inicia conexão e query
  conn = __init_connection()

  # Menu lateral com escolha para página a ser apresentada
  choice = st.sidebar.radio(label="Menu", options=["Home", "Análise"])

  # Apresenta os alarmes na tela principal
  if choice == "Home":  
    __tela_home(conn)
  elif choice == "Análise":
    __tela_analise(conn)

  # Fecha a conexão com o DB
  conn.close()

  
  

if __name__ == "__main__":
  # update every 2 mins
  interval = 2    # Intervalo de atualização (em minutos)
  st_autorefresh(interval=interval*60000, key="dataframerefresh")

  main()
