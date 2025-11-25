import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import requests
from typing import Dict, List
import json
import random
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Crypto Dashboard - Real Time",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

class RealTimeCryptoFetcher:
    def __init__(self):
        self.price_data = {}
        self.historical_data = {}
        self.running = False
        self.symbols = []
        self.base_prices = {}  # Para simulação realista
        self.last_api_call = 0
        self.api_interval = 30  # Chama API real a cada 30s
        
    def fetch_real_data(self, symbols):
        """Busca dados reais das APIs (menos frequente)"""
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
                        
                        # Atualiza preço base para simulação
                        self.base_prices[symbol] = {
                            'price': price,
                            'change': change,
                            'volume': volume,
                            'volatility': min(abs(change) * 0.1, 2.0)  # Volatilidade baseada na mudança real
                        }
                
                self.last_api_call = time.time()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erro API: {str(e)}")
            return False
    
    def simulate_realistic_price(self, symbol):
        """Simula variações de preço realistas baseadas em dados reais"""
        if symbol not in self.base_prices:
            return None
        
        base_data = self.base_prices[symbol]
        base_price = base_data['price']
        volatility = base_data['volatility']
        
        # Gera variação realista usando random walk
        # Variação pequena (-0.5% a +0.5%) com tendência baseada no momentum
        random_change = random.gauss(0, volatility * 0.001)  # Distribuição normal
        
        # Adiciona um pouco de momentum (tendência a continuar direção)
        if hasattr(self, '_last_direction'):
            momentum = self._last_direction.get(symbol, 0) * 0.3
            random_change += momentum
        else:
            self._last_direction = {}
        
        # Limita a variação máxima por tick
        random_change = max(-0.005, min(0.005, random_change))  # Máximo 0.5% por tick
        
        new_price = base_price * (1 + random_change)
        
        # Armazena direção para momentum
        self._last_direction[symbol] = random_change
        
        return new_price
    
    def update_simulated_data(self):
        """Atualiza dados com simulação realista"""
        current_time = pd.Timestamp.now()
        
        for symbol in self.symbols:
            if symbol in self.base_prices:
                # Simula novo preço
                new_price = self.simulate_realistic_price(symbol)
                if new_price is None:
                    continue
                
                # Calcula mudança desde o último tick
                last_price = None
                if symbol in self.price_data:
                    last_price = self.price_data[symbol]['price']
                
                tick_change = 0
                if last_price:
                    tick_change = ((new_price - last_price) / last_price) * 100
                
                # Calcula mudança desde o início da sessão
                session_change = 0
                if symbol in self.historical_data and self.historical_data[symbol]['prices']:
                    first_price = self.historical_data[symbol]['prices'][0]
                    session_change = ((new_price - first_price) / first_price) * 100
                else:
                    session_change = self.base_prices[symbol]['change']
                
                # Simula volume baseado na volatilidade
                base_volume = self.base_prices[symbol]['volume']
                volume_multiplier = 1 + abs(tick_change) * 10  # Mais volume com mais volatilidade
                simulated_volume = base_volume * volume_multiplier
                
                self.price_data[symbol] = {
                    'price': new_price,
                    'change': session_change,
                    'tick_change': tick_change,
                    'volume': simulated_volume,
                    'timestamp': current_time
                }
                
                # Atualiza histórico
                if symbol not in self.historical_data:
                    self.historical_data[symbol] = {'timestamps': [], 'prices': [], 'volumes': []}
                
                self.historical_data[symbol]['timestamps'].append(current_time)
                self.historical_data[symbol]['prices'].append(new_price)
                self.historical_data[symbol]['volumes'].append(simulated_volume)
                
                # Limita histórico (mais pontos para gráfico mais suave)
                max_points = 200
                if len(self.historical_data[symbol]['timestamps']) > max_points:
                    self.historical_data[symbol]['timestamps'].pop(0)
                    self.historical_data[symbol]['prices'].pop(0)
                    self.historical_data[symbol]['volumes'].pop(0)
    
    def start_fetching(self, symbols):
        """Inicia busca de dados"""
        self.symbols = symbols
        self.running = True
        
        # Busca dados reais iniciais
        success = self.fetch_real_data(symbols)
        if success:
            # Inicia com dados simulados baseados nos reais
            self.update_simulated_data()
        
        return success
    
    def stop_fetching(self):
        """Para a busca de dados"""
        self.running = False
        self.price_data.clear()
        self.historical_data.clear()
        self.base_prices.clear()
    
    def update_data(self):
        """Atualiza dados (rápido para simulação, lento para API real)"""
        if not self.running or not self.symbols:
            return False
        
        current_time = time.time()
        
        # Atualiza dados reais da API ocasionalmente
        if current_time - self.last_api_call > self.api_interval:
            self.fetch_real_data(self.symbols)
        
        # Sempre atualiza simulação para tempo real
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
    st.session_state.data_fetcher = RealTimeCryptoFetcher()
    st.session_state.last_update = time.time()

def create_realtime_chart(symbol, historical_data):
    """Cria gráfico em tempo real com candlestick simulado"""
    if symbol not in historical_data or not historical_data[symbol]['timestamps']:
        fig = go.Figure()
        fig.add_annotation(
            text="🔄 Conectando...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=18, color="#00D4AA")
        )
        fig.update_layout(
            template='plotly_dark',
            height=400,
            title=f'⚡ {symbol.replace("USDT", "/USD")} - Tempo Real',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    timestamps = historical_data[symbol]['timestamps']
    prices = historical_data[symbol]['prices']
    volumes = historical_data[symbol].get('volumes', [0] * len(prices))
    
    if len(prices) < 2:
        return create_realtime_chart(symbol, {})
    
    fig = go.Figure()
    
    # Determina cor baseada na tendência recente
    recent_change = prices[-1] - prices[max(0, len(prices)-10)]
    color = '#00D4AA' if recent_change >= 0 else '#FF4B4B'
    
    # Linha principal com gradiente
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        mode='lines',
        name=symbol.replace('USDT', ''),
        line=dict(
            color=color, 
            width=3,
            shape='spline',  # Linha mais suave
            smoothing=0.3
        ),
        fill='tonexty',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)',
        hovertemplate='<b>%{fullData.name}</b><br>' +
                     'Preço: $%{y:,.6f}<br>' +
                     'Tempo: %{x|%H:%M:%S}<br>' +
                     '<extra></extra>'
    ))
    
    # Adiciona pontos nos últimos 5 valores para destaque
    if len(prices) >= 5:
        fig.add_trace(go.Scatter(
            x=timestamps[-5:],
            y=prices[-5:],
            mode='markers',
            marker=dict(
                size=[6, 7, 8, 9, 12],  # Último ponto maior
                color=color,
                line=dict(width=2, color='white'),
                symbol='circle'
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Linha de média móvel simples (últimos 20 pontos)
    if len(prices) >= 20:
        ma_prices = []
        ma_timestamps = []
        for i in range(19, len(prices)):
            ma_price = sum(prices[i-19:i+1]) / 20
            ma_prices.append(ma_price)
            ma_timestamps.append(timestamps[i])
        
        fig.add_trace(go.Scatter(
            x=ma_timestamps,
            y=ma_prices,
            mode='lines',
            name='MA20',
            line=dict(color='orange', width=1, dash='dot'),
            opacity=0.7,
            hovertemplate='MA20: $%{y:,.6f}<extra></extra>'
        ))
    
    # Configuração do layout
    fig.update_layout(
        title=f'⚡ {symbol.replace("USDT", "/USD")} - Tempo Real',
        xaxis_title='',
        yaxis_title='Preço (USD)',
        template='plotly_dark',
        height=400,
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
        )
    )
    
    # Formatar eixos
    if prices:
        max_price = max(prices)
        min_price = min(prices)
        price_range = max_price - min_price
        
        if max_price < 0.01:
            fig.update_yaxes(tickformat='.8f')
        elif max_price < 1:
            fig.update_yaxes(tickformat='.6f')
        elif max_price < 10:
            fig.update_yaxes(tickformat='.4f')
        else:
            fig.update_yaxes(tickformat=',.2f')
        
        # Range dinâmico
        if price_range > 0:
            fig.update_yaxes(
                range=[min_price - price_range * 0.05, max_price + price_range * 0.05]
            )
    
    # Configuração do eixo X para tempo real
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.2)',
        tickformat='%H:%M:%S'
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.2)'
    )
    
    return fig

