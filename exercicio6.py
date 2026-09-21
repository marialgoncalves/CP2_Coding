import os
from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DATABASE", "security_lab"),
}


ANALISTAS = [
    (1, "ana", "key-ana-001", 5),
    (2, "bruno", "key-bruno-002", 2),
]

INCIDENTES = [
    (1, 1, "Brute force SSH", "critica", "aberto"),
    (2, 2, "Phishing no RH", "media", "aberto"),
]


def conectar_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


def preparar_banco():
    conexao = conectar_mysql()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analistas (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            api_key VARCHAR(255) NOT NULL UNIQUE,
            nivel INT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidentes (
            id INT PRIMARY KEY,
            dono_id INT NOT NULL,
            titulo VARCHAR(255) NOT NULL,
            severidade VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            FOREIGN KEY (dono_id) REFERENCES analistas(id)
        )
    """)

    cursor.execute("DELETE FROM incidentes")
    cursor.execute("DELETE FROM analistas")

    cursor.executemany("""
        INSERT INTO analistas
        (id, nome, api_key, nivel)
        VALUES (%s, %s, %s, %s)
    """, ANALISTAS)

    cursor.executemany("""
        INSERT INTO incidentes
        (id, dono_id, titulo, severidade, status)
        VALUES (%s, %s, %s, %s, %s)
    """, INCIDENTES)

    conexao.commit()

    cursor.close()
    conexao.close()


def autenticar():
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome, nivel
        FROM analistas
        WHERE api_key = %s
    """, (api_key,))

    analista = cursor.fetchone()

    cursor.close()
    conexao.close()

    return analista


@app.route("/api/incidentes/<int:incidente_id>", methods=["GET"])
def obter_incidente(incidente_id):
    analista = autenticar()

    if analista is None:
        return jsonify({
            "erro": "não autenticado"
        }), 401

    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            dono_id,
            titulo,
            severidade,
            status
        FROM incidentes
        WHERE id = %s
    """, (incidente_id,))

    incidente = cursor.fetchone()

    cursor.close()
    conexao.close()

    if incidente is None:
        return jsonify({
            "erro": "incidente não encontrado"
        }), 404

    if incidente["dono_id"] != analista["id"]:
        return jsonify({
            "erro": "acesso negado"
        }), 403

    return jsonify(incidente), 200


@app.route("/api/incidentes", methods=["GET"])
def listar_incidentes():
    analista = autenticar()

    if analista is None:
        return jsonify({
            "erro": "não autenticado"
        }), 401

    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            dono_id,
            titulo,
            severidade,
            status
        FROM incidentes
        WHERE dono_id = %s
    """, (analista["id"],))

    incidentes = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify(incidentes), 200


@app.route("/api/incidentes/<int:incidente_id>", methods=["DELETE"])
def apagar_incidente(incidente_id):
    analista = autenticar()

    if analista is None:
        return jsonify({
            "erro": "não autenticado"
        }), 401

    if analista["nivel"] < 5:
        return jsonify({
            "erro": "acesso negado"
        }), 403

    conexao = conectar_mysql()
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id
        FROM incidentes
        WHERE id = %s
    """, (incidente_id,))

    incidente = cursor.fetchone()

    if incidente is None:
        cursor.close()
        conexao.close()

        return jsonify({
            "erro": "incidente não encontrado"
        }), 404

    cursor.execute("""
        DELETE FROM incidentes
        WHERE id = %s
    """, (incidente_id,))

    conexao.commit()

    cursor.close()
    conexao.close()

    return jsonify({
        "mensagem": "incidente removido com sucesso"
    }), 200


if __name__ == "__main__":
    preparar_banco()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )