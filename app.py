import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import requests
import threading
from typing import Dict, List
import json

# Configuração da página
st.set_page_config(
    page_title="Crypto Dashboard - Tempo Real",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class CryptoDataFetcher:
    def __init__(self):
        self.price_data = {}
        self.historical_data = {}
        self.running = False
        self.symbols = []
        
    def fetch_binance_data(self, symbols):
        """Busca dados da API REST da Binance"""
        try:
            # URL da API pública da Binance (funciona globalmente)
            url = "https://api.binance.com/api/v3/ticker/24hr"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                current_time = pd.Timestamp.now()
                
                for item in data:
                    symbol = item['symbol']
                    if symbol in symbols:
                        price = float(item['lastPrice'])
                        change = float(item['priceChangePercent'])
                        volume = float(item['volume'])
                        
                        # Atualiza dados atuais
                        self.price_data[symbol] = {
                            'price': price,
                            'change': change,
                            'volume': volume,
                            'timestamp': current_time
                        }
                        
                        # Atualiza histórico
                        if symbol not in self.historical_data:
                            self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                        
                        self.historical_data[symbol]['timestamps'].append(current_time)
                        self.historical_data[symbol]['prices'].append(price)
                        
                        # Limita histórico
                        if len(self.historical_data[symbol]['timestamps']) > 50:
                            self.historical_data[symbol]['timestamps'].pop(0)
                            self.historical_data[symbol]['prices'].pop(0)
                
                return True
            else:
                st.error(f"Erro na API: {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"Erro ao buscar dados: {str(e)}")
            return False
    
    def fetch_alternative_data(self, symbols):
        """Busca dados de fonte alternativa (CoinGecko)"""
        try:
            # Mapeia símbolos Binance para IDs CoinGecko
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
            
            # Filtra símbolos disponíveis
            available_symbols = [s for s in symbols if s in symbol_map]
            if not available_symbols:
                return False
            
            # Monta lista de IDs
            ids = ','.join([symbol_map[s] for s in available_symbols])
            
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': ids,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current_time = pd.Timestamp.now()
                
                for symbol in available_symbols:
                    coin_id = symbol_map[symbol]
                    if coin_id in data:
                        coin_data = data[coin_id]
                        price = float(coin_data['usd'])
                        change = float(coin_data.get('usd_24h_change', 0))
                        
                        # Atualiza dados atuais
                        self.price_data[symbol] = {
                            'price': price,
                            'change': change,
                            'volume': 0,  # CoinGecko free tier não tem volume
                            'timestamp': current_time
                        }
                        
                        # Atualiza histórico
                        if symbol not in self.historical_data:
                            self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                        
                        self.historical_data[symbol]['timestamps'].append(current_time)
                        self.historical_data[symbol]['prices'].append(price)
                        
                        # Limita histórico
                        if len(self.historical_data[symbol]['timestamps']) > 50:
                            self.historical_data[symbol]['timestamps'].pop(0)
                            self.historical_data[symbol]['prices'].pop(0)
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erro CoinGecko: {str(e)}")
            return False
    
    def start_fetching(self, symbols):
        """Inicia busca de dados"""
        self.symbols = symbols
        self.running = True
        
        # Tenta Binance primeiro, depois CoinGecko
        success = self.fetch_binance_data(symbols)
        if not success:
            success = self.fetch_alternative_data(symbols)
        
        return success
    
    def stop_fetching(self):
        """Para a busca de dados"""
        self.running = False
    
    def update_data(self):
        """Atualiza dados"""
        if self.running and self.symbols:
            success = self.fetch_binance_data(self.symbols)
            if not success:
                success = self.fetch_alternative_data(self.symbols)
            return success
        return False
    
    def get_data(self):
        """Retorna dados atuais"""
        return self.price_data, self.historical_data
    
    def is_running(self):
        """Verifica se está ativo"""
        return self.running

# Inicialização do estado da sessão
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = CryptoDataFetcher()
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
        yaxis_title='Preço (USD)',
        template='plotly_dark',
        height=350,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    # Formatar eixo Y
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
        if st.button("🚀 Iniciar", type="primary", use_container_width=True):
            if selected_symbols:
                with st.spinner("Buscando dados..."):
                    success = st.session_state.data_fetcher.start_fetching(selected_symbols)
                    if success:
                        st.success("Dados carregados!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao buscar dados")
            else:
                st.warning("Selecione pelo menos uma criptomoeda")
    
    with col2:
        if st.button("🛑 Parar", use_container_width=True):
            st.session_state.data_fetcher.stop_fetching()
            st.info("Parado")
            time.sleep(0.5)
            st.rerun()
    
    # Status
    if st.session_state.data_fetcher.is_running():
        st.success("🟢 Ativo")
    else:
        st.error("🔴 Inativo")
    
    st.markdown("---")
    
    # Configurações de atualização
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    refresh_interval = st.select_slider(
        "Intervalo de atualização:",
        options=[10, 30, 60, 120],
        value=30,
        format_func=lambda x: f"{x}s"
    )

# Área principal
current_data, historical_data = st.session_state.data_fetcher.get_data()

if selected_symbols and current_data:
    
    # Métricas em tempo real
    st.subheader("📊 Preços Atuais")
    
    num_cols = min(len(selected_symbols), 3)
    cols = st.columns(num_cols)
    
    for i, symbol in enumerate(selected_symbols):
        if symbol in current_data:
            data = current_data[symbol]
            
            with cols[i % num_cols]:
                # Formatação do preço
                if data['price'] < 1:
                    price_str = f"${data['price']:.6f}"
                elif data['price'] < 10:
                    price_str = f"${data['price']:.4f}"
                else:
                    price_str = f"${data['price']:.2f}"
                
                change_symbol = "+" if data['change'] >= 0 else ""
                
                st.metric(
                    label=symbol.replace('USDT', '/USD'),
                    value=price_str,
                    delta=f"{change_symbol}{data['change']:.2f}%"
                )
    
    st.markdown("---")
    
    # Gráficos individuais
    st.subheader("📈 Histórico de Preços")
    
    num_selected = len(selected_symbols)
    
    if num_selected == 1:
        fig = create_price_chart(selected_symbols[0], historical_data)
        st.plotly_chart(fig, use_container_width=True)
    elif num_selected <= 4:
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

else:
    # Tela inicial
    st.info("👈 Selecione as criptomoedas na barra lateral e clique em 'Iniciar' para começar!")
    
    st.subheader("🎯 Recursos do Dashboard:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📊 Dados em Tempo Real**
        - Preços atualizados
        - Variação 24h
        - Múltiplas fontes de dados
        """)
    
    with col2:
        st.markdown("""
        **📈 Gráficos Interativos**
        - Histórico de preços
        - Gráficos individuais
        - Comparação de performance
        """)
    
    with col3:
        st.markdown("""
        **🌐 APIs Confiáveis**
        - Binance API
        - CoinGecko (fallback)
        - Dados globalmente acessíveis
        """)

# Auto-refresh
if auto_refresh and st.session_state.data_fetcher.is_running():
    # Atualiza dados
    st.session_state.data_fetcher.update_data()
    time.sleep(refresh_interval)
    st.rerun()

# Footer
st.markdown("---")
st.markdown("💡 **Fonte de Dados:** Binance API (principal) e CoinGecko API (fallback). Atualização automática configurável.")