def create_volume_chart(symbol, historical_data):
    """Cria gráfico de volume"""
    if symbol not in historical_data or 'volumes' not in historical_data[symbol]:
        return None
    
    timestamps = historical_data[symbol]['timestamps']
    volumes = historical_data[symbol]['volumes']
    prices = historical_data[symbol]['prices']
    
    if len(volumes) < 2:
        return None
    
    fig = go.Figure()
    
    # Cores baseadas na variação de preço
    colors = []
    for i in range(len(volumes)):
        if i == 0:
            colors.append('#00D4AA')
        else:
            color = '#00D4AA' if prices[i] >= prices[i-1] else '#FF4B4B'
            colors.append(color)
    
    fig.add_trace(go.Bar(
        x=timestamps,
        y=volumes,
        marker_color=colors,
        name='Volume',
        opacity=0.7,
        hovertemplate='Volume: %{y:,.0f}<br>Tempo: %{x|%H:%M:%S}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'📊 {symbol.replace("USDT", "/USD")} - Volume',
        xaxis_title='',
        yaxis_title='Volume',
        template='plotly_dark',
        height=200,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

# Interface principal
st.title("⚡ Dashboard Crypto - Tempo Real")
st.markdown("*Atualizações a cada segundo com simulação realista baseada em dados reais*")
st.markdown("---")

# Sidebar para configurações
with st.sidebar:
    st.header("⚙️ Configurações")
    
    # Seleção de criptomoedas
    available_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT'
    ]
    
    selected_symbols = st.multiselect(
        "🎯 Selecione as criptomoedas:",
        available_symbols,
        default=['BTCUSDT', 'ETHUSDT'],
        max_selections=4  # Limitado para melhor performance
    )
    
    st.markdown("---")
    
    # Controles
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 INICIAR", type="primary", use_container_width=True):
            if selected_symbols:
                with st.spinner("🔄 Conectando APIs..."):
                    success = st.session_state.data_fetcher.start_fetching(selected_symbols)
                    if success:
                        st.success("✅ ATIVO!")
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
    
    # Status em tempo real
    if st.session_state.data_fetcher.is_running():
        st.success("🟢 TRANSMISSÃO AO VIVO")
        st.markdown("📡 **Fonte:** CoinGecko API")
        st.markdown("🔄 **Atualização:** 1-2 segundos")
        st.markdown("📊 **Simulação:** Realística")
    else:
        st.error("🔴 OFFLINE")
    
    st.markdown("---")
    
    # Configurações avançadas
    st.subheader("⚙️ Configurações")
    
    show_volume = st.checkbox("📊 Mostrar Volume", value=True)
    show_ma = st.checkbox("📈 Média Móvel", value=True)
    
    update_speed = st.select_slider(
        "⚡ Velocidade de Atualização:",
        options=[1, 2, 3, 5],
        value=2,
        format_func=lambda x: f"{x}s - {'Muito Rápido' if x==1 else 'Rápido' if x==2 else 'Médio' if x==3 else 'Lento'}"
    )

# Área principal
current_data, historical_data = st.session_state.data_fetcher.get_data()

if selected_symbols and current_data:
    
    # Métricas em tempo real com animação
    st.subheader("💰 Preços ao Vivo")
    
    cols = st.columns(len(selected_symbols))
    
    for i, symbol in enumerate(selected_symbols):
        if symbol in current_data:
            data = current_data[symbol]
            
            with cols[i]:
                # Formatação de preço inteligente
                price = data['price']
                if price < 0.001:
                    price_str = f"${price:.8f}"
                elif price < 1:
                    price_str = f"${price:.6f}"
                elif price < 100:
                    price_str = f"${price:.4f}"
                else:
                    price_str = f"${price:,.2f}"
                
                # Delta com mudança do tick
                tick_change = data.get('tick_change', 0)
                session_change = data['change']
                
                # Emoji baseado na tendência
                trend_emoji = "🟢" if session_change >= 0 else "🔴"
                tick_emoji = "📈" if tick_change >= 0 else "📉"
                
                st.metric(
                    label=f"{trend_emoji} {symbol.replace('USDT', '/USD')}",
                    value=price_str,
                    delta=f"{session_change:+.2f}% (24h)",
                    help=f"Último tick: {tick_change:+.4f}% {tick_emoji}"
                )
    
    st.markdown("---")
    
    # Gráficos em tempo real
    st.subheader("📈 Gráficos ao Vivo")
    
    if len(selected_symbols) == 1:
        # Um gráfico grande
        symbol = selected_symbols[0]
        fig = create_realtime_chart(symbol, historical_data)
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{symbol}")
        
        if show_volume:
            vol_fig = create_volume_chart(symbol, historical_data)
            if vol_fig:
                st.plotly_chart(vol_fig, use_container_width=True, key=f"volume_{symbol}")
    
    elif len(selected_symbols) == 2:
        # Dois gráficos lado a lado
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = create_realtime_chart(selected_symbols[0], historical_data)
            st.plotly_chart(fig1, use_container_width=True, key=f"chart_{selected_symbols[0]}")
            
        with col2:
            fig2 = create_realtime_chart(selected_symbols[1], historical_data)
            st.plotly_chart(fig2, use_container_width=True, key=f"chart_{selected_symbols[1]}")
    
    else:
        # Grid 2x2
        for i in range(0, len(selected_symbols), 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < len(selected_symbols):
                    fig = create_realtime_chart(selected_symbols[i], historical_data)
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{selected_symbols[i]}")
            
            with col2:
                if i + 1 < len(selected_symbols):
                    fig = create_realtime_chart(selected_symbols[i + 1], historical_data)
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{selected_symbols[i + 1]}")
    
    # Estatísticas em tempo real
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        active_count = len([s for s in selected_symbols if s in current_data])
        st.metric("🎯 Ativos", f"{active_count}/{len(selected_symbols)}")
    
    with col2:
        if current_data:
            last_update = max([data['timestamp'] for data in current_data.values()])
            seconds_ago = int((pd.Timestamp.now() - last_update).total_seconds())
            st.metric("🕒 Última Atualização", f"{seconds_ago}s")
    
    with col3:
        total_points = sum([len(historical_data.get(s, {}).get('prices', [])) for s in selected_symbols])
        st.metric("📊 Pontos de Dados", f"{total_points:,}")
    
    with col4:
        if current_data:
            avg_change = sum([data['change'] for data in current_data.values()]) / len(current_data)
            trend = "🚀" if avg_change > 1 else "📈" if avg_change > 0 else "📉" if avg_change > -1 else "💥"
            st.metric("📈 Tendência Geral", f"{avg_change:+.2f}% {trend}")

else:
    # Tela inicial
    st.info("👈 **Selecione até 4 criptomoedas** e clique em **'INICIAR'** para transmissão ao vivo!")
    
    st.subheader("⚡ Recursos do Dashboard em Tempo Real:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🚀 Tempo Real Verdadeiro**
        - Atualizações a cada 1-2 segundos
        - Simulação realística baseada em dados reais
        - Gráficos suaves com spline
        - Indicadores de tendência instantâneos
        
        **📊 Visualizações Avançadas**
        - Gráficos com gradientes e animações
        - Média móvel em tempo real
        - Volume colorido por tendência
        - Múltiplos layouts responsivos
        """)
    
    with col2:
        st.markdown("""
        **🎯 Dados Precisos**
        - Base em APIs reais (CoinGecko)
        - Volatilidade calculada dinamicamente
        - Momentum e tendências realistas
        - Histórico de até 200 pontos
        
        **⚙️ Configurações Flexíveis**
        - Velocidade de atualização ajustável
        - Seleção de indicadores
        - Layout adaptativo
        - Performance otimizada
        """)

# Auto-refresh em tempo real
if st.session_state.data_fetcher.is_running():
    # Placeholder para status ao vivo
    status_placeholder = st.empty()
    
    with status_placeholder.container():
        st.success(f"🔴 AO VIVO - Próxima atualização em {update_speed}s")
    
    # Atualiza dados
    st.session_state.data_fetcher.update_data()
    
    # Aguarda e recarrega
    time.sleep(update_speed)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("⚡ **Dashboard Crypto Real-Time** | Dados: CoinGecko API + Simulação Realística | Atualização: 1-5s")
