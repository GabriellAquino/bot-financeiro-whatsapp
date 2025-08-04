# app.py - Versão FINAL com inicialização automática do DB
import os
import psycopg2
from flask import Flask, request
import datetime

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def init_db():
    """
    Verifica se a tabela 'usuarios' existe. Se não existir,
    cria todas as tabelas necessárias.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Query para verificar se a tabela 'usuarios' já existe
        cur.execute("SELECT to_regclass('public.usuarios')")
        table_exists = cur.fetchone()[0]

        if table_exists:
            print("As tabelas já existem. Nenhuma ação necessária.")
        else:
            print("Tabelas não encontradas. Criando tabelas...")
            # Se a tabela não existe, cria ambas
            cur.execute("""
            CREATE TABLE usuarios (
                id SERIAL PRIMARY KEY,
                numero_whatsapp TEXT NOT NULL UNIQUE,
                data_criacao TIMESTAMP NOT NULL
            )
            """)

            cur.execute("""
            CREATE TABLE transacoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                valor REAL NOT NULL,
                descricao TEXT,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
            """)
            conn.commit()
            print("Tabelas inicializadas com sucesso.")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro durante a inicialização do DB: {e}")

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    # A lógica do webhook continua exatamente a mesma de antes
    sender_id = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').lower().strip()
    
    if not sender_id:
        return ('', 400)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("SELECT id FROM usuarios WHERE numero_whatsapp = %s", (sender_id,))
        user = cur.fetchone()

        if not user:
            timestamp = datetime.datetime.now()
            cur.execute("INSERT INTO usuarios (numero_whatsapp, data_criacao) VALUES (%s, %s) RETURNING id", 
                        (sender_id, timestamp))
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
                tipo_final = 'Despesa' if tipo_comando in ['despesa', 'gasto'] else 'Receita'
                timestamp = datetime.datetime.now()

                cur.execute("""
                    INSERT INTO transacoes (usuario_id, tipo, valor, descricao, timestamp) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, tipo_final, valor, descricao, timestamp))
                conn.commit()
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Erro de conexão com o DB no webhook: {e}")

    return ('', 204)

# Bloco principal
if __name__ != '__main__':
    # Esta linha será executada quando o código rodar no Render (não localmente)
    # Chama a função para verificar e, se necessário, criar o banco de dados
    init_db()

if __name__ == '__main__':
    # Esta parte é para rodar localmente, se necessário
    app.run(port=5000, debug=True)
