import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time
import requests
import random
import numpy as np
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(
    page_title="Crypto Dashboard - Candlesticks",
    page_icon="🕯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Evita loops infinitos
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.running = False
    st.session_state.data = {}
    st.session_state.candles = {}
    st.session_state.last_update = 0

class SimpleCryptoFetcher:
    def __init__(self):
        self.symbols_map = {
            'BTCUSDT': 'bitcoin',
            'ETHUSDT': 'ethereum', 
            'BNBUSDT': 'binancecoin',
            'ADAUSDT': 'cardano',
            'XRPUSDT': 'ripple',
            'SOLUSDT': 'solana',
            'DOTUSDT': 'polkadot',
            'DOGEUSDT': 'dogecoin',
            'AVAXUSDT': 'avalanche-2',
            'LINKUSDT': 'chainlink'
        }
    
    def fetch_prices(self, symbols):
        """Busca preços reais da API"""
        try:
            available_symbols = [s for s in symbols if s in self.symbols_map]
            if not available_symbols:
                return {}
            
            ids = ','.join([self.symbols_map[s] for s in available_symbols])
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': ids,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = {}
                
                for symbol in available_symbols:
                    coin_id = self.symbols_map[symbol]
                    if coin_id in data:
                        coin_data = data[coin_id]
                        result[symbol] = {
                            'price': float(coin_data['usd']),
                            'change': float(coin_data.get('usd_24h_change', 0)),
                            'timestamp': datetime.now()
                        }
                
                return result
            
        except Exception as e:
            st.error(f"Erro na API: {str(e)}")
            return {}
        
        return {}
    
    def generate_candle(self, symbol, base_price, timestamp):
        """Gera um candle baseado no preço base"""
        # Variação pequena para simular OHLC
        variation = base_price * 0.002  # 0.2% de variação máxima
        
        open_price = base_price + random.uniform(-variation, variation)
        close_price = base_price + random.uniform(-variation, variation)
        
        high_price = max(open_price, close_price) + random.uniform(0, variation/2)
        low_price = min(open_price, close_price) - random.uniform(0, variation/2)
        
        volume = random.uniform(1000000, 5000000)
        
        return {
            'timestamp': timestamp,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }

def create_candlestick_chart(symbol, candles_data):
    """Cria gráfico de candlestick"""
    if not candles_data:
        fig = go.Figure()
        fig.add_annotation(
            text="Aguardando dados...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            template='plotly_dark',
            height=400,
            title=f'{symbol.replace("USDT", "/USD")} - Carregando...'
        )
        return fig
    
    # Prepara dados
    timestamps = [candle['timestamp'] for candle in candles_data]
    opens = [candle['open'] for candle in candles_data]
    highs = [candle['high'] for candle in candles_data]
    lows = [candle['low'] for candle in candles_data]
    closes = [candle['close'] for candle in candles_data]
    volumes = [candle['volume'] for candle in candles_data]
    
    # Cria subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'🕯️ {symbol.replace("USDT", "/USD")}', 'Volume'),
        row_heights=[0.7, 0.3]
    )
    
    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name=symbol,
            increasing_line_color='#00D4AA',
            decreasing_line_color='#FF4B4B'
        ),
        row=1, col=1
    )
    
    # Volume
    colors = ['#00D4AA' if c >= o else '#FF4B4B' for o, c in zip(opens, closes)]
    
    fig.add_trace(
        go.Bar(
            x=timestamps,
            y=volumes,
            name='Volume',
            marker_color=colors,
            opacity=0.7
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        template='plotly_dark',
        height=500,
        showlegend=False,
        xaxis_rangeslider_visible=False
    )
    
    return fig

# Interface principal
st.title("🕯️ Crypto Dashboard - Candlesticks")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    available_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT']
    
    selected_symbols = st.multiselect(
        "Selecione as criptomoedas:",
        available_symbols,
        default=['BTCUSDT', 'ETHUSDT'],
        max_selections=3
    )
    
    st.markdown("---")
    
    # Controles simples
    if st.button("🚀 Iniciar", type="primary"):
        if selected_symbols:
            st.session_state.running = True
            st.session_state.selected_symbols = selected_symbols
            st.success("Dashboard iniciado!")
        else:
            st.warning("Selecione pelo menos uma criptomoeda")
    
    if st.button("🛑 Parar"):
        st.session_state.running = False
        st.info("Dashboard parado")
    
    # Status
    if st.session_state.running:
        st.success("🟢 Ativo")
    else:
        st.error("🔴 Inativo")
    
    # Controle manual de atualização
    if st.button("🔄 Atualizar Dados"):
        if st.session_state.running and selected_symbols:
            fetcher = SimpleCryptoFetcher()
            new_data = fetcher.fetch_prices(selected_symbols)
            
            if new_data:
                current_time = datetime.now()
                
                for symbol, price_data in new_data.items():
                    # Inicializa candles se necessário
                    if symbol not in st.session_state.candles:
                        st.session_state.candles[symbol] = []
                    
                    # Gera novo candle
                    candle = fetcher.generate_candle(
                        symbol, 
                        price_data['price'], 
                        current_time
                    )
                    
                    st.session_state.candles[symbol].append(candle)
                    
                    # Limita histórico
                    if len(st.session_state.candles[symbol]) > 50:
                        st.session_state.candles[symbol].pop(0)
                    
                    # Atualiza dados atuais
                    st.session_state.data[symbol] = {
                        'price': candle['close'],
                        'change': price_data['change'],
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'volume': candle['volume']
                    }
                
                st.session_state.last_update = time.time()
                st.success("Dados atualizados!")
                st.rerun()

# Área principal
if st.session_state.running and hasattr(st.session_state, 'selected_symbols'):
    
    # Métricas
    if st.session_state.data:
        st.subheader("💰 Preços Atuais")
        
        cols = st.columns(len(st.session_state.selected_symbols))
        
        for i, symbol in enumerate(st.session_state.selected_symbols):
            if symbol in st.session_state.data:
                data = st.session_state.data[symbol]
                
                with cols[i]:
                    price = data['price']
                    change = data['change']
                    
                    if price < 1:
                        price_str = f"${price:.6f}"
                    elif price < 100:
                        price_str = f"${price:.4f}"
                    else:
                        price_str = f"${price:,.2f}"
                    
                    st.metric(
                        label=symbol.replace('USDT', '/USD'),
                        value=price_str,
                        delta=f"{change:+.2f}%"
                    )
        
        st.markdown("---")
    
    # Gráficos
    st.subheader("📈 Gráficos de Candlestick")
    
    if len(st.session_state.selected_symbols) == 1:
        symbol = st.session_state.selected_symbols[0]
        candles = st.session_state.candles.get(symbol, [])
        fig = create_candlestick_chart(symbol, candles)
        st.plotly_chart(fig, use_container_width=True)
    
    elif len(st.session_state.selected_symbols) == 2:
        col1, col2 = st.columns(2)
        
        with col1:
            symbol1 = st.session_state.selected_symbols[0]
            candles1 = st.session_state.candles.get(symbol1, [])
            fig1 = create_candlestick_chart(symbol1, candles1)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            symbol2 = st.session_state.selected_symbols[1]
            candles2 = st.session_state.candles.get(symbol2, [])
            fig2 = create_candlestick_chart(symbol2, candles2)
            st.plotly_chart(fig2, use_container_width=True)
    
    else:
        # Grid para 3 símbolos
        col1, col2 = st.columns(2)
        
        with col1:
            symbol1 = st.session_state.selected_symbols[0]
            candles1 = st.session_state.candles.get(symbol1, [])
            fig1 = create_candlestick_chart(symbol1, candles1)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            symbol2 = st.session_state.selected_symbols[1]
            candles2 = st.session_state.candles.get(symbol2, [])
            fig2 = create_candlestick_chart(symbol2, candles2)
            st.plotly_chart(fig2, use_container_width=True)
        
        if len(st.session_state.selected_symbols) > 2:
            symbol3 = st.session_state.selected_symbols[2]
            candles3 = st.session_state.candles.get(symbol3, [])
            fig3 = create_candlestick_chart(symbol3, candles3)
            st.plotly_chart(fig3, use_container_width=True)
    
    # Informações
    if st.session_state.data:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Moedas Ativas", len(st.session_state.data))
        
        with col2:
            if st.session_state.last_update:
                seconds_ago = int(time.time() - st.session_state.last_update)
                st.metric("Última Atualização", f"{seconds_ago}s atrás")
        
        with col3:
            total_candles = sum([len(candles) for candles in st.session_state.candles.values()])
            st.metric("Total de Candles", total_candles)

else:
    # Tela inicial
    st.info("👈 Selecione as criptomoedas na barra lateral e clique em 'Iniciar'")
    
    st.subheader("🕯️ Recursos do Dashboard:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📊 Candlesticks Profissionais**
        - Gráficos OHLC (Open, High, Low, Close)
        - Volume integrado
        - Cores verde/vermelho por tendência
        - Dados baseados em preços reais
        """)
    
    with col2:
        st.markdown("""
        **⚡ Controle Manual**
        - Atualização sob demanda
        - Sem loops infinitos
        - Performance otimizada
        - Interface estável
        """)

# Footer
st.markdown("---")
st.markdown("🕯️ **Dashboard Candlestick** | Dados: CoinGecko API | Atualização Manual")
