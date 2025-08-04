# app.py - Versão para PostgreSQL
import os
import psycopg2
from flask import Flask, request
import datetime

app = Flask(__name__)

# Pega a URL do banco de dados a partir das variáveis de ambiente do Render
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Cria uma conexão com o banco de dados PostgreSQL."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Função para criar as tabelas do banco de dados se elas não existirem."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        numero_whatsapp TEXT NOT NULL UNIQUE,
        data_criacao TIMESTAMP NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
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
    cur.close()
    conn.close()
    print("Tabelas inicializadas com sucesso.")

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    # Lógica completa do webhook aqui...
    # (O código é o mesmo da resposta anterior sobre PostgreSQL)
    sender_id = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').lower().strip()

    if not sender_id:
        return ('', 400)

    conn = get_db_connection()
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
    return ('', 204)

if __name__ == '__main__':
    # Não precisamos mais do init_db() aqui ao rodar localmente
    app.run(port=5000, debug=True)