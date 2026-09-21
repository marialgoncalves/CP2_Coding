from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)


MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "security_lab"
}


COLUNAS = {
    "data": "criado_em",
    "sev": "severidade",
    "ip": "ip_origem"
}

ORDEM = {
    "asc": "ASC",
    "desc": "DESC"
}


def conectar_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


def preparar_banco():
    conn = conectar_mysql()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            criado_em DATETIME NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            ip_origem VARCHAR(45) NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM eventos")
    quantidade = cursor.fetchone()[0]

    if quantidade == 0:
        dados = [
            ("2026-09-01 08:00:00", "alta", "192.168.1.10"),
            ("2026-09-01 09:00:00", "media", "192.168.1.20"),
            ("2026-09-01 10:00:00", "critica", "10.0.0.15"),
            ("2026-09-01 11:00:00", "baixa", "172.16.0.5"),
            ("2026-09-01 12:00:00", "alta", "192.168.1.30"),
            ("2026-09-01 13:00:00", "media", "10.0.0.20"),
            ("2026-09-01 14:00:00", "critica", "172.16.0.10"),
        ]

        cursor.executemany(
            """
            INSERT INTO eventos
                (criado_em, severidade, ip_origem)
            VALUES (%s, %s, %s)
            """,
            dados
        )

    conn.commit()

    cursor.close()
    conn.close()


@app.route("/api/eventos", methods=["GET"])
def listar_eventos():
    ordenar_por = request.args.get("ordenar_por", "data")
    ordem = request.args.get("ordem", "asc")
    tamanho = request.args.get("tamanho", "10")

    if ordenar_por not in COLUNAS:
        return jsonify({
            "erro": "campo de ordenação inválido"
        }), 400

    if ordem not in ORDEM:
        return jsonify({
            "erro": "ordem inválida"
        }), 400

    try:
        tamanho = int(tamanho)
    except ValueError:
        return jsonify({
            "erro": "tamanho deve ser um número inteiro"
        }), 400

    if tamanho <= 0:
        return jsonify({
            "erro": "tamanho deve ser maior que zero"
        }), 400

    tamanho = min(tamanho, 100)

    coluna = COLUNAS[ordenar_por]
    direcao = ORDEM[ordem]

    query = f"""
        SELECT id, criado_em, severidade, ip_origem
        FROM eventos
        ORDER BY {coluna} {direcao}
        LIMIT %s
    """

    conn = conectar_mysql()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(query, (tamanho,))
        eventos = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return jsonify({
        "total": len(eventos),
        "eventos": eventos
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


def executar_testes():
    with app.test_client() as client:

        resposta = client.get(
            "/api/eventos?ordenar_por=sev&ordem=asc&tamanho=5"
        )

        print(
            "[TESTE 1]",
            resposta.status_code,
            resposta.get_json()
        )

        resposta = client.get(
            "/api/eventos?ordenar_por=id%20DESC&ordem=asc&tamanho=5"
        )

        print(
            "[TESTE 2]",
            resposta.status_code,
            resposta.get_json()
        )

        resposta = client.get(
            "/api/eventos?ordenar_por=data&ordem=asc&tamanho=abc"
        )

        print(
            "[TESTE 3]",
            resposta.status_code,
            resposta.get_json()
        )

        resposta = client.get(
            "/api/eventos?ordenar_por=data&ordem=asc&tamanho=100000"
        )

        dados = resposta.get_json()

        print(
            "[TESTE 4]",
            resposta.status_code,
            "quantidade:",
            len(dados["eventos"])
        )


if __name__ == "__main__":
    preparar_banco()

    print("=" * 60)
    print("EXERCÍCIO 5 — API DE EVENTOS")
    print("=" * 60)

    executar_testes()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )