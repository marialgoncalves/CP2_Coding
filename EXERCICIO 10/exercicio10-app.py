import os
import logging
import mysql.connector
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

logging.basicConfig(level=logging.ERROR)


MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "senha"),
    "database": os.getenv("MYSQL_DATABASE", "seguranca"),
}


API_KEYS = {
    "key-ana-001": {
        "id": 1,
        "nivel": 5,
    },
    "key-bruno-002": {
        "id": 2,
        "nivel": 2,
    },
}


def db():
    return mysql.connector.connect(**MYSQL_CONFIG)


def aplicar_headers(resposta):
    resposta.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'"
    )

    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"

    return resposta


@app.after_request
def headers_seguranca(resposta):
    return aplicar_headers(resposta)


def autenticar():
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    return API_KEYS.get(api_key)


@app.route("/api/usuarios/buscar")
def buscar():
    nome = request.args.get("nome", "")

    conexao = None
    cursor = None

    try:
        conexao = db()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                nome,
                email
            FROM usuarios
            WHERE nome LIKE %s
            """,
            (f"%{nome}%",),
        )

        usuarios = cursor.fetchall()

        return jsonify(usuarios), 200

    except Exception:
        app.logger.exception("Erro interno em /api/usuarios/buscar")

        return jsonify({
            "erro": "erro interno"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@app.route("/perfil")
def perfil():
    usuario = request.args.get("u", "")

    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Perfil</title>
        </head>
        <body>
            <h1>Bem-vindo, {{ usuario }}</h1>
        </body>
        </html>
        """,
        usuario=usuario,
    )


@app.route(
    "/api/usuarios/<int:uid>",
    methods=["DELETE"]
)
def remover(uid):
    usuario = autenticar()

    if usuario is None:
        return jsonify({
            "erro": "não autenticado"
        }), 401

    if usuario["nivel"] < 5:
        return jsonify({
            "erro": "acesso negado"
        }), 403

    conexao = None
    cursor = None

    try:
        conexao = db()
        cursor = conexao.cursor()

        cursor.execute(
            """
            DELETE FROM usuarios
            WHERE id = %s
            """,
            (uid,),
        )

        if cursor.rowcount == 0:
            conexao.rollback()

            return jsonify({
                "erro": "usuário não encontrado"
            }), 404

        conexao.commit()

        return jsonify({
            "removido": uid
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        app.logger.exception(
            "Erro interno ao remover usuário"
        )

        return jsonify({
            "erro": "erro interno"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@app.route("/api/relatorio")
def relatorio():
    conexao = None
    cursor = None

    try:
        conexao = db()
        cursor = conexao.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nome,
                email
            FROM usuarios
            """
        )

        dados = cursor.fetchall()

        return jsonify(dados), 200

    except Exception:
        app.logger.exception(
            "Erro interno ao gerar relatório"
        )

        return jsonify({
            "erro": "erro interno"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@app.errorhandler(500)
def erro_500(_erro):
    return jsonify({
        "erro": "erro interno"
    }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )