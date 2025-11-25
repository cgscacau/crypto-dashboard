import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import json
import threading
from typing import Dict, List, Callable
import websocket

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
        self.data_callback = None
        self.price_data = {}
        self.historical_data = {}
        self.running = False
        
    def on_message(self, ws, message):
        """Processa mensagens recebidas do WebSocket"""
        try:
            data = json.loads(message)
            
            if 'stream' in data:
                stream_data = data['data']
                symbol = stream_data['s']
                price = float(stream_data['c'])
                timestamp = pd.Timestamp.now()
                
                # Atualiza dados de preço atual
                self.price_data[symbol] = {
                    'price': price,
                    'change': float(stream_data['P']),
                    'volume': float(stream_data['v']),
                    'timestamp': timestamp
                }
                
                # Mantém histórico para gráficos
                if symbol not in self.historical_data:
                    self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                
                self.historical_data[symbol]['timestamps'].append(timestamp)
                self.historical_data[symbol]['prices'].append(price)
                
                # Limita o histórico para os últimos 100 pontos
                if len(self.historical_data[symbol]['timestamps']) > 100:
                    self.historical_data[symbol]['timestamps'].pop(0)
                    self.historical_data[symbol]['prices'].pop(0)
                
                # Chama callback se definido
                if self.data_callback:
                    self.data_callback(self.price_data, self.historical_data)
                    
        except Exception as e:
            st.error(f"Erro ao processar mensagem: {e}")
    
    def on_error(self, ws, error):
        """Trata erros da conexão WebSocket"""
        st.error(f"Erro WebSocket: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Trata fechamento da conexão"""
        self.running = False
    
    def on_open(self, ws):
        """Trata abertura da conexão"""
        self.running = True
    
    def start_stream(self, symbols: List[str], callback: Callable = None):
        """Inicia stream para símbolos específicos"""
        self.data_callback = callback
        
        # Converte símbolos para lowercase (padrão Binance)
        streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
        stream_names = "/".join(streams)
        
        url = f"wss://stream.binance.com:9443/stream?streams={stream_names}"
        
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Inicia em thread separada para não bloquear
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def stop_stream(self):
        """Para o stream WebSocket"""
        if self.ws:
            self.ws.close()
        self.running = False

# Inicialização do estado da sessão
if 'websocket_client' not in st.session_state:
    st.session_state.websocket_client = BinanceWebSocket()
    st.session_state.data_updated = False
    st.session_state.current_data = {}
    st.session_state.historical_data = {}

def update_data_callback(price_data, historical_data):
    """Callback chamado quando novos dados chegam"""
    st.session_state.current_data = price_data
    st.session_state.historical_data = historical_data
    st.session_state.data_updated = True

def create_price_chart(symbol, historical_data):
    """Cria gráfico de preços para um símbolo"""
    if symbol not in historical_data or not historical_data[symbol]['timestamps']:
        fig = go.Figure()
        fig.add_annotation(
            text="Aguardando dados...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="white")
        )
        fig.update_layout(
            template='plotly_dark',
            height=400,
            title=f'{symbol} - Aguardando dados'
        )
        return fig
    
    timestamps = historical_data[symbol]['timestamps']
    prices = historical_data[symbol]['prices']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        mode='lines+markers',
        name=symbol,
        line=dict(color='#00D4AA', width=2),
        marker=dict(size=4)
    ))
    
    fig.update_layout(
        title=f'{symbol} - Preço em Tempo Real',
        xaxis_title='Tempo',
        yaxis_title='Preço (USDT)',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig

def create_comparison_chart(symbols, historical_data):
    """Cria gráfico comparativo normalizado"""
    fig = go.Figure()
    
    colors = ['#00D4AA', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    
    for i, symbol in enumerate(symbols):
        if symbol in historical_data and historical_data[symbol]['timestamps']:
            timestamps = historical_data[symbol]['timestamps']
            prices = historical_data[symbol]['prices']
            
            # Normaliza preços (percentual de mudança desde o primeiro valor)
            if prices and len(prices) > 0:
                base_price = prices[0]
                normalized_prices = [(p - base_price) / base_price * 100 for p in prices]
                
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=normalized_prices,
                    mode='lines',
                    name=symbol,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
    
    fig.update_layout(
        title='Comparação de Performance (%)',
        xaxis_title='Tempo',
        yaxis_title='Mudança Percentual (%)',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig

# Interface principal
st.title("📈 Dashboard de Criptomoedas - Tempo Real")
st.markdown("---")

# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de criptomoedas
    available_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 
                        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT']
    
    selected_symbols = st.multiselect(
        "Selecione as criptomoedas:",
        available_symbols,
        default=['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    )
    
    # Controles de conexão
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Conectar", type="primary"):
            if selected_symbols:
                try:
                    st.session_state.websocket_client.start_stream(
                        selected_symbols, 
                        update_data_callback
                    )
                    st.success("Conectado!")
                except Exception as e:
                    st.error(f"Erro ao conectar: {e}")
            else:
                st.error("Selecione pelo menos uma criptomoeda")
    
    with col2:
        if st.button("🛑 Desconectar"):
            try:
                st.session_state.websocket_client.stop_stream()
                st.info("Desconectado")
            except Exception as e:
                st.error(f"Erro ao desconectar: {e}")
    
    # Status da conexão
    if st.session_state.websocket_client.running:
        st.success("🟢 Conectado")
    else:
        st.error("🔴 Desconectado")
    
    # Auto-refresh
    auto_refresh = st.checkbox("Auto-refresh (3s)", value=True)

# Área principal
if selected_symbols and st.session_state.current_data:
    
    # Métricas em tempo real
    st.subheader("📊 Preços Atuais")
    
    # Calcula número de colunas dinamicamente
    num_cols = min(len(selected_symbols), 4)
    cols = st.columns(num_cols)
    
    for i, symbol in enumerate(selected_symbols):
        if symbol in st.session_state.current_data:
            data = st.session_state.current_data[symbol]
            
            with cols[i % num_cols]:
                change_symbol = "+" if data['change'] >= 0 else ""
                
                st.metric(
                    label=symbol.replace('USDT', '/USDT'),
                    value=f"${data['price']:.4f}",
                    delta=f"{change_symbol}{data['change']:.2f}%"
                )
    
    st.markdown("---")
    
    # Gráficos individuais
    st.subheader("📈 Gráficos Individuais")
    
    # Layout responsivo para gráficos
    if len(selected_symbols) == 1:
        fig = create_price_chart(selected_symbols[0], st.session_state.historical_data)
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Para múltiplos símbolos, mostra em grid 2x2
        for i in range(0, len(selected_symbols), 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < len(selected_symbols):
                    fig = create_price_chart(selected_symbols[i], st.session_state.historical_data)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if i + 1 < len(selected_symbols):
                    fig = create_price_chart(selected_symbols[i + 1], st.session_state.historical_data)
                    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de comparação
    if len(selected_symbols) > 1:
        st.markdown("---")
        st.subheader("⚖️ Comparação de Performance")
        comparison_fig = create_comparison_chart(selected_symbols, st.session_state.historical_data)
        st.plotly_chart(comparison_fig, use_container_width=True)

else:
    # Tela inicial
    st.info("👈 Selecione as criptomoedas na barra lateral e clique em 'Conectar' para começar!")
    
    # Exemplo visual
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
if auto_refresh and st.session_state.websocket_client.running:
    time.sleep(3)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("💡 **Dica:** Este dashboard utiliza WebSocket da Binance para dados em tempo real. Mantenha a conexão ativa para receber atualizações.")
