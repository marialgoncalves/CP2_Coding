import os
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
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "alertas")


ATIVOS = [
    (1, "SRV-WEB01", "192.168.1.10", "alta"),
    (2, "PC-RH03", "192.168.1.45", "baixa"),
]

ALERTAS = [
    (1, 1, "BRUTE_FORCE", "critica"),
    (2, 1, "PORT_SCAN", "alta"),
    (3, 2, "XSS", "media"),
]


def conectar_mysql():
    return mysql.connector.connect(**MYSQL_CONFIG)


def preparar_mysql():
    conexao = conectar_mysql()
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ativos (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            ip VARCHAR(45) NOT NULL UNIQUE,
            criticidade ENUM('baixa', 'media', 'alta') NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INT PRIMARY KEY,
            ativo_id INT NOT NULL,
            tipo VARCHAR(100) NOT NULL,
            severidade VARCHAR(50) NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
    """)

    # Limpa os dados para que o exercício possa ser executado novamente sem duplicar registros.
    cursor.execute("DELETE FROM alertas")
    cursor.execute("DELETE FROM ativos")

    cursor.executemany("""
        INSERT INTO ativos (id, nome, ip, criticidade)
        VALUES (%s, %s, %s, %s)
    """, ATIVOS)

    cursor.executemany("""
        INSERT INTO alertas (id, ativo_id, tipo, severidade)
        VALUES (%s, %s, %s, %s)
    """, ALERTAS)

    conexao.commit()

    cursor.close()
    conexao.close()


def ler_alertas_com_join():
    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)

    query = """
        SELECT
            a.id AS alerta_id,
            a.tipo,
            a.severidade,
            at.nome,
            at.ip,
            at.criticidade
        FROM alertas AS a
        INNER JOIN ativos AS at
            ON a.ativo_id = at.id
        WHERE a.severidade = %s
           OR a.severidade = %s
           OR a.severidade = %s
    """

    # Os valores são passados separadamente da SQL.
    parametros = ("critica", "alta", "media")

    cursor.execute(query, parametros)

    resultados = cursor.fetchall()

    cursor.close()
    conexao.close()

    return resultados


def montar_documentos(resultados):
    documentos = []

    for alerta in resultados:
        documento = {
            "tipo": alerta["tipo"],
            "severidade": alerta["severidade"],
            "ativo": {
                "nome": alerta["nome"],
                "ip": alerta["ip"],
                "criticidade": alerta["criticidade"],
            },
        }

        documentos.append(documento)

    return documentos


def conectar_mongodb():
    cliente = MongoClient(MONGO_URI)

    banco = cliente[MONGO_DATABASE]
    colecao = banco[MONGO_COLLECTION]

    return cliente, colecao


def inserir_documentos(documentos):
    cliente, colecao = conectar_mongodb()

    # Limpa a coleção para permitir novas execuções.
    colecao.delete_many({})

    resultado = colecao.insert_many(documentos)

    quantidade = len(resultado.inserted_ids)

    cliente.close()

    return quantidade


# VERIFICAÇÃO DA MIGRAÇÃO
def contar_alertas_mysql():
    conexao = conectar_mysql()
    cursor = conexao.cursor()

    cursor.execute("SELECT COUNT(*) FROM alertas")

    quantidade = cursor.fetchone()[0]

    cursor.close()
    conexao.close()

    return quantidade


def contar_documentos_mongodb():
    cliente, colecao = conectar_mongodb()

    quantidade = colecao.count_documents({})

    cliente.close()

    return quantidade


def consultar_ativos_criticos():
    cliente, colecao = conectar_mongodb()

    resultados = list(
        colecao.find(
            {"ativo.criticidade": "alta"},
            {"_id": 0}
        )
    )

    cliente.close()

    return resultados


# EXECUÇÃO PRINCIPAL
def main():
    print("=" * 70)
    print("EXERCÍCIO 2 — MIGRAÇÃO MYSQL → MONGODB")
    print("=" * 70)

    print("\n[1] Preparando MySQL...")
    preparar_mysql()
    print("[OK] MySQL criado e populado.")

    print("\n[2] Executando JOIN parametrizado...")
    resultados = ler_alertas_com_join()

    print(f"[OK] {len(resultados)} alertas recuperados do MySQL.")

    for alerta in resultados:
        print(
            f"    {alerta['tipo']} | "
            f"{alerta['severidade']} | "
            f"{alerta['nome']} | "
            f"{alerta['ip']}"
        )

    print("\n[3] Convertendo registros para documentos MongoDB...")
    documentos = montar_documentos(resultados)

    for documento in documentos:
        print(f"    {documento}")

    print("\n[4] Inserindo documentos no MongoDB...")
    quantidade_inserida = inserir_documentos(documentos)

    print(
        f"[OK] {quantidade_inserida} documentos inseridos."
    )

    print("\n[5] Verificando integridade da migração...")

    quantidade_mysql = contar_alertas_mysql()
    quantidade_mongodb = contar_documentos_mongodb()

    print(
        f"MySQL: {quantidade_mysql} alertas | "
        f"MongoDB: {quantidade_mongodb} documentos"
    )

    if quantidade_mysql == quantidade_mongodb:
        print("MIGRAÇÃO ÍNTEGRA")
    else:
        print("ERRO: quantidade de registros diferente!")

    print("\n[6] Consulta sem JOIN:")
    resultados_criticos = consultar_ativos_criticos()

    print(
        'Consulta: db.alertas.find({"ativo.criticidade":"alta"})'
    )

    print(
        f"Resultado: {len(resultados_criticos)} documentos"
    )

    for documento in resultados_criticos:
        print(f"    {documento}")

    print("\n[7] Análise do modelo de documentos")
    print(
        "Ganho: a leitura do alerta já possui os dados do ativo embutidos, "
        "eliminando a necessidade de JOIN."
    )
    print(
        "Perda: existe duplicação dos dados do ativo; se o ativo for "
        "renomeado, será necessário atualizar vários documentos."
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()

