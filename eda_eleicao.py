import pandas as pd
import numpy as np
from IPython.display import display
import plotly.express as px
import matplotlib.pyplot as plt
from plotnine import *
import seaborn as sns
import streamlit as st
from PIL import Image


# Cria um dataframe incluindo ao dataset as siglas dos candidatos juntamente
# ao dados dos candidatos que possue o número de votos
@st.cache
def trata_dados_partidos(data1, data2):
    # data1
    remover = ['DATA_GERACAO', 'HORA_GERACAO', 'SIGLA_UE']

    data1.columns = data1.iloc[0]
    data1 = data1.drop(index=0)
    data1 = data1.drop(columns=remover)

    # data2
    # dados_partidos é um dataframe/ glossário dos códigos dos candidatos e seus partidos

    dados_partidos = data2[['NR_CANDIDATO', 'SG_PARTIDO']].copy()
    dados_partidos2 = data2[['NR_PARTIDO', 'SG_PARTIDO']].copy()

    dados_partidos = pd.DataFrame(np.insert(dados_partidos.values, 0, values=[95, 'VOTO BRANCO'], axis=0))
    dados_partidos = pd.DataFrame(np.insert(dados_partidos.values, 0, values=[96, 'VOTO NULO'], axis=0))

    dados_partidos = dados_partidos.rename(columns={0: 'NUM_VOTAVEL', 1: 'SG_PARTIDO'})
    dados_partidos2 = dados_partidos2.rename(columns={'NR_PARTIDO': 'NUM_VOTAVEL'})

    dados_partidos = dados_partidos.drop_duplicates(subset=['NUM_VOTAVEL'], keep='first')
    dados_partidos2 = dados_partidos2.drop_duplicates(subset=['NUM_VOTAVEL'], keep='first')

    glossario_partidos = pd.concat([dados_partidos, dados_partidos2])

    glossario_partidos = glossario_partidos.drop_duplicates(subset=['NUM_VOTAVEL'], keep='first')

    # Glossario nome dos vereadores

    dados_nomes = data2[data2['CD_CARGO'] == 13][['NR_CANDIDATO', 'NM_CANDIDATO', 'CD_MUNICIPIO']]

    dados_nomes = pd.DataFrame(np.insert(dados_nomes.values, 0, values=[95, 'VOTO BRANCO', 81051], axis=0))
    dados_nomes = pd.DataFrame(np.insert(dados_nomes.values, 0, values=[96, 'VOTO NULO', 81051], axis=0))

    dados_nomes = dados_nomes.rename(columns={0: 'NUM_VOTAVEL', 1: 'NM_CANDIDATO', 2: 'CODIGO_MUNICIPIO'})

    dados_nomes = dados_nomes.drop_duplicates(subset=['NM_CANDIDATO'], keep='first')

    # data_merge é o
    # todo dos dados novamente, porém agregando as siglas do partido aos dados

    data_merge = pd.merge(data1, glossario_partidos, how='left', on='NUM_VOTAVEL')

    data_merge_nomes = pd.merge(data_merge, dados_nomes, how='left', on=['NUM_VOTAVEL', 'CODIGO_MUNICIPIO'])

    return data1, data2, dados_partidos, data_merge, data_merge_nomes

@st.cache
def trata_vereador(data_merge, glossario_endereco):
    dados_vereador = data_merge[data_merge['CODIGO_CARGO'] == 13]

    dados_vereador = dados_vereador[dados_vereador['CODIGO_MUNICIPIO'] == 81051]

    dados_vereador.fillna('VOTO EM LEGENDA', inplace=True)

    # df com endereço para cada zona/seção
    glossario_endereco.rename(columns=({'ZONA': 'NUM_ZONA', 'SEÇÃO': 'NUM_SECAO'}), inplace=True)

    dado_endereco = pd.merge(dados_vereador, glossario_endereco, how='left', on=['NUM_ZONA', 'NUM_SECAO'])

    dist_votos = dado_endereco.groupby(['BAIRRO', 'SG_PARTIDO'])['QTDE_VOTOS'].sum().to_frame()
    dist_votos = dist_votos.reset_index()

    return dados_vereador, dado_endereco

