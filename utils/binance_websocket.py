import websocket
import json
import threading
import time
from typing import Dict, Callable, List
import pandas as pd

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
            print(f"Erro ao processar mensagem: {e}")
    
    def on_error(self, ws, error):
        """Trata erros da conexão WebSocket"""
        print(f"Erro WebSocket: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Trata fechamento da conexão"""
        print("Conexão WebSocket fechada")
        self.running = False
    
    def on_open(self, ws):
        """Trata abertura da conexão"""
        print("Conexão WebSocket estabelecida")
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
    
    def get_current_data(self):
        """Retorna dados atuais"""
        return self.price_data, self.historical_data
