import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time
import requests
from typing import Dict, List
import json
import random
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Crypto Dashboard - Candlesticks",
    page_icon="🕯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class CandlestickCryptoFetcher:
    def __init__(self):
        self.price_data = {}
        self.historical_data = {}
        self.running = False
        self.symbols = []
        self.base_prices = {}
        self.last_api_call = 0
        self.api_interval = 30
        self.candle_interval = 10  # Novo candle a cada 10 segundos
        self.current_candles = {}  # Candles em formação
        
    def fetch_real_data(self, symbols):
        """Busca dados reais das APIs"""
        try:
            symbol_map = {
                'BTCUSDT': 'bitcoin',
                'ETHUSDT': 'ethereum', 
                'BNBUSDT': 'binancecoin',
                'ADAUSDT': 'cardano',
                'XRPUSDT': 'ripple',
                'SOLUSDT': 'solana',
                'DOTUSDT': 'polkadot',
                'DOGEUSDT': 'dogecoin',
                'AVAXUSDT': 'avalanche-2',
                'LINKUSDT': 'chainlink',
                'MATICUSDT': 'matic-network',
                'LTCUSDT': 'litecoin',
                'UNIUSDT': 'uniswap',
                'ATOMUSDT': 'cosmos',
                'FILUSDT': 'filecoin'
            }
            
            available_symbols = [s for s in symbols if s in symbol_map]
            if not available_symbols:
                return False
            
            ids = ','.join([symbol_map[s] for s in available_symbols])
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': ids,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for symbol in available_symbols:
                    coin_id = symbol_map[symbol]
                    if coin_id in data:
                        coin_data = data[coin_id]
                        price = float(coin_data['usd'])
                        change = float(coin_data.get('usd_24h_change', 0))
                        volume = float(coin_data.get('usd_24h_vol', 0))
                        
                        self.base_prices[symbol] = {
                            'price': price,
                            'change': change,
                            'volume': volume,
                            'volatility': min(abs(change) * 0.05, 1.0)
                        }
                
                self.last_api_call = time.time()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erro API: {str(e)}")
            return False
    
    def simulate_realistic_tick(self, symbol):
        """Simula um tick de preço realista"""
        if symbol not in self.base_prices:
            return None
        
        base_data = self.base_prices[symbol]
        base_price = base_data['price']
        volatility = base_data['volatility']
        
        # Random walk com volatilidade baseada em dados reais
        random_change = random.gauss(0, volatility * 0.001)
        
        # Momentum (tendência a continuar direção)
        if hasattr(self, '_momentum'):
            momentum = self._momentum.get(symbol, 0) * 0.4
            random_change += momentum
        else:
            self._momentum = {}
        
        # Limita variação máxima por tick
        random_change = max(-0.003, min(0.003, random_change))
        
        new_price = base_price * (1 + random_change)
        
        # Atualiza momentum
        self._momentum[symbol] = random_change * 0.7 + self._momentum.get(symbol, 0) * 0.3
        
        # Simula volume baseado na volatilidade
        base_volume = base_data['volume']
        volume_factor = 1 + abs(random_change) * 50
        tick_volume = base_volume * volume_factor * random.uniform(0.00001, 0.0001)
        
        return new_price, tick_volume
    
    def update_candle_data(self, symbol, price, volume, timestamp):
        """Atualiza dados do candle atual"""
        candle_time = timestamp.floor(f'{self.candle_interval}S')  # Arredonda para intervalo do candle
        
        if symbol not in self.current_candles:
            self.current_candles[symbol] = {}
        
        if candle_time not in self.current_candles[symbol]:
            # Novo candle
            self.current_candles[symbol][candle_time] = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'timestamp': candle_time
            }
        else:
            # Atualiza candle existente
            candle = self.current_candles[symbol][candle_time]
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['close'] = price
            candle['volume'] += volume
        
        # Move candles completos para histórico
        self.move_completed_candles_to_history(symbol, timestamp)
    
    def move_completed_candles_to_history(self, symbol, current_timestamp):
        """Move candles completos para o histórico"""
        if symbol not in self.current_candles:
            return
        
        current_candle_time = current_timestamp.floor(f'{self.candle_interval}S')
        
        if symbol not in self.historical_data:
            self.historical_data[symbol] = {
                'timestamps': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': []
            }
        
        # Move candles completos (não o atual)
        completed_candles = []
        for candle_time, candle_data in list(self.current_candles[symbol].items()):
            if candle_time < current_candle_time:
                completed_candles.append((candle_time, candle_data))
                del self.current_candles[symbol][candle_time]
        
        # Adiciona ao histórico em ordem cronológica
        for candle_time, candle_data in sorted(completed_candles):
            self.historical_data[symbol]['timestamps'].append(candle_time)
            self.historical_data[symbol]['open'].append(candle_data['open'])
            self.historical_data[symbol]['high'].append(candle_data['high'])
            self.historical_data[symbol]['low'].append(candle_data['low'])
            self.historical_data[symbol]['close'].append(candle_data['close'])
            self.historical_data[symbol]['volume'].append(candle_data['volume'])
        
        # Limita histórico
        max_candles = 100
        for key in ['timestamps', 'open', 'high', 'low', 'close', 'volume']:
            while len(self.historical_data[symbol][key]) > max_candles:
                self.historical_data[symbol][key].pop(0)
    
    def get_current_candle_data(self, symbol):
        """Retorna dados do candle atual em formação"""
        if symbol not in self.current_candles:
            return None
        
        current_candles = list(self.current_candles[symbol].values())
        if not current_candles:
            return None
        
        # Retorna o candle mais recente
        return current_candles[-1]
    
    def update_simulated_data(self):
        """Atualiza dados com simulação de ticks"""
        current_time = pd.Timestamp.now()
        
        for symbol in self.symbols:
            if symbol in self.base_prices:
                # Simula tick
                tick_data = self.simulate_realistic_tick(symbol)
                if tick_data is None:
                    continue
                
                new_price, tick_volume = tick_data
                
                # Atualiza candle
                self.update_candle_data(symbol, new_price, tick_volume, current_time)
                
                # Calcula mudanças
                current_candle = self.get_current_candle_data(symbol)
                if current_candle:
                    # Mudança desde abertura do candle atual
                    candle_change = ((current_candle['close'] - current_candle['open']) / current_candle['open']) * 100
                    
                    # Mudança desde início da sessão
                    session_change = self.base_prices[symbol]['change']
                    if self.historical_data.get(symbol, {}).get('close'):
                        first_close = self.historical_data[symbol]['close'][0]
                        session_change = ((new_price - first_close) / first_close) * 100
                    
                    self.price_data[symbol] = {
                        'price': new_price,
                        'open': current_candle['open'],
                        'high': current_candle['high'],
                        'low': current_candle['low'],
                        'close': current_candle['close'],
                        'volume': current_candle['volume'],
                        'change': session_change,
                        'candle_change': candle_change,
                        'timestamp': current_time
                    }
    
    def start_fetching(self, symbols):
        """Inicia busca de dados"""
        self.symbols = symbols
        self.running = True
        
        # Busca dados reais iniciais
        success = self.fetch_real_data(symbols)
        if success:
            # Inicia simulação
            self.update_simulated_data()
        
        return success
    
    def stop_fetching(self):
        """Para a busca de dados"""
        self.running = False
        self.price_data.clear()
        self.historical_data.clear()
        self.base_prices.clear()
        self.current_candles.clear()
    
    def update_data(self):
        """Atualiza dados"""
        if not self.running or not self.symbols:
            return False
        
        current_time = time.time()
        
        # Atualiza dados reais ocasionalmente
        if current_time - self.last_api_call > self.api_interval:
            self.fetch_real_data(self.symbols)
        
        # Sempre atualiza simulação
        if self.base_prices:
            self.update_simulated_data()
            return True
        
        return False
    
    def get_data(self):
        """Retorna dados atuais"""
        return self.price_data, self.historical_data
    
    def is_running(self):
        """Verifica se está ativo"""
        return self.running

# Inicialização do estado da sessão
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = CandlestickCryptoFetcher()

def create_candlestick_chart(symbol, historical_data, current_data):
    """Cria gráfico de candlestick com volume"""
    if symbol not in historical_data or not historical_data[symbol]['timestamps']:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('Preço', 'Volume'),
            row_width=[0.7, 0.3]
        )
        
        fig.add_annotation(
            text="🕯️ Formando candles...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=18, color="#00D4AA"),
            row=1, col=1
        )
        
        fig.update_layout(
            template='plotly_dark',
            height=600,
            title=f'🕯️ {symbol.replace("USDT", "/USD")} - Candlestick',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        return fig
    
    # Dados históricos
    timestamps = historical_data[symbol]['timestamps']
    opens = historical_data[symbol]['open']
    highs = historical_data[symbol]['high']
    lows = historical_data[symbol]['low']
    closes = historical_data[symbol]['close']
    volumes = historical_data[symbol]['volume']
    
    # Adiciona candle atual se disponível
    current_candle = st.session_state.data_fetcher.get_current_candle_data(symbol)
    if current_candle:
        timestamps = timestamps + [current_candle['timestamp']]
        opens = opens + [current_candle['open']]
        highs = highs + [current_candle['high']]
        lows = lows + [current_candle['low']]
        closes = closes + [current_candle['close']]
        volumes = volumes + [current_candle['volume']]
    
    if len(timestamps) < 1:
        return create_candlestick_chart(symbol, {}, current_data)
    
    # Cria subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f'🕯️ {symbol.replace("USDT", "/USD")} - Candlestick', '📊 Volume'),
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
            name=symbol.replace('USDT', ''),
            increasing_line_color='#00D4AA',
            decreasing_line_color='#FF4B4B',
            increasing_fillcolor='#00D4AA',
            decreasing_fillcolor='#FF4B4B',
            line=dict(width=1),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Abertura: $%{open:,.6f}<br>' +
                         'Máxima: $%{high:,.6f}<br>' +
                         'Mínima: $%{low:,.6f}<br>' +
                         'Fechamento: $%{close:,.6f}<br>' +
                         'Tempo: %{x|%H:%M:%S}<br>' +
                         '<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Média móvel simples
    if len(closes) >= 20:
        ma20 = []
        ma_timestamps = []
        for i in range(19, len(closes)):
            ma_price = sum(closes[i-19:i+1]) / 20
            ma20.append(ma_price)
            ma_timestamps.append(timestamps[i])
        
        fig.add_trace(
            go.Scatter(
                x=ma_timestamps,
                y=ma20,
                mode='lines',
                name='MA20',
                line=dict(color='orange', width=2, dash='dot'),
                opacity=0.8,
                hovertemplate='MA20: $%{y:,.6f}<extra></extra>'
            ),
            row=1, col=1
        )
    
    # Volume com cores
    volume_colors = []
    for i in range(len(volumes)):
        if i == 0:
            volume_colors.append('#00D4AA')
        else:
            color = '#00D4AA' if closes[i] >= opens[i] else '#FF4B4B'
            volume_colors.append(color)
    
    fig.add_trace(
        go.Bar(
            x=timestamps,
            y=volumes,
            name='Volume',
            marker_color=volume_colors,
            opacity=0.7,
            hovertemplate='Volume: %{y:,.0f}<br>Tempo: %{x|%H:%M:%S}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Layout
    fig.update_layout(
        template='plotly_dark',
        height=600,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis_rangeslider_visible=False  # Remove o range slider padrão
    )
    
    # Formatação dos eixos
    if closes:
        max_price = max(highs)
        min_price = min(lows)
        
        if max_price < 0.01:
            fig.update_yaxes(tickformat='.8f', row=1, col=1)
        elif max_price < 1:
            fig.update_yaxes(tickformat='.6f', row=1, col=1)
        elif max_price < 100:
            fig.update_yaxes(tickformat='.4f', row=1, col=1)
        else:
            fig.update_yaxes(tickformat=',.2f', row=1, col=1)
    
    # Grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    
    # Formatação do volume
    fig.update_yaxes(title_text="Volume", tickformat='.0s', row=2, col=1)
    
    return fig

def create_mini_candlestick(symbol, historical_data, current_data):
    """Cria versão mini do candlestick para grid"""
    if symbol not in historical_data or not historical_data[symbol]['timestamps']:
        fig = go.Figure()
        fig.add_annotation(
            text="🕯️ Loading...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#00D4AA")
        )
        fig.update_layout(
            template='plotly_dark',
            height=300,
            title=f'{symbol.replace("USDT", "/USD")}',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        return fig
    
    # Dados históricos + candle atual
    timestamps = historical_data[symbol]['timestamps'][:]
    opens = historical_data[symbol]['open'][:]
    highs = historical_data[symbol]['high'][:]
    lows = historical_data[symbol]['low'][:]
    closes = historical_data[symbol]['close'][:]
    
    # Adiciona candle atual
    current_candle = st.session_state.data_fetcher.get_current_candle_data(symbol)
    if current_candle:
        timestamps.append(current_candle['timestamp'])
        opens.append(current_candle['open'])
        highs.append(current_candle['high'])
        lows.append(current_candle['low'])
        closes.append(current_candle['close'])
    
    if len(timestamps) < 1:
        return create_mini_candlestick(symbol, {}, current_data)
    
    fig = go.Figure()
    
    # Candlestick mini
    fig.add_trace(
        go.Candlestick(
            x=timestamps,
            open=opens,
            high=highs,
            low=lows,
            close=closes,
            name=symbol.replace('USDT', ''),
            increasing_line_color='#00D4AA',
            decreasing_line_color='#FF4B4B',
            increasing_fillcolor='#00D4AA',
            decreasing_fillcolor='#FF4B4B',
            line=dict(width=1),
            showlegend=False
        )
    )
    
    fig.update_layout(
        template='plotly_dark',
        height=300,
        title=f'🕯️ {symbol.replace("USDT", "/USD")}',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_rangeslider_visible=False
    )
    
    # Formatação
    if closes:
        max_price = max(highs)
        if max_price < 0.01:
            fig.update_yaxes(tickformat='.8f')
        elif max_price < 1:
            fig.update_yaxes(tickformat='.6f')
        elif max_price < 100:
            fig.update_yaxes(tickformat='.4f')
        else:
            fig.update_yaxes(tickformat=',.2f')
    
    return fig

# Interface principal
st.title("🕯️ Dashboard Crypto - Candlesticks")
st.markdown("*Gráficos de velas japonesas com OHLC e volume em tempo real*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    available_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT'
    ]
    
    selected_symbols = st.multiselect(
        "🎯 Selecione as criptomoedas:",
        available_symbols,
        default=['BTCUSDT', 'ETHUSDT'],
        max_selections=4
    )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 INICIAR", type="primary", use_container_width=True):
            if selected_symbols:
                with st.spinner("🔄 Iniciando candles..."):
                    success = st.session_state.data_fetcher.start_fetching(selected_symbols)
                    if success:
                        st.success("✅ Candles ativos!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erro de conexão")
            else:
                st.warning("⚠️ Selecione criptomoedas")
    
    with col2:
        if st.button("🛑 PARAR", use_container_width=True):
            st.session_state.data_fetcher.stop_fetching()
            st.info("⏹️ Parado")
            time.sleep(0.5)
            st.rerun()
    
    # Status
    if st.session_state.data_fetcher.is_running():
        st.success("🟢 CANDLES AO VIVO")
        st.markdown("🕯️ **Intervalo:** 10 segundos")
        st.markdown("📊 **OHLC:** Open/High/Low/Close")
        st.markdown("📈 **Volume:** Colorido por tendência")
    else:
        st.error("🔴 OFFLINE")
    
    st.markdown("---")
    
    # Configurações
    st.subheader("⚙️ Opções")
    
    update_speed = st.select_slider(
        "⚡ Velocidade:",
        options=[1, 2, 3, 5],
        value=2,
        format_func=lambda x: f"{x}s"
    )
    
    chart_style = st.radio(
        "📊 Estilo:",
        ["Completo (com volume)", "Mini (só candles)"],
        index=0
    )

# Área principal
current_data, historical_data = st.session_state.data_fetcher.get_data()

if selected_symbols and current_data:
    
    # Métricas OHLC
    st.subheader("💰 Dados OHLC Atuais")
    
    cols = st.columns(len(selected_symbols))
    
    for i, symbol in enumerate(selected_symbols):
        if symbol in current_data:
            data = current_data[symbol]
            
            with cols[i]:
                # Preço atual (Close)
                price = data['close']
                if price < 0.001:
                    price_str = f"${price:.8f}"
                elif price < 1:
                    price_str = f"${price:.6f}"
                elif price < 100:
                    price_str = f"${price:.4f}"
                else:
                    price_str = f"${price:,.2f}"
                
                candle_change = data.get('candle_change', 0)
                session_change = data['change']
                
                # Emoji do candle
                candle_emoji = "🟢" if candle_change >= 0 else "🔴"
                
                st.metric(
                    label=f"{candle_emoji} {symbol.replace('USDT', '/USD')}",
                    value=price_str,
                    delta=f"{session_change:+.2f}% (24h)",
                    help=f"Candle: {candle_change:+.3f}%\nOpen: ${data['open']:.6f}\nHigh: ${data['high']:.6f}\nLow: ${data['low']:.6f}"
                )
    
    st.markdown("---")
    
    # Gráficos de candlestick
    st.subheader("🕯️ Gráficos de Velas")
    
    if len(selected_symbols) == 1:
        # Um gráfico grande completo
        symbol = selected_symbols[0]
        if chart_style == "Completo (com volume)":
            fig = create_candlestick_chart(symbol, historical_data, current_data)
        else:
            fig = create_mini_candlestick(symbol, historical_data, current_data)
        st.plotly_chart(fig, use_container_width=True, key=f"candle_{symbol}")
    
    elif len(selected_symbols) == 2:
        # Dois gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            if chart_style == "Completo (com volume)":
                fig1 = create_candlestick_chart(selected_symbols[0], historical_data, current_data)
            else:
                fig1 = create_mini_candlestick(selected_symbols[0], historical_data, current_data)
            st.plotly_chart(fig1, use_container_width=True, key=f"candle_{selected_symbols[0]}")
            
        with col2:
            if chart_style == "Completo (com volume)":
                fig2 = create_candlestick_chart(selected_symbols[1], historical_data, current_data)
            else:
                fig2 = create_mini_candlestick(selected_symbols[1], historical_data, current_data)
            st.plotly_chart(fig2, use_container_width=True, key=f"candle_{selected_symbols[1]}")
    
    else:
        # Grid 2x2 com mini candles
        for i in range(0, len(selected_symbols), 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < len(selected_symbols):
                    fig = create_mini_candlestick(selected_symbols[i], historical_data, current_data)
                    st.plotly_chart(fig, use_container_width=True, key=f"candle_{selected_symbols[i]}")
            
            with col2:
                if i + 1 < len(selected_symbols):
                    fig = create_mini_candlestick(selected_symbols[i + 1], historical_data, current_data)
                    st.plotly_chart(fig, use_container_width=True, key=f"candle_{selected_symbols[i + 1]}")
    
    # Estatísticas dos candles
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        active_candles = len([s for s in selected_symbols if s in current_data])
        st.metric("🕯️ Candles Ativos", f"{active_candles}/{len(selected_symbols)}")
    
    with col2:
        if current_data:
            avg_candle_change = sum([data.get('candle_change', 0) for data in current_data.values()]) / len(current_data)
            trend = "🟢" if avg_candle_change >= 0 else "🔴"
            st.metric("📊 Tendência Candles", f"{avg_candle_change:+.3f}% {trend}")
    
    with col3:
        total_candles = sum([len(historical_data.get(s, {}).get('timestamps', [])) for s in selected_symbols])
        st.metric("📈 Total de Candles", f"{total_candles}")
    
    with col4:
        if current_data:
            total_volume = sum([data.get('volume', 0) for data in current_data.values()])
            st.metric("📊 Volume Total", f"{total_volume:,.0f}")

else:
    # Tela inicial
    st.info("👈 **Selecione até 4 criptomoedas** e clique em **'INICIAR'** para candles ao vivo!")
    
    st.subheader("🕯️ Recursos dos Candlesticks:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🕯️ Velas Japonesas Reais**
        - OHLC (Open, High, Low, Close)
        - Candles a cada 10 segundos
        - Cores verde/vermelho por tendência
        - Dados baseados em ticks realistas
        
        **📊 Volume Integrado**
        - Volume colorido por direção do candle
        - Correlação preço x volume
        - Gráfico de barras sincronizado
        """)
    
    with col2:
        st.markdown("""
        **📈 Análise Técnica**
        - Média móvel de 20 períodos
        - Identificação de tendências
        - Suporte e resistência visual
        - Padrões de candles
        
        **⚙️ Layouts Flexíveis**
        - Gráfico completo com volume
        - Mini candles para múltiplas moedas
        - Grid responsivo 2x2
        """)

# Auto-refresh
if st.session_state.data_fetcher.is_running():
    status_placeholder = st.empty()
    with status_placeholder.container():
        st.success(f"🕯️ FORMANDO CANDLES - Próximo tick em {update_speed}s")
    
    st.session_state.data_fetcher.update_data()
    time.sleep(update_speed)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("🕯️ **Candlestick Dashboard** | OHLC + Volume | Candles de 10s | Dados: CoinGecko + Simulação Realística")