@st.cache
def trata_bairro(dado_endereco):
    dist_votos = dado_endereco.groupby(['BAIRRO', 'SG_PARTIDO', 'NM_CANDIDATO'])['QTDE_VOTOS'].sum().to_frame()
    dist_votos = dist_votos.reset_index()

    return dist_votos

@st.cache
def trata_candidato(dado_endereco):
    dist_candidatos = dado_endereco.groupby(['BAIRRO', 'SG_PARTIDO', 'NM_CANDIDATO', 'NUM_VOTAVEL'])[
        'QTDE_VOTOS'].sum().to_frame()
    dist_candidatos = dist_candidatos.reset_index()

    return dist_candidatos

@st.cache
def gap2016(filiados,dado_endereco):
    colunas = ['NOME COMPLETO', 'Partido (2020)']
    candidatos = filiados[colunas]
    candidatos = candidatos.rename(columns={'NOME COMPLETO': 'NM_CANDIDATO'})

    cand2016 = dado_endereco[['NM_CANDIDATO', 'SG_PARTIDO']].drop_duplicates(subset='NM_CANDIDATO')

    cand2016.drop(cand2016.loc[cand2016['NM_CANDIDATO'] == 'VOTO EM LEGENDA'].index, inplace=True)
    cand2016.drop(cand2016.loc[cand2016['NM_CANDIDATO'] == 'VOTO BRANCO'].index, inplace=True)
    cand2016.drop(cand2016.loc[cand2016['NM_CANDIDATO'] == 'VOTO NULO'].index, inplace=True)

    resp2020 = pd.merge(candidatos, cand2016, how='outer', on=['NM_CANDIDATO'])

    respambos = pd.merge(candidatos, cand2016, how='inner', on=['NM_CANDIDATO'])

    respcomp = pd.merge(dado_endereco, respambos[['NM_CANDIDATO', 'Partido (2020)']], how='left', on=['NM_CANDIDATO'])

    respcomp.drop(respcomp.loc[respcomp['NM_CANDIDATO'] == 'VOTO EM LEGENDA'].index, inplace=True)
    respcomp.drop(respcomp.loc[respcomp['NM_CANDIDATO'] == 'VOTO BRANCO'].index, inplace=True)
    respcomp.drop(respcomp.loc[respcomp['NM_CANDIDATO'] == 'VOTO NULO'].index, inplace=True)

    gapvotos = respcomp[respcomp['Partido (2020)'].isna()].groupby(['BAIRRO', 'SG_PARTIDO'])[
        'QTDE_VOTOS'].sum().sort_values(ascending=False).to_frame()
    gapvotos = gapvotos.reset_index()

    return gapvotos


# QUANTIDADE DE VOTOS QUE CADA PARTIDO RECEBEU POR BAIRRO
@st.cache(suppress_st_warning=True)
def grafico_bairros2(lista_bairros, dist_votos):
    i = 1
    for c in lista_bairros:
        fig = plt.figure(figsize=(8, 8))
        frame = dist_votos[dist_votos['BAIRRO'] == c]
        fig = px.bar(frame, x='QTDE_VOTOS', y='SG_PARTIDO', color='NM_CANDIDATO', orientation='h',
                     height=800, width=800)

        fig.update_layout(
            title=c,
            legend_title="Legend Title",
            font=dict(size=10)
        )
        fig.update_yaxes(categoryorder='total descending')

        st.plotly_chart(fig, use_container_width=False)

        i = i + 1

