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
            ip VARCHAR(45) NOT NULL UNIQUE,
            criticidade ENUM('baixa', 'media', 'alta') NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE alertas (
            id INT PRIMARY KEY,
            ativo_id INT NOT NULL,
            tipo VARCHAR(100) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            criado_em DATETIME NOT NULL,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
    """)

    ativos = [
        (
            1,
            "SRV-WEB01",
            "192.168.1.10",
            "alta"
        ),
        (
            2,
            "PC-RH03",
            "192.168.1.45",
            "baixa"
        ),
    ]

    alertas = [
        (
            1,
            1,
            "BRUTE_FORCE",
            "critica",
            datetime(2026, 9, 1, 10, 0, 0)
        ),
        (
            2,
            1,
            "PORT_SCAN",
            "alta",
            datetime(2026, 9, 1, 11, 0, 0)
        ),
        (
            3,
            2,
            "XSS",
            "media",
            datetime(2026, 9, 1, 12, 0, 0)
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO ativos
            (id, nome, ip, criticidade)
        VALUES
            (%s, %s, %s, %s)
        """,
        ativos
    )

    cursor.executemany(
        """
        INSERT INTO alertas
            (id, ativo_id, tipo, severidade, criado_em)
        VALUES
            (%s, %s, %s, %s, %s)
        """,
        alertas
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("[OK] MySQL preparado.")


def extrair_dados_mysql():
    conn = conectar_mysql()
    cursor = conn.cursor(dictionary=True)

    # Os valores continuam separados dos comandos SQL.
    # O parâmetro permite demonstrar o uso de consulta parametrizada.
    query = """
        SELECT
            al.id AS alerta_id,
            al.ativo_id,
            al.tipo,
            al.severidade,
            al.criado_em,
            at.nome AS ativo_nome,
            at.ip AS ativo_ip,
            at.criticidade AS ativo_criticidade
        FROM alertas al
        INNER JOIN ativos at
            ON al.ativo_id = at.id
        WHERE al.id >= %s
        ORDER BY al.id
    """

    cursor.execute(query, (1,))

    resultados = cursor.fetchall()

    cursor.close()
    conn.close()

    return resultados


def contar_alertas_mysql():
    conn = conectar_mysql()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM alertas")

    quantidade = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return quantidade


def converter_para_mongodb(registros):
    documentos = []

    for registro in registros:
        documento = {
            "alerta_id": registro["alerta_id"],
            "tipo": registro["tipo"],
            "severidade": registro["severidade"],
            "criado_em": registro["criado_em"],
            "ativo": {
                "nome": registro["ativo_nome"],
                "ip": registro["ativo_ip"],
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
            f"[OK] {len(resultado.inserted_ids)} "
            "documentos inseridos no MongoDB."
        )

    return colecao


def comparar_quantidades(total_mysql, colecao):
    total_mongo = colecao.count_documents({})

    print()
    print(f"MySQL: {total_mysql} alertas")
    print(f"MongoDB: {total_mongo} documentos")

    if total_mysql == total_mongo:
        print("MIGRAÇÃO ÍNTEGRA")
    else:
        print("ERRO: a quantidade de registros não coincide.")

    return total_mongo


def consultar_criticidade_alta(colecao):
    resultados = list(
        colecao.find(
            {
                "ativo.criticidade": "alta"
            },
            {
                "_id": 0
            }
        )
    )

    print()
    print(
        'db.alertas.find({"ativo.criticidade":"alta"})'
    )

    for documento in resultados:
        print(documento)

    print(
        f"Quantidade encontrada: {len(resultados)}"
    )

    return resultados


def main():
    print("=" * 70)
    print("EXERCÍCIO 2 — MIGRAÇÃO MYSQL → MONGODB")
    print("=" * 70)

    preparar_mysql()

    registros = extrair_dados_mysql()

    print(
        f"[INFO] Registros obtidos pelo JOIN: "
        f"{len(registros)}"
    )

    documentos = converter_para_mongodb(registros)

    colecao = migrar_para_mongodb(documentos)

    total_mysql = contar_alertas_mysql()

    comparar_quantidades(
        total_mysql,
        colecao
    )

    resultados_alta = consultar_criticidade_alta(
        colecao
    )

    print()
    print("ANÁLISE:")
    print(
        "- Ganho: os dados do ativo ficam embutidos no "
        "documento e a leitura não precisa de JOIN."
    )
    print(
        "- Perda: existe duplicação dos dados do ativo "
        "em vários alertas."
    )
    print(
        "- Se o nome, IP ou criticidade de um ativo mudar, "
        "pode ser necessário utilizar update_many() "
        "nos documentos relacionados."
    )

    if (
        total_mysql == 3
        and len(documentos) == 3
        and colecao.count_documents({}) == 3
        and len(resultados_alta) == 2
    ):
        print()
        print("[OK] Todos os resultados esperados foram confirmados.")
    else:
        print()
        print("[ERRO] Algum resultado não corresponde ao enunciado.")


if __name__ == "__main__":
    main()