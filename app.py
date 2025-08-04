# app.py - Versão FINAL com RESPOSTAS AUTOMÁTICAS
import os
import psycopg2
from flask import Flask, request
import datetime
# NOVO: Importa a classe para criar respostas para o Twilio
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def init_db():
    # A função init_db() continua a mesma de antes
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.usuarios')")
        table_exists = cur.fetchone()[0]
        if not table_exists:
            print("Tabelas não encontradas. Criando tabelas...")
            cur.execute("CREATE TABLE usuarios (id SERIAL PRIMARY KEY, numero_whatsapp TEXT NOT NULL UNIQUE, data_criacao TIMESTAMP NOT NULL)")
            cur.execute("CREATE TABLE transacoes (id SERIAL PRIMARY KEY, usuario_id INTEGER NOT NULL, tipo TEXT NOT NULL, valor REAL NOT NULL, descricao TEXT, timestamp TIMESTAMP NOT NULL, FOREIGN KEY (usuario_id) REFERENCES usuarios (id))")
            conn.commit()
            print("Tabelas inicializadas com sucesso.")
        else:
            print("As tabelas já existem. Nenhuma ação necessária.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro durante a inicialização do DB: {e}")

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    sender_id = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').lower().strip()
    
    # NOVO: Cria um objeto de resposta
    resp = MessagingResponse()
    reply_message = "" # Variável para guardar nossa mensagem de resposta

    if not sender_id:
        # Se não houver remetente, não faz nada
        return ('', 400)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("SELECT id FROM usuarios WHERE numero_whatsapp = %s", (sender_id,))
        user = cur.fetchone()

        if not user:
            timestamp = datetime.datetime.now()
            cur.execute("INSERT INTO usuarios (numero_whatsapp, data_criacao) VALUES (%s, %s) RETURNING id", (sender_id, timestamp))
            user_id = cur.fetchone()[0]
            conn.commit()
        else:
            user_id = user[0]

        try:
            partes = incoming_msg.split()
            tipo_comando = partes[0]
            
            if tipo_comando in ['despesa', 'gasto', 'receita', 'ganho']:
                valor_str = partes[1].replace(',', '.')
                valor = float(valor_str)
                descricao = " ".join(partes[2:])
                
                if not descricao: # Adiciona uma descrição padrão se não houver
                    descricao = "Sem descrição"
                
                tipo_final = 'Despesa' if tipo_comando in ['despesa', 'gasto'] else 'Receita'
                timestamp = datetime.datetime.now()

                cur.execute(
                    "INSERT INTO transacoes (usuario_id, tipo, valor, descricao, timestamp) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, tipo_final, valor, descricao, timestamp)
                )
                conn.commit()
                
                # NOVO: Define a mensagem de sucesso
                valor_formatado = f"R$ {valor:.2f}".replace('.', ',')
                if tipo_final == 'Despesa':
                    reply_message = f"Despesa de {valor_formatado} ({descricao}) adicionada com sucesso!"
                else:
                    reply_message = f"Receita de {valor_formatado} ({descricao}) adicionada com sucesso!"

            else:
                # NOVO: Define uma mensagem de ajuda se o comando for inválido
                reply_message = "Comando não reconhecido. Use: 'despesa <valor> <descrição>' ou 'receita <valor> <descrição>'."

        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")
            # NOVO: Define uma mensagem de erro genérica
            reply_message = "Ocorreu um erro ao processar sua solicitação. Verifique o formato do comando."

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro de conexão com o DB no webhook: {e}")
        reply_message = "Não foi possível conectar ao serviço. Tente novamente mais tarde."

    # NOVO: Adiciona a mensagem de resposta ao objeto TwiML e o retorna
    resp.message(reply_message)
    return str(resp)

# Bloco principal
if __name__ != '__main__':
    init_db()

if __name__ == '__main__':
    app.run(port=5000, debug=True)
