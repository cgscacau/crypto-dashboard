import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import requests
from typing import Dict, List
import json
import numpy as np

# Configuração da página
st.set_page_config(
    page_title="Crypto Dashboard - Tempo Real OHLC",
    page_icon="🕯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class CryptoDataFetcher:
    def __init__(self):
        self.price_data = {}
        self.historical_data = {}
        self.ohlc_data = {}
        self.running = False
        self.symbols = []
        self.candle_interval = 60  # segundos para cada vela
        
    def init_ohlc_data(self, symbol):
        """Inicializa estrutura de dados OHLC para um símbolo"""
        if symbol not in self.ohlc_data:
            self.ohlc_data[symbol] = {
                'timestamps': [],
                'open': [],
                'high': [],
                'low': [],
                'close': [],
                'volume': [],
                'current_candle': None
            }
    
    def update_ohlc_candle(self, symbol, price, volume, timestamp):
        """Atualiza ou cria nova vela OHLC"""
        self.init_ohlc_data(symbol)
        
        current_time = timestamp
        candle_start_time = pd.Timestamp(
            current_time.floor(f'{self.candle_interval}s')
        )
        
        ohlc = self.ohlc_data[symbol]
        
        # Se é uma nova vela ou primeira vela
        if (ohlc['current_candle'] is None or 
            candle_start_time > ohlc['timestamps'][-1] if ohlc['timestamps'] else True):
            
            # Finaliza vela anterior se existir
            if ohlc['current_candle'] is not None:
                # A vela anterior já está finalizada
                pass
            
            # Inicia nova vela
            ohlc['timestamps'].append(candle_start_time)
            ohlc['open'].append(price)
            ohlc['high'].append(price)
            ohlc['low'].append(price)
            ohlc['close'].append(price)
            ohlc['volume'].append(volume)
            
            ohlc['current_candle'] = {
                'start_time': candle_start_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
            
        else:
            # Atualiza vela atual
            if ohlc['timestamps']:
                last_idx = -1
                ohlc['high'][last_idx] = max(ohlc['high'][last_idx], price)
                ohlc['low'][last_idx] = min(ohlc['low'][last_idx], price)
                ohlc['close'][last_idx] = price
                ohlc['volume'][last_idx] = max(ohlc['volume'][last_idx], volume)
                
                # Atualiza vela atual
                ohlc['current_candle']['high'] = max(ohlc['current_candle']['high'], price)
                ohlc['current_candle']['low'] = min(ohlc['current_candle']['low'], price)
                ohlc['current_candle']['close'] = price
                ohlc['current_candle']['volume'] = max(ohlc['current_candle']['volume'], volume)
        
        # Limita histórico a 50 velas
        if len(ohlc['timestamps']) > 50:
            ohlc['timestamps'].pop(0)
            ohlc['open'].pop(0)
            ohlc['high'].pop(0)
            ohlc['low'].pop(0)
            ohlc['close'].pop(0)
            ohlc['volume'].pop(0)
        
    def fetch_coingecko_data(self, symbols):
        """Busca dados do CoinGecko (API gratuita e global)"""
        try:
            # Mapeia símbolos para IDs CoinGecko
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
                'include_24hr_vol': 'true',
                'include_last_updated_at': 'true'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                current_time = pd.Timestamp.now()
                
                for symbol in available_symbols:
                    coin_id = symbol_map[symbol]
                    if coin_id in data:
                        coin_data = data[coin_id]
                        price = float(coin_data['usd'])
                        change = float(coin_data.get('usd_24h_change', 0))
                        volume = float(coin_data.get('usd_24h_vol', 0))
                        
                        self.price_data[symbol] = {
                            'price': price,
                            'change': change,
                            'volume': volume,
                            'timestamp': current_time
                        }
                        
                        # Atualiza dados OHLC
                        self.update_ohlc_candle(symbol, price, volume, current_time)
                        
                        # Atualiza histórico de linha (para comparação)
                        if symbol not in self.historical_data:
                            self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                        
                        self.historical_data[symbol]['timestamps'].append(current_time)
                        self.historical_data[symbol]['prices'].append(price)
                        
                        # Limita histórico de linha
                        if len(self.historical_data[symbol]['timestamps']) > 100:
                            self.historical_data[symbol]['timestamps'].pop(0)
                            self.historical_data[symbol]['prices'].pop(0)
                
                return True
            else:
                print(f"CoinGecko API Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Erro CoinGecko: {str(e)}")
            return False
    
    def fetch_cryptocompare_data(self, symbols):
        """Busca dados do CryptoCompare (backup)"""
        try:
            symbol_map = {
                'BTCUSDT': 'BTC',
                'ETHUSDT': 'ETH',
                'BNBUSDT': 'BNB',
                'ADAUSDT': 'ADA',
                'XRPUSDT': 'XRP',
                'SOLUSDT': 'SOL',
                'DOTUSDT': 'DOT',
                'DOGEUSDT': 'DOGE',
                'AVAXUSDT': 'AVAX',
                'LINKUSDT': 'LINK',
                'MATICUSDT': 'MATIC',
                'LTCUSDT': 'LTC',
                'UNIUSDT': 'UNI',
                'ATOMUSDT': 'ATOM',
                'FILUSDT': 'FIL'
            }
            
            available_symbols = [s for s in symbols if s in symbol_map]
            if not available_symbols:
                return False
            
            crypto_symbols = ','.join([symbol_map[s] for s in available_symbols])
            
            url = "https://min-api.cryptocompare.com/data/pricemultifull"
            params = {
                'fsyms': crypto_symbols,
                'tsyms': 'USD'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                current_time = pd.Timestamp.now()
                
                if 'RAW' in data:
                    for symbol in available_symbols:
                        crypto_symbol = symbol_map[symbol]
                        if crypto_symbol in data['RAW'] and 'USD' in data['RAW'][crypto_symbol]:
                            coin_data = data['RAW'][crypto_symbol]['USD']
                            price = float(coin_data['PRICE'])
                            change = float(coin_data.get('CHANGEPCT24HOUR', 0))
                            volume = float(coin_data.get('VOLUME24HOUR', 0))
                            
                            self.price_data[symbol] = {
                                'price': price,
                                'change': change,
                                'volume': volume,
                                'timestamp': current_time
                            }
                            
                            # Atualiza dados OHLC
                            self.update_ohlc_candle(symbol, price, volume, current_time)
                            
                            # Atualiza histórico de linha
                            if symbol not in self.historical_data:
                                self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                            
                            self.historical_data[symbol]['timestamps'].append(current_time)
                            self.historical_data[symbol]['prices'].append(price)
                            
                            # Limita histórico de linha
                            if len(self.historical_data[symbol]['timestamps']) > 100:
                                self.historical_data[symbol]['timestamps'].pop(0)
                                self.historical_data[symbol]['prices'].pop(0)
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erro CryptoCompare: {str(e)}")
            return False
    
    def fetch_coinapi_data(self, symbols):
        """Busca dados do CoinAPI (outro backup)"""
        try:
            symbol_map = {
                'BTCUSDT': 'BTC',
                'ETHUSDT': 'ETH',
                'BNBUSDT': 'BNB',
                'ADAUSDT': 'ADA',
                'XRPUSDT': 'XRP',
                'SOLUSDT': 'SOL',
                'DOTUSDT': 'DOT',
                'DOGEUSDT': 'DOGE',
                'AVAXUSDT': 'AVAX',
                'LINKUSDT': 'LINK',
                'MATICUSDT': 'MATIC',
                'LTCUSDT': 'LTC',
                'UNIUSDT': 'UNI',
                'ATOMUSDT': 'ATOM',
                'FILUSDT': 'FIL'
            }
            
            current_time = pd.Timestamp.now()
            success_count = 0
            
            for symbol in symbols:
                if symbol in symbol_map:
                    crypto_symbol = symbol_map[symbol]
                    
                    # URL da API pública do CoinAPI (rate limit baixo mas funciona)
                    url = f"https://rest.coinapi.io/v1/exchangerate/{crypto_symbol}/USD"
                    
                    try:
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            price = float(data['rate'])
                            
                            # Como não temos dados de mudança 24h, calculamos baseado no histórico
                            change = 0
                            if symbol in self.historical_data and self.historical_data[symbol]['prices']:
                                old_price = self.historical_data[symbol]['prices'][0]
                                change = ((price - old_price) / old_price) * 100
                            
                            self.price_data[symbol] = {
                                'price': price,
                                'change': change,
                                'volume': 0,  # Não disponível na API gratuita
                                'timestamp': current_time
                            }
                            
                            # Atualiza dados OHLC
                            self.update_ohlc_candle(symbol, price, 0, current_time)
                            
                            # Atualiza histórico de linha
                            if symbol not in self.historical_data:
                                self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                            
                            self.historical_data[symbol]['timestamps'].append(current_time)
                            self.historical_data[symbol]['prices'].append(price)
                            
                            # Limita histórico de linha
                            if len(self.historical_data[symbol]['timestamps']) > 100:
                                self.historical_data[symbol]['timestamps'].pop(0)
                                self.historical_data[symbol]['prices'].pop(0)
                            
                            success_count += 1
                            time.sleep(0.1)  # Rate limiting
                            
                    except Exception as e:
                        print(f"Erro para {symbol}: {e}")
                        continue
            
            return success_count > 0
            
        except Exception as e:
            print(f"Erro CoinAPI: {str(e)}")
            return False
    
    def start_fetching(self, symbols, candle_interval=60):
        """Inicia busca de dados com fallbacks"""
        self.symbols = symbols
        self.candle_interval = candle_interval
        self.running = True
        
        # Tenta múltiplas APIs em ordem de preferência
        success = self.fetch_coingecko_data(symbols)
        
        if not success:
            st.warning("CoinGecko indisponível, tentando CryptoCompare...")
            success = self.fetch_cryptocompare_data(symbols)
        
        if not success:
            st.warning("CryptoCompare indisponível, tentando CoinAPI...")
            success = self.fetch_coinapi_data(symbols)
        
        return success
    
    def stop_fetching(self):
        """Para a busca de dados"""
        self.running = False
        self.price_data.clear()
        self.historical_data.clear()
        self.ohlc_data.clear()
    
    def update_data(self):
        """Atualiza dados"""
        if self.running and self.symbols:
            # Tenta as APIs na mesma ordem
            success = self.fetch_coingecko_data(self.symbols)
            if not success:
                success = self.fetch_cryptocompare_data(self.symbols)
            if not success:
                success = self.fetch_coinapi_data(self.symbols)
            return success
        return False
    
    def get_data(self):
        """Retorna dados atuais"""
        return self.price_data, self.historical_data
    
    def get_ohlc_data(self):
        """Retorna dados OHLC"""
        return self.ohlc_data
    
    def is_running(self):
        """Verifica se está ativo"""
        return self.running

# Inicialização do estado da sessão
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = CryptoDataFetcher()
    st.session_state.last_update = time.time()

def create_candlestick_chart(symbol, ohlc_data):
    """Cria gráfico de velas (candlestick) para um símbolo"""
    if symbol not in ohlc_data or not ohlc_data[symbol]['timestamps']:
        fig = go.Figure()
        fig.add_annotation(
            text="Carregando velas...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            template='plotly_dark',
            height=400,
            title=f'🕯️ {symbol.replace("USDT", "/USD")} - Carregando...',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    data = ohlc_data[symbol]
    
    if not data['timestamps'] or len(data['timestamps']) == 0:
        return create_candlestick_chart(symbol, {})
    
    fig = go.Figure()
    
    # Adiciona candlestick
    fig.add_trace(go.Candlestick(
        x=data['timestamps'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name=symbol.replace('USDT', ''),
        increasing_line_color='#00D4AA',  # Verde para alta
        decreasing_line_color='#FF6B6B',  # Vermelho para baixa
        increasing_fillcolor='#00D4AA',
        decreasing_fillcolor='#FF6B6B',
        line=dict(width=1),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                     'Tempo: %{x|%H:%M:%S}<br>' +
                     'Abertura: $%{open:,.4f}<br>' +
                     'Máxima: $%{high:,.4f}<br>' +
                     'Mínima: $%{low:,.4f}<br>' +
                     'Fechamento: $%{close:,.4f}<br>' +
                     '<extra></extra>'
    ))
    
    # Adiciona linha de média móvel simples (SMA)
    if len(data['close']) >= 5:
        sma_periods = min(5, len(data['close']))
        sma = []
        for i in range(len(data['close'])):
            if i >= sma_periods - 1:
                sma_value = sum(data['close'][i-sma_periods+1:i+1]) / sma_periods
                sma.append(sma_value)
            else:
                sma.append(None)
        
        fig.add_trace(go.Scatter(
            x=data['timestamps'],
            y=sma,
            mode='lines',
            name=f'SMA({sma_periods})',
            line=dict(color='#FFA500', width=2, dash='dash'),
            opacity=0.7,
            hovertemplate='<b>SMA(%{fullData.name})</b><br>' +
                         'Valor: $%{y:,.4f}<br>' +
                         '<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'🕯️ {symbol.replace("USDT", "/USD")} - Gráfico de Velas',
        xaxis_title='Tempo',
        yaxis_title='Preço (USD)',
        template='plotly_dark',
        height=400,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )
    
    # Remove range slider do candlestick
    fig.update_layout(xaxis_rangeslider_visible=False)
    
    # Formatar eixo Y baseado nos preços
    if data['close']:
        max_price = max(max(data['high']) if data['high'] else [0])
        min_price = min(min(data['low']) if data['low'] else [0])
        
        if max_price < 1:
            fig.update_yaxes(tickformat='.6f')
        elif max_price < 10:
            fig.update_yaxes(tickformat='.4f')
        else:
            fig.update_yaxes(tickformat=',.2f')
    
    return fig

def create_volume_chart(symbol, ohlc_data):
    """Cria gráfico de volume para um símbolo"""
    if symbol not in ohlc_data or not ohlc_data[symbol]['timestamps']:
        return None
    
    data = ohlc_data[symbol]
    
    if not data['volume'] or all(v == 0 for v in data['volume']):
        return None
    
    fig = go.Figure()
    
    # Cores baseadas na direção da vela
    colors = []
    for i in range(len(data['close'])):
        if i < len(data['open']) and data['close'][i] >= data['open'][i]:
            colors.append('#00D4AA')  # Verde para alta
        else:
            colors.append('#FF6B6B')  # Vermelho para baixa
    
    fig.add_trace(go.Bar(
        x=data['timestamps'],
        y=data['volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.7,
        hovertemplate='<b>Volume</b><br>' +
                     'Tempo: %{x|%H:%M:%S}<br>' +
                     'Volume: %{y:,.0f}<br>' +
                     '<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'📊 {symbol.replace("USDT", "/USD")} - Volume',
        xaxis_title='Tempo',
        yaxis_title='Volume',
        template='plotly_dark',
        height=200,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    return fig

def create_comparison_chart(symbols, historical_data):
    """Cria gráfico comparativo normalizado (mantém linha para comparação)"""
    fig = go.Figure()
    
    colors = ['#00D4AA', '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    
    for i, symbol in enumerate(symbols):
        if symbol in historical_data and historical_data[symbol]['timestamps']:
            timestamps = historical_data[symbol]['timestamps']
            prices = historical_data[symbol]['prices']
            
            if prices and len(prices) > 1:
                base_price = prices[0]
                normalized_prices = [(p - base_price) / base_price * 100 for p in prices]
                
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=normalized_prices,
                    mode='lines+markers',
                    name=symbol.replace('USDT', ''),
                    line=dict(color=colors[i % len(colors)], width=3),
                    marker=dict(size=4),
                    hovertemplate='<b>%{fullData.name}</b><br>' +
                                 'Variação: %{y:+.2f}%<br>' +
                                 'Tempo: %{x|%H:%M:%S}<br>' +
                                 '<extra></extra>'
                ))
    
    fig.update_layout(
        title='📊 Comparação de Performance - Variação %',
        xaxis_title='Tempo',
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
            xanchor="center",
            x=0.5
        )
    )
    
    # Adiciona linha zero
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    return fig

# Interface principal
st.title("🕯️ Dashboard de Criptomoedas - Gráfico de Velas")
st.markdown("*Análise técnica com candlesticks em tempo real*")
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
    
    # Configuração do timeframe das velas
    st.markdown("**🕯️ Configuração das Velas:**")
    candle_interval = st.selectbox(
        "Intervalo das velas:",
        options=[30, 60, 120, 300, 600],
        index=1,
        format_func=lambda x: f"{x}s" if x < 60 else f"{x//60}min"
    )
    
    st.markdown("---")
    
    # Controles de conexão
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Iniciar", type="primary", use_container_width=True):
            if selected_symbols:
                with st.spinner("🔄 Buscando dados..."):
                    success = st.session_state.data_fetcher.start_fetching(selected_symbols, candle_interval)
                    if success:
                        st.success("✅ Dados carregados!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao buscar dados de todas as fontes")
            else:
                st.warning("⚠️ Selecione pelo menos uma criptomoeda")
    
    with col2:
        if st.button("🛑 Parar", use_container_width=True):
            st.session_state.data_fetcher.stop_fetching()
            st.info("⏹️ Dashboard parado")
            time.sleep(0.5)
            st.rerun()
    
    # Status
    if st.session_state.data_fetcher.is_running():
        st.success("🟢 Dashboard Ativo")
        st.info(f"🕯️ Velas de {candle_interval}s")
    else:
        st.error("🔴 Dashboard Inativo")
    
    st.markdown("---")
    
    # Configurações de atualização
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    refresh_interval = st.select_slider(
        "⏱️ Intervalo de atualização:",
        options=[15, 30, 60, 120, 300],
        value=30,
        format_func=lambda x: f"{x}s" if x < 60 else f"{x//60}min"
    )
    
    # Opções de visualização
    st.markdown("---")
    st.markdown("**📊 Opções de Visualização:**")
    show_volume = st.checkbox("Mostrar Volume", value=True)
    show_sma = st.checkbox("Mostrar Média Móvel", value=True)
    
    # Informações sobre APIs
    st.markdown("---")
    st.markdown("**📡 Fontes de Dados:**")
    st.markdown("• CoinGecko API")
    st.markdown("• CryptoCompare API")  
    st.markdown("• CoinAPI")

# Área principal
current_data, historical_data = st.session_state.data_fetcher.get_data()
ohlc_data = st.session_state.data_fetcher.get_ohlc_data()

if selected_symbols and current_data:
    
    # Métricas em tempo real
    st.subheader("💰 Preços Atuais")
    
    num_cols = min(len(selected_symbols), 4)
    cols = st.columns(num_cols)
    
    for i, symbol in enumerate(selected_symbols):
        if symbol in current_data:
            data = current_data[symbol]
            
            with cols[i % num_cols]:
                # Formatação do preço
                if data['price'] < 0.01:
                    price_str = f"${data['price']:.8f}"
                elif data['price'] < 1:
                    price_str = f"${data['price']:.6f}"
                elif data['price'] < 10:
                    price_str = f"${data['price']:.4f}"
                else:
                    price_str = f"${data['price']:,.2f}"
                
                change_symbol = "+" if data['change'] >= 0 else ""
                
                st.metric(
                    label=f"💎 {symbol.replace('USDT', '/USD')}",
                    value=price_str,
                    delta=f"{change_symbol}{data['change']:.2f}%"
                )
    
    st.markdown("---")
    
    # Gráficos de velas
    st.subheader("🕯️ Gráficos de Velas (Candlestick)")
    
    num_selected = len(selected_symbols)
    
    if num_selected == 1:
        # Um gráfico grande
        symbol = selected_symbols[0]
        candlestick_fig = create_candlestick_chart(symbol, ohlc_data)
        st.plotly_chart(candlestick_fig, use_container_width=True)
        
        # Volume se habilitado
        if show_volume:
            volume_fig = create_volume_chart(symbol, ohlc_data)
            if volume_fig:
                st.plotly_chart(volume_fig, use_container_width=True)
    
    elif num_selected <= 4:
        # Dois por linha
        for i in range(0, num_selected, 2):
            col1, col2 = st.columns(2)
            
            with col1:
                if i < num_selected:
                    symbol = selected_symbols[i]
                    candlestick_fig = create_candlestick_chart(symbol, ohlc_data)
                    st.plotly_chart(candlestick_fig, use_container_width=True)
                    
                    if show_volume:
                        volume_fig = create_volume_chart(symbol, ohlc_data)
                        if volume_fig:
                            st.plotly_chart(volume_fig, use_container_width=True)
            
            with col2:
                if i + 1 < num_selected:
                    symbol = selected_symbols[i + 1]
                    candlestick_fig = create_candlestick_chart(symbol, ohlc_data)
                    st.plotly_chart(candlestick_fig, use_container_width=True)
                    
                    if show_volume:
                        volume_fig = create_volume_chart(symbol, ohlc_data)
                        if volume_fig:
                            st.plotly_chart(volume_fig, use_container_width=True)
    
    else:
        # Três por linha para mais de 4
        for i in range(0, num_selected, 3):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if i < num_selected:
                    symbol = selected_symbols[i]
                    candlestick_fig = create_candlestick_chart(symbol, ohlc_data)
                    st.plotly_chart(candlestick_fig, use_container_width=True)
            
            with col2:
                if i + 1 < num_selected:
                    symbol = selected_symbols[i + 1]
                    candlestick_fig = create_candlestick_chart(symbol, ohlc_data)
                    st.plotly_chart(candlestick_fig, use_container_width=True)
                    
            with col3:
                if i + 2 < num_selected:
                    symbol = selected_symbols[i + 2]
                    candlestick_fig = create_candlestick_chart(symbol, ohlc_data)
                    st.plotly_chart(candlestick_fig, use_container_width=True)
    
    # Gráfico de comparação (mantém linha)
    if num_selected > 1:
        st.markdown("---")
        comparison_fig = create_comparison_chart(selected_symbols, historical_data)
        st.plotly_chart(comparison_fig, use_container_width=True)
    
    # Estatísticas OHLC
    st.markdown("---")
    st.subheader("📊 Estatísticas das Velas")
    
    for symbol in selected_symbols:
        if symbol in ohlc_data and ohlc_data[symbol]['timestamps']:
            data = ohlc_data[symbol]
            
            if data['close']:
                with st.expander(f"📈 {symbol.replace('USDT', '/USD')} - Detalhes"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("🕯️ Total de Velas", len(data['timestamps']))
                    
                    with col2:
                        if data['high']:
                            max_high = max(data['high'])
                            st.metric("⬆️ Máxima", f"${max_high:,.4f}")
                    
                    with col3:
                        if data['low']:
                            min_low = min(data['low'])
                            st.metric("⬇️ Mínima", f"${min_low:,.4f}")
                    
                    with col4:
                        if data['close'] and len(data['close']) > 1:
                            price_change = ((data['close'][-1] - data['close'][0]) / data['close'][0]) * 100
                            st.metric("📈 Variação Total", f"{price_change:+.2f}%")
    
    # Estatísticas gerais
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 Moedas Ativas", len([s for s in selected_symbols if s in current_data]))
    
    with col2:
        if current_data:
            last_update = max([data['timestamp'] for data in current_data.values()])
            seconds_ago = int((pd.Timestamp.now() - last_update).total_seconds())
            st.metric("🕒 Última Atualização", f"{seconds_ago}s atrás")
    
    with col3:
        total_candles = sum([len(ohlc_data.get(s, {}).get('timestamps', [])) for s in selected_symbols])
        st.metric("🕯️ Total de Velas", total_candles)
    
    with col4:
        if current_data:
            avg_change = sum([data['change'] for data in current_data.values()]) / len(current_data)
            st.metric("📈 Média de Variação", f"{avg_change:+.2f}%")

elif selected_symbols and st.session_state.data_fetcher.is_running():
    # Conectado mas sem dados ainda
    st.info("🔄 Dashboard ativo! Aguardando próxima atualização de dados...")
    
    with st.spinner("Carregando dados das APIs..."):
        time.sleep(3)
        st.rerun()

else:
    # Tela inicial
    st.info("👈 **Selecione as criptomoedas** na barra lateral e clique em **'Iniciar'** para começar!")
    
    st.subheader("🌟 Recursos do Dashboard:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🕯️ Análise Técnica**
        - Gráficos de velas (OHLC)
        - Média móvel simples
        - Análise de volume
        - Timeframes configuráveis
        """)
    
    with col2:
        st.markdown("""
        **📊 Visualizações**
        - Candlesticks interativos
        - Gráficos de volume
        - Comparação de performance
        - Layout responsivo
        """)
    
    with col3:
        st.markdown("""
        **🌐 APIs Confiáveis**
        - CoinGecko (principal)
        - CryptoCompare (backup)
        - CoinAPI (backup)
        - Cobertura global
        """)
    
    # Demo com dados OHLC fictícios
    st.markdown("---")
    st.subheader("🎮 Preview do Dashboard:")
    
    # Cria dados demo OHLC
    demo_times = pd.date_range(start='2024-01-01 10:00:00', periods=10, freq='1H')
    demo_open = [45000, 45100, 45050, 45200, 45150, 45300, 45250, 45400, 45350, 45500]
    demo_high = [45150, 45200, 45150, 45300, 45250, 45400, 45350, 45500, 45450, 45600]
    demo_low = [44950, 45000, 44950, 45100, 45050, 45200, 45150, 45300, 45250, 45400]
    demo_close = [45100, 45050, 45200, 45150, 45300, 45250, 45400, 45350, 45500, 45450]
    
    demo_fig = go.Figure()
    
    demo_fig.add_trace(go.Candlestick(
        x=demo_times,
        open=demo_open,
        high=demo_high,
        low=demo_low,
        close=demo_close,
        name='BTC/USD (Demo)',
        increasing_line_color='#00D4AA',
        decreasing_line_color='#FF6B6B',
        increasing_fillcolor='#00D4AA',
        decreasing_fillcolor='#FF6B6B'
    ))
    
    demo_fig.update_layout(
        title='🕯️ Exemplo: Bitcoin/USD - Gráfico de Velas',
        template='plotly_dark',
        height=400,
        showlegend=False,
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(demo_fig, use_container_width=True)

# Auto-refresh
if auto_refresh and st.session_state.data_fetcher.is_running():
    with st.spinner(f"🔄 Atualizando dados... (próxima atualização em {refresh_interval}s)"):
        st.session_state.data_fetcher.update_data()
        time.sleep(refresh_interval)
        st.rerun()

# Footer
st.markdown("---")
st.markdown("💡 **Dashboard de Criptomoedas com Análise Técnica** - Gráficos de velas em tempo real | Dados de CoinGecko, CryptoCompare e CoinAPI")
