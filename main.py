# IMPORTS
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import numpy as np
import pandas as pd
import mysql.connector
from mysql.connector.connection import MySQLConnection, MySQLCursorBuffered
from datetime import datetime, timedelta
import plotly.figure_factory as ff
import plotly.express as px
import plotly.graph_objects as go
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
    st.write(f"Erro na conexão do Banco de Dados -> {e}")

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

  for (id, hora, _, medida, equipamento, tipo, valor, vref_min, vref_max,
      unidade, tempo, _, _, _, _) in rows:

      hora = hora - timedelta(hours=3)    # Consertando o horário para timezone UTC-3

      # Construindo a mensagem do alarme
      msg = f"{hora.date().strftime('%d/%m/%Y')} - {hora.time()}: \t {equipamento.upper()}"
      msg_min = f"Valor MÍNIMO: {vref_min} {unidade}" if vref_min else ""
      msg_max = f"Valor MÁXIMO: {vref_max} {unidade}" if vref_max else ""

      explainer = f"<h4 style='text-align:center'>{hora.date().strftime('%d/%m/%Y')}&ensp;&ensp;{hora.time()}</br>" + \
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




def __graf_count_status (df: pd.DataFrame) -> None:
  """Imprimir Gráfico de barras de distribuição por status

  Args:
      df (pd.DataFrame): Dataframe com os dados resultantes da query.
  """
  data = pd.DataFrame(df["status"].value_counts())
  data["porcentagem"] = np.round(data["status"]*100 / np.sum(data["status"]), 1)

  fig = go.Figure()

  fig.add_trace(
    go.Bar(
      x=data.index,
      y=data["porcentagem"],
      texttemplate= "%{y:.1f} %",
      marker_color = ["#e63946", "#023e8a", "#2a9d8f"]
    )
  )
  fig.update_layout({
    "font": {"size": 20},
    "title": {
      "text": "Status dos Alarmes das Áreas Externas",
      "font": {"size": 36},
    },
    "xaxis": {
      "title": {
        "text": "Status dos Alarmes",
        "font": {"size": 24}
      }
    },
    "yaxis": {
      "title": {
        "text": "Porcentagem [%]",
        "font": {"size": 24}
      }
    }
  })

  st.plotly_chart(fig)




def __graf_pareto (df: pd.DataFrame) -> None:
  """Imprimir Diagrama de Pareto das causas de ocorrÊncia de alarmes.

  Args:
      df (pd.DataFrame): Dataframe com os dados resultantes da query.
  """
  data = pd.DataFrame(df["medida"].value_counts(sort=True, ascending=False))
  data["cumsum"] = data["medida"].cumsum()
  data["porcentagem"] = np.round(data["medida"]*100 / np.sum(data["medida"]), 1)
  data["cum_porcentagem"] = data["porcentagem"].cumsum()

  pareto_barras = {
    "name": "Count", 
    "type": "bar", 
    "x": data.index,
    "y": data["medida"],
    "marker": {"color": "rgb(34,163,192)"}
  }
  pareto_cumulativo = {
    "line": {
      "color": "rgb(243,158,115)", 
      "width": 2.4
    }, 
    "name": "Cumulative Percentage", 
    "type": "scatter", 
    "x": data.index,
    "y": data["cum_porcentagem"],
    "yaxis": "y2"
  }
  pareto_limite = {
    "line": {
      "dash": "dash", 
      "color": "rgba(128,128,128,.45)", 
      "width": 1.5
    }, 
    "name": "80%", 
    "type": "scatter", 
    "x": data.index,
    "y": [80,] * len(data),
    "yaxis": "y2"
  }

  graf_data = go.Data([pareto_barras, pareto_cumulativo, pareto_limite])

  layout = {
    "font": {
      "size": 12, 
      "color": "rgb(128,128,128)", 
      "family": "Balto, sans-serif"
    }, 
    "title": "Diagrama de Pareto", 
    "xaxis": {"tickangle": -90}, 
    "yaxis": {
      "title": "Count", 
      "tickfont": {"color": "rgba(34,163,192,.75)"}, 
      "tickvals": [0, 6000, 12000, 18000, 24000, 30000], 
      "titlefont": {
        "size": 14, 
        "color": "rgba(34,163,192,.75)", 
        "family": "Balto, sans-serif"
      }
    }, 
    "legend": {
      "x": 0.83, 
      "y": 1.3, 
      "font": {
        "size": 12, 
        "color": "rgba(128,128,128,.75)", 
        "family": "Balto, sans-serif"
      }
    }, 
    "margin": {
      "b": 250, 
      "l": 60, 
      "r": 60, 
      "t": 65
    }, 
    "yaxis2": {
      "side": "right", 
      "range": [0, 101], 
      "tickfont": {"color": "rgba(243,158,115,.9)"}, 
      "tickvals": [0, 20, 40, 60, 80, 100], 
      "overlaying": "y"
    }, 
    "showlegend": True, 
    "annotations": [
      {
        "x": 1.029, 
        "y": 0.75, 
        "font": {
          "size": 14, 
          "color": "rgba(243,158,115,.9)", 
          "family": "Balto, sans-serif"
        }, 
        "text": "Cumulative Percentage", 
        "xref": "paper", 
        "yref": "paper", 
        "showarrow": False, 
        "textangle": 90
      }
    ]
  }

  fig = go.Figure(data=graf_data, layout=layout)
  st.plotly_chart(fig)




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
  st.header("Análise dos Alarmes das Áreas Externas")
  st.subheader(":hammer: Tela em Construção")
  st.write()

  # Filtros de busca para análise         # ISSUE: Filtro
  st.write()
  st.sidebar.header("Filtrar por data:")
  st.sidebar.date_input(label="Data início", key="date_inicio")
  st.sidebar.date_input(label="Data final", key="date_final")
  st.sidebar.checkbox(label="Esse mês", key="date_checkbox")
  st.sidebar.button(label="Filtrar", key="bt_date_filter")

  # Query
  query = "SELECT * FROM alarmes_externas;"
  df = pd.read_sql_query(sql=query, con=conn, parse_dates=["TIMESTAMP", "datetime_trat"])

  # Gráfico 1 - Distribuição dos alarmes por status
  __graf_count_status(df)

  # Gráfico 2 - Distribuição de Pareto dos Alarmes
  __graf_pareto(df)




# FUNCAO PRINCIPAL
def main() -> None:
  """Execução principal da aplicação.
  """
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
