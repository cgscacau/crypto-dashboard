import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import json
import threading
import websocket
from typing import Dict, List
import queue

# Configuração da página
st.set_page_config(
    page_title="Crypto Dashboard - Tempo Real",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class BinanceWebSocket:
    def __init__(self):
        self.ws = None
        self.data_queue = queue.Queue()
        self.price_data = {}
        self.historical_data = {}
        self.running = False
        self.thread = None
        self.symbols = []
        
    def on_message(self, ws, message):
        """Processa mensagens recebidas do WebSocket"""
        try:
            data = json.loads(message)
            
            if 'stream' in data and 'data' in data:
                stream_data = data['data']
                symbol = stream_data['s']
                price = float(stream_data['c'])
                timestamp = pd.Timestamp.now()
                
                # Coloca dados na queue para processamento thread-safe
                self.data_queue.put({
                    'symbol': symbol,
                    'price': price,
                    'change': float(stream_data['P']),
                    'volume': float(stream_data['v']),
                    'timestamp': timestamp
                })
                
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
    
    def on_error(self, ws, error):
        """Trata erros da conexão WebSocket"""
        print(f"Erro WebSocket: {error}")
        self.running = False
    
    def on_close(self, ws, close_status_code, close_msg):
        """Trata fechamento da conexão"""
        print("Conexão WebSocket fechada")
        self.running = False
    
    def on_open(self, ws):
        """Trata abertura da conexão"""
        print("Conexão WebSocket estabelecida")
        self.running = True
    
    def process_queue(self):
        """Processa dados da queue de forma thread-safe"""
        processed_data = False
        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()
                symbol = data['symbol']
                
                # Atualiza dados de preço atual
                self.price_data[symbol] = {
                    'price': data['price'],
                    'change': data['change'],
                    'volume': data['volume'],
                    'timestamp': data['timestamp']
                }
                
                # Mantém histórico para gráficos
                if symbol not in self.historical_data:
                    self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                
                self.historical_data[symbol]['timestamps'].append(data['timestamp'])
                self.historical_data[symbol]['prices'].append(data['price'])
                
                # Limita o histórico para os últimos 50 pontos
                if len(self.historical_data[symbol]['timestamps']) > 50:
                    self.historical_data[symbol]['timestamps'].pop(0)
                    self.historical_data[symbol]['prices'].pop(0)
                
                processed_data = True
                
        except queue.Empty:
            pass
        
        return processed_data
    
    def start_stream(self, symbols: List[str]):
        """Inicia stream para símbolos específicos"""
        if self.running:
            self.stop_stream()
        
        self.symbols = symbols
        
        # Converte símbolos para lowercase (padrão Binance)
        streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
        stream_names = "/".join(streams)
        
        url = f"wss://stream.binance.com:9443/stream?streams={stream_names}"
        
        try:
            self.ws = websocket.WebSocketApp(
                url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Inicia em thread separada
            self.thread = threading.Thread(target=self.ws.run_forever, kwargs={
                'ping_interval': 20,
                'ping_timeout': 10
            })
            self.thread.daemon = True
            self.thread.start()
            
            return True
            
        except Exception as e:
            print(f"Erro ao iniciar stream: {e}")
            return False
    
    def stop_stream(self):
        """Para o stream WebSocket"""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
    
    def get_connection_status(self):
        """Verifica status da conexão"""
        return self.running and self.thread and self.thread.is_alive()
    
    def get_data(self):
        """Retorna dados atuais processando a queue"""
        self.process_queue()
        return self.price_data, self.historical_data

# Inicialização do estado da sessão
if 'websocket_client' not in st.session_state:
    st.session_state.websocket_client = BinanceWebSocket()
    st.session_state.last_update = time.time()

def create_price_chart(symbol, historical_data):
    """Cria gráfico de preços para um símbolo"""
    if symbol not in historical_data or not historical_data[symbol]['timestamps']:
        fig = go.Figure()
        fig.add_annotation(
            text="Aguardando dados...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            template='plotly_dark',
            height=350,
            title=f'{symbol} - Aguardando dados',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    timestamps = historical_data[symbol]['timestamps']
    prices = historical_data[symbol]['prices']
    
    fig = go.Figure()
    
    # Determina cor baseada na tendência
    color = '#00D4AA' if len(prices) > 1 and prices[-1] >= prices[0] else '#FF6B6B'
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        mode='lines+markers',
        name=symbol,
        line=dict(color=color, width=2),
        marker=dict(size=3),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                     'Preço: $%{y:.4f}<br>' +
                     'Tempo: %{x}<br>' +
                     '<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'{symbol.replace("USDT", "/USDT")}',
        xaxis_title='',
        yaxis_title='Preço (USDT)',
        template='plotly_dark',
        height=350,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    # Formatar eixo Y para mostrar preços com precisão adequada
    if prices:
        max_price = max(prices)
        if max_price < 1:
            fig.update_yaxes(tickformat='.6f')
        elif max_price < 10:
            fig.update_yaxes(tickformat='.4f')
        else:
            fig.update_yaxes(tickformat='.2f')
    
    return fig

def create_comparison_chart(symbols, historical_data):
    """Cria gráfico comparativo normalizado"""
    fig = go.Figure()
    
    colors = ['#00D4AA', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    
    for i, symbol in enumerate(symbols):
        if symbol in historical_data and historical_data[symbol]['timestamps']:
            timestamps = historical_data[symbol]['timestamps']
            prices = historical_data[symbol]['prices']
            
            if prices and len(prices) > 0:
                base_price = prices[0]
                normalized_prices = [(p - base_price) / base_price * 100 for p in prices]
                
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=normalized_prices,
                    mode='lines',
                    name=symbol.replace('USDT', ''),
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                 'Variação: %{y:.2f}%<br>' +
                                 '<extra></extra>'
                ))
    
    fig.update_layout(
        title='📊 Comparação de Performance (%)',
        xaxis_title='',
        yaxis_title='Variação (%)',
        template='plotly_dark',
        height=400,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

# Interface principal
st.title("📈 Dashboard de Criptomoedas - Tempo Real")
st.markdown("---")

# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de criptomoedas
    available_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT',
        'MATICUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'FILUSDT'
    ]
    
    selected_symbols = st.multiselect(
        "Selecione as criptomoedas:",
        available_symbols,
        default=['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
        max_selections=6
    )
    
    st.markdown("---")
    
    # Controles de conexão
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Conectar", type="primary", use_container_width=True):
            if selected_symbols:
                try:
                    success = st.session_state.websocket_client.start_stream(selected_symbols)
                    if success:
                        st.success("Conectando...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao conectar")
                except Exception as e:
                    st.error(f"Erro: {str(e)}")
            else:
                st.warning("Selecione pelo menos uma criptomoeda")
    
    with col2:
        if st.button("🛑 Parar", use_container_width=True):
            try:
                st.session_state.websocket_client.stop_stream()
                st.info("Desconectado")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {str(e)}")
    
    # Status da conexão
    connection_status = st.session_state.websocket_client.get_connection_status()
    if connection_status:
        st.success("🟢 Conectado")
    else:
        st.error("🔴 Desconectado")
    
    st.markdown("---")
    
    # Configurações de atualização
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    refresh_interval = st.select_slider(
        "Intervalo de atualização:",
        options=[1, 2, 3, 5],
        value=2,
        format_func=lambda x: f"{x}s"
    )

# Área principal
current_data, historical_data = st.session_state.websocket_client.get_data()

if selected_symbols and current_data:
    
    # Métricas em tempo real
    st.subheader("📊 Preços Atuais")
    
    # Organiza métricas em grid responsivo
    num_cols = min(len(selected_symbols), 3)
    cols = st.columns(num_cols)
    
    for i, symbol in enumerate(selected_symbols):
        if symbol in current_data:
            data = current_data[symbol]
            
            with cols[i % num_cols]:
                # Formatação do preço baseada no valor
                if data['price'] < 1:
                    price_str = f"${data['price']:.6f}"
                elif data['price'] < 10:
                    price_str = f"${data['price']:.4f}"
                else:
                    price_str = f"${data['price']:.2f}"
                
                change_symbol = "+" if data['change'] >= 0 else ""
                
                st.metric(
                    label=symbol.replace('USDT', '/USDT'),
                    value=price_str,
                    delta=f"{change_symbol}{data['change']:.2f}%"
                )
    
    st.markdown("---")
    
    # Gráficos individuais
    st.subheader("📈 Gráficos em Tempo Real")
    
    # Layout responsivo para gráficos
    num_selected = len(selected_symbols)
    
    if num_selected == 1:
        fig = create_price_chart(selected_symbols[0], historical_data)
        st.plotly_chart(fig, use_container_width=True)
    elif num_selected <= 4:
        # Grid 2x2
        for i in range(0, num_selected, 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < num_selected:
                    fig = create_price_chart(selected_symbols[i], historical_data)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if i + 1 < num_selected:
                    fig = create_price_chart(selected_symbols[i + 1], historical_data)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        # Grid 3x2 para mais de 4
        for i in range(0, num_selected, 3):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if i < num_selected:
                    fig = create_price_chart(selected_symbols[i], historical_data)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if i + 1 < num_selected:
                    fig = create_price_chart(selected_symbols[i + 1], historical_data)
                    st.plotly_chart(fig, use_container_width=True)
                    
            with col3:
                if i + 2 < num_selected:
                    fig = create_price_chart(selected_symbols[i + 2], historical_data)
                    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de comparação
    if num_selected > 1:
        st.markdown("---")
        comparison_fig = create_comparison_chart(selected_symbols, historical_data)
        st.plotly_chart(comparison_fig, use_container_width=True)
    
    # Informações adicionais
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Moedas Monitoradas", len(selected_symbols))
    
    with col2:
        if current_data:
            last_update = max([data['timestamp'] for data in current_data.values()])
            seconds_ago = (pd.Timestamp.now() - last_update).total_seconds()
            st.metric("Última Atualização", f"{int(seconds_ago)}s atrás")
    
    with col3:
        total_data_points = sum([len(historical_data.get(symbol, {}).get('prices', [])) for symbol in selected_symbols])
        st.metric("Pontos de Dados", total_data_points)

elif selected_symbols and st.session_state.websocket_client.get_connection_status():
    # Conectado mas sem dados ainda
    st.info("🔄 Conectado! Aguardando dados da Binance...")
    
    # Placeholder para gráficos
    with st.spinner("Carregando dados..."):
        time.sleep(2)
        st.rerun()

else:
    # Tela inicial
    st.info("👈 Selecione as criptomoedas na barra lateral e clique em 'Conectar' para começar!")
    
    # Recursos do dashboard
    st.subheader("🎯 Recursos do Dashboard:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📊 Métricas em Tempo Real**
        - Preços atualizados instantaneamente
        - Variação percentual
        - Volume de negociação
        """)
    
    with col2:
        st.markdown("""
        **📈 Gráficos Interativos**
        - Histórico de preços em tempo real
        - Gráficos individuais por moeda
        - Comparação de performance
        """)
    
    with col3:
        st.markdown("""
        **⚡ Conexão WebSocket**
        - Dados direto da Binance
        - Baixa latência
        - Múltiplas criptomoedas
        """)

# Auto-refresh
if auto_refresh and st.session_state.websocket_client.get_connection_status():
    time.sleep(refresh_interval)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("💡 **Dica:** Este dashboard utiliza WebSocket da Binance para dados em tempo real. Para melhor performance, limite a 6 criptomoedas simultaneamente.")
