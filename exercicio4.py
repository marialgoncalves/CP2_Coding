import os
from datetime import datetime, timezone

import mysql.connector
from pymongo import MongoClient


MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DATABASE", "security_lab"),
}

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "security_lab")


usuarios = [
    (1, "ana", "ana@x.com", 5),
    (2, "bruno", "bruno@x.com", 2),
    (3, "caio", "caio@x.com", 1),
]


def conectar_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)
    banco = cliente[MONGO_DATABASE]
    return cliente, banco["auditoria"]


def preparar_banco():
    conexao = conectar_mysql()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            nivel_acesso INT NOT NULL
        )
    """)

    cursor.execute("DELETE FROM usuarios")

    cursor.executemany("""
        INSERT INTO usuarios
        (id, nome, email, nivel_acesso)
        VALUES (%s, %s, %s, %s)
    """, usuarios)

    conexao.commit()
    cursor.close()
    conexao.close()


def registrar_auditoria(
    quem,
    alvo,
    nivel_anterior,
    nivel_novo,
    resultado
):
    cliente, colecao = conectar_mongodb()

    colecao.insert_one({
        "quem": quem,
        "alvo": alvo,
        "nivel_anterior": nivel_anterior,
        "nivel_novo": nivel_novo,
        "resultado": resultado,
        "timestamp": datetime.now(timezone.utc),
    })

    cliente.close()


def alterar_nivel(admin_id, alvo_id, novo_nivel):
    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    nivel_anterior = None
    resultado = "RECUSADO"

    try:
        cursor.execute("""
            SELECT id, nivel_acesso
            FROM usuarios
            WHERE id = %s
            FOR UPDATE
        """, (admin_id,))

        admin = cursor.fetchone()

        cursor.execute("""
            SELECT id, nivel_acesso
            FROM usuarios
            WHERE id = %s
            FOR UPDATE
        """, (alvo_id,))

        alvo = cursor.fetchone()

        if admin is None:
            conexao.rollback()

            registrar_auditoria(
                admin_id,
                alvo_id,
                None,
                novo_nivel,
                "RECUSADO"
            )

            return "RECUSADO (admin inexistente)"

        if alvo is not None:
            nivel_anterior = alvo["nivel_acesso"]

        if admin["nivel_acesso"] < 5:
            conexao.rollback()

            registrar_auditoria(
                admin_id,
                alvo_id,
                nivel_anterior,
                novo_nivel,
                "RECUSADO"
            )

            return "RECUSADO (admin sem privilégio)"

        if admin_id == alvo_id:
            conexao.rollback()

            registrar_auditoria(
                admin_id,
                alvo_id,
                nivel_anterior,
                novo_nivel,
                "RECUSADO"
            )

            return "RECUSADO (auto-promoção)"

        if alvo is None:
            conexao.rollback()

            registrar_auditoria(
                admin_id,
                alvo_id,
                None,
                novo_nivel,
                "RECUSADO"
            )

            return "RECUSADO (alvo inexistente)"

        cursor.execute("""
            UPDATE usuarios
            SET nivel_acesso = %s
            WHERE id = %s
        """, (novo_nivel, alvo_id))

        if cursor.rowcount != 1:
            conexao.rollback()

            registrar_auditoria(
                admin_id,
                alvo_id,
                nivel_anterior,
                novo_nivel,
                "RECUSADO"
            )

            return "RECUSADO (alteração não realizada)"

        conexao.commit()
        resultado = "OK"

        registrar_auditoria(
            admin_id,
            alvo_id,
            nivel_anterior,
            novo_nivel,
            resultado
        )

        return (
            f"OK. commit. "
            f"Usuário {alvo_id}: "
            f"{nivel_anterior} -> {novo_nivel}"
        )

    except Exception:
        conexao.rollback()

        registrar_auditoria(
            admin_id,
            alvo_id,
            nivel_anterior,
            novo_nivel,
            "RECUSADO"
        )

        return "RECUSADO (erro na transação)"

    finally:
        cursor.close()
        conexao.close()


def consultar_usuario(usuario_id):
    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, nome, nivel_acesso
        FROM usuarios
        WHERE id = %s
    """, (usuario_id,))

    usuario = cursor.fetchone()

    cursor.close()
    conexao.close()

    return usuario


def contar_recusas():
    cliente, colecao = conectar_mongodb()

    quantidade = colecao.count_documents({
        "resultado": "RECUSADO"
    })

    cliente.close()

    return quantidade


def main():
    preparar_banco()

    cliente, colecao = conectar_mongodb()
    colecao.delete_many({})
    cliente.close()

    print("alterar_nivel(1, 2, 4) ->",
          alterar_nivel(1, 2, 4))

    print("Bruno:",
          consultar_usuario(2)["nivel_acesso"])

    print("alterar_nivel(2, 3, 5) ->",
          alterar_nivel(2, 3, 5))

    print("Caio:",
          consultar_usuario(3)["nivel_acesso"])

    print("alterar_nivel(1, 1, 9) ->",
          alterar_nivel(1, 1, 9))

    print("Ana:",
          consultar_usuario(1)["nivel_acesso"])

    print("alterar_nivel(1, 99, 3) ->",
          alterar_nivel(1, 99, 3))

    cliente, colecao = conectar_mongodb()

    total = colecao.count_documents({})
    recusas = colecao.count_documents({
        "resultado": "RECUSADO"
    })

    print(f"\nTrilha de auditoria: {total} documentos")
    print(
        'db.auditoria.count_documents({"resultado":"RECUSADO"})'
        f" -> {recusas}"
    )

    cliente.close()


if __name__ == "__main__":
    main()