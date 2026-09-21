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


COLUNAS = {
    "data": "criado_em",
    "sev": "severidade",
    "ip": "ip_origem",
}

ORDEM = {
    "asc": "ASC",
    "desc": "DESC",
}

TAMANHO_MAXIMO = 100


def conectar_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


@app.route("/api/eventos", methods=["GET"])
def listar_eventos():
    ordenar_por = request.args.get("ordenar_por", "data")
    ordem = request.args.get("ordem", "asc")
    tamanho = request.args.get("tamanho", "10")

    # ORDER BY não aceita um placeholder para nome de coluna:
    # LIMIT %s funciona porque o valor é um dado.
    # ORDER BY %s não funciona porque nome de coluna é um identificador SQL.
    # Portanto, identificadores devem ser controlados por uma whitelist fechada.

    if ordenar_por not in COLUNAS:
        return jsonify({
            "erro": "campo de ordenação inválido"
        }), 400

    if ordem not in ORDEM:
        return jsonify({
            "erro": "ordem de ordenação inválida"
        }), 400

    try:
        tamanho = int(tamanho)
    except ValueError:
        return jsonify({
            "erro": "tamanho deve ser inteiro"
        }), 400

    if tamanho < 1:
        return jsonify({
            "erro": "tamanho deve ser maior que zero"
        }), 400

    tamanho = min(tamanho, TAMANHO_MAXIMO)

    coluna = COLUNAS[ordenar_por]
    direcao = ORDEM[ordem]

    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    query = f"""
        SELECT
            id,
            tipo,
            severidade,
            ip_origem,
            criado_em
        FROM eventos
        ORDER BY {coluna} {direcao}
        LIMIT %s
    """

    cursor.execute(query, (tamanho,))

    eventos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return jsonify({
        "total": len(eventos),
        "eventos": eventos
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )