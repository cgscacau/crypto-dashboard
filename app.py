import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import requests
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
                        
                        # Atualiza histórico
                        if symbol not in self.historical_data:
                            self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                        
                        self.historical_data[symbol]['timestamps'].append(current_time)
                        self.historical_data[symbol]['prices'].append(price)
                        
                        # Limita histórico
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
                            
                            # Atualiza histórico
                            if symbol not in self.historical_data:
                                self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                            
                            self.historical_data[symbol]['timestamps'].append(current_time)
                            self.historical_data[symbol]['prices'].append(price)
                            
                            # Limita histórico
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
                            
                            # Atualiza histórico
                            if symbol not in self.historical_data:
                                self.historical_data[symbol] = {'timestamps': [], 'prices': []}
                            
                            self.historical_data[symbol]['timestamps'].append(current_time)
                            self.historical_data[symbol]['prices'].append(price)
                            
                            # Limita histórico
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
    
    def start_fetching(self, symbols):
        """Inicia busca de dados com fallbacks"""
        self.symbols = symbols
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
            text="Carregando dados...", 
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            template='plotly_dark',
            height=350,
            title=f'{symbol.replace("USDT", "/USD")} - Carregando...',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    
    timestamps = historical_data[symbol]['timestamps']
    prices = historical_data[symbol]['prices']
    
    if not timestamps or not prices:
        return create_price_chart(symbol, {})
    
    fig = go.Figure()
    
    # Determina cor baseada na tendência
    color = '#00D4AA' if len(prices) > 1 and prices[-1] >= prices[0] else '#FF6B6B'
    
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=prices,
        mode='lines+markers',
        name=symbol.replace('USDT', ''),
        line=dict(color=color, width=3),
        marker=dict(size=4, color=color),
        fill='tonexty' if len(prices) > 1 else None,
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)',
        hovertemplate='<b>%{fullData.name}</b><br>' +
                     'Preço: $%{y:,.4f}<br>' +
                     'Tempo: %{x|%H:%M:%S}<br>' +
                     '<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'📈 {symbol.replace("USDT", "/USD")}',
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
        min_price = min(prices)
        if max_price < 1:
            fig.update_yaxes(tickformat='.6f')
        elif max_price < 10:
            fig.update_yaxes(tickformat='.4f')
        else:
            fig.update_yaxes(tickformat=',.2f')
        
        # Adiciona range para melhor visualização
        price_range = max_price - min_price
        fig.update_yaxes(
            range=[min_price - price_range * 0.1, max_price + price_range * 0.1]
        )
    
    return fig

def create_comparison_chart(symbols, historical_data):
    """Cria gráfico comparativo normalizado"""
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
st.title("📈 Dashboard de Criptomoedas")
st.markdown("*Dados em tempo real de múltiplas fontes confiáveis*")
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
        max_selections=8
    )
    
    st.markdown("---")
    
    # Controles de conexão
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Iniciar", type="primary", use_container_width=True):
            if selected_symbols:
                with st.spinner("🔄 Buscando dados..."):
                    success = st.session_state.data_fetcher.start_fetching(selected_symbols)
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
    
    # Informações sobre APIs
    st.markdown("---")
    st.markdown("**📡 Fontes de Dados:**")
    st.markdown("• CoinGecko API")
    st.markdown("• CryptoCompare API")  
    st.markdown("• CoinAPI")

# Área principal
current_data, historical_data = st.session_state.data_fetcher.get_data()

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
    
    # Gráficos individuais
    st.subheader("📈 Gráficos de Preços")
    
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
    
    # Estatísticas
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
        total_points = sum([len(historical_data.get(s, {}).get('prices', [])) for s in selected_symbols])
        st.metric("📊 Pontos de Dados", total_points)
    
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
        **💰 Dados Financeiros**
        - Preços em tempo real
        - Variação 24h
        - Volume de negociação
        - Múltiplas moedas
        """)
    
    with col2:
        st.markdown("""
        **📊 Visualizações**
        - Gráficos interativos
        - Histórico de preços
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
    
    # Demo com dados fictícios
    st.markdown("---")
    st.subheader("🎮 Preview do Dashboard:")
    
    demo_fig = go.Figure()
    demo_times = pd.date_range(start='2024-01-01 10:00:00', periods=20, freq='5min')
    demo_prices = [45000 + i*100 + (i%3)*200 for i in range(20)]
    
    demo_fig.add_trace(go.Scatter(
        x=demo_times,
        y=demo_prices,
        mode='lines+markers',
        name='BTC/USD (Demo)',
        line=dict(color='#00D4AA', width=3),
        marker=dict(size=4)
    ))
    
    demo_fig.update_layout(
        title='📈 Exemplo: Bitcoin/USD',
        template='plotly_dark',
        height=300,
        showlegend=False
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
st.markdown("💡 **Dashboard de Criptomoedas** - Dados de CoinGecko, CryptoCompare e CoinAPI | Atualização automática configurável")
