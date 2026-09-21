import mysql.connector
from pymongo import MongoClient
from datetime import datetime


MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "security_lab"
}

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DATABASE = "security_lab"


def conectar_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


def conectar_mongo():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DATABASE]


def preparar_mysql():
    conn = conectar_mysql()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS alertas")
    cursor.execute("DROP TABLE IF EXISTS ativos")

    cursor.execute("""
        CREATE TABLE ativos (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            criticidade VARCHAR(20) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE alertas (
            id INT PRIMARY KEY,
            ativo_id INT NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            descricao VARCHAR(255) NOT NULL,
            criado_em DATETIME NOT NULL,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
    """)

    ativos = [
        (1, "Servidor-Web-01", "alta"),
        (2, "Servidor-DB-01", "alta"),
        (3, "Notebook-ADM-01", "media"),
    ]

    alertas = [
        (
            1,
            1,
            "critica",
            "Tentativa de exploração",
            datetime(2026, 9, 1, 10, 0, 0)
        ),
        (
            2,
            1,
            "alta",
            "Múltiplas falhas de autenticação",
            datetime(2026, 9, 1, 11, 0, 0)
        ),
        (
            3,
            2,
            "alta",
            "Porta administrativa exposta",
            datetime(2026, 9, 1, 12, 0, 0)
        ),
        (
            4,
            3,
            "media",
            "Software desatualizado",
            datetime(2026, 9, 1, 13, 0, 0)
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO ativos (id, nome, criticidade)
        VALUES (%s, %s, %s)
        """,
        ativos
    )

    cursor.executemany(
        """
        INSERT INTO alertas
            (id, ativo_id, severidade, descricao, criado_em)
        VALUES (%s, %s, %s, %s, %s)
        """,
        alertas
    )

    conn.commit()

    print("[OK] Banco MySQL preparado.")

    cursor.close()
    conn.close()


def extrair_dados_mysql():
    conn = conectar_mysql()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            al.id AS alerta_id,
            al.ativo_id,
            al.severidade,
            al.descricao,
            al.criado_em,
            at.nome AS ativo_nome,
            at.criticidade AS ativo_criticidade
        FROM alertas al
        INNER JOIN ativos at
            ON al.ativo_id = at.id
        ORDER BY al.id
    """

    cursor.execute(query)
    resultados = cursor.fetchall()

    cursor.close()
    conn.close()

    return resultados


def converter_para_mongodb(registros):
    documentos = []

    for registro in registros:
        documento = {
            "alerta_id": registro["alerta_id"],
            "severidade": registro["severidade"],
            "descricao": registro["descricao"],
            "criado_em": registro["criado_em"],
            "ativo": {
                "id": registro["ativo_id"],
                "nome": registro["ativo_nome"],
                "criticidade": registro["ativo_criticidade"]
            }
        }

        documentos.append(documento)

    return documentos


def migrar_para_mongodb(documentos):
    db = conectar_mongo()
    colecao = db["alertas"]

    colecao.delete_many({})

    if documentos:
        resultado = colecao.insert_many(documentos)
        print(
            f"[OK] {len(resultado.inserted_ids)} documentos "
            "inseridos no MongoDB."
        )

    return colecao


def comparar_quantidades(total_mysql, colecao):
    total_mongo = colecao.count_documents({})

    print(f"[INFO] Alertas no MySQL: {total_mysql}")
    print(f"[INFO] Documentos no MongoDB: {total_mongo}")

    if total_mysql == total_mongo:
        print("[OK] Nenhum alerta foi perdido durante a migração.")
    else:
        print("[ERRO] A quantidade de registros não coincide.")

    return total_mongo


def consultar_ativos_criticidade_alta(colecao):
    resultados = list(
        colecao.find(
            {"ativo.criticidade": "alta"},
            {"_id": 0}
        )
    )

    print("\nAlertas relacionados a ativos de criticidade alta:")

    for alerta in resultados:
        print(
            f"- Alerta {alerta['alerta_id']} | "
            f"Ativo: {alerta['ativo']['nome']} | "
            f"Severidade: {alerta['severidade']}"
        )

    print(f"[INFO] Total encontrado: {len(resultados)}")

    return resultados


def main():
    print("=" * 60)
    print("EXERCÍCIO 2 — MIGRAÇÃO MYSQL → MONGODB")
    print("=" * 60)

    preparar_mysql()

    registros = extrair_dados_mysql()

    print(f"[INFO] Registros obtidos pelo JOIN: {len(registros)}")

    documentos = converter_para_mongodb(registros)

    colecao = migrar_para_mongodb(documentos)

    comparar_quantidades(
        total_mysql=len(registros),
        colecao=colecao
    )

    consultar_ativos_criticidade_alta(colecao)

    print("\nANÁLISE:")
    print(
        "- O modelo relacional utiliza JOIN entre ativos e alertas."
    )
    print(
        "- No MongoDB, os dados do ativo são incorporados "
        "diretamente ao documento do alerta."
    )
    print(
        "- O embedding evita JOINs durante consultas que precisam "
        "dos dados do ativo junto ao alerta."
    )
    print(
        "- A desvantagem é a duplicação dos dados do ativo caso "
        "existam muitos alertas para o mesmo ativo."
    )
    print(
        "- A comparação das quantidades confirma que nenhum alerta "
        "foi perdido durante a migração."
    )


if __name__ == "__main__":
    main()