# QUANTIDADE DE VOTOS QUE CADA CANDIDATO RECEBEU POR BAIRRO
@st.cache(suppress_st_warning=True)
def grafico_candidatos(lista_bairros,dist_candidatos):
    i = 1
    percentil = np.percentile(dist_candidatos['QTDE_VOTOS'], 75)
    media = np.mean(dist_candidatos['QTDE_VOTOS'])
    for c in lista_bairros:
        fig = plt.figure(figsize=(20, 30))
        frame = dist_candidatos[(dist_candidatos['BAIRRO'] == c)]
        frame = frame[frame['QTDE_VOTOS'] > percentil].sort_values(by='QTDE_VOTOS', ascending=False)

        #         ax = sns.barplot(y=frame['NM_CANDIDATO'], x=frame['QTDE_VOTOS'], ci=None)
        fig = px.bar(frame, x="QTDE_VOTOS", y="NM_CANDIDATO", color='SG_PARTIDO', orientation='h',
                     height=800, width=800)

        fig.update_layout(
            title=c,
            legend_title="Legend Title",
            font=dict(size=7)
        )
        fig.update_yaxes(dtick=0.5)
        fig.update_yaxes(categoryorder='total descending')

        st.plotly_chart(fig, use_container_width=False)
        i = i + 1

# QUANTIDADE DE VOTOS QUE UM CANDIDATO RECEBEU EM CADA BAIRRO
@st.cache(suppress_st_warning=True)
def candidatos(lista_candidato, dist_candidatos):
    h = 1
    percentil = np.percentile(dist_candidatos['QTDE_VOTOS'], 75)
    media = np.mean(dist_candidatos['QTDE_VOTOS'])

    for c in lista_candidato:
        fig = plt.figure(figsize=(12, 8))

        candidato = dist_candidatos[dist_candidatos['NM_CANDIDATO'] == c]
        candidato = candidato[candidato['QTDE_VOTOS'] > percentil].sort_values(by='QTDE_VOTOS', ascending=False)

        fig = px.bar(candidato, y="BAIRRO", x="QTDE_VOTOS", color='SG_PARTIDO', orientation='h',
                     height=800, width=800)

        fig.update_layout(
            title=c,
            legend_title="Sigla partido",
            font=dict(size=7)
        )
        fig.update_yaxes(dtick=0.5)
        fig.update_yaxes(categoryorder='total descending')

        st.plotly_chart(fig, use_container_width=False)

        h = h + 1

@st.cache(suppress_st_warning=True)
def grafico_gap(gapvotos):
    fig = px.bar(gapvotos, x="QTDE_VOTOS", y="BAIRRO", color='SG_PARTIDO', orientation='h',
                 height=800, width=800)

    fig.update_layout(
        title="Plot Title",
        legend_title="Legend Title",
        font=dict(
            size=10,
        )
    )
    fig.update_yaxes(categoryorder='total ascending')
    st.plotly_chart(fig, use_container_width=False)


def main():
    image = Image.open('monica.png')
    st.image(image,
    use_column_width = True)





    # Opção de entrada por senha
    password = st.sidebar.text_input("Digite a senha", type="password")

    if password == '':
        st.title('Análise exporatória de dados de eleições de Florianópolis')

        st.header('Em desenvolvimento')
        # st.write('Preview dos dados', df1.head())


    elif (password != 'monica19022') and (password != ''):
        st.title('Análise exporatória de dados de eleições de Florianópolis')

        st.sidebar.text('Sai daqui.')

    elif password == 'monica19022':

        st.sidebar.text('Senha correta.')

        data1 = pd.read_csv('votacao_secao_2016_SC.txt', sep=';', encoding='latin1')
        data2 = pd.read_csv('votacao_candidato_munzona_2016_SC.csv', sep=';', encoding='latin1')
        df_lucas = pd.read_excel('Zona e Secao 2016 - revisado.xlsx')
        filiados = pd.read_excel('Candidatos 2016 e 2020.xlsx')

        colunas = ['DATA_GERACAO', 'HORA_GERACAO', 'ANO_ELEICAO', 'NUM_TURNO', 'DESCRICAO_ELEICAO', 'SIGLA_UF',
                   'SIGLA_UE',
                   'CODIGO_MUNICIPIO',
                   'NOME_MUNICIPIO', 'NUM_ZONA', 'NUM_SECAO', 'CODIGO_CARGO', 'DESCRICAO_CARGO', 'NUM_VOTAVEL',
                   'QTDE_VOTOS']
        data1 = pd.DataFrame(np.insert(data1.values, 0, values=colunas, axis=0))

        df1, df2, dados_partidos, data_merge, data_merge_nomes = trata_dados_partidos(data1, data2)

        dados_vereador, dado_endereco = trata_vereador(data_merge_nomes, df_lucas)

        dist_votos = trata_bairro(dado_endereco)

        dist_candidatos = trata_candidato(dado_endereco)

        gapvotos = gap2016(filiados, dado_endereco)



        #Seleção para quais análises deseja visualizar
        select_anal = st.sidebar.radio('Escolhas qual análise deseja ver:',
                                              ('Nenhuma','Vereador 2016', 'Gap votos 2016/2020'))

        # Todas análises para vereador em 2016
        if select_anal == 'Vereador 2016':

            select_anal_vereador = st.sidebar.radio('Visualização por bairros ou candidatos:',
                                           ('Nenhuma', 'Bairros', 'Candidatos'))


            if select_anal_vereador == 'Nenhuma':
                st.write("Selecione ao lado entre as opções Bairros e Candidatos para visualizar ,respectivamente, as informações em função dos bairros de Florianópolis ou em função dos candidatos ")

            # Opções de visualização em função dos bairros de Florianópolis
            if select_anal_vereador == 'Bairros':
                st.write("Voto por candidato para visualizar os candidatos e quantos votos cada um recebeu nos bairros selecionados ")
                st.write("Voto por partido para visualizar quantos votos cada partido recebeu nos bairros selecionados ")
                voto_bairro = st.multiselect("Selecione uma ou mais:", ('None', 'Voto por partido', 'Voto por candidato'))

                if 'Voto por partido' in voto_bairro:
                    st.title('Partidos x Bairro')

                    # load tickers list
                    dist_votos = trata_bairro(dado_endereco)
                    tickers_sel = st.multiselect("Escolha o bairro:", sorted(dist_votos['BAIRRO'].unique()))

                    # bairros = ['ABRAÃO', 'CENTRO']
                    if st.button('Ver gráficos'):
                        st.write(grafico_bairros2(tickers_sel, dist_votos))

                if 'Voto por candidato' in voto_bairro:
                    st.title('Candidatos x Bairro')

                    dist_candidatos = trata_candidato(dado_endereco)
                    tickers_bairro = st.multiselect('Escolha o bairro', sorted(dist_candidatos['BAIRRO'].unique()))
                    if st.button('Ver gráficos'):
                        st.write(grafico_candidatos(tickers_bairro, dist_candidatos))


            if select_anal_vereador == 'Candidatos':
                st.title('Desempenho dos candidatos escolhidos em cada bairro')

                dist_candidatos = trata_candidato(dado_endereco)

                tickers_candidato = st.multiselect("Escolha o candidato:", sorted(dist_candidatos['NM_CANDIDATO'].unique()))
                st.write(candidatos(tickers_candidato, dist_candidatos))

        if select_anal == 'Gap votos 2016/2020':

            gapvotos = gap2016(filiados, dado_endereco)
            st.write(grafico_gap(gapvotos))

            # scatter_var1 = st.selectbox('Select variable for x axis:', numeric_vars)
                    # scatter_var2 = st.selectbox('Select variable for y axis:', numeric_vars)
                    # make_scatter(scatter_var1, scatter_var2, df)
                    # st.pyplot()
                #
                # if sidebar_visualization == 'Bar':
                #     bar_num_var = st.selectbox('Select numeric Variable:', numeric_vars)
                #     bar_cat_var = st.selectbox('Select categorical Variable:', object_vars)
                #     make_barplot(bar_cat_var, bar_num_var, df)
                #     st.pyplot()
                #
                # if sidebar_visualization == 'Histogram':
                #     col_hist = st.selectbox('Select column:', numeric_vars)
                #     make_histogram(col_hist, df)
                #     st.pyplot()
                #     normalize_var = st.button('Log Normalize Feature')
                #     if normalize_var:
                #         df[col_hist] = np.log1p(df[col_hist])
                #         make_histogram(col_hist, df)
                #         st.pyplot()




main()